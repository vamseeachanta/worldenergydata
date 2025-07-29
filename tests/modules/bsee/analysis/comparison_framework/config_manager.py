"""
Configuration Manager for Drilling Days Comparison Framework

Handles loading and validation of comparison configuration files.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ComparisonConfigManager:
    """Manages configuration loading and validation for comparison framework."""

    def __init__(self):
        """Initialize the configuration manager."""
        self.config: Optional[Dict[str, Any]] = None
        self.config_file_path: Optional[str] = None

    def load_config(self, config_file: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Loaded configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        resolved_path = self.resolve_config_path(config_file)
        
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"Configuration file not found: {resolved_path}")
        
        try:
            with open(resolved_path, 'r') as f:
                self.config = yaml.safe_load(f)
                self.config_file_path = resolved_path
                
            logger.info(f"Loaded configuration from: {resolved_path}")
            return self.config
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {resolved_path}: {e}")
            raise

    def resolve_config_path(self, config_file: str) -> str:
        """
        Resolve configuration file path relative to test directory.
        
        Args:
            config_file: Configuration file name or path
            
        Returns:
            Absolute path to configuration file
        """
        if os.path.isabs(config_file):
            return config_file
            
        # If relative path, resolve relative to the test directory
        current_dir = os.path.dirname(__file__)
        parent_dir = os.path.dirname(current_dir)  # Go up from comparison_framework
        config_path = os.path.join(parent_dir, config_file)
        
        return config_path

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration structure and required fields.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid, False otherwise
        """
        required_sections = ['meta', 'methods', 'comparison']
        
        # Check required top-level sections
        for section in required_sections:
            if section not in config:
                logger.error(f"Missing required configuration section: {section}")
                return False
        
        # Validate methods section
        if not self._validate_methods_section(config.get('methods', {})):
            return False
            
        # Validate comparison section
        if not self._validate_comparison_section(config.get('comparison', {})):
            return False
        
        return True

    def _validate_methods_section(self, methods: Dict[str, Any]) -> bool:
        """Validate methods configuration section."""
        required_methods = ['lease_method', 'api12_method']
        
        for method in required_methods:
            if method not in methods:
                logger.error(f"Missing required method configuration: {method}")
                return False
                
            method_config = methods[method]
            required_fields = ['config_file', 'key_columns']
            
            for field in required_fields:
                if field not in method_config:
                    logger.error(f"Missing required field '{field}' in {method} configuration")
                    return False
        
        return True

    def _validate_comparison_section(self, comparison: Dict[str, Any]) -> bool:
        """Validate comparison configuration section."""
        required_fields = ['tolerance', 'output']
        
        for field in required_fields:
            if field not in comparison:
                logger.error(f"Missing required field '{field}' in comparison configuration")
                return False
        
        return True

    def get_method_config(self, method_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for specific method.
        
        Args:
            method_name: Name of the method ('lease_method' or 'api12_method')
            
        Returns:
            Method configuration dictionary or None if not found
        """
        if not self.config or 'methods' not in self.config:
            logger.error("No configuration loaded or methods section missing")
            return None
            
        return self.config['methods'].get(method_name)

    def get_comparison_config(self) -> Optional[Dict[str, Any]]:
        """
        Get comparison configuration.
        
        Returns:
            Comparison configuration dictionary or None if not found
        """
        if not self.config or 'comparison' not in self.config:
            logger.error("No configuration loaded or comparison section missing")
            return None
            
        return self.config['comparison']

    def get_meta_config(self) -> Optional[Dict[str, Any]]:
        """
        Get meta configuration.
        
        Returns:
            Meta configuration dictionary or None if not found
        """
        if not self.config or 'meta' not in self.config:
            logger.error("No configuration loaded or meta section missing")
            return None
            
        return self.config['meta']