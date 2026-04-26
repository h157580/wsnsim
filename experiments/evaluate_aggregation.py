import numpy as np
import matplotlib.pyplot as plt
from wsnsim.aggregation import PassthroughStrategy, TreeDeltaAvgStrategy
from typing import List, Tuple, Optional

def generate_sensor_data(n_samples: int = 1000, noise_std: float = 0.05) -> np.ndarray:
    """Generate a synthetic sensor signal (sine wave + trend + noise)."""
    t = np.linspace(0, 4 * np.pi, n_samples)
    signal = np.sin(t) + 0.5 * t / (4 * np.pi) # Sine + slight upward trend
    noise = np.random.normal(0, noise_std, n_samples)
    return signal + noise

def run_experiment(data: np.ndarray, strategy: any) -> Tuple[List[Tuple[int, float]], int]:
    """Simulate data transmission using a strategy.
    
    Returns:
        A list of (timestamp, payload) pairs and the total packet count.
    """
    transmissions = []
    packet_count = 0
    
    for i, val in enumerate(data):
        result = strategy.process_data(val)
        if result is not None:
            transmissions.append((i, result))
            packet_count += 1
            
    return transmissions, packet_count

def reconstruct_signal(n_samples: int, transmissions: List[Tuple[int, float]], is_delta: bool = True) -> np.ndarray:
    """Reconstruct the signal at the sink using Zero-Order Hold."""
    reconstructed = np.zeros(n_samples)
    current_value = 0.0
    tx_idx = 0
    
    # Handle the very first packet (it's always absolute in our TreeDeltaAvgStrategy)
    if not transmissions:
        return reconstructed

    for i in range(n_samples):
        if tx_idx < len(transmissions) and transmissions[tx_idx][0] == i:
            tx_time, payload = transmissions[tx_idx]
            if is_delta:
                # Our implementation: first is absolute, rest are deltas
                if tx_idx == 0:
                    current_value = payload
                else:
                    current_value += payload
            else:
                current_value = payload
            tx_idx += 1
        
        reconstructed[i] = current_value
        
    return reconstructed

def evaluate():
    np.random.seed(57)
    n_samples = 1000

    ground_truth = generate_sensor_data(n_samples)
    
    configs = [
        ("Passthrough", PassthroughStrategy(), False),
        ("DeltaAvg (N=5, T=0)", TreeDeltaAvgStrategy(window_size=5, threshold=0.0), True),
        ("DeltaAvg (N=10, T=0)", TreeDeltaAvgStrategy(window_size=10, threshold=0.0), True),
        ("DeltaAvg (N=5, T=0.2)", TreeDeltaAvgStrategy(window_size=5, threshold=0.2), True),
        ("DeltaAvg (N=10, T=0.5)", TreeDeltaAvgStrategy(window_size=10, threshold=0.5), True),
    ]
    
    print(f"{'Strategy':<25} | {'Packets':<8} | {'Reduction':<10} | {'MSE':<10}")
    print("-" * 65)
    
    plt.figure(figsize=(12, 8))
    plt.plot(ground_truth, label="Ground Truth (Sensor)", alpha=0.3, color='gray', linestyle='--')

    for name, strategy, is_delta in configs:
        txs, count = run_experiment(ground_truth, strategy)
        reconstructed = reconstruct_signal(n_samples, txs, is_delta=is_delta)
        
        mse = np.mean((ground_truth - reconstructed)**2)
        reduction = 1.0 - (count / n_samples)
        
        print(f"{name:<25} | {count:<8} | {reduction:>9.1%} | {mse:>10.5f}")
        
        if name != "Passthrough":
            plt.plot(reconstructed, label=f"{name} (MSE={mse:.3f})")

    plt.title("WSN Data Aggregation: Reconstruction Accuracy vs. Compression")
    plt.xlabel("Time Step")
    plt.ylabel("Sensor Value")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    output_path = "reports/figures/aggregation_comparison.png"
    plt.savefig(output_path)
    print(f"\nPlot saved to: {output_path}")

if __name__ == "__main__":
    evaluate()
