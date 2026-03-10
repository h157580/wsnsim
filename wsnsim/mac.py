from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional, Callable
import numpy as np

if TYPE_CHECKING:
    from numpy.random import Generator
    from .sim import EventScheduler
    from .energy import EnergyModel
    from .energy import RadioState


@dataclass(frozen=True)
class MacConfig:
    """MAC parameters. All time units in seconds.
    
    To ensure Slotted ALOHA efficiency, tx_duration should be <= slot_time.
    """
    slot_time: float = 0.005       # 5ms slot
    cw_min: int = 7                # Binary backoff initial window (slots)
    cw_max: int = 1023             # Binary backoff max window (slots)
    max_retries: int = 5           # Max retransmission attempts
    tx_duration: float = 0.005     # Matches slot_time for Slotted ALOHA
    ack_timeout: float = 0.015     # Time to wait for an ACK before backoff

class BaseMac:
    """Common state and energy tracking for MAC protocols."""
    def __init__(self, node_id: int, scheduler: EventScheduler, rng: Generator, 
                 config: MacConfig, channel: Any, energy_model: Optional[EnergyModel] = None):
        self.node_id = node_id
        self.scheduler = scheduler
        self.rng = rng
        self.config = config
        self.channel = channel
        self.energy_model = energy_model
        
        self.on_receive: Optional[Callable[[Any], None]] = None
        self.retries = 0
        self.waiting_for_ack = False

    def _update_radio(self, state_name: str):
        if self.energy_model:
            self.energy_model.update_state(RadioState[state_name], self.scheduler.current_time)

    def on_ack(self):
        """Called by the upper layer or channel when a valid ACK is received."""
        self.waiting_for_ack = False

    def _transmit(self, payload: Any, dest_id: int, tx_power_mw: float):
        """Low-level transmission call."""
        self._update_radio("TX")
        self.waiting_for_ack = True
        self.channel.transmit(self.node_id, payload, dest_id, tx_power_mw, self.config.tx_duration)
        self.scheduler.schedule(self.config.tx_duration, self._update_radio, "IDLE")

class PureAlohaMac(BaseMac):
    """Pure ALOHA: Send immediately, backoff on ACK timeout."""
    def send(self, payload: Any, dest_id: int, tx_power_mw: float):
        self.retries = 0
        self._attempt_send(payload, dest_id, tx_power_mw)

    def _attempt_send(self, payload: Any, dest_id: int, tx_power_mw: float):
        self._transmit(payload, dest_id, tx_power_mw)
        # Collision detection via ACK timeout
        self.scheduler.schedule(self.config.ack_timeout, self._check_ack, payload, dest_id, tx_power_mw)

    def _check_ack(self, payload: Any, dest_id: int, tx_power_mw: float):
        if self.waiting_for_ack:
            if self.retries < self.config.max_retries:
                self.retries += 1
                # Standard ALOHA backoff: random delay
                delay = self.rng.integers(1, 2**self.retries + 1) * self.config.slot_time
                self.scheduler.schedule(delay, self._attempt_send, payload, dest_id, tx_power_mw)
            else:
                pass # Max retries reached, packet dropped

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
        self.scheduler.schedule(self.config.ack_timeout, self._check_ack, payload, dest_id, tx_power_mw)

    def _check_ack(self, payload: Any, dest_id: int, tx_power_mw: float):
        if self.waiting_for_ack:
            if self.retries < self.config.max_retries:
                self.retries += 1
                # Backoff for N slots, then re-sync
                slots_to_skip = self.rng.integers(1, 2**self.retries + 1)
                delay = slots_to_skip * self.config.slot_time
                self.scheduler.schedule(delay, self._sync_and_attempt, payload, dest_id, tx_power_mw)

class CsmaMac(BaseMac):
    """CSMA/CA with Freeze Mechanism: Backoff counter pauses when channel is busy."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backoff_slots = 0
        self.cw = self.config.cw_min

    def send(self, payload: Any, dest_id: int, tx_power_mw: float):
        self.retries = 0
        self.cw = self.config.cw_min
        self._start_new_backoff(payload, dest_id, tx_power_mw)

    def _start_new_backoff(self, payload: Any, dest_id: int, tx_power_mw: float):
        self.backoff_slots = self.rng.integers(0, self.cw + 1)
        self._backoff_step(payload, dest_id, tx_power_mw)

    def _backoff_step(self, payload: Any, dest_id: int, tx_power_mw: float):
        """The core CSMA/CA loop with Freeze logic."""
        if self.backoff_slots == 0:
            # Counter zero: check channel one last time before sending
            if not self.channel.is_busy(self.node_id):
                self._transmit(payload, dest_id, tx_power_mw)
                # Wait for ACK
                self.scheduler.schedule(self.config.ack_timeout, self._check_ack, payload, dest_id, tx_power_mw)
            else:
                # CCA failed: handle as a collision/busy channel (retry with backoff)
                self._handle_collision_or_busy(payload, dest_id, tx_power_mw)
            return

        if not self.channel.is_busy(self.node_id):
            # IDLE: Decrement counter and wait for next slot
            self.backoff_slots -= 1
            self.scheduler.schedule(self.config.slot_time, self._backoff_step, payload, dest_id, tx_power_mw)
        else:
            # BUSY: FREEZE the counter. Just wait one slot and check again.
            self.scheduler.schedule(self.config.slot_time, self._backoff_step, payload, dest_id, tx_power_mw)

    def _check_ack(self, payload: Any, dest_id: int, tx_power_mw: float):
        """Verify if an ACK was received; if not, trigger retransmission."""
        if self.waiting_for_ack:
            self.waiting_for_ack = False
            self._handle_collision_or_busy(payload, dest_id, tx_power_mw)

    def _handle_collision_or_busy(self, payload: Any, dest_id: int, tx_power_mw: float):
        if self.retries < self.config.max_retries:
            self.retries += 1
            # Exponentially increase contention window
            self.cw = min((self.cw + 1) * 2 - 1, self.config.cw_max)
            self._start_new_backoff(payload, dest_id, tx_power_mw)
        else:
            pass # Packet dropped
