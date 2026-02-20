"""Tests for scheduler CLI: start | stop | status | run-job <name>."""
import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Use subprocess to invoke CLI as module
import subprocess
import sys


MINIMAL_CONFIG = """
jobs:
  - name: bsee_refresh
    interval: daily
    time: "02:00"
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


class TestCLIStatusCommand:
    def test_status_returns_dict(self, tmp_path):
        config_path = _write_config(tmp_path)
        from worldenergydata.scheduler.cli import cmd_status
        from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob

        result = cmd_status(config_path=config_path, jobs=[BseeRefreshJob()])
        assert isinstance(result, dict)
        assert "jobs" in result

    def test_status_no_jobs_shows_empty(self, tmp_path):
        config_path = _write_config(tmp_path)
        from worldenergydata.scheduler.cli import cmd_status

        result = cmd_status(config_path=config_path, jobs=[])
        assert isinstance(result, dict)


class TestCLIRunJobCommand:
    def test_run_job_executes_and_returns_result(self, tmp_path):
        config_path = _write_config(tmp_path)
        from worldenergydata.scheduler.cli import cmd_run_job
        from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob
        from worldenergydata.scheduler.jobs.base import JobResult

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


class TestCLIStopCommand:
    def test_stop_returns_confirmation(self, tmp_path):
        config_path = _write_config(tmp_path)
        from worldenergydata.scheduler.cli import cmd_stop

        # stop without running scheduler should return gracefully
        result = cmd_stop(config_path=config_path)
        assert result is not None
