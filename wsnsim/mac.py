from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional, Callable
import numpy as np
from .energy import RadioState

if TYPE_CHECKING:
    from numpy.random import Generator
    from .sim import EventScheduler
    from .energy import EnergyModel


@dataclass(frozen=True)
class MacConfig:
    """MAC parameters. All time units in seconds.
    
    To ensure Slotted ALOHA efficiency, tx_duration should be <= slot_time.
    """
    slot_time: float = 0.005       # 5ms slot
    cw_min: int = 7                # Binary backoff initial window (slots)
    cw_max: int = 1023             # Binary backoff max window (slots)
    max_retries: int = 5           # Max retransmission attempts
    tx_duration: float = 0.005     # Default duration (fallback)
    ack_timeout: float = 0.015     # Time to wait for an ACK before backoff
    bit_rate: float = 250000.0     # 250 kbps (standard for 802.15.4)

class BaseMac:
    """Common state and energy tracking for MAC protocols."""
    def __init__(self, node_id: int, scheduler: EventScheduler, rng: Generator, 
                 config: MacConfig, channel: Any, energy_model: Optional[EnergyModel] = None,
                 security_model: Optional[Any] = None):
        self.node_id = node_id
        self.scheduler = scheduler
        self.rng = rng
        self.config = config
        self.channel = channel
        self.energy_model = energy_model
        self.security_model = security_model
        
        self.on_receive_data: Optional[Callable[[Any], None]] = None
        self.retries = 0
        self.waiting_for_ack = False
        self.received_cache: dict[tuple[int, int], bool] = {}  # (src, packet_id) -> True

    def _update_radio(self, state_name: str):
        if self.energy_model:
            self.energy_model.update_state(RadioState[state_name], self.scheduler.current_time)

    def receive(self, packet: Any, duration: float):
        """Called by the channel when a packet arrives at this node.
        
        Args:
            packet: The received packet object.
            duration: The time it took to receive the packet (for energy tracking).
        """
        if packet.dest != self.node_id and packet.dest != -1:
            return # Not for us

        # Retroactive energy accounting for the reception period
        if self.energy_model:
            # If already dead, we can't receive anything
            if self.energy_model.is_out_of_energy(self.scheduler.current_time):
                return

            # Update up to the start of reception
            last_change = self.energy_model.metrics.last_state_change_time
            start_rx_time = max(last_change, self.scheduler.current_time - duration)
            
            self.energy_model.update_state(RadioState.RX, start_rx_time)
            self.energy_model.update_state(RadioState.IDLE, self.scheduler.current_time)

        # Security Verification (skip for ACKs for now to avoid complexity)
        if self.security_model and not packet.is_ack:
            from .common import Packet
            if isinstance(packet, Packet):
                if not self.security_model.verify_packet(packet, self.energy_model, self.scheduler.current_time):
                    # Replay detected or invalid OR node died during verification - drop the packet
                    return

        if packet.is_ack:
            self._handle_ack(packet)
        else:
            self._handle_data(packet)

    def _handle_ack(self, packet: Any):
        """Handle incoming ACK: stop waiting for the current packet."""
        # Simple Stop-and-Wait ARQ: any ACK addressed to us clears the flag.
        self.waiting_for_ack = False

    def _handle_data(self, packet: Any):
        """Handle incoming data: send ACK and pass up if not a duplicate."""
        # 1. Send ACK if it was a unicast packet
        if packet.dest == self.node_id:
            # SIFS (Short Interframe Space) delay before ACK
            ack_delay = self.config.slot_time * 0.1 
            self.scheduler.schedule(ack_delay, self._send_ack, packet.src, packet.packet_id)

        # 2. Duplicate detection
        cache_key = (packet.src, packet.packet_id)
        if cache_key in self.received_cache:
            return # Duplicate, don't pass up
        
        self.received_cache[cache_key] = True
        if len(self.received_cache) > 200:
            # Remove the oldest item (Python 3.7+ dicts are ordered)
            oldest_key = next(iter(self.received_cache))
            del self.received_cache[oldest_key]

        # 3. Pass to upper layer
        if self.on_receive_data:
            self.on_receive_data(packet)

    def _send_ack(self, dest_id: int, packet_id: int):
        """Transmit a small ACK packet."""
        # Final energy check
        if self.energy_model and self.energy_model.is_out_of_energy(self.scheduler.current_time):
            return

        from .common import Packet
        ack_pkt = Packet(
            src=self.node_id,
            dest=dest_id,
            payload="ACK",
            packet_id=packet_id,
            is_ack=True
        )
        # ACKs are small, so they take less time
        ack_duration = self.config.tx_duration * 0.4
        self._update_radio("TX")
        # Use a fixed low power for ACK to avoid interference
        self.channel.transmit(self.node_id, ack_pkt, dest_id, 1.0, ack_duration)
        self.scheduler.schedule(ack_duration, self._update_radio, "IDLE")

    def _transmit(self, payload: Any, dest_id: int, tx_power_mw: float):
        """Low-level transmission call with security signing and dynamic duration."""
        from .common import Packet
        
        # 0. Check if we have energy to even start
        if self.energy_model and self.energy_model.is_out_of_energy(self.scheduler.current_time):
            return

        # 1. Apply Security Signing (only if not already signed/nonce is 0)
        latency = 0.0
        if self.security_model and isinstance(payload, Packet) and payload.nonce == 0:
            latency = self.security_model.sign_packet(payload, self.energy_model, self.scheduler.current_time)
            
        # 2. Re-check energy after potential crypto cost
        if self.energy_model and self.energy_model.is_out_of_energy(self.scheduler.current_time):
            return

        # 3. Calculate dynamic transmission duration based on size
        duration = self.config.tx_duration
        if isinstance(payload, Packet):
            # bits / (bits/sec) = seconds
            duration = (payload.size_bytes * 8) / self.config.bit_rate
            
        # 4. Schedule actual transmission after crypto processing delay
        if latency > 0:
            self.scheduler.schedule(latency, self._do_transmit, payload, dest_id, tx_power_mw, duration)
        else:
            self._do_transmit(payload, dest_id, tx_power_mw, duration)

    def _do_transmit(self, payload: Any, dest_id: int, tx_power_mw: float, duration: float):
        """Physical radio transmission after potential crypto delay."""
        # Final energy check
        if self.energy_model and self.energy_model.is_out_of_energy(self.scheduler.current_time):
            return

        self._update_radio("TX")
        # Set waiting flag for unicast (dest_id != -1)
        self.waiting_for_ack = (dest_id != -1)
        self.channel.transmit(self.node_id, payload, dest_id, tx_power_mw, duration)
        self.scheduler.schedule(duration, self._update_radio, "IDLE")

