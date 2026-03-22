import numpy as np
import matplotlib.pyplot as plt
from wsnsim.topology import RandomTopology, TopologyConfig
from wsnsim.common import Position

def main():
    config = TopologyConfig(area_width=100.0, area_height=100.0, num_nodes=20)
    range_m = 30.0
    
    # Seeds
    seed_a = 42
    seed_b = 2026
    
    # 1. Generate with seed_a
    rng1 = np.random.default_rng(seed_a)
    topo1 = RandomTopology(config, rng1)
    pos1 = topo1.generate()
    
    # 2. Generate with seed_a again
    rng2 = np.random.default_rng(seed_a)
    topo2 = RandomTopology(config, rng2)
    pos2 = topo2.generate()
    
    # 3. Generate with seed_b
    rng3 = np.random.default_rng(seed_b)
    topo3 = RandomTopology(config, rng3)
    pos3 = topo3.generate()
    
    # Verify exact match for 1 and 2
    for p1, p2 in zip(pos1, pos2):
        assert p1.x == p2.x and p1.y == p2.y
    
    # Plotting
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    topos = [
        (pos1, f"Seed: {seed_a} (Run 1)"),
        (pos2, f"Seed: {seed_a} (Run 2)"),
        (pos3, f"Seed: {seed_b}")
    ]
    
    for i, (positions, title) in enumerate(topos):
        ax = axes[i]
        G = topo1.to_graph(positions, range_m) # Use any topo instance to call to_graph
        
        # Get nodes and edges
        x = [p.x for p in positions]
        y = [p.y for p in positions]
        
        # Draw edges
        for u, v in G.edges():
            ax.plot([positions[u].x, positions[v].x], [positions[u].y, positions[v].y], 
                    color='gray', alpha=0.3, linestyle='-')
        
        # Draw nodes
        ax.scatter(x, y, s=50, c='blue', edgecolors='black', zorder=3)
        
        # Label nodes
        for idx, (px, py) in enumerate(zip(x, y)):
            ax.text(px+1, py+1, str(idx), fontsize=8)
            
        ax.set_title(title)
        ax.set_xlim(0, config.area_width)
        ax.set_ylim(0, config.area_height)
        ax.set_aspect('equal')
        ax.grid(True, linestyle=':', alpha=0.5)
        
        # Add connectivity metrics to title or text
        m = topo1.get_connectivity_metrics(positions, range_m)
        ax.text(5, 5, f"Connected: {m['is_connected']}\nReach: {m['sink_reachability']*100:.0f}%", 
                bbox=dict(facecolor='white', alpha=0.8))

    plt.tight_layout()
    output_path = "reports/figures/seed_reproducibility.png"
    plt.savefig(output_path, dpi=300)
    print(f"Seed reproducibility figure saved to {output_path}")

if __name__ == "__main__":
    main()
