from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Any, Optional, Tuple

class AggregationStrategy(ABC):
    """Abstract base class for data aggregation and compression strategies.
    
    Note on Associativity:
        To ensure tree-independence, we use weighted averages. 
        Each aggregated value carries a 'sample_weight' (number of raw samples).
    """
    
    @abstractmethod
    def process_data(self, value: float, weight: int = 1) -> Optional[Tuple[Any, int, bool]]:
        """Process a new data point.
        
        Args:
            value: The numerical data (raw sample or weighted average).
            weight: The number of raw samples this value represents.
            
        Returns:
            A tuple of (payload, total_weight, is_absolute) if sending, else None.
        """
        pass

    @abstractmethod
    def reset(self):
        """Reset the internal buffer."""
        pass

class PassthroughStrategy(AggregationStrategy):
    """Raw data transmission: forwards every data point immediately as absolute."""
    
    def process_data(self, value: float, weight: int = 1) -> Optional[Tuple[Any, int, bool]]:
        return (value, weight, True)

    def reset(self):
        pass

class TreeDeltaAvgStrategy(AggregationStrategy):
    """Robust Tree-based Average + Delta-encoding.
    
    Features:
    - Weighted Average: Ensures associativity across multiple hops.
    - Delta-encoding: Sends difference from last transmitted value.
    - Threshold: Suppresses insignificant changes.
    - Periodic Reset: Sends absolute value every K transmissions to prevent drift.
    """
    
    def __init__(self, window_size: int = 5, threshold: float = 0.0, refresh_interval: int = 10):
        """
        Args:
            window_size: Total weight (samples) to collect before aggregating.
            threshold: Minimum absolute change required to trigger a transmission.
            refresh_interval: Send absolute value every K transmissions to reset drift.
        """
        self.window_size = window_size
        self.threshold = threshold
        self.refresh_interval = refresh_interval
        
        self.weighted_sum: float = 0.0
        self.total_weight: int = 0
        self.last_sent_avg: float = 0.0
        self.tx_count: int = 0
        self.is_first_transmission: bool = True

    def process_data(self, value: float, weight: int = 1) -> Optional[Tuple[Any, int, bool]]:
        # Calculate weighted sum for true associativity
        self.weighted_sum += value * weight
        self.total_weight += weight
        
        if self.total_weight >= self.window_size:
            current_avg = self.weighted_sum / self.total_weight
            output_weight = self.total_weight
            
            # Decide if we should send an absolute refresh
            is_absolute = self.is_first_transmission or (self.tx_count % self.refresh_interval == 0)
            
            if is_absolute:
                payload = current_avg
                should_send = True
            else:
                delta = current_avg - self.last_sent_avg
                payload = delta
                should_send = abs(delta) >= self.threshold

            if should_send:
                self.last_sent_avg = current_avg
                self.tx_count += 1
                self.is_first_transmission = False
                self.reset()
                return (payload, output_weight, is_absolute)
            else:
                # Suppressed by threshold, but we still clear the window
                self.reset()
                return None
            
        return None

    def reset(self):
        """Clear the temporary buffer/weighted sum."""
        self.weighted_sum = 0.0
        self.total_weight = 0
