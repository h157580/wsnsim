# PROJECT BRIEF: Wireless Sensor Network (WSN) Simulator

## 1. Project Overview
A Discrete-Event Simulator (DES) for researching energy-efficient protocols, data aggregation, and Edge AI in Wireless Sensor Networks.

## 2. Radio Channel Model
Stochastic modeling of signal propagation and interference:
- **Log-Distance Path Loss**: Models signal attenuation over distance using the path loss exponent ($\eta$).
- **Log-Normal Shadowing**: Captures environmental variability using a Gaussian distribution in the dB domain ($\sigma$).
- **Packet Reception Ratio (PRR)**: Calculates delivery probability based on Signal-to-Noise Ratio (SNR) and modulation parameters.

## 3. MAC Layer Strategy
Selection of the MAC protocol impacts network throughput and energy efficiency:
- **Pure ALOHA**: Lowest complexity. Ideal for extremely sparse, low-duty-cycle networks where collisions are rare.
- **Slotted ALOHA**: Requires global time synchronization (e.g., via beacons). Doubles throughput (36.8%) compared to Pure ALOHA by forcing transmissions to slot boundaries.
- **CSMA/CA**: Highest efficiency in medium-to-high traffic. Uses Carrier Sense (CCA) and random backoff (Freeze mechanism) to actively avoid collisions at the cost of higher IDLE/RX energy consumption.
- **Reliability**: All MAC implementations include ACK/timeout logic and exponential backoff for retransmissions (up to `max_retries`).
    - **Stop-and-Wait ARQ**: Sender waits for a unicast ACK before proceeding; uses `ack_timeout` for collision detection.
    - **Duplicate Filtering**: Receivers maintain an O(1) LRU cache of `(src, packet_id)` to drop retransmissions while still re-sending ACKs.
    - **ACK Specs**: Control frames use reduced duration (40% of DATA) and lower transmit power (1mW) to minimize interference.
- **Validation Strategy**: Use `DeterministicChannel` for strict verification of collision overlaps and "Freeze" logic before transitioning to stochastic `ChannelModel` PRR analysis.

## 4. Topology & Spatial Modeling
The simulator supports varied deployment scenarios to evaluate protocol performance under different density and connectivity conditions:
- **Random Uniform**: Nodes distributed evenly across the area; useful for general performance baselines.
- **Grid**: Deterministic, regular placement; ideal for debugging and multi-hop routing verification.
- **Cluster**: Stochastic grouping around random cluster heads; simulates realistic scenarios like environmental monitoring in specific hotspots.
- **Connectivity Analysis**: NetworkX integration for graph-theoretic analysis. Supported metrics:
    - **Sink Reachability**: Fraction of nodes that can reach Node 0 (the central sink).
    - **Component Count**: Number of isolated node groups.
    - **Average Degree**: Average number of neighbors per node, indicating network density.
    - **Max Component Size**: Size of the largest connected sub-network.
- **Visualization**: Enhanced plotting with:
    - **Legend**: Clear identification of sensors, sink, and communication links.
    - **Sink Node Highlighting**: Node 0 is rendered as a distinct red square ('s').
    - **Reproducibility verification**: Script to visualize deterministic generation across different seeds.
- **Spatial Optimization**: Uses `scipy.spatial.KDTree` and `sparse_distance_matrix` to achieve $O(N \log N)$ neighbor lookups.

## 5. Clock Synchronization & Localization
Precise time and spatial awareness are critical for advanced WSN features:
- **SyncClock**: Simulates local oscillators with constant ppm (parts per million) drift and initial offsets.
- **RSSI Localization**: Estimates node positions using anchor nodes and trilateration. Uses Least Squares (LS) optimization for 2D coordinate discovery.
- **DOP Analysis**: Includes Dilution of Precision checks to quantify how anchor geometry impacts error sensitivity.

## 6. Data Aggregation
In-network processing to reduce data volume and radio usage:
- **Tree-based Aggregation**: Hierarchical flow where intermediate nodes combine data from children.
- **Delta Encoding**: Transmitting only changes between samples to minimize payload size.
- **Weight Awareness**: Propagates sample counts through the tree to ensure mathematically accurate weighted averages across multiple hops.

## 7. Security Model
Balanced approach between data protection and resource constraints:
- **Replay Protection**: Uses monotonic nonces (counters) to prevent malicious packet re-injection.
- **Overhead Analysis**: Explicitly models the energy cost of CPU-bound cryptographic operations and the increased radio cost due to security headers.
- **Integrity Guards**: MAC-level verification ensuring only authenticated packets are processed by higher layers.

