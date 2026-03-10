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
