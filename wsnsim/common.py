from __future__ import annotations
from dataclasses import dataclass

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
