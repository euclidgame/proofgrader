#!/usr/bin/env python3
"""
ProofGrader Generation Script

Generate solutions from one or more models.
Completely independent of evaluation - generate once, evaluate many times.

Examples:
    # Generate from multiple models
    python scripts/generate.py \
        --data-dir data/my_dataset \
        --models gpt-4 o3 gemini-2.5-pro
    
    # Generate from single model
    python scripts/generate.py \
        --data-dir data/my_dataset \
        --models gpt-4
    
    # Custom output location
    python scripts/generate.py \
        --data-dir data/my_dataset \
        --models gpt-4 \
        --output custom_solutions.jsonl
"""

import sys
import argparse
import logging
import json
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from proofgrader import InferenceEngine, config, PromptFormatter
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
    """Read JSONL file."""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(records: List[Dict[str, Any]], path: Path) -> None:
    """Write JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    logger.info(f"Wrote {len(records)} records to {path}")


def main():
    """Main generation function."""
    parser = argparse.ArgumentParser(
        description="Generate mathematical proofs and solutions (generation only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from multiple models
  python scripts/generate.py \\
      --data-dir data/my_dataset \\
      --models gpt-4 o3 gemini-2.5-pro
  
  # Generate from single model
  python scripts/generate.py \\
      --data-dir data/my_dataset \\
      --models gpt-4
  
  # Custom template
  python scripts/generate.py \\
      --data-dir data/my_dataset \\
      --models gpt-4 \\
      --template math
  
  # List templates
  python scripts/generate.py --list-templates
        """
    )
    
    # Data directory option (simpler interface)
    parser.add_argument(
        "--data-dir", type=str, required=True,
        help="Directory containing problems.jsonl"
    )
    
    # Model options (now supports multiple!)
    parser.add_argument(
        "--models", type=str, nargs='+', required=True,
        help="One or more model names for generation"
    )
    
    # Output options
    parser.add_argument(
        "--output", type=str,
        help="Output file path (default: data-dir/model_solutions.jsonl)"
    )
    
    # Template options
    parser.add_argument(
        "--template", type=str, default="default",
        help="Prompt template to use (default: default)"
    )
    parser.add_argument(
        "--template-config", type=str,
        help="Path to template YAML config file"
    )
    parser.add_argument(
        "--list-templates", action="store_true",
        help="List available templates and exit"
    )
    parser.add_argument(
        "--template-info", type=str,
        help="Show detailed info about a specific template"
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
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable caching of previous results"
    )
    
    # Validation options
    parser.add_argument(
        "--strict-validation", action="store_true",
        help="Exit immediately if validation fails"
    )
    parser.add_argument(
        "--skip-validation", action="store_true",
        help="Skip validation checks"
    )
    
    # Logging options
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
    
    # Setup paths
    data_dir = Path(args.data_dir)
    problems_path = data_dir / "problems.jsonl"
    
    if not problems_path.exists():
        logger.error(f"problems.jsonl not found in {data_dir}")
        sys.exit(1)
    
    # Output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = data_dir / "model_solutions.jsonl"
    
    # Print overview
    print("\n" + "="*80)
    print("SOLUTION GENERATION")
    print("="*80)
    print(f"Data directory: {data_dir}")
    print(f"Problems: {problems_path}")
    print(f"Models: {args.models}")
    print(f"Output: {output_path}")
    print(f"Template: {args.template}")
    print(f"Validation: {'Skipped' if args.skip_validation else ('Strict' if args.strict_validation else 'Enabled')}")
    print("="*80 + "\n")
    
    # Validate problems
    if not args.skip_validation:
        logger.info("🔍 Validating input problems...")
        validator = DataValidator()
        problems_validation = validator.validate_problems(problems_path)
        
        if not problems_validation['valid']:
            logger.error("❌ Problem validation failed!")
            if problems_validation.get('duplicate_ids'):
                logger.error(f"  Duplicate IDs: {problems_validation['duplicate_ids'][:5]}")
            if problems_validation.get('missing_id', 0) > 0:
                logger.error(f"  {problems_validation['missing_id']} problems without IDs")
            
            if args.strict_validation:
                sys.exit(1)
        else:
            logger.info("✓ Problem validation passed\n")
    
    # Generate solutions
    all_solutions = []
    
    for model_idx, model in enumerate(args.models):
        logger.info(f"{'='*80}")
        logger.info(f"Generating with {model} ({model_idx+1}/{len(args.models)})")
        logger.info(f"{'='*80}\n")
        
        # Temporary output for this model
        temp_output = output_path.parent / f"temp_{model.replace('/', '_')}.jsonl"
        
        # Configure engine
        original_dataset = config.dataset_name
        original_output = config.output_path
        config.dataset_name = str(problems_path)
        config.output_path = str(temp_output)
        
        if args.template_config:
            config.prompt_template_config = args.template_config
        
        try:
            engine = InferenceEngine(model_name=model)
            
            # Run inference (one response per problem)
            success = engine.run_inference(
                template=args.template,
                max_concurrent=args.max_concurrent,
                use_cache=not args.no_cache,
                n_sampling=1,  # One solution per model
                max_examples=args.max_problems
            )
            
            if not success:
                logger.error(f"Generation failed for {model}")
                continue
            
            # Read and reformat
            if temp_output.exists():
                generated = read_jsonl(temp_output)
                
                for record in generated:
                    problem_id = record.get('id', record.get('problem_id', 'unknown'))
                    
                    # Extract solution
                    if 'responses' in record and isinstance(record['responses'], list):
                        solution_text = record['responses'][0] if record['responses'] else ''
                    else:
                        solution_text = record.get('response', record.get('solution', ''))
                    
                    # Create solution record, preserving all fields
                    solution_record = {
                        'problem_id': problem_id,
                        'generator': model,
                        'solution': solution_text,
                        'problem': record.get('problem', record.get('question', '')),
                        'model': model,
                        'generation_metadata': record.get('generation_info', {}),
                        'reference_solutions': record.get('reference_solutions'),
                        **{k: v for k, v in record.items()
                           if k not in ['id', 'problem', 'question', 'response', 'responses',
                                        'generation_info', 'token_usage', 'solution']}
                    }
                    
                    # Remove None values
                    solution_record = {k: v for k, v in solution_record.items() if v is not None}
                    all_solutions.append(solution_record)
                
                # Clean up temp file
                temp_output.unlink()
                logger.info(f"✓ Generated {len([s for s in all_solutions if s['generator'] == model])} solutions\n")
                
        except Exception as e:
            logger.error(f"Error generating with {model}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Restore config
            config.dataset_name = original_dataset
            config.output_path = original_output
    
    if not all_solutions:
        logger.error("No solutions generated!")
        sys.exit(1)
    
    # Write all solutions
    write_jsonl(all_solutions, output_path)
    
    # Validate
    if not args.skip_validation:
        logger.info("\n🔍 Validating generated solutions...")
        validator = DataValidator()
        solutions_validation = validator.validate_solutions(output_path, problems_path)
        
        if not solutions_validation['valid']:
            logger.warning("⚠️  Solution validation found issues")
            if solutions_validation.get('duplicate_composite_ids', 0) > 0:
                logger.error("  CRITICAL: Duplicate solution IDs!")
            if solutions_validation.get('orphan_solutions'):
                logger.warning(f"  WARNING: {len(solutions_validation['orphan_solutions'])} orphan solutions")
            
            if args.strict_validation:
                sys.exit(1)
        else:
            logger.info("✓ Solution validation passed")
    
    # Summary
    print("\n" + "="*80)
    print("GENERATION COMPLETE!")
    print("="*80)
    print(f"Solutions: {output_path}")
    print(f"Total: {len(all_solutions)} solutions")
    print(f"Problems: {len(set(s['problem_id'] for s in all_solutions))}")
    print(f"Models: {len(set(s['generator'] for s in all_solutions))}")
    print("="*80)
    print("\nNext step - Evaluate:")
    print(f"  python scripts/evaluate.py \\")
    print(f"    --data-dir {data_dir} \\")
    print(f"    --model gemini-2.5-pro")
    print("="*80 + "\n")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
