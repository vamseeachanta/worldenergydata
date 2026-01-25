"""
Pytest configuration with performance tracking.
"""

import sys
from pathlib import Path

# Add src directory to sys.path so pytest can resolve validators module
# (validators is a top-level package at src/validators/, separate from worldenergydata)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
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


# Skip collection of experimental/archived test files
def pytest_ignore_collect(path, config):
    """Skip collection of experimental and archived test files.

    Test directory structure (2025-01):
        tests/
        ├── unit/           # Module-grouped unit tests
        │   ├── bsee/
        │   ├── fdas/
        │   ├── marine_safety/
        │   ├── hse/
        │   ├── reporting/
        │   ├── vessel_hull_models/
        │   └── well_production_dashboard/
        ├── integration/    # Integration tests
        │   └── modules/
        ├── e2e/            # End-to-end tests
        ├── fixtures/       # Test fixtures
        ├── helpers/        # Test helpers
        └── _archived/      # Legacy tests (not collected)
            ├── legacy/
            └── validation_runs/
    """
    import re
    path_str = str(path)
    basename = path.basename

    # Skip query_*.py files (exploratory scripts)
    if basename.startswith("query_") and basename.endswith("_test.py"):
        return True

    # Skip _archived directory and all subdirectories (consolidated 2025-01)
    if "/_archived/" in path_str or path_str.endswith("/_archived"):
        return True

    # Legacy pattern - keep for backward compatibility
    if "_archived_tests" in path_str:
        return True

    # Skip 2025-* dated experimental directories
    if re.search(r"202\d-\d{2}-\d{2}", basename):
        return True

    # Skip directories explicitly listed in norecursedirs but not being honored
    excluded_patterns = [
        "comprehensive-report-system",
        "financial-analysis-sme-code",
        "well-data-verification",
        "/legacy/",
        "legacy_",
        "custom_scripts",
    ]

    for pattern in excluded_patterns:
        if pattern in path_str:
            return True

    return False