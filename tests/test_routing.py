import pytest
from wsnsim.common import Packet
from wsnsim.routing import FloodingRouting, TreeRouting
from wsnsim.topology import Topology, TopologyConfig, GridTopology
import networkx as nx
import numpy as np

def test_flooding_loop_prevention():
    """Verify that flooding drops packets it has already seen."""
    router = FloodingRouting(node_id=1)
    packet = Packet(src=0, dest=2, payload="Hello", packet_id=101, ttl=10)
    
    # First time: should forward (return -1)
    assert router.forward(packet) == -1
    assert packet.ttl == 9
    assert packet.hop_count == 1
    
    # Second time with same packet: should drop (return None)
    assert router.forward(packet) is None

def test_flooding_ttl_expiration():
    """Verify that flooding drops packets when TTL reaches zero."""
    router = FloodingRouting(node_id=1)
    packet = Packet(src=0, dest=2, payload="Hello", packet_id=102, ttl=1)
    
    # First hop: OK
    assert router.forward(packet) == -1
    assert packet.ttl == 0
    
    # Second hop: Should drop because TTL=0
    packet2 = Packet(src=0, dest=2, payload="Hello", packet_id=103, ttl=0)
    assert router.forward(packet2) is None

def test_tree_routing_sink_path():
    """Verify that tree routing correctly forwards towards the sink."""
    # Node 1's parent is Node 0
    router = TreeRouting(node_id=1, parent_id=0)
    packet = Packet(src=1, dest=0, payload="Data", packet_id=1, ttl=10)
    
    assert router.forward(packet) == 0
    assert packet.ttl == 9
    assert packet.hop_count == 1

def test_tree_routing_no_parent():
    """Verify that tree routing drops packets if no parent is known."""
    router = TreeRouting(node_id=5, parent_id=None)
    packet = Packet(src=5, dest=0, payload="Data", packet_id=1)
    
    assert router.forward(packet) is None

def test_bfs_tree_construction():
    """Verify tree construction using BFS on a grid topology."""
    # Create a 3x3 grid
    rng = np.random.default_rng(42)
    config = TopologyConfig(area_width=100, area_height=100, num_nodes=9)
    topo = GridTopology(config, rng)
    positions = topo.generate()
    # Range of 40m ensures connectivity in a 3x3 grid (spacing is ~33m)
    graph = topo.to_graph(positions, range_m=40.0)
    
    # Create routers for each node using the factory method
    routers = {i: TreeRouting.from_graph(i, graph) for i in range(9)}
    
    # Check metrics (Node 8 is 4 hops away from Node 0 in a 3x3 grid BFS)
    # (0,0) -> (0,1) -> (0,2)
    # (1,0) -> (1,1) -> (1,2)
    # (2,0) -> (2,1) -> (2,2)
    # Actually, grid generation might differ, let's verify connectivity
    assert nx.is_connected(graph)
    
    # Check a specific path (e.g., node 8)
    curr = 8
    path = [curr]
    for _ in range(10):
        packet = Packet(src=8, dest=0, payload="test", packet_id=1)
        next_hop = routers[curr].forward(packet)
        if next_hop is None:
            break
        path.append(next_hop)
        curr = next_hop
        
    assert path[-1] == 0
    assert len(path) > 1
    # Check that metric decreases along the path
    for i in range(len(path) - 1):
        assert routers[path[i]].metric > routers[path[i+1]].metric
