"""
Configuration loader for SME Financial Analysis
Imports and uses YAML support from comprehensive reports
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Import from comprehensive reports for YAML support
try:
    from worldenergydata.modules.bsee.reports.comprehensive.config.config_router import ConfigRouter
    COMPREHENSIVE_CONFIG_AVAILABLE = True
except ImportError:
    COMPREHENSIVE_CONFIG_AVAILABLE = False

logger = logging.getLogger(__name__)


class SMEConfigLoader:
    """
    Configuration loader for SME financial analysis
    Uses YAML support from comprehensive reports where available
    """
    
    DEFAULT_CONFIG = {
        'financial': {
            'lease_groups': {
                'STONES': ['G03608', 'G04003'],
                'CASCADE_CHINOOK': ['G25488', 'G25492'],
                'JULIA': ['G24030', 'G24041'],
                'ANCHOR': ['G34628', 'G34631']
            },
            'economic_parameters': {
                'oil_price_usd': 50.00,
                'gas_price_usd_mcf': 3.00,
                'discount_rate': 0.10,
                'tax_rate': 0.35,
                'royalty_rate': 0.1875,
                'severance_tax_rate': 0.05,
                'operating_cost_per_bbl': 12.50
            },
            'drilling_costs': {
                'rig_rate_usd_per_day': 300000,
                'completion_rate_usd_per_day': 400000,
                'mobilization_cost_usd': 5000000,
                'demobilization_cost_usd': 3000000
            },
            'data_paths': {
                'production_data': 'multi_year_lease_matrix_with_charts.xlsx',
                'drilling_completion': 'drilling_and_completion_days_by_api.xlsx',
                'lease_assumptions': 'leases_assumptions.xlsx',
                'wti_prices': 'wti_full_monthly.xlsx'
            },
            'output_options': {
                'include_readme': True,
                'include_charts': True,
                'format_numbers': True,
                'decimal_places': 2
            }
        }
    }
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            base_path: Base path for configuration files
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.config_dir = self.base_path / 'config'
        self.comprehensive_router = None
        
        # Try to use comprehensive config router if available
        if COMPREHENSIVE_CONFIG_AVAILABLE:
            try:
                self.comprehensive_router = ConfigRouter()
                logger.info("Using comprehensive report configuration support")
            except Exception as e:
                logger.warning(f"Could not initialize comprehensive config router: {e}")
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults
        
        Args:
            config_path: Path to configuration file (optional)
            
        Returns:
            Configuration dictionary
        """
        if config_path is None:
            # Look for default config file
            default_paths = [
                self.config_dir / 'financial_config.yaml',
                self.config_dir / 'sme_config.yaml',
                self.base_path / 'financial_config.yaml',
                Path(__file__).parent / 'config' / 'financial_config.yaml'
            ]
            
            for path in default_paths:
                if path.exists():
                    config_path = str(path)
                    break
        
        if config_path and Path(config_path).exists():
            try:
                config = self._load_yaml_file(config_path)
                logger.info(f"Loaded configuration from {config_path}")
                
                # Merge with defaults
                return self._merge_configs(self.DEFAULT_CONFIG, config)
            except Exception as e:
                logger.error(f"Error loading config from {config_path}: {e}")
                logger.info("Using default configuration")
        
        return self.DEFAULT_CONFIG.copy()
    
    def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load YAML configuration file
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Configuration dictionary
        """
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _merge_configs(self, default: Dict[str, Any], custom: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge custom configuration with defaults
        
        Args:
            default: Default configuration
            custom: Custom configuration
            
        Returns:
            Merged configuration
        """
        import copy
        result = copy.deepcopy(default)
        
        def merge_dict(base, overlay):
            for key, value in overlay.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
        
        merge_dict(result, custom)
        return result
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration structure and values
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if valid, raises ValueError if not
        """
        if 'financial' not in config:
            raise ValueError("Configuration must contain 'financial' section")
        
        sme_config = config['financial']
        
        # Validate required sections
        required_sections = ['lease_groups', 'economic_parameters', 'drilling_costs']
        for section in required_sections:
            if section not in sme_config:
                raise ValueError(f"Missing required section: {section}")
        
        # Validate economic parameters
        params = sme_config['economic_parameters']
        if params['oil_price_usd'] <= 0:
            raise ValueError("Oil price must be positive")
        if params['gas_price_usd_mcf'] <= 0:
            raise ValueError("Gas price must be positive")
        if not (0 <= params['discount_rate'] <= 1):
            raise ValueError("Discount rate must be between 0 and 1")
        if not (0 <= params['tax_rate'] <= 1):
            raise ValueError("Tax rate must be between 0 and 1")
        if not (0 <= params['royalty_rate'] <= 1):
            raise ValueError("Royalty rate must be between 0 and 1")
        
        # Validate drilling costs
        costs = sme_config['drilling_costs']
        if costs['rig_rate_usd_per_day'] <= 0:
            raise ValueError("Rig rate must be positive")
        if costs['completion_rate_usd_per_day'] <= 0:
            raise ValueError("Completion rate must be positive")
        
        return True
    
    def save_config(self, config: Dict[str, Any], output_path: str):
        """
        Save configuration to YAML file
        
        Args:
            config: Configuration dictionary
            output_path: Path to save configuration
        """
        # Validate before saving
        self.validate_config(config)
        
        # Ensure directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to YAML
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration saved to {output_path}")
    
    def get_lease_groups(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, list]:
        """
        Get lease group mappings from configuration
        
        Args:
            config: Configuration dictionary (optional)
            
        Returns:
            Dictionary of group names to lease lists
        """
        if config is None:
            config = self.load_config()
        
        return config['financial']['lease_groups']
    
    def get_economic_parameters(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Get economic parameters from configuration
        
        Args:
            config: Configuration dictionary (optional)
            
        Returns:
            Dictionary of economic parameters
        """
        if config is None:
            config = self.load_config()
        
        return config['financial']['economic_parameters']
    
    def get_drilling_costs(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Get drilling cost parameters from configuration
        
        Args:
            config: Configuration dictionary (optional)
            
        Returns:
            Dictionary of drilling cost parameters
        """
        if config is None:
            config = self.load_config()
        
        return config['financial']['drilling_costs']