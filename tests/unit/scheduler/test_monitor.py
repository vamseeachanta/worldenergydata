"""Tests for scheduler monitor: JobLogger, RetryManager, StatusReporter, webhook."""
import json
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from worldenergydata.scheduler.jobs.base import JobResult
from worldenergydata.scheduler.monitor import (
    JobLogger,
    RetryManager,
    StatusReporter,
)


def make_result(name="bsee_refresh", status="success", records=10, error=None):
    now = datetime.now()
    return JobResult(
        job_name=name,
        start_time=now,
        end_time=now + timedelta(seconds=2),
        status=status,
        records_updated=records,
        error_msg=error,
    )


class TestJobLogger:
    def test_log_result_creates_file(self, tmp_path):
        logger = JobLogger(log_dir=str(tmp_path), retention_days=30)
        result = make_result()
        logger.log_result(result)
        log_files = list(tmp_path.glob("*.json"))
        assert len(log_files) == 1

    def test_log_result_json_structure(self, tmp_path):
        logger = JobLogger(log_dir=str(tmp_path), retention_days=30)
        result = make_result(name="sodir_refresh", status="success", records=42)
        logger.log_result(result)
        log_files = list(tmp_path.glob("*.json"))
        with open(log_files[0]) as f:
            data = json.load(f)
        assert data["job_name"] == "sodir_refresh"
        assert data["status"] == "success"
        assert data["records_updated"] == 42
        assert "start_time" in data
        assert "end_time" in data

    def test_log_result_failure_includes_error(self, tmp_path):
        logger = JobLogger(log_dir=str(tmp_path), retention_days=30)
        result = make_result(status="failure", error="Network error")
        logger.log_result(result)
        log_files = list(tmp_path.glob("*.json"))
        with open(log_files[0]) as f:
            data = json.load(f)
        assert data["status"] == "failure"
        assert data["error_msg"] == "Network error"

    def test_multiple_log_results(self, tmp_path):
        logger = JobLogger(log_dir=str(tmp_path), retention_days=30)
        logger.log_result(make_result("job_a"))
        logger.log_result(make_result("job_b"))
        log_files = list(tmp_path.glob("*.json"))
        assert len(log_files) == 2

    def test_log_dir_created_if_missing(self, tmp_path):
        new_dir = tmp_path / "new_logs"
        logger = JobLogger(log_dir=str(new_dir), retention_days=30)
        logger.log_result(make_result())
        assert new_dir.exists()

    def test_old_logs_purged_on_rotate(self, tmp_path):
        """Logs older than retention_days should be removed."""
        import time

        logger = JobLogger(log_dir=str(tmp_path), retention_days=1)
        # Create an old log file manually (2 days old)
        old_file = tmp_path / "old_log_20240101_000000_bsee.json"
        old_file.write_text('{"job_name": "old"}')
        old_time = (datetime.now() - timedelta(days=2)).timestamp()
        os.utime(str(old_file), (old_time, old_time))

        logger.rotate_logs()
        assert not old_file.exists()

    def test_recent_logs_not_purged(self, tmp_path):
        """Logs within retention_days should NOT be removed."""
        logger = JobLogger(log_dir=str(tmp_path), retention_days=30)
        recent_file = tmp_path / "recent_log.json"
        recent_file.write_text('{"job_name": "recent"}')

        logger.rotate_logs()
        assert recent_file.exists()


