import pytest
import numpy as np
from wsnsim.sim import EventScheduler
from wsnsim.mac import MacConfig, PureAlohaMac
from wsnsim.common import Packet
from wsnsim.security import SecurityConfig, SecurityModel
from wsnsim.energy import RadioEnergyConfig, EnergyModel, RadioState

@pytest.fixture
def energy_config():
    return RadioEnergyConfig(
        power_tx_mw=10.0, power_rx_mw=5.0, power_idle_mw=1.0, power_sleep_mw=0.01,
        wakeup_cost_mj=0.1, battery_capacity_joules=100.0
    )

@pytest.fixture
def sec_config():
    return SecurityConfig(crypto_energy_j=0.01, crypto_latency_s=0.1, overhead_bytes=28)

def test_security_logic(sec_config):
    """Verify basic security logic (signing and verification) without network."""
    sec = SecurityModel(node_id=1, config=sec_config)
    pkt = Packet(src=0, dest=1, payload="Data", packet_id=1, size_bytes=8)
    
    # 1. Signing
    sec.sign_packet(pkt)
    assert pkt.nonce == 1
    assert pkt.size_bytes == 36 # 8 + 28
    
    # 2. Verification
    assert sec.verify_packet(pkt) is True
    
    # 3. Replay
    assert sec.verify_packet(pkt) is False # Same nonce should be rejected
    
    # 4. Fresh packet
    pkt2 = Packet(src=0, dest=1, payload="Data2", packet_id=2, size_bytes=8, nonce=2)
    assert sec.verify_packet(pkt2) is True

def test_overhead_integration(energy_config, sec_config):
    """Verify energy and latency overhead integrated via the MAC layer."""
    scheduler = EventScheduler()
    energy = EnergyModel(energy_config, RadioState.IDLE)
    sec = SecurityModel(0, sec_config)
    
    class MockChannel:
        def __init__(self): self.tx_calls = []
        def transmit(self, *args): self.tx_calls.append(scheduler.current_time)
        def is_busy(self, node_id): return False

    channel = MockChannel()
    mac = PureAlohaMac(0, scheduler, np.random.default_rng(42), 
                       MacConfig(bit_rate=250000), channel, energy, sec)
    
    pkt = Packet(src=0, dest=0, payload="Data", packet_id=1, size_bytes=8)
    scheduler.schedule(1.0, mac.send, pkt, 1, 1.0)
    scheduler.run(until=1.2)
    
    # 1. Latency overhead: 1.0 + 0.1 (crypto_latency_s) = 1.1
    assert len(channel.tx_calls) == 1
    assert channel.tx_calls[0] == pytest.approx(1.1)
    
    # 2. Energy overhead: crypto_energy_j (0.01 J) should be consumed
    assert energy.metrics.total_energy_consumed_j >= 0.01

def test_multi_source_out_of_order_replay(sec_config):
    """Verify complex replay protection with multiple sources and out-of-order packets."""
    receiver_id = 1
    receiver_sec = SecurityModel(node_id=receiver_id, config=sec_config)
    executed_payloads = []
    
    def process_incoming(pkt):
        if receiver_sec.verify_packet(pkt):
            executed_payloads.append(pkt.payload)
            return True
        return False

    # 1. Node 0 sends nonce=1 -> Accepted
    assert process_incoming(Packet(src=0, dest=receiver_id, payload="A1", packet_id=101, nonce=1)) is True
    
    # 2. Node 2 sends nonce=1 -> Accepted (different source)
    assert process_incoming(Packet(src=2, dest=receiver_id, payload="B1", packet_id=201, nonce=1)) is True
    
    # 3. Node 0 sends nonce=3 (gap) -> Accepted
    assert process_incoming(Packet(src=0, dest=receiver_id, payload="A3", packet_id=103, nonce=3)) is True
    
    # 4. REPLAY: Node 0 nonce=1 -> REJECTED
    assert process_incoming(Packet(src=0, dest=receiver_id, payload="A1", packet_id=101, nonce=1)) is False
    
    # 5. STALE: Node 0 nonce=2 (delayed/out-of-order) -> REJECTED
    assert process_incoming(Packet(src=0, dest=receiver_id, payload="A2", packet_id=102, nonce=2)) is False
    
    # 6. Node 2 sends nonce=2 -> Accepted
    assert process_incoming(Packet(src=2, dest=receiver_id, payload="B2", packet_id=202, nonce=2)) is True

    assert executed_payloads == ["A1", "B1", "A3", "B2"]
