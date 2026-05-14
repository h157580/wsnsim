# Project Evidence List

## 1. Core Functionality
- [x] **DES Kernel**: `tests/test_sim.py` (Stable ordering verified).
- [x] **Radio Channel**: `reports/CHANNEL_VALIDATION.md` (Path loss/Shadowing curves).
- [x] **Energy Model**: `tests/test_energy.py` (State-based tracking verified).

## 2. Intelligence & Optimization
- [x] **Edge AI Validation**: `reports/EDGE_AI_SUMMARY.md` (F1-score vs. Data Saving).
- [x] **Aggregation Performance**: `reports/AGGREGATION_PERFORMANCE.md`.
- [x] Pareto Framework: `reports/figures/wsn_pareto_plot.png`.
- [x] Case Study Demo: `reports/figures/case_study_pareto.png` (Forest Fire optimal point found).

## 3. Code Quality
- [x] **Test Suite**: 65 tests passing (checked via `pytest`).
- [x] **Typing**: PEP 484 compliance across `wsnsim/`.
- [x] **Config**: Frozen dataclasses in `wsnsim/common.py`.

## 4. Case Study Data
- [x] Raw Data: `reports/wsn_raw_sweep.csv`.
- [x] Config: `reports/optimization_config.json`.
