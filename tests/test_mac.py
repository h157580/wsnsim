import pytest
import numpy as np
from typing import Any, Set, Dict
from wsnsim.sim import EventScheduler
from wsnsim.mac import MacConfig, PureAlohaMac, SlottedAlohaMac, CsmaMac
from wsnsim.common import Packet

class DeterministicChannel:
    """A channel for testing that tracks overlaps and delivers packets via mac.receive()."""
    def __init__(self, scheduler: EventScheduler):
        self.scheduler = scheduler
        self.active_transmitters: Set[int] = set()
        self.nodes: Dict[int, Any] = {}
        # Track (node_id, start_time, end_time, packet)
        self.history = []
        self.collisions = set()

    def add_node(self, node_id: int, mac_layer: Any):
        self.nodes[node_id] = mac_layer

    def is_busy(self, node_id: int) -> bool:
        return len(self.active_transmitters) > 0

    def transmit(self, node_id: int, packet: Packet, dest_id: int, tx_power_mw: float, duration: float):
        start_time = self.scheduler.current_time
        end_time = start_time + duration
        
        # Collision detection
        is_collision = False
        if self.active_transmitters:
            is_collision = True
            self.collisions.add(node_id)
            for other_id in self.active_transmitters:
                self.collisions.add(other_id)
        
        self.active_transmitters.add(node_id)
        self.history.append((node_id, start_time, end_time, packet))
        
        # Schedule delivery at the end of transmission duration
        # Matches Mac layer expectation: calls mac.receive with duration
        self.scheduler.schedule(duration, self._end_transmission, node_id, dest_id, packet, duration, is_collision)

    def _end_transmission(self, node_id: int, dest_id: int, packet: Packet, duration: float, was_collision_at_start: bool):
        if node_id in self.active_transmitters:
            self.active_transmitters.remove(node_id)
        
        # Final collision check: if someone else started while we were transmitting
        in_collision = node_id in self.collisions or was_collision_at_start
        
        if not in_collision:
            # Deliver to destination (unicast or broadcast)
            for target_id, mac in self.nodes.items():
                if target_id == node_id:
                    continue
                if dest_id == -1 or dest_id == target_id:
                    # Deliver a copy of the packet
                    pkt_copy = Packet(
                        src=packet.src,
                        dest=packet.dest,
                        payload=packet.payload,
                        packet_id=packet.packet_id,
                        ttl=packet.ttl,
                        next_hop=packet.next_hop,
                        is_ack=packet.is_ack,
                        nonce=packet.nonce,
                        size_bytes=packet.size_bytes
                    )
                    mac.receive(pkt_copy, duration)
        
        # Clean up collision flag for this node
        if node_id in self.collisions:
            self.collisions.remove(node_id)

@pytest.fixture
def scheduler():
    return EventScheduler()

@pytest.fixture
def mac_config():
    return MacConfig(
        slot_time=0.01,
        cw_min=7,
        cw_max=31,
        max_retries=3,
        tx_duration=0.005,
        ack_timeout=0.03, # Increased for real ACK turnaround
        bit_rate=250000.0
    )

def test_pure_aloha_collision(scheduler, mac_config):
    """Verify Pure ALOHA collision and ARQ retry."""
    rng0 = np.random.default_rng(42)
    rng1 = np.random.default_rng(43)
    channel = DeterministicChannel(scheduler)
    
    mac0 = PureAlohaMac(0, scheduler, rng0, mac_config, channel)
    mac1 = PureAlohaMac(1, scheduler, rng1, mac_config, channel)
    channel.add_node(0, mac0)
    channel.add_node(1, mac1)

    p0 = Packet(src=0, dest=1, payload="data0", packet_id=100)
    p1 = Packet(src=1, dest=0, payload="data1", packet_id=200)

    # Node 0 starts at T=0
    scheduler.schedule(0, mac0.send, p0, 1, 1.0)
    # Node 1 starts at T=0.0001 (overlaps with 0.000256 duration)
    scheduler.schedule(0.0001, mac1.send, p1, 0, 1.0)

    scheduler.run(until=0.2)

    # Both should have retried due to collision
    assert mac0.retries > 0
    assert mac1.retries > 0
    
    # Check history for retransmissions (more than 2 TXs total)
    assert len(channel.history) >= 4 

def test_csma_ack_success(scheduler, mac_config):
    """Verify that CSMA successfully receives an ACK and stops retrying."""
    rng0 = np.random.default_rng(42)
    rng1 = np.random.default_rng(43)
    channel = DeterministicChannel(scheduler)
    
    mac0 = CsmaMac(0, scheduler, rng0, mac_config, channel)
    mac1 = CsmaMac(1, scheduler, rng1, mac_config, channel)
    channel.add_node(0, mac0)
    channel.add_node(1, mac1)

    p0 = Packet(src=0, dest=1, payload="data0", packet_id=100)
    
    # Node 0 sends at T=0
    scheduler.schedule(0, mac0.send, p0, 1, 1.0)
    
    scheduler.run(until=0.1)

    # Node 0 should have 0 retries because it received an ACK
    assert mac0.retries == 0
    # Channel should show: 1 DATA packet and 1 ACK packet
    assert len(channel.history) == 2
    assert channel.history[0][3].is_ack is False
    assert channel.history[1][3].is_ack is True

def test_duplicate_filtering(scheduler, mac_config):
    """Verify that the MAC layer filters out duplicate packets but still ACKs them."""
    rng0 = np.random.default_rng(42)
    rng1 = np.random.default_rng(43)
    channel = DeterministicChannel(scheduler)
    
    mac0 = CsmaMac(0, scheduler, rng0, mac_config, channel)
    mac1 = CsmaMac(1, scheduler, rng1, mac_config, channel)
    channel.add_node(0, mac0)
    channel.add_node(1, mac1)

    received_payloads = []
    mac1.on_receive_data = lambda p: received_payloads.append(p.payload)

    p0 = Packet(src=0, dest=1, payload="data0", packet_id=100)

    # We manually trigger delivery twice (simulating an lost ACK scenario)
    mac1.receive(p0, 0.005)
    mac1.receive(p0, 0.005)

    # Upper layer should only see it ONCE
    assert len(received_payloads) == 1
    
    # But channel should have 2 ACK transmissions scheduled
    scheduler.run(until=0.1)
    # Check history for ACKs (filter is_ack=True)
    acks = [h for h in channel.history if h[3].is_ack]
    assert len(acks) == 2