## 8. Edge AI & Anomaly Detection
To maximize battery life, the simulator implements on-node intelligence to suppress redundant transmissions:
- **Detectors**:
    - **Z-Score**: Sliding-window based approach with standard deviation floor to prevent hyper-sensitivity on perfectly stable signals.
    - **EWMA**: Recursive exponential moving average. High memory efficiency and excellent performance on non-stationary signals. Uses a `warmup_period` to ensure stable statistics before active detection.
- **Metrics**:
    - **Byte-level Saving**: Calculates efficiency by accounting for both data payloads (float32) and protocol overhead (12-byte headers).
    - **F1-Score**: Harmonic mean of Precision and Recall, ensuring detectors are optimized for both reliability (catching anomalies) and efficiency (minimizing false positives).
- **Validation Strategy**: Use **Cross-Validation** across multiple seeds to identify the Pareto front between data saving and False Positive Rate (FPR).

## 9. Units
- **Time**: seconds (s) | **Energy**: Joules (J)
- **Distance**: meters (m) | **Power**: milliWatts (mW)

## 10. Coding Rules
- **Environment**: Python 3.11+
- **Typing**: Strict type hints (PEP 484) for all public interfaces.
- **Config**: Frozen `dataclasses` for all configuration/parameters.
- **RNG**: Components must accept a `numpy.random.Generator` instance (using `seed`) for isolated, reproducible randomness. Seed param for every RNG.
- **Quality**: `pytest` suite required for all modules; Google-style docstrings.

## 11. Federated Learning (FedAvg)
Distributed model training optimized for resource-constrained sensor nodes:
- **Memory-Efficient Training**: Uses **Online Learning** (incremental SGD) to update model weights sample-by-sample, eliminating the need for RAM-intensive data buffers.
- **Sparse Updates**: Implements threshold-based transmission suppression. A node only sends its local model to the Sink if the maximum change in weights exceeds the `update_threshold`, significantly saving radio energy.
- **Amnesia-Free Aggregation**: The `FederatedServer` accounts for silent nodes during FedAvg by incorporating the previous global weights for non-reporting nodes, ensuring stability and preventing "model hijacking" by a few active nodes.
- **Dynamic Cost Modeling**: The routing layer automatically adjusts packet size based on the model's parameter count (4 bytes per parameter for float32), allowing the `EnergyModel` to calculate realistic transmission costs.
- **Convergence Metrics**: Uses **Global MSE** (Mean Squared Error) on a separate validation set as a proxy for accuracy, enabling a quantitative analysis of the Energy vs. Quality trade-off.
- **Synchronization**: Supports a **Download Step** where nodes can be synchronized with the latest global model via downlink messages, preventing local model divergence.

## 12. Design Space Exploration (DSE) & Optimization
Systematic evaluation of protocol parameters to find optimal trade-offs:
- **Deterministic Sweeps**: All parameter sampling MUST be reproducible via a fixed seed set before grid selection.
- **Aggregation**: Multi-objective optimization (Pareto) MUST be performed on results averaged across repetitions to filter out stochastic noise.
- **Epsilon-Dominance**: Employs tolerant Pareto filtering to identify robust design regions rather than isolated, noise-sensitive optimums.
- **Traceability**: Automated configuration dump (JSON) of the design space is mandatory for every optimization run.
- **Sensitivity Metrics**: Quantifies local gradients to identify which parameters (e.g., Duty Cycle vs. TX Power) are the primary drivers of network performance.

## 13. Definition of Done
- [x] Discrete-Event Simulator (DES) kernel with stable event ordering.
- [x] Radio Channel Model (Path Loss, Shadowing, PRR).
- [x] Energy Model with hardware state tracking and "time-of-death" calculation.
- [x] MAC Layer (ALOHA, CSMA/CA) with collision modeling and ARQ.
- [x] Topology Generators (Random, Grid, Cluster) with optimized spatial graph generation.
- [x] In-Network Data Aggregation (Delta-encoding, Tree-based weighting).
- [x] Security Model (Overhead modeling, Replay protection).
- [x] Edge AI (Anomaly Detection, Cross-validation).
- [x] Federated Learning (FedAvg) with sparse model updates.
- [x] **DSE Framework**: Functional sweep runner, Pareto selection, and Sensitivity analysis.
- [x] **Full Reproducibility**: Bit-for-bit consistency verified across runs for all optimization tasks.
