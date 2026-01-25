"""
Test marker utilities and decorators for WorldEnergyData tests.

This module provides convenient decorators and utilities for marking tests
with appropriate categories for selective execution.
"""

import pytest
from typing import Callable, Any


# ==================== Marker Decorators ====================

unit = pytest.mark.unit
"""Mark test as a unit test - fast, isolated test of individual component."""

integration = pytest.mark.integration
"""Mark test as an integration test - tests component interactions."""

performance = pytest.mark.performance
"""Mark test as a performance test - benchmark and timing test."""

data_validation = pytest.mark.data_validation
"""Mark test as a data validation test - verifies data quality."""

slow = pytest.mark.slow
"""Mark test as slow - takes more than 1 second to execute."""

smoke = pytest.mark.smoke
"""Mark test as a smoke test - quick verification test."""

regression = pytest.mark.regression
"""Mark test as a regression test - test for previously fixed bug."""

api = pytest.mark.api
"""Mark test as an API test - tests external API interactions."""

database = pytest.mark.database
"""Mark test as a database test - requires database access."""

network = pytest.mark.network
"""Mark test as a network test - requires network access."""

skip_ci = pytest.mark.skip_ci
"""Mark test to skip in CI/CD - should not run in automated pipelines."""

wip = pytest.mark.wip
"""Mark test as work in progress - test under development."""


# ==================== Conditional Markers ====================

def requires_network(func: Callable) -> Callable:
    """
    Mark test as requiring network access and skip if offline.
    """
    import socket
    
    def has_network():
        try:
            socket.create_connection(("8.8.8.8", 80), timeout=3)
            return True
        except OSError:
            return False
    
    return pytest.mark.skipif(
        not has_network(),
        reason="Network access required but not available"
    )(network(func))


def requires_data_file(filename: str) -> Callable:
    """
    Mark test as requiring specific data file and skip if not present.
    
    Args:
        filename: Name of required data file
    """
    from pathlib import Path
    
    def decorator(func: Callable) -> Callable:
        data_path = Path("tests/test_data") / filename
        return pytest.mark.skipif(
            not data_path.exists(),
            reason=f"Required data file {filename} not found"
        )(func)
    
    return decorator


def min_python_version(version: str) -> Callable:
    """
    Mark test to run only on specified Python version or higher.
    
    Args:
        version: Minimum Python version (e.g., "3.10")
    """
    import sys
    
    def decorator(func: Callable) -> Callable:
        major, minor = map(int, version.split('.'))
        current = sys.version_info
        
        return pytest.mark.skipif(
            current.major < major or 
            (current.major == major and current.minor < minor),
            reason=f"Requires Python {version} or higher"
        )(func)
    
    return decorator


# ==================== Marker Combinations ====================

def unit_fast(func: Callable) -> Callable:
    """Mark test as a fast unit test."""
    return unit(pytest.mark.timeout(1)(func))


def integration_slow(func: Callable) -> Callable:
    """Mark test as a slow integration test."""
    return integration(slow(func))


def performance_benchmark(func: Callable) -> Callable:
    """Mark test as a performance benchmark test."""
    return performance(pytest.mark.benchmark(func))


# ==================== Test Suite Helpers ====================

class TestSuites:
    """Predefined test suite combinations."""
    
    QUICK = "-m 'smoke or (unit and not slow)'"
    """Quick test suite - smoke tests and fast unit tests."""
    
    UNIT = "-m unit"
    """All unit tests."""
    
    INTEGRATION = "-m integration"
    """All integration tests."""
    
    PERFORMANCE = "-m performance"
    """All performance tests."""
    
    CI = "-m 'not skip_ci and not wip'"
    """Tests suitable for CI/CD."""
    
    FULL = "-m 'not wip'"
    """Full test suite excluding work in progress."""
    
    DATA = "-m data_validation"
    """Data validation tests."""
    
    OFFLINE = "-m 'not network and not api'"
    """Tests that don't require network access."""


# ==================== Usage Examples ====================

def example_usage():
    """
    Example usage of test markers:
    
    # Single marker
    @unit
    def test_simple_function():
        assert 1 + 1 == 2
    
    # Multiple markers
    @unit
    @smoke
    def test_critical_function():
        assert True
    
    # Conditional markers
    @requires_network
    def test_api_call():
        # Test API functionality
        pass
    
    # Custom timeout
    @pytest.mark.timeout(10)
    @integration
    def test_complex_workflow():
        # Test complex integration
        pass
    
    # Run specific test suites from command line:
    # pytest -m "unit"                    # Run all unit tests
    # pytest -m "unit and not slow"       # Run fast unit tests
    # pytest -m "smoke"                   # Run smoke tests
    # pytest -m "not network"             # Run offline tests
    """
    pass


if __name__ == "__main__":
    print("Test Marker Utilities for WorldEnergyData")
    print("\nAvailable markers:")
    markers = [
        "unit", "integration", "performance", "data_validation",
        "slow", "smoke", "regression", "api", "database", 
        "network", "skip_ci", "wip"
    ]
    for marker in markers:
        print(f"  - {marker}")
    
    print("\nPredefined test suites:")
    for suite_name in dir(TestSuites):
        if not suite_name.startswith('_'):
            suite_cmd = getattr(TestSuites, suite_name)
            if isinstance(suite_cmd, str):
                print(f"  - {suite_name}: {suite_cmd}")