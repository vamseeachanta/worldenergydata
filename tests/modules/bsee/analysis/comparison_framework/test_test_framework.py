"""
Comparison Test Framework for Drilling Days Analysis

Main framework for orchestrating comparison between different drilling days 
calculation methods.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

# Import existing dependencies
try:
    from worldenergydata.engine import engine
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False
    
try:
    import deepdiff
    DEEPDIFF_AVAILABLE = True
except ImportError:
    DEEPDIFF_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from .config_manager import ComparisonConfigManager

logger = logging.getLogger(__name__)


class ComparisonTestFramework:
    """Main framework for running drilling days comparison tests."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the comparison test framework.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_manager = ComparisonConfigManager()
        self.is_initialized = False
        self.comparison_results = {}
        self.method_outputs = {}
        
        if config_file:
            self.initialize(config_file)

    def initialize(self, config_file: str) -> bool:
        """
        Initialize the framework with configuration.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load and validate configuration
            config = self.config_manager.load_config(config_file)
            
            if not self.config_manager.validate_config(config):
                logger.error("Configuration validation failed")
                return False
            
            # Validate dependencies
            deps = self.validate_dependencies()
            if not all(deps.values()):
                missing = [k for k, v in deps.items() if not v]
                logger.error(f"Missing required dependencies: {missing}")
                return False
            
            self.is_initialized = True
            logger.info("Framework initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Framework initialization failed: {e}")
            self.is_initialized = False
            return False

    def validate_dependencies(self) -> Dict[str, bool]:
        """
        Validate required dependencies are available.
        
        Returns:
            Dictionary of dependency availability status
        """
        return {
            'engine_available': ENGINE_AVAILABLE,
            'deepdiff_available': DEEPDIFF_AVAILABLE,
            'yaml_available': YAML_AVAILABLE
        }

    def is_ready(self) -> bool:
        """
        Check if framework is ready to run comparisons.
        
        Returns:
            True if framework is ready, False otherwise
        """
        return self.is_initialized and self.config_manager.config is not None

    def get_method_config(self, method_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for specific method.
        
        Args:
            method_name: Name of the method
            
        Returns:
            Method configuration or None if not found
        """
        if not self.is_ready():
            logger.error("Framework not initialized")
            return None
            
        return self.config_manager.get_method_config(method_name)

    def execute_method(self, method_name: str) -> bool:
        """
        Execute a specific drilling days calculation method.
        
        Args:
            method_name: Name of method to execute
            
        Returns:
            True if execution successful, False otherwise
        """
        if not self.is_ready():
            logger.error("Framework not initialized")
            return False
        
        method_config = self.get_method_config(method_name)
        if not method_config:
            logger.error(f"Configuration not found for method: {method_name}")
            return False
        
        try:
            # Get config file path relative to test directory
            config_file = method_config['config_file']
            config_path = self.config_manager.resolve_config_path(config_file)
            
            if not os.path.exists(config_path):
                logger.error(f"Method config file not found: {config_path}")
                return False
            
            # Execute method using worldenergydata engine
            logger.info(f"Executing {method_name} with config: {config_path}")
            cfg = engine(config_path)
            
            # Store execution result
            self.method_outputs[method_name] = {
                'config_file': config_path,
                'executed': True,
                'config_obj': cfg
            }
            
            logger.info(f"Successfully executed {method_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing {method_name}: {e}")
            return False

    def run_comparison(self) -> Dict[str, Any]:
        """
        Run complete comparison workflow.
        
        Returns:
            Comparison results dictionary
            
        Raises:
            RuntimeError: If framework not initialized
        """
        if not self.is_ready():
            raise RuntimeError("Framework not initialized")
        
        logger.info("Starting drilling days comparison workflow")
        
        # Execute both methods
        methods = ['lease_method', 'api12_method']
        execution_results = {}
        
        for method in methods:
            logger.info(f"Executing {method}")
            success = self.execute_method(method)
            execution_results[method] = success
            
            if not success:
                logger.warning(f"Failed to execute {method}")
        
        # Store results
        self.comparison_results = {
            'execution_results': execution_results,
            'methods_executed': len([k for k, v in execution_results.items() if v]),
            'total_methods': len(methods),
            'success': all(execution_results.values())
        }
        
        logger.info(f"Comparison workflow completed. Success: {self.comparison_results['success']}")
        return self.comparison_results

    def get_comparison_results(self) -> Dict[str, Any]:
        """
        Get results from last comparison run.
        
        Returns:
            Comparison results dictionary
        """
        return self.comparison_results

    def get_method_outputs(self) -> Dict[str, Any]:
        """
        Get output information from executed methods.
        
        Returns:
            Method outputs dictionary
        """
        return self.method_outputs

    def cleanup(self):
        """Clean up framework resources."""
        self.comparison_results = {}
        self.method_outputs = {}
        logger.info("Framework cleaned up")