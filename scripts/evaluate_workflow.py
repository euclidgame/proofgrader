#!/usr/bin/env python3
"""
ProofGrader Workflow Evaluation Script

This script runs complex evaluation workflows with multiple stages:
- single: Basic single-shot evaluation
- decompose-then-judge: Decompose problem into steps, then judge
- repeat-and-aggregate: Multiple evaluations with aggregation
- reflect-and-revise: Self-critique and revision workflow

For simple single-shot evaluation, consider using evaluate.py instead.

Examples:
    # Single-stage evaluation
    python scripts/evaluate_workflow.py --evaluator-model gemini-2.5-pro --workflow single
    
    # Decompose then judge
    python scripts/evaluate_workflow.py --evaluator-model gemini-2.5-pro \\
        --workflow decompose-then-judge --steps-model gpt-4
    
    # Repeat and aggregate
    python scripts/evaluate_workflow.py --evaluator-model gemini-2.5-pro \\
        --workflow repeat-and-aggregate --num-runs 5
"""

import sys
from pathlib import Path

# Add parent directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import and run the evaluator workflow module
from proofgrader.workflow_runner import main

if __name__ == "__main__":
    print("="*80)
    print("ProofGrader - Workflow Evaluation Mode")
    print("="*80)
    print()
    main()


