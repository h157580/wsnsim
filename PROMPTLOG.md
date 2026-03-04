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
