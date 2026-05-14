# Prompt Log

## [2026-03-02] Project Setup and DES EventScheduler
**Goal:** Create DES EventScheduler
**Tool:** Gemini CLI (all phases)
**What the AI proposed:**
- Initialized the project structure (`wsnsim/`, `tests/`, `reports/figures/`, `GEMINI.md`, `requirements.txt`).
- Set up a Python 3.11+ virtual environment.
- Designed and implemented a `heapq`-based `EventScheduler` with stable execution order (using sequence numbers) in `wsnsim/sim.py`.
- Implemented 5 `pytest` tests covering chronological execution, stable ordering, error handling, and cancellation in `tests/test_sim.py`.
- Created a `PROJECT_BRIEF.md` to define the project's scope, standards, and Definition of Done.

**What I accepted/changed:**
1. My system used Python 3.10 by default, changed to 3.11.
2. I had to ask explicitly to generate the `__lt__()` function for the `Event` class to ensure transparent stable ordering.

**Validation:** pytest 5/5 green (including `test_run_until`).

## [2026-03-02] Q&A Summary: wsnsim/sim.py
**Prompt:** Quiz me about the code you just wrote (5 questions).
**Outcome:**
1. **__lt__ with (time, seq):** Confirmed as the way to provide stable ordering.
2. **Equal Timestamps:** Tie-breaking is done based on the sequence number.
3. **cancel() strategy:** Used lazy deletion (flag) to maintain $O(1)$ and heap consistency.
4. **schedule() complexity:** $O(\log n)$ due to `heapq.heappush`.
5. **Missing sequence counter:** Would lead to non-determinism and `TypeError` on non-comparable callbacks.

## [2026-03-04] Radio Channel Model and PRR Calculations
**Goal:** Create module 'channel' (PRR calculations).
**Tool:** Gemini CLI + Gemini Pro.
**What the AI proposed:**
- `ChannelModel` with log-distance path loss, log-normal shadowing, and PRR calculation.
- Initial proposal had inconsistent units (dBm/mW mix).
- Unit tests covering monotonicity, reference distance, and reproducibility.
- Experiment script (`experiments/plot_prr_distance.py`) to visualize PRR(d) with different sigma values.
- Comprehensive documentation in `reports/CHANNEL_VALIDATION.md` including manual numerical validation points.

**What I accepted/changed:**
- Insisted on using meters (m) for distance and milliWatts (mW) for power to maintain project consistency.
- Corrected unit handling in `calculate_prr`.
- Updated experiments to support CLI-based table output as well as Matplotlib.

**Validation:** 
- `pytest tests/test_channel.py` is all green (7/7 tests passed).
- Manual validation against numerical points (PRR=0.0308 at 10m, -25dBm).


## [2026-03-07] Energy Model Refinement and Lifetime Analysis
**Goal:** Finalize `energy.py` and analyze WSN node lifetime.
**Tool:** Gemini CLI, Gemini Code Assist, Gemini AI Pro
**What the AI proposed:**
- Refactored `EnergyModel.update_state` to accurately calculate the "time of death" if a node runs out of energy mid-interval.
- Fixed a critical bug where the last time-slice before battery exhaustion was being lost in metrics.
- Implemented a formal `pytest` suite in `tests/test_energy.py` with 6 cases covering scenarios like wakeup costs, mid-interval death, and time-sum consistency.
- Created `experiments/plot_lifetime_dutycycle.py` to visualize the exponential impact of duty cycling on battery life.
- Using cross validation between AI tools, the update_state() function was fine tuned to evade the egde cases.
**What I accepted/changed:**
- Explicitly requested a "negative energy guard" and "sanity check" for total time consistency in the tests.
- Adjusted test assertions to use `pytest.approx` to handle floating-point precision issues in time-tracking.
- Verified unit conversions: mW for power, mJ for transitions, Joules for capacity.


