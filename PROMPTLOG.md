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
**Tool:** Gemini CLI
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
