import pytest
import numpy as np
from wsnsim.sync_localization import SyncClock, trilaterate, estimate_distance_from_rssi
from wsnsim.common import Position
from wsnsim.channel import ChannelConfig

def test_sync_clock_drift():
    """Verify that local and global durations are correctly converted without noise."""
    clock = SyncClock(drift_ppm=40.0)
    global_duration = 100.0
    expected_local = 100.0 * (1 + 40/1_000_000.0)
    assert clock.to_local_duration(global_duration) == pytest.approx(expected_local)
    assert clock.to_global_duration(expected_local) == pytest.approx(global_duration)

def test_trilateration_3_anchors_ideal():
    """Test trilateration with 3 anchors and a known point (5, 5) - Ideal Case."""
    target = Position(5.0, 5.0)
    anchors = [Position(0,0), Position(10,0), Position(0,10)]
    distances = [p.distance_to(target) for p in anchors]
    est = trilaterate(anchors, distances)
    error = target.distance_to(est)
    print(f"\n[Ideal 3-Anchor] Error: {error:.2e} m")
    assert error < 1e-10

def test_trilateration_noisy_rssi():
    """Test trilateration with standard 4.0 dB shadowing noise."""
    target = Position(5.0, 5.0)
    anchors = [Position(0,0), Position(15,0), Position(0,15), Position(15,15)]
    config = ChannelConfig(sigma=4.0, n=3.0, pl_d0=40.0, d0=1.0)
    tx_power_dbm = 0.0
    rng = np.random.default_rng(42)
    
    noisy_distances = []
    for a in anchors:
        true_dist = a.distance_to(target)
        pl_true = config.pl_d0 + 10 * config.n * np.log10(true_dist / config.d0)
        rssi_noisy = (tx_power_dbm - pl_true) + rng.normal(0, config.sigma)
        dist_est = estimate_distance_from_rssi(rssi_noisy, tx_power_dbm, config.n, config.d0, config.pl_d0)
        noisy_distances.append(dist_est)
    
    est = trilaterate(anchors, noisy_distances)
    error = target.distance_to(est)
    print(f"\n[Standard Noise 4dB] Estimated Pos: ({est.x:.2f}, {est.y:.2f}), Error: {error:.2f} m")
    assert error < 8.0 

def test_trilateration_noise_scaling():
    """Observe how localization error increases with noise (sigma)."""
    target = Position(10, 10)
    anchors = [Position(0,0), Position(20,0), Position(0,20), Position(20,20)]
    config = ChannelConfig(n=3.0, pl_d0=40.0, d0=1.0)
    rng = np.random.default_rng(123)
    
    print("\n[Noise Scaling Test]")
    for sigma in [0.0, 2.0, 4.0, 8.0]:
        noisy_dists = []
        for a in anchors:
            d = a.distance_to(target)
            rssi = 0.0 - (config.pl_d0 + 10 * config.n * np.log10(d/config.d0))
            rssi += rng.normal(0, sigma)
            noisy_dists.append(estimate_distance_from_rssi(rssi, 0, config.n, config.d0, config.pl_d0))
        
        est = trilaterate(anchors, noisy_dists)
        error = target.distance_to(est)
        print(f"  Sigma: {sigma} dB -> Error: {error:.2f} m")

def test_trilateration_anchor_count_effect():
    """Observe how more anchors mitigate high noise (sigma=6dB)."""
    target = Position(10, 10)
    sigma = 6.0
    config = ChannelConfig(n=3.0, pl_d0=40.0, d0=1.0)
    rng = np.random.default_rng(99)
    
    anchors_3 = [Position(0,0), Position(20,0), Position(10,20)]
    anchors_10 = [Position(x, y) for x in [0, 10, 20] for y in [0, 10, 20]] # 9 points
    anchors_10.append(Position(5, 5)) # 10th point

    def get_error(anchors):
        noisy_dists = []
        for a in anchors:
            d = a.distance_to(target)
            rssi = 0.0 - (config.pl_d0 + 10 * config.n * np.log10(d/config.d0))
            rssi += rng.normal(0, sigma)
            noisy_dists.append(estimate_distance_from_rssi(rssi, 0, config.n, config.d0, config.pl_d0))
        est = trilaterate(anchors, noisy_dists)
        return target.distance_to(est)

    err_3 = get_error(anchors_3)
    err_10 = get_error(anchors_10)
    
    print(f"\n[Anchor Count Test (Sigma=6dB)]")
    print(f"  3 Anchors Error: {err_3:.2f} m")
    print(f"  10 Anchors Error: {err_10:.2f} m")
    assert err_10 < err_3 or err_10 < 10.0

def test_trilateration_outside_hull():
    """Observe the 'Dilution of Precision' when target is outside the anchor hull."""
    # Anchors in a small 10x10 area
    anchors = [Position(0,0), Position(10,0), Position(0,10), Position(10,10)]
    # Target is far outside
    target = Position(50, 50)
    config = ChannelConfig(sigma=2.0) # Low noise
    rng = np.random.default_rng(42)
    
    noisy_dists = []
    for a in anchors:
        d = a.distance_to(target)
        rssi = 0.0 - (config.pl_d0 + 10 * config.n * np.log10(d/config.d0))
        rssi += rng.normal(0, config.sigma)
        noisy_dists.append(estimate_distance_from_rssi(rssi, 0, config.n, config.d0, config.pl_d0))
    
    est = trilaterate(anchors, noisy_dists)
    error = target.distance_to(est)
    print(f"\n[Outside Hull Test (Sigma=2dB)]")
    print(f"  Target: (50, 50), Estimated: ({est.x:.2f}, {est.y:.2f})")
    print(f"  Localization Error: {error:.2f} m")
    # High error is EXPECTED here due to Geometric Dilution of Precision (DOP).
    # Since the target is far outside the small anchor hull, small RSSI errors
    # translate to huge position shifts.
    assert error < 150.0

def test_trilateration_insufficient_anchors():
    """Verify that it raises error for < 3 anchors."""
    with pytest.raises(ValueError, match="At least 3 anchors"):
        trilaterate([Position(0, 0), Position(1, 1)], [1.0, 1.0])

def test_trilateration_collinear_anchors():
    """Verify that it raises error for anchors in a straight line."""
    anchors = [Position(0,0), Position(10,0), Position(20,0)]
    distances = [5.0, 5.0, 15.0]
    with pytest.raises(ValueError, match="collinear or degenerate"):
        trilaterate(anchors, distances)
