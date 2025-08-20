"""
Test configuration management system for WorldEnergyData.

This module provides centralized configuration for test execution,
including environment settings, data paths, and test parameters.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import yaml


@dataclass
class TestConfig:
    """Main test configuration class."""
    
    # Environment settings
    environment: str = "test"
    debug: bool = False
    verbose: bool = True
    
    # Paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    test_root: Path = field(default_factory=lambda: Path(__file__).parent)
    test_data_dir: Path = field(default_factory=lambda: Path(__file__).parent / "test_data")
    temp_dir: Path = field(default_factory=lambda: Path(__file__).parent / "temp")
    results_dir: Path = field(default_factory=lambda: Path(__file__).parent / "results")
    
    # Test execution settings
    parallel_workers: int = 4
    timeout_seconds: int = 300
    max_failures: int = 5
    retry_count: int = 2
    
    # Coverage settings
    coverage_threshold: float = 90.0
    coverage_fail_under: float = 0.0  # Start at 0, gradually increase
    
    # Performance settings
    benchmark_rounds: int = 10
    benchmark_warmup: int = 5
    performance_threshold_ms: int = 1000
    
    # Data settings
    sample_data_size: int = 1000
    test_fields: List[str] = field(default_factory=lambda: ['JULIA', 'JACK', 'ST_MALO'])
    test_api_numbers: List[str] = field(default_factory=lambda: ['608124003301', '608124003302'])
    
    # Network settings
    api_timeout: int = 30
    mock_external_apis: bool = True
    offline_mode: bool = False
    
    # Reporting settings
    generate_html_report: bool = True
    generate_json_report: bool = True
    report_verbosity: str = "detailed"
    
    def __post_init__(self):
        """Initialize directories and validate configuration."""
        # Create directories if they don't exist
        for dir_path in [self.test_data_dir, self.temp_dir, self.results_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_file(cls, config_file: Path) -> 'TestConfig':
        """Load configuration from YAML or JSON file."""
        if config_file.suffix == '.yaml' or config_file.suffix == '.yml':
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
        elif config_file.suffix == '.json':
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {config_file.suffix}")
        
        return cls(**config_data)
    
    @classmethod
    def from_env(cls) -> 'TestConfig':
        """Load configuration from environment variables."""
        config_data = {}
        
        # Map environment variables to config fields
        env_mapping = {
            'TEST_ENV': 'environment',
            'TEST_DEBUG': 'debug',
            'TEST_PARALLEL_WORKERS': 'parallel_workers',
            'TEST_TIMEOUT': 'timeout_seconds',
            'TEST_COVERAGE_THRESHOLD': 'coverage_threshold',
            'TEST_OFFLINE_MODE': 'offline_mode',
        }
        
        for env_key, config_key in env_mapping.items():
            if env_key in os.environ:
                value = os.environ[env_key]
                # Convert to appropriate type
                if config_key in ['debug', 'offline_mode']:
                    value = value.lower() == 'true'
                elif config_key in ['parallel_workers', 'timeout_seconds']:
                    value = int(value)
                elif config_key == 'coverage_threshold':
                    value = float(value)
                
                config_data[config_key] = value
        
        return cls(**config_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'environment': self.environment,
            'debug': self.debug,
            'verbose': self.verbose,
            'parallel_workers': self.parallel_workers,
            'timeout_seconds': self.timeout_seconds,
            'max_failures': self.max_failures,
            'retry_count': self.retry_count,
            'coverage_threshold': self.coverage_threshold,
            'coverage_fail_under': self.coverage_fail_under,
            'benchmark_rounds': self.benchmark_rounds,
            'benchmark_warmup': self.benchmark_warmup,
            'performance_threshold_ms': self.performance_threshold_ms,
            'sample_data_size': self.sample_data_size,
            'test_fields': self.test_fields,
            'test_api_numbers': self.test_api_numbers,
            'api_timeout': self.api_timeout,
            'mock_external_apis': self.mock_external_apis,
            'offline_mode': self.offline_mode,
            'generate_html_report': self.generate_html_report,
            'generate_json_report': self.generate_json_report,
            'report_verbosity': self.report_verbosity,
        }
    
    def save(self, config_file: Path):
        """Save configuration to file."""
        config_data = self.to_dict()
        
        if config_file.suffix == '.yaml' or config_file.suffix == '.yml':
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
        elif config_file.suffix == '.json':
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        else:
            raise ValueError(f"Unsupported config file format: {config_file.suffix}")


class TestEnvironment:
    """Test environment configuration manager."""
    
    ENVIRONMENTS = {
        'test': {
            'base_url': 'http://localhost:8000',
            'database': 'test_db',
            'log_level': 'DEBUG',
        },
        'staging': {
            'base_url': 'https://staging.example.com',
            'database': 'staging_db',
            'log_level': 'INFO',
        },
        'production': {
            'base_url': 'https://api.example.com',
            'database': 'prod_db',
            'log_level': 'WARNING',
        }
    }
    
    @classmethod
    def get(cls, env_name: str = 'test') -> Dict[str, Any]:
        """Get environment configuration."""
        if env_name not in cls.ENVIRONMENTS:
            raise ValueError(f"Unknown environment: {env_name}")
        return cls.ENVIRONMENTS[env_name]


class TestDataConfig:
    """Test data configuration and paths."""
    
    def __init__(self, base_dir: Path = None):
        """Initialize test data configuration."""
        self.base_dir = base_dir or Path(__file__).parent / "test_data"
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def sample_excel(self) -> Path:
        """Path to sample Excel file."""
        return self.base_dir / "sample_data.xlsx"
    
    @property
    def sample_csv(self) -> Path:
        """Path to sample CSV file."""
        return self.base_dir / "sample_data.csv"
    
    @property
    def sample_yaml(self) -> Path:
        """Path to sample YAML config."""
        return self.base_dir / "sample_config.yml"
    
    @property
    def mock_api_responses(self) -> Path:
        """Path to mock API response files."""
        return self.base_dir / "mock_responses"
    
    def get_field_data(self, field_name: str) -> Path:
        """Get path to field-specific test data."""
        return self.base_dir / "fields" / f"{field_name.lower()}_data.csv"


# ==================== Global Configuration Instance ====================

# Load configuration based on priority:
# 1. Environment variables
# 2. Config file if exists
# 3. Default values

def load_test_config() -> TestConfig:
    """Load test configuration from available sources."""
    config_file = Path(__file__).parent / "test_config.yml"
    
    if config_file.exists():
        config = TestConfig.from_file(config_file)
    elif os.environ.get('TEST_ENV'):
        config = TestConfig.from_env()
    else:
        config = TestConfig()
    
    return config


# Global configuration instance
TEST_CONFIG = load_test_config()
TEST_ENV = TestEnvironment.get(TEST_CONFIG.environment)
TEST_DATA = TestDataConfig(TEST_CONFIG.test_data_dir)


# ==================== Configuration Utilities ====================

def get_test_setting(key: str, default: Any = None) -> Any:
    """Get test configuration setting."""
    return getattr(TEST_CONFIG, key, default)


def update_test_setting(key: str, value: Any):
    """Update test configuration setting."""
    setattr(TEST_CONFIG, key, value)


def reset_test_config():
    """Reset test configuration to defaults."""
    global TEST_CONFIG
    TEST_CONFIG = TestConfig()


# ==================== Export Configuration ====================

__all__ = [
    'TestConfig',
    'TestEnvironment',
    'TestDataConfig',
    'TEST_CONFIG',
    'TEST_ENV',
    'TEST_DATA',
    'load_test_config',
    'get_test_setting',
    'update_test_setting',
    'reset_test_config',
]