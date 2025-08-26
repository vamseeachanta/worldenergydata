"""
Pytest configuration with performance tracking.
"""

import pytest
from pathlib import Path
from worldenergydata.testing.performance import TestPerformanceTracker


# Initialize global tracker
_performance_tracker = None


def pytest_configure(config):
    """Configure pytest with performance tracking."""
    global _performance_tracker
    
    # Initialize performance tracker
    db_path = Path(".test_performance.db")
    _performance_tracker = TestPerformanceTracker(db_path)
    
    # Register as plugin
    config.pluginmanager.register(_performance_tracker, 'performance_tracker')


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Called before test setup."""
    if _performance_tracker:
        _performance_tracker.start_test(item.nodeid)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Called to create test report."""
    outcome = yield
    report = outcome.get_result()
    
    # Only record on test call (not setup/teardown)
    if report.when == 'call' and _performance_tracker:
        _performance_tracker.end_test(item.nodeid, report)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Called after test session finishes."""
    if _performance_tracker:
        summary = _performance_tracker.get_session_summary()
        
        print("\n" + "="*60)
        print("Test Performance Summary")
        print("="*60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print(f"Average Duration: {summary['avg_duration']:.3f}s")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        
        # Check for regressions
        from worldenergydata.testing.performance import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer(_performance_tracker.db)
        regressions = analyzer.detect_regressions(lookback_days=7)
        
        if regressions:
            print("\n⚠️  Performance Regressions Detected:")
            for reg in regressions[:3]:
                print(f"  - {reg['test_name']}: {reg['regression_factor']:.2f}x slower")
        
        print("="*60)


# Custom markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests for performance tracking"
    )
    config.addinivalue_line(
        "markers", "benchmark: marks tests for benchmarking"
    )