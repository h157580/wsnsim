import pytest
import numpy as np
import os
import csv
from wsnsim.optimization import DesignSpace, identify_pareto, SweepRunner

def test_design_space_full_grid():
    space = DesignSpace({
        "a": [1, 2],
        "b": ["x", "y", "z"]
    })
    combos = space.get_combinations()
    assert len(combos) == 6
    assert combos[0] == {"a": 1, "b": "x"}
    assert combos[-1] == {"a": 2, "b": "z"}

def test_design_space_sampling():
    space = DesignSpace({
        "p": list(range(100))
    })
    # Sample 10 points out of 100
    combos = space.get_combinations(sample_size=10)
    assert len(combos) == 10
    # Ensure all are unique
    unique_vals = set(c["p"] for c in combos)
    assert len(unique_vals) == 10

def test_identify_pareto_strict():
    # Points: A(1, 10), B(2, 8), C(0.5, 12), D(1.5, 9), E(3, 5)
    # Objectives: Minimize x (True), Maximize y (False)
    results = [
        {"x": 1.0, "y": 10.0}, # A
        {"x": 2.0, "y": 8.0},  # B (Dominated by A)
        {"x": 0.5, "y": 12.0}, # C (Dominates everyone)
        {"x": 1.5, "y": 9.0},  # D (Dominated by A)
        {"x": 3.0, "y": 5.0}   # E (Dominated by B)
    ]
    
    pareto = identify_pareto(results, {"x": True, "y": False})
    # Only C should remain as it is strictly better in both
    assert len(pareto) == 1
    assert pareto[0]["x"] == 0.5

def test_identify_pareto_with_tolerance():
    # Case where points are very close
    results = [
        {"x": 1.0, "y": 10.0},
        {"x": 1.01, "y": 9.99} # Very close to the first one
    ]
    
    # Strict filtering: only the first stays
    strict = identify_pareto(results, {"x": True, "y": False}, tolerance=0.0)
    assert len(strict) == 1
    
    # Lenient filtering (tolerance 0.05): both stay
    lenient = identify_pareto(results, {"x": True, "y": False}, tolerance=0.05)
    assert len(lenient) == 2

def mock_sim(params):
    # Deterministic mock simulation
    return {
        "energy": params["p1"] * 2.0,
        "pdr": 1.0 / params["p2"]
    }

def test_sweep_runner_and_aggregation(tmp_path):
    space = DesignSpace({
        "p1": [0.1, 0.5],
        "p2": [10]
    })
    
    runner = SweepRunner(mock_sim, space, max_workers=2)
    # 2 configs x 3 reps = 6 tasks
    results = runner.run(repetitions=3, seed_base=100)
    
    assert len(results) == 6
    
    # Test Aggregation
    aggregated = runner.aggregate_results()
    assert len(aggregated) == 2 # 2 unique configs
    
    # Check if p1=0.5 config has energy=1.0 (mean of 1.0, 1.0, 1.0)
    config_05 = next(r for r in aggregated if r["p1"] == 0.5)
    assert pytest.approx(config_05["energy"]) == 1.0
    
    # Test CSV saving
    csv_file = tmp_path / "test.csv"
    runner.save_to_csv(str(csv_file), data=aggregated)
    assert os.path.exists(csv_file)
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2
        assert "energy" in rows[0]
