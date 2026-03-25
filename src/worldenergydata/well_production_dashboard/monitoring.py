"""
Monitoring and Audit Logging for Well Production Dashboard

This module provides monitoring, logging, and audit trail functionality
for the well production dashboard, integrating with the verification system
to track data quality, performance metrics, and user actions.
"""

import json
import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger(f"{__name__}.audit")


@dataclass
class AuditEntry:
    """Represents an audit log entry"""

    timestamp: datetime = field(default_factory=datetime.now)
    user: str = "system"
    action: str = ""
    resource: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    status: str = "success"
    duration_ms: Optional[float] = None
    verification_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring"""

    query_count: int = 0
    total_query_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    data_points_processed: int = 0
    errors_count: int = 0
    avg_response_time: float = 0.0
    peak_memory_mb: float = 0.0
    active_sessions: int = 0

    def update_average_response_time(self):
        """Update average response time"""
        if self.query_count > 0:
            self.avg_response_time = self.total_query_time / self.query_count


class DashboardMonitor:
    """
    Main monitoring class for the well production dashboard.

    Features:
    - Audit logging with verification integration
    - Performance metrics tracking
    - Anomaly detection
    - Resource usage monitoring
    - Alert management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize dashboard monitor.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

        # Audit storage
        self.audit_entries = deque(maxlen=10000)  # Keep last 10k entries in memory
        self.audit_file = Path(
            self.config.get("audit_file", "logs/dashboard_audit.jsonl")
        )

        # Performance metrics
        self.metrics = PerformanceMetrics()
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 metric snapshots

        # Alert thresholds
        self.alert_thresholds = {
            "response_time_ms": self.config.get("alert_response_time", 5000),
            "error_rate": self.config.get("alert_error_rate", 0.05),
            "memory_mb": self.config.get("alert_memory_mb", 1000),
            "quality_score": self.config.get("alert_quality_score", 0.7),
        }

        # Alert callbacks
        self.alert_callbacks: List[Callable] = []

        # Anomaly detection
        self.anomaly_buffer = defaultdict(list)
        self.anomaly_thresholds = self.config.get("anomaly_thresholds", {})

        # Ensure audit directory exists
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)

        # Start background monitoring thread
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        if self.config.get("enable_background_monitoring", True):
            self.start_background_monitoring()

    def audit_action(
        self,
        action: str,
        resource: str,
        user: str = "system",
        details: Optional[Dict[str, Any]] = None,
        verification_score: Optional[float] = None,
    ) -> AuditEntry:
        """
        Log an audit entry for an action.

        Args:
            action: Action being performed (e.g., "data_export", "query_wells")
            resource: Resource being accessed (e.g., "well_W001", "field_XYZ")
            user: User performing the action
            details: Additional details about the action
            verification_score: Optional data quality score

        Returns:
            Created audit entry
        """
        entry = AuditEntry(
            user=user,
            action=action,
            resource=resource,
            details=details or {},
            verification_score=verification_score,
        )

        # Add to memory buffer
        self.audit_entries.append(entry)

        # Write to file
        self._write_audit_to_file(entry)

        # Log to standard logger
        audit_logger.info(f"AUDIT: {action} on {resource} by {user}")

        return entry

    def audit_verification(
        self,
        well_id: str,
        quality_score: float,
        anomalies: List[str],
        user: str = "system",
    ) -> AuditEntry:
        """
        Log a verification audit entry.

        Args:
            well_id: Well being verified
            quality_score: Quality score from verification
            anomalies: List of detected anomalies
            user: User performing verification

        Returns:
            Created audit entry
        """
        details = {
            "quality_score": quality_score,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "passed": quality_score >= self.alert_thresholds["quality_score"],
        }

        return self.audit_action(
            action="data_verification",
            resource=f"well_{well_id}",
            user=user,
            details=details,
            verification_score=quality_score,
        )

    @contextmanager
    def track_performance(self, operation: str):
        """
        Context manager to track performance of an operation.

        Args:
            operation: Name of the operation being tracked

        Example:
            with monitor.track_performance("query_wells"):
                # Perform operation
                pass
        """
        start_time = time.time()

        try:
            yield
            status = "success"
        except Exception as e:
            status = "error"
            self.metrics.errors_count += 1
            logger.error(f"Error in {operation}: {e}")
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000

            # Update metrics
            self.metrics.query_count += 1
            self.metrics.total_query_time += duration_ms
            self.metrics.update_average_response_time()

            # Create audit entry
            self.audit_action(
                action=operation,
                resource="dashboard",
                details={"duration_ms": duration_ms, "status": status},
            )

            # Check for performance alerts
            if duration_ms > self.alert_thresholds["response_time_ms"]:
                self._trigger_alert(
                    "slow_response",
                    {"operation": operation, "duration_ms": duration_ms},
                )

    def track_cache_access(self, hit: bool):
        """
        Track cache hit/miss.

        Args:
            hit: True if cache hit, False if miss
        """
        if hit:
            self.metrics.cache_hits += 1
        else:
            self.metrics.cache_misses += 1

    def track_data_processing(self, data_points: int):
        """
        Track data points processed.

        Args:
            data_points: Number of data points processed
        """
        self.metrics.data_points_processed += data_points

    def detect_anomaly(self, metric_name: str, value: float) -> bool:
        """
        Detect if a metric value is anomalous.

        Args:
            metric_name: Name of the metric
            value: Current value of the metric

        Returns:
            True if anomaly detected
        """
        # Add to buffer
        self.anomaly_buffer[metric_name].append(value)

        # Keep only recent values
        if len(self.anomaly_buffer[metric_name]) > 100:
            self.anomaly_buffer[metric_name].pop(0)

        # Check if we have enough data
        if len(self.anomaly_buffer[metric_name]) < 10:
            return False

        # Calculate statistics
        values = self.anomaly_buffer[metric_name]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance**0.5

        # Check if current value is anomalous (> 3 std deviations)
        if std_dev > 0:
            z_score = abs(value - mean) / std_dev
            if z_score > 3:
                self._trigger_alert(
                    "anomaly_detected",
                    {
                        "metric": metric_name,
                        "value": value,
                        "mean": mean,
                        "std_dev": std_dev,
                        "z_score": z_score,
                    },
                )
                return True

        return False

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get current metrics summary.

        Returns:
            Dictionary with metrics summary
        """
        cache_hit_rate = 0
        if self.metrics.cache_hits + self.metrics.cache_misses > 0:
            cache_hit_rate = self.metrics.cache_hits / (
                self.metrics.cache_hits + self.metrics.cache_misses
            )

        error_rate = 0
        if self.metrics.query_count > 0:
            error_rate = self.metrics.errors_count / self.metrics.query_count

        return {
            "query_count": self.metrics.query_count,
            "avg_response_time_ms": self.metrics.avg_response_time,
            "cache_hit_rate": cache_hit_rate,
            "error_rate": error_rate,
            "data_points_processed": self.metrics.data_points_processed,
            "active_sessions": self.metrics.active_sessions,
            "peak_memory_mb": self.metrics.peak_memory_mb,
        }

    def get_audit_trail(
        self,
        resource: Optional[str] = None,
        user: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditEntry]:
        """
        Get audit trail with optional filters.

        Args:
            resource: Filter by resource
            user: Filter by user
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            List of matching audit entries
        """
        entries = list(self.audit_entries)

        if resource:
            entries = [e for e in entries if e.resource == resource]

        if user:
            entries = [e for e in entries if e.user == user]

        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]

        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]

        return entries

    def register_alert_callback(self, callback: Callable):
        """
        Register a callback for alerts.

        Args:
            callback: Function to call when alert is triggered
        """
        self.alert_callbacks.append(callback)

    def _trigger_alert(self, alert_type: str, details: Dict[str, Any]):
        """
        Trigger an alert.

        Args:
            alert_type: Type of alert
            details: Alert details
        """
        alert = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "details": details,
        }

        logger.warning(f"ALERT: {alert_type} - {details}")

        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def _write_audit_to_file(self, entry: AuditEntry):
        """Write audit entry to file"""
        try:
            with open(self.audit_file, "a") as f:
                f.write(entry.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit entry to file: {e}")

    def start_background_monitoring(self):
        """Start background monitoring thread"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return

        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(target=self._background_monitor)
        self._monitoring_thread.daemon = True
        self._monitoring_thread.start()
        logger.info("Background monitoring started")

    def stop_background_monitoring(self):
        """Stop background monitoring thread"""
        self._stop_monitoring.set()
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("Background monitoring stopped")

    def _background_monitor(self):
        """Background monitoring loop"""
        while not self._stop_monitoring.is_set():
            try:
                # Take metrics snapshot
                snapshot = asdict(self.metrics)
                snapshot["timestamp"] = datetime.now().isoformat()
                self.metrics_history.append(snapshot)

                # Check memory usage
                import psutil

                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.metrics.peak_memory_mb = max(
                    self.metrics.peak_memory_mb, memory_mb
                )

                if memory_mb > self.alert_thresholds["memory_mb"]:
                    self._trigger_alert("high_memory", {"memory_mb": memory_mb})

                # Check error rate
                if self.metrics.query_count > 100:  # Only check after 100 queries
                    error_rate = self.metrics.errors_count / self.metrics.query_count
                    if error_rate > self.alert_thresholds["error_rate"]:
                        self._trigger_alert(
                            "high_error_rate", {"error_rate": error_rate}
                        )

            except Exception as e:
                logger.error(f"Error in background monitoring: {e}")

            # Sleep for monitoring interval
            self._stop_monitoring.wait(self.config.get("monitoring_interval", 60))


def monitor_function(action: str = None):
    """
    Decorator to monitor function execution.

    Args:
        action: Optional action name (defaults to function name)

    Example:
        @monitor_function(action="export_data")
        def export_wells(well_ids):
            # Function implementation
            pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = kwargs.get("monitor")
            if not monitor:
                # Try to get monitor from first arg if it's a class instance
                if args and hasattr(args[0], "monitor"):
                    monitor = args[0].monitor

            if monitor and isinstance(monitor, DashboardMonitor):
                operation = action or func.__name__
                with monitor.track_performance(operation):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Export main classes
__all__ = ["AuditEntry", "PerformanceMetrics", "DashboardMonitor", "monitor_function"]
