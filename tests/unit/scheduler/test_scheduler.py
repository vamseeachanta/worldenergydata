"""Tests for DataScheduler: registration, start/stop, status, run_once."""
import pytest
import tempfile
import os
import yaml
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call
from pathlib import Path

from worldenergydata.scheduler.jobs.base import JobResult, AbstractJob
from worldenergydata.scheduler.scheduler import DataScheduler


MINIMAL_CONFIG = """
jobs:
  - name: mock_job
    interval: daily
    time: "02:00"
    enabled: true
  - name: disabled_job
    interval: daily
    time: "03:00"
    enabled: false

monitoring:
  log_dir: {log_dir}
  log_retention_days: 30
  retry_max: 3
  retry_backoff_seconds: 0
  webhook_url: null
  status_file: {status_file}
"""


class MockJob(AbstractJob):
    name = "mock_job"
    call_count = 0

    def run(self, config: dict) -> JobResult:
        MockJob.call_count += 1
        return JobResult(
            job_name=self.name,
            start_time=datetime.now(),
            end_time=datetime.now(),
            status="success",
            records_updated=1,
            error_msg=None,
        )


class DisabledJob(AbstractJob):
    name = "disabled_job"

    def run(self, config: dict) -> JobResult:
        return JobResult(
            job_name=self.name,
            start_time=datetime.now(),
            end_time=datetime.now(),
            status="success",
            records_updated=0,
            error_msg=None,
        )


def _write_config(tmp_path) -> str:
    log_dir = str(tmp_path / "logs")
    status_file = str(tmp_path / "status.json")
    content = MINIMAL_CONFIG.format(log_dir=log_dir, status_file=status_file)
    config_file = tmp_path / "scheduler_config.yml"
    config_file.write_text(content)
    return str(config_file)


class TestDataSchedulerRegistration:
    def test_register_job(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        job = MockJob()
        scheduler.register_job(job)
        assert "mock_job" in scheduler._jobs

    def test_register_multiple_jobs(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(MockJob())
        scheduler.register_job(DisabledJob())
        assert len(scheduler._jobs) == 2

    def test_register_duplicate_job_raises(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(MockJob())
        with pytest.raises(ValueError, match="already registered"):
            scheduler.register_job(MockJob())

    def test_initial_status_empty(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        status = scheduler.status()
        assert isinstance(status, dict)
        assert "jobs" in status


class TestDataSchedulerRunOnce:
    def setup_method(self):
        MockJob.call_count = 0

    def test_run_once_executes_job(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(MockJob())
        scheduler.run_once("mock_job")
        assert MockJob.call_count == 1

    def test_run_once_updates_status(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(MockJob())
        scheduler.run_once("mock_job")
        status = scheduler.status()
        assert "mock_job" in status["jobs"]
        assert status["jobs"]["mock_job"]["last_result"] == "success"

    def test_run_once_unknown_job_raises(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        with pytest.raises(ValueError, match="not registered"):
            scheduler.run_once("nonexistent_job")

    def test_run_once_records_last_run_time(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(MockJob())
        before = datetime.now()
        scheduler.run_once("mock_job")
        after = datetime.now()
        last_run = scheduler.status()["jobs"]["mock_job"]["last_run"]
        assert last_run is not None
        last_run_dt = datetime.fromisoformat(last_run)
        assert before <= last_run_dt <= after

    def test_run_once_disabled_job_is_skipped(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(DisabledJob())
        result = scheduler.run_once("disabled_job")
        assert result.status == "skipped"


class TestDataSchedulerStatus:
    def setup_method(self):
        MockJob.call_count = 0

    def test_status_before_any_run(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(MockJob())
        status = scheduler.status()
        assert status["jobs"]["mock_job"]["last_run"] is None
        assert status["jobs"]["mock_job"]["last_result"] is None

    def test_status_contains_next_run(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(MockJob())
        status = scheduler.status()
        assert "next_run" in status["jobs"]["mock_job"]

    def test_status_all_jobs_listed(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(MockJob())
        scheduler.register_job(DisabledJob())
        status = scheduler.status()
        assert "mock_job" in status["jobs"]
        assert "disabled_job" in status["jobs"]


class TestDataSchedulerStartStop:
    def test_stop_sets_running_false(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler._running = True
        scheduler.stop()
        assert scheduler._running is False

    def test_is_running_initially_false(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        assert scheduler._running is False

    def test_start_sets_running_true_until_stopped(self, tmp_path):
        """start() blocks; test that _running is set by using threading."""
        import threading

        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(MockJob())

        def stop_after_start():
            import time
            time.sleep(0.05)
            scheduler.stop()

        t = threading.Thread(target=stop_after_start)
        t.start()
        scheduler.start(tick_interval=0.01)  # fast tick for test
        t.join()
        assert scheduler._running is False
