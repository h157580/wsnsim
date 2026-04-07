import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List, Dict, Any

from wsnsim.sim import EventScheduler
from wsnsim.common import Position, Packet
from wsnsim.energy import EnergyModel, RadioEnergyConfig, RadioState
from wsnsim.mac import MacConfig, CsmaMac
from wsnsim.channel import ChannelModel, ChannelConfig

@dataclass
class SimNode:
    """A node container integrating all layers for the reliability experiment."""
    node_id: int
    scheduler: EventScheduler
    energy_model: EnergyModel
    mac: CsmaMac
    
    def __init__(self, node_id: int, scheduler: EventScheduler, rng: np.random.Generator, 
                 mac_config: MacConfig, energy_config: RadioEnergyConfig, channel: Any):
        self.node_id = node_id
        self.scheduler = scheduler
        self.energy_model = EnergyModel(energy_config, RadioState.IDLE, scheduler.current_time)
        self.mac = CsmaMac(node_id, scheduler, rng, mac_config, channel, self.energy_model)
        self.received_packets: List[Packet] = []
        self.mac.on_receive_data = self.receive_packet

    def receive_packet(self, packet: Packet):
        self.received_packets.append(packet)

class ReliabilityChannel:
    """A realistic channel that simulates collisions and delivers packets with duration."""
    def __init__(self, model: ChannelModel, positions: List[Position]):
        self.model = model
        self.positions = positions
        self.nodes: Dict[int, SimNode] = {}
        # node_id -> end_time of its current transmission
        self.active_transmissions: Dict[int, float] = {} 

    def add_node(self, node: SimNode):
        self.nodes[node.node_id] = node

    def is_busy(self, node_id: int) -> bool:
        now = self.nodes[node_id].scheduler.current_time
        # Clean up finished transmissions
        self.active_transmissions = {k: v for k, v in self.active_transmissions.items() if v > now}
        # Medium is busy if ANY other node is transmitting
        busy_nodes = [k for k in self.active_transmissions.keys() if k != node_id]
        return len(busy_nodes) > 0

    def transmit(self, src_id: int, packet: Packet, dest_id: int, tx_power_mw: float, duration: float):
        now = self.nodes[src_id].scheduler.current_time
        end_time = now + duration
        
        # Check for collision: if anyone else is already transmitting
        is_collision = len([k for k, v in self.active_transmissions.items() if v > now]) > 0
        
        self.active_transmissions[src_id] = end_time
        
        # Schedule delivery after 'duration' seconds
        self.nodes[src_id].scheduler.schedule(duration, self._deliver, src_id, dest_id, packet, duration, is_collision)

    def _deliver(self, src_id: int, dest_id: int, packet: Packet, duration: float, collided_at_start: bool):
        now = self.nodes[src_id].scheduler.current_time
        
        # Clean up active flag
        if src_id in self.active_transmissions and self.active_transmissions[src_id] <= now:
            del self.active_transmissions[src_id]

        if collided_at_start:
            return # Packet destroyed by initial collision

        # For every node, check PRR based on distance
        for other_id, other_node in self.nodes.items():
            if other_id == src_id:
                continue
            
            dist = self.positions[src_id].distance_to(self.positions[other_id])
            # Data power: 10mW, ACK power: 1mW (simplified)
            pwr = 1.0 if packet.is_ack else 10.0
            
            if self.model.is_received(pwr, dist):
                if dest_id == -1 or dest_id == other_id:
                    # Success! Deliver to MAC
                    pkt_copy = Packet(
                        src=packet.src,
                        dest=packet.dest,
                        payload=packet.payload,
                        packet_id=packet.packet_id,
                        is_ack=packet.is_ack
                    )
                    other_node.mac.receive(pkt_copy, duration)

def run_experiment(max_retries: int, cw_min: int = 7):
    scheduler = EventScheduler()
    rng = np.random.default_rng(42) # Consistent seed for comparison
    
    chan_model = ChannelModel(ChannelConfig(sigma=5.0), rng) # High shadowing to force retries
    
    # Generic Radio Energy Config (mW)
    energy_cfg = RadioEnergyConfig(
        power_tx_mw=45.0,    # TX at 10mW output uses ~45mW total
        power_rx_mw=20.0,    # RX listening
        power_idle_mw=20.0,   # Idle (same as RX in many chips)
        power_sleep_mw=0.01,
        wakeup_cost_mj=0.05,
        battery_capacity_joules=1000.0
    )
    
    mac_cfg = MacConfig(
        max_retries=max_retries, 
        cw_min=cw_min, 
        cw_max=127,
        ack_timeout=0.04  # Enough for DATA + SIFS + ACK
    )
    
    # 20 Nodes randomly around a Sink (Node 0) in 60m radius
    num_sensors = 20
    positions = [Position(0, 0)]
    for i in range(num_sensors):
        r = rng.uniform(20, 70)
        theta = rng.uniform(0, 2*np.pi)
        positions.append(Position(r * np.cos(theta), r * np.sin(theta)))
        
    channel = ReliabilityChannel(chan_model, positions)
    nodes = []
    for i in range(num_sensors + 1):
        n = SimNode(i, scheduler, rng, mac_cfg, energy_cfg, channel)
        channel.add_node(n)
        nodes.append(n)
        
    # Each sensor sends 5 packets to sink over 10 seconds
    total_generated = 0
    for i in range(1, num_sensors + 1):
        for p in range(5):
            tx_time = rng.uniform(0.1, 10.0)
            pkt = Packet(src=i, dest=0, payload=f"data-{i}-{p}", packet_id=i*100 + p)
            scheduler.schedule(tx_time, nodes[i].mac.send, pkt, 0, 10.0)
            total_generated += 1
            
    scheduler.run(until=25.0)
    
    # Collect results
    received_at_sink = len(nodes[0].received_packets)
    pdr = received_at_sink / total_generated if total_generated > 0 else 0
    
    # Calculate extra energy (above background idle)
    total_j = sum(n.energy_model.get_total_consumed_j(scheduler.current_time) for n in nodes)
    idle_j = (num_sensors + 1) * (energy_cfg.power_idle_mw * scheduler.current_time / 1000.0)
    extra_j = max(0, total_j - idle_j)
    
    return pdr, extra_j

if __name__ == "__main__":
    retries = [0, 1, 2, 3, 5, 8, 12]
    pdr_results = []
    energy_results = []
    
    print(f"{'Retries':<8} | {'PDR (%)':<10} | {'Extra Energy (J)':<15}")
    print("-" * 40)
    
    for r in retries:
        p, e = run_experiment(r)
        pdr_results.append(p * 100)
        energy_results.append(e)
        print(f"{r:<8} | {p*100:>10.2f} | {e:>15.4f}")
        
    # Plotting
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # PDR Curve
    color = 'tab:blue'
    ax1.set_xlabel('Max Retry Limit')
    ax1.set_ylabel('Packet Delivery Ratio (PDR %)', color=color)
    ax1.plot(retries, pdr_results, color=color, marker='o', linewidth=2, label='PDR')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, linestyle='--', alpha=0.6)
    
    # Energy Curve
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Additional Energy Consumed (J)', color=color)
    ax2.plot(retries, energy_results, color=color, marker='s', linewidth=2, label='Energy Cost')
    ax2.tick_params(axis='y', labelcolor=color)
    
    plt.title('The Cost of Reliability: PDR vs. Energy (CSMA/CA ARQ)')
    fig.tight_layout()
    plt.savefig('reports/figures/pdr_vs_energy_retry.png')
    print("\nResult plot saved to reports/figures/pdr_vs_energy_retry.png")
    plt.show()
