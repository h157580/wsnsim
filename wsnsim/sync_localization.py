from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import List, Optional
from .common import Position

class SyncClock:
    """Simulates a node's local clock with a constant drift in ppm.
    
    Attributes:
        drift_ppm: Drift in parts per million (e.g., 40.0).
        drift_factor: (1 + drift_ppm / 1e6).
    """
    def __init__(self, drift_ppm: float):
        self.drift_ppm = drift_ppm
        self.drift_factor = 1.0 + (drift_ppm / 1_000_000.0)
        self.offset = 0.0  # Initial phase offset

    def to_local_duration(self, global_duration: float) -> float:
        """Converts real-world duration to node-local duration."""
        return global_duration * self.drift_factor

    def to_global_duration(self, local_duration: float) -> float:
        """Converts node-local duration to real-world duration."""
        return local_duration / self.drift_factor

    def get_local_time(self, global_now: float) -> float:
        """Returns the current local clock reading for a given global time."""
        return global_now * self.drift_factor + self.offset

def trilaterate(anchor_positions: List[Position], distances: List[float]) -> Position:
    """Estimates position using Least Squares Trilateration.
    
    Solves (x - xi)^2 + (y - yi)^2 = di^2 by linearizing the equations.
    
    Args:
        anchor_positions: List of at least 3 anchor coordinates.
        distances: Measured distances to each anchor.
        
    Returns:
        Estimated Position.
        
    Raises:
        ValueError: If fewer than 3 anchors are provided or matrix is singular.
    """
    if len(anchor_positions) < 3:
        raise ValueError("At least 3 anchors are required for 2D trilateration.")
    
    n = len(anchor_positions)
    # A matrix and b vector for Ax = b
    # Linearized form (subtracting the n-th equation):
    # 2x(xn - xi) + 2y(yn - yi) = di^2 - dn^2 - xi^2 + xn^2 - yi^2 + yn^2
    
    A = []
    b = []
    
    xn, yn = anchor_positions[-1].x, anchor_positions[-1].y
    dn = distances[-1]
    
    for i in range(n - 1):
        xi, yi = anchor_positions[i].x, anchor_positions[i].y
        di = distances[i]
        
        A.append([2 * (xn - xi), 2 * (yn - yi)])
        
        val = (di**2 - dn**2) - (xi**2 - xn**2) - (yi**2 - yn**2)
        b.append(val)
        
    A = np.array(A)
    b = np.array(b)
    
    # Check for collinearity/numerical stability
    # If the matrix is near-singular, the estimation will be wild
    if np.linalg.matrix_rank(A) < 2:
        raise ValueError("Anchor geometry is collinear or degenerate; cannot determine 2D position.")

    # Solve using Least Squares
    x_est, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    
    return Position(x=float(x_est[0]), y=float(x_est[1]))

def estimate_distance_from_rssi(rssi_dbm: float, tx_power_dbm: float, 
                                 path_loss_exp: float, d0: float, l0: float) -> float:
    """Estimates distance from RSSI using the log-distance path loss model.
    
    Formula: d = d0 * 10^((Ptx - L0 - Prx) / (10 * n))
    
    Args:
        rssi_dbm: Received signal strength (Prx).
        tx_power_dbm: Transmit power (Ptx).
        path_loss_exp: Path loss exponent (n).
        d0: Reference distance (m).
        l0: Path loss at reference distance (dB).
    """
    return d0 * 10**((tx_power_dbm - l0 - rssi_dbm) / (10 * path_loss_exp))
