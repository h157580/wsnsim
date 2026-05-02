import numpy as np
import json
import matplotlib.pyplot as plt
from dataclasses import asdict
from typing import List, Dict, Any
from datetime import datetime
from wsnsim.edge_ai import (
    SignalConfig, SignalGenerator, EdgeAIMetrics,
    ZScoreConfig, ZScoreDetector,
    EWMAConfig, EWMADetector,
    EdgeAIConfig, EdgeAIStrategy
)

def run_experiment(detector_type: str, det_config: Any, sig_config: SignalConfig, seeds: List[int]) -> Dict[str, float]:
    """Runs a batch of simulations across different seeds and averages the metrics."""
    agg_metrics = []
    
    for seed in seeds:
        rng = np.random.default_rng(seed)
        gen = SignalGenerator(rng, sig_config)
        metrics = EdgeAIMetrics()
        
        if detector_type == "ZScore":
            detector = ZScoreDetector(det_config)
        else:
            detector = EWMADetector(det_config)
            
        strategy = EdgeAIStrategy(detector, metrics, EdgeAIConfig(heartbeat=100))
        
        # Simulating 2000 samples for robust statistics
        for _ in range(2000):
            val, is_anomaly = gen.next_sample()
            strategy.process_data(val, is_anomaly=is_anomaly)
            
        fpr = metrics.false_positives / (metrics.false_positives + metrics.true_negatives) if (metrics.false_positives + metrics.true_negatives) > 0 else 0.0
        
        agg_metrics.append({
            "f1": metrics.f1_score,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "reduction": metrics.byte_reduction,
            "fpr": fpr
        })
        
    # Return average across seeds
    return {
        key: float(np.mean([m[key] for m in agg_metrics]))
        for key in agg_metrics[0].keys()
    }

