"""ProofGrader - A framework for generating and evaluating mathematical proofs.

This package provides core infrastructure for:
- Inference engine for generation and evaluation
- API clients for various LLM providers
- Dataset handling for problem sets
- Prompt formatting and template management
- Advanced evaluation workflows
- Metrics computation and analysis
- Dashboard and visualization tools
"""

__version__ = "0.1.0"

from .inference import InferenceEngine
from .config import config
from .api_client import APIClient
from .dataset_handler import DatasetHandler
from .prompt_formatter import PromptFormatter

__all__ = [
    "InferenceEngine",
    "config",
    "APIClient",
    "DatasetHandler",
    "PromptFormatter",
    "workflows",
    "metrics",
    "dashboard",
]


