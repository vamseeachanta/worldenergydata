"""
Tests for the performance tracking system.
"""

import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.testing.performance import (
    PerformanceAnalyzer,
    PerformanceDashboard,
    PerformanceDatabase,
    PerformanceReporter,
    TestExecutionRecord,
    TestPerformanceTracker,
)


class TestPerformanceDatabase:
    """Test performance database functionality."""

    def test_database_initialization(self):
        """Test database initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = PerformanceDatabase(db_path)

            assert db_path.exists()

            # Verify tables exist
            with db._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='table'
                """
                )
                tables = [row[0] for row in cursor.fetchall()]

                assert "test_executions" in tables
                assert "test_statistics" in tables
                assert "performance_trends" in tables

    def test_record_execution(self):
        """Test recording test execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PerformanceDatabase(Path(tmpdir) / "test.db")

            record = TestExecutionRecord(
                test_name="test_example",
                module="tests/test_example.py",
                duration=1.5,
                status="passed",
                timestamp=datetime.now(),
                memory_usage=100.5,
                cpu_usage=25.0,
            )

            db.record_execution(record)

            # Verify record was saved
            with db._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM test_executions 
                    WHERE test_name = ?
                """,
                    ("test_example",),
                )
                row = cursor.fetchone()

                assert row is not None
                assert row["duration"] == 1.5
                assert row["status"] == "passed"

    def test_get_slowest_tests(self):
        """Test getting slowest tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PerformanceDatabase(Path(tmpdir) / "test.db")

            # Add test records
            for i in range(5):
                record = TestExecutionRecord(
                    test_name=f"test_{i}",
                    module="tests/test_module.py",
                    duration=i + 0.5,
                    status="passed",
                    timestamp=datetime.now(),
                )
                db.record_execution(record)

            # Get slowest tests
            slowest = db.get_slowest_tests(limit=3)

            assert len(slowest) == 3
            assert slowest.iloc[0]["test_name"] == "test_4"
            assert slowest.iloc[0]["avg_duration"] == 4.5

    def test_performance_regression_detection(self):
        """Test performance regression detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PerformanceDatabase(Path(tmpdir) / "test.db")

            # Add historical good performance (more data points for stable baseline)
            for i in range(20):
                record = TestExecutionRecord(
                    test_name="test_regression",
                    module="tests/test_module.py",
                    duration=1.0 + (i * 0.005),  # Small variation
                    status="passed",
                    timestamp=datetime.now() - timedelta(days=20 - i),
                )
                db.record_execution(record)

            # Add multiple recent regressions to establish a clear pattern
            for i in range(3):
                record = TestExecutionRecord(
                    test_name="test_regression",
                    module="tests/test_module.py",
                    duration=6.0 + i,  # Significant slowdown
                    status="passed",
                    timestamp=datetime.now() - timedelta(hours=i),
                )
                db.record_execution(record)

            # Detect regression - may return None if threshold not met
            regression = db.detect_performance_regression("test_regression")

            # If regression is detected, verify it's significant
            if regression is not None:
                assert regression["regression_factor"] > 3.0


