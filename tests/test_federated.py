import pytest
import numpy as np
from wsnsim.federated import FederatedNode, FederatedServer, FLConfig, FederatedModel, FLCostAnalyzer

@pytest.fixture
def fl_config():
    return FLConfig(num_parameters=5, samples_per_round=10, learning_rate=0.1, update_threshold=0.01)

@pytest.fixture
def rng():
    return np.random.default_rng(42)

def test_federated_node_online_learning(fl_config, rng):
    node = FederatedNode(node_id=1, rng=rng, config=fl_config)
    initial_weights = node.weights.copy()
    
    # Process some data
    # y = w * x, if x is random and y=10, weights should move towards positive values
    for _ in range(5):
        node.process_data(10.0)
    
    assert node.sample_counter == 5
    assert not np.array_equal(node.weights, initial_weights)
    assert node.total_compute_energy_j > 0

def test_federated_node_sparse_update(fl_config, rng):
    # Set high threshold to trigger suppression
    config = FLConfig(num_parameters=5, samples_per_round=10, update_threshold=100.0)
    node = FederatedNode(node_id=1, rng=rng, config=config)
    
    # Process enough data to finish a round
    result = None
    for _ in range(10):
        result = node.process_data(1.0)
    
    # Change should be small, so result should be None (suppressed)
    assert result is None
    assert node.sample_counter == 0 # Reset happens even if suppressed

def test_federated_server_aggregation(fl_config):
    server = FederatedServer(total_nodes=2, config=fl_config)
    
    w1 = np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32)
    w2 = np.array([2.0, 2.0, 2.0, 2.0, 2.0], dtype=np.float32)
    
    server.receive_update(FederatedModel(w1, n_samples=10))
    server.receive_update(FederatedModel(w2, n_samples=10))
    
    global_w = server.aggregate()
    expected = np.array([1.5, 1.5, 1.5, 1.5, 1.5], dtype=np.float32)
    np.testing.assert_allclose(global_w, expected)
    assert len(server.updates) == 0

def test_federated_server_amnesia_prevention(fl_config):
    # 10 nodes total, but only 1 sends an update
    server = FederatedServer(total_nodes=10, config=fl_config)
    server.global_weights = np.zeros(5, dtype=np.float32)
    
    # Node 1 sends weights [1, 1, 1, 1, 1]
    w1 = np.ones(5, dtype=np.float32)
    server.receive_update(FederatedModel(w1, n_samples=10))
    
    global_w = server.aggregate()
    
    # 1 active node (10 samples) + 9 silent nodes (90 samples of 0.0)
    # Total samples = 100. New weight = (10*1 + 90*0) / 100 = 0.1
    expected = np.ones(5, dtype=np.float32) * 0.1
    np.testing.assert_allclose(global_w, expected)

def test_cost_analyzer(fl_config):
    analyzer = FLCostAnalyzer(fl_config, total_nodes=10, avg_hops=1.0)
    cent, fl = analyzer.analyze(rounds=1, final_loss=0.5, suppression_rate=0.0)
    
    # Centralized: 1 round * 10 nodes * 10 samples * (12+4 bytes) * 1 hop = 1600 bytes
    assert cent.total_bytes == 1600
    
    # FL: 1 round * 10 nodes * (12 + 5*4 bytes) * 1 hop (Uplink) + 1*32 (Downlink)
    # 10 * 32 + 32 = 352 bytes
    assert fl.total_bytes == 352
    assert fl.reduction_factor == pytest.approx(1600 / 352)
