"""
Tests for monitoring and audit logging functionality.
"""

import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

from worldenergydata.well_production_dashboard.monitoring import (
    AuditEntry,
    DashboardMonitor,
    PerformanceMetrics,
    monitor_function,
)


class TestAuditEntry(unittest.TestCase):
    """Test audit entry functionality."""

    def test_audit_entry_creation(self):
        """Test creating an audit entry."""
        entry = AuditEntry(
            user="test_user",
            action="data_export",
            resource="well_W001",
            details={"format": "excel"},
            status="success",
            duration_ms=150.5,
            verification_score=0.95,
        )

        self.assertEqual(entry.user, "test_user")
        self.assertEqual(entry.action, "data_export")
        self.assertEqual(entry.resource, "well_W001")
        self.assertEqual(entry.details["format"], "excel")
        self.assertEqual(entry.status, "success")
        self.assertEqual(entry.duration_ms, 150.5)
        self.assertEqual(entry.verification_score, 0.95)

    def test_audit_entry_to_dict(self):
        """Test converting audit entry to dictionary."""
        entry = AuditEntry(user="test_user", action="query", resource="dashboard")

        data = entry.to_dict()

        self.assertIn("timestamp", data)
        self.assertEqual(data["user"], "test_user")
        self.assertEqual(data["action"], "query")
        self.assertEqual(data["resource"], "dashboard")

    def test_audit_entry_to_json(self):
        """Test converting audit entry to JSON."""
        entry = AuditEntry(
            user="test_user",
            action="query",
            resource="dashboard",
            details={"query_type": "aggregate"},
        )

        json_str = entry.to_json()
        data = json.loads(json_str)

        self.assertEqual(data["user"], "test_user")
        self.assertEqual(data["action"], "query")
        self.assertEqual(data["details"]["query_type"], "aggregate")


