
import numpy as np
import matplotlib.pyplot as plt
import os
from wsnsim.optimization import DesignSpace, SweepRunner, identify_pareto

def forest_fire_sim(p):
    """
    Simulates a Forest Fire Detection scenario.
    Impact of Duty Cycle and TX Power on PDR, Latency, and Energy.
    """
    rng = np.random.default_rng(p["_seed"])
    tx_power = p["tx_power"]
    duty_cycle = p["duty_cycle"]
    
    # Model assumptions for the case study
    base_nodes = 100
    avg_hops = 4.5 * (1 + 0.05 * rng.standard_normal())
    
    # 1. Energy: Direct function of radio activity
    energy = (tx_power * 0.5 + 5.0) * duty_cycle # mW scale simplified to J/h unit
    
    # 2. PDR: Path loss + Interference impact
    # Higher TX power helps, but high duty cycle increases collision probability
    noise = 0.02 * rng.standard_normal()
    collision_prob = 0.1 * duty_cycle
    pdr = 1.0 - (1.0 / (tx_power + 1.0)) - collision_prob + noise
    pdr = np.clip(pdr, 0.01, 0.99)
    
    # 3. Latency: Dependent on duty cycle and hop count
    # T_wait per hop ~ 1 / duty_cycle
    latency = (avg_hops * 2.0) / (duty_cycle + 1e-6)
    
    return {
        "energy": energy,
        "pdr": pdr,
        "latency": latency
    }

def run_demo():
    print("🚀 Running Forest Fire Case Study Demo...")
    
    # Define design space: Duty Cycle (1% - 30%), TX Power (1 - 20 mW)
    space = DesignSpace({
        "tx_power": np.linspace(1, 20, 20).tolist(),
        "duty_cycle": np.linspace(0.01, 0.3, 20).tolist()
    })
    
    runner = SweepRunner(forest_fire_sim, space)
    results = runner.run(repetitions=10, sample_size=400)
    aggregated = runner.aggregate_results()
    
    # Identify Pareto Front (Energy vs PDR)
    pareto = identify_pareto(aggregated, {"energy": True, "pdr": False}, tolerance=0.002)
    
    # SCENARIO SELECTION:
    # "The Safety-First Guard"
    # Needs PDR > 90% and Latency < 60s
    candidates = [p for p in aggregated if p["pdr"] > 0.90 and p["latency"] < 60]
    
    if not candidates:
        print("⚠️ No points met the strict safety criteria. Relaxing PDR to 85%...")
        candidates = [p for p in aggregated if p["pdr"] > 0.85 and p["latency"] < 60]

    # Pick the most energy efficient from valid candidates
    best_point = min(candidates, key=lambda x: x["energy"])
    
    print("\n✅ OPTIMAL DESIGN POINT FOUND:")
    print(f"   - TX Power:    {best_point['tx_power']:.2f} mW")
    print(f"   - Duty Cycle:  {best_point['duty_cycle']:.1%} %")
    print(f"   - Reliability: {best_point['pdr']:.1%} PDR")
    print(f"   - Latency:     {best_point['latency']:.1f} s")
    print(f"   - Energy Cost: {best_point['energy']:.4f} units")

    # Visualization
    plt.figure(figsize=(12, 5))
    
    # Plot 1: Energy vs PDR Pareto
    plt.subplot(1, 2, 1)
    plt.scatter([a["energy"] for a in aggregated], [a["pdr"] for a in aggregated], 
                c='lightgray', alpha=0.5, s=10, label="Explored Space")
    
    p_energy = [p["energy"] for p in pareto]
    p_pdr = [p["pdr"] for p in pareto]
    idx = np.argsort(p_energy)
    plt.plot(np.array(p_energy)[idx], np.array(p_pdr)[idx], 'r--', alpha=0.6)
    plt.scatter(p_energy, p_pdr, c='red', s=30, label="Pareto Front")
    
    plt.scatter(best_point["energy"], best_point["pdr"], c='blue', s=100, marker='*', label="SELECTED POINT")
    plt.xlabel("Energy (Joules [J]) - Lower is better")
    plt.ylabel("PDR (Reliability)")
    plt.title("Energy vs. Reliability")
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)

    # Plot 2: Latency vs Energy
    plt.subplot(1, 2, 2)
    plt.scatter([a["energy"] for a in aggregated], [a["latency"] for a in aggregated], 
                c='lightgray', alpha=0.5, s=10)
    plt.scatter(best_point["energy"], best_point["latency"], c='blue', s=100, marker='*', label="SELECTED POINT")
    plt.axhline(60, color='green', linestyle=':', label="Max Latency (60s)")
    plt.xlabel("Energy (Joules [J])")
    plt.ylabel("Latency (s)")
    plt.title("Energy vs. Latency")
    plt.yscale('log')
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    os.makedirs("reports/figures/presentation", exist_ok=True)
    plt.savefig("reports/figures/presentation/case_study_pareto.png")
    print("\n📊 Visualization saved to: reports/figures/presentation/case_study_pareto.png")

if __name__ == "__main__":
    run_demo()
