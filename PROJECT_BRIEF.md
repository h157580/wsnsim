# PROJECT BRIEF: wsnsim

## 1. Project Goal
Develop a high-fidelity, discrete-event simulator in Python for research into Wireless Sensor Network (WSN) protocols. The simulator prioritizes reproducibility, modularity, and precise energy modeling for resource-constrained environments.

## 2. Modules
- **sim**: Core DES engine (Event, Queue, Scheduler).
- **node**: Orchestrator composing hardware/protocol modules into a single entity.
- **application**: Generates traffic patterns (CBR, Poisson, Event-driven).
- **phy/channel**: Signal propagation, interference, and hardware state transitions.
- **energy**: Battery modeling and consumption tracking (J = mW/1000 * s).
- **mac/routing**: Medium access (CSMA/TDMA) and multi-hop pathfinding.
- **topology**: Deployment (Random, Grid) and mobility management.
- **metrics/common**: Performance analysis and shared types (Packet, Position).

## 3. Units
- **Time**: seconds (s) | **Energy**: Joules (J)
- **Distance**: meters (m) | **Power**: milliWatts (mW)

## 4. Coding Rules
- **Environment**: Python 3.11+
- **Typing**: Strict type hints (PEP 484) for all public interfaces.
- **Config**: Frozen `dataclasses` for all configuration/parameters.
- **RNG**: Components must accept a `numpy.random.Generator` instance (using `seed`) for isolated, reproducible randomness.

## 5. Definition of Done
- Green `pytest` suite with >80% coverage.
- Google-style docstrings and type-annotated parameters.
- Updated `PROMPTLOG.md` for every major feature/fix.
