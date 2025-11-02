#!/usr/bin/env python3
"""
ProofGrader Full Workflow Script

This script runs the complete ProofGym workflow:
1. Generate solutions from multiple models with multiple attempts
2. Evaluate the solutions using evaluator workflows
3. Compute metrics if expert gradings are available

Examples:
    # Full workflow with single model
    python scripts/run_full_workflow.py --data-dir data/test_data \\
        --generators gpt-4 --num-attempts 3
    
    # Multiple models with evaluation
    python scripts/run_full_workflow.py --data-dir data/test_data \\
        --generators gpt-4 gemini-2.5-pro --num-attempts 5 \\
        --evaluator gemini-2.5-pro --workflow single
    
    # Full workflow with metrics (if expert gradings exist)
    python scripts/run_full_workflow.py --data-dir data/test_data \\
        --generators gpt-4 --num-attempts 3 \\
        --evaluator gemini-2.5-pro --compute-metrics
"""

import sys
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from tqdm import tqdm

# Add parent directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from proofgrader import InferenceEngine, config
from proofgrader.data_validation import DataValidator

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


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read JSONL file and return list of records."""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(records: List[Dict[str, Any]], path: Path) -> None:
    """Write records to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    logger.info(f"Wrote {len(records)} records to {path}")


def generate_solutions(
    problems_path: Path,
    generators: List[str],
    num_attempts: int,
    output_path: Path,
    template: str = "default",
    template_config: str = None,
    max_concurrent: int = 100,
    use_cache: bool = True,
    skip_validation: bool = False,
    strict_validation: bool = False
) -> Path:
    """
    Generate solutions for problems using multiple models.
    
    Args:
        problems_path: Path to problems.jsonl
        generators: List of model names to use for generation
        num_attempts: Number of attempts per model per problem
        output_path: Path to save generated solutions
        template: Template name for generation
        template_config: Path to template config
        max_concurrent: Maximum concurrent requests
        use_cache: Whether to use caching
    
    Returns:
        Path to the generated solutions file
    """
    logger.info("="*80)
    logger.info("STEP 1: Solution Generation")
    logger.info("="*80)
    logger.info(f"Problems: {problems_path}")
    logger.info(f"Generators: {generators}")
    logger.info(f"Attempts per model: {num_attempts}")
    logger.info(f"Output: {output_path}")
    logger.info("="*80)
    
    all_solutions = []
    
    for generator_idx, generator in enumerate(generators):
        logger.info(f"\nGenerating solutions with {generator}...")
        
        # Create temporary output for this generator
        temp_output = output_path.parent / f"temp_{generator.replace('/', '_')}.jsonl"
        
        # Configure the engine for this generator
        original_dataset = config.dataset_name
        original_output = config.output_path
        config.dataset_name = str(problems_path)
        config.output_path = str(temp_output)
        
        try:
            engine = InferenceEngine(model_name=generator)
            
            # Run inference with the specified number of attempts
            success = engine.run_inference(
                template=template,
                max_concurrent=max_concurrent,
                use_cache=use_cache,
                n_sampling=num_attempts
            )
            
            if not success:
                logger.error(f"Generation failed for {generator}")
                continue
            
            # Read generated results and reformat with required fields
            if temp_output.exists():
                generated = read_jsonl(temp_output)
                
                for record in generated:
                    problem_id = record.get('id', record.get('problem_id', 'unknown'))
                    
                    # Extract solution (assuming single response per generator)
                    if 'responses' in record and isinstance(record['responses'], list):
                        # If multiple responses, take the first one
                        solution_text = record['responses'][0] if record['responses'] else ''
                    else:
                        solution_text = record.get('response', record.get('solution', ''))
                    
                    # Create solution record, preserving all original fields
                    solution_record = {
                        'problem_id': problem_id,
                        'generator': generator,
                        'solution': solution_text,
                        'problem': record.get('problem', record.get('question', '')),
                        'model': generator,
                        'generation_metadata': record.get('generation_info', {}),
                        # Preserve reference_solutions if present
                        'reference_solutions': record.get('reference_solutions'),
                        # Preserve any other fields except those we've already handled
                        **{k: v for k, v in record.items() 
                           if k not in ['id', 'problem', 'question', 'response', 'responses', 
                                        'generation_info', 'token_usage', 'solution']}
                    }
                    
                    # Remove None values to keep output clean
                    solution_record = {k: v for k, v in solution_record.items() if v is not None}
                    
                    all_solutions.append(solution_record)
                
                # Clean up temp file
                temp_output.unlink()
                
        except Exception as e:
            logger.error(f"Error generating solutions with {generator}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Restore original config
            config.dataset_name = original_dataset
            config.output_path = original_output
    
    # Write all solutions
    write_jsonl(all_solutions, output_path)
    logger.info(f"\n✓ Generated {len(all_solutions)} total solutions")
    
    # Validate generated solutions
    if not skip_validation:
        logger.info("\n🔍 Validating generated solutions...")
        validator = DataValidator()
        solutions_validation = validator.validate_solutions(output_path, problems_path)
        
        if not solutions_validation['valid']:
            logger.warning("⚠️  Solution validation found issues")
            if solutions_validation.get('duplicate_composite_ids', 0) > 0:
                logger.error("  CRITICAL: Duplicate solution IDs detected!")
            if solutions_validation.get('orphan_solutions'):
                logger.warning(f"  WARNING: {len(solutions_validation['orphan_solutions'])} orphan solutions")
            
            if strict_validation:
                logger.error("Exiting due to --strict-validation")
                sys.exit(1)
        else:
            logger.info("✓ Solution validation passed")
    
    return output_path


def run_evaluation_workflow(
    solutions_path: Path,
    evaluator: str,
    workflow: str,
    data_version: str,
    template: str = "basic",
    output_dir: Path = None,
    skip_validation: bool = False,
    strict_validation: bool = False,
    **workflow_kwargs
) -> Path:
    """
    Run evaluation workflow on generated solutions.
    
    Args:
        solutions_path: Path to solutions JSONL
        evaluator: Evaluator model name
        workflow: Workflow type (single, decompose-then-judge, etc.)
        data_version: Data version identifier
        template: Evaluation template name
        output_dir: Output directory for results
        **workflow_kwargs: Additional workflow arguments
    
    Returns:
        Path to evaluation results
    """
    logger.info("\n" + "="*80)
    logger.info("STEP 2: Evaluation Workflow")
    logger.info("="*80)
    logger.info(f"Solutions: {solutions_path}")
    logger.info(f"Evaluator: {evaluator}")
    logger.info(f"Workflow: {workflow}")
    logger.info("="*80)
    
    # Import workflow runner
    from proofgrader.workflow_runner import main as workflow_main
    
    # Build arguments for workflow
    args_list = [
        '--evaluator-model', evaluator,
        '--workflow', workflow,
        '--template', template,
        '--data-version', data_version,
        '--dataset', str(solutions_path),
    ]
    
    if output_dir:
        args_list.extend(['--dump-dir', str(output_dir)])
    
    # Add additional workflow-specific arguments
    for key, value in workflow_kwargs.items():
        if value is not None:
            args_list.extend([f'--{key.replace("_", "-")}', str(value)])
    
    # Run workflow
    original_argv = sys.argv
    sys.argv = ['workflow_runner'] + args_list
    
    try:
        workflow_main()
        logger.info("✓ Evaluation workflow completed")
        
        # Validate evaluations
        if not skip_validation and output_dir and output_dir.exists():
            logger.info("\n🔍 Validating evaluations...")
            validator = DataValidator()
            eval_validation = validator.validate_evaluations(output_dir, solutions_path)
            
            if not eval_validation['valid']:
                logger.warning("⚠️  Evaluation validation found issues")
                if eval_validation.get('duplicate_ids', 0) > 0:
                    logger.warning(f"  {eval_validation['duplicate_ids']} duplicate evaluation IDs")
                if eval_validation.get('missing_evaluations', 0) > 0:
                    logger.warning(f"  {eval_validation['missing_evaluations']} solutions without evaluations")
                
                if strict_validation:
                    logger.error("Exiting due to --strict-validation")
                    sys.exit(1)
            else:
                logger.info("✓ Evaluation validation passed")
                
    except SystemExit as e:
        if e.code != 0:
            logger.error(f"Evaluation workflow failed with exit code {e.code}")
            raise
    finally:
        sys.argv = original_argv
    
    return output_dir or PROJECT_ROOT / "outputs"


def compute_metrics(
    solutions_path: Path,
    expert_gradings_path: Path,
    evaluations_path: Path,
    output_path: Path
) -> None:
    """
    Compute metrics comparing evaluations with expert gradings.
    
    Args:
        solutions_path: Path to solutions JSONL
        expert_gradings_path: Path to expert gradings JSONL
        evaluations_path: Path to evaluation results
        output_path: Path to save metrics
    """
    logger.info("\n" + "="*80)
    logger.info("STEP 3: Metrics Computation")
    logger.info("="*80)
    logger.info(f"Expert gradings: {expert_gradings_path}")
    logger.info(f"Evaluations: {evaluations_path}")
    logger.info("="*80)
    
    # Import metrics modules
    try:
        from proofgrader.metrics import compute_evaluator_distances
        from proofgrader.metrics import compute_evaluator_binary_metrics
    except ImportError as e:
        logger.error(f"Failed to import metrics modules: {e}")
        logger.info("Metrics computation skipped")
        return
    
    # Prepare arguments for metrics computation
    # The metrics computation expects:
    # - Ground truth: evaluation_merged.jsonl (expert gradings)
    # - Evaluator predictions: directory with *.eval.jsonl files
    # - Output directory for reports
    
    # Check if evaluations directory exists and has expected structure
    if not evaluations_path.exists():
        logger.error(f"Evaluations directory not found: {evaluations_path}")
        return
    
    # Set up output directory for metrics
    metrics_dir = output_path.parent / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Computing correlation metrics...")
    
    # Prepare arguments for compute_evaluator_distances
    import argparse
    metrics_args = argparse.Namespace(
        merged_path=str(expert_gradings_path),
        eval_dir=str(evaluations_path),
        out_dir=str(metrics_dir),
        data_version=None,
        skip_disagreement=False,
        skip_order=False,
        skip_verify=False
    )
    
    try:
        # Run metrics computation
        original_argv = sys.argv
        sys.argv = [
            'compute_evaluator_distances',
            '--merged-path', str(expert_gradings_path),
            '--eval-dir', str(evaluations_path),
            '--out-dir', str(metrics_dir)
        ]
        
        compute_evaluator_distances.main()
        
        sys.argv = original_argv
        
        logger.info(f"✓ Metrics computed successfully")
        logger.info(f"  Reports saved to: {metrics_dir}")
        
        # Check if binary metrics should be computed
        binary_gt = expert_gradings_path.parent / "evaluation_merged_binary.jsonl"
        if binary_gt.exists():
            logger.info(f"Computing binary classification metrics...")
            binary_metrics_dir = metrics_dir / "binary"
            binary_metrics_dir.mkdir(parents=True, exist_ok=True)
            
            sys.argv = [
                'compute_evaluator_binary_metrics',
                '--gt-path', str(binary_gt),
                '--eval-dir', str(evaluations_path),
                '--out-dir', str(binary_metrics_dir)
            ]
            
            compute_evaluator_binary_metrics.main()
            sys.argv = original_argv
            
            logger.info(f"✓ Binary metrics computed successfully")
            logger.info(f"  Binary reports saved to: {binary_metrics_dir}")
        
    except Exception as e:
        logger.error(f"Error computing metrics: {e}")
        import traceback
        traceback.print_exc()
        sys.argv = original_argv


def main():
    parser = argparse.ArgumentParser(
        description="ProofGrader Full Workflow - Complete pipeline from generation to evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic workflow with single model
  python scripts/run_full_workflow.py --data-dir data/test_data \\
      --generators gpt-4 --num-attempts 3

  # Multiple models
  python scripts/run_full_workflow.py --data-dir data/test_data \\
      --generators gpt-4 gemini-2.5-pro deepseek-r1 \\
      --num-attempts 5

  # Full workflow with evaluation
  python scripts/run_full_workflow.py --data-dir data/test_data \\
      --generators gpt-4 --num-attempts 3 \\
      --evaluator gemini-2.5-pro --workflow single

  # Skip generation (use existing solutions)
  python scripts/run_full_workflow.py --data-dir data/test_data \\
      --skip-generation --evaluator gemini-2.5-pro
        """
    )
    
    # Data directory
    parser.add_argument(
        "--data-dir", type=str, required=True,
        help="Directory containing problems.jsonl (and optionally expert_gradings.jsonl)"
    )
    
    # Generation options
    parser.add_argument(
        "--generators", type=str, nargs='+', default=["gpt-4"],
        help="List of generator models to use (default: gpt-4)"
    )
    parser.add_argument(
        "--num-attempts", type=int, default=1,
        help="Number of generation attempts per model (default: 1)"
    )
    parser.add_argument(
        "--generation-template", type=str, default="default",
        help="Template for generation (default: default)"
    )
    parser.add_argument(
        "--skip-generation", action="store_true",
        help="Skip generation step (use existing model_solutions.jsonl)"
    )
    
    # Evaluation options
    parser.add_argument(
        "--evaluator", type=str, default="gemini-2.5-pro",
        help="Evaluator model (default: gemini-2.5-pro)"
    )
    parser.add_argument(
        "--workflow", type=str, default="single",
        choices=["single", "decompose-then-judge", "repeat-and-aggregate", "reflect-and-revise"],
        help="Evaluation workflow (default: single)"
    )
    parser.add_argument(
        "--evaluation-template", type=str, default="basic",
        help="Template for evaluation (default: basic)"
    )
    parser.add_argument(
        "--skip-evaluation", action="store_true",
        help="Skip evaluation step"
    )
    
    # Metrics options
    parser.add_argument(
        "--compute-metrics", action="store_true",
        help="Compute metrics if expert_gradings.jsonl exists"
    )
    
    # Validation options
    parser.add_argument(
        "--strict-validation", action="store_true",
        help="Exit immediately if validation fails at any stage"
    )
    parser.add_argument(
        "--skip-validation", action="store_true",
        help="Skip all validation checks"
    )
    
    # Output options
    parser.add_argument(
        "--output-dir", type=str,
        help="Output directory (default: data-dir/outputs)"
    )
    
    # Advanced options
    parser.add_argument(
        "--max-concurrent", type=int, default=100,
        help="Maximum concurrent requests (default: 100)"
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable caching"
    )
    parser.add_argument(
        "--max-problems", type=int,
        help="Maximum number of problems to process (for testing)"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    data_dir = Path(args.data_dir)
    problems_path = data_dir / "problems.jsonl"
    
    if not problems_path.exists():
        logger.error(f"problems.jsonl not found in {data_dir}")
        sys.exit(1)
    
    # Output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = data_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Paths
    solutions_path = output_dir / "model_solutions.jsonl"
    
    # Check for expert gradings in multiple possible locations/names
    expert_gradings_path = None
    possible_gradings = [
        data_dir / "expert_gradings.jsonl",
        data_dir / "evaluation_merged.jsonl",
        data_dir / "evaluations.jsonl"
    ]
    for path in possible_gradings:
        if path.exists():
            expert_gradings_path = path
            break
    
    # Print workflow overview
    print("\n" + "="*80)
    print("PROOFGYM FULL WORKFLOW")
    print("="*80)
    print(f"Data directory: {data_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Generators: {args.generators}")
    print(f"Evaluator: {args.evaluator}")
    print(f"Workflow: {args.workflow}")
    if expert_gradings_path:
        print(f"Expert gradings found: {expert_gradings_path.name}")
    else:
        print(f"Expert gradings: Not found")
    print(f"Validation: {'Skipped' if args.skip_validation else ('Strict' if args.strict_validation else 'Enabled')}")
    print("="*80 + "\n")
    
    # Validate problems before starting
    if not args.skip_validation:
        logger.info("🔍 Validating input problems...")
        validator = DataValidator()
        problems_validation = validator.validate_problems(problems_path)
        
        if not problems_validation['valid']:
            logger.error("❌ Problem validation failed!")
            if problems_validation.get('duplicate_ids'):
                logger.error(f"  Duplicate problem IDs: {problems_validation['duplicate_ids'][:5]}")
            if problems_validation.get('missing_id', 0) > 0:
                logger.error(f"  {problems_validation['missing_id']} problems without IDs")
            
            if args.strict_validation:
                logger.error("Exiting due to --strict-validation")
                sys.exit(1)
        else:
            logger.info("✓ Problem validation passed")
    
    # Step 1: Generate solutions
    if not args.skip_generation:
        solutions_path = generate_solutions(
            problems_path=problems_path,
            generators=args.generators,
            num_attempts=1,  # Simplified: one response per generator
            output_path=solutions_path,
            template=args.generation_template,
            max_concurrent=args.max_concurrent,
            use_cache=not args.no_cache,
            skip_validation=args.skip_validation,
            strict_validation=args.strict_validation
        )
    else:
        if not solutions_path.exists():
            logger.error(f"--skip-generation specified but {solutions_path} not found")
            sys.exit(1)
        logger.info(f"Using existing solutions: {solutions_path}")
    
    # Step 2: Run evaluation workflow
    if not args.skip_evaluation:
        eval_output_dir = run_evaluation_workflow(
            solutions_path=solutions_path,
            evaluator=args.evaluator,
            workflow=args.workflow,
            data_version=data_dir.name,
            template=args.evaluation_template,
            output_dir=output_dir / "evaluations",
            skip_validation=args.skip_validation,
            strict_validation=args.strict_validation
        )
    
    # Step 3: Compute metrics
    if args.compute_metrics:
        if expert_gradings_path and expert_gradings_path.exists():
            metrics_output = output_dir / "metrics.json"
            compute_metrics(
                solutions_path=solutions_path,
                expert_gradings_path=expert_gradings_path,
                evaluations_path=output_dir / "evaluations",
                output_path=metrics_output
            )
        else:
            logger.warning("--compute-metrics specified but expert gradings file not found")
            logger.warning(f"Looked in: {', '.join(str(p) for p in possible_gradings)}")
    
    # Summary
    print("\n" + "="*80)
    print("WORKFLOW COMPLETE!")
    print("="*80)
    print(f"Solutions: {solutions_path}")
    if not args.skip_evaluation:
        print(f"Evaluations: {output_dir / 'evaluations'}")
    if args.compute_metrics and expert_gradings_path and expert_gradings_path.exists():
        print(f"Metrics: {output_dir / 'metrics'}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

