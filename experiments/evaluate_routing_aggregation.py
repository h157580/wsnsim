import numpy as np
import matplotlib.pyplot as plt
from wsnsim.common import Packet
from wsnsim.routing import AggregatingTreeRouting
from wsnsim.aggregation import PassthroughStrategy, TreeDeltaAvgStrategy
from typing import List

def generate_sensor_data(n_samples: int = 1000, noise_std: float = 0.05) -> np.ndarray:
    """Generate a synthetic sensor signal."""
    t = np.linspace(0, 4 * np.pi, n_samples)
    signal = np.sin(t) + 0.5 * t / (4 * np.pi)
    noise = np.random.normal(0, noise_std, n_samples)
    return signal + noise

def simulate_routing_aggregation(data: np.ndarray, router: AggregatingTreeRouting) -> List[Packet]:
    """Simulate packets passing through an aggregating router."""
    captured_packets = []
    
    for i, val in enumerate(data):
        pkt = Packet(src=2, dest=0, payload=val, packet_id=i)
        next_hop = router.forward(pkt)
        
        if next_hop is not None:
            # We store a copy of the packet as it was forwarded (including new metadata)
            captured_packets.append(Packet(
                src=pkt.src, dest=pkt.dest, 
                payload=pkt.payload, packet_id=pkt.packet_id,
                is_absolute=pkt.is_absolute,
                sample_weight=pkt.sample_weight
            ))
            
    return captured_packets

def reconstruct_from_packets(n_samples: int, packets: List[Packet]) -> np.ndarray:
    """Reconstruct signal from received packets using is_absolute flag."""
    reconstructed = np.zeros(n_samples)
    current_value = 0.0
    pkt_idx = 0
    
    for i in range(n_samples):
        if pkt_idx < len(packets) and packets[pkt_idx].packet_id == i:
            pkt = packets[pkt_idx]
            payload = float(pkt.payload)
            
            if pkt.is_absolute:
                current_value = payload
            else:
                current_value += payload
                
            pkt_idx += 1
        reconstructed[i] = current_value
        
    return reconstructed

def evaluate():
    np.random.seed(57)
    n_samples = 1000
    ground_truth = generate_sensor_data(n_samples)
    
    # Scenarios to compare
    scenarios = [
        ("Baseline (No Aggregation)", AggregatingTreeRouting(1, parent_id=0, strategy=PassthroughStrategy())),
        ("Aggregated (N=5, T=0.2, R=10)", AggregatingTreeRouting(1, parent_id=0, strategy=TreeDeltaAvgStrategy(5, 0.2, refresh_interval=10))),
        ("Aggregated (N=10, T=0.4, R=5)", AggregatingTreeRouting(1, parent_id=0, strategy=TreeDeltaAvgStrategy(10, 0.4, refresh_interval=5))),
    ]
    
    print(f"{'Scenario':<30} | {'Packets':<8} | {'Reduction':<10} | {'MSE':<10}")
    print("-" * 75)
    
    plt.figure(figsize=(12, 7))
    plt.plot(ground_truth, label="Ground Truth", alpha=0.3, color='gray')

    for name, router in scenarios:
        forwarded_packets = simulate_routing_aggregation(ground_truth, router)
        reconstructed = reconstruct_from_packets(n_samples, forwarded_packets)
        
        count = len(forwarded_packets)
        reduction = 1.0 - (count / n_samples)
        mse = np.mean((ground_truth - reconstructed)**2)
        
        # Count how many were absolute vs delta
        abs_count = sum(1 for p in forwarded_packets if p.is_absolute)
        delta_count = count - abs_count
        
        print(f"{name:<30} | {count:<8} | {reduction:>9.1%} | {mse:>10.5f} (Abs: {abs_count}, Delta: {delta_count})")
        
        if name != "Baseline (No Aggregation)":
            plt.plot(reconstructed, label=f"{name} (MSE={mse:.3f})")

    plt.title("Robust Routing & Aggregation: Multi-hop weighting and Periodic Refresh")
    plt.xlabel("Sample Index")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True, alpha=0.2)
    
    output_path = "reports/figures/robust_aggregation_test.png"
    plt.savefig(output_path)
    print(f"\nRobust evaluation complete. Plot saved to: {output_path}")

if __name__ == "__main__":
    evaluate()
