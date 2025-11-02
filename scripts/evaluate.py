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
    
    # Evaluate with metrics (requires expert_gradings.jsonl)
    python scripts/evaluate.py \
        --data-dir data/my_dataset \
        --model gemini-2.5-pro \
        --compute-metrics
    
    # Compute metrics only (skip evaluation, use existing results)
    python scripts/evaluate.py \
        --data-dir data/my_dataset \
        --metrics-only
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
  
  # Metrics only (use existing evaluations)
  python scripts/evaluate.py \\
      --data-dir data/my_dataset \\
      --metrics-only
  
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
    
    # Metrics options
    parser.add_argument(
        "--compute-metrics", action="store_true",
        help="Compute metrics after evaluation (requires expert_gradings.jsonl)"
    )
    parser.add_argument(
        "--metrics-only", action="store_true",
        help="Only compute metrics (skip evaluation). Requires existing evaluations and expert_gradings.jsonl"
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
    
    # If metrics-only mode, skip to metrics computation
    if args.metrics_only:
        print("\n" + "="*80)
        print("METRICS COMPUTATION ONLY")
        print("="*80)
        print(f"Data directory: {data_dir}")
        print("="*80 + "\n")
        
        # Jump directly to metrics computation
        import subprocess
        
        # Check for expert gradings
        expert_gradings_path = None
        for name in ['expert_gradings.jsonl', 'evaluation_merged.jsonl', 'evaluations.jsonl']:
            candidate = data_dir / name
            if candidate.exists():
                expert_gradings_path = candidate
                break
        
        if not expert_gradings_path:
            logger.error("\n❌ Cannot compute metrics: No ground truth file found!")
            logger.error(f"\nLooked for in {data_dir}:")
            logger.error("  - expert_gradings.jsonl (preferred)")
            logger.error("  - evaluation_merged.jsonl")
            logger.error("  - evaluations.jsonl")
            logger.error("\nPlease add a ground truth file to the data directory.")
            sys.exit(1)
        
        logger.info(f"✓ Ground truth file: {expert_gradings_path}")
        
        # Check that evaluations exist
        eval_outputs_dir = data_dir / "evaluation_outputs" / "evaluator_gradings"
        if not eval_outputs_dir.exists() or not list(eval_outputs_dir.iterdir()):
            logger.error(f"\n❌ No evaluations found in {eval_outputs_dir}")
            logger.error("\nRun evaluation first:")
            logger.error(f"  python scripts/evaluate.py --data-dir {data_dir} --model gpt-4o")
            sys.exit(1)
        
        # Run metrics
        metrics_script = Path(__file__).parent.parent / "proofgrader" / "metrics" / "compute_evaluator_distances.py"
        cmd = [sys.executable, str(metrics_script), "--data-dir", str(data_dir)]
        
        logger.info(f"\nRunning: {' '.join(cmd)}\n")
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            logger.error("\n❌ Metrics computation failed")
            sys.exit(1)
        
        logger.info("\n" + "="*80)
        logger.info("✓ METRICS COMPUTATION COMPLETE")
        logger.info("="*80)
        logger.info(f"Metrics: {data_dir}/evaluation_outputs/metrics/")
        logger.info("="*80)
        sys.exit(0)
    
    # Normal evaluation mode
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
        '--data-dir', str(data_dir),
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
        
    except SystemExit as e:
        if e.code != 0 and e.code is not None:
            logger.error(f"Evaluation failed with exit code {e.code}")
            sys.argv = original_argv
            sys.exit(e.code)
    finally:
        sys.argv = original_argv
    
    # Compute metrics if requested (separate step after evaluation succeeds)
    if args.compute_metrics:
        logger.info("\n" + "="*80)
        logger.info("COMPUTING METRICS")
        logger.info("="*80)
        
        # Check for expert gradings (required for metrics)
        expert_gradings_path = None
        for name in ['expert_gradings.jsonl', 'evaluation_merged.jsonl', 'evaluations.jsonl']:
            candidate = data_dir / name
            if candidate.exists():
                expert_gradings_path = candidate
                break
        
        if not expert_gradings_path:
            logger.warning("\n⚠️  Cannot compute metrics: No ground truth file found!")
            logger.warning(f"\nLooked for in {data_dir}:")
            logger.warning("  - expert_gradings.jsonl (preferred)")
            logger.warning("  - evaluation_merged.jsonl")
            logger.warning("  - evaluations.jsonl")
            logger.info("\n💡 To compute metrics, add a ground truth file to the data directory, then run:")
            logger.info(f"    python proofgrader/metrics/compute_evaluator_distances.py --data-dir {data_dir}")
            logger.info("\nEvaluation completed successfully (without metrics).")
            sys.exit(0)
        
        logger.info(f"✓ Ground truth file: {expert_gradings_path}")
        
        # Run metrics computation
        import subprocess
        metrics_script = Path(__file__).parent.parent / "proofgrader" / "metrics" / "compute_evaluator_distances.py"
        
        cmd = [
            sys.executable,
            str(metrics_script),
            "--data-dir", str(data_dir)
        ]
        
        logger.info(f"\nRunning: {' '.join(cmd)}\n")
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            logger.error("\n❌ Metrics computation failed")
            sys.exit(1)
        
        logger.info("\n" + "="*80)
        logger.info("✓ EVALUATION AND METRICS COMPLETE")
        logger.info("="*80)
        logger.info(f"Evaluations: {data_dir}/evaluation_outputs/evaluator_gradings/")
        logger.info(f"Metrics: {data_dir}/evaluation_outputs/metrics/")
        logger.info("="*80)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
