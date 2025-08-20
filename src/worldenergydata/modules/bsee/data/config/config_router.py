"""
Configuration Router Module

This module handles routing enhanced data refresh system,
allowing to run based on configuration.
"""

from typing import Dict, Any, Optional
from loguru import logger
from pathlib import Path
import yaml


class ConfigRouter:
    """
    Route configuration between legacy and enhanced systems.
    
    This class determines which system to use based on configuration
    and ensures proper isolation between the two implementations.
    """
    
    def __init__(self):
        """Initialize the configuration router."""
        self.enhanced_mode = None
        self.config_source = None
    
    def is_enhanced_mode(self, cfg: Dict[str, Any]) -> bool:
        """
        Determine if enhanced mode should be used.
        
        Args:
            cfg: Configuration dictionary
            
        Returns:
            True if enhanced mode is enabled, False for legacy mode
        """
        # Check mode in meta section (primary method)
        mode = cfg.get('meta', {}).get('mode', 'legacy')
        # Handle None values gracefully
        if mode is None:
            mode = 'legacy'
        mode = str(mode).lower()
        enhanced = (mode == 'enhanced')
        
        # Store the mode for later reference
        self.enhanced_mode = enhanced
        
        if enhanced:
            logger.info("Enhanced mode ENABLED - Using fresh data access")
        else:
            logger.info("Legacy mode ENABLED - Using legacy system")
        
        return enhanced
    
    def load_enhanced_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load enhanced configuration file.
        
        Args:
            config_path: Optional path to enhanced config file
            
        Returns:
            Enhanced configuration dictionary
        """
        if config_path is None:
            # Default enhanced config path
            config_path = "tests/modules/bsee/data/refresh/data_refresh_enhanced.yml"
        
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.warning(f"Enhanced config file not found: {config_path}")
            # Return default enhanced configuration
            return self.get_default_enhanced_config()
        
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Handle empty file, None result, or non-dict result
            if not isinstance(config, dict):
                logger.warning(f"Invalid YAML structure (expected dict, got {type(config).__name__}): {config_path}")
                return self.get_default_enhanced_config()
            
            logger.info(f"Loaded enhanced configuration from {config_path}")
            self.config_source = 'enhanced_file'
            return config
            
        except Exception as e:
            logger.error(f"Error loading enhanced config: {str(e)}")
            return self.get_default_enhanced_config()
    
    def get_default_enhanced_config(self) -> Dict[str, Any]:
        """
        Get default enhanced configuration.
        
        Returns:
            Default configuration for enhanced mode
        """
        config = {
            'meta': {
                'library': 'worldenergydata',
                'basename': 'bsee',
                'mode': 'enhanced'
            },
            # Mode is set in meta section
            'data': {
                # No 'refresh' flag in enhanced mode to avoid legacy system activation
                'well': True,
                'war': True,
                'production': True
            },
            'sources': {
                'well': {
                    'url': 'https://www.data.bsee.gov/Well/Files/APDRawData.zip',
                    'update_frequency': 'daily'
                },
                'war': {
                    'url': 'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip',
                    'update_frequency': 'daily'
                },
                'production': {
                    'url': 'https://www.data.bsee.gov/Production/Files/ProductionRawData.zip',
                    'update_frequency': 'bi_monthly'
                }
            },
            'processing': {
                'in_memory': True,
                'save_zip': False,
                'chunk_size': 8192,
                'timeout': 300
            },
            'default': {
                'log_level': 'INFO'
            }
        }
        
        self.config_source = 'default_enhanced'
        return config
    
    def merge_configs(self, base_cfg: Dict[str, Any], enhanced_cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge base configuration with enhanced configuration.
        
        Args:
            base_cfg: Base/legacy configuration
            enhanced_cfg: Enhanced configuration
            
        Returns:
            Merged configuration dictionary
        """
        # Deep merge of configurations
        merged = base_cfg.copy()
        
        def deep_merge(target: dict, source: dict) -> dict:
            """Recursively merge source into target."""
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    deep_merge(target[key], value)
                else:
                    target[key] = value
            return target
        
        merged = deep_merge(merged, enhanced_cfg)
        
        # Ensure mode is preserved in meta
        if self.enhanced_mode and 'meta' in merged:
            merged['meta']['mode'] = 'enhanced'
        
        return merged
    
    def validate_config(self, cfg: Dict[str, Any]) -> bool:
        """
        Validate configuration for enhanced mode.
        
        Args:
            cfg: Configuration dictionary
            
        Returns:
            True if configuration is valid, False otherwise
        """
        valid = True
        
        # Check for required data flags based on mode
        if self.enhanced_mode:
            # Enhanced mode doesn't use refresh flag
            pass
        else:
            # Legacy mode requires refresh flag
            if not cfg.get('data', {}).get('refresh'):
                logger.warning("Data refresh flag is not set for legacy mode")
                valid = False
        
        # Check for at least one data type flag
        data_flags = ['well', 'war', 'production', 'apm']
        if not any(cfg.get('data', {}).get(flag) for flag in data_flags):
            logger.warning("No data type flags are set")
            valid = False
        
        # Check for file paths if in legacy mode
        if not self.enhanced_mode:
            if not cfg.get('parameters', {}).get('filepath'):
                logger.warning("File paths not configured for legacy mode")
                valid = False
        
        return valid
    
    def get_system_info(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get information about which system is being used.
        
        Args:
            cfg: Configuration dictionary
            
        Returns:
            System information dictionary
        """
        info = {
            'mode': 'enhanced' if self.is_enhanced_mode(cfg) else 'legacy',
            'config_source': self.config_source or 'unknown',
            'features': {
                'fresh_data': self.enhanced_mode,
                'in_memory_processing': self.enhanced_mode,
                'war_data_support': cfg.get('data', {}).get('war', False),
                'well_data_support': cfg.get('data', {}).get('well', False) or cfg.get('data', {}).get('apm', False),
                'production_data_support': cfg.get('data', {}).get('production', False)
            },
            'data_sources': {
                'well': 'fresh_download' if self.enhanced_mode else 'local_zip',
                'war': 'fresh_download' if self.enhanced_mode else 'not_supported',
                'production': 'fresh_download' if self.enhanced_mode else 'local_zip'
            }
        }
        
        return info
    
    def log_config_summary(self, cfg: Dict[str, Any]) -> None:
        """
        Log a summary of the configuration.
        
        Args:
            cfg: Configuration dictionary
        """
        info = self.get_system_info(cfg)
        
        logger.info("=" * 60)
        logger.info("BSEE Data Refresh Configuration Summary")
        logger.info("=" * 60)
        logger.info(f"Mode: {info['mode'].upper()}")
        logger.info(f"Config Source: {info['config_source']}")
        logger.info("Features:")
        for feature, enabled in info['features'].items():
            status = "[ENABLED]" if enabled else "[DISABLED]"
            logger.info(f"  {status} {feature.replace('_', ' ').title()}")
        logger.info("Data Sources:")
        for source, method in info['data_sources'].items():
            logger.info(f"  {source.upper()}: {method}")
        logger.info("=" * 60)