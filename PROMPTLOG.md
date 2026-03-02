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
