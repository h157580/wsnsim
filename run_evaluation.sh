#!/bin/bash

# wsnsim: Master Evaluation Script
# This script runs the full verification suite: Tests + Case Study Demo.

set -e # Exit on error

echo "===================================================="
echo "🚀 Starting wsnsim Full Evaluation Suite"
echo "===================================================="

# 1. Environment Setup (Ensure local module is discoverable)
export PYTHONPATH=$PYTHONPATH:.

# 2. Run Quality Gate (Tests)
echo -e "\n🧪 Phase 1: Running Unit Tests..."
pytest

# 3. Run Case Study (Results Generation)
echo -e "\n📊 Phase 2: Running Forest Fire Case Study Demo..."
python3 experiments/case_study_demo.py

echo -e "\n===================================================="
echo "✅ Evaluation Complete!"
echo "Check 'PRESENTATION.md' for the project overview."
echo "Check 'reports/figures/presentation/' for the latest plots."
echo "===================================================="
