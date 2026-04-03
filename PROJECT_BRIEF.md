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
- **common**: Shared types (Position) and utility functions.

## 3. MAC Layer Strategy
Selection of the MAC protocol impacts network throughput and energy efficiency:
- **Pure ALOHA**: Lowest complexity. Ideal for extremely sparse, low-duty-cycle networks where collisions are rare.
- **Slotted ALOHA**: Requires global time synchronization (e.g., via beacons). Doubles throughput (36.8%) compared to Pure ALOHA by forcing transmissions to slot boundaries.
- **CSMA/CA**: Highest efficiency in medium-to-high traffic. Uses Carrier Sense (CCA) and random backoff (Freeze mechanism) to actively avoid collisions at the cost of higher IDLE/RX energy consumption.
- **Reliability**: All MAC implementations include ACK/timeout logic and exponential backoff for retransmissions (up to `max_retries`).
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

## 5. Units
- **Time**: seconds (s) | **Energy**: Joules (J)
- **Distance**: meters (m) | **Power**: milliWatts (mW)

## 6. Coding Rules
- **Environment**: Python 3.11+
- **Typing**: Strict type hints (PEP 484) for all public interfaces.
- **Config**: Frozen `dataclasses` for all configuration/parameters.
- **RNG**: Components must accept a `numpy.random.Generator` instance (using `seed`) for isolated, reproducible randomness. Seed param for every RNG.
- **Quality**: `pytest` suite required for all modules; Google-style docstrings.

## 7. Definition of Done
- Green `pytest` suite with >80% coverage.
- Google-style docstrings and type-annotated parameters.
- Updated `PROMPTLOG.md` for every major feature/fix.

## 8. Known Architectural Decisions
- **Event Cancellation**: Uses a lazy-deletion flag (flagging as cancelled) rather than heap removal, ensuring $O(1)$ cancellation vs. $O(n)$ search.
- **PRR Modeling**: Uses a continuous BER-based mapping (sigmoid-like) rather than a binary step function, allowing for more realistic "grey zones" in communication.
- **Energy Tracking**: Stores cumulative energy consumed and time-in-state rather than calculating instantaneous power, ensuring precision and handling "time of death" mid-interval.
- **MAC Backoff**: `CsmaMac` implements a "freeze" mechanism where the backoff counter only decrements when the channel is idle, preventing unfairness in high-traffic scenarios.
- **Spatial Optimization**: Graph generation from positions uses `scipy.spatial.KDTree` and `sparse_distance_matrix` to achieve $O(N \log N)$ neighbor lookups, avoiding $O(N^2)$ brute-force distance checks for large networks.
- **Pure Generation**: Topology generators are implemented as pure methods (`generate() -> List[Position]`) without internal state, ensuring that the same configuration can be used to generate multiple realizations if needed, and simplifying testing/verification.
- **2D Plane Constraint**: All spatial calculations are currently restricted to the 2D plane ($x, y$) for performance and simplicity in basic research scenarios.
- **Routing Next Hop**: Routing protocols explicitly set `packet.next_hop` before passing the packet down to the MAC layer. This determines whether the transmission is a unicast (expecting an ACK) or a broadcast (no ACK).
- **Flooding Cache**: `FloodingRouting` uses a predictable FIFO queue combined with a Set for $O(1)$ lookups to prevent broadcast storms of recently seen packets.