class PureAlohaMac(BaseMac):
    """Pure ALOHA: Send immediately, backoff on ACK timeout."""
    def send(self, payload: Any, dest_id: int, tx_power_mw: float):
        self.retries = 0
        self._attempt_send(payload, dest_id, tx_power_mw)

    def _attempt_send(self, payload: Any, dest_id: int, tx_power_mw: float):
        self._transmit(payload, dest_id, tx_power_mw)
        if self.waiting_for_ack:
            self.scheduler.schedule(self.config.ack_timeout, self._check_ack, payload, dest_id, tx_power_mw)

    def _check_ack(self, payload: Any, dest_id: int, tx_power_mw: float):
        if self.waiting_for_ack:
            if self.retries < self.config.max_retries:
                self.retries += 1
                delay = self.rng.integers(1, 2**self.retries + 1) * self.config.slot_time
                self.scheduler.schedule(delay, self._attempt_send, payload, dest_id, tx_power_mw)

class SlottedAlohaMac(BaseMac):
    """Slotted ALOHA: Sync to slot boundary, then behave like Pure ALOHA."""
    def send(self, payload: Any, dest_id: int, tx_power_mw: float):
        self.retries = 0
        self._sync_and_attempt(payload, dest_id, tx_power_mw)

    def _sync_and_attempt(self, payload: Any, dest_id: int, tx_power_mw: float):
        now = self.scheduler.current_time
        wait = (self.config.slot_time - (now % self.config.slot_time)) % self.config.slot_time
        self.scheduler.schedule(wait, self._run_slot, payload, dest_id, tx_power_mw)

    def _run_slot(self, payload: Any, dest_id: int, tx_power_mw: float):
        self._transmit(payload, dest_id, tx_power_mw)
        if self.waiting_for_ack:
            self.scheduler.schedule(self.config.ack_timeout, self._check_ack, payload, dest_id, tx_power_mw)

    def _check_ack(self, payload: Any, dest_id: int, tx_power_mw: float):
        if self.waiting_for_ack:
            if self.retries < self.config.max_retries:
                self.retries += 1
                slots_to_skip = self.rng.integers(1, 2**self.retries + 1)
                delay = slots_to_skip * self.config.slot_time
                self.scheduler.schedule(delay, self._sync_and_attempt, payload, dest_id, tx_power_mw)

class CsmaMac(BaseMac):
    """CSMA/CA with Freeze Mechanism and ARQ."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backoff_slots = 0
        self.cw = self.config.cw_min

    def send(self, payload: Any, dest_id: int, tx_power_mw: float):
        # print(f"DEBUG: Node {self.node_id} MAC.send called for payload {payload.payload}")
        self.retries = 0
        self.cw = self.config.cw_min
        self._start_new_backoff(payload, dest_id, tx_power_mw)

    def _start_new_backoff(self, payload: Any, dest_id: int, tx_power_mw: float):
        self.backoff_slots = self.rng.integers(0, self.cw + 1)
        self._backoff_step(payload, dest_id, tx_power_mw)

    def _backoff_step(self, payload: Any, dest_id: int, tx_power_mw: float):
        # Stop if we already got an ACK for this transmission (e.g. from previous attempt)
        if not self.waiting_for_ack and self.retries > 0:
            return

        if self.backoff_slots == 0:
            if not self.channel.is_busy(self.node_id):
                self._transmit(payload, dest_id, tx_power_mw)
                if self.waiting_for_ack:
                    self.scheduler.schedule(self.config.ack_timeout, self._check_ack, payload, dest_id, tx_power_mw)
            else:
                self._handle_collision_or_busy(payload, dest_id, tx_power_mw)
            return

        if not self.channel.is_busy(self.node_id):
            self.backoff_slots -= 1
        
        self.scheduler.schedule(self.config.slot_time, self._backoff_step, payload, dest_id, tx_power_mw)

    def _check_ack(self, payload: Any, dest_id: int, tx_power_mw: float):
        if self.waiting_for_ack:
            self._handle_collision_or_busy(payload, dest_id, tx_power_mw)

    def _handle_collision_or_busy(self, payload: Any, dest_id: int, tx_power_mw: float):
        if self.retries < self.config.max_retries:
            self.retries += 1
            self.cw = min((self.cw + 1) * 2 - 1, self.config.cw_max)
            self._start_new_backoff(payload, dest_id, tx_power_mw)
