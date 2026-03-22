import numpy as np
import os
from wsnsim.topology import RandomTopology, GridTopology, ClusterTopology, TopologyConfig, ClusterTopologyConfig

def main():
    # Ensure output directory exists
    out_dir = "reports/figures"
    os.makedirs(out_dir, exist_ok=True)
    
    rng = np.random.default_rng(42)
    base_config = TopologyConfig(area_width=100.0, area_height=100.0, num_nodes=50)
    range_m = 25.0
    
    # 1. Random Topology
    print("Generating Random Topology...")
    rt = RandomTopology(base_config, rng)
    pos_r = rt.generate()
    rt.save_visualization(pos_r, f"{out_dir}/topo_random.png", range_m=range_m)
    
    # 2. Grid Topology
    print("Generating Grid Topology...")
    gt = GridTopology(base_config, rng)
    pos_g = gt.generate()
    gt.save_visualization(pos_g, f"{out_dir}/topo_grid.png", range_m=range_m)
    
    # 3. Cluster Topology
    print("Generating Cluster Topology...")
    ct_config = ClusterTopologyConfig(area_width=100.0, area_height=100.0, num_nodes=50, num_clusters=4, cluster_std=8.0)
    ct = ClusterTopology(ct_config, rng)
    pos_c = ct.generate()
    ct.save_visualization(pos_c, f"{out_dir}/topo_cluster.png", range_m=range_m)
    
    print(f"Done! Check the files in {out_dir}/")

if __name__ == "__main__":
    main()
