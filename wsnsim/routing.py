from __future__ import annotations
from typing import Dict, List, Optional, Set, Any
from .common import Packet

class BaseRouting:
    """Base class for all routing strategies."""
    def __init__(self, node_id: int):
        self.node_id = node_id

    def forward(self, packet: Packet) -> Optional[int]:
        """Decide the next hop for a packet.
        
        Returns:
            The next hop ID (integer) or None if the packet should be dropped.
        """
        raise NotImplementedError("Subclasses must implement forward()")

class FloodingRouting(BaseRouting):
    """Simple flooding: re-broadcast if TTL > 0 and packet not seen before."""
    def __init__(self, node_id: int, max_seen_cache: int = 100):
        super().__init__(node_id)
        # Set for O(1) lookups, List for O(1) FIFO eviction
        self.seen_set: Set[tuple[int, int]] = set()
        self.seen_queue: List[tuple[int, int]] = []
        self.max_seen_cache = max_seen_cache

    def forward(self, packet: Packet) -> Optional[int]:
        # Drop if already seen or TTL is zero
        key = (packet.src, packet.packet_id)
        
        if key in self.seen_set or packet.ttl <= 0:
            return None
            
        # Add to cache with FIFO eviction
        if len(self.seen_queue) >= self.max_seen_cache:
            oldest = self.seen_queue.pop(0)
            self.seen_set.remove(oldest)
            
        self.seen_set.add(key)
        self.seen_queue.append(key)
        
        # Decrement TTL and mark for broadcast
        packet.ttl -= 1
        packet.hop_count += 1
        packet.next_hop = -1
        return -1 # Broadcast constant

import networkx as nx

class TreeRouting(BaseRouting):
    """Convergecast routing: all traffic flows towards the sink (Node 0)."""
    def __init__(self, node_id: int, parent_id: Optional[int] = None):
        super().__init__(node_id)
        self.parent_id = parent_id
        # For future ETX/Metric support
        self.metric: float = float('inf') if node_id != 0 else 0.0

    @classmethod
    def from_graph(cls, node_id: int, graph: nx.Graph, sink_id: int = 0, metric_type: str = "hops") -> TreeRouting:
        """Factory method to create a TreeRouting instance using a graph.
        
        Args:
            node_id: The ID of the node this router belongs to.
            graph: A NetworkX graph representing the network topology.
            sink_id: The ID of the sink node (root of the tree).
            metric_type: "hops" for BFS or "etx" for shortest path based on 1/PRR.
        """
        router = cls(node_id)
        router.update_from_graph(graph, sink_id, metric_type)
        return router

    def update_from_graph(self, graph: nx.Graph, sink_id: int = 0, metric_type: str = "hops"):
        """Update parent and metric based on the graph topology."""
        if self.node_id == sink_id:
            self.parent_id = None
            self.metric = 0.0
            return

        if metric_type == "etx":
            try:
                # Calculate path towards the sink
                path = nx.shortest_path(graph, source=self.node_id, target=sink_id, weight="etx")
                if len(path) > 1:
                    self.parent_id = path[1]
                    self.metric = nx.shortest_path_length(graph, source=self.node_id, target=sink_id, weight="etx")
                else:
                    self.parent_id = None
                    self.metric = float('inf')
            except (nx.NetworkXNoPath, nx.NodeNotFound, KeyError):
                self._update_hops(graph, sink_id)
        else:
            self._update_hops(graph, sink_id)

    def _update_hops(self, graph: nx.Graph, sink_id: int):
        """Internal helper for hop-count BFS towards the sink."""
        try:
            # Dijkstra/Shortest path for BFS (unweighted) to find next hop reliably
            path = nx.shortest_path(graph, source=self.node_id, target=sink_id)
            if len(path) > 1:
                self.parent_id = path[1]
                self.metric = float(len(path) - 1)
            else:
                self.parent_id = None
                self.metric = float('inf')
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self.parent_id = None
            self.metric = float('inf')

    def update_route(self, parent_id: int, metric: float):
        """Update the parent and associated path metric (e.g., hop count or ETX)."""
        self.parent_id = parent_id
        self.metric = metric

    def forward(self, packet: Packet) -> Optional[int]:
        """Route packet towards the parent."""
        if packet.dest != 0:
            # For now, TreeRouting only supports convergecast to the sink
            return None

        if self.node_id == 0:
            # Already at destination
            return None

        if self.parent_id is None:
            # Route unknown
            return None

        packet.ttl -= 1
        packet.hop_count += 1
        packet.next_hop = self.parent_id
        return self.parent_id
