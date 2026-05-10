from __future__ import annotations
import numpy as np
import itertools
import time
import csv
import random
from dataclasses import dataclass
from typing import Dict, List, Any, Callable, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

@dataclass
class DesignSpace:
    """Defines the parameters and their ranges for exploration."""
    parameters: Dict[str, List[Any]]

    def save_config(self, filename: str):
        """Saves the design space configuration to a JSON file."""
        import json
        with open(filename, 'w') as f:
            json.dump(self.parameters, f, indent=4)
        print(f"Design space configuration saved to {filename}")

    def get_combinations(self, sample_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return parameter combinations with optional random sampling."""
        keys = list(self.parameters.keys())
        values = list(self.parameters.values())
        all_combos = list(itertools.product(*values))
        
        # SANITY CHECK: Warn about combinatorial explosion
        if len(all_combos) > 5000 and sample_size is None:
            print(f"WARNING: Large design space ({len(all_combos)} points). "
                  "Consider using 'sample_size' to avoid long execution times.")
        
        if sample_size and sample_size < len(all_combos):
            # DECISION: Structured sampling to prevent combinatorial explosion
            sampled_indices = random.sample(range(len(all_combos)), sample_size)
            combos = [all_combos[i] for i in sampled_indices]
        else:
            combos = all_combos
            
        return [dict(zip(keys, combo)) for combo in combos]

def is_dominated(point: np.ndarray, others: np.ndarray) -> bool:
    """DECISION: Pareto-dominance test.
    A point P is dominated if there exists another point O such that:
    1. O is at least as good as P in ALL objectives (O_i <= P_i for all i)
    2. O is strictly better than P in at least ONE objective (O_j < P_j)
    
    Note: Logic assumes MINIMIZATION. Maximization goals must be flipped beforehand.
    """
    return np.any(np.all(others <= point, axis=1) & np.any(others < point, axis=1))

def identify_pareto(results: List[Dict[str, Any]], objectives: Dict[str, bool], tolerance: float = 0.0) -> List[Dict[str, Any]]:
    """Identifies Pareto-optimal configurations with tolerance (epsilon-dominance).
    
    Args:
        results: List of result dictionaries.
        objectives: Optimization goals (True for MINIMIZE, False for MAXIMIZE).
        tolerance: Leniency threshold. If > 0, 'near-optimal' points are also kept.
    """
    if not results: return []

    obj_names = list(objectives.keys())
    data = []
    for res in results:
        point = []
        for name, minimize in objectives.items():
            val = float(res[name])
            point.append(val if minimize else -val)
        data.append(np.array(point))
    
    data = np.array(data)
    pareto_indices = []
    
    for i in range(len(data)):
        point = data[i]
        others = np.delete(data, i, axis=0)
        
        # DECISION: Epsilon-dominance. A point is dominated only if something
        # is significantly better (by tolerance) in all objectives.
        is_dominated = np.any(
            np.all(others <= (point - tolerance), axis=1) & 
            np.any(others < (point - tolerance), axis=1)
        )
        
        if not is_dominated:
            pareto_indices.append(i)
            
    return [results[i] for i in pareto_indices]

class SweepRunner:
    """Parallelized parameter sweep runner."""
    def __init__(self, sim_func: Callable, design_space: DesignSpace, max_workers: Optional[int] = None):
        self.sim_func = sim_func
        self.design_space = design_space
        self.max_workers = max_workers
        self.results = []

    def run(self, repetitions: int = 1, sample_size: Optional[int] = None, seed_base: int = 42):
        # DECISION: Seed the random module to make task sampling reproducible
        random.seed(seed_base)
        combos = self.design_space.get_combinations(sample_size=sample_size)
        tasks = [{**c, "_seed": seed_base + r, "_rep": r} for c in combos for r in range(repetitions)]

        print(f"Starting sweep: {len(combos)} points x {repetitions} reps = {len(tasks)} tasks.")
        
        start_time = time.time()
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.sim_func, t): t for t in tasks}
            for i, f in enumerate(as_completed(futures)):
                try:
                    self.results.append({**futures[f], **f.result()})
                except Exception as e:
                    print(f"Task failed: {e}")
                if (i + 1) % 20 == 0 or (i + 1) == len(tasks):
                    print(f"  Progress: {i+1}/{len(tasks)} tasks...")

        print(f"Sweep completed in {time.time() - start_time:.2f}s.")
        return self.results

    def aggregate_results(self) -> List[Dict[str, Any]]:
        """DECISION: Aggregation before filtering to avoid the 'noisy Pareto-front' problem.
        Averages results across repetitions (reps) with identical parameters.
        """
        if not self.results: return []

        # Separate parameters and metrics
        param_keys = [k for k in self.results[0].keys() if not k.startswith('_') and k not in ["energy", "pdr", "latency"]]
        # Note: This list could be extracted dynamically if metric names were known.
        # Here we safely filter out internal variables with '_' prefix (_seed, _rep).

        grouped: Dict[tuple, List[Dict[str, float]]] = {}

        for r in self.results:
            # The configuration (parameters) forms the key
            config_key = tuple(r[k] for k in param_keys)
            if config_key not in grouped:
                grouped[config_key] = []
            grouped[config_key].append(r)

        aggregated = []
        for config_key, runs in grouped.items():
            # New dict with parameters
            agg_entry = {k: v for k, v in zip(param_keys, config_key)}

            # Average metrics
            metric_keys = [k for k in runs[0].keys() if k not in param_keys and not k.startswith('_')]
            for m_key in metric_keys:
                agg_entry[m_key] = np.mean([run[m_key] for run in runs])
                # Optional: Standard deviation (std) could also be stored for confidence analysis

            aggregated.append(agg_entry)

        return aggregated


    def save_to_csv(self, filename: str, data: Optional[List[Dict[str, Any]]] = None):
        """Save results to a CSV file. If data is not provided, saves raw results."""
        target_data = data if data is not None else self.results
        if not target_data:
            print("No data to save.")
            return
            
        keys = target_data[0].keys()
        with open(filename, 'w', newline='') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(target_data)
        print(f"Results saved to {filename}")

def calculate_sensitivity(results: List[Dict[str, Any]], 
                          target_metric: str, 
                          param_name: str) -> Dict[str, float]:
    """Calculates the sensitivity of a target metric to a specific parameter.
    
    Returns a dictionary of local slopes between adjacent parameter values:
    {'p1->p2': (delta_metric / delta_param)}
    """
    # Group by parameter value and average the metric
    values = {}
    for r in results:
        p_val = r.get(param_name)
        if p_val is None or not isinstance(p_val, (int, float)): continue
        if p_val not in values: values[p_val] = []
        values[p_val].append(r[target_metric])
    
    sorted_p = sorted(values.keys())
    sensitivity = {}
    
    for i in range(len(sorted_p) - 1):
        p1, p2 = sorted_p[i], sorted_p[i+1]
        m1 = np.mean(values[p1])
        m2 = np.mean(values[p2])
        
        delta_p = p2 - p1
        if delta_p != 0:
            slope = (m2 - m1) / delta_p
            # Normalize by baseline value to get relative sensitivity if p1 != 0
            sensitivity[f"{p1}->{p2}"] = slope
            
    return sensitivity
