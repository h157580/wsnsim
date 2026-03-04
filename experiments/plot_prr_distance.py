import numpy as np
import matplotlib.pyplot as plt
from wsnsim.channel import ChannelConfig, ChannelModel

def run_prr_experiment():
    # Alapbeállítások
    tx_power_mw = 1.0  # 0 dBm
    distances = np.linspace(1, 60, 100)
    sigmas = [0, 3, 6, 9]
    trials = 200  # Ennyi csomagot küldünk minden távolságon az átlagoláshoz
    
    plt.figure(figsize=(10, 6))
    rng = np.random.default_rng(seed=42)

    for sigma in sigmas:
        config = ChannelConfig(sigma=sigma)
        model = ChannelModel(config, rng)
        
        avg_prrs = []
        for d in distances:
            # Megszámoljuk a sikeres vételeket
            successes = sum(1 for _ in range(trials) if model.is_received(tx_power_mw, d))
            avg_prrs.append(successes / trials)
        
        plt.plot(distances, avg_prrs, label=f'sigma = {sigma} dB')

    plt.title(f"PRR vs Distance (Trials per point: {trials})")
    plt.xlabel("Distance (m)")
    plt.ylabel("Average PRR")
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.ylim(-0.05, 1.05)
    
    # Megjelenítés
    print("\n--- PRR(d) Experiment Summary ---")
    print(f"{'Dist (m)':>10} | {'sigma=0':>10} | {'sigma=3':>10} | {'sigma=6':>10} | {'sigma=9':>10}")
    print("-" * 55)
    
    # Print results for a few key distances
    sample_distances = [1, 10, 20, 30, 40, 50, 60]
    for d in sample_distances:
        row = [f"{d:>10.1f}"]
        for sigma in sigmas:
            config = ChannelConfig(sigma=sigma)
            model = ChannelModel(config, rng)
            successes = sum(1 for _ in range(trials) if model.is_received(tx_power_mw, d))
            row.append(f"{successes/trials:>10.2f}")
        print(" | ".join(row))

    plt.show()
    print("\nExperiment complete.")

if __name__ == "__main__":
    run_prr_experiment()
