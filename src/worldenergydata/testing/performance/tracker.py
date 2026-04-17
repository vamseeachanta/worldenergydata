"""
Test performance tracker using pytest hooks.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import psutil
import pytest

from worldenergydata.common.logging import get_logger

from .database import PerformanceDatabase, TestExecutionRecord

logger = get_logger(__name__)


class TestPerformanceTracker:
    """Track test performance metrics during execution."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize performance tracker.

        Args:
            db_path: Path to performance database
        """
        self.db = PerformanceDatabase(db_path)
        self.test_start_times: Dict[str, float] = {}
        self.test_memory_start: Dict[str, float] = {}
        self.test_cpu_start: Dict[str, float] = {}
        self.process = psutil.Process()

    def start_test(self, nodeid: str):
        """
        Record test start metrics.

        Args:
            nodeid: Test node ID
        """
        self.test_start_times[nodeid] = time.perf_counter()

        # Record resource usage at start
        try:
            self.test_memory_start[nodeid] = (
                self.process.memory_info().rss / 1024 / 1024
            )  # MB
            self.test_cpu_start[nodeid] = self.process.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def end_test(self, nodeid: str, report: pytest.TestReport):
        """
        Record test end metrics and save to database.

        Args:
            nodeid: Test node ID
            report: Pytest test report
        """
        if nodeid not in self.test_start_times:
            return

        # Calculate duration
        duration = time.perf_counter() - self.test_start_times[nodeid]

        # Calculate resource usage
        memory_usage = None
        cpu_usage = None

        try:
            current_memory = self.process.memory_info().rss / 1024 / 1024
            memory_usage = current_memory - self.test_memory_start.get(
                nodeid, current_memory
            )
            cpu_usage = self.process.cpu_percent() - self.test_cpu_start.get(nodeid, 0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        # Determine test status
        if report.passed:
            status = "passed"
        elif report.failed:
            status = "failed"
        elif report.skipped:
            status = "skipped"
        else:
            status = "unknown"

        # Extract test name and module
        parts = nodeid.split("::")
        if len(parts) >= 2:
            module = parts[0]
            test_name = "::".join(parts[1:])
        else:
            module = nodeid
            test_name = nodeid

        # Get error message if failed
        error_message = None
        if report.failed and report.longrepr:
            error_message = str(report.longrepr)[:500]  # Limit error message length

        # Determine test size based on duration
        if duration < 0.1:
            test_size = "small"
        elif duration < 1.0:
            test_size = "medium"
        else:
            test_size = "large"

        # Create execution record
        record = TestExecutionRecord(
            test_name=test_name,
            module=module,
            duration=duration,
            status=status,
            timestamp=datetime.now(),
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            error_message=error_message,
            test_size=test_size,
            tags=report.keywords if hasattr(report, "keywords") else None,
        )

        # Save to database
        self.db.record_execution(record)

        # Clean up
        self.test_start_times.pop(nodeid, None)
        self.test_memory_start.pop(nodeid, None)
        self.test_cpu_start.pop(nodeid, None)

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of the current test session.

        Returns:
            Dictionary with session metrics
        """
        # Get recent executions from this session
        now = datetime.now()

        # This would typically filter by session ID
        # For now, get tests from last hour
        recent_tests = self.db.get_performance_trends(days=1)

        if recent_tests.empty:
            return {
                "total_tests": 0,
                "total_duration": 0,
                "avg_duration": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0,
            }

        latest = recent_tests.iloc[0]

        return {
            "total_tests": int(latest["total_tests"]),
            "total_duration": float(latest["total_duration"]),
            "avg_duration": float(latest["avg_duration"]),
            "passed_tests": int(latest["passed_tests"]),
            "failed_tests": int(latest["failed_tests"]),
            "success_rate": float(latest.get("success_rate", 0)),
        }


# Pytest plugin implementation
class PytestPerformancePlugin:
    """Pytest plugin for performance tracking."""

    def __init__(self, tracker: Optional[TestPerformanceTracker] = None):
        """
        Initialize plugin.

        Args:
            tracker: Performance tracker instance
        """
        self.tracker = tracker or TestPerformanceTracker()

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item):
        """Called before test setup."""
        self.tracker.start_test(item.nodeid)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        """Called to create test report."""
        outcome = yield
        report = outcome.get_result()

        # Only record on test call (not setup/teardown)
        if report.when == "call":
            self.tracker.end_test(item.nodeid, report)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus):
        """Called after test session finishes."""
        summary = self.tracker.get_session_summary()

        logger.info("\n" + "=" * 60)
        logger.info("Test Performance Summary")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {summary['total_tests']}")
        logger.info(f"Total Duration: {summary['total_duration']:.2f}s")
        logger.info(f"Average Duration: {summary['avg_duration']:.3f}s")
        logger.info(f"Success Rate: {summary['success_rate']:.1f}%")
        logger.info("=" * 60)


def pytest_configure(config):
    """Register the plugin."""
    config.pluginmanager.register(PytestPerformancePlugin(), "performance_tracker")
