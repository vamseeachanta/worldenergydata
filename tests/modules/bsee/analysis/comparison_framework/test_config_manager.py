import pytest
import os
import yaml
from pathlib import Path

import deepdiff
DEEPDIFF_AVAILABLE = True

from comparison_framework.config_manager import ComparisonConfigManager


class TestComparisonConfigManager:
    """Test suite for ComparisonConfigManager functionality."""

    @pytest.fixture
    def sample_config_data(self):
        """Sample configuration data for testing."""
        return {
            'meta': {
                'library': 'worldenergydata',
                'basename': 'drilling_days_comparison',
                'label': 'test_comparison'
            },
            'methods': {
                'lease_method': {
                    'config_file': 'drilling_n_completion_days.yml',
                    'output_file': 'drilling_and_completion_days_by_api.xlsx',
                    'key_columns': {
                        'api': 'API_WELL_NUMBER',
                        'drilling_days': 'DRILLING_DAYS'
                    }
                },
                'api12_method': {
                    'config_file': 'query_api_01_wells_api12_rig_days.yml',
                    'output_pattern': 'block_api12_*.csv',
                    'key_columns': {
                        'api': 'API12',
                        'drilling_days': 'Drilling Days'
                    }
                }
            },
            'comparison': {
                'tolerance': {
                    'drilling_days': 5,
                    'completion_days': 3
                },
                'output': {
                    'report_file': 'test_comparison_report.xlsx'
                }
            }
        }

    @pytest.fixture
    def temp_config_file(self, tmp_path, sample_config_data):
        """Create temporary config file for testing."""
        config_file = tmp_path / "test_comparison_config.yml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)
        return str(config_file)

    def test_config_manager_initialization(self):
        """Test ComparisonConfigManager can be initialized."""
        manager = ComparisonConfigManager()
        assert manager is not None
        assert hasattr(manager, 'load_config')
        assert hasattr(manager, 'validate_config')

    def test_load_config_from_file(self, temp_config_file, sample_config_data):
        """Test loading configuration from YAML file."""
        manager = ComparisonConfigManager()
        config = manager.load_config(temp_config_file)
        
        assert config is not None
        assert 'meta' in config
        assert 'methods' in config
        assert 'comparison' in config
        
        # Verify specific configuration values
        assert config['meta']['basename'] == sample_config_data['meta']['basename']
        assert 'lease_method' in config['methods']
        assert 'api12_method' in config['methods']

    def test_validate_config_structure(self, sample_config_data):
        """Test configuration validation for required sections."""
        manager = ComparisonConfigManager()
        
        # Valid configuration should pass
        assert manager.validate_config(sample_config_data) is True
        
        # Missing required sections should fail
        invalid_config = {'meta': {'basename': 'test'}}
        assert manager.validate_config(invalid_config) is False

    def test_get_method_config(self, sample_config_data):
        """Test retrieving method-specific configuration."""
        manager = ComparisonConfigManager()
        manager.config = sample_config_data
        
        lease_config = manager.get_method_config('lease_method')
        assert lease_config is not None
        assert lease_config['config_file'] == 'drilling_n_completion_days.yml'
        
        api12_config = manager.get_method_config('api12_method')
        assert api12_config is not None
        assert api12_config['config_file'] == 'query_api_01_wells_api12_rig_days.yml'

    def test_get_comparison_config(self, sample_config_data):
        """Test retrieving comparison-specific configuration."""
        manager = ComparisonConfigManager()
        manager.config = sample_config_data
        
        comparison_config = manager.get_comparison_config()
        assert comparison_config is not None
        assert 'tolerance' in comparison_config
        assert comparison_config['tolerance']['drilling_days'] == 5

    def test_invalid_config_file_handling(self):
        """Test handling of invalid or missing configuration files."""
        manager = ComparisonConfigManager()
        
        # Non-existent file should raise appropriate error
        with pytest.raises((FileNotFoundError, IOError)):
            manager.load_config('non_existent_file.yml')

    def test_config_file_resolution(self):
        """Test configuration file path resolution."""
        manager = ComparisonConfigManager()
        
        # Test relative path resolution
        current_dir = os.path.dirname(__file__)
        parent_dir = os.path.dirname(current_dir)
        expected_path = os.path.join(parent_dir, 'comparison_config.yml')
        
        resolved_path = manager.resolve_config_path('comparison_config.yml')
        assert resolved_path == expected_path or os.path.exists(resolved_path)