import pytest
import numpy as np
from wsnsim.edge_ai import (
    ZScoreConfig,
    ZScoreDetector,
    EWMAConfig,
    EWMADetector,
    SignalConfig,
    SignalGenerator,
    EdgeAIMetrics,
    EdgeAIConfig,
    EdgeAIStrategy
)

@pytest.fixture
def rng():
    return np.random.default_rng(42)

def test_zscore_detector_basic():
    config = ZScoreConfig(window_size=10, threshold=3.0)
    detector = ZScoreDetector(config)
    # Warmup with small noise to establish a realistic baseline std (~0.1)
    for i in range(10):
        val = 25.0 + (0.1 if i % 2 == 0 else -0.1)
        detector.is_anomaly(val)
    
    # Normal value (within 3 sigma)
    assert not detector.is_anomaly(25.2)
    # Anomaly (far outside)
    assert detector.is_anomaly(35.0)

def test_ewma_detector_warmup():
    # Test that it doesn't detect anomalies during warmup even with zero variance
    config = EWMAConfig(alpha=0.2, threshold_mult=2.0, warmup_period=5)
    detector = EWMADetector(config)
    
    # First call: initializes moving_avg, warmup_count becomes 1
    assert not detector.is_anomaly(25.0)
    
    # Next 4 calls: updates stats, warmup_count goes from 1 to 5
    for _ in range(4):
        assert not detector.is_anomaly(25.0)
    
    assert detector.warmup_count == 5
    # The 6th call still has warmup_count=5, so it shouldn't detect yet (5 > 5 is False)
    assert not detector.is_anomaly(100.0) 
    
    # Now warmup_count is 6, the 7th call should detect (6 > 5 is True)
    assert detector.warmup_count == 6
    assert detector.is_anomaly(100.0)

def test_edge_ai_strategy_zscore_metrics(rng):
    metrics = EdgeAIMetrics()
    # Using window_size=10, threshold=3.0
    detector = ZScoreDetector(ZScoreConfig(window_size=10, threshold=3.0))
    config = EdgeAIConfig(heartbeat=10)
    strategy = EdgeAIStrategy(detector, metrics, config)
    
    # 1. Warmup with normal data (should be TNs)
    for _ in range(10):
        # We alternate slightly to create non-zero variance
        val = 25.0 + (0.1 if _ % 2 == 0 else -0.1)
        strategy.process_data(val, is_anomaly=False)
    
    assert metrics.true_negatives == 10
    assert metrics.total_samples == 10
    
    # 2. True Positive: Anomaly detected, ground truth is anomaly
    strategy.process_data(35.0, is_anomaly=True)
    assert metrics.true_positives == 1
    
    # 3. False Positive: Anomaly detected, ground truth is normal
    # (Value 26.0 should be > 3 sigma away from mean 25.0 with std 0.1)
    strategy.process_data(26.0, is_anomaly=False)
    assert metrics.false_positives == 1
    
    # 4. False Negative: No anomaly detected, ground truth is anomaly
    # (Value 25.1 is within 3 sigma, so not detected, but we claim it's an anomaly)
    strategy.process_data(25.1, is_anomaly=True)
    assert metrics.false_negatives == 1
    
    # Final check
    assert metrics.total_samples == 13
    # Precision = 1 TP / (1 TP + 1 FP) = 0.5
    assert metrics.precision == 0.5
    # Recall = 1 TP / (1 TP + 1 FN) = 0.5
    assert metrics.recall == 0.5
    # F1 = 2 * (0.5 * 0.5) / (0.5 + 0.5) = 0.5
    assert metrics.f1_score == 0.5

def test_edge_ai_strategy_ewma_metrics(rng):
    metrics = EdgeAIMetrics()
    # EWMA with warmup_period=5
    config_ewma = EWMAConfig(alpha=0.2, threshold_mult=3.0, warmup_period=5)
    detector = EWMADetector(config_ewma)
    strategy = EdgeAIStrategy(detector, metrics, EdgeAIConfig(heartbeat=20))
    
    # 1. Warmup with small noise (std will be ~0.1)
    for i in range(6):
        val = 25.0 + (0.1 if i % 2 == 0 else -0.1)
        strategy.process_data(val, is_anomaly=False)
    
    assert metrics.true_negatives == 6
    
    # 2. True Positive
    strategy.process_data(100.0, is_anomaly=True)
    assert metrics.true_positives == 1
    
    # 3. False Positive (val=26.0 is ~10 sigma away if std=0.1)
    strategy.process_data(26.0, is_anomaly=False)
    assert metrics.false_positives == 1
    
    # 4. False Negative: No anomaly detected, ground truth is anomaly
    # (Value 25.05 is within 3 sigma range [~24.7, 25.3], so it should be missed)
    strategy.process_data(25.05, is_anomaly=True)
    assert metrics.false_negatives == 1

    
    assert metrics.total_samples == 9
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5

def test_signal_generator_stats(rng):
    # Test that generator follows SignalConfig
    config = SignalConfig(base_val=50.0, std=1.0, anomaly_prob=0.0)
    gen = SignalGenerator(rng, config)
    
    samples = [gen.next_sample()[0] for _ in range(1000)]
    assert np.mean(samples) == pytest.approx(50.0, abs=0.2)
    assert np.std(samples) == pytest.approx(1.0, abs=0.2)

def test_edge_ai_integration(rng):
    # Full pipeline integration test
    sig_config = SignalConfig(base_val=25.0, std=0.5, anomaly_prob=0.05, magnitude=10.0)
    gen = SignalGenerator(rng, sig_config)
    
    metrics = EdgeAIMetrics()
    detector = ZScoreDetector(ZScoreConfig(window_size=30, threshold=3.0))
    strategy = EdgeAIStrategy(detector, metrics, EdgeAIConfig(heartbeat=100))
    
    # Process 500 samples
    for _ in range(500):
        val, is_anomaly = gen.next_sample()
        strategy.process_data(val, is_anomaly=is_anomaly)
    
    # Sanity checks
    assert metrics.total_samples == 500
    assert metrics.transmitted_packets > 0
    # Precision and Recall should be reasonably high for this simple setup
    assert metrics.f1_score > 0.5
    assert metrics.byte_reduction > 0.5 # Significant savings expected

def test_ewma_integration(rng):
    # Full pipeline integration test for EWMA
    sig_config = SignalConfig(base_val=20.0, std=0.2, anomaly_prob=0.05, magnitude=5.0)
    gen = SignalGenerator(rng, sig_config)
    
    metrics = EdgeAIMetrics()
    # Using a slightly higher threshold to reduce false positives
    detector = EWMADetector(EWMAConfig(alpha=0.3, threshold_mult=5.0, warmup_period=30))
    strategy = EdgeAIStrategy(detector, metrics, EdgeAIConfig(heartbeat=100))
    
    # Process 500 samples
    for _ in range(500):
        val, is_anomaly = gen.next_sample()
        strategy.process_data(val, is_anomaly=is_anomaly)
    
    # Sanity checks
    assert metrics.total_samples == 500
    assert metrics.transmitted_packets > 0
    # EWMA should perform well on this stable signal
    assert metrics.f1_score > 0.7
    assert metrics.byte_reduction > 0.7




