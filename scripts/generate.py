#!/usr/bin/env python3
"""
ProofGrader Generation Script

This script generates mathematical proofs/solutions using language models.
Use this for solution generation tasks.

Examples:
    # Generate with default model
    python scripts/generate.py --dataset squad --template math
    
    # Generate with specific model
    python scripts/generate.py --model gemini-2.5-pro --template default
    
    # List available templates
    python scripts/generate.py --list-templates
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path to import proofgrader
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from proofgrader import InferenceEngine, config, PromptFormatter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce verbosity of HTTP request logs
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('openai._base_client').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


def main():
    """Main generation function with command line interface."""
    parser = argparse.ArgumentParser(
        description="ProofGrader Generation - Generate mathematical proofs and solutions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic generation
  python scripts/generate.py --dataset hendrycks/math --template math
  
  # Custom output location
  python scripts/generate.py --output results/my_generations.jsonl
  
  # Limited examples for testing
  python scripts/generate.py --max-examples 10
  
  # Multiple samples per problem
  python scripts/generate.py --n-sampling 5
        """
    )
    
    # Model options
    parser.add_argument("--model", type=str, default="gemini-2.5-pro",
                       help="Model name to use (default: gemini-2.5-pro)")
    
    # Dataset options
    parser.add_argument("--dataset", type=str, help="Dataset name or path to JSONL file")
    parser.add_argument("--dataset-config", type=str, help="Dataset configuration/subset")
    parser.add_argument("--dataset-split", type=str, default="train", help="Dataset split")
    parser.add_argument("--problem-field", type=str, help="Field containing the problem")
    parser.add_argument("--max-examples", type=int, help="Maximum number of examples")
    
    # Output options
    parser.add_argument("--output", type=str, help="Output file path")
    
    # Template options
    parser.add_argument("--template", type=str, default="default", 
                       help="Prompt template to use (default: default)")
    parser.add_argument("--template-config", type=str, 
                       help="Path to template YAML config file")
    parser.add_argument("--list-templates", action="store_true",
                       help="List available templates and exit")
    parser.add_argument("--template-info", type=str, 
                       help="Show detailed info about a specific template")
    
    # Generation options
    parser.add_argument("--max-tokens", type=int, help="Maximum tokens to generate")
    parser.add_argument("--temperature", type=float, help="Temperature for generation")
    parser.add_argument("--n-sampling", type=int, default=1,
                       help="Number of samples per problem (default: 1)")
    
    # Performance options
    parser.add_argument("--max-concurrent", type=int, default=100,
                       help="Maximum concurrent requests (default: 100)")
    parser.add_argument("--no-cache", action="store_true",
                       help="Disable caching of previous results")
    
    # Logging options
    parser.add_argument("--log-level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set logging level (default: INFO)")
    
    args = parser.parse_args()
    
    # Update logging level
    numeric_level = getattr(logging, args.log_level.upper(), None)
    logger.setLevel(numeric_level)
    logging.getLogger().setLevel(numeric_level)
    
    # Handle template listing/info
    if args.list_templates or args.template_info:
        template_config = args.template_config or config.prompt_template_config
        formatter = PromptFormatter(template_config)
        
        if args.list_templates:
            templates = formatter.get_template_info()
            print("\n" + "="*80)
            print("Available Templates for Generation")
            print("="*80)
            for name, info in templates.items():
                print(f"\n{name:20} - {info['description']}")
                print(f"{'':20}   Variables: {', '.join(info.get('variables', []))}")
            print("\n" + "="*80)
            sys.exit(0)
        
        if args.template_info:
            info = formatter.get_template_info(args.template_info)
            if 'error' in info:
                print(f"Error: {info['error']}")
                sys.exit(1)
            print(f"\nTemplate: {info['name']}")
            print("=" * 50)
            print(f"Description: {info['description']}")
            print(f"Variables: {', '.join(info['variables'])}")
            sys.exit(0)
    
    # Update config from arguments
    if args.dataset:
        config.dataset_name = args.dataset
    if args.dataset_config:
        config.dataset_config = args.dataset_config
    if args.dataset_split:
        config.dataset_split = args.dataset_split
    if args.problem_field:
        config.problem_field = args.problem_field
    if args.max_examples:
        config.max_examples = args.max_examples
    if args.output:
        config.output_path = args.output
    if args.template_config:
        config.prompt_template_config = args.template_config
    if args.max_tokens:
        config.max_tokens = args.max_tokens
    if args.temperature:
        config.temperature = args.temperature
    
    # Print configuration
    print("\n" + "="*80)
    print("ProofGrader - Generation Mode")
    print("="*80)
    print(f"Model: {args.model}")
    print(f"Dataset: {config.dataset_name}")
    print(f"Template: {args.template}")
    print(f"Output: {config.output_path}")
    print(f"Max concurrent: {args.max_concurrent}")
    print(f"Sampling: {args.n_sampling}x per problem")
    print(f"Cache: {'disabled' if args.no_cache else 'enabled'}")
    print("="*80 + "\n")
    
    # Run generation
    engine = InferenceEngine(model_name=args.model)
    success = engine.run_inference(
        template=args.template,
        max_concurrent=args.max_concurrent,
        use_cache=not args.no_cache,
        n_sampling=args.n_sampling,
        max_examples=args.max_examples
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()






