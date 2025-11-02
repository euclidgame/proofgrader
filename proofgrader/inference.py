"""Simplified main inference script - async batch mode only."""

import json
import logging
import argparse
import time
import signal
import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from tqdm import tqdm

from .config import config
from .dataset_handler import DatasetHandler
from .prompt_formatter import PromptFormatter
from .api_client import APIClient

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


# BatchResultSaver removed - results are written all at once at the end

class ProgressTracker:
    """Thread-safe progress tracker for async operations."""
    
    def __init__(self, total: int, desc: str = "Progress"):
        self.total = total
        self.desc = desc
        self.completed = 0
        self.start_time = time.time()
        self.last_update = 0
        self.lock = threading.Lock()
        self.update_interval = 0.5
        self.last_count = 0
    
    def update(self, count: int = 1):
        """Update progress count."""
        with self.lock:
            self.completed += count
            current_time = time.time()
            
            if current_time - self.last_update >= self.update_interval or self.completed == self.total:
                self._print_progress()
                self.last_update = current_time
    
    def set_completed(self, completed: int):
        """Set the exact number of completed items."""
        with self.lock:
            self.completed = completed
            current_time = time.time()
            
            if current_time - self.last_update >= self.update_interval or self.completed == self.total:
                self._print_progress()
                self.last_update = current_time
    
    def _print_progress(self):
        """Print current progress."""
        elapsed = time.time() - self.start_time
        percentage = (self.completed / self.total) * 100
        
        if elapsed > 0:
            overall_rate = self.completed / elapsed
            if hasattr(self, 'rates'):
                self.rates.append(overall_rate)
                if len(self.rates) > 5:
                    self.rates.pop(0)
                rate = sum(self.rates) / len(self.rates)
            else:
                self.rates = [overall_rate]
                rate = overall_rate
        else:
            rate = 0
        
        if rate > 0:
            eta = (self.total - self.completed) / rate
            if eta > 3600:
                eta_str = f"ETA: {eta/3600:.1f}h"
            elif eta > 60:
                eta_str = f"ETA: {eta/60:.1f}m"
            else:
                eta_str = f"ETA: {eta:.0f}s"
        else:
            eta_str = "ETA: --"
        
        print(f"\r{self.desc}: {self.completed}/{self.total} ({percentage:.1f}%) | {rate:.1f}/s | {eta_str}", end='', flush=True)
    
    def finish(self):
        """Mark progress as complete."""
        with self.lock:
            self.completed = self.total
            elapsed = time.time() - self.start_time
            rate = self.completed / elapsed if elapsed > 0 else 0
            print(f"\r{self.desc}: {self.completed}/{self.total} (100.0%) | {rate:.1f}/s | Completed in {elapsed:.1f}s")


