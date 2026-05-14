import numpy as np
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from wsnsim.sim import EventScheduler
from wsnsim.common import Position, Packet
from wsnsim.topology import TopologyConfig, GridTopology
from wsnsim.channel import ChannelConfig, ChannelModel
from wsnsim.mac import MacConfig, CsmaMac
from wsnsim.routing import FloodingRouting, TreeRouting, BaseRouting
from wsnsim.energy import RadioEnergyConfig, EnergyModel, RadioState

@dataclass
class SimStats:
    sent_count: int = 0
    received_count: int = 0
    total_latency: float = 0.0
    total_energy_j: float = 0.0
    hop_counts: List[int] = None

    def __post_init__(self):
        if self.hop_counts is None:
            self.hop_counts = []

class SimNode:
    def __init__(
        self, 
        node_id: int, 
        scheduler: EventScheduler, 
        rng: np.random.Generator,
        mac_config: MacConfig,
        energy_config: RadioEnergyConfig,
        channel: Any,
        routing_strategy: str,
        positions: List[Position],
        tx_power_mw: float = 1.0
    ):
        self.node_id = node_id
        self.scheduler = scheduler
        self.positions = positions
        self.tx_power_mw = tx_power_mw
        
        # 1. Energy Model
        self.energy = EnergyModel(energy_config, RadioState.IDLE, scheduler.current_time)
        
        # 2. MAC Layer
        self.mac = CsmaMac(node_id, scheduler, rng, mac_config, channel, self.energy)
        self.mac.on_receive_data = self.receive_packet
        
        # 3. Routing Layer
        if routing_strategy == "flooding":
            self.routing = FloodingRouting(node_id)
        elif routing_strategy == "tree":
            self.routing = TreeRouting(node_id)
        else:
            raise ValueError(f"Unknown routing: {routing_strategy}")
            
        self.stats = SimStats()
        self.received_packet_ids: Set[tuple[int, int]] = set()

    def send_data(self, dest_id: int, payload: Any):
        """Application layer send."""
        packet_id = self.stats.sent_count
        packet = Packet(
            src=self.node_id,
            dest=dest_id,
            payload={"timestamp": self.scheduler.current_time, "data": payload},
            packet_id=packet_id,
            ttl=32
        )
        self.stats.sent_count += 1
        
        # Initial routing decision
        if isinstance(self.routing, FloodingRouting):
            packet.next_hop = -1
        elif isinstance(self.routing, TreeRouting):
            packet.next_hop = self.routing.parent_id if self.routing.parent_id is not None else -1

        self._forward_to_mac(packet)

    def receive_packet(self, packet: Packet):
        """Callback from MAC layer."""
        if packet.dest == self.node_id:
            key = (packet.src, packet.packet_id)
            if key in self.received_packet_ids:
                return # Ignore duplicates for stats

            # Reached destination!
            self.received_packet_ids.add(key)
            latency = self.scheduler.current_time - packet.payload["timestamp"]
            self.stats.received_count += 1
            self.stats.total_latency += latency
            self.stats.hop_counts.append(packet.hop_count)
            return

        # Not for us (or for everyone), try forwarding
        next_hop = self.routing.forward(packet)
        if next_hop is not None:
            self._forward_to_mac(packet)

    def _forward_to_mac(self, packet: Packet):
        # Use node's configured TX power
        self.mac.send(packet, packet.next_hop, tx_power_mw=self.tx_power_mw)

class SimpleGlobalChannel:
    """A channel that uses ChannelModel to deliver packets based on distance."""
    def __init__(self, model: ChannelModel, positions: List[Position]):
        self.model = model
        self.positions = positions
        self.nodes: Dict[int, SimNode] = {}
        self.active_transmissions: Dict[int, float] = {}
        self.history = []
        self.tx_counter = 0

    def add_node(self, node: SimNode):
        self.nodes[node.node_id] = node

    def is_busy(self, node_id: int) -> bool:
        now = self.nodes[node_id].scheduler.current_time
        # Clean up old transmissions
        self.active_transmissions = {k: v for k, v in self.active_transmissions.items() if v > now}
        
        # If any node is currently transmitting, the medium is busy
        return len(self.active_transmissions) > 0

    def transmit(self, src_id: int, packet: Packet, dest_id: int, tx_power_mw: float, duration: float):
        now = self.nodes[src_id].scheduler.current_time
        self.active_transmissions[src_id] = now + duration
        self.history.append((src_id, now, now + duration))
        
        # Progress indicator
        self.tx_counter += 1
        if self.tx_counter % 500 == 0:
            print(".", end="", flush=True)
        
        # Determine reception for all other nodes
        for other_id, other_node in self.nodes.items():
            if other_id == src_id:
                continue
                
            dist = self.positions[src_id].distance_to(self.positions[other_id])
            
            # Use ChannelModel to decide if packet is received
            if self.model.is_received(tx_power_mw, dist):
                if dest_id == -1 or dest_id == other_id:
                    # Deliver packet
                    pkt_copy = Packet(
                        src=packet.src,
                        dest=packet.dest,
                        payload=packet.payload,
                        packet_id=packet.packet_id,
                        ttl=packet.ttl,
                        next_hop=packet.next_hop,
                        hop_count=packet.hop_count,
                        is_ack=packet.is_ack,
                        is_absolute=packet.is_absolute,
                        sample_weight=packet.sample_weight,
                        nonce=packet.nonce,
                        size_bytes=packet.size_bytes
                    )
                    other_node.scheduler.schedule(duration, other_node.mac.receive, pkt_copy, duration)

