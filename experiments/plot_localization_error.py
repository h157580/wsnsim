import numpy as np
import matplotlib.pyplot as plt
from wsnsim.sync_localization import trilaterate, estimate_distance_from_rssi
from wsnsim.common import Position
from wsnsim.channel import ChannelConfig

def run_localization_experiment():
    # Setup
    target = Position(10, 10)
    anchors = [Position(0,0), Position(20,0), Position(0,20), Position(20,20)]
    config = ChannelConfig(n=3.0, pl_d0=40.0, d0=1.0)
    tx_power_dbm = 0.0
    
    sigmas = np.linspace(0, 10, 20) # 0 to 10 dB noise
    avg_errors = []
    max_errors = []
    
    rng = np.random.default_rng(42)
    iterations = 100 # Run 100 trials per noise level for a stable average

    print("Running localization experiment...")
    for sigma in sigmas:
        errors = []
        for _ in range(iterations):
            noisy_dists = []
            for a in anchors:
                d = a.distance_to(target)
                # True RSSI
                rssi = tx_power_dbm - (config.pl_d0 + 10 * config.n * np.log10(d/config.d0))
                # Add Shadowing
                rssi += rng.normal(0, sigma)
                # Estimate distance
                d_est = estimate_distance_from_rssi(rssi, tx_power_dbm, config.n, config.d0, config.pl_d0)
                noisy_dists.append(d_est)
            
            try:
                est = trilaterate(anchors, noisy_dists)
                errors.append(target.distance_to(est))
            except ValueError:
                continue
        
        avg_errors.append(np.mean(errors))
        max_errors.append(np.max(errors))

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(sigmas, avg_errors, 'b-o', label='Average Error')
    plt.fill_between(sigmas, 0, max_errors, color='blue', alpha=0.1, label='Max Error Range')
    
    plt.title('Localization Error vs. Shadowing Noise (4 Anchors)')
    plt.xlabel('Shadowing Sigma (dB)')
    plt.ylabel('Position Error (m)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    output_path = "reports/figures/localization_error_vs_noise.png"
    plt.savefig(output_path)
    print(f"Plot saved to {output_path}")

if __name__ == "__main__":
    run_localization_experiment()
