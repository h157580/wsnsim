import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any
from .aggregation import AggregationStrategy

@dataclass
class FederatedModel:
    """Represents a model in the FL process."""
    weights: np.ndarray
    n_samples: int

    @property
    def size_bytes(self) -> int:
        """Calculate serialized size for communication cost modeling (float32)."""
        # Ensure we count 4 bytes per parameter even if internal representation is float64
        return self.weights.size * 4

@dataclass(frozen=True)
class FLConfig:
    """Configuration for Federated Learning."""
    num_parameters: int = 10
    samples_per_round: int = 100
    learning_rate: float = 0.1
    compute_energy_per_sample_j: float = 0.00005  # 50 micro-Joules per sample training
    update_threshold: float = 0.01 # Minimum max-weight-change to trigger transmission

class FederatedNode(AggregationStrategy):
    """Memory-efficient local FL logic with proper SGD, synchronization, and loss tracking."""
    
    def __init__(
        self, 
        node_id: int,
        rng: np.random.Generator,
        config: FLConfig = FLConfig(), 
        initial_weights: Optional[np.ndarray] = None
    ):
        self.node_id = node_id
        self.rng = rng
        self.config = config
        # Use float32 for consistency with WSN hardware constraints
        self.weights = initial_weights if initial_weights is not None else np.zeros(config.num_parameters, dtype=np.float32)
        self.last_sent_weights = self.weights.copy()
        self.sample_counter = 0
        self.round_count = 0
        self.total_compute_energy_j = 0.0
        
        # Convergence metrics (Proxy for accuracy)
        self.mse_accumulator = 0.0
        self.current_loss = 0.0

    def set_weights(self, global_weights: np.ndarray):
        """Synchronize local model with the global model (Download step)."""
        self.weights = global_weights.astype(np.float32).copy()
        self.last_sent_weights = self.weights.copy()

    def process_data(self, value: float, weight: int = 1) -> Optional[Tuple[FederatedModel, int, bool]]:
        """Proper SGD update using synthetic features. Tracks MSE as a convergence proxy."""
        self.total_compute_energy_j += weight * self.config.compute_energy_per_sample_j
        
        for _ in range(weight):
            # 1. Generate a synthetic feature vector (reproducible via rng)
            x = self.rng.standard_normal(self.config.num_parameters).astype(np.float32)
            
            # 2. Predict and calculate error (y_hat = w * x)
            prediction = np.dot(self.weights, x)
            error = value - prediction
            
            # 3. Accumulate Loss (MSE)
            self.mse_accumulator += error**2
            
            # 4. SGD Update: w = w + lr * error * x
            self.weights += (self.config.learning_rate * error * x).astype(np.float32)
            self.sample_counter += 1
            
        if self.sample_counter >= self.config.samples_per_round:
            self.current_loss = self.mse_accumulator / self.sample_counter
            self.mse_accumulator = 0.0 

            # Sparse Update Check
            delta = np.abs(self.weights - self.last_sent_weights)
            if np.max(delta) >= self.config.update_threshold:
                model_update = FederatedModel(
                    weights=self.weights.copy(), 
                    n_samples=self.sample_counter
                )
                result = (model_update, self.sample_counter, True)
                self.last_sent_weights = self.weights.copy()
            else:
                # Suppress update: change is below threshold
                result = None
            
            self.reset()
            self.round_count += 1
            return result
            
        return None

    def reset(self):
        """Reset the sample counter for the next round."""
        self.sample_counter = 0

class FederatedServer:
    """Sink-side logic for FedAvg aggregation with memory and global loss tracking."""
    
    def __init__(self, total_nodes: int, config: FLConfig = FLConfig()):
        self.config = config
        self.total_nodes = total_nodes
        self.global_weights = np.zeros(config.num_parameters, dtype=np.float32)
        self.updates: List[FederatedModel] = []

    def receive_update(self, model: FederatedModel):
        """Register a new local update from a node."""
        self.updates.append(model)

    def aggregate(self) -> np.ndarray:
        """Perform FedAvg, accounting for silent nodes to maintain stability."""
        if not self.updates:
            return self.global_weights

        # Total samples calculation including silent nodes
        total_active_samples = sum(m.n_samples for m in self.updates)
        num_silent_nodes = max(0, self.total_nodes - len(self.updates))
        total_silent_samples = num_silent_nodes * self.config.samples_per_round
        
        total_samples = total_active_samples + total_silent_samples

        # Weighted average of active and silent nodes
        new_weights = np.zeros_like(self.global_weights)
        for m in self.updates:
            new_weights += m.weights * (m.n_samples / total_samples)

        if total_silent_samples > 0:
            # Silent nodes are assumed to still have the old global weights
            new_weights += self.global_weights * (total_silent_samples / total_samples)

        self.global_weights = new_weights
        self.updates = []
        return self.global_weights

    def evaluate(self, validation_data: List[Tuple[float, np.ndarray]]) -> float:
        """Calculate global MSE on a validation set to measure convergence."""
        if not validation_data:
            return 0.0
        
        total_error = 0.0
        for value, x in validation_data:
            prediction = np.dot(self.global_weights, x)
            total_error += (value - prediction)**2
            
        return total_error / len(validation_data)

@dataclass
class FLCostReport:
    """Summary of communication costs and convergence performance."""
    strategy: str
    total_bytes: int
    total_energy_j: float
    final_loss: float = 0.0
    reduction_factor: float = 1.0

class FLCostAnalyzer:
    """Calculates and compares communication costs vs model quality."""
    
    def __init__(self, config: FLConfig, total_nodes: int, avg_hops: float = 2.0):
        self.config = config
        self.total_nodes = total_nodes
        self.avg_hops = avg_hops
        self.header_bytes = 12
        self.sample_bytes = 4
        self.energy_per_byte_j = 0.000001 

    def analyze(self, rounds: int, final_loss: float, suppression_rate: float = 0.5) -> Tuple[FLCostReport, FLCostReport]:
        """Returns (CentralizedReport, FLReport) for a comprehensive comparison."""
        
        # 1. Centralized Calculation
        cent_bytes = rounds * self.total_nodes * self.config.samples_per_round * (self.header_bytes + self.sample_bytes) * self.avg_hops
        cent_energy = cent_bytes * self.energy_per_byte_j
        # Assuming centralized reaches near-zero loss for comparison
        cent_report = FLCostReport("Centralized", int(cent_bytes), cent_energy, final_loss=0.01) 
        
        # 2. Federated Learning Calculation
        model_size = self.config.num_parameters * 4
        active_nodes_per_round = self.total_nodes * (1 - suppression_rate)
        
        fl_uplink = rounds * active_nodes_per_round * (self.header_bytes + model_size) * self.avg_hops
        fl_downlink = rounds * (self.header_bytes + model_size) * self.avg_hops
        
        fl_bytes = fl_uplink + fl_downlink
        fl_energy = fl_bytes * self.energy_per_byte_j
        
        reduction = cent_bytes / fl_bytes if fl_bytes > 0 else 0
        fl_report = FLCostReport("Federated", int(fl_bytes), fl_energy, final_loss=final_loss, reduction_factor=reduction)
        
        return cent_report, fl_report
