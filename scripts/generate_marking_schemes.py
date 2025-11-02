#!/usr/bin/env python3
"""
Generate Marking Schemes for Problems

This script generates marking schemes for each problem in problems.jsonl
using the marking_scheme template and adds them as a new field.

Examples:
    # Generate marking schemes and save to new file
    python scripts/generate_marking_schemes.py \
        --data-dir data/test_data \
        --model gemini-2.5-pro
    
    # Use specific template
    python scripts/generate_marking_schemes.py \
        --data-dir data/test_data \
        --model gpt-4o \
        --template marking_scheme_from_problem
    
    # Overwrite original problems.jsonl
    python scripts/generate_marking_schemes.py \
        --data-dir data/test_data \
        --model gemini-2.5-pro \
        --overwrite
"""

import sys
import argparse
import logging
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from proofgrader.prompt_formatter import PromptFormatter
from proofgrader.config import config
from proofgrader.api_client import APIClient

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


async def generate_marking_schemes(
    problems: List[Dict[str, Any]],
    model_name: str,
    template: str,
    prompt_formatter: PromptFormatter,
    max_concurrent: int = 10
) -> List[str]:
    """
    Generate marking schemes for problems using the marking_scheme template.
    
    Args:
        problems: List of problem records
        model_name: Model to use for generation
        template: Template name
        prompt_formatter: PromptFormatter instance
        max_concurrent: Maximum concurrent requests
        
    Returns:
        List of generated marking schemes
    """
    api_client = APIClient(default_model=model_name)
    
    # Format prompts
    logger.info("📝 Formatting prompts...")
    prompts = []
    for problem in problems:
        # Check what the template needs
        template_info = prompt_formatter.get_template_info(template)
        variables = template_info.get('variables', [])
        
        # Prepare data for template
        data = {
            'problem': problem.get('problem', problem.get('question', '')),
        }
        
        # Add solution if template needs it
        if 'solution' in variables or 'reference_solution' in variables:
            solution = problem.get('reference_solutions', problem.get('solution', ''))
            data['solution'] = solution
            data['reference_solution'] = solution
        
        prompt = prompt_formatter.format_problem(data, template)
        prompts.append(prompt)
    
    # Generate marking schemes
    logger.info(f"🚀 Generating {len(prompts)} marking schemes with {model_name}...")
    marking_schemes = await api_client.get_responses_batch(
        prompts,
        model_name=model_name,
        max_concurrent=max_concurrent
    )
    
    return marking_schemes


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate marking schemes for problems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate marking schemes
  python scripts/generate_marking_schemes.py \\
      --data-dir data/test_data \\
      --model gemini-2.5-pro
  
  # Use different template
  python scripts/generate_marking_schemes.py \\
      --data-dir data/test_data \\
      --model gpt-4o \\
      --template marking_scheme_from_problem
  
  # Overwrite original problems.jsonl (careful!)
  python scripts/generate_marking_schemes.py \\
      --data-dir data/test_data \\
      --model gemini-2.5-pro \\
      --overwrite
        """
    )
    
    # Required options
    parser.add_argument(
        "--data-dir", type=str, required=True,
        help="Directory containing problems.jsonl"
    )
    parser.add_argument(
        "--model", type=str, default="gemini-2.5-pro",
        help="Model to use for generating marking schemes (default: gemini-2.5-pro)"
    )
    
    # Template options
    parser.add_argument(
        "--template", type=str, default="marking_scheme",
        help="Template to use (default: marking_scheme)"
    )
    parser.add_argument(
        "--template-config", type=str,
        help="Path to template YAML config file"
    )
    
    # Output options
    parser.add_argument(
        "--output", type=str,
        help="Output file path (default: data-dir/problems_with_marking_schemes.jsonl)"
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite original problems.jsonl (default: create new file)"
    )
    
    # Performance options
    parser.add_argument(
        "--max-concurrent", type=int, default=10,
        help="Maximum concurrent requests (default: 10)"
    )
    parser.add_argument(
        "--max-problems", type=int,
        help="Limit number of problems (for testing)"
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
    
    # Setup paths
    data_dir = Path(args.data_dir)
    problems_path = data_dir / "problems.jsonl"
    
    if not problems_path.exists():
        logger.error(f"problems.jsonl not found in {data_dir}")
        sys.exit(1)
    
    # Output path
    if args.overwrite:
        output_path = problems_path
        logger.warning("⚠️  Will OVERWRITE original problems.jsonl")
    elif args.output:
        output_path = Path(args.output)
    else:
        output_path = data_dir / "problems_with_marking_schemes.jsonl"
    
    # Configure template
    if args.template_config:
        config.prompt_template_config = args.template_config
    
    # Print overview
    print("\n" + "="*80)
    print("MARKING SCHEME GENERATION")
    print("="*80)
    print(f"Data directory: {data_dir}")
    print(f"Problems: {problems_path}")
    print(f"Model: {args.model}")
    print(f"Template: {args.template}")
    print(f"Output: {output_path}")
    print("="*80 + "\n")
    
    # Load problems
    logger.info("📚 Loading problems...")
    problems = read_jsonl(problems_path)
    
    if args.max_problems:
        problems = problems[:args.max_problems]
        logger.info(f"Limited to {len(problems)} problems for testing")
    
    logger.info(f"Loaded {len(problems)} problems")
    
    # Check if problems already have marking schemes
    with_schemes = sum(1 for p in problems if p.get('marking_scheme'))
    if with_schemes > 0:
        logger.warning(f"⚠️  {with_schemes}/{len(problems)} problems already have marking schemes")
        if not args.overwrite:
            response = input("Continue and replace them? [y/N]: ")
            if response.lower() != 'y':
                logger.info("Cancelled.")
                sys.exit(0)
    
    # Initialize prompt formatter
    prompt_formatter = PromptFormatter(config.prompt_template_config)
    
    # Validate template
    if not prompt_formatter.validate_template(args.template):
        logger.error(f"Invalid template: {args.template}")
        available = prompt_formatter.get_available_templates()
        logger.info(f"Available templates: {available}")
        sys.exit(1)
    
    # Show template info
    template_info = prompt_formatter.get_template_info(args.template)
    logger.info(f"Template: {template_info.get('name', args.template)}")
    logger.info(f"Variables: {template_info.get('variables', [])}")
    
    # Generate marking schemes
    try:
        marking_schemes = asyncio.run(generate_marking_schemes(
            problems,
            args.model,
            args.template,
            prompt_formatter,
            args.max_concurrent
        ))
        
        logger.info(f"✓ Generated {len(marking_schemes)} marking schemes")
        
        # Add marking schemes to problems
        logger.info("📝 Adding marking schemes to problems...")
        problems_with_schemes = []
        for problem, marking_scheme in zip(problems, marking_schemes):
            problem_copy = dict(problem)
            problem_copy['marking_scheme'] = marking_scheme
            problems_with_schemes.append(problem_copy)
        
        # Write output
        write_jsonl(problems_with_schemes, output_path)
        
        # Summary
        print("\n" + "="*80)
        print("MARKING SCHEME GENERATION COMPLETE!")
        print("="*80)
        print(f"Output: {output_path}")
        print(f"Problems: {len(problems_with_schemes)}")
        print(f"Model: {args.model}")
        print("="*80)
        
        if not args.overwrite and output_path != problems_path:
            print(f"\n💡 To use these marking schemes, update your problems.jsonl:")
            print(f"   mv {output_path} {problems_path}")
        
        print("\n")
        
    except Exception as e:
        logger.error(f"Error generating marking schemes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

