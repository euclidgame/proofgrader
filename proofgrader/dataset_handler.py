"""Simplified dataset handler for loading datasets from Hugging Face or local JSONL files."""

import logging
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datasets import load_dataset

logger = logging.getLogger(__name__)

class DatasetHandler:
    """Handler for loading datasets from Hugging Face or local JSONL files."""
    
    def __init__(self, dataset_name: str, dataset_config: Optional[str] = None, split: str = "train"):
        """
        Initialize dataset handler.
        
        Args:
            dataset_name: Name of the Hugging Face dataset (e.g., "squad", "glue") 
                         OR path to local JSONL file (e.g., "data/problems.jsonl")
            dataset_config: Optional dataset configuration/subset (ignored for local files)
            split: Dataset split to use (ignored for local files, default: "train")
        """
        self.dataset_name = dataset_name
        self.dataset_config = dataset_config
        self.split = split
        self.dataset = None
        self.is_local_file = self._is_local_file(dataset_name)
        
    def _is_local_file(self, dataset_name: str) -> bool:
        """Check if dataset_name refers to a local file."""
        # Check for common file extensions first (strongest indicator)
        if dataset_name.endswith(('.jsonl', '.json', '.txt', '.csv')):
            return True
        
        # Check if it's a path that actually exists
        if os.path.exists(dataset_name):
            return True
            
        # Check for explicit local path patterns
        if ('/' in dataset_name or '\\' in dataset_name):
            # Exclude HuggingFace org/model patterns (exactly 2 parts, no file extension, no explicit path)
            parts = dataset_name.split('/')
            if (len(parts) == 2 and 
                not dataset_name.startswith('./') and 
                not dataset_name.startswith('/') and
                '.' not in dataset_name and
                not os.path.exists(dataset_name)):
                # Likely HuggingFace org/model format
                return False
            # Everything else with path separators is treated as local path
            return True
            
        return False
        
    def _load_jsonl_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load data from a JSONL file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Local dataset file not found: {file_path}")
        
        data = []
        line_num = 0
        
        logger.info(f"Loading local JSONL file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        item = json.loads(line)
                        
                        # Skip metadata lines (first line might contain metadata)
                        if line_num == 1 and 'metadata' in item and len(item) == 1:
                            logger.info(f"Skipping metadata line: {item['metadata']}")
                            continue
                            
                        # Add index if not present
                        if 'id' not in item:
                            item['id'] = len(data)
                            
                        data.append(item)
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping invalid JSON on line {line_num}: {e}")
                        continue
                        
        except Exception as e:
            raise Exception(f"Error reading JSONL file {file_path} at line {line_num}: {e}")
        
        logger.info(f"Loaded {len(data)} examples from local file: {file_path}")
        return data
        
    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load dataset from Hugging Face or local JSONL file."""
        try:
            if self.is_local_file:
                # Load from local JSONL file
                data = self._load_jsonl_file(self.dataset_name)
                self.dataset = data  # Store for caching
                return data
            else:
                # Load from Hugging Face
                logger.info(f"Loading HuggingFace dataset: {self.dataset_name}")
                if self.dataset_config:
                    logger.info(f"Using config: {self.dataset_config}")
                
                self.dataset = load_dataset(
                    self.dataset_name, 
                    self.dataset_config, 
                    split=self.split
                )
                
                # Convert to list of dictionaries
                data = []
                for i, item in enumerate(self.dataset):
                    # Add index if not present
                    if 'id' not in item:
                        item['id'] = i
                    data.append(dict(item))
                
                logger.info(f"Loaded {len(data)} examples from HuggingFace dataset: {self.dataset_name}")
                return data
                
        except Exception as e:
            dataset_type = "local file" if self.is_local_file else "HuggingFace dataset"
            logger.error(f"Failed to load {dataset_type} {self.dataset_name}: {e}")
            raise
    
    def get_problems(self, problem_field: str = "question", max_examples: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Extract problems from the dataset.
        
        Args:
            problem_field: Field name containing the problem/question text
            max_examples: Maximum number of examples to return (None for all)
        
        Returns:
            List of problem dictionaries
        """
        if self.dataset is None:
            data = self.load_dataset()
        else:
            # Handle both HF dataset and local data formats
            if self.is_local_file:
                data = self.dataset
            else:
                data = [dict(item) for item in self.dataset]
        
        problems = []
        for item in data:
            # Find the problem text in common field names
            problem_text = None
            for field in [problem_field, 'question', 'problem', 'text', 'input', 'prompt']:
                if field in item:
                    problem_text = item[field]
                    break
            if problem_text:
                problems.append({
                    'id': item.get('id', len(problems)),
                    'problem': problem_text,
                    'metadata': {k: v for k, v in item.items() if k != field}
                })
            
            # Stop if we've reached max_examples
            if max_examples and len(problems) >= max_examples:
                break
        
        logger.info(f"Extracted {len(problems)} problems")
        return problems
    
    def get_dataset_info(self) -> Dict[str, Any]:
        """Get information about the dataset."""
        if self.dataset is None:
            data = self.load_dataset()
        else:
            data = self.dataset if self.is_local_file else self.dataset
        
        if self.is_local_file:
            # For local files, analyze the structure
            sample_item = data[0] if data else {}
            return {
                'dataset_name': self.dataset_name,
                'dataset_type': 'local_file',
                'config': None,
                'split': None,
                'num_examples': len(data),
                'features': list(sample_item.keys()) if sample_item else [],
                'example': sample_item
            }
        else:
            # For HuggingFace datasets
            return {
                'dataset_name': self.dataset_name,
                'dataset_type': 'huggingface',
                'config': self.dataset_config,
                'split': self.split,
                'num_examples': len(self.dataset),
                'features': list(self.dataset.features.keys()) if self.dataset.features else [],
                'example': dict(self.dataset[0]) if len(self.dataset) > 0 else {}
            } 