class TestRetryManager:
    def test_retry_success_first_attempt(self):
        call_count = 0

        def job_fn():
            nonlocal call_count
            call_count += 1
            return make_result(status="success")

        manager = RetryManager(max_retries=3, backoff_seconds=0)
        result = manager.run_with_retry(job_fn)
        assert result.status == "success"
        assert call_count == 1

    def test_retry_success_on_second_attempt(self):
        call_count = 0

        def job_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return make_result(status="failure", error="Transient error")
            return make_result(status="success")

        manager = RetryManager(max_retries=3, backoff_seconds=0)
        result = manager.run_with_retry(job_fn)
        assert result.status == "success"
        assert call_count == 2

    def test_retry_exhausted_returns_failure(self):
        call_count = 0

        def job_fn():
            nonlocal call_count
            call_count += 1
            return make_result(status="failure", error="Persistent error")

        manager = RetryManager(max_retries=3, backoff_seconds=0)
        result = manager.run_with_retry(job_fn)
        assert result.status == "failure"
        assert call_count == 3

    def test_retry_exception_is_caught(self):
        call_count = 0

        def job_fn():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Unexpected crash")

        manager = RetryManager(max_retries=2, backoff_seconds=0)
        result = manager.run_with_retry(job_fn)
        assert result.status == "failure"
        assert "Unexpected crash" in result.error_msg
        assert call_count == 2

    def test_retry_uses_exponential_backoff(self):
        """Backoff doubles: 60s -> 120s -> 240s."""
        manager = RetryManager(max_retries=3, backoff_seconds=60)
        delays = [manager.backoff_delay(attempt) for attempt in range(3)]
        assert delays == [60, 120, 240]

    def test_retry_zero_max_retries_runs_once(self):
        call_count = 0

        def job_fn():
            nonlocal call_count
            call_count += 1
            return make_result(status="failure")

        manager = RetryManager(max_retries=0, backoff_seconds=0)
        result = manager.run_with_retry(job_fn)
        assert call_count == 1


class TestStatusReporter:
    def test_status_report_all_success(self, tmp_path):
        results = [
            make_result("bsee_refresh", "success"),
            make_result("sodir_refresh", "success"),
        ]
        reporter = StatusReporter(status_file=str(tmp_path / "status.json"))
        report = reporter.build_report(results)
        assert report["total_jobs"] == 2
        assert report["success_count"] == 2
        assert report["failure_count"] == 0

    def test_status_report_mixed(self, tmp_path):
        results = [
            make_result("bsee_refresh", "success"),
            make_result("sodir_refresh", "failure", error="Timeout"),
            make_result("eia_us_refresh", "skipped"),
        ]
        reporter = StatusReporter(status_file=str(tmp_path / "status.json"))
        report = reporter.build_report(results)
        assert report["total_jobs"] == 3
        assert report["success_count"] == 1
        assert report["failure_count"] == 1
        assert report["skipped_count"] == 1

    def test_status_report_writes_json_file(self, tmp_path):
        results = [make_result("bsee_refresh", "success")]
        reporter = StatusReporter(status_file=str(tmp_path / "status.json"))
        reporter.write_status(results)
        status_file = tmp_path / "status.json"
        assert status_file.exists()
        data = json.loads(status_file.read_text())
        assert "total_jobs" in data
        assert "generated_at" in data

    def test_status_report_per_job_details(self, tmp_path):
        results = [make_result("bsee_refresh", "success", records=99)]
        reporter = StatusReporter(status_file=str(tmp_path / "status.json"))
        report = reporter.build_report(results)
        assert "jobs" in report
        job_detail = report["jobs"]["bsee_refresh"]
        assert job_detail["status"] == "success"
        assert job_detail["records_updated"] == 99

    def test_webhook_post_called_when_configured(self, tmp_path):
        results = [make_result("bsee_refresh", "success")]
        reporter = StatusReporter(
            status_file=str(tmp_path / "status.json"),
            webhook_url="http://example.com/hook",
        )
        with patch("worldenergydata.scheduler.monitor.requests") as mock_requests:
            mock_requests.post.return_value = MagicMock(status_code=200)
            reporter.write_status(results)
            mock_requests.post.assert_called_once()
            call_url = mock_requests.post.call_args[0][0]
            assert call_url == "http://example.com/hook"

    def test_webhook_not_called_when_not_configured(self, tmp_path):
        results = [make_result("bsee_refresh", "success")]
        reporter = StatusReporter(status_file=str(tmp_path / "status.json"))
        with patch("worldenergydata.scheduler.monitor.requests") as mock_requests:
            reporter.write_status(results)
            mock_requests.post.assert_not_called()

    def test_webhook_failure_does_not_raise(self, tmp_path):
        """Webhook errors should not crash the reporter."""
        results = [make_result("bsee_refresh", "success")]
        reporter = StatusReporter(
            status_file=str(tmp_path / "status.json"),
            webhook_url="http://bad.example.com/hook",
        )
        with patch("worldenergydata.scheduler.monitor.requests") as mock_requests:
            mock_requests.post.side_effect = Exception("Connection refused")
            # Should NOT raise
            reporter.write_status(results)