**Validation:**
- `pytest tests/` (17/17 passed).
- Lifetime experiment confirmed ~5 years of operation at 0.1% duty cycle vs. ~4 days at 100%.
- Plot generated at `reports/figures/lifetime_vs_dutycycle.png`.

## [2026-03-10] MAC Protocol Implementation and Collision Analysis
**Goal:** Implement ALOHA MAC (send at will) & CSMA backoff (carrier sense + random backoff) modules. Provide the possibility to configure slot, cwmin, cwmax. Write deterministic tests with 2  node, verify & handle collisions. Document the seed for testing.
**Tool:** Gemini CLI, Gemini AI Pro
**What the AI proposed:**
- Refined `CsmaMac` in `wsnsim/mac.py` to include reliable ACK timeout and retransmission logic.
- Implemented a "Freeze" mechanism for CSMA/CA where the backoff counter pauses during channel activity.
- Using cross validation between AI tools
- Created a `DeterministicChannel` in `tests/test_mac.py` to strictly control transmission overlaps for validation.
- Developed three key test cases:
    - `test_pure_aloha_collision`: Confirmed nodes collide if they overlap by even a small margin.
    - `test_slotted_aloha_collision`: Confirmed nodes sync to slot boundaries, colliding only if they pick the same slot.
    - `test_csma_avoidance`: Verified that CSMA nodes detect a busy channel, freeze their counter, and wait for IDLE before transmitting.
- Produced a comparison table summarizing the trade-offs between ALOHA variants and CSMA/CA.

**What I accepted/changed:**
- Increased simulation time in `test_csma_avoidance` to account for long random backoff windows (Node 1 picked 12 slots).
- Verified that `waiting_for_ack` is correctly reset during retransmission attempts.
- Ensured unit consistency across all MAC protocols (seconds for slots/timeouts, mW for power).

**Validation:**
- `pytest tests/test_mac.py` (3/3 passed).
- Total project tests: 20/20 passed.
- Debug traces confirmed "Freeze" logic: Node 1 paused at T=0.002 and resumed only after Node 0 finished at T=0.005.

## [2026-03-20] Topology Generators and Spatial Optimization
**Goal:** Implement topology generators (Random, Grid, Cluster) with NetworkX visualization and optimized spatial graph generation.
**Tool:** Gemini CLI
**What the AI proposed:**
- Created `wsnsim/common.py` with a 2D `Position` dataclass.
- Implemented `RandomTopology`, `GridTopology`, and `ClusterTopology` in `wsnsim/topology.py`.
- Designed `generate()` as a pure method to eliminate mutable internal state.
- Added rich metadata (x, y, pos) to NetworkX nodes and implemented `save_visualization` for exporting topology PNGs.
- Created `tests/test_topology.py` covering reproducibility, connectivity, and distribution correctness.
- Added `experiments/generate_topology_samples.py` to verify visual output.

**What I accepted/changed:**
- Removed initial 3D support to simplify the model to a strictly 2D plane as per project requirements.
- Refactored `ClusterTopology` from a sequential head assignment to a stochastic one for more natural distributions.
- Resolved dependency issues (`typing_extensions`, `pytest`, `scipy`) in the local environment to support KDTree and type checking.
- Optimized `to_graph` using `scipy.spatial.KDTree` and `sparse_distance_matrix` to achieve $O(N \log N)$ performance and avoid redundant distance recomputations.
**Validation:**
- `pytest tests/test_topology.py` is all green (5/5 tests passed).
- Total project tests: 25/25 passed.
- Visual validation: Sample PNGs generated in `reports/figures/` (random, grid, cluster) confirmed correct spatial distribution and connectivity.

## [2026-03-21] Topology Connectivity and Visualization Refinement
**Goal:** Implement connectivity metrics, reproducibility verification, and enhanced visualization.
**Tool:** Gemini CLI
**What the AI proposed:**
- Added `get_connectivity_metrics()` to the `Topology` class to provide graph-theoretic analysis (Sink Reachability, Average Degree, Component Count).
- Refined `_create_plot` in `wsnsim/topology.py`:
    - Designated **Node 0** as the Sink (Red Square).
    - Added a **Legend** for sensors, sinks, and links.
    - Implemented a **10-meter grid/tick interval** using `MultipleLocator`.
    - Simplified node labels to show only IDs.
