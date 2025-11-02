#!/usr/bin/env python3
"""
Setup script for ProofGrader.
Checks system requirements and optionally installs as a package.
"""

import subprocess
import sys
import os
import platform
from pathlib import Path
from setuptools import setup, find_packages

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def check_gpu():
    """Check for GPU availability."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            print(f"✅ GPU available: {gpu_count} device(s)")
            for i in range(gpu_count):
                print(f"   - {torch.cuda.get_device_name(i)}")
            return True
        else:
            print("ℹ️  No GPU detected - will use CPU (slower)")
            return False
    except ImportError:
        print("ℹ️  PyTorch not installed yet - GPU check will be done after installation")
        return False

def install_dependencies():
    """Install required dependencies."""
    print("\n📦 Installing dependencies...")
    
    try:
        # Upgrade pip first
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True)
        
        # Install requirements
        if Path("requirements.txt").exists():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                          check=True)
            print("✅ Dependencies installed successfully!")
            return True
        else:
            print("❌ requirements.txt not found")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_environment():
    """Set up the environment for optimal performance."""
    print("\n🔧 Setting up environment...")
    
    # Check if we're in a virtual environment
    in_venv = (hasattr(sys, 'real_prefix') or 
               (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))
    
    if in_venv:
        print("✅ Virtual environment detected")
    else:
        print("⚠️  No virtual environment detected")
        print("   Consider using: python -m venv venv && source venv/bin/activate")
    
    # Set environment variables for better performance
    env_vars = {
        'TOKENIZERS_PARALLELISM': 'false',  # Avoid tokenizer warnings
        'CUDA_VISIBLE_DEVICES': '',  # Will be set based on GPU availability
    }
    
    # Check for GPU and set CUDA_VISIBLE_DEVICES
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            env_vars['CUDA_VISIBLE_DEVICES'] = ','.join(str(i) for i in range(gpu_count))
        else:
            env_vars['CUDA_VISIBLE_DEVICES'] = ''
    except ImportError:
        pass
    
    print("📝 Recommended environment variables:")
    for key, value in env_vars.items():
        print(f"   export {key}={value}")
    
    return True

def run_setup_checks():
    """Run setup checks without installing package."""
    print("🚀 ProofGrader Setup")
    print("=" * 50)
    
    # Check system requirements
    print("\n🔍 Checking system requirements...")
    
    if not check_python_version():
        return False
    
    print(f"✅ Operating system: {platform.system()} {platform.release()}")
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Check installations
    print("\n🔍 Verifying installations...")
    check_gpu()
    
    # Set up environment
    setup_environment()
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Generate solutions:")
    print("   python scripts/generate.py --dataset squad --template math")
    print("2. Evaluate solutions:")
    print("   python scripts/evaluate.py --dataset results.jsonl --template evaluation")
    print("3. Run evaluation workflows:")
    print("   python scripts/evaluate_workflow.py --evaluator-model gemini-2.5-pro")
    print("\nFor more information, see README.md")
    
    return True

# Package metadata
setup(
    name="proofgrader",
    version="0.1.0",
    description="A framework for generating and evaluating mathematical proofs",
    author="ProofGrader Team",
    packages=find_packages(include=["proofgrader", "proofgrader.*"]),
    python_requires=">=3.8",
    install_requires=[
        "torch>=2.0.0",
        "transformers>=4.30.0",
        "datasets>=2.12.0",
        "pyyaml>=6.0",
        "tqdm>=4.65.0",
        "openai>=1.0.0",
        "google-generativeai>=0.3.0",
        "anthropic>=0.5.0",
        "httpx>=0.24.0",
        "matplotlib>=3.5.0",
        "seaborn>=0.12.0",
        "pandas>=1.4.0",
        "numpy>=1.21.0",
        "plotly>=5.0.0",
        "dash>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ]
    },
    scripts=[
        "scripts/generate.py",
        "scripts/evaluate.py",
        "scripts/evaluate_workflow.py",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

if __name__ == "__main__":
    # If running as a script (not via pip install), run setup checks
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] not in ["install", "develop", "sdist", "bdist_wheel"]):
        success = run_setup_checks()
        sys.exit(0 if success else 1)
