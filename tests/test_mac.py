import pytest
import numpy as np
from typing import Any, Set, Dict
from wsnsim.sim import EventScheduler
from wsnsim.mac import MacConfig, PureAlohaMac, SlottedAlohaMac, CsmaMac

class DeterministicChannel:
    """A channel for testing that tracks overlaps and can trigger ACKs."""
    def __init__(self, scheduler: EventScheduler):
        self.scheduler = scheduler
        self.active_transmitters: Set[int] = set()
        self.nodes: Dict[int, Any] = {}
        # Track (node_id, start_time, end_time)
        self.history = []
        self.collisions = set()

    def add_node(self, node_id: int, mac_layer: Any):
        self.nodes[node_id] = mac_layer

    def is_busy(self, node_id: int) -> bool:
        # In this simple test channel, everyone hears everyone
        return len(self.active_transmitters) > 0

    def transmit(self, node_id: int, payload: Any, dest_id: int, tx_power_mw: float, duration: float):
        start_time = self.scheduler.current_time
        end_time = start_time + duration
        
        # If someone else is already transmitting, it's a collision for everyone active
        if self.active_transmitters:
            self.collisions.add(node_id)
            for other_id in self.active_transmitters:
                self.collisions.add(other_id)
        
        self.active_transmitters.add(node_id)
        self.history.append((node_id, start_time, end_time))
        
        # Schedule the end of transmission
        self.scheduler.schedule(duration, self._end_transmission, node_id, dest_id)

    def _end_transmission(self, node_id: int, dest_id: int):
        self.active_transmitters.remove(node_id)
        
        # If this specific transmission didn't suffer a collision, deliver ACK
        # Note: In real life, Node B would send an ACK packet. 
        # Here we simulate the MAC receiving a successful ACK.
        if node_id not in self.collisions:
            # Simulate ACK delay (half slot)
            self.scheduler.schedule(0.001, self.nodes[node_id].on_ack)
        else:
            # Reset collision flag for this node for future transmissions
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
        ack_timeout=0.02
    )

def test_pure_aloha_collision(scheduler, mac_config):
    """Verify that Pure ALOHA nodes collide if they overlap and then backoff.
    
    Seeds 42 and 43 are chosen to ensure overlapping transmissions and 
    distinct exponential backoff paths.
    """
    rng0 = np.random.default_rng(42)
    rng1 = np.random.default_rng(43)
    channel = DeterministicChannel(scheduler)
    
    mac0 = PureAlohaMac(0, scheduler, rng0, mac_config, channel)
    mac1 = PureAlohaMac(1, scheduler, rng1, mac_config, channel)
    channel.add_node(0, mac0)
    channel.add_node(1, mac1)

    # Node 0 starts at T=0
    scheduler.schedule(0, mac0.send, "pkt0", 1, 1.0)
    # Node 1 starts at T=0.002 (overlaps with node 0's 0.005 duration)
    scheduler.schedule(0.002, mac1.send, "pkt1", 0, 1.0)

    # Run enough for first attempt and backoff
    scheduler.run(until=0.1)

    # Check that both nodes had to retry
    assert mac0.retries > 0
    assert mac1.retries > 0
    # Verify they both transmitted at least twice (original + retry)
    node0_txs = [h for h in channel.history if h[0] == 0]
    node1_txs = [h for h in channel.history if h[0] == 1]
    assert len(node0_txs) >= 2
    assert len(node1_txs) >= 2

def test_slotted_aloha_collision(scheduler, mac_config):
    """Verify that Slotted ALOHA nodes sync to slot and collide.
    
    Seeds 42 and 43 are used to verify that synchronization to the 
    slot boundary causes collision regardless of independent backoff logic.
    """
    rng0 = np.random.default_rng(42)
    rng1 = np.random.default_rng(43)
    channel = DeterministicChannel(scheduler)
    
    mac0 = SlottedAlohaMac(0, scheduler, rng0, mac_config, channel)
    mac1 = SlottedAlohaMac(1, scheduler, rng1, mac_config, channel)
    channel.add_node(0, mac0)
    channel.add_node(1, mac1)

    # Node 0 wants to send at T=0.001 -> Syncs to T=0.01
    scheduler.schedule(0.001, mac0.send, "pkt0", 1, 1.0)
    # Node 1 wants to send at T=0.008 -> Syncs to T=0.01
    scheduler.schedule(0.008, mac1.send, "pkt1", 0, 1.0)

    scheduler.run(until=0.015)

    # Both should have started exactly at T=0.01
    txs_at_01 = [h for h in channel.history if h[1] == pytest.approx(0.01)]
    assert len(txs_at_01) == 2

def test_csma_avoidance(scheduler, mac_config):
    """Verify CSMA avoidance: Node 1 should wait if Node 0 is transmitting.
    
    Seed 42 is used for both nodes to ensure Node 1 picks a 
    predictable backoff window (12 slots) that allows us to 
    verify the 'Freeze' logic during Node 0's transmission.
    """
    # Fixed seed to make backoff deterministic for node 1
    # cw_min=7 means backoff_slots will be in [0, 7]
    rng0 = np.random.default_rng(42)
    rng1 = np.random.default_rng(42) # Use same seed to check specific backoff
    channel = DeterministicChannel(scheduler)
    
    mac0 = CsmaMac(0, scheduler, rng0, mac_config, channel)
    mac1 = CsmaMac(1, scheduler, rng1, mac_config, channel)
    channel.add_node(0, mac0)
    channel.add_node(1, mac1)

    # Node 0 starts a long transmission at T=0
    # We'll manually set its duration longer for this test or just start it first
    scheduler.schedule(0, mac0.send, "pkt0", 1, 1.0)
    
    # Node 1 tries to send at T=0.002
    # It should see channel busy and freeze/wait
    scheduler.schedule(0.002, mac1.send, "pkt1", 0, 1.0)

    scheduler.run(until=0.2)

    # History should show Node 0 started first
    assert channel.history[0][0] == 0
    assert channel.history[0][1] == 0.0
    
    # Node 1 should have started ONLY after Node 0 finished (T=0.005)
    node1_tx = next(h for h in channel.history if h[0] == 1)
    assert node1_tx[1] >= 0.005
