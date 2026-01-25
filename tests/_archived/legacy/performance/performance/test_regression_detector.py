"""
Tests for Performance Regression Detection System
"""

import pytest
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch
from tests.performance.regression_detector import (
    PerformanceRegressionDetector,
    RegressionMonitor
)


class TestPerformanceRegressionDetector:
    """Test suite for regression detection functionality"""
    
    @pytest.fixture
    def detector(self, tmp_path):
        """Create detector with temporary baseline path"""
        return PerformanceRegressionDetector(
            baseline_path=str(tmp_path / "baselines"),
            threshold_percent=20.0
        )
    
    def test_init(self, detector):
        """Test detector initialization"""
        assert detector.threshold_percent == 20.0
        assert detector.baseline_path.exists()
        assert detector.current_metrics == {}
        assert detector.baselines == {}
    
    def test_record_metric(self, detector):
        """Test recording performance metrics"""
        detector.record_metric("test_func", 1.5, memory_usage=100.0)
        detector.record_metric("test_func", 1.6, memory_usage=105.0)
        
        assert "test_func" in detector.current_metrics
        assert len(detector.current_metrics["test_func"]["execution_times"]) == 2
        assert detector.current_metrics["test_func"]["execution_times"] == [1.5, 1.6]
        assert detector.current_metrics["test_func"]["memory_usage"] == [100.0, 105.0]
    
    def test_detect_regression_no_baseline(self, detector):
        """Test regression detection with no baseline"""
        detector.record_metric("test_func", 1.5)
        has_regression, details = detector.detect_regression("test_func")
        
        assert not has_regression
        assert "warning" in details
        assert details["warning"] == "No baseline for comparison"
    
    def test_detect_regression_with_regression(self, detector):
        """Test detecting actual regression"""
        # Set baseline
        detector.baselines["test_func"] = {
            "avg_execution_time": 1.0,
            "std_execution_time": 0.1
        }
        
        # Record slower execution
        detector.record_metric("test_func", 1.3)  # 30% slower
        detector.record_metric("test_func", 1.25)
        
        has_regression, details = detector.detect_regression("test_func")
        
        assert has_regression
        assert details["percent_change"] > 20
        assert details["has_regression"] is True
    
    def test_detect_regression_within_threshold(self, detector):
        """Test when performance is within acceptable threshold"""
        # Set baseline
        detector.baselines["test_func"] = {
            "avg_execution_time": 1.0,
            "std_execution_time": 0.1
        }
        
        # Record slightly slower execution (within threshold)
        detector.record_metric("test_func", 1.1)  # 10% slower
        detector.record_metric("test_func", 1.15)
        
        has_regression, details = detector.detect_regression("test_func")
        
        assert not has_regression
        assert details["percent_change"] < 20
        assert details["has_regression"] is False
    
    def test_detect_improvement(self, detector):
        """Test detecting performance improvement"""
        # Set baseline
        detector.baselines["test_func"] = {
            "avg_execution_time": 2.0,
            "std_execution_time": 0.1
        }
        
        # Record faster execution
        detector.record_metric("test_func", 1.5)  # 25% faster
        detector.record_metric("test_func", 1.4)
        
        has_regression, details = detector.detect_regression("test_func")
        
        assert not has_regression
        assert details["percent_change"] < 0  # Negative means improvement
    
    def test_save_and_load_baselines(self, detector):
        """Test saving and loading baselines"""
        # Record metrics
        detector.record_metric("test1", 1.0)
        detector.record_metric("test2", 2.0)
        
        # Convert to baselines
        detector.update_baselines_smart()
        detector.save_baselines("test_module")
        
        # Create new detector and load
        new_detector = PerformanceRegressionDetector(
            baseline_path=str(detector.baseline_path)
        )
        loaded = new_detector.load_baselines("test_module")
        
        assert "test1" in loaded
        assert "test2" in loaded
        assert loaded["test1"]["avg_execution_time"] == 1.0
        assert loaded["test2"]["avg_execution_time"] == 2.0
    
    def test_analyze_all_tests(self, detector):
        """Test analyzing all recorded tests"""
        # Set baselines
        detector.baselines = {
            "test_regression": {"avg_execution_time": 1.0},
            "test_improvement": {"avg_execution_time": 2.0},
            "test_stable": {"avg_execution_time": 1.0}
        }
        
        # Record current metrics
        detector.record_metric("test_regression", 1.5)  # 50% slower
        detector.record_metric("test_improvement", 1.5)  # 25% faster
        detector.record_metric("test_stable", 1.05)  # 5% slower (stable)
        
        results = detector.analyze_all_tests()
        
        assert len(results["regressions"]) == 1
        assert len(results["improvements"]) == 1
        assert len(results["stable"]) == 1
        assert results["total_tests"] == 3
    
    def test_update_baselines_smart(self, detector):
        """Test smart baseline updates (skip regressions)"""
        # Set initial baselines
        detector.baselines = {
            "test_regression": {"avg_execution_time": 1.0},
            "test_improvement": {"avg_execution_time": 2.0}
        }
        
        # Record metrics
        detector.record_metric("test_regression", 1.5)  # Regression
        detector.record_metric("test_improvement", 1.5)  # Improvement
        
        original_regression_baseline = detector.baselines["test_regression"]["avg_execution_time"]
        
        detector.update_baselines_smart()
        
        # Regression baseline should not update
        assert detector.baselines["test_regression"]["avg_execution_time"] == original_regression_baseline
        # Improvement baseline should update
        assert detector.baselines["test_improvement"]["avg_execution_time"] == 1.5
    
    def test_generate_report(self, detector):
        """Test report generation"""
        # Setup test data
        detector.baselines = {
            "test_slow": {"avg_execution_time": 1.0},
            "test_fast": {"avg_execution_time": 2.0}
        }
        
        detector.record_metric("test_slow", 1.5)  # Regression
        detector.record_metric("test_fast", 1.5)  # Improvement
        
        report = detector.generate_report()
        
        assert "Performance Regression Detection Report" in report
        assert "REGRESSIONS DETECTED: 1" in report
        assert "IMPROVEMENTS: 1" in report
        assert "test_slow" in report
        assert "test_fast" in report


