import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple
from wsnsim.federated import FederatedNode, FederatedServer, FLConfig, FLCostAnalyzer

def run_experiment():
    print("Running Federated Learning Trade-off Experiment...")
    
    # --- Settings ---
    num_nodes = 20
    num_params = 10
    total_samples_per_node = 1000
    update_periods = [1, 10, 20, 50, 100, 250, 500] # x-axis
    
    rng = np.random.default_rng(42)
    # The "ground truth" model we want the network to learn
    w_true = rng.standard_normal(num_params).astype(np.float32)
    
    # Results storage
    results_bytes = []
    results_mse = []
    
    for up in update_periods:
        print(f"  Testing update_period = {up}...")
        
        # 1. Setup FL components
        config = FLConfig(num_parameters=num_params, samples_per_round=up, learning_rate=0.05)
        server = FederatedServer(total_nodes=num_nodes, config=config)
        nodes = [FederatedNode(node_id=i, rng=rng, config=config) for i in range(num_nodes)]
        
        # Communication Cost Tracker (Simplified model)
        # Centralized if up=1, otherwise FL
        analyzer = FLCostAnalyzer(config, num_nodes, avg_hops=2.0)
        
        # 2. Simulation Loop (Sequential for simplicity)
        rounds = total_samples_per_node // up
        for r in range(rounds):
            # Each node processes 'up' samples
            for node in nodes:
                # Synthetic data: y = w_true * x + noise
                for _ in range(up):
                    x = rng.standard_normal(num_params).astype(np.float32)
                    y = np.dot(w_true, x) + rng.normal(0, 0.1)
                    res = node.process_data(y)
                    
                    if res:
                        server.receive_update(res[0])
            
            # End of round: Global Aggregation and Sync
            global_w = server.aggregate()
            for node in nodes:
                node.set_weights(global_w)
        
        # 3. Final Evaluation
        # Validation set (100 fresh samples)
        val_data = []
        for _ in range(100):
            x = rng.standard_normal(num_params).astype(np.float32)
            y = np.dot(w_true, x)
            val_data.append((y, x))
            
        final_mse = server.evaluate(val_data)
        
        # Get communication cost estimate
        # (Using suppression_rate=0 for conservative estimate of bytes)
        cent, fl = analyzer.analyze(rounds, final_mse, suppression_rate=0.0)
        
        actual_bytes = cent.total_bytes if up == 1 else fl.total_bytes
        results_bytes.append(actual_bytes / 1024.0) # KB
        results_mse.append(final_mse)

    # --- Plotting ---
    fig, ax1 = plt.subplots(figsize=(10, 6))

    color_bytes = 'tab:blue'
    ax1.set_xlabel('Update Period (Samples per Round)')
    ax1.set_ylabel('Total Comm. Cost (KB)', color=color_bytes)
    ax1.plot(update_periods, results_bytes, marker='s', color=color_bytes, linewidth=2, label='Comm. Cost')
    ax1.tick_params(axis='y', labelcolor=color_bytes)
    ax1.grid(True, linestyle='--', alpha=0.6)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    color_mse = 'tab:red'
    ax2.set_ylabel('Final Global MSE (Lower is Better)', color=color_mse)
    ax2.plot(update_periods, results_mse, marker='o', color=color_mse, linewidth=2, label='Loss (MSE)')
    ax2.tick_params(axis='y', labelcolor=color_mse)
    ax2.set_yscale('log')

    plt.title(f'FL Trade-off: Communication Cost vs. Convergence ({num_nodes} Nodes)')
    fig.tight_layout()
    
    save_path = 'reports/figures/fl_update_period_tradeoff.png'
    plt.savefig(save_path, dpi=300)
    print(f"\nSuccess! Plot saved to: {save_path}")
    print(f"Centralized (up=1) Bytes: {results_bytes[0]:.2f} KB | MSE: {results_mse[0]:.6f}")
    print(f"FL (up=100) Bytes: {results_bytes[4]:.2f} KB | MSE: {results_mse[4]:.6f}")

if __name__ == "__main__":
    run_experiment()