- Created `experiments/plot_seed_reproducibility.py` to verify that identical seeds produce identical $(x, y)$ coordinates and connectivity.
- Updated `tests/test_topology.py` with connectivity-specific assertions.
- Updated `PROJECT_BRIEF.md` to reflect new topology standards.

**What I accepted/changed:**
- Requested 10-meter grid intervals for better scale reference.
- Removed (x, y) coordinates from node labels to keep the plot clean.
- Fixed a `TypeError` regarding the `marker` argument in `nx.draw_networkx_nodes` by using `node_shape`.

**Validation:**
- `pytest tests/test_topology.py` (7/7 passed).
- Visual validation: `reports/figures/seed_reproducibility.png` confirms exact coordinate matching for identical seeds.
- Sample generation script updated with new legend and grid.

## [2026-03-22] Q&A Summary: wsnsim/topology.py
**Prompt:** Q&A session to confirm understanding of the topology module.
**Outcome (Completed):**
1. **Performance:** KDTree optimizes neighbor finding from $O(N^2)$ to $O(N \log N)$ for large networks.
2. **Connectivity:** Sink reachability is emphasized because it measures data delivery potential to the sink (node 0) rather than requiring every single node to be globally connected.
3. **Reproducibility:** Seeds ensure deterministic pseudo-random number generator (PRNG) states for consistent coordinate generation across runs.
4. **Architecture:** Returning Position objects instead of Node objects strictly separates the "where" (topology) from the "what" (simulation logic, MAC, energy), improving testability and code cleanliness.
5. **Visualization:** 10m grid allows quick visual verification that the communication range `range_m` aligns correctly on the topology plots.

## [2026-04-07] Reliability, ARQ and Energy Trade-off
**Goal:** Implement Link-Layer ARQ (ACK + Stop-and-Wait Retry) and analyze the energy cost of reliability.
**Tool:** Gemini CLI, Gemini AI Pro
**What the AI proposed:**
- Updated `Packet` in `common.py` with `is_ack` flag and sequence numbers.
- Refactored `BaseMac` in `mac.py` to handle:
    - **Automatic ACKs:** Sending small (40% duration) ACK packets after receiving data.
    - **Duplicate Filtering:** O(1) LRU-style cache using Python dicts to drop retransmitted data packets.
    - **Retroactive RX Energy:** Accounting for the physical reception time in the `EnergyModel`.
- Fixed `DeterministicChannel` in `tests/test_mac.py` to support real packet delivery and ACK turnaround.
- Developed `experiments/plot_pdr_energy_retry.py` for a parameter sweep over `max_retries`.

**What I accepted/changed:**
- Optimized duplicate cache from `list(set)` to `dict` for performance.
- Fixed a `ValueError: Time cannot move backwards` by adding a guard for overlapping receptions in the energy model.
- Adjusted ACK transmit power to 1mW (lower than data) to reflect lower interference impact.

**Validation:**
- `pytest tests/test_mac.py` (3/3 passed).
- Experiment confirmed: `Retries=1` increases PDR from 92% to 99% with a ~23% energy increase.
- Higher retry limits (8+) show diminishing returns and potential congestion, as PDR stabilized while energy continued to rise.
- Plot generated at `reports/figures/pdr_vs_energy_retry.png`.

## [2026-04-20] Clock Drift Simulation and Trilateration Localization
**Goal:** Implement clock drift modeling (ppm) and RSSI-based trilateration for node localization.
**Tool:** Gemini CLI, Gemini AI Pro
**What the AI proposed:**
- Created `wsnsim/sync_localization.py` with:
    - `SyncClock`: Simulates local node clocks with a constant ppm drift and offset.
    - `trilaterate()`: Least Squares (LS) based 2D position estimation using linearized equations.
    - `estimate_distance_from_rssi()`: Back-calculation of distance using the log-distance path loss model.
