from __future__ import annotations
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from typing import List, TYPE_CHECKING
from dataclasses import dataclass
from scipy.spatial import KDTree
from .common import Position

if TYPE_CHECKING:
    from numpy.random import Generator

@dataclass(frozen=True)
class TopologyConfig:
    """Base configuration for topology generation.
    
    Attributes:
        area_width: Width of the deployment area in meters.
        area_height: Height of the deployment area in meters.
        num_nodes: Total number of nodes to deploy.
    """
    area_width: float
    area_height: float
    num_nodes: int

class Topology:
    """Base class for node topology generation."""
    def __init__(self, config: TopologyConfig, rng: Generator) -> None:
        """Initialize the topology generator.
        
        Args:
            config: Topology configuration parameters.
            rng: NumPy random generator for reproducibility.
        """
        self.config = config
        self.rng = rng

    def generate(self) -> List[Position]:
        """Generate and return a list of node positions.
        
        Returns:
            List of generated Position objects.
        """
        raise NotImplementedError("Subclasses must implement generate()")

    def to_graph(self, positions: List[Position], range_m: float) -> nx.Graph:
        """Convert positions to a NetworkX graph with rich metadata using KDTree.
        
        Args:
            positions: List of node positions.
            range_m: Maximum distance for a direct wireless link.
            
        Returns:
            A NetworkX Graph object with node metadata (x, y, pos).
        """
        G = nx.Graph()
        for i, pos in enumerate(positions):
            G.add_node(
                i, 
                pos=(pos.x, pos.y),
                x=pos.x,
                y=pos.y
            )
            
        if not positions or range_m <= 0:
            return G

        # Optimize neighbor search using KDTree
        coords = np.array([[p.x, p.y] for p in positions])
        tree = KDTree(coords)
        
        # Use sparse_distance_matrix to get both pairs and distances in one pass
        dists = tree.sparse_distance_matrix(tree, range_m)
        
        for (i, j), d in dists.items():
            if i < j: # Only add one direction for undirected graph
                G.add_edge(i, j, weight=float(d))
            
        return G

    def _create_plot(self, positions: List[Position], range_m: float = 0.0) -> None:
        """Internal helper to setup the Matplotlib/NetworkX plot."""
        if not positions:
            print("No positions to plot.")
            return

        G = self.to_graph(positions, range_m)
        pos_dict = nx.get_node_attributes(G, 'pos')
        
        plt.figure(figsize=(10, 8))
        
        # Highlight Sink (Node 0) vs regular Sensors
        sensor_nodes = [n for n in G.nodes() if n != 0]
        sink_node = [0] if 0 in G.nodes() else []

        if sink_node:
            nx.draw_networkx_nodes(G, pos_dict, nodelist=sink_node, node_size=200, 
                                   node_color='red', node_shape='s', label='Sink (Node 0)', alpha=0.9)
        
        nx.draw_networkx_nodes(G, pos_dict, nodelist=sensor_nodes, node_size=100, 
                               node_color='skyblue', label='Sensor Node', alpha=0.8)
        
        nx.draw_networkx_labels(G, pos_dict, font_size=8)
        
        if range_m > 0:
            nx.draw_networkx_edges(G, pos_dict, alpha=0.3, edge_color='gray', label=f'Link (range={range_m}m)')
            plt.title(f"{self.__class__.__name__} (Range: {range_m}m, Edges: {G.number_of_edges()})")
        else:
            plt.title(f"{self.__class__.__name__} ({len(positions)} nodes)")

        plt.xlabel("X (m)")
        plt.ylabel("Y (m)")
        
        # Set 10m grid/tick intervals
        from matplotlib.ticker import MultipleLocator
        plt.gca().xaxis.set_major_locator(MultipleLocator(10.0))
        plt.gca().yaxis.set_major_locator(MultipleLocator(10.0))
        
        plt.xlim(-self.config.area_width * 0.05, self.config.area_width * 1.05)
        plt.ylim(-self.config.area_height * 0.05, self.config.area_height * 1.05)
        plt.grid(True, linestyle=':', alpha=0.5)
        
        # Add Legend
        plt.legend(scatterpoints=1, loc='upper right', frameon=True, shadow=True)
        plt.axis('on')

    def visualize(self, positions: List[Position], range_m: float = 0.0) -> None:
        """Display the topology visualization.
        
        Args:
            positions: List of node positions to visualize.
            range_m: If > 0, draw edges between nodes within this range.
        """
        self._create_plot(positions, range_m)
        plt.show()

    def save_visualization(self, positions: List[Position], filename: str, range_m: float = 0.0) -> None:
        """Export the topology visualization to a file.
        
        Args:
            positions: List of node positions.
            filename: Path to save the image (e.g., 'topology.png').
            range_m: If > 0, draw edges between nodes within this range.
        """
        self._create_plot(positions, range_m)
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

    def get_connectivity_metrics(self, positions: List[Position], range_m: float, sink_id: int = 0) -> dict:
        """Calculate key network connectivity metrics.
        
        Args:
            positions: List of node positions.
            range_m: Maximum communication range in meters.
            sink_id: ID of the sink node (usually 0).
            
        Returns:
            Dictionary containing:
                is_connected: Boolean, True if the whole graph is connected.
                num_components: Integer, number of connected components.
                avg_degree: Float, average number of neighbors per node.
                sink_reachability: Float (0.0 to 1.0), fraction of nodes that can reach the sink.
                max_component_size: Integer, number of nodes in the largest component.
        """
        G = self.to_graph(positions, range_m)
        num_nodes = G.number_of_nodes()
        
        if num_nodes == 0:
            return {
                "is_connected": False,
                "num_components": 0,
                "avg_degree": 0.0,
                "sink_reachability": 0.0,
                "max_component_size": 0
            }

        # Component analysis
        components = list(nx.connected_components(G)) # find groups of nodes in the graph where every node in a group is connected to every other node in that same group through some path
        num_components = len(components)
        max_comp_size = len(max(components, key=len))
        is_connected = (num_components == 1 and num_nodes > 0)
        
        # Average degree
        degrees = [d for n, d in G.degree()]
        avg_degree = sum(degrees) / num_nodes
        
        # Sink reachability (nodes in the same component as the sink)
        sink_comp = next((c for c in components if sink_id in c), set()) # find the component that contains the sink node, if it exists
        sink_reachability = len(sink_comp) / num_nodes if num_nodes > 0 else 0.0  # calculate the fraction of nodes that can reach the sink (i.e., are in the same component as the sink)
        
        return {
            "is_connected": is_connected,
            "num_components": num_components,
            "avg_degree": avg_degree,
            "sink_reachability": sink_reachability,
            "max_component_size": max_comp_size
        }