class InferenceEngine:
    """Simplified inference engine - async batch mode only."""
    
    def __init__(self, model_name: str = "gemini-2.5-pro", model_config=None):
        self.config = model_config or config
        self.model_name = model_name
        self.api_client = APIClient(default_model=self.model_name)
        self.dataset_handler = DatasetHandler(
            self.config.dataset_name,
            self.config.dataset_config,
            self.config.dataset_split
        )
        self.prompt_formatter = PromptFormatter(self.config.prompt_template_config)
        
    def _inputs_match(self, input_data: Dict[str, Any], cached_data: Dict[str, Any]) -> bool:
        """
        Check if input data matches cached data by comparing all input fields.
        
        Args:
            input_data: Current input problem data
            cached_data: Cached result data
            
        Returns:
            True if all input fields match
        """
        # Compare all fields except response, generation_info, token_usage, errors
        excluded_fields = {'response', 'responses', 'generation_info', 'token_usage', 'errors'}
        
        for key, value in input_data.items():
            if key in excluded_fields:
                continue
            cached_value = cached_data.get(key)
            if cached_value != value:
                logger.debug(f"Input mismatch for key '{key}': {value} != {cached_value}")
                return False
        
        return True
    
    def _is_result_valid(self, result: Dict[str, Any], input_data: Dict[str, Any], 
                        template: str, model: str) -> bool:
        """
        Check if cached result is valid for current configuration.
        
        Args:
            result: Cached result
            input_data: Current input data
            template: Current template name
            model: Current model name
            
        Returns:
            True if result is valid and can be reused
        """
        # Check basic structure
        if not result.get('id'):
            return False
        
        # Check if response exists and is valid
        response = result.get('response')
        responses = result.get('responses')
        
        if not response and not responses:
            return False
        
        # Check response content
        if response is not None:
            if not response or response.startswith('ERROR:'):
                return False
        elif responses is not None:
            if not isinstance(responses, list) or not responses:
                return False
            for resp in responses:
                if not resp or resp.startswith('ERROR:'):
                    return False
        
        # Check generation_info matches current config
        gen_info = result.get('generation_info', {})
        if gen_info.get('model') != model:
            logger.debug(f"Model mismatch: {gen_info.get('model')} != {model}")
            return False
        if gen_info.get('template') != template:
            logger.debug(f"Template mismatch: {gen_info.get('template')} != {template}")
            return False
        
        # Check if all input fields match
        if not self._inputs_match(input_data, result):
            return False
        
        return True
    
    def load_existing_results(self, output_path: str, input_data_by_id: Dict[str, Dict[str, Any]], 
                             template: str, model: str) -> tuple[Dict[str, Dict[str, Any]], Set[str]]:
        """
        Load existing results and validate against current input data.
        
        Args:
            output_path: Path to output file
            input_data_by_id: Current input data indexed by ID
            template: Current template name
            model: Current model name
            
        Returns:
            tuple: (valid_results_dict, invalid_ids_set)
        """
        output_file = Path(output_path)
        valid_results = {}
        invalid_ids = set()
        
        if not output_file.exists():
            logger.info(f"No existing results found at {output_path}")
            return valid_results, invalid_ids
        
        logger.info(f"Loading and validating existing results from {output_path}")
        
        total_lines = 0
        valid_count = 0
        invalid_count = 0
        
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    total_lines += 1
                    
                    try:
                        result = json.loads(line)
                        problem_id = result.get('id')
                        
                        if not problem_id:
                            invalid_count += 1
                            continue
                        
                        # Get corresponding input data
                        input_data = input_data_by_id.get(problem_id)
                        if not input_data:
                            logger.debug(f"No input data for cached result {problem_id}")
                            invalid_ids.add(problem_id)
                            invalid_count += 1
                            continue
                        
                        # Validate result
                        if self._is_result_valid(result, input_data, template, model):
                            valid_results[problem_id] = result
                            valid_count += 1
                        else:
                            invalid_ids.add(problem_id)
                            invalid_count += 1
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON on line {line_num}: {e}")
                        invalid_count += 1
                        continue
            
            logger.info(f"Results validation summary:")
            logger.info(f"  Total lines: {total_lines}")
            logger.info(f"  Valid (reusable): {valid_count}")
            logger.info(f"  Invalid (will reprocess): {invalid_count}")
            
            return valid_results, invalid_ids
            
        except Exception as e:
            logger.error(f"Error loading results: {e}")
            return {}, set()
    
    def filter_completed_problems(self, problems: List[Dict[str, Any]], 
                                 existing_results: Dict[str, Dict[str, Any]]) -> tuple:
        """Filter out problems that have valid cached results."""
        remaining = []
        completed = []
        
        for problem in problems:
            problem_id = problem.get('id')
            if problem_id and problem_id in existing_results:
                completed.append(problem)
            else:
                remaining.append(problem)
        
        if completed:
            logger.info(f"Skipping {len(completed)} completed problems")
        if remaining:
            logger.info(f"Processing {len(remaining)} problems")
        
        return remaining, completed
    
    def _rewrite_output_with_valid_results(self, valid_results: Dict[str, Dict[str, Any]], output_path: str):
        """Rewrite output file with only valid results."""
        output_file = Path(output_path)
        backup_path = output_file.with_suffix(output_file.suffix + '.backup')
        
        # Create backup
        if backup_path.exists():
            backup_path.unlink()
        if output_file.exists():
            output_file.rename(backup_path)
            logger.info(f"Created backup: {backup_path}")
        
        # Write valid results
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                for result in valid_results.values():
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
            logger.info(f"Rewrote output with {len(valid_results)} valid results")
        except Exception as e:
            logger.error(f"Error rewriting output: {e}")
            if backup_path.exists():
                backup_path.rename(output_file)
                logger.info("Restored backup")
    
    async def process_problems_async(self, problems: List[Dict[str, Any]], 
                                    template: str = "default",
                                    max_concurrent: int = 10,
                                    n_sampling: int = 1) -> List[Dict[str, Any]]:
        """
        Process problems asynchronously using remote API.
        
        Args:
            problems: List of problems to process
            template: Template name to use
            max_concurrent: Maximum concurrent requests
            n_sampling: Number of samples per problem
            
        Returns:
            List of results
        """
        logger.info(f"Processing {len(problems)} problems asynchronously")
        logger.info(f"Settings: model={self.model_name}, template={template}, concurrent={max_concurrent}, n_sampling={n_sampling}")
        
        # Format all prompts
        print("📝 Formatting prompts...")
        prompts = []
        problem_indices = []
        
        for problem_idx, problem in enumerate(tqdm(problems, desc="Formatting prompts")):
            prompt = self.prompt_formatter.format_problem(problem, template)
            for _ in range(n_sampling):
                prompts.append(prompt)
                problem_indices.append(problem_idx)
        
        # Generate responses in batch
        print(f"🚀 Generating {len(prompts)} responses...")
        progress_tracker = ProgressTracker(len(prompts), "Generating responses")
        
        def progress_callback(completed, total):
            progress_tracker.set_completed(completed)
        
        all_response_texts, all_token_usages = await self.api_client.get_responses_batch(
            prompts,
            model_name=self.model_name,
            max_concurrent=max_concurrent,
            progress_callback=progress_callback,
            return_usage=True
        )
        
        progress_tracker.finish()
        
        # Group responses and create results
        print("📊 Creating result records...")
        results = []
        
        for problem_idx, problem in enumerate(tqdm(problems, desc="Processing results")):
            # Collect responses for this problem
            problem_responses = []
            problem_usages = []
            
            for i, (resp_idx, resp_text, usage) in enumerate(zip(problem_indices, all_response_texts, all_token_usages)):
                if resp_idx == problem_idx:
                    problem_responses.append(resp_text)
                    problem_usages.append(usage)
            
            # Create result record (preserves input + adds response/generation_info)
            result = self._create_result_record(problem, problem_responses, problem_usages, template)
            results.append(result)
        
        return results
    
    def _create_result_record(self, input_data: Dict[str, Any], 
                            responses: List[str], usages: List[Dict], 
                            template: str) -> Dict[str, Any]:
        """
        Create result record by preserving input and adding response + generation_info.
        
        Args:
            input_data: Original input data (preserved as-is)
            responses: List of response texts
            usages: List of token usage dicts
            template: Template name used
            
        Returns:
            Result dict with input fields + response + generation_info
        """
        # Start with a copy of input data (preserves all fields)
        result = dict(input_data)
        
        # Add response(s)
        if len(responses) == 1:
            result['response'] = responses[0]
        else:
            result['responses'] = responses
        
        # Add generation_info
        result['generation_info'] = {
            'model': self.model_name,
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
            'template': template,
            'n_sampling': len(responses)
        }
        
        # Add token usage
        if usages:
            if len(usages) == 1:
                result['token_usage'] = usages[0]
            else:
                result['token_usage'] = usages
        
        return result
    
    def run_inference(self, template: str = "default", 
                     max_concurrent: int = 10,
                     use_cache: bool = True, 
                     n_sampling: int = 1,
                     max_examples: Optional[int] = None) -> bool:
        """
        Run the complete inference pipeline (async batch mode only).
        
        Args:
            template: Template name to use
            max_concurrent: Maximum concurrent requests
            use_cache: Whether to use caching
            n_sampling: Number of samples per problem
            max_examples: Optional limit on number of examples
            
        Returns:
            True if successful
        """
        try:
            # Validate template
            if not self.prompt_formatter.validate_template(template):
                logger.error(f"Invalid template: {template}")
                available = self.prompt_formatter.get_available_templates()
                logger.info(f"Available templates: {available}")
                return False
            
            # Load dataset
            print("📚 Loading dataset...")
            problems = self.dataset_handler.get_problems(
                problem_field=self.config.problem_field,
                max_examples=max_examples or self.config.max_examples
            )
            logger.info(f"Loaded {len(problems)} problems from {self.config.dataset_name}")
            
            # Build input data index by ID for caching validation
            input_data_by_id = {p.get('id'): p for p in problems if p.get('id')}
            
            # Set up caching
            valid_results = []
            if use_cache:
                print("🗂️  Loading existing results...")
                valid_results, invalid_ids = self.load_existing_results(
                    self.config.output_path, 
                    input_data_by_id,
                    template,
                    self.model_name
                )
                
                problems, completed = self.filter_completed_problems(problems, valid_results)
                
                # Clean up output file
                if valid_results:
                    self._rewrite_output_with_valid_results(valid_results, self.config.output_path)
                
                if not problems:
                    logger.info("All problems completed! No work to do.")
                    return True
            
            # Show dataset and template info
            dataset_info = self.dataset_handler.get_dataset_info()
            logger.info(f"Dataset: {dataset_info['dataset_name']}")
            logger.info(f"Fields: {dataset_info['features']}")
            
            template_info = self.prompt_formatter.get_template_info(template)
            if 'error' not in template_info:
                logger.info(f"Template: {template_info.get('name', template)}")
                logger.info(f"Variables: {template_info.get('variables', [])}")
            
            # Process problems
            print(f"🔄 Processing {len(problems)} problems...")
            start_time = time.time()
            
            results = asyncio.run(self.process_problems_async(
                problems, template, max_concurrent, n_sampling
            ))
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"Processing completed in {processing_time:.2f}s")
            logger.info(f"Average: {processing_time/len(problems):.2f}s per problem")
            
            # Show stats
            stats = self.api_client.get_stats()
            logger.info(f"API stats: {stats}")
            
            # Write all results to file
            if results:
                output_file = Path(self.config.output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.config.output_path, 'w', encoding='utf-8') as f:
                    for result in results:
                        json_line = json.dumps(result, ensure_ascii=False)
                        f.write(json_line + '\n')
                
                logger.info(f"💾 Saved {len(results)} results to {self.config.output_path}")
            
            print("✅ Inference completed successfully!")
            return True
                
        except Exception as e:
            logger.error(f"Error in inference pipeline: {e}")
            import traceback
            traceback.print_exc()
            return False


