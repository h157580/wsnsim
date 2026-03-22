import pytest
import numpy as np
from wsnsim.topology import RandomTopology, GridTopology, ClusterTopology, TopologyConfig, ClusterTopologyConfig
from wsnsim.common import Position

@pytest.fixture
def rng():
    return np.random.default_rng(42)

@pytest.fixture
def base_config():
    return TopologyConfig(area_width=100.0, area_height=100.0, num_nodes=25)

def test_random_topology(base_config, rng):
    topo = RandomTopology(base_config, rng)
    positions = topo.generate()
    
    assert len(positions) == base_config.num_nodes
    for p in positions:
        assert 0 <= p.x <= base_config.area_width
        assert 0 <= p.y <= base_config.area_height

def test_grid_topology(base_config, rng):
    topo = GridTopology(base_config, rng)
    positions = topo.generate()
    
    assert len(positions) == base_config.num_nodes
    # Check uniqueness (roughly)
    coords = set((p.x, p.y) for p in positions)
    assert len(coords) == base_config.num_nodes

def test_cluster_topology(rng):
    config = ClusterTopologyConfig(area_width=100.0, area_height=100.0, num_nodes=20, num_clusters=2, cluster_std=1.0)
    topo = ClusterTopology(config, rng)
    positions = topo.generate()
    
    assert len(positions) == 20

def test_reproducibility(base_config):
    rng1 = np.random.default_rng(123)
    topo1 = RandomTopology(base_config, rng1)
    pos1 = topo1.generate()
    
    rng2 = np.random.default_rng(123)
    topo2 = RandomTopology(base_config, rng2)
    pos2 = topo2.generate()
    
    for p1, p2 in zip(pos1, pos2):
        assert p1.x == p2.x
        assert p1.y == p2.y

def test_graph_conversion(base_config, rng):
    topo = RandomTopology(base_config, rng)
    positions = topo.generate()
    # Range that should cover most nodes
    G = topo.to_graph(positions, range_m=150.0) 
    assert G.number_of_nodes() == base_config.num_nodes
    # With 150m range in 100x100 area, it should be a complete graph or nearly so
    assert G.number_of_edges() == (base_config.num_nodes * (base_config.num_nodes - 1)) / 2

def test_connectivity_metrics(base_config, rng):
    topo = RandomTopology(base_config, rng)
    # Create nodes in a predictable line
    positions = [Position(x=i*10.0, y=0.0) for i in range(5)]
    
    # Range: 5m -> All nodes isolated
    metrics = topo.get_connectivity_metrics(positions, range_m=5.0)
    assert not metrics["is_connected"]
    assert metrics["num_components"] == 5
    assert metrics["avg_degree"] == 0.0
    assert metrics["sink_reachability"] == 0.2 # Only Node 0 itself
    
    # Range: 11m -> Line graph (0-1-2-3-4)
    metrics = topo.get_connectivity_metrics(positions, range_m=11.0)
    assert metrics["is_connected"]
    assert metrics["num_components"] == 1
    # Ends have degree 1, middle 3 have degree 2 -> (1+2+2+2+1)/5 = 1.6
    assert metrics["avg_degree"] == 1.6
    assert metrics["sink_reachability"] == 1.0
    
    # Range: 45m -> All reach Node 0, but maybe not fully connected
    # Node 0 (0) can reach 10, 20, 30, 40
    # Node 4 (40) can reach 30, 20, 10, 0
    metrics = topo.get_connectivity_metrics(positions, range_m=45.0)
    assert metrics["is_connected"]
    assert metrics["sink_reachability"] == 1.0

def test_connectivity_sparse_grid(rng):
    # 2x2 grid, distance between nodes is 50m
    config = TopologyConfig(area_width=100.0, area_height=100.0, num_nodes=4)
    topo = GridTopology(config, rng)
    positions = topo.generate()
    # Grid points are roughly (33,33), (33,66), (66,33), (66,66)
    # Distance between adjacent is ~33m
    
    # Range 20m -> Isolated
    metrics = topo.get_connectivity_metrics(positions, range_m=20.0)
    assert metrics["num_components"] == 4
    
    # Range 40m -> Connected
    metrics = topo.get_connectivity_metrics(positions, range_m=40.0)
    assert metrics["is_connected"]
    assert metrics["avg_degree"] == 2.0 # (2+2+2+2)/4