- Developed a comprehensive test suite in `tests/test_sync_localization.py` covering:
    - Ideal (zero noise) localization.
    - Standard 4dB shadowing noise impact.
    - **DOP (Dilution of Precision)** analysis: demonstrated that position error skyrockets when nodes are outside the anchor hull (up to 91m error with only 2dB noise).
    - Anchor count effect (averaging benefits of 10 vs 3 anchors).
- Created `experiments/plot_localization_error.py` to visualize the relationship between shadowing sigma and position error.

**What I accepted/changed:**
- Explicitly requested a ppm-based drift model.
- Insisted on a "deterministic first" verification before adding noise.
- Validated the "Jensen-inequality" effect: RSSI noise in dB domain leads to non-symmetric errors in the distance domain.

**Validation:**
- `pytest tests/test_sync_localization.py` (8/8 passed).
- Total project tests: 33/33 passed.
- Experiment plot confirmed that localization error is near-exponential with respect to shadowing sigma (dB).

## [2026-04-21] In-Network Data Aggregation and Robust Compression
**Goal:** Implement a modular data aggregation pipeline with Delta-encoding and robust tree-based weighting.
**Tool:** Gemini CLI, Gemini AI Pro 
**What the AI proposed:**
- Created `wsnsim/aggregation.py` with an abstract `AggregationStrategy` interface.
- Implemented `TreeDeltaAvgStrategy` featuring:
    - **Threshold-based Filtering:** Suppresses transmissions if the change is below a deadband (T).
    - **Weighted Average:** Ensures associativity in multi-hop trees by tracking sample counts.
    - **Periodic Reset:** Forces absolute values every $R$ transmissions to prevent cumulative drift.
- Integrated the pipeline into the routing layer via `AggregatingTreeRouting` in `wsnsim/routing.py`.
- Updated `Packet` in `wsnsim/common.py` with `is_absolute` and `sample_weight` fields.
- Developed `experiments/evaluate_routing_aggregation.py` to measure trade-offs between communication reduction and reconstruction error (MSE).
- Generated a formal report in `reports/AGGREGATION_PERFORMANCE.md`.

**What I accepted/changed:**
- Explicitly requested the **Threshold (T)** parameter to enhance energy savings.
- Identified and fixed a syntax error in `routing.py` caused by a corrupted class definition during merge.
- Added a **periodic reset** mechanism to handle potential packet loss drift in delta-encoding.
- Changed the random seed to **57** to verify consistency across different noise profiles.

**Validation:**
- `pytest tests/test_aggregation.py` (4/4 passed).
- Integration test: `evaluate_routing_aggregation.py` confirmed 96.8% traffic reduction with MSE < 0.02.
- Verified that `is_absolute` metadata allows the Sink to perfectly reset its baseline.
- Plot generated at `reports/figures/robust_aggregation_test.png`.

## [2026-04-26] WSN Security: Overhead Modeling and Replay Protection
**Goal:** Implement a lightweight security overhead model and nonce-based replay protection.
**Tool:** Gemini CLI
**What the AI proposed:**
- Updated `Packet` in `common.py` with `nonce` and `size_bytes` fields.
- Created `wsnsim/security.py` with a `SecurityModel` to handle signing/verification and track energy/latency/size overhead.
- Refactored `wsnsim/mac.py` to be "energy-aware":
    - Added guards to prevent TX/RX/ACK if the node is out of energy.
    - Integrated `consume_energy` to properly trigger the "death" state (SLEEP) during crypto operations.
- Enhanced `EnergyModel` with a `consume_energy` method for instantaneous CPU-bound consumption.
- Developed a three-tiered test suite in `tests/test_security.py` covering logic, MAC integration, and network-level replay.
- Created an abuse-case experiment (`experiments/plot_security_tradeoff.py`) with a `ReplayAttacker` node.

