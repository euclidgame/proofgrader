"""Configuration file for vLLM inference setup."""

import os
import subprocess
from dataclasses import dataclass
from typing import Optional, Dict, Any

def get_gpu_count() -> int:
    """Get the number of available GPUs."""
    try:
        # Try to get GPU count using nvidia-smi
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:  # Check if output is not empty
                gpu_count = len(output.split('\n'))
                return max(1, gpu_count)  # Ensure at least 1
            else:
                return 1  # No GPUs detected
        else:
            return 1  # Default to 1 if nvidia-smi fails
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        # nvidia-smi not available or failed, default to 1
        return 1

@dataclass
class ModelConfig:
    """Configuration for the model and vLLM server."""
    # Model settings
    model_name: str = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"  # Default model
    tensor_parallel_size: int = get_gpu_count()  # Automatically detect GPU count
    dtype: str = "float16"
    max_model_len: int = -1
    
    # Server settings
    host: str = "localhost"
    port: int = 11434
    
    # Generation settings
    max_tokens: int = 65536
    temperature: float = 0.6
    top_p: float = 0.95
    
    # Dataset settings (Hugging Face)
    dataset_name: str = "xiaomama2002/olympic_dataset"  # HF dataset name
    dataset_config: Optional[str] = None  # Optional dataset config/subset
    dataset_split: str = "train"  # Dataset split
    problem_field: str = "question"  # Field containing the problem/question
    max_examples: Optional[int] = None  # Limit examples for testing (None for all)
    
    # Processing settings
    processing_mode: str = "batch"  # sequential, parallel, async
    max_workers: int = 32  # Thread pool size for parallel mode
    max_concurrent: int = 32  # Max concurrent requests for async mode
    
    # Output settings
    output_path: str = "outputs.jsonl"
    
    # Prompt settings
    prompt_template_config: str = "templates/"  # Path to YAML template config (directory or file)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "model": self.model_name,
            "tensor_parallel_size": self.tensor_parallel_size,
            "dtype": self.dtype,
            "max_model_len": self.max_model_len,
            "host": self.host,
            "port": self.port,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
    
    def show_gpu_info(self) -> None:
        """Display GPU configuration information."""
        print(f"🖥️  GPU Configuration:")
        print(f"   - Detected GPUs: {self.tensor_parallel_size}")
        print(f"   - Tensor Parallel Size: {self.tensor_parallel_size}")
        if self.tensor_parallel_size > 1:
            print(f"   - Multi-GPU mode enabled")
        else:
            print(f"   - Single GPU/CPU mode")

# Global config instance
config = ModelConfig() 