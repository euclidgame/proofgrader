#!/usr/bin/env python3
"""
ProofGrader Evaluation Script

Evaluate solutions using various workflows.
Completely independent of generation - can run multiple times on same solutions.

Examples:
    # Basic evaluation (uses data-dir/model_solutions.jsonl)
    python scripts/evaluate.py \
        --data-dir data/my_dataset \
        --model gemini-2.5-pro
    
    # Custom dataset
    python scripts/evaluate.py \
        --data-dir data/my_dataset \
        --model gpt-4 \
        --dataset custom_solutions.jsonl
    
    # Different workflow
    python scripts/evaluate.py \
        --data-dir data/my_dataset \
        --model gemini-2.5-pro \
        --workflow decompose-then-judge
    
    # Compute metrics
    python scripts/evaluate.py \
        --data-dir data/my_dataset \
        --model gemini-2.5-pro \
        --compute-metrics
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from proofgrader import PromptFormatter
from proofgrader.workflow_runner import main as workflow_main

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
    """Main evaluation function."""
    parser = argparse.ArgumentParser(
        description="Evaluate mathematical proofs and solutions with workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic evaluation
  python scripts/evaluate.py \\
      --data-dir data/my_dataset \\
      --model gemini-2.5-pro
  
  # Different evaluator
  python scripts/evaluate.py \\
      --data-dir data/my_dataset \\
      --model gpt-4
  
  # Different workflow
  python scripts/evaluate.py \\
      --data-dir data/my_dataset \\
      --model gemini-2.5-pro \\
      --workflow decompose-then-judge
  
  # With metrics
  python scripts/evaluate.py \\
      --data-dir data/my_dataset \\
      --model gemini-2.5-pro \\
      --compute-metrics
  
  # List templates
  python scripts/evaluate.py --list-templates
        """
    )
    
    # Data directory (simpler interface)
    parser.add_argument(
        "--data-dir", type=str, required=True,
        help="Directory containing solutions (looks for model_solutions.jsonl)"
    )
    
    # Model option
    parser.add_argument(
        "--model", type=str, default="gemini-2.5-pro",
        help="Evaluator model name (default: gemini-2.5-pro)"
    )
    
    # Dataset option (with smart default)
    parser.add_argument(
        "--dataset", type=str,
        help="Path to solutions JSONL (default: data-dir/model_solutions.jsonl)"
    )
    
    # Workflow options
    parser.add_argument(
        "--workflow", type=str, default="single",
        choices=["single", "decompose-then-judge", "repeat-and-aggregate", "reflect-and-revise"],
        help="Evaluation workflow (default: single)"
    )
    parser.add_argument(
        "--template", type=str, default="basic",
        help="Evaluation template (default: basic)"
    )
    parser.add_argument(
        "--template-config", type=str,
        help="Path to template YAML config file"
    )
    
    # Template listing
    parser.add_argument(
        "--list-templates", action="store_true",
        help="List available templates and exit"
    )
    parser.add_argument(
        "--template-info", type=str,
        help="Show detailed info about a specific template"
    )
    
    # Workflow-specific options
    parser.add_argument(
        "--steps-model", type=str,
        help="Model for decomposition (decompose-then-judge workflow)"
    )
    parser.add_argument(
        "--num-runs", type=int,
        help="Number of runs (repeat-and-aggregate workflow)"
    )
    parser.add_argument(
        "--critic-model", type=str,
        help="Critic model (reflect-and-revise workflow)"
    )
    
    # Metrics option
    parser.add_argument(
        "--compute-metrics", action="store_true",
        help="Compute metrics if expert gradings exist"
    )
    
    # Performance options
    parser.add_argument(
        "--max-concurrent", type=int, default=100,
        help="Maximum concurrent requests (default: 100)"
    )
    parser.add_argument(
        "--max-problems", type=int,
        help="Maximum number of problems (for testing)"
    )
    
    # Output options
    parser.add_argument(
        "--output-dir", type=str,
        help="Output directory for evaluation results"
    )
    
    # Logging
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Update logging level
    numeric_level = getattr(logging, args.log_level.upper(), None)
    logger.setLevel(numeric_level)
    logging.getLogger().setLevel(numeric_level)
    
    # Handle template listing
    if args.list_templates or args.template_info:
        from proofgrader import config
        template_config = args.template_config or config.prompt_template_config
        formatter = PromptFormatter(template_config)
        
        if args.list_templates:
            templates = formatter.get_template_info()
            print("\n" + "="*80)
            print("Available Templates for Evaluation")
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
    
    # Setup paths
    data_dir = Path(args.data_dir)
    
    # Default dataset location
    if args.dataset:
        dataset_path = Path(args.dataset)
    else:
        dataset_path = data_dir / "model_solutions.jsonl"
    
    if not dataset_path.exists():
        logger.error(f"Solutions file not found: {dataset_path}")
        logger.error("Run generation first:")
        logger.error(f"  python scripts/generate.py --data-dir {data_dir} --models gpt-4")
        sys.exit(1)
    
    # Print overview
    print("\n" + "="*80)
    print("EVALUATION")
    print("="*80)
    print(f"Data directory: {data_dir}")
    print(f"Solutions: {dataset_path}")
    print(f"Evaluator: {args.model}")
    print(f"Workflow: {args.workflow}")
    print(f"Template: {args.template}")
    print("="*80 + "\n")
    
    # Build arguments for workflow runner
    workflow_args = [
        '--evaluator-model', args.model,
        '--workflow', args.workflow,
        '--dataset', str(dataset_path),
        '--data-version', data_dir.name,
        '--template', args.template,
    ]
    
    if args.template_config:
        workflow_args.extend(['--template-config', args.template_config])
    
    if args.output_dir:
        workflow_args.extend(['--dump-dir', args.output_dir])
    
    if args.steps_model:
        workflow_args.extend(['--steps-model', args.steps_model])
    
    if args.num_runs:
        workflow_args.extend(['--num-runs', str(args.num_runs)])
    
    if args.critic_model:
        workflow_args.extend(['--critic-model', args.critic_model])
    
    if args.max_problems:
        workflow_args.extend(['--max-examples', str(args.max_problems)])
    
    # Run workflow
    original_argv = sys.argv
    sys.argv = ['evaluate'] + workflow_args
    
    try:
        workflow_main()
        logger.info("\n✓ Evaluation completed")
        
        # Compute metrics if requested
        if args.compute_metrics:
            logger.info("\n" + "="*80)
            logger.info("COMPUTING METRICS")
            logger.info("="*80)
            
            # Find expert gradings
            expert_gradings_path = None
            for name in ['expert_gradings.jsonl', 'evaluation_merged.jsonl', 'evaluations.jsonl']:
                candidate = data_dir / name
                if candidate.exists():
                    expert_gradings_path = candidate
                    break
            
            if not expert_gradings_path:
                logger.warning("No expert gradings found. Skipping metrics.")
                logger.info("Looked for: expert_gradings.jsonl, evaluation_merged.jsonl, evaluations.jsonl")
            else:
                logger.info(f"Expert gradings: {expert_gradings_path}")
                
                # Import metrics
                try:
                    from proofgrader.metrics import compute_evaluator_distances
                    
                    # Determine evaluations directory
                    if args.output_dir:
                        eval_dir = Path(args.output_dir)
                    else:
                        # Default location from workflow_runner
                        eval_dir = PROJECT_ROOT / "_archive" / "output_data" / "evaluator_outputs" / "evaluator_grades" / data_dir.name
                    
                    metrics_dir = data_dir / "metrics"
                    metrics_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Run metrics
                    sys.argv = [
                        'compute_metrics',
                        '--merged-path', str(expert_gradings_path),
                        '--eval-dir', str(eval_dir),
                        '--out-dir', str(metrics_dir)
                    ]
                    
                    compute_evaluator_distances.main()
                    
                    logger.info(f"✓ Metrics saved to: {metrics_dir}")
                    
                except Exception as e:
                    logger.error(f"Error computing metrics: {e}")
                    import traceback
                    traceback.print_exc()
        
    except SystemExit as e:
        if e.code != 0 and e.code is not None:
            logger.error(f"Evaluation failed with exit code {e.code}")
            sys.exit(e.code)
    finally:
        sys.argv = original_argv
    
    sys.exit(0)


if __name__ == "__main__":
    main()