class TestRegressionMonitor:
    """Test suite for regression monitoring"""
    
    @pytest.fixture
    def monitor(self, tmp_path):
        """Create monitor with detector"""
        detector = PerformanceRegressionDetector(
            baseline_path=str(tmp_path / "baselines")
        )
        return RegressionMonitor(detector)
    
    def test_start_end_test(self, monitor):
        """Test monitoring test execution"""
        monitor.start_test("test_func")
        assert "test_func" in monitor.start_times
        
        time.sleep(0.01)  # Small delay
        monitor.end_test("test_func", memory_usage=100.0)
        
        assert "test_func" not in monitor.start_times
        assert "test_func" in monitor.detector.current_metrics
        assert len(monitor.detector.current_metrics["test_func"]["execution_times"]) == 1
    
    def test_end_test_without_start(self, monitor):
        """Test ending test that wasn't started"""
        with pytest.warns(UserWarning, match="was not started"):
            monitor.end_test("test_func")
    
    def test_regression_warning(self, monitor):
        """Test warning on regression detection"""
        # Set baseline for regression
        monitor.detector.baselines["test_func"] = {
            "avg_execution_time": 0.001
        }
        
        monitor.start_test("test_func")
        time.sleep(0.01)  # Ensure it's slower than baseline
        
        with pytest.warns(UserWarning, match="Performance regression detected"):
            monitor.end_test("test_func")


@pytest.mark.benchmark
class TestRegressionDetectorIntegration:
    """Integration tests with pytest-benchmark"""
    
    def test_integration_with_benchmark(self, benchmark, tmp_path):
        """Test integration with pytest-benchmark"""
        detector = PerformanceRegressionDetector(
            baseline_path=str(tmp_path / "baselines")
        )
        
        def sample_function():
            """Sample function to benchmark"""
            result = sum(i ** 2 for i in range(1000))
            return result
        
        # Run benchmark
        result = benchmark(sample_function)
        
        # Record benchmark result
        detector.record_metric(
            "sample_function",
            benchmark.stats["mean"],
            memory_usage=None
        )
        
        # Should not have regression on first run
        has_regression, details = detector.detect_regression("sample_function")
        assert not has_regression  # No baseline yet
        
        # Update baseline
        detector.update_baselines_smart()
        
        # Simulate slower execution
        detector.current_metrics = {}
        detector.record_metric(
            "sample_function",
            benchmark.stats["mean"] * 1.5  # 50% slower
        )
        
        # Should detect regression
        has_regression, details = detector.detect_regression("sample_function")
        assert has_regression
        assert details["percent_change"] > 40