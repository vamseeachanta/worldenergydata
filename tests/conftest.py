"""
Global pytest fixtures and configuration for WorldEnergyData tests.

This file provides shared fixtures, factories, and test utilities
that are automatically available to all test files.
"""

import os
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Generator
import pandas as pd
import numpy as np
import pytest
import yaml


# Configure pytest to ignore archived tests
collect_ignore_glob = ["*/_archived_tests/*"]

# ==================== Path Fixtures ====================

@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir(project_root) -> Path:
    """Return the test data directory."""
    return project_root / "tests" / "test_data"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ==================== Data Factories ====================

@pytest.fixture
def sample_production_data() -> pd.DataFrame:
    """Generate sample oil/gas production data."""
    dates = pd.date_range(start='2020-01-01', periods=36, freq='M')
    return pd.DataFrame({
        'date': dates,
        'oil_production_bbl': np.random.uniform(1000, 5000, 36),
        'gas_production_mcf': np.random.uniform(500, 2000, 36),
        'water_production_bbl': np.random.uniform(100, 1000, 36),
        'api_well_number': ['608124003301'] * 36,
        'field_name': ['JULIA'] * 36
    })


@pytest.fixture
def sample_well_data() -> Dict[str, Any]:
    """Generate sample well data."""
    return {
        'api_well_number': '608124003301',
        'well_name': 'JULIA A-1',
        'operator': 'EXXON MOBIL',
        'field': 'JULIA',
        'water_depth_ft': 7000,
        'total_depth_ft': 32000,
        'spud_date': '2014-03-15',
        'completion_date': '2014-09-20',
        'status': 'ACTIVE',
        'latitude': 28.123456,
        'longitude': -88.654321
    }


@pytest.fixture
def sample_directional_survey() -> pd.DataFrame:
    """Generate sample directional survey data."""
    depths = np.arange(0, 32000, 100)
    return pd.DataFrame({
        'measured_depth_ft': depths,
        'true_vertical_depth_ft': depths * 0.95,
        'inclination_deg': np.random.uniform(0, 45, len(depths)),
        'azimuth_deg': np.random.uniform(0, 360, len(depths))
    })


@pytest.fixture
def sample_economic_data() -> Dict[str, Any]:
    """Generate sample economic analysis data."""
    return {
        'oil_price_bbl': 75.0,
        'gas_price_mcf': 3.5,
        'discount_rate': 0.10,
        'opex_per_bbl': 15.0,
        'capex_initial': 500_000_000,
        'project_life_years': 20,
        'tax_rate': 0.35,
        'royalty_rate': 0.125
    }


@pytest.fixture
def sample_bsee_config() -> Dict[str, Any]:
    """Generate sample BSEE configuration."""
    return {
        'api_numbers': ['608124003301', '608124003302'],
        'analysis_type': 'production',
        'date_range': {
            'start': '2020-01-01',
            'end': '2023-12-31'
        },
        'output_format': 'csv',
        'include_plots': True
    }


# ==================== Mock Data Fixtures ====================

@pytest.fixture
def mock_excel_file(temp_dir) -> Path:
    """Create a mock Excel file with test data."""
    file_path = temp_dir / "test_data.xlsx"
    
    # Create sample data
    df = pd.DataFrame({
        'Date': pd.date_range('2020-01-01', periods=12, freq='M'),
        'Oil_Production': np.random.uniform(1000, 5000, 12),
        'Gas_Production': np.random.uniform(500, 2000, 12),
        'Revenue': np.random.uniform(100000, 500000, 12)
    })
    
    # Write to Excel
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Production', index=False)
        
    return file_path


@pytest.fixture
def mock_yaml_config(temp_dir) -> Path:
    """Create a mock YAML configuration file."""
    config_path = temp_dir / "config.yml"
    
    config = {
        'analysis': {
            'type': 'production',
            'fields': ['JULIA', 'JACK', 'ST_MALO'],
            'date_range': {
                'start': '2020-01-01',
                'end': '2023-12-31'
            }
        },
        'output': {
            'format': 'csv',
            'directory': 'results',
            'include_plots': True
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
        
    return config_path


# ==================== Database Fixtures ====================

@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing."""
    class MockConnection:
        def __init__(self):
            self.connected = True
            
        def execute(self, query):
            return []
            
        def close(self):
            self.connected = False
            
    return MockConnection()


# ==================== Performance Fixtures ====================

@pytest.fixture
def benchmark_data() -> pd.DataFrame:
    """Generate large dataset for performance testing."""
    return pd.DataFrame({
        'timestamp': pd.date_range('2010-01-01', periods=10000, freq='D'),
        'value': np.random.randn(10000),
        'category': np.random.choice(['A', 'B', 'C'], 10000)
    })


# ==================== Test Environment Fixtures ====================

@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def isolated_filesystem(tmp_path):
    """Create an isolated filesystem for testing."""
    original_dir = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_dir)


# ==================== Assertion Helpers ====================

@pytest.fixture
def assert_dataframe_equal():
    """Helper to assert DataFrame equality with better error messages."""
    def _assert(df1: pd.DataFrame, df2: pd.DataFrame, **kwargs):
        try:
            pd.testing.assert_frame_equal(df1, df2, **kwargs)
        except AssertionError as e:
            print(f"\nDataFrame 1 shape: {df1.shape}")
            print(f"DataFrame 2 shape: {df2.shape}")
            print(f"\nDataFrame 1 columns: {list(df1.columns)}")
            print(f"DataFrame 2 columns: {list(df2.columns)}")
            print(f"\nFirst few rows of DataFrame 1:\n{df1.head()}")
            print(f"\nFirst few rows of DataFrame 2:\n{df2.head()}")
            raise e
    return _assert


# ==================== Parametrization Helpers ====================

def pytest_generate_tests(metafunc):
    """Dynamic test parametrization based on markers."""
    if "field_name" in metafunc.fixturenames:
        fields = ['JULIA', 'JACK', 'ST_MALO', 'ANCHOR']
        metafunc.parametrize("field_name", fields)
        
    if "data_format" in metafunc.fixturenames:
        formats = ['csv', 'xlsx', 'json']
        metafunc.parametrize("data_format", formats)


# ==================== Session Fixtures ====================

@pytest.fixture(scope="session")
def test_session_id() -> str:
    """Generate a unique ID for this test session."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


@pytest.fixture(scope="session")
def shared_test_data(tmp_path_factory) -> Path:
    """Create shared test data for the entire session."""
    data_dir = tmp_path_factory.mktemp("shared_data")
    
    # Create some shared test files
    (data_dir / "sample.csv").write_text("col1,col2\n1,2\n3,4")
    (data_dir / "sample.json").write_text('{"key": "value"}')
    
    return data_dir


# ==================== Cleanup Fixtures ====================

@pytest.fixture(autouse=True)
def cleanup_test_outputs(request):
    """Automatically clean up test outputs after each test."""
    yield
    # Cleanup code here if needed
    pass


# ==================== Custom Markers ====================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_network: mark test as requiring network access"
    )
    config.addinivalue_line(
        "markers", "requires_data: mark test as requiring test data files"
    )
    config.addinivalue_line(
        "markers", "long_running: mark test as taking significant time"
    )