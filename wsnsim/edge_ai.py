from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, TYPE_CHECKING, Protocol
from abc import ABC, abstractmethod
from .aggregation import AggregationStrategy

if TYPE_CHECKING:
    from numpy.random import Generator

@dataclass(frozen=True)
class SignalConfig:
    """Configuration for synthetic signal generation."""
    base_val: float = 25.0
    std: float = 0.5
    anomaly_prob: float = 0.01
    magnitude: float = 5.0

@dataclass
class EdgeAIMetrics:
    """Tracks the performance and efficiency of Edge AI strategies."""
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0
    total_samples: int = 0
    transmitted_packets: int = 0
    packet_header_bytes: int = 12  # Standard WSN header size (e.g., 802.15.4 style)
    sample_size_bytes: int = 4     # float32

    @property
    def baseline_bytes(self) -> int:
        """Total bytes if every sample was sent as a separate packet."""
        return self.total_samples * (self.packet_header_bytes + self.sample_size_bytes)

    @property
    def transmitted_bytes(self) -> int:
        """Total bytes actually transmitted."""
        return self.transmitted_packets * (self.packet_header_bytes + self.sample_size_bytes)

    @property
    def byte_reduction(self) -> float:
        """Percentage of BYTES saved compared to baseline."""
        if self.baseline_bytes == 0: return 0.0
        return 1.0 - (self.transmitted_bytes / self.baseline_bytes)
    
    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 1.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 1.0

    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        return 2 * (p * r) / (p + r) if (p + r) > 0 else 0.0

    @property
    def data_reduction(self) -> float:
        """Percentage of samples NOT transmitted."""
        if self.total_samples == 0: return 0.0
        return 1.0 - (self.transmitted_packets / self.total_samples)

class SignalGenerator:
    """Generates synthetic sensor data with labeled anomalies for validation."""
    
    def __init__(self, rng: Generator, config: SignalConfig = SignalConfig()):
        self.rng = rng
        self.config = config

    def next_sample(self) -> Tuple[float, bool]:
        """Returns (value, is_anomaly) based on configured parameters."""
        is_anomaly = self.rng.random() < self.config.anomaly_prob
        noise = self.rng.normal(0, self.config.std)
        value = self.config.base_val + noise
        
        if is_anomaly:
            direction = 1 if self.rng.random() > 0.5 else -1
            value += direction * self.config.magnitude
            
        return value, is_anomaly

@dataclass(frozen=True)
class ZScoreConfig:
    """Configuration for the Z-score anomaly detector."""
    window_size: int = 30
    threshold: float = 3.0
    max_consecutive: int = 5

@dataclass(frozen=True)
class EWMAConfig:
    """Configuration for the EWMA anomaly detector."""
    alpha: float = 0.2
    threshold_mult: float = 3.0
    max_consecutive: int = 5
    warmup_period: int = 10

class Detector(ABC):
    @abstractmethod
    def is_anomaly(self, value: float) -> bool:
        pass

class ZScoreDetector(Detector):
    """Robust Z-score detector with Outlier Rejection and Baseline Shift handling."""
    def __init__(self, config: ZScoreConfig = ZScoreConfig()):
        self.config = config
        
        self.buffer: List[float] = []
        self.sum_x: float = 0.0
        self.sum_x2: float = 0.0
        self.consecutive_anomalies = 0

    def is_anomaly(self, value: float) -> bool:
        n = len(self.buffer)
        if n < 2:
            self._update_stats(value)
            return False
            
        mean = self.sum_x / n
        variance = (self.sum_x2 / n) - (mean ** 2)
        std = np.sqrt(max(0, variance))
        
        # Use a small floor for std to avoid hyper-sensitivity on perfectly stable signals
        z_score = abs(value - mean) / (max(1e-3, std) + 1e-6)
        is_anomaly = z_score > self.config.threshold
        
        if is_anomaly:
            self.consecutive_anomalies += 1
        else:
            self.consecutive_anomalies = 0

        # Logic: 
        # 1. If it's normal -> Update
        # 2. If it's an anomaly but we've seen too many -> Baseline shifted, must update!
        # 3. If it's a "fresh" anomaly -> REJECT from stats (prevent masking)
        if not is_anomaly or self.consecutive_anomalies > self.config.max_consecutive:
            if n >= self.config.window_size:
                oldest = self.buffer.pop(0)
                self.sum_x -= oldest
                self.sum_x2 -= oldest**2
            
            self._update_stats(value)
            if self.consecutive_anomalies > self.config.max_consecutive:
                self.consecutive_anomalies = 0 # Reset after forcing update
            
        return is_anomaly

    def _update_stats(self, value: float):
        self.buffer.append(value)
        self.sum_x += value
        self.sum_x2 += value**2