def run_simulation(strategy: str, seed: int, num_packets: int = 1, tx_power_mw: float = 1.0, area_size: float = 300.0):
    """Runs a single simulation scenario."""
    rng = np.random.default_rng(seed)
    scheduler = EventScheduler()

    # Configuration
    topo_cfg = TopologyConfig(area_width=area_size, area_height=area_size, num_nodes=49)
    chan_cfg = ChannelConfig(packet_length=128)
    mac_cfg = MacConfig()
    energy_cfg = RadioEnergyConfig(
        power_tx_mw=52.2, power_rx_mw=56.4, power_idle_mw=56.4,
        power_sleep_mw=0.06, wakeup_cost_mj=0.0, battery_capacity_joules=100.0
    )

    # 1. Setup Topology
    topo = GridTopology(topo_cfg, rng)
    positions = topo.generate()

    # 2. Setup Channel
    chan_model = ChannelModel(chan_cfg, rng)
    channel = SimpleGlobalChannel(chan_model, positions)

    # 3. Create Nodes
    nodes = {}
    for i in range(topo_cfg.num_nodes):
        nodes[i] = SimNode(i, scheduler, rng, mac_cfg, energy_cfg, channel, strategy, positions, tx_power_mw=tx_power_mw)
        channel.add_node(nodes[i])

    # 4. If Tree, build the tree
    if strategy == "tree":
        # Dynamic range based on spacing
        spacing = area_size / (np.sqrt(topo_cfg.num_nodes) + 1)
        # Use a slightly larger range for graph construction to find potential paths
        graph = topo.to_graph(positions, range_m=spacing * 1.5)
        for i in range(topo_cfg.num_nodes):
            nodes[i].routing.update_from_graph(graph, sink_id=0)

    # 5. Schedule Traffic
    for i in range(1, topo_cfg.num_nodes):
        for p in range(num_packets):
            delay = rng.uniform(0.1, 5.0) + (p * 5.0)
            scheduler.schedule(delay, nodes[i].send_data, 0, f"data-{p}")

    # 6. Run Simulation
    print(f"  {strategy:<10}", end="", flush=True)
    scheduler.run(until=40.0)
    print(" [Done]")

    # 7. Collect Results
    total_sent_app = sum(n.stats.sent_count for i, n in nodes.items() if i != 0)
    total_received = nodes[0].stats.received_count
    total_tx_count = len(channel.history)

    pdr = (total_received / total_sent_app) * 100 if total_sent_app > 0 else 0
    avg_lat = nodes[0].stats.total_latency / total_received if total_received > 0 else 0
    avg_hops = np.mean(nodes[0].stats.hop_counts) if nodes[0].stats.hop_counts else 0

    return {
        "Strategy": strategy.capitalize(),
        "PDR (%)": pdr,
        "Avg Latency (s)": avg_lat,
        "Avg Hops": avg_hops,
        "Total TX": total_tx_count,
        "Total Received": total_received
    }

def print_results(results):
    header = f"{'Strategy':<10} | {'PDR (%)':>8} | {'Lat (s)':>8} | {'Hops':>6} | {'Total TX':>10} | {'Recv':>6}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['Strategy']:<10} | {r['PDR (%)']:8.2f} | {r['Avg Latency (s)']:8.3f} | {r['Avg Hops']:6.1f} | {r['Total TX']:10} | {r['Total Received']:6}")

if __name__ == "__main__":
    SEED = 999

    print(f"=== SCENARIO 1: Baseline (1.0mW, 300x300m) ===")
    res1 = []
    res1.append(run_simulation("flooding", SEED, tx_power_mw=1.0, area_size=300.0))
    res1.append(run_simulation("tree", SEED, tx_power_mw=1.0, area_size=300.0))
    print_results(res1)

    print(f"\n=== SCENARIO 2: Fragile Network (0.25mW, 350x350m) ===")
    res2 = []
    res2.append(run_simulation("flooding", SEED, tx_power_mw=0.25, area_size=350.0))
    res2.append(run_simulation("tree", SEED, tx_power_mw=0.25, area_size=350.0))
    print_results(res2)

    print("\nObservation:")
    print("- In Baseline, both should perform well, but Tree is much quieter.")
    print("- In Fragile, links are unreliable. Flooding might show spatial diversity benefits,")
    print("  while Tree relies heavily on individual link reliability and MAC retries.")

