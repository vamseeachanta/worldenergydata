"""
Performance Testing Configuration

This module configures pytest-benchmark for performance testing of worldenergydata.
"""

import random
import string
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

try:
    from pytest_benchmark.fixture import BenchmarkFixture

    _HAS_BENCHMARK = True
except ImportError:
    _HAS_BENCHMARK = False
    BenchmarkFixture = None


@pytest.fixture
def benchmark_config(benchmark):
    """Configure benchmark settings for consistent performance testing."""
    if not _HAS_BENCHMARK:
        pytest.skip("pytest-benchmark not installed")
    benchmark.pedantic = True  # More precise measurements
    benchmark.warmup_rounds = 5  # Warmup before actual measurements
    benchmark.calibration_precision = 10  # Calibration precision
    benchmark.max_rounds = 100  # Maximum rounds for stable results
    return benchmark


@pytest.fixture
def sample_production_data():
    """Generate sample production data for performance testing."""
    dates = pd.date_range(start="2020-01-01", end="2024-12-31", freq="D")
    data = {
        "date": dates,
        "oil_production": np.random.uniform(1000, 10000, len(dates)),
        "gas_production": np.random.uniform(5000, 50000, len(dates)),
        "water_production": np.random.uniform(100, 5000, len(dates)),
        "well_id": np.random.choice(["WELL-001", "WELL-002", "WELL-003"], len(dates)),
        "field_name": np.random.choice(["Field-A", "Field-B", "Field-C"], len(dates)),
    }
    return pd.DataFrame(data)


@pytest.fixture
def large_dataset():
    """Generate large dataset for memory and performance testing."""
    # 1 million rows
    size = 1_000_000
    data = {
        "timestamp": pd.date_range(start="2000-01-01", periods=size, freq="H"),
        "value1": np.random.randn(size),
        "value2": np.random.randn(size),
        "value3": np.random.randn(size),
        "category": np.random.choice(["A", "B", "C", "D"], size),
        "id": [
            "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            for _ in range(size)
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_well_data():
    """Generate sample well data for directional survey performance testing."""
    depths = np.linspace(0, 10000, 1000)
    data = {
        "measured_depth": depths,
        "inclination": np.random.uniform(0, 90, len(depths)),
        "azimuth": np.random.uniform(0, 360, len(depths)),
        "tvd": depths * 0.95,  # True vertical depth
        "northing": np.cumsum(np.random.uniform(-10, 10, len(depths))),
        "easting": np.cumsum(np.random.uniform(-10, 10, len(depths))),
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_financial_data():
    """Generate sample financial data for NPV calculations."""
    periods = 360  # 30 years monthly
    data = {
        "period": range(1, periods + 1),
        "revenue": np.random.uniform(100000, 500000, periods),
        "opex": np.random.uniform(20000, 100000, periods),
        "capex": np.zeros(periods),
    }
    # Add some initial capex
    data["capex"][:12] = np.random.uniform(1000000, 2000000, 12)
    return pd.DataFrame(data)


@pytest.fixture
def performance_thresholds():
    """Define performance thresholds for critical operations."""
    return {
        "data_loading": 1.0,  # seconds
        "data_processing": 5.0,  # seconds
        "npv_calculation": 0.5,  # seconds
        "visualization": 2.0,  # seconds
        "export": 3.0,  # seconds
        "memory_usage_mb": 500,  # MB
    }


@pytest.fixture(autouse=True)
def reset_random_state():
    """Reset random state for reproducible benchmarks."""
    np.random.seed(42)
    random.seed(42)