class EWMADetector(Detector):
    """Robust EWMA detector with Outlier Rejection."""
    def __init__(self, config: EWMAConfig = EWMAConfig()):
        self.config = config
        
        self.moving_avg: Optional[float] = None
        self.moving_std: float = 0.0
        self.warmup_count: int = 0
        self.consecutive_anomalies = 0

    def is_anomaly(self, value: float) -> bool:
        if self.moving_avg is None:
            self.moving_avg = value
            self.warmup_count = 1
            return False
        
        diff = abs(value - self.moving_avg)
        # Only detect after warmup and use a small floor for std to avoid division/zero issues
        is_outlier = (self.warmup_count > self.config.warmup_period and 
                      diff > (self.config.threshold_mult * max(1e-3, self.moving_std)))
        
        if is_outlier:
            self.consecutive_anomalies += 1
        else:
            self.consecutive_anomalies = 0

        # Update stats if normal OR baseline shift detected
        if not is_outlier or self.consecutive_anomalies > self.config.max_consecutive:
            # Recursive update
            self.moving_avg = (1 - self.config.alpha) * self.moving_avg + self.config.alpha * value
            self.moving_std = (1 - self.config.alpha) * self.moving_std + self.config.alpha * diff
            self.warmup_count += 1
            if self.consecutive_anomalies > self.config.max_consecutive:
                self.consecutive_anomalies = 0
                
        return is_outlier

@dataclass(frozen=True)
class EdgeAIConfig:
    """Configuration for the Edge AI strategy."""
    heartbeat: int = 100

class EdgeAIStrategy(AggregationStrategy):
    """Wraps a detector to decide when to transmit data."""
    def __init__(self, detector: Detector, metrics: EdgeAIMetrics, config: EdgeAIConfig = EdgeAIConfig()):
        self.detector = detector
        self.metrics = metrics
        self.config = config
        self.steps_since_tx = 0
        self.acc_value = 0.0
        self.acc_count = 0

    def process_data(self, value: float, is_anomaly: Optional[bool] = None, weight: int = 1) -> Optional[Tuple[float, int, bool]]:
        self.metrics.total_samples += weight
        self.steps_since_tx += weight
        self.acc_value += value * weight
        self.acc_count += weight
        
        detected = self.detector.is_anomaly(value)
        
        if is_anomaly is not None:
            if detected and is_anomaly:
                self.metrics.true_positives += weight
            elif detected and not is_anomaly:
                self.metrics.false_positives += weight
            elif not detected and is_anomaly:
                self.metrics.false_negatives += weight
            else:
                self.metrics.true_negatives += weight
        
        # We send if anomaly is detected OR heartbeat reached
        if detected or self.steps_since_tx >= self.config.heartbeat:
            result = (value if detected else self.acc_value/self.acc_count, self.acc_count, True)
            self.metrics.transmitted_packets += 1
            self.reset_internal()
            return result
            
        return None

    def reset_internal(self):
        self.steps_since_tx = 0
        self.acc_value = 0.0
        self.acc_count = 0

    def reset(self):
        """Reset for AggregationStrategy interface."""
        self.reset_internal()
