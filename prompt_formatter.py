"""Prompt formatter that reads templates from YAML configuration."""

import yaml
import logging
from typing import Dict, Any, List, Set, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class PromptFormatter:
    """Format prompts using templates from YAML configuration."""
    
    def __init__(self, config_path: str = "templates/", system_prompt: Optional[str] = None):
        """
        Initialize prompt formatter with YAML configuration.
        
        Args:
            config_path: Path to YAML file or directory of YAML files (default: "templates/")
            system_prompt: Default system prompt (optional)
        """
        self.config_path = Path(config_path)
        self.default_system_prompt = system_prompt
        self.templates = {}
        self.settings = {}
        self.load_templates()
        
    def load_templates(self):
        """Load templates from YAML configuration file or directory."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Template path not found: {self.config_path}")
                logger.info("Using built-in templates")
                self._load_builtin_templates()
                return
            
            # Check if path is a directory or file
            if self.config_path.is_dir():
                self._load_from_directory()
            else:
                self._load_from_file(self.config_path)
            
            logger.info(f"Loaded {len(self.templates)} total valid templates")
            
        except Exception as e:
            logger.error(f"Error loading templates from {self.config_path}: {e}")
            logger.info("Using built-in templates")
            self._load_builtin_templates()
    
    def _load_from_directory(self):
        """Load and merge templates from all YAML files in a directory."""
        yaml_files = sorted(self.config_path.glob("*.yaml"))
        
        if not yaml_files:
            logger.warning(f"No YAML files found in {self.config_path}")
            self._load_builtin_templates()
            return
        
        logger.info(f"Loading templates from {len(yaml_files)} YAML files in {self.config_path}")
        
        for yaml_file in yaml_files:
            try:
                self._load_from_file(yaml_file)
                logger.info(f"  ✓ Loaded templates from {yaml_file.name}")
            except Exception as e:
                logger.error(f"  ✗ Error loading {yaml_file.name}: {e}")
    
    def _load_from_file(self, file_path: Path):
        """Load templates from a single YAML file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Merge templates
        file_templates = config.get('templates', {})
        for name, template_config in file_templates.items():
            if self._validate_template_config(name, template_config):
                # Check for conflicts
                if name in self.templates:
                    logger.warning(f"Template '{name}' already exists (from another file), skipping duplicate from {file_path.name}")
                else:
                    self.templates[name] = template_config
        
        # Merge settings (use first encountered or most permissive)
        file_settings = config.get('settings', {})
        for key, value in file_settings.items():
            if key not in self.settings:
                self.settings[key] = value
            elif key == 'max_template_length':
                # Use the larger max length
                self.settings[key] = max(self.settings[key], value)
    
    def _validate_template_config(self, name: str, template_config: Dict[str, Any]) -> bool:
        """Validate a template configuration."""
        required_fields = ['name', 'description', 'template', 'variables']
        
        for field in required_fields:
            if field not in template_config:
                logger.error(f"Template '{name}' missing required field: {field}")
                return False
        
        # Check if template contains all declared variables
        template_text = template_config['template']
        declared_vars = set(template_config['variables'])
        
        # Find variables used in template
        import re
        # This regex matches single braces {word} but not double braces {{word}}
        # It uses negative lookbehind and lookahead to avoid matching escaped braces
        used_vars = set(re.findall(r'(?<!\{)\{(\w+)\}(?!\})', template_text))
        
        # Check for undeclared variables
        undeclared = used_vars - declared_vars
        if undeclared:
            logger.error(f"Template '{name}' uses undeclared variables: {undeclared}")
            return False
        
        # Check for unused declared variables
        unused = declared_vars - used_vars
        if unused:
            logger.warning(f"Template '{name}' declares unused variables: {unused}")
        
        return True
    
    def _load_builtin_templates(self):
        """Load built-in templates as fallback."""
        self.templates = {
            'default': {
                'name': 'Default',
                'description': 'Simple problem-answer format',
                'template': 'Problem: {problem}\n\nAnswer:',
                'variables': ['problem']
            },
            'chat': {
                'name': 'Chat Style',
                'description': 'Chat-style format',
                'template': '<|system|>\n{system_prompt}\n<|user|>\n{problem}\n<|assistant|>\n',
                'variables': ['problem', 'system_prompt'],
                'system_prompt': 'You are a helpful assistant.'
            },
            'instruct': {
                'name': 'Instruction Following',
                'description': 'Instruction-following format',
                'template': '### Instruction:\n{problem}\n\n### Response:\n',
                'variables': ['problem']
            },
            'qa': {
                'name': 'Question-Answer',
                'description': 'Question-answer format',
                'template': 'Q: {problem}\nA:',
                'variables': ['problem']
            }
        }
        
        self.settings = {
            'default_template': 'default',
            'max_template_length': 4096,
            'required_variables': ['problem']
        }
    
    def format_problem(self, problem: Dict[str, Any], template_name: str = "default") -> str:
        """Format a problem using the specified template."""
        if template_name not in self.templates:
            logger.warning(f"Template '{template_name}' not found, using default")
            template_name = self.settings.get('default_template', 'default')
        
        template_config = self.templates[template_name]
        template_text = template_config['template']
        required_vars = template_config['variables']
        
        # Prepare variables
        variables = self._prepare_variables(problem, template_config)
        
        # Check if all required variables are available
        missing_vars = set(required_vars) - set(variables.keys())
        if missing_vars:
            logger.error(f"Missing required variables for template '{template_name}': {missing_vars}")
            # Use fallback template
            return self._format_fallback(problem)
        
        # Format the template
        try:
            formatted_prompt = template_text.format(**variables)
            
            # Check length limit
            max_length = self.settings.get('max_template_length', 4096)
            if len(formatted_prompt) > max_length:
                logger.warning(f"Template output exceeds max length ({len(formatted_prompt)} > {max_length})")
            
            return formatted_prompt
            
        except Exception as e:
            logger.error(f"Error formatting template '{template_name}': {e}")
            return self._format_fallback(problem)
    
    def _prepare_variables(self, problem: Dict[str, Any], template_config: Dict[str, Any]) -> Dict[str, str]:
        """Prepare variables for template formatting."""
        variables = {}
        required_vars = template_config['variables']
        
        # Core variables
        if 'problem' in required_vars:
            variables['problem'] = problem.get('problem', '')
        
        # Solution variable (for evaluation templates)
        if 'solution' in required_vars:
            variables['solution'] = problem.get('solution', '')
        
        # System prompt (only if required by template)
        if 'system_prompt' in required_vars:
            # Use template-specific system prompt, fallback to default, or empty string
            template_system_prompt = template_config.get('system_prompt')
            if template_system_prompt:
                variables['system_prompt'] = template_system_prompt
            elif self.default_system_prompt:
                variables['system_prompt'] = self.default_system_prompt
            else:
                variables['system_prompt'] = 'You are a helpful assistant.'
        
        # Optional variables (only if required by template)
        if 'context' in required_vars:
            variables['context'] = problem.get('context', '')
        
        if 'examples' in required_vars:
            variables['examples'] = problem.get('examples', '')
        
        # Custom variables from problem metadata
        metadata = problem.get('metadata', {})
        for var in required_vars:
            if var in metadata:
                variables[var] = str(metadata[var])
            elif var in problem and var not in variables:
                # Check if variable exists directly in problem dict (for manually added variables)
                variables[var] = str(problem[var])
            elif var not in variables:
                # Provide empty string for missing variables
                variables[var] = ''
        
        return variables
    
    def _format_fallback(self, problem: Dict[str, Any]) -> str:
        """Fallback formatting when template fails."""
        problem_text = problem.get('problem', '')
        return f"Problem: {problem_text}\n\nAnswer:"
    
    def get_available_templates(self) -> List[str]:
        """Get list of available template names."""
        return list(self.templates.keys())
    
    def get_template_info(self, template_name: str = None) -> Dict[str, Any]:
        """Get information about a template or all templates."""
        if template_name:
            if template_name in self.templates:
                template_config = self.templates[template_name]
                info = {
                    'name': template_config['name'],
                    'description': template_config['description'],
                    'variables': template_config['variables']
                }
                # Only include system_prompt if it exists
                if 'system_prompt' in template_config:
                    info['system_prompt'] = template_config['system_prompt']
                elif self.default_system_prompt:
                    info['system_prompt'] = self.default_system_prompt
                return info
            else:
                return {"error": f"Template '{template_name}' not found"}
        else:
            return {
                name: {
                    "name": config.get("name", name),
                    "description": config.get("description", "No description"),
                    "variables": config.get("variables", [])
                }
                for name, config in self.templates.items()
            }
    
    def validate_template(self, template_name: str) -> bool:
        """Validate that a template exists and is properly formatted."""
        if template_name not in self.templates:
            return False
        
        template_config = self.templates[template_name]
        return self._validate_template_config(template_name, template_config) 