def signal_handler(signum, frame):
    """Handle interrupt signals."""
    logger.info("Received interrupt signal, shutting down...")
    sys.exit(0)


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description="Simplified Inference Pipeline - Async Batch Mode Only",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--model", type=str, default="gemini-2.5-pro",
                       help="Model name to use (default: gemini-2.5-pro)")
    parser.add_argument("--dataset", type=str, help="Dataset name or path to JSONL file")
    parser.add_argument("--dataset-config", type=str, help="Dataset configuration/subset")
    parser.add_argument("--dataset-split", type=str, default="train", help="Dataset split")
    parser.add_argument("--problem-field", type=str, help="Field containing the problem")
    parser.add_argument("--max-examples", type=int, help="Maximum number of examples")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--template", type=str, default="default", help="Prompt template")
    parser.add_argument("--max-concurrent", type=int, default=100,
                       help="Maximum concurrent requests")
    parser.add_argument("--template-config", type=str, help="Path to template YAML")
    parser.add_argument("--max-tokens", type=int, help="Maximum tokens to generate")
    parser.add_argument("--temperature", type=float, help="Temperature for generation")
    parser.add_argument("--no-cache", action="store_true",
                       help="Disable caching")
    parser.add_argument("--log-level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set logging level")
    parser.add_argument("--n-sampling", type=int, default=1,
                       help="Number of samples per problem")
    parser.add_argument("--list-templates", action="store_true",
                       help="List available templates")
    parser.add_argument("--template-info", type=str, help="Show template details")
    
    args = parser.parse_args()
    
    # Update logging level
    numeric_level = getattr(logging, args.log_level.upper(), None)
    logger.setLevel(numeric_level)
    logging.getLogger().setLevel(numeric_level)
    
    # Update config
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
    
    # Handle template listing/info
    if args.list_templates or args.template_info:
        formatter = PromptFormatter(config.prompt_template_config)
        
        if args.list_templates:
            templates = formatter.get_template_info()
            print("\nAvailable templates:")
            print("=" * 80)
            for name, info in templates.items():
                print(f"{name:20} - {info['description']}")
                print(f"{'':20}   Variables: {', '.join(info.get('variables', []))}")
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
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run inference
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