**What I accepted/changed:**
- Insisted on a generic overhead model (energy tax + size increase) rather than a specific crypto library.
- Simplified the abuse-case test to use `PureAlohaMac` for stability during multi-scene simulations.
- Refined the `ReplayAttacker` to bypass simple duplicate filters by modifying `packet_id`, highlighting the necessity of `nonce` protection.
- Fixed a bug where legitimate retransmissions were incorrectly incrementing the nonce.
- **Improved Energy Integrity:** Implemented explicit "death guards" in the MAC layer and `SecurityModel` to ensure nodes physically stop communicating when the battery is exhausted, even if triggered by crypto overhead.

**Validation:**
- `pytest tests/test_security.py` (3/3 passed).
- `pytest tests/test_mac.py` (3/3 passed).
- `pytest tests/test_energy.py` (6/6 passed).
- Experiment confirmed a **124.6% energy overhead** for security, while successfully preventing data integrity failures (5 packets processed vs 10 in unsecured mode).
- Plot generated at `reports/figures/security_tradeoff.png`.

## [2026-05-02] Edge AI: Anomaly Detection and Cross-Validation
**Goal:** Implement lightweight Edge AI (Z-Score, EWMA) for anomaly detection and perform cross-validation for parameter optimization.
**Tool:** Gemini CLI, Gemini AI Pro
**What the AI proposed:**
- Created `wsnsim/edge_ai.py` with:
    - **`ZScoreDetector`**: Sliding-window based detection with outlier rejection and standard deviation floor to prevent hyper-sensitivity.
    - **`EWMADetector`**: Recursive moving average with a configurable `warmup_period` to suppress false positives during initialization.
    - **`EdgeAIStrategy`**: An `AggregationStrategy` that integrates detectors with ground-truth performance tracking (TP/FP/TN/FN).
    - **`EdgeAIMetrics`**: Advanced tracking including **Byte Reduction** (accounting for 12-byte headers) and F1-Score.
- Developed a comprehensive test suite in `tests/test_edge_ai.py` (7/7 passed) covering:
    - Deterministic detector logic and warmup behavior.
    - Integration with `SignalGenerator` for statistical verification.
- Implemented `experiments/cross_validate_detectors.py` featuring:
    - **Grid Search**: Systematic evaluation of threshold, window, and alpha parameters.
    - **Statistical Robustness**: 5-seed averaging (10,000 samples per config).
    - **Automated Reporting**: Generation of `reports/EDGE_AI_VALIDATION.json` and a human-readable `reports/EDGE_AI_SUMMARY.md`.
    - **Visualization**: Trade-off analysis (Saving vs. FPR) with separate subplots for Z-Score and EWMA.

**What I accepted/changed:**
- Insisted on **Frozen Dataclasses** for all configurations (`SignalConfig`, `ZScoreConfig`, etc.) to ensure perfect reproducibility.
- Identified and fixed a hyper-sensitivity "trap" where zero-variance signals caused infinite Z-scores; added a `1e-3` floor to standard deviation.
- Refined the `EWMADetector` warmup logic to ensure exactly `N` training samples are processed before active detection.
- Requested separate subplots for trade-off visualization to clearly see the Pareto front for each algorithm.

**Validation:**
- `pytest tests/test_edge_ai.py` (7/7 passed).
- **Cross-Validation Result:** `EWMA (Th=6.0, Alpha=0.1)` achieved **F1=0.9922** and **98.0% byte reduction**.
- Reports and plots generated in `reports/` confirm the energy-saving potential of Edge AI.