def cross_validate():
    print(f"Starting Edge AI Cross-Validation Experiment...")
    print(f"Timestamp: {datetime.now().isoformat()}\n")
    
    seeds = [42, 57, 101, 202, 303]
    # Fixed signal config for this comparison
    sig_config = SignalConfig(base_val=25.0, std=0.5, anomaly_prob=0.02, magnitude=5.0)
    
    results = []
    
    # --- Z-Score Grid Search ---
    print(f"{'Detector':<10} | {'Param (Th/W)':<12} | {'F1-Score':<10} | {'Precision':<10} | {'Recall':<10} | {'Saving':<8}")
    print("-" * 75)
    
    for threshold in [2.5, 3.0, 4.0, 5.0]:
        for window in [20, 30, 50]:
            config = ZScoreConfig(window_size=window, threshold=threshold)
            m = run_experiment("ZScore", config, sig_config, seeds)
            results.append({"type": "ZScore", "config": asdict(config), "metrics": m})
            print(f"{'ZScore':<10} | {threshold:>4}/{window:<7} | {m['f1']:>10.4f} | {m['precision']:>10.4f} | {m['recall']:>10.4f} | {m['reduction']:>8.1%}")

    # --- EWMA Grid Search ---
    print("-" * 75)
    for threshold in [3.0, 4.0, 5.0, 6.0]:
        for alpha in [0.1, 0.2, 0.3]:
            config = EWMAConfig(alpha=alpha, threshold_mult=threshold, warmup_period=30)
            m = run_experiment("EWMA", config, sig_config, seeds)
            results.append({"type": "EWMA", "config": asdict(config), "metrics": m})
            print(f"{'EWMA':<10} | {threshold:>4}/{alpha:<7} | {m['f1']:>10.4f} | {m['precision']:>10.4f} | {m['recall']:>10.4f} | {m['reduction']:>8.1%}")

    # Save to report
    report = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "seeds": seeds,
            "signal_config": asdict(sig_config)
        },
        "results": results
    }
    
    report_path = "reports/EDGE_AI_VALIDATION.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)
    
    # Plotting: Communication Saving vs False Positive Rate (Subplots for clarity)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Z-Score Subplot
    z_results = [r for r in results if r["type"] == "ZScore"]
    z_fpr = [r["metrics"]["fpr"] * 100 for r in z_results]
    z_save = [r["metrics"]["reduction"] * 100 for r in z_results]
    best_z = max(z_results, key=lambda x: x["metrics"]["f1"])
    
    ax1.scatter(z_fpr, z_save, color='blue', alpha=0.6, s=100, label='Z-Score Configs')
    ax1.annotate(f"BEST (F1={best_z['metrics']['f1']:.2f})", 
                 (best_z['metrics']['fpr']*100, best_z['metrics']['reduction']*100),
                 textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold')
    ax1.set_title("Z-Score: Saving vs. FPR")
    ax1.set_xlabel("False Positive Rate (%)")
    ax1.set_ylabel("Communication Saving (%)")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # EWMA Subplot
    e_results = [r for r in results if r["type"] == "EWMA"]
    e_fpr = [r["metrics"]["fpr"] * 100 for r in e_results]
    e_save = [r["metrics"]["reduction"] * 100 for r in e_results]
    best_e = max(e_results, key=lambda x: x["metrics"]["f1"])
    
    ax2.scatter(e_fpr, e_save, color='green', alpha=0.6, s=100, label='EWMA Configs')
    ax2.annotate(f"BEST (F1={best_e['metrics']['f1']:.2f})", 
                 (best_e['metrics']['fpr']*100, best_e['metrics']['reduction']*100),
                 textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold')
    ax2.set_title("EWMA: Saving vs. FPR")
    ax2.set_xlabel("False Positive Rate (%)")
    ax2.set_ylabel("Communication Saving (%)")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    fig_path = "reports/figures/edge_ai_tradeoff.png"
    plt.savefig(fig_path)
    print(f"Refined trade-off plots saved to: {fig_path}")

    # Generate Markdown Summary
    md_path = "reports/EDGE_AI_SUMMARY.md"
    with open(md_path, "w") as f:
        f.write("# Edge AI Detector Cross-Validation Summary\n\n")
        f.write(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        f.write("## Experiment Configuration\n")
        f.write(f"- **Seeds:** `{seeds}`\n")
        f.write(f"- **Samples per run:** 2000\n")
        f.write(f"- **Total samples per config:** {len(seeds) * 2000}\n")
        f.write(f"- **Signal Config:** `base={sig_config.base_val}, std={sig_config.std}, anomaly_prob={sig_config.anomaly_prob}`\n\n")
        
        f.write("## Results Table\n\n")
        f.write("| Detector | Param (Th/W or Th/A) | F1-Score | Precision | Recall | FPR (%) | Byte Saving |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        
        for res in results:
            m = res["metrics"]
            p = res["config"]
            if res["type"] == "ZScore":
                param = f"{p['threshold']}/{p['window_size']}"
            else:
                param = f"{p['threshold_mult']}/{p['alpha']}"
            f.write(f"| {res['type']} | {param} | {m['f1']:.4f} | {m['precision']:.4f} | {m['recall']:.4f} | {m['fpr']*100:.2f}% | {m['reduction']:.1%} |\n")
        
        f.write("\n## Top Performers\n")
        best_z = max([r for r in results if r["type"] == "ZScore"], key=lambda x: x["metrics"]["f1"])
        best_e = max([r for r in results if r["type"] == "EWMA"], key=lambda x: x["metrics"]["f1"])
        
        f.write(f"- **Best ZScore:** Threshold={best_z['config']['threshold']}, Window={best_z['config']['window_size']} (F1={best_z['metrics']['f1']:.4f})\n")
        f.write(f"- **Best EWMA:** Threshold={best_e['config']['threshold_mult']}, Alpha={best_e['config']['alpha']} (F1={best_e['metrics']['f1']:.4f})\n")

    print(f"\nExperiment complete. Full report saved to: {report_path}")
    print(f"Human-readable summary saved to: {md_path}")

if __name__ == "__main__":
    cross_validate()
