from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class Position:
    """Represents a 2D coordinate in the network.
    
    All units are in meters (m).
    """
    x: float
    y: float

    def distance_to(self, other: Position) -> float:
        """Calculate Euclidean distance to another position."""
        return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5

@dataclass
class Packet:
    """Standard packet structure for routing and MAC layers."""
    src: int
    dest: int
    payload: Any
    packet_id: int
    ttl: int = 64
    next_hop: int = -1  # -1 for broadcast
    hop_count: int = 0
