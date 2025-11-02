"""Metrics computation and analysis for evaluators.

This module provides tools for computing evaluator performance metrics,
including binary metrics, distance measures, and comparative analysis.
"""

from . import compute_evaluator_distances
from . import compute_evaluator_binary_metrics

__all__ = [
    'compute_evaluator_distances',
    'compute_evaluator_binary_metrics'
]