class TestPerformanceMetrics(unittest.TestCase):
    """Test performance metrics functionality."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = PerformanceMetrics()

        self.assertEqual(metrics.query_count, 0)
        self.assertEqual(metrics.total_query_time, 0.0)
        self.assertEqual(metrics.cache_hits, 0)
        self.assertEqual(metrics.cache_misses, 0)
        self.assertEqual(metrics.data_points_processed, 0)
        self.assertEqual(metrics.errors_count, 0)

    def test_update_average_response_time(self):
        """Test updating average response time."""
        metrics = PerformanceMetrics()

        metrics.query_count = 10
        metrics.total_query_time = 500.0
        metrics.update_average_response_time()

        self.assertEqual(metrics.avg_response_time, 50.0)

    def test_update_average_with_zero_queries(self):
        """Test updating average with zero queries."""
        metrics = PerformanceMetrics()

        metrics.update_average_response_time()

        self.assertEqual(metrics.avg_response_time, 0.0)


class TestDashboardMonitor(unittest.TestCase):
    """Test dashboard monitor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.audit_file = Path(self.temp_dir) / "audit.jsonl"

        self.config = {
            "audit_file": str(self.audit_file),
            "enable_background_monitoring": False,
        }

        self.monitor = DashboardMonitor(config=self.config)

    def tearDown(self):
        """Clean up test fixtures."""
        # Stop monitoring if running
        if hasattr(self, "monitor"):
            self.monitor.stop_background_monitoring()

        # Clean up temp files
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_audit_action(self):
        """Test auditing an action."""
        entry = self.monitor.audit_action(
            action="data_export",
            resource="well_W001",
            user="test_user",
            details={"format": "pdf"},
            verification_score=0.85,
        )

        self.assertEqual(entry.action, "data_export")
        self.assertEqual(entry.resource, "well_W001")
        self.assertEqual(entry.user, "test_user")
        self.assertEqual(entry.verification_score, 0.85)

        # Check that entry was added to buffer
        self.assertIn(entry, self.monitor.audit_entries)

        # Check that entry was written to file
        self.assertTrue(self.audit_file.exists())

    def test_audit_verification(self):
        """Test auditing a verification."""
        entry = self.monitor.audit_verification(
            well_id="W001",
            quality_score=0.92,
            anomalies=["missing_data", "outlier"],
            user="verifier",
        )

        self.assertEqual(entry.action, "data_verification")
        self.assertEqual(entry.resource, "well_W001")
        self.assertEqual(entry.verification_score, 0.92)
        self.assertEqual(entry.details["anomaly_count"], 2)
        self.assertTrue(entry.details["passed"])

    def test_track_performance_success(self):
        """Test tracking performance of successful operation."""
        with self.monitor.track_performance("test_operation"):
            time.sleep(0.01)  # Simulate some work

        self.assertEqual(self.monitor.metrics.query_count, 1)
        self.assertGreater(self.monitor.metrics.total_query_time, 0)
        self.assertEqual(self.monitor.metrics.errors_count, 0)

    def test_track_performance_error(self):
        """Test tracking performance of failed operation."""
        try:
            with self.monitor.track_performance("test_operation"):
                raise ValueError("Test error")
        except ValueError:
            pass

        self.assertEqual(self.monitor.metrics.query_count, 1)
        self.assertEqual(self.monitor.metrics.errors_count, 1)

    def test_track_cache_access(self):
        """Test tracking cache hits and misses."""
        self.monitor.track_cache_access(hit=True)
        self.monitor.track_cache_access(hit=True)
        self.monitor.track_cache_access(hit=False)

        self.assertEqual(self.monitor.metrics.cache_hits, 2)
        self.assertEqual(self.monitor.metrics.cache_misses, 1)

    def test_track_data_processing(self):
        """Test tracking data processing."""
        self.monitor.track_data_processing(1000)
        self.monitor.track_data_processing(500)

        self.assertEqual(self.monitor.metrics.data_points_processed, 1500)

    def test_detect_anomaly(self):
        """Test anomaly detection."""
        # Add normal values
        for i in range(20):
            self.monitor.detect_anomaly("test_metric", 100 + i)

        # Add anomalous value
        is_anomaly = self.monitor.detect_anomaly("test_metric", 500)

        self.assertTrue(is_anomaly)

    def test_detect_anomaly_insufficient_data(self):
        """Test anomaly detection with insufficient data."""
        # Add only a few values
        for i in range(5):
            is_anomaly = self.monitor.detect_anomaly("test_metric", 100 + i)
            self.assertFalse(
                is_anomaly
            )  # Should not detect anomaly with insufficient data

    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        # Set up some metrics
        self.monitor.metrics.query_count = 100
        self.monitor.metrics.total_query_time = 5000
        self.monitor.metrics.cache_hits = 80
        self.monitor.metrics.cache_misses = 20
        self.monitor.metrics.errors_count = 5
        self.monitor.metrics.data_points_processed = 10000
        self.monitor.metrics.update_average_response_time()

        summary = self.monitor.get_metrics_summary()

        self.assertEqual(summary["query_count"], 100)
        self.assertEqual(summary["avg_response_time_ms"], 50.0)
        self.assertEqual(summary["cache_hit_rate"], 0.8)
        self.assertEqual(summary["error_rate"], 0.05)
        self.assertEqual(summary["data_points_processed"], 10000)

    def test_get_audit_trail_no_filters(self):
        """Test getting audit trail without filters."""
        # Add some audit entries
        self.monitor.audit_action("action1", "resource1", "user1")
        self.monitor.audit_action("action2", "resource2", "user2")
        self.monitor.audit_action("action3", "resource1", "user1")

        trail = self.monitor.get_audit_trail()

        self.assertEqual(len(trail), 3)

    def test_get_audit_trail_with_resource_filter(self):
        """Test getting audit trail with resource filter."""
        # Add some audit entries
        self.monitor.audit_action("action1", "resource1", "user1")
        self.monitor.audit_action("action2", "resource2", "user2")
        self.monitor.audit_action("action3", "resource1", "user1")

        trail = self.monitor.get_audit_trail(resource="resource1")

        self.assertEqual(len(trail), 2)
        for entry in trail:
            self.assertEqual(entry.resource, "resource1")

    def test_get_audit_trail_with_user_filter(self):
        """Test getting audit trail with user filter."""
        # Add some audit entries
        self.monitor.audit_action("action1", "resource1", "user1")
        self.monitor.audit_action("action2", "resource2", "user2")
        self.monitor.audit_action("action3", "resource1", "user1")

        trail = self.monitor.get_audit_trail(user="user1")

        self.assertEqual(len(trail), 2)
        for entry in trail:
            self.assertEqual(entry.user, "user1")

    def test_get_audit_trail_with_time_filter(self):
        """Test getting audit trail with time filter."""
        now = datetime.now()

        # Add entries with different timestamps
        entry1 = self.monitor.audit_action("action1", "resource1")
        entry1.timestamp = now - timedelta(hours=2)

        entry2 = self.monitor.audit_action("action2", "resource2")
        entry2.timestamp = now - timedelta(hours=1)

        entry3 = self.monitor.audit_action("action3", "resource3")
        entry3.timestamp = now

        # Get entries from last hour
        trail = self.monitor.get_audit_trail(
            start_time=now - timedelta(hours=1.5), end_time=now
        )

        self.assertEqual(len(trail), 2)  # Should only get entry2 and entry3

    def test_register_alert_callback(self):
        """Test registering alert callbacks."""
        callback = Mock()
        self.monitor.register_alert_callback(callback)

        # Trigger an alert
        self.monitor._trigger_alert("test_alert", {"test": "data"})

        callback.assert_called_once()
        alert = callback.call_args[0][0]
        self.assertEqual(alert["type"], "test_alert")
        self.assertEqual(alert["details"]["test"], "data")

    def test_alert_on_slow_response(self):
        """Test alert triggered on slow response."""
        self.monitor.alert_thresholds["response_time_ms"] = 10  # Set low threshold

        callback = Mock()
        self.monitor.register_alert_callback(callback)

        with self.monitor.track_performance("slow_operation"):
            time.sleep(0.02)  # Sleep for 20ms

        # Check that alert was triggered
        callback.assert_called_once()
        alert = callback.call_args[0][0]
        self.assertEqual(alert["type"], "slow_response")

    @patch("src.worldenergydata.well_production_dashboard.monitoring.psutil")
    def test_background_monitoring(self, mock_psutil):
        """Test background monitoring thread."""
        # Configure mock
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 500 * 1024 * 1024  # 500 MB
        mock_psutil.Process.return_value = mock_process

        # Create monitor with short interval
        config = {
            "audit_file": str(self.audit_file),
            "enable_background_monitoring": False,
            "monitoring_interval": 0.1,
        }
        monitor = DashboardMonitor(config=config)

        # Start monitoring
        monitor.start_background_monitoring()
        time.sleep(0.3)  # Let it run for a bit

        # Check that metrics were collected
        self.assertGreater(len(monitor.metrics_history), 0)
        self.assertGreater(monitor.metrics.peak_memory_mb, 0)

        # Stop monitoring
        monitor.stop_background_monitoring()


class TestMonitorDecorator(unittest.TestCase):
    """Test monitor function decorator."""

    def test_monitor_function_with_monitor(self):
        """Test monitor decorator with monitor instance."""
        monitor = Mock(spec=DashboardMonitor)

        @monitor_function(action="test_action")
        def test_func(x, monitor=None):
            return x * 2

        result = test_func(5, monitor=monitor)

        self.assertEqual(result, 10)
        monitor.track_performance.assert_called_once()

    def test_monitor_function_without_monitor(self):
        """Test monitor decorator without monitor instance."""

        @monitor_function(action="test_action")
        def test_func(x):
            return x * 2

        result = test_func(5)

        self.assertEqual(result, 10)  # Should work normally without monitor

    def test_monitor_function_with_class_method(self):
        """Test monitor decorator with class method."""

        class TestClass:
            def __init__(self):
                self.monitor = Mock(spec=DashboardMonitor)

            @monitor_function()
            def test_method(self, x):
                return x * 3

        obj = TestClass()
        result = obj.test_method(4)

        self.assertEqual(result, 12)
        obj.monitor.track_performance.assert_called_once()


if __name__ == "__main__":
    unittest.main()
