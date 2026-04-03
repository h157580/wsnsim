import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any
import os

from wsnsim.sim import EventScheduler
from wsnsim.common import Position, Packet
from wsnsim.topology import TopologyConfig, GridTopology
from wsnsim.channel import ChannelConfig, ChannelModel
from wsnsim.mac import MacConfig, CsmaMac
from wsnsim.routing import FloodingRouting, TreeRouting
from wsnsim.energy import RadioEnergyConfig, EnergyModel, RadioState

# Reuse the SimNode and SimpleGlobalChannel logic from the previous experiment
# (In a real project, these would be in a 'wsnsim.experiment_utils' module)

class SimNode:
    def __init__(self, node_id, scheduler, rng, mac_config, energy_config, channel, strategy, positions, tx_power_mw):
        self.node_id = node_id
        self.scheduler = scheduler
        self.positions = positions
        self.tx_power_mw = tx_power_mw
        self.energy = EnergyModel(energy_config, RadioState.IDLE, scheduler.current_time)
        self.mac = CsmaMac(node_id, scheduler, rng, mac_config, channel, self.energy)
        self.mac.on_receive = self.receive_packet
        self.routing = FloodingRouting(node_id) if strategy == "flooding" else TreeRouting(node_id)
        self.sent_count = 0
        self.received_count = 0
        self.total_latency = 0.0
        self.received_packet_ids = set()

    def send_data(self, dest_id, payload):
        packet = Packet(src=self.node_id, dest=dest_id, payload={"ts": self.scheduler.current_time}, 
                        packet_id=self.sent_count, ttl=32)
        self.sent_count += 1
        if isinstance(self.routing, FloodingRouting): packet.next_hop = -1
        else: packet.next_hop = self.routing.parent_id if self.routing.parent_id is not None else -1
        self.mac.send(packet, packet.next_hop, tx_power_mw=self.tx_power_mw)

    def receive_packet(self, packet):
        if packet.dest == self.node_id:
            key = (packet.src, packet.packet_id)
            if key not in self.received_packet_ids:
                self.received_packet_ids.add(key)
                self.received_count += 1
                self.total_latency += (self.scheduler.current_time - packet.payload["ts"])
            return
        next_hop = self.routing.forward(packet)
        if next_hop is not None: self.mac.send(packet, packet.next_hop, tx_power_mw=self.tx_power_mw)

class SimpleGlobalChannel:
    def __init__(self, model, positions):
        self.model, self.positions = model, positions
        self.nodes = {}
        self.active_transmissions = {}

    def add_node(self, node): self.nodes[node.node_id] = node
    def is_busy(self, node_id):
        now = self.nodes[node_id].scheduler.current_time
        self.active_transmissions = {k: v for k, v in self.active_transmissions.items() if v > now}
        return len(self.active_transmissions) > 0

    def transmit(self, src_id, packet, dest_id, tx_power_mw, duration):
        now = self.nodes[src_id].scheduler.current_time
        self.active_transmissions[src_id] = now + duration
        for other_id, other_node in self.nodes.items():
            if other_id == src_id: continue
            dist = self.positions[src_id].distance_to(self.positions[other_id])
            if self.model.is_received(tx_power_mw, dist):
                if dest_id == -1 or dest_id == other_id:
                    pkt_copy = Packet(packet.src, packet.dest, packet.payload, packet.packet_id, 
                                      packet.ttl, packet.next_hop, packet.hop_count)
                    other_node.scheduler.schedule(duration, other_node.mac.on_receive, pkt_copy)
                    if dest_id == other_id:
                        other_node.scheduler.schedule(duration + 0.002, self.nodes[src_id].mac.on_ack)

def run_sim(strategy: str, area_size: float, seed: int):
    rng = np.random.default_rng(seed)
    scheduler = EventScheduler()
    topo_cfg = TopologyConfig(area_width=area_size, area_height=area_size, num_nodes=25)
    chan_cfg = ChannelConfig(packet_length=128)
    mac_cfg = MacConfig()
    energy_cfg = RadioEnergyConfig(52.2, 56.4, 56.4, 0.06, 0.0, 1000.0)
    
    topo = GridTopology(topo_cfg, rng)
    positions = topo.generate()
    channel = SimpleGlobalChannel(ChannelModel(chan_cfg, rng), positions)
    
    nodes = {}
    for i in range(topo_cfg.num_nodes):
        nodes[i] = SimNode(i, scheduler, rng, mac_cfg, energy_cfg, channel, strategy, positions, 0.5)
        channel.add_node(nodes[i])
    
    if strategy == "tree":
        spacing = area_size / (np.sqrt(topo_cfg.num_nodes) + 1)
        graph = topo.to_graph(positions, range_m=spacing * 1.6)
        for i in range(topo_cfg.num_nodes): nodes[i].routing.update_from_graph(graph, sink_id=0)

    for i in range(1, topo_cfg.num_nodes):
        scheduler.schedule(rng.uniform(0.1, 2.0), nodes[i].send_data, 0, "payload")

    scheduler.run(until=20.0)
    
    for n in nodes.values(): n.energy.update_state(RadioState.SLEEP, scheduler.current_time)
    
    total_sent = sum(n.sent_count for i, n in nodes.items() if i != 0)
    total_received = nodes[0].received_count
    total_energy_j = sum(n.energy.metrics.total_energy_consumed_j for n in nodes.values())
    
    # Energy per bit calculation
    total_bits = total_received * chan_cfg.packet_length
    epb = (total_energy_j / total_bits) if total_bits > 0 else float('nan')
    
    return {
        "pdr": (total_received / total_sent * 100) if total_sent > 0 else 0,
        "lat": (nodes[0].total_latency / total_received) if total_received > 0 else 0,
        "epb": epb
    }

def main():
    spacings = np.linspace(100, 400, 7)
    strategies = ["flooding", "tree"]
    results = {s: {"pdr": [], "lat": [], "epb": []} for s in strategies}
    
    print("Starting sweep over area size...")
    for area in spacings:
        print(f"  Testing area {area:.0f}x{area:.0f}m...")
        for s in strategies:
            res = run_sim(s, area, 42)
            results[s]["pdr"].append(res["pdr"])
            results[s]["lat"].append(res["lat"])
            results[s]["epb"].append(res["epb"])

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))
    
    for s in strategies:
        ax1.plot(spacings, results[s]["pdr"], marker='o', label=s.capitalize())
        ax2.plot(spacings, results[s]["lat"], marker='s', label=s.capitalize())
        ax3.plot(spacings, results[s]["epb"], marker='^', label=s.capitalize())

    ax1.set_title("Packet Delivery Ratio (PDR)")
    ax1.set_xlabel("Area Size (m)"); ax1.set_ylabel("PDR (%)"); ax1.grid(True)
    
    ax2.set_title("Average Latency")
    ax2.set_xlabel("Area Size (m)"); ax2.set_ylabel("Latency (s)"); ax2.grid(True)
    
    ax3.set_title("Energy per Bit (EPB)")
    ax3.set_xlabel("Area Size (m)"); ax3.set_ylabel("Energy (J/bit)"); ax3.grid(True)
    ax3.set_yscale('log')
    
    plt.legend()
    os.makedirs("reports/figures", exist_ok=True)
    plt.savefig("reports/figures/routing_comparison_sweep.png")
    print("\nGraphs saved to reports/figures/routing_comparison_sweep.png")

if __name__ == "__main__":
    main()
