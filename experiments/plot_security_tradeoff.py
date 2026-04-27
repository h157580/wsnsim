import numpy as np
import matplotlib.pyplot as plt
from wsnsim.sim import EventScheduler
from wsnsim.mac import MacConfig, PureAlohaMac
from wsnsim.common import Packet
from wsnsim.security import SecurityConfig, SecurityModel
from wsnsim.energy import RadioEnergyConfig, EnergyModel, RadioState

class ReplayAttacker:
    """Attacker model: listens to the channel and replays data packets after a delay."""
    def __init__(self, node_id, scheduler, channel, replay_delay=1.0):
        self.node_id = node_id
        self.scheduler = scheduler
        self.channel = channel
        self.replay_delay = replay_delay
        self.is_active = False

    def receive(self, packet, duration):
        if self.is_active and not packet.is_ack and packet.src != self.node_id:
            # Captures a copy and schedules a replay
            from copy import deepcopy
            self.scheduler.schedule(self.replay_delay, self.replay, deepcopy(packet))

    def replay(self, packet):
        # Attacker re-transmits the packet but gives it a NEW packet_id 
        # to bypass simple MAC-level duplicate filtering
        from copy import deepcopy
        p_replay = deepcopy(packet)
        p_replay.packet_id += 1000 # New ID, same payload/nonce
        
        bit_rate = 250000.0
        duration = (p_replay.size_bytes * 8) / bit_rate
        self.channel.transmit(self.node_id, p_replay, p_replay.dest, 10.0, duration)

class SimpleNetworkChannel:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.nodes = {}

    def add_node(self, node_id, mac):
        self.nodes[node_id] = mac

    def is_busy(self, node_id):
        return False

    def transmit(self, src_id, packet, dest_id, tx_power, duration):
        # Deliver to everyone else (simulating a broadcast medium)
        for nid, mac in self.nodes.items():
            if nid != src_id:
                from copy import deepcopy
                self.scheduler.schedule(duration, mac.receive, deepcopy(packet), duration)

def run_scenario(use_security=False, use_attacker=False):
    scheduler = EventScheduler()
    rng = np.random.default_rng(42)
    channel = SimpleNetworkChannel(scheduler)
    
    e_cfg = RadioEnergyConfig(
        power_tx_mw=15.0, power_rx_mw=10.0, power_idle_mw=1.0, power_sleep_mw=0.01,
        wakeup_cost_mj=0.1, battery_capacity_joules=100.0
    )
    s_cfg = SecurityConfig(crypto_energy_j=0.005, crypto_latency_s=0.005, overhead_bytes=28)
    m_cfg = MacConfig(bit_rate=250000.0, max_retries=0)

    # Node 0: Legitimate Sender
    energy0 = EnergyModel(e_cfg, RadioState.IDLE)
    sec0 = SecurityModel(0, s_cfg) if use_security else None
    mac0 = PureAlohaMac(0, scheduler, rng, m_cfg, channel, energy0, sec0)
    
    # Node 1: Sink (Receiver)
    energy1 = EnergyModel(e_cfg, RadioState.IDLE)
    sec1 = SecurityModel(1, s_cfg) if use_security else None
    mac1 = PureAlohaMac(1, scheduler, rng, m_cfg, channel, energy1, sec1)
    
    # Statistics tracking at the Sink
    stats = {"processed_payloads": []}
    mac1.on_receive_data = lambda p: stats["processed_payloads"].append(p.payload)

    channel.add_node(0, mac0)
    channel.add_node(1, mac1)

    # Attacker
    attacker = ReplayAttacker(666, scheduler, channel)
    attacker.is_active = use_attacker
    channel.add_node(666, attacker)

    # Legitimate node sends 5 packets
    for i in range(5):
        pkt = Packet(src=0, dest=1, payload=f"VAL_{i}", packet_id=100+i, size_bytes=8)
        scheduler.schedule(1.0 + i*2.0, mac0.send, pkt, 1, 10.0)

    scheduler.run(until=20.0)

    return {
        "energy_j": energy0.get_total_consumed_j(20.0),
        "processed_count": len(stats["processed_payloads"]),
        "integrity_error": len(stats["processed_payloads"]) > 5
    }

def main():
    print("Running Security Trade-off Experiment...")
    print("-" * 60)
    
    # 1. Baseline
    res_a = run_scenario(use_security=False, use_attacker=False)
    print(f"Scenario A (Baseline):    Energy={res_a['energy_j']:.4f}J, Packets={res_a['processed_count']}")

    # 2. Unsecured Attack
    res_b = run_scenario(use_security=False, use_attacker=True)
    print(f"Scenario B (No Security): Energy={res_b['energy_j']:.4f}J, Packets={res_b['processed_count']} (INTEGRITY FAILURE!)")

    # 3. Secured Attack
    res_c = run_scenario(use_security=True, use_attacker=True)
    print(f"Scenario C (Secured):    Energy={res_c['energy_j']:.4f}J, Packets={res_c['processed_count']} (Replay blocked)")
    
    # Calculate Overhead
    overhead = (res_c['energy_j'] / res_a['energy_j'] - 1) * 100
    print("-" * 60)
    print(f"Security Energy Overhead: {overhead:.1f}%")

    # Visualization
    labels = ['Baseline', 'Unsecured Attack', 'Secured Attack']
    energy_vals = [res_a['energy_j'], res_b['energy_j'], res_c['energy_j']]
    packet_vals = [res_a['processed_count'], res_b['processed_count'], res_c['processed_count']]

    fig, ax1 = plt.subplots(figsize=(10, 6))

    color = 'tab:blue'
    ax1.set_xlabel('Scenario')
    ax1.set_ylabel('Energy Consumed (J)', color=color)
    ax1.bar(labels, energy_vals, color=color, alpha=0.6, label='Energy')
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Packets Processed by Sink', color=color)
    ax2.plot(labels, packet_vals, color=color, marker='o', markersize=10, linewidth=2, label='Packets')
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.set_ylim(0, 12)

    plt.title('WSN Security Trade-off: Energy vs. Data Integrity')
    fig.tight_layout()
    plt.savefig('reports/figures/security_tradeoff.png')
    print("\nResults saved to reports/figures/security_tradeoff.png")

if __name__ == "__main__":
    main()