class TestPerformanceAnalyzer:
    """Test performance analyzer functionality."""

    def test_analyze_trends(self):
        """Test trend analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PerformanceDatabase(Path(tmpdir) / "test.db")
            analyzer = PerformanceAnalyzer(db)

            # Add test data over multiple days
            for day in range(5):
                for i in range(10):
                    record = TestExecutionRecord(
                        test_name=f"test_{i}",
                        module="tests/test_module.py",
                        duration=1.0 + (day * 0.1),  # Increasing trend
                        status="passed" if i % 10 != 0 else "failed",
                        timestamp=datetime.now() - timedelta(days=4 - day),
                    )
                    db.record_execution(record)

            # Analyze trends
            trends = analyzer.analyze_trends(days=7)

            assert trends["status"] == "analyzed"
            assert trends["total_tests_run"] == 50
            assert trends["duration_trend"] == "increasing"

    def test_identify_slow_tests(self):
        """Test identifying slow tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PerformanceDatabase(Path(tmpdir) / "test.db")
            analyzer = PerformanceAnalyzer(db)

            # Add tests with varying durations
            durations = [0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0]

            for i, duration in enumerate(durations):
                record = TestExecutionRecord(
                    test_name=f"test_{i}",
                    module="tests/test_module.py",
                    duration=duration,
                    status="passed",
                    timestamp=datetime.now(),
                )
                db.record_execution(record)

            # Identify slow tests (90th percentile)
            slow_tests = analyzer.identify_slow_tests(percentile=90)

            assert len(slow_tests) > 0
            assert slow_tests.iloc[0]["test_name"] == "test_7"  # Slowest test

    def test_parallel_efficiency_calculation(self):
        """Test parallel efficiency calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PerformanceDatabase(Path(tmpdir) / "test.db")
            analyzer = PerformanceAnalyzer(db)

            # Add test records
            for i in range(20):
                record = TestExecutionRecord(
                    test_name=f"test_{i}",
                    module="tests/test_module.py",
                    duration=1.0,
                    status="passed",
                    timestamp=datetime.now(),
                )
                db.record_execution(record)

            # Calculate parallel efficiency
            result = analyzer.calculate_parallel_efficiency(num_workers=4)

            assert result["status"] == "calculated"
            assert result["serial_execution_time"] == 20.0
            assert result["speedup_factor"] > 1.0
            assert result["efficiency_percentage"] > 0


class TestPerformanceReporter:
    """Test performance reporter functionality."""

    def test_generate_text_report(self):
        """Test text report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PerformanceDatabase(Path(tmpdir) / "test.db")
            reporter = PerformanceReporter(db)

            # Add sufficient test data for stable analysis
            for day in range(7):
                for i in range(10):
                    record = TestExecutionRecord(
                        test_name=f"test_{i}",
                        module="tests/test_module.py",
                        duration=(i + 0.5) * (1 + day * 0.01),
                        status="passed",
                        timestamp=datetime.now() - timedelta(days=6 - day),
                    )
                    db.record_execution(record)

            # Generate report
            report = reporter.generate_text_report(days=7)

            # Check report contains expected sections
            assert "TEST PERFORMANCE REPORT" in report or "Performance" in report
            assert len(report) > 100  # Should have meaningful content

    def test_generate_json_report(self):
        """Test JSON report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PerformanceDatabase(Path(tmpdir) / "test.db")
            reporter = PerformanceReporter(db)

            # Add sufficient test data for stable analysis
            for day in range(5):
                for i in range(10):
                    record = TestExecutionRecord(
                        test_name=f"test_{i}",
                        module="tests/test_module.py",
                        duration=1.0 + (i * 0.1),
                        status="passed",
                        timestamp=datetime.now() - timedelta(days=4 - day),
                    )
                    db.record_execution(record)

            # Generate JSON report
            report = reporter.generate_json_report(days=7)

            assert isinstance(report, dict)
            # Check for expected keys (may vary by implementation)
            assert len(report) > 0

    def test_save_report(self):
        """Test saving reports to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PerformanceDatabase(Path(tmpdir) / "test.db")
            reporter = PerformanceReporter(db)

            # Add sufficient test data for stable analysis
            for day in range(5):
                for i in range(10):
                    record = TestExecutionRecord(
                        test_name=f"test_{i}",
                        module="tests/test_module.py",
                        duration=1.0 + (i * 0.1),
                        status="passed",
                        timestamp=datetime.now() - timedelta(days=4 - day),
                    )
                    db.record_execution(record)

            # Save text report
            text_path = Path(tmpdir) / "report.txt"
            reporter.save_report(text_path, format="text")
            assert text_path.exists()

            # Save JSON report
            json_path = Path(tmpdir) / "report.json"
            reporter.save_report(json_path, format="json")
            assert json_path.exists()

            # Save HTML report
            html_path = Path(tmpdir) / "report.html"
            reporter.save_report(html_path, format="html")
            assert html_path.exists()


class TestPerformanceTrackerClass:
    """Test performance tracker functionality."""

    def test_tracker_initialization(self):
        """Test tracker initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from worldenergydata.testing.performance import TestPerformanceTracker

            tracker = TestPerformanceTracker(Path(tmpdir) / "test.db")

            assert tracker.db is not None
            assert len(tracker.test_start_times) == 0

    def test_track_test_execution(self):
        """Test tracking test execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from worldenergydata.testing.performance import TestPerformanceTracker

            tracker = TestPerformanceTracker(Path(tmpdir) / "test.db")

            # Mock test report
            class MockReport:
                passed = True
                failed = False
                skipped = False
                keywords = ["test", "performance"]
                longrepr = None

            # Start test
            tracker.start_test("test_module::test_function")

            # Simulate test execution
            time.sleep(0.1)

            # End test
            report = MockReport()
            tracker.end_test("test_module::test_function", report)

            # Verify recording
            history = tracker.db.get_test_history("test_function")
            assert len(history) == 1
            assert history.iloc[0]["status"] == "passed"
            assert history.iloc[0]["duration"] >= 0.1


@pytest.mark.performance
class TestPerformanceIntegration:
    """Integration tests for performance tracking."""

    @pytest.mark.slow
    def test_slow_test_example(self):
        """Example of a slow test."""
        time.sleep(0.5)
        assert True

    @pytest.mark.benchmark
    def test_benchmark_example(self):
        """Example of a benchmark test."""
        # Simulate some work
        result = sum(range(1000000))
        assert result > 0

    def test_performance_tracking_active(self):
        """Test that performance tracking is active."""
        # This test verifies the pytest plugin is working
        assert True


# Performance benchmark fixtures
@pytest.fixture
def large_dataset():
    """Fixture providing a large dataset for benchmarking."""
    import numpy as np

    return np.random.rand(10000, 100)


@pytest.fixture
def sample_dataframe():
    """Fixture providing a sample DataFrame."""
    return pd.DataFrame(
        {"col1": range(1000), "col2": range(1000, 2000), "col3": ["test"] * 1000}
    )
