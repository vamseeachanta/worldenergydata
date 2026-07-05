"""Tests for DataScheduler: registration, start/stop, status, run_once."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import yaml

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult
from worldenergydata.scheduler.scheduler import DataScheduler

MINIMAL_CONFIG = """
jobs:
  - name: mock_job
    interval: daily
    time: "02:00"
    enabled: true
    output_dir: {mock_output_dir}
  - name: disabled_job
    interval: daily
    time: "03:00"
    enabled: false
    output_dir: {disabled_output_dir}

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
    last_config = None

    def run(self, config: dict) -> JobResult:
        MockJob.call_count += 1
        MockJob.last_config = dict(config)
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


class FakeSpainCoresJob(AbstractJob):
    name = "spain_cores_refresh"
    default_output_dir = Path("data/spain/cores")
    last_config = None

    def run(self, config: dict) -> JobResult:
        FakeSpainCoresJob.last_config = dict(config)
        output_dir = Path(config["_scheduler_repo_root"]) / config["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "_metadata.json").write_text(
            json.dumps({"module": "spain_cores", "record_count": 2}) + "\n",
            encoding="utf-8",
        )
        (output_dir / "metadata").mkdir()
        (output_dir / "metadata" / "cores_refresh_metadata.json").write_text(
            json.dumps({"statistics_page": "https://www.cores.es/en/estadisticas"})
            + "\n",
            encoding="utf-8",
        )
        (output_dir / "normalized").mkdir()
        (output_dir / "normalized" / "cores_all_production.csv").write_text(
            "field_name,year,month,oil_bbl,gas_mcf\nAyoluengo,2026,1,1.0,2.0\n",
            encoding="utf-8",
        )
        return JobResult(
            job_name=self.name,
            start_time=datetime.now(),
            end_time=datetime.now(),
            status="success",
            records_updated=2,
            error_msg=None,
        )


def _write_config(tmp_path) -> str:
    log_dir = str(tmp_path / "logs")
    status_file = str(tmp_path / "status.json")
    content = MINIMAL_CONFIG.format(
        log_dir=log_dir,
        status_file=status_file,
        mock_output_dir=str(tmp_path / "data" / "mock_job"),
        disabled_output_dir=str(tmp_path / "data" / "disabled_job"),
    )
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
        MockJob.last_config = None
        FakeSpainCoresJob.last_config = None

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

    def test_run_once_success_writes_scheduler_manifest(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(MockJob())

        result = scheduler.run_once("mock_job")

        manifest_path = tmp_path / "data" / "mock_job" / "manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["job_name"] == "mock_job"
        assert manifest["status"] == "success"
        assert manifest["records_updated"] == result.records_updated
        assert manifest["refresh_interval_days"] == 1
        assert manifest["last_success_ts"]

    def test_run_once_skipped_job_does_not_write_success_manifest(self, tmp_path):
        config_path = _write_config(tmp_path)
        scheduler = DataScheduler(config_path=config_path)
        scheduler.register_job(DisabledJob())

        scheduler.run_once("disabled_job")

        manifest_path = tmp_path / "data" / "disabled_job" / "manifest.json"
        assert not manifest_path.exists()

    def test_run_once_relative_output_dir_resolves_from_config_dir(self, tmp_path):
        config_dir = tmp_path / "config" / "scheduler"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "scheduler_config.yml"
        config_path.write_text(
            MINIMAL_CONFIG.format(
                log_dir=str(tmp_path / "logs"),
                status_file=str(tmp_path / "status.json"),
                mock_output_dir="data/modules/mock_job",
                disabled_output_dir="data/modules/disabled_job",
            )
        )
        scheduler = DataScheduler(config_path=str(config_path))
        scheduler.register_job(MockJob())

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path.parent)
            scheduler.run_once("mock_job")
        finally:
            os.chdir(original_cwd)

        manifest_path = tmp_path / "data" / "modules" / "mock_job" / "manifest.json"
        assert manifest_path.exists()

    def test_run_once_passes_scheduler_repo_root_to_job_config(self, tmp_path):
        config_dir = tmp_path / "config" / "scheduler"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "scheduler_config.yml"
        config_path.write_text(
            MINIMAL_CONFIG.format(
                log_dir=str(tmp_path / "logs"),
                status_file=str(tmp_path / "status.json"),
                mock_output_dir="data/modules/mock_job",
                disabled_output_dir="data/modules/disabled_job",
            )
        )
        scheduler = DataScheduler(config_path=str(config_path))
        scheduler.register_job(MockJob())

        scheduler.run_once("mock_job")

        assert MockJob.last_config["_scheduler_repo_root"] == str(tmp_path)
        assert (
            "_scheduler_repo_root"
            not in scheduler._config.get_job_config("mock_job")
        )

    def test_run_once_spain_cores_writes_outputs_and_manifest_under_one_root(
        self, tmp_path
    ):
        config_dir = tmp_path / "config" / "scheduler"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "scheduler_config.yml"
        config_path.write_text(
            """
jobs:
  - name: spain_cores_refresh
    interval: monthly
    time: "08:00"
    enabled: true
    output_dir: data/spain/cores
    refresh_fixture: false

monitoring:
  log_dir: {log_dir}
  log_retention_days: 30
  retry_max: 3
  retry_backoff_seconds: 0
  webhook_url: null
  status_file: {status_file}
""".format(
                log_dir=str(tmp_path / "logs"),
                status_file=str(tmp_path / "status.json"),
            )
        )
        scheduler = DataScheduler(config_path=str(config_path))
        scheduler.register_job(FakeSpainCoresJob())

        result = scheduler.run_once("spain_cores_refresh")

        output_dir = tmp_path / "data" / "spain" / "cores"
        assert result.status == "success"
        assert FakeSpainCoresJob.last_config["_scheduler_repo_root"] == str(tmp_path)
        assert (output_dir / "_metadata.json").exists()
        assert (output_dir / "metadata" / "cores_refresh_metadata.json").exists()
        assert (output_dir / "normalized" / "cores_all_production.csv").exists()
        assert (output_dir / "manifest.json").exists()


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
