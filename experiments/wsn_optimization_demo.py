import numpy as np
import matplotlib.pyplot as plt
import os
from wsnsim.optimization import DesignSpace, SweepRunner, identify_pareto

def wsn_sim_model(p):
    """
    Simulation model based on the provided logic.
    Parameters: tx_power, duty_cycle, node_count (used to calculate hop_count)
    """
    # Unpack parameters
    tx_power = p["tx_power"]
    duty_cycle = p["duty_cycle"]
    # Derived value: hop_count (dependent on node_count, with some noise)
    hop_count = np.sqrt(p["node_count"]) * (1 + 0.1 * np.random.default_rng(p["_seed"]).standard_normal())
    
    # DECISION: Conflicting objectives
    energy = tx_power * duty_cycle
    # PDR: Higher tx_power is better, higher hop_count is worse
    pdr = 1 - (0.1 * hop_count / (tx_power + 1e-6))
    pdr = np.clip(pdr, 0, 1)
    
    latency = hop_count / duty_cycle
    
    return {
        "energy": energy,
        "pdr": pdr,
        "latency": latency
    }

def main():
    print("=== High-Density Multi-Objective WSN Optimization Sweep ===")
    
    # DECISION: Denser design space for better curve visualization
    # 50 * 50 = 2500 possible combinations
    space = DesignSpace({
        "node_count": [100], 
        "tx_power": np.linspace(1, 20, 50).tolist(), 
        "duty_cycle": np.linspace(0.01, 0.5, 50).tolist()
    })
    
    # 1. Run Sweep
    runner = SweepRunner(wsn_sim_model, space)
    # Save config dump
    os.makedirs("reports", exist_ok=True)
    space.save_config("reports/optimization_config.json")
    
    # 500 unique configurations, each with 5 repetitions
    results = runner.run(repetitions=5, sample_size=500)
    
    # 2. Pareto-front search (Aggregated for noise reduction)
    # DECISION: Average across repetitions first for a clean front
    aggregated = runner.aggregate_results()
    
    # DECISION: Fine-tuned leniency (target approx. 50 points)
    # Tolerance of 0.005 allows 'near-optimal' points to stay
    pareto = identify_pareto(aggregated, {"energy": True, "pdr": False}, tolerance=0.005)
    
    print(f"\nPareto-optimal solutions count: {len(pareto)}/{len(aggregated)}")
    
    # 3. Save and Visualization
    os.makedirs("reports/figures", exist_ok=True)
    # Save both raw and aggregated data
    runner.save_to_csv("reports/wsn_raw_sweep.csv")
    runner.save_to_csv("reports/wsn_aggregated_sweep.csv", data=aggregated)
    
    plt.figure(figsize=(10, 6))
    
    # All aggregated configurations (gray background)
    plt.scatter([a["energy"] for a in aggregated], [a["pdr"] for a in aggregated], 
                c='gray', alpha=0.3, label='All configurations')
    
    # Pareto-front (red curve)
    p_energy = [p["energy"] for p in pareto]
    p_pdr = [p["pdr"] for p in pareto]
    
    # Sort for cleaner line plotting
    sorted_indices = np.argsort(p_energy)
    plt.plot(np.array(p_energy)[sorted_indices], np.array(p_pdr)[sorted_indices], 
             color='red', linestyle='--', alpha=0.5)
    plt.scatter(p_energy, p_pdr, c='red', s=80, label='Pareto-front (Cleaned)')
    
    plt.xlabel("Energy Consumption (J)")
    plt.ylabel("PDR (Reliability)")
    plt.title("Energy vs. Reliability Pareto-front (2D Focus)")
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.savefig("reports/figures/presentation/wsn_pareto_plot.png")
    print("Plot saved: reports/figures/presentation/wsn_pareto_plot.png")

    # 4. Sensitivity Analysis
    print("\n=== Sensitivity Analysis ===")
    from wsnsim.optimization import calculate_sensitivity
    
    # How sensitive is Energy to TX Power?
    energy_tx_sens = calculate_sensitivity(aggregated, "energy", "tx_power")
    avg_tx_sens = np.mean(list(energy_tx_sens.values()))
    
    # How sensitive is Energy to Duty Cycle?
    energy_dc_sens = calculate_sensitivity(aggregated, "energy", "duty_cycle")
    avg_dc_sens = np.mean(list(energy_dc_sens.values()))
    
    print(f"Avg Energy sensitivity to TX Power: {avg_tx_sens:.4f} J/unit")
    print(f"Avg Energy sensitivity to Duty Cycle: {avg_dc_sens:.4f} J/unit")
    
    if avg_tx_sens > avg_dc_sens:
        print("Insight: TX Power has a higher impact on Energy consumption.")
    else:
        print("Insight: Duty Cycle has a higher impact on Energy consumption.")

if __name__ == "__main__":
    main()
