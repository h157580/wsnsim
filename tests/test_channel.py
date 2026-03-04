import pytest
import numpy as np
from wsnsim.channel import ChannelConfig, ChannelModel

@pytest.fixture
def rng():
    """Provides a seeded random generator for reproducible tests."""
    return np.random.default_rng(seed=42)

@pytest.fixture
def config():
    """Default channel configuration."""
    return ChannelConfig(
        d0=1.0,
        pl_d0=40.0,
        n=3.0,
        sigma=4.0,
        noise_floor_mw=10**(-105.0 / 10.0),
        packet_length=1024
    )

@pytest.fixture
def model(config, rng):
    """Default channel model instance."""
    return ChannelModel(config, rng)

def test_reference_distance_path_loss(model):
    """Verify path loss at and below reference distance d0."""
    # d <= d0 should return pl_d0
    assert model.get_path_loss(0.5) == 40.0
    assert model.get_path_loss(1.0) == 40.0
    assert model.get_path_loss(0.0) == 40.0

def test_path_loss_monotonicity(model):
    """Verify path loss increases with distance for d > d0."""
    pl1 = model.get_path_loss(2.0)
    pl2 = model.get_path_loss(10.0)
    assert pl2 > pl1
    # Check specific value: 40 + 10 * 3 * log10(10/1) = 40 + 30 = 70
    assert pytest.approx(pl2) == 70.0

def test_prr_monotonicity_no_shadowing(model):
    """With shadowing disabled, PRR should strictly decrease with distance."""
    # Use very low power to ensure we are in the transition zone
    # 0.0001 mW = -40 dBm
    tx_power_mw = 0.0001 
    prr1 = model.calculate_prr(tx_power_mw, 5.0, use_shadowing=False)
    prr2 = model.calculate_prr(tx_power_mw, 10.0, use_shadowing=False)
    assert prr1 > prr2

def test_reproducibility(config):
    """Two models with the same seed must produce identical results."""
    rng1 = np.random.default_rng(seed=123)
    rng2 = np.random.default_rng(seed=123)
    model1 = ChannelModel(config, rng1)
    model2 = ChannelModel(config, rng2)
    
    tx_power = 1.0
    dist = 20.0
    
    # Check multiple iterations of stochastic PRR
    for _ in range(10):
        assert model1.calculate_prr(tx_power, dist) == model2.calculate_prr(tx_power, dist)
        assert model1.is_received(tx_power, dist) == model2.is_received(tx_power, dist)

def test_shadowing_distribution(model):
    """Verify shadowing follows a normal distribution with mean 0 and std sigma."""
    samples = [model.get_shadowing() for _ in range(10000)]
    assert pytest.approx(np.mean(samples), abs=0.1) == 0.0
    assert pytest.approx(np.std(samples), rel=0.05) == model.config.sigma

def test_link_budget_extremes(model):
    """Verify PRR at extreme power levels."""
    # Very high power -> PRR ~ 1.0
    assert model.calculate_prr(1000.0, 1.0, use_shadowing=False) == pytest.approx(1.0)
    
    # Very low power -> PRR ~ 0.0
    # 1e-15 mW is -150 dBm, well below noise floor (-105 dBm)
    assert model.calculate_prr(1e-15, 1.0, use_shadowing=False) == pytest.approx(0.0)

def test_invalid_tx_power(model):
    """Handle non-positive TX power gracefully (should result in 0 PRR)."""
    # For a real system, we might raise an error, but returning 0 PRR is safe for simulations.
    # Note: calculate_prr uses log10(tx_power_mw), which will fail if not handled.
    # Let's see how our current implementation handles it (it likely crashes).
    # If it crashes, we should update the implementation.
    with pytest.raises(ValueError):
        model.calculate_prr(0.0, 1.0)
    with pytest.raises(ValueError):
        model.calculate_prr(-1.0, 1.0)
