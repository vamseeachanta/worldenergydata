"""Tests for well production dashboard monitoring module."""

import importlib
import json
import sys
from datetime import datetime

# The well_production_dashboard __init__.py chains imports that require reportlab.
# Import the monitoring module directly to avoid the chain.
_spec = importlib.util.spec_from_file_location(
    "worldenergydata.well_production_dashboard.monitoring",
    "src/worldenergydata/well_production_dashboard/monitoring.py",
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

AuditEntry = _mod.AuditEntry
DashboardMonitor = _mod.DashboardMonitor
PerformanceMetrics = _mod.PerformanceMetrics
monitor_function = _mod.monitor_function


class TestAuditEntry:
    def test_defaults(self):
        entry = AuditEntry()
        assert entry.user == "system"
        assert entry.action == ""
        assert entry.resource == ""
        assert entry.details == {}
        assert entry.status == "success"
        assert entry.duration_ms is None
        assert entry.verification_score is None
        assert isinstance(entry.timestamp, datetime)

    def test_custom(self):
        entry = AuditEntry(
            user="admin",
            action="data_export",
            resource="well_W001",
            details={"format": "csv"},
            status="success",
            duration_ms=150.0,
            verification_score=0.95,
        )
        assert entry.user == "admin"
        assert entry.action == "data_export"
        assert entry.resource == "well_W001"
        assert entry.details == {"format": "csv"}
        assert entry.duration_ms == 150.0
        assert entry.verification_score == 0.95

    def test_to_dict(self):
        entry = AuditEntry(
            user="admin",
            action="query",
            resource="well_W001",
        )
        d = entry.to_dict()
        assert d["user"] == "admin"
        assert d["action"] == "query"
        assert d["resource"] == "well_W001"
        assert isinstance(d["timestamp"], str)

    def test_to_json(self):
        entry = AuditEntry(action="test", resource="r1")
        j = entry.to_json()
        parsed = json.loads(j)
        assert parsed["action"] == "test"
        assert parsed["resource"] == "r1"


class TestPerformanceMetrics:
    def test_defaults(self):
        pm = PerformanceMetrics()
        assert pm.query_count == 0
        assert pm.total_query_time == 0.0
        assert pm.cache_hits == 0
        assert pm.cache_misses == 0
        assert pm.data_points_processed == 0
        assert pm.errors_count == 0
        assert pm.avg_response_time == 0.0
        assert pm.peak_memory_mb == 0.0
        assert pm.active_sessions == 0

    def test_update_average_response_time(self):
        pm = PerformanceMetrics()
        pm.query_count = 10
        pm.total_query_time = 500.0
        pm.update_average_response_time()
        assert pm.avg_response_time == 50.0

    def test_update_average_zero_queries(self):
        pm = PerformanceMetrics()
        pm.update_average_response_time()
        assert pm.avg_response_time == 0.0


class TestDashboardMonitorInit:
    def test_defaults(self, tmp_path):
        # Disable background monitoring to avoid thread issues in tests
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        assert isinstance(mon.metrics, PerformanceMetrics)
        assert mon.alert_thresholds["response_time_ms"] == 5000
        assert mon.alert_thresholds["error_rate"] == 0.05
        assert mon.alert_thresholds["memory_mb"] == 1000
        assert mon.alert_thresholds["quality_score"] == 0.7
        assert mon.alert_callbacks == []

    def test_custom_thresholds(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
            "alert_response_time": 3000,
            "alert_error_rate": 0.1,
        }
        mon = DashboardMonitor(config=config)
        assert mon.alert_thresholds["response_time_ms"] == 3000
        assert mon.alert_thresholds["error_rate"] == 0.1


class TestAuditAction:
    def test_basic(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        entry = mon.audit_action("data_export", "well_W001", user="admin")
        assert entry.action == "data_export"
        assert entry.resource == "well_W001"
        assert entry.user == "admin"
        assert len(mon.audit_entries) == 1

    def test_with_details(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        entry = mon.audit_action(
            "query", "field_XYZ",
            details={"filter": "active"},
            verification_score=0.95,
        )
        assert entry.details == {"filter": "active"}
        assert entry.verification_score == 0.95

    def test_writes_to_file(self, tmp_path):
        audit_file = tmp_path / "audit.jsonl"
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(audit_file),
        }
        mon = DashboardMonitor(config=config)
        mon.audit_action("test_action", "test_resource")
        content = audit_file.read_text()
        parsed = json.loads(content.strip())
        assert parsed["action"] == "test_action"


class TestAuditVerification:
    def test_basic(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        entry = mon.audit_verification("W001", 0.85, ["spike_detected"])
        assert entry.action == "data_verification"
        assert entry.resource == "well_W001"
        assert entry.details["quality_score"] == 0.85
        assert entry.details["anomalies"] == ["spike_detected"]
        assert entry.details["anomaly_count"] == 1
        assert entry.details["passed"] is True  # 0.85 >= 0.7

    def test_below_threshold(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        entry = mon.audit_verification("W002", 0.5, ["missing_data", "outlier"])
        assert entry.details["passed"] is False  # 0.5 < 0.7


class TestTrackCacheAccess:
    def test_hit(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        mon.track_cache_access(True)
        assert mon.metrics.cache_hits == 1
        assert mon.metrics.cache_misses == 0

    def test_miss(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        mon.track_cache_access(False)
        assert mon.metrics.cache_hits == 0
        assert mon.metrics.cache_misses == 1


class TestTrackDataProcessing:
    def test_basic(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        mon.track_data_processing(100)
        mon.track_data_processing(50)
        assert mon.metrics.data_points_processed == 150


class TestDetectAnomaly:
    def test_not_enough_data(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        # Less than 10 data points
        for i in range(9):
            assert mon.detect_anomaly("metric1", float(i)) is False

    def test_normal_values(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        # Add values with natural variance so 101 is within 3 std devs
        import random
        random.seed(42)
        for _ in range(20):
            mon.detect_anomaly("metric1", 100.0 + random.uniform(-5, 5))
        assert mon.detect_anomaly("metric1", 101.0) is False

    def test_anomalous_value(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        # Add 10 similar values, then check a wildly different value
        for _ in range(10):
            mon.detect_anomaly("metric1", 100.0)
        # All values are 100.0 so std_dev is small; 1000.0 should be anomalous
        # But wait -- if all values are exactly the same, std_dev = 0, so no anomaly detected
        # Add some small variance first
        for i in range(10):
            mon.detect_anomaly("metric1", 100.0 + i * 0.1)
        assert mon.detect_anomaly("metric1", 500.0) is True


class TestGetMetricsSummary:
    def test_initial(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        summary = mon.get_metrics_summary()
        assert summary["query_count"] == 0
        assert summary["avg_response_time_ms"] == 0.0
        assert summary["cache_hit_rate"] == 0
        assert summary["error_rate"] == 0

    def test_with_data(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        mon.metrics.query_count = 100
        mon.metrics.errors_count = 5
        mon.metrics.cache_hits = 60
        mon.metrics.cache_misses = 40
        mon.metrics.avg_response_time = 200.0
        mon.metrics.data_points_processed = 5000
        summary = mon.get_metrics_summary()
        assert summary["query_count"] == 100
        assert summary["error_rate"] == 0.05
        assert summary["cache_hit_rate"] == 0.6


class TestGetAuditTrail:
    def test_no_filters(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        mon.audit_action("action1", "resource1")
        mon.audit_action("action2", "resource2")
        trail = mon.get_audit_trail()
        assert len(trail) == 2

    def test_filter_by_resource(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        mon.audit_action("action1", "well_W001")
        mon.audit_action("action2", "well_W002")
        mon.audit_action("action3", "well_W001")
        trail = mon.get_audit_trail(resource="well_W001")
        assert len(trail) == 2

    def test_filter_by_user(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        mon.audit_action("action1", "r1", user="admin")
        mon.audit_action("action2", "r2", user="system")
        trail = mon.get_audit_trail(user="admin")
        assert len(trail) == 1
        assert trail[0].user == "admin"


class TestRegisterAlertCallback:
    def test_register(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        alerts = []
        mon.register_alert_callback(lambda a: alerts.append(a))
        assert len(mon.alert_callbacks) == 1


class TestTriggerAlert:
    def test_callback_called(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        alerts = []
        mon.register_alert_callback(lambda a: alerts.append(a))
        mon._trigger_alert("test_alert", {"detail": "info"})
        assert len(alerts) == 1
        assert alerts[0]["type"] == "test_alert"

    def test_callback_error_handled(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)

        def bad_callback(alert):
            raise RuntimeError("callback failed")

        mon.register_alert_callback(bad_callback)
        # Should not raise
        mon._trigger_alert("test", {})


class TestTrackPerformance:
    def test_basic(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        with mon.track_performance("test_op"):
            pass
        assert mon.metrics.query_count == 1
        assert mon.metrics.total_query_time > 0

    def test_error_tracked(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)
        try:
            with mon.track_performance("test_op"):
                raise ValueError("test error")
        except ValueError:
            pass
        assert mon.metrics.errors_count == 1
        assert mon.metrics.query_count == 1


class TestMonitorFunction:
    def test_decorator_without_monitor(self):
        @monitor_function(action="test")
        def my_func():
            return 42

        assert my_func() == 42

    def test_decorator_with_monitor_kwarg(self, tmp_path):
        config = {
            "enable_background_monitoring": False,
            "audit_file": str(tmp_path / "audit.jsonl"),
        }
        mon = DashboardMonitor(config=config)

        @monitor_function(action="test_action")
        def my_func(monitor=None):
            return 42

        result = my_func(monitor=mon)
        assert result == 42
        assert mon.metrics.query_count == 1
