"""Data validation utilities for ensuring ID integrity across pipeline stages."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read JSONL file and return list of records."""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


class DataValidator:
    """Validates data integrity across pipeline stages."""
    
    def __init__(self):
        self.issues = defaultdict(list)
        self.stats = {}
    
    def validate_problems(self, problems_path: Path) -> Dict[str, Any]:
        """Validate problem data."""
        logger.info(f"Validating problems: {problems_path}")
        
        if not problems_path.exists():
            self.issues['missing_files'].append(str(problems_path))
            return {'valid': False, 'error': 'File not found'}
        
        problems = read_jsonl(problems_path)
        problem_ids = []
        duplicate_ids = []
        missing_problem_field = []
        
        for i, problem in enumerate(problems):
            # Check for ID
            pid = problem.get('id')
            if not pid:
                missing_problem_field.append(i)
            else:
                problem_ids.append(pid)
            
            # Check for problem text
            if 'problem' not in problem and 'question' not in problem:
                self.issues['missing_problem_text'].append((i, pid))
        
        # Check for duplicate IDs
        id_counts = Counter(problem_ids)
        duplicate_ids = [pid for pid, count in id_counts.items() if count > 1]
        
        result = {
            'total': len(problems),
            'unique_ids': len(set(problem_ids)),
            'duplicate_ids': duplicate_ids,
            'missing_id': len(missing_problem_field),
            'valid': len(duplicate_ids) == 0 and len(missing_problem_field) == 0
        }
        
        self.stats['problems'] = result
        
        if not result['valid']:
            if duplicate_ids:
                logger.warning(f"  ⚠ Found {len(duplicate_ids)} duplicate problem IDs")
            if missing_problem_field:
                logger.warning(f"  ⚠ Found {len(missing_problem_field)} problems without ID")
        else:
            logger.info(f"  ✓ All {result['total']} problems have valid unique IDs")
        
        return result
    
    def validate_solutions(
        self, 
        solutions_path: Path, 
        problems_path: Path = None
    ) -> Dict[str, Any]:
        """Validate solution data and optionally check against problems."""
        logger.info(f"Validating solutions: {solutions_path}")
        
        if not solutions_path.exists():
            self.issues['missing_files'].append(str(solutions_path))
            return {'valid': False, 'error': 'File not found'}
        
        solutions = read_jsonl(solutions_path)
        
        # Collect IDs
        composite_ids = []
        missing_fields = []
        problem_ids = set()
        
        for i, sol in enumerate(solutions):
            # Extract fields
            problem_id = sol.get('problem_id') or sol.get('id')
            generator = sol.get('generator') or sol.get('model')
            response_idx = sol.get('response_idx', 0)
            
            # Check required fields
            issues = []
            if not problem_id:
                issues.append('problem_id/id')
            if not generator:
                issues.append('generator/model')
            if 'solution' not in sol and 'response' not in sol and 'responses' not in sol:
                issues.append('solution/response')
            
            if issues:
                missing_fields.append((i, issues))
            else:
                composite_ids.append((problem_id, generator, response_idx))
                problem_ids.add(problem_id)
        
        # Check for duplicate composite IDs
        id_counts = Counter(composite_ids)
        duplicate_ids = [cid for cid, count in id_counts.items() if count > 1]
        
        result = {
            'total': len(solutions),
            'unique_composite_ids': len(set(composite_ids)),
            'unique_problem_ids': len(problem_ids),
            'duplicate_composite_ids': len(duplicate_ids),
            'missing_fields': len(missing_fields),
            'valid': len(duplicate_ids) == 0 and len(missing_fields) == 0
        }
        
        # Validate against problems if provided
        if problems_path and problems_path.exists():
            problems = read_jsonl(problems_path)
            valid_problem_ids = {p.get('id') for p in problems if p.get('id')}
            orphan_solutions = problem_ids - valid_problem_ids
            
            if orphan_solutions:
                result['orphan_solutions'] = list(orphan_solutions)
                result['valid'] = False
                logger.warning(f"  ⚠ Found {len(orphan_solutions)} solutions referencing non-existent problems")
        
        self.stats['solutions'] = result
        
        if not result['valid']:
            if duplicate_ids:
                logger.warning(f"  ⚠ Found {len(duplicate_ids)} duplicate solution IDs")
                logger.warning(f"     Examples: {duplicate_ids[:3]}")
            if missing_fields:
                logger.warning(f"  ⚠ Found {len(missing_fields)} solutions with missing fields")
                logger.warning(f"     Examples: {missing_fields[:3]}")
        else:
            logger.info(f"  ✓ All {result['total']} solutions have valid unique IDs")
        
        return result
    
    def validate_evaluations(
        self,
        evaluations_dir: Path,
        solutions_path: Path = None
    ) -> Dict[str, Any]:
        """Validate evaluation data."""
        logger.info(f"Validating evaluations: {evaluations_dir}")
        
        if not evaluations_dir.exists():
            self.issues['missing_files'].append(str(evaluations_dir))
            return {'valid': False, 'error': 'Directory not found'}
        
        # Collect all evaluations
        all_evals = []
        eval_files = list(evaluations_dir.glob("*.eval.jsonl"))
        
        for eval_file in eval_files:
            evals = read_jsonl(eval_file)
            all_evals.extend(evals)
        
        if not all_evals:
            logger.warning(f"  ⚠ No evaluation files found")
            return {'valid': False, 'total': 0, 'error': 'No evaluation files'}
        
        # Extract IDs
        eval_ids = []
        missing_score = []
        
        for i, eval_record in enumerate(all_evals):
            problem_id = eval_record.get('id') or eval_record.get('problem_id')
            
            # Try to extract generator from various fields
            generator = None
            if 'generator' in eval_record:
                generator = eval_record['generator']
            elif 'model' in eval_record:
                generator = eval_record['model']
            elif 'unique_id' in eval_record and '::' in eval_record['unique_id']:
                # Extract from composite ID
                parts = eval_record['unique_id'].split('::')
                if len(parts) >= 2:
                    generator = parts[1]
            
            response_idx = eval_record.get('response_idx', 0)
            
            if problem_id and generator:
                eval_ids.append((problem_id, generator, response_idx))
            
            # Check for score
            if 'score' not in eval_record:
                missing_score.append((i, problem_id))
        
        # Check for duplicates
        id_counts = Counter(eval_ids)
        duplicate_ids = [eid for eid, count in id_counts.items() if count > 1]
        
        result = {
            'total': len(all_evals),
            'files': len(eval_files),
            'unique_ids': len(set(eval_ids)),
            'duplicate_ids': len(duplicate_ids),
            'missing_score': len(missing_score),
            'valid': len(duplicate_ids) == 0 and len(missing_score) == 0
        }
        
        # Validate against solutions if provided
        if solutions_path and solutions_path.exists():
            solutions = read_jsonl(solutions_path)
            solution_ids = {
                (s.get('problem_id') or s.get('id'), 
                 s.get('generator') or s.get('model'),
                 s.get('response_idx', 0))
                for s in solutions
            }
            
            eval_id_set = set(eval_ids)
            missing_evals = solution_ids - eval_id_set
            extra_evals = eval_id_set - solution_ids
            
            if missing_evals:
                result['missing_evaluations'] = len(missing_evals)
                logger.warning(f"  ⚠ {len(missing_evals)} solutions without evaluations")
            
            if extra_evals:
                result['extra_evaluations'] = len(extra_evals)
                logger.warning(f"  ⚠ {len(extra_evals)} evaluations without matching solutions")
        
        self.stats['evaluations'] = result
        
        if result['valid']:
            logger.info(f"  ✓ All {result['total']} evaluations have valid IDs")
        else:
            if duplicate_ids:
                logger.warning(f"  ⚠ Found {len(duplicate_ids)} duplicate evaluation IDs")
        
        return result
    
    def validate_expert_gradings(
        self,
        gradings_path: Path,
        solutions_path: Path = None
    ) -> Dict[str, Any]:
        """Validate expert grading data."""
        logger.info(f"Validating expert gradings: {gradings_path}")
        
        if not gradings_path.exists():
            logger.info(f"  ℹ No expert gradings found (optional)")
            return {'valid': True, 'total': 0, 'optional': True}
        
        gradings = read_jsonl(gradings_path)
        
        grading_ids = []
        missing_fields = []
        
        for i, grading in enumerate(gradings):
            problem_id = grading.get('problem_id')
            model_name = grading.get('model_name') or grading.get('model') or grading.get('generator')
            score = grading.get('score')
            
            if not problem_id or not model_name:
                missing_fields.append(i)
            else:
                grading_ids.append((problem_id, model_name))
            
            if score is None:
                missing_fields.append(i)
        
        result = {
            'total': len(gradings),
            'unique_ids': len(set(grading_ids)),
            'missing_fields': len(missing_fields),
            'valid': len(missing_fields) == 0
        }
        
        self.stats['expert_gradings'] = result
        
        if result['valid']:
            logger.info(f"  ✓ All {result['total']} expert gradings have valid IDs")
        else:
            logger.warning(f"  ⚠ Found {len(missing_fields)} gradings with missing fields")
        
        return result
    
    def validate_full_pipeline(
        self,
        data_dir: Path,
        output_dir: Path = None
    ) -> Dict[str, Any]:
        """Validate entire pipeline data integrity."""
        logger.info("="*80)
        logger.info("DATA VALIDATION")
        logger.info("="*80)
        
        problems_path = data_dir / "problems.jsonl"
        
        # Find output dir
        if output_dir is None:
            output_dir = data_dir / "outputs"
        
        solutions_path = output_dir / "model_solutions.jsonl"
        evaluations_dir = output_dir / "evaluations"
        
        # Find expert gradings
        gradings_path = None
        for name in ['expert_gradings.jsonl', 'evaluation_merged.jsonl', 'evaluations.jsonl']:
            candidate = data_dir / name
            if candidate.exists():
                gradings_path = candidate
                break
        
        # Validate each stage
        problems_result = self.validate_problems(problems_path)
        solutions_result = self.validate_solutions(solutions_path, problems_path)
        evaluations_result = self.validate_evaluations(evaluations_dir, solutions_path)
        
        if gradings_path:
            gradings_result = self.validate_expert_gradings(gradings_path, solutions_path)
        else:
            gradings_result = {'valid': True, 'optional': True, 'total': 0}
        
        # Overall summary
        all_valid = all([
            problems_result.get('valid', False),
            solutions_result.get('valid', False),
            evaluations_result.get('valid', False),
            gradings_result.get('valid', True)  # Optional
        ])
        
        summary = {
            'overall_valid': all_valid,
            'problems': problems_result,
            'solutions': solutions_result,
            'evaluations': evaluations_result,
            'expert_gradings': gradings_result
        }
        
        logger.info("="*80)
        if all_valid:
            logger.info("✓ DATA VALIDATION PASSED")
        else:
            logger.warning("⚠ DATA VALIDATION FOUND ISSUES")
        logger.info(f"  Problems: {problems_result.get('total', 0)}")
        logger.info(f"  Solutions: {solutions_result.get('total', 0)}")
        logger.info(f"  Evaluations: {evaluations_result.get('total', 0)}")
        if not gradings_result.get('optional'):
            logger.info(f"  Expert Gradings: {gradings_result.get('total', 0)}")
        logger.info("="*80)
        
        return summary


def validate_data(data_dir: Path, output_dir: Path = None) -> bool:
    """
    Convenience function to validate data integrity.
    
    Args:
        data_dir: Directory containing problems.jsonl
        output_dir: Directory containing outputs (default: data_dir/outputs)
    
    Returns:
        True if all validations pass, False otherwise
    """
    validator = DataValidator()
    result = validator.validate_full_pipeline(data_dir, output_dir)
    return result['overall_valid']


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate ProofGrader data integrity")
    parser.add_argument("--data-dir", type=str, required=True, help="Data directory")
    parser.add_argument("--output-dir", type=str, help="Output directory (default: data-dir/outputs)")
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    valid = validate_data(data_dir, output_dir)
    sys.exit(0 if valid else 1)

