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
