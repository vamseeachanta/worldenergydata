"""Tests for scheduler CLI: start | stop | status | run-job <name>."""

from datetime import datetime
from unittest.mock import patch

import pytest

MINIMAL_CONFIG = """
jobs:
  - name: bsee_refresh
    interval: daily
    time: "02:00"
    enabled: true
  - name: lng_terminals_refresh
    interval: weekly
    time: "07:00"
    enabled: true

monitoring:
  log_dir: {log_dir}
  log_retention_days: 30
  retry_max: 3
  retry_backoff_seconds: 0
  webhook_url: null
  status_file: {status_file}
"""


def _write_config(tmp_path) -> str:
    log_dir = str(tmp_path / "logs")
    status_file = str(tmp_path / "status.json")
    content = MINIMAL_CONFIG.format(log_dir=log_dir, status_file=status_file)
    config_file = tmp_path / "scheduler_config.yml"
    config_file.write_text(content)
    return str(config_file)


class TestCLIImports:
    def test_cli_module_importable(self):
        from worldenergydata.scheduler import cli

        assert cli is not None

    def test_cli_has_main_entry_point(self):
        from worldenergydata.scheduler.cli import main

        assert callable(main)

    def test_cli_has_status_command(self):
        from worldenergydata.scheduler.cli import cmd_status

        assert callable(cmd_status)

    def test_cli_has_run_job_command(self):
        from worldenergydata.scheduler.cli import cmd_run_job

        assert callable(cmd_run_job)

    def test_cli_has_stop_command(self):
        from worldenergydata.scheduler.cli import cmd_stop

        assert callable(cmd_stop)

    def test_cli_all_jobs_includes_lng_terminals_job(self):
        from worldenergydata.scheduler.cli import ALL_JOBS

        names = [job.name for job in ALL_JOBS]
        assert "lng_terminals_refresh" in names
        assert "spain_cores_refresh" in names


class TestCLIStatusCommand:
    def test_status_default_job_registry_includes_lng_terminals(self, tmp_path):
        config_path = _write_config(tmp_path)
        from worldenergydata.scheduler.cli import cmd_status

        result = cmd_status(config_path=config_path)

        assert "lng_terminals_refresh" in result["jobs"]

    def test_status_returns_dict(self, tmp_path):
        config_path = _write_config(tmp_path)
        from worldenergydata.scheduler.cli import cmd_status
        from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob
        from worldenergydata.scheduler.jobs.lng_terminals_refresh import (
            LngTerminalsRefreshJob,
        )

        result = cmd_status(
            config_path=config_path,
            jobs=[BseeRefreshJob(), LngTerminalsRefreshJob()],
        )
        assert isinstance(result, dict)
        assert "jobs" in result
        assert "lng_terminals_refresh" in result["jobs"]

    def test_status_no_jobs_shows_empty(self, tmp_path):
        config_path = _write_config(tmp_path)
        from worldenergydata.scheduler.cli import cmd_status

        result = cmd_status(config_path=config_path, jobs=[])
        assert isinstance(result, dict)


class TestCLIRunJobCommand:
    def test_run_job_executes_and_returns_result(self, tmp_path):
        config_path = _write_config(tmp_path)
        from worldenergydata.scheduler.cli import cmd_run_job
        from worldenergydata.scheduler.jobs.base import JobResult
        from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob

        result = cmd_run_job(
            job_name="bsee_refresh",
            config_path=config_path,
            jobs=[BseeRefreshJob()],
        )
        assert isinstance(result, JobResult)

    def test_run_job_unknown_name_raises(self, tmp_path):
        config_path = _write_config(tmp_path)
        from worldenergydata.scheduler.cli import cmd_run_job
        from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob

        with pytest.raises(ValueError):
            cmd_run_job(
                job_name="nonexistent_job",
                config_path=config_path,
                jobs=[BseeRefreshJob()],
            )

    def test_run_job_default_registry_loads_spain_cores_job(self, tmp_path):
        config_path = tmp_path / "scheduler_config.yml"
        config_path.write_text(
            """
jobs:
  - name: spain_cores_refresh
    interval: monthly
    time: "08:00"
    enabled: true
    output_dir: data/spain/cores

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
        from worldenergydata.scheduler import cli
        from worldenergydata.scheduler.jobs.base import JobResult

        class _FakeSpainJob:
            name = "spain_cores_refresh"

            def run(self, config):
                return JobResult(
                    job_name=self.name,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    status="success",
                    records_updated=2,
                    error_msg=None,
                )

        def fake_load_job_class(class_path):
            assert (
                class_path
                == "worldenergydata.scheduler.jobs.spain_cores_refresh.SpainCoresRefreshJob"
            )
            return _FakeSpainJob

        with patch.object(cli, "_load_job_class", side_effect=fake_load_job_class):
            result = cli.cmd_run_job(
                job_name="spain_cores_refresh",
                config_path=str(config_path),
            )

        assert result.status == "success"
        assert result.records_updated == 2


class TestCLIStopCommand:
    def test_stop_returns_confirmation(self, tmp_path):
        config_path = _write_config(tmp_path)
        from worldenergydata.scheduler.cli import cmd_stop

        # stop without running scheduler should return gracefully
        result = cmd_stop(config_path=config_path)
        assert result is not None
