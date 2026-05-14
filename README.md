# wsnsim - Wireless Sensor Network Simulator

## Quick Start
```bash
# Setup environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run quality gate (65 tests)
pytest -q

# Run the Forest Fire Case Study (Pareto Optimization)
export PYTHONPATH=$PYTHONPATH:.
python3 experiments/case_study_demo.py
```

## What are we simulating?
- **Scenario:** Forest Fire Detection. A dense network of sensors monitoring temperature and gas spikes in a high-shadowing environment (foliage).
- **Network:** Cluster-based topology with multi-hop tree routing to a central Sink.
- **Goal:** Multi-objective optimization to find the best balance between battery life and safety.
- **Metrics:** 
    - **PDR (Packet Reception Ratio):** Reliability of alert delivery.
    - **Latency:** Time-to-report for critical fire events.
    - **Energy (J):** Total consumption per operational hour.
    - **Lifetime:** Estimated node longevity based on Li-SOCl2 battery models.

## Modules
- `wsnsim/sim.py`: DES engine (Stable heapq-based event scheduler).
- `wsnsim/channel.py`: Radio model (Log-distance Path Loss + Shadowing + PRR).
- `wsnsim/energy.py`: Energy state machine (TX/RX/Idle/Sleep tracking).
- `wsnsim/mac.py`: MAC layer (CSMA/CA with exponential backoff).
- `wsnsim/routing.py`: Network layer (Flooding and Hierarchical Tree).
- `wsnsim/edge_ai.py`: Intelligence (On-node Z-Score/EWMA anomaly detection).
- `wsnsim/optimization.py`: DSE Engine (Pareto front identification & Sensitivity analysis).

## Reproducibility
- **Seed Handling:** Every component accepts a `numpy.random.Generator` instance. All experiments use fixed seed sequences.
- **Config Dump:** Simulation parameters are automatically exported to `reports/optimization_config.json`.
- **Output Files:** Results are saved to `reports/` (CSV) and visualizations to `reports/figures/presentation/` (PNG).
