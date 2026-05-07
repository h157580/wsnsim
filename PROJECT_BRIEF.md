# PROJECT BRIEF: wsnsim

## 1. Project Goal
Develop a high-fidelity, discrete-event simulator in Python for research into Wireless Sensor Network (WSN) protocols. The simulator prioritizes reproducibility, modularity, and precise energy modeling for resource-constrained environments.

## 2. Modules
- **sim**: Core DES engine (Event, Queue, Scheduler).
- **node**: Orchestrator composing hardware/protocol modules into a single entity.
- **application**: Generates traffic patterns (CBR, Poisson, Event-driven).
- **phy/channel**: Signal propagation, interference, and hardware state transitions.
- **energy**: Battery modeling and consumption tracking (J = mW/1000 * s).
- **mac**: ALOHA, CSMA/CA with exponential backoff.
- **routing**: flooding + tree routing.
- **topology**: Deployment (Random, Grid, Cluster) and graph-based analysis.
- **sync_localization**: Clock drift modeling and RSSI-based trilateration.
- **aggregation**: In-network data aggregation pipeline (e.g., delta-encoding).
- **federated**: Federated Learning (FedAvg) implementation with memory-efficient online training.
- **security**: Lightweight security overhead modeling and replay protection.
- **edge_ai**: Lightweight anomaly detection (Z-Score, EWMA) and data reduction strategies.
- **common**: Shared types (Position) and utility functions.

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
- **Localization**:
    - **RSSI-based Distance Estimation**: Back-calculates distance using the log-distance path loss model.
    - **Trilateration**: Least Squares (LS) based 2D position estimation using linearized equations from anchors.
    - **DOP Analysis**: Modeling the Dilution of Precision to highlight how anchor geometry impacts accuracy.

## 6. In-Network Data Aggregation
Reduces traffic volume by combining data from multiple nodes along the routing tree:
- **Weighted Averaging**: Ensures mathematical associativity in multi-hop trees via `sample_weight`.
- **Delta-encoding**: Transmits only the difference from the last reported value.
- **Threshold-based Suppression**: Discards updates if the change is below a deadband value ($T$).
- **Periodic Reset**: Sends absolute values every $R$ transmissions to prevent cumulative drift.

## 7. WSN Security & Overhead
Provides a realistic model of security costs in resource-constrained networks:
- **Overhead Model**: Accounts for CPU energy tax (crypto operations) and packet size increase (signatures, nonces).
- **Replay Protection**: Uses strictly increasing nonces to prevent attackers from re-injecting valid historical packets.
- **Energy Integrity**: "Death guards" ensure that nodes stop all physical activity when the battery is exhausted, preventing "zombie" states caused by heavy crypto overhead.

## 8. Edge AI & Data Reduction
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

## 11. Definition of Done
- Green `pytest` suite with >80% coverage.
- Google-style docstrings and type-annotated parameters.
- Updated `PROMPTLOG.md` for every major feature/fix.

## 12. Known Architectural Decisions
- **Event Cancellation**: Uses a lazy-deletion flag ($O(1)$) rather than heap removal, ensuring $O(1)$ cancellation vs. $O(n)$ search.
- **PRR Modeling**: Uses a continuous BER-based mapping (sigmoid-like) rather than a binary step function, allowing for more realistic "grey zones" in communication.
- **Energy Tracking**: Stores cumulative energy consumed and time-in-state rather than calculating instantaneous power.
    - **Retroactive RX Accounting**: MAC layer accounts for the physical reception duration by updating the `EnergyModel` state from the packet's end-time back to its start-time, ensuring "Listening" vs. "Receiving" precision.
- **MAC Backoff**: `CsmaMac` implements a "freeze" mechanism where the backoff counter only decrements when the channel is idle, preventing unfairness in high-traffic scenarios.
- **Reliability Trade-off**: Empirical analysis confirms that `max_retries=1-3` provides the optimal balance (PDR > 99%) for most scenarios, while higher values lead to diminishing returns and congestion.
- **Spatial Optimization**: Graph generation from positions uses `scipy.spatial.KDTree` and `sparse_distance_matrix` to achieve $O(N \log N)$ neighbor lookups.
- **Pure Generation**: Topology generators are implemented as pure methods (`generate() -> List[Position]`) without internal state.
- **2D Plane Constraint**: All spatial calculations are currently restricted to the 2D plane ($x, y$).
- **Routing Next Hop**: Routing protocols explicitly set `packet.next_hop` before passing the packet down to the MAC layer. This determines whether the transmission is a unicast (expecting an ACK) or a broadcast (no ACK).
- **Flooding Cache**: `FloodingRouting` uses a predictable FIFO queue combined with a Set for $O(1)$ lookups to prevent broadcast storms of recently seen packets.

## 13. Federated Learning (FedAvg)
Distributed model training optimized for resource-constrained sensor nodes:
- **Memory-Efficient Training**: Uses **Online Learning** (incremental SGD) to update model weights sample-by-sample, eliminating the need for RAM-intensive data buffers.
- **Sparse Updates**: Implements threshold-based transmission suppression. A node only sends its local model to the Sink if the maximum change in weights exceeds the `update_threshold`, significantly saving radio energy.
- **Amnesia-Free Aggregation**: The `FederatedServer` accounts for silent nodes during FedAvg by incorporating the previous global weights for non-reporting nodes, ensuring stability and preventing "model hijacking" by a few active nodes.
- **Dynamic Cost Modeling**: The routing layer automatically adjusts packet size based on the model's parameter count (4 bytes per parameter for float32), allowing the `EnergyModel` to calculate realistic transmission costs.
- **Convergence Metrics**: Uses **Global MSE** (Mean Squared Error) on a separate validation set as a proxy for accuracy, enabling a quantitative analysis of the Energy vs. Quality trade-off.
- **Synchronization**: Supports a **Download Step** where nodes can be synchronized with the latest global model via downlink messages, preventing local model divergence.
