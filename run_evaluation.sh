#!/bin/bash

# wsnsim: Master Evaluation Script
# This script runs the full verification suite: Tests + Module Experiments + Case Study.

set -e # Exit on error

echo "===================================================="
echo "🚀 Starting wsnsim Full Evaluation Suite"
echo "===================================================="

# 1. Environment Setup (Ensure local module is discoverable)
export PYTHONPATH=$PYTHONPATH:.

# 2. Run Quality Gate (Tests)
echo -e "\n🧪 Phase 1: Running Unit Tests..."
pytest

# 3. Module-specific Validation Experiments
echo -e "\n🔬 Phase 2: Running Module-specific Experiments..."

echo " - [Routing] Comparing strategies..."
python3 experiments/compare_routing_strategies.py

echo " - [Edge AI] Cross-validating detectors..."
python3 experiments/cross_validate_detectors.py

echo " - [Aggregation] Evaluating data fusion..."
python3 experiments/evaluate_aggregation.py

echo " - [Federated] Evaluating FL trade-offs..."
python3 experiments/evaluate_fl_tradeoffs.py

echo " - [Routing+Agg] Evaluating routing aggregation..."
python3 experiments/evaluate_routing_aggregation.py

echo " - [Optimization] Running optimization demo..."
python3 experiments/wsn_optimization_demo.py

echo " - [Security] Simulating security trade-offs..."
python3 experiments/plot_security_tradeoff.py

echo " - [Sync/Loc] Evaluating localization error..."
python3 experiments/plot_localization_error.py

# 4. Run Case Study (Final Results Generation)
echo -e "\n📊 Phase 3: Running Forest Fire Case Study Demo..."
python3 experiments/case_study_demo.py

echo -e "\n===================================================="
echo "✅ Evaluation Complete!"
echo "----------------------------------------------------"
echo "📂 Results Summary:"
echo " - Plots:   reports/figures/presentation/"
echo " - Data:    reports/*.csv"
echo " - Reports: reports/*.md"
echo " - Config:  reports/optimization_config.json"
echo "----------------------------------------------------"
echo "Check 'PRESENTATION.md' for a high-level overview."
echo "===================================================="
