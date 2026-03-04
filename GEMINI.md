# wsnsim: Wireless Sensor Network Simulator

Python 3.11+ Discrete-Event Simulator (DES) for WSN research.

## Architecture
- **sim.py**: `EventScheduler` (heapq-based, stable ordering with `sequence_number`).
- **channel.py**: `ChannelModel` (log-distance path loss, PRR).
- **energy.py**: `EnergyModel` (TX/RX/idle/sleep, Joules).
- **mac.py**: CSMA/CA with exponential backoff.
- **routing.py**: flooding + tree routing.

## Technical Standards
- **Units**: time=s, energy=J, distance=m, power=mW.
- **Typing**: Strict type hints (PEP 484) for all public interfaces.
- **Config**: Frozen `dataclasses` for all configuration/parameters.
- **Reproducibility**: Components must accept a `numpy.random.Generator` instance (seed-based).
- **Quality**: `pytest` suite required for all modules; Google-style docstrings.
- **Documentation**: Maintain `PROMPTLOG.md` for every major feature/fix.