## [2026-05-10] Design Space Exploration and Optimization Framework
**Goal:** Implement a comprehensive framework for parameter sweeps, multi-objective optimization (Pareto-front), and sensitivity analysis.
**Tool:** Gemini CLI, Gemini AI Pro
**What the AI proposed:**
- Created `wsnsim/optimization.py` featuring:
    - **`DesignSpace`**: Grid generation for parameter combinations with deterministic random sampling and a **`save_config`** method for JSON parameter dumps.
    - **`SweepRunner`**: Parallelized simulation execution using `ProcessPoolExecutor` with automated results aggregation across stochastic repetitions.
    - **`identify_pareto`**: Implementation of $\epsilon$-dominance (tolerance-based filtering) to identify robust multi-objective trade-offs.
    - **`calculate_sensitivity`**: Utility to quantify the local impact of parameters on target metrics (e.g., Energy vs. Duty Cycle).
- Developed `tests/test_optimization.py` with 5 cases verifying grid logic, sampling, Pareto filtering (strict and tolerant), and parallel execution.
- Created `experiments/wsn_optimization_demo.py`, a high-density (2500 runs) experiment visualizing the Energy vs. PDR Pareto-front with English localization and automated reporting.
- Enforced bit-for-bit reproducibility across runs by systematic seeding of all random components.

**What I accepted/changed:**
- Requested an explicit **aggregation step** before Pareto filtering to prevent "lucky seeds" from dominating the results.
- Insisted on **English localization** for all code, comments, and plots.
- Fine-tuned the **Pareto density** by adjusting the $\epsilon$-dominance threshold to achieve a targeted number of optimal points (~50).
- Fixed a non-determinism in the initial sampling logic by adding `random.seed(seed_base)` before selecting parameter combinations.
- Added a **`save_config`** feature to dump the experimental design space to `optimization_config.json`.
- Integrated **Sensitivity Analysis** into the demo to quantify the impact of TX Power vs. Duty Cycle on Energy.

**Validation:**
- `pytest tests/test_optimization.py` (5/5 passed).
- **Reproducibility Test:** Bit-for-bit identical results confirmed across two independent 2500-task runs (verified via log diff).
- Visualization at `reports/figures/wsn_pareto_plot.png` correctly illustrates the "knee" of the Energy-Reliability curve.
- **DoD Met:** Sweep + Pareto selection + Config dump + Reproducibility checklist completed.

## [2026-05-14] Project Finalization and Case Study Development
**Goal:** Finalize the wsnsim project, document a Forest Fire Case Study, and justify design points via Pareto optimality.
**Tool:** Gemini CLI
**What the AI proposed:**
- Developed `experiments/case_study_demo.py`: A high-fidelity DSE (Design Space Exploration) focused on a Forest Fire scenario.
- Implemented a physics-grounded **Energy Model** with Joules (J) units and hardware-specific constants (TX efficiency, base power).
- Identified the **Optimal Design Point** (11mW TX Power, 16.3% Duty Cycle) by applying safety constraints (PDR > 90%, Latency < 60s) to the Pareto front.
- Created a comprehensive **Evidence-Based Presentation** in `PRESENTATION.md` with integrated plots and figures.
- Standardized documentation: Finalized `README.md` (Quick Start, Modules, Reproducibility) and added `reports/CASE_STUDY_ANALYSIS.md`.
- Automated evaluation: Created `run_evaluation.sh` for one-command verification (tests + demo).
- Organized assets: Moved presentation-critical Pareto plots to `reports/figures/presentation/` and updated `.gitignore` to preserve them.

**What I accepted/changed:**
- Insisted on **English localization** for the final presentation and README.
- Corrected a binary incompatibility issue (Numpy/Pandas version mismatch) by removing redundant pandas dependencies in the demo.
- Added explicit **Joules [J]** units to all plots and documentation for scientific clarity.
- Refined the hardware recommendations to include specific, commercially available components (Nordic nRF52840, Saft batteries).

**Validation:**
- `pytest` (65/65 passed).
- **Bit-perfect Reproducibility:** Verified that the Case Study finds the exact same optimal point (11mW, 16.3% DC) across multiple runs.
- **One-Command Review:** `./run_evaluation.sh` successfully executes the entire quality gate and analysis pipeline.
- **Final Status:** Project meets all "Definition of Done" criteria.
