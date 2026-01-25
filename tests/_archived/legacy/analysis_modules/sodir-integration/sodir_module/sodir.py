"""
Main SODIR module router implementation.

This module follows the BSEE architectural pattern to provide a consistent
interface for SODIR data collection and analysis within the WorldEnergyData framework.
"""

import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Sodir:
    """
    Main SODIR module class implementing the router pattern.
    
    This class orchestrates data collection from the Norwegian Offshore Directorate
    (SODIR) API and integrates with existing WorldEnergyData analysis tools.
    """
    
    def __init__(self):
        """Initialize SODIR module."""
        self.module_name = "sodir"
        self.data_instance = None
        self.analysis_instance = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize data and analysis components lazily."""
        # Components will be imported when needed to avoid circular imports
        pass
    
    def router(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main router method following BSEE pattern.
        
        Args:
            cfg: Configuration dictionary containing:
                - module: Module name (should be 'sodir')
                - data_types: List of data types to collect
                - api: API configuration (base_url, rate_limit, cache_ttl)
                - output: Output configuration (directory, format)
                - analysis: Analysis configuration (optional)
        
        Returns:
            Updated configuration dictionary with results
        
        Raises:
            ValueError: If configuration is invalid
            ImportError: If required components cannot be imported
        """
        # Validate configuration first (outside try block for proper error propagation)
        self._validate_config(cfg)
        
        try:
            
            # Initialize module section in config
            if 'basename' not in cfg:
                cfg['basename'] = self.module_name
            
            cfg[cfg['basename']] = {}
            cfg[cfg['basename']].update({'data': cfg.get('data', {}).copy()})
            cfg[cfg['basename']].update({'analysis': cfg.get('analysis', {}).copy()})
            
            # Import and initialize data component
            if self.data_instance is None:
                from .data import SodirData
                self.data_instance = SodirData()
            
            # Route to data collection
            logger.info(f"Starting SODIR data collection for types: {cfg.get('data_types', [])}")
            cfg, data = self.data_instance.router(cfg)
            
            # Route to analysis if configured
            if cfg.get('analysis', {}).get('enabled', False):
                if self.analysis_instance is None:
                    from .analysis import SodirAnalysis
                    self.analysis_instance = SodirAnalysis()
                
                logger.info("Running SODIR analysis")
                cfg = self.analysis_instance.router(cfg, data)
            
            # Add status information
            cfg[cfg['basename']]['status'] = 'completed'
            cfg[cfg['basename']]['data_collected'] = list(data.keys()) if data else []
            
            logger.info("SODIR module processing completed successfully")
            return cfg
            
        except Exception as e:
            logger.error(f"Error in SODIR router: {str(e)}")
            if 'basename' in cfg and cfg['basename'] in cfg:
                cfg[cfg['basename']]['status'] = 'error'
                cfg[cfg['basename']]['error'] = str(e)
            raise
    
    def _validate_config(self, cfg: Dict[str, Any]) -> None:
        """
        Validate configuration dictionary.
        
        Args:
            cfg: Configuration dictionary to validate
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Check for required fields
        if not cfg:
            raise ValueError("Configuration cannot be empty")
        
        # Validate module name if specified
        if 'module' in cfg and cfg['module'] != self.module_name:
            logger.warning(f"Module mismatch: expected '{self.module_name}', got '{cfg['module']}'")
        
        # Validate data types if specified
        if 'data_types' in cfg:
            valid_types = ['blocks', 'wellbores', 'fields', 'discoveries', 'surveys', 'facilities']
            invalid_types = [dt for dt in cfg['data_types'] if dt not in valid_types]
            if invalid_types:
                raise ValueError(f"Invalid data types: {invalid_types}. Valid types: {valid_types}")
        
        # Validate API configuration if specified
        if 'api' in cfg:
            api_config = cfg['api']
            if 'base_url' in api_config:
                if not api_config['base_url'].startswith('http'):
                    raise ValueError(f"Invalid API base URL: {api_config['base_url']}")
            
            if 'rate_limit' in api_config:
                if not isinstance(api_config['rate_limit'], (int, float)) or api_config['rate_limit'] <= 0:
                    raise ValueError(f"Invalid rate limit: {api_config['rate_limit']}")
            
            if 'cache_ttl' in api_config:
                if not isinstance(api_config['cache_ttl'], (int, float)) or api_config['cache_ttl'] < 0:
                    raise ValueError(f"Invalid cache TTL: {api_config['cache_ttl']}")
        
        logger.debug("Configuration validated successfully")