class RandomTopology(Topology):
    """Uniform random deployment of nodes."""
    def generate(self) -> List[Position]:
        return [
            Position(
                x=self.rng.uniform(0, self.config.area_width),
                y=self.rng.uniform(0, self.config.area_height)
            )
            for _ in range(self.config.num_nodes)
        ]

class GridTopology(Topology):
    """Deterministic grid deployment."""
    def generate(self) -> List[Position]:
        positions = []
        # Calculate grid dimensions (square-ish)
        side = int(np.ceil(np.sqrt(self.config.num_nodes)))
        dx = self.config.area_width / (side + 1)
        dy = self.config.area_height / (side + 1)
        
        count = 0
        for i in range(1, side + 1):
            for j in range(1, side + 1):
                if count < self.config.num_nodes:
                    positions.append(Position(x=i * dx, y=j * dy))
                    count += 1
        return positions

@dataclass(frozen=True)
class ClusterTopologyConfig(TopologyConfig):
    """Config for clustered deployment.
    
    Attributes:
        num_clusters: Number of cluster centers.
        cluster_std: Spread of nodes around the center (meters).
    """
    num_clusters: int = 4
    cluster_std: float = 10.0

class ClusterTopology(Topology):
    """Nodes grouped around random cluster heads."""
    def __init__(self, config: ClusterTopologyConfig, rng: Generator) -> None:
        super().__init__(config, rng)
        self.config: ClusterTopologyConfig = config

    def generate(self) -> List[Position]:
        if self.config.num_clusters <= 0:
            return []

        # 1. Place cluster heads
        heads = [
            (self.rng.uniform(0, self.config.area_width), 
             self.rng.uniform(0, self.config.area_height))
            for _ in range(self.config.num_clusters)
        ]

        # 2. Distribute nodes stochastically among clusters
        positions = []
        for _ in range(self.config.num_nodes):
            head_idx = self.rng.integers(0, self.config.num_clusters)
            head = heads[head_idx]
            
            x = self.rng.normal(head[0], self.config.cluster_std)
            y = self.rng.normal(head[1], self.config.cluster_std)
            
            # Keep within bounds
            x = np.clip(x, 0, self.config.area_width)
            y = np.clip(y, 0, self.config.area_height)
            positions.append(Position(x, y))
            
        return positions
