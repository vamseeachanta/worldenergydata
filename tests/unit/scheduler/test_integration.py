"""Integration test: full scheduler cycle with mocked adapters.

Validates: job registration -> run_once -> status.json -> staleness -> alerting.
All external HTTP calls are mocked. This tests the wiring, not the data sources.

Note: D-04 symlink (data/modules/ -> /mnt/ace/worldenergydata/data/modules/)
is set up at deployment time, not during tests. Tests use tmp_path.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult
from worldenergydata.scheduler.scheduler import DataScheduler
from worldenergydata.scheduler.staleness import STALENESS_THRESHOLDS

FROZEN_NOW = datetime(2026, 3, 25, 12, 0, 0)


def _write_config(
    tmp_path: Path, jobs: list, monitoring_overrides: dict | None = None
) -> str:
    """Write a minimal scheduler config YAML to tmp_path and return its path."""
    monitoring = {
        "log_dir": str(tmp_path / "logs"),
        "status_file": str(tmp_path / "status.json"),
        "log_retention_days": 30,
        "retry_max": 1,
        "retry_backoff_seconds": 0,
    }
    if monitoring_overrides:
        monitoring.update(monitoring_overrides)

    config = {"jobs": jobs, "monitoring": monitoring}
    config_path = tmp_path / "scheduler_config.yml"
    config_path.write_text(yaml.dump(config), encoding="utf-8")
    return str(config_path)


class _SuccessJob(AbstractJob):
    """Mock job that always succeeds with configurable records count."""

    def __init__(self, name: str, records: int = 100):
        self.name = name
        self._records = records

    def run(self, config: dict) -> JobResult:
        now = datetime.now()
        return JobResult(
            job_name=self.name,
            start_time=now,
            end_time=now + timedelta(seconds=5),
            status="success",
            records_updated=self._records,
            error_msg=None,
        )


class _FailureJob(AbstractJob):
    """Mock job that always fails."""

    def __init__(self, name: str):
        self.name = name

    def run(self, config: dict) -> JobResult:
        now = datetime.now()
        return JobResult(
            job_name=self.name,
            start_time=now,
            end_time=now + timedelta(seconds=2),
            status="failure",
            records_updated=0,
            error_msg="Simulated failure for testing",
        )


class _SkippedJob(AbstractJob):
    """Mock Tier 2 stub job that returns skipped."""

    def __init__(self, name: str):
        self.name = name

    def run(self, config: dict) -> JobResult:
        now = datetime.now()
        return JobResult(
            job_name=self.name,
            start_time=now,
            end_time=now + timedelta(seconds=1),
            status="skipped",
            records_updated=0,
            error_msg=None,
        )


class TestFullCycleSuccess:
    """Test full scheduler cycle with all jobs succeeding."""

    def test_full_cycle_success(self, tmp_path):
        """Register EIA, BSEE, SODIR jobs. Run each. Verify status.json."""
        jobs_config = [
            {
                "name": "eia_us_refresh",
                "interval": "monthly",
                "time": "04:00",
                "enabled": True,
            },
            {
                "name": "bsee_refresh",
                "interval": "weekly",
                "time": "02:00",
                "enabled": True,
            },
            {
                "name": "sodir_refresh",
                "interval": "daily",
                "time": "03:00",
                "enabled": True,
            },
        ]
        config_path = _write_config(tmp_path, jobs_config)
        scheduler = DataScheduler(config_path)

        # Register mock jobs
        scheduler.register_job(_SuccessJob("eia_us_refresh", records=500))
        scheduler.register_job(_SuccessJob("bsee_refresh", records=1000))
        scheduler.register_job(_SuccessJob("sodir_refresh", records=200))

        # Run each job
        for job_name in ["eia_us_refresh", "bsee_refresh", "sodir_refresh"]:
            result = scheduler.run_once(job_name)
            assert result.status == "success"
            assert result.records_updated > 0

        # Verify status.json was written
        status_path = tmp_path / "status.json"
        assert status_path.exists(), "status.json should be written after run_once"

        status_data = json.loads(status_path.read_text(encoding="utf-8"))
        assert "jobs" in status_data

        # All 3 jobs should be in status.json (last run writes all)
        # Note: check_and_alert writes one result at a time per run_once call,
        # so the last call's status.json will have the sodir_refresh entry
        # The scheduler.status() method gives the enriched in-memory view
        enriched = scheduler.status()
        assert "staleness" in enriched
        assert "sodir_refresh" in enriched["staleness"]
        assert "bsee_refresh" in enriched["staleness"]
        assert "eia_us_refresh" in enriched["staleness"]

        # Each staleness entry should have threshold_hours
        for source in ["sodir_refresh", "bsee_refresh", "eia_us_refresh"]:
            assert "threshold_hours" in enriched["staleness"][source]


class TestFullCycleWithFailure:
    """Test cycle with one job failing — alerts should fire."""

    def test_full_cycle_with_failure(self, tmp_path):
        """One failed job triggers alert, others succeed."""
        jobs_config = [
            {
                "name": "eia_us_refresh",
                "interval": "monthly",
                "time": "04:00",
                "enabled": True,
            },
            {
                "name": "bsee_refresh",
                "interval": "weekly",
                "time": "02:00",
                "enabled": True,
            },
            {
                "name": "sodir_refresh",
                "interval": "daily",
                "time": "03:00",
                "enabled": True,
            },
        ]
        config_path = _write_config(tmp_path, jobs_config)
        scheduler = DataScheduler(config_path)

        # Register: EIA succeeds, BSEE fails, SODIR succeeds
        scheduler.register_job(_SuccessJob("eia_us_refresh", records=500))
        scheduler.register_job(_FailureJob("bsee_refresh"))
        scheduler.register_job(_SuccessJob("sodir_refresh", records=200))

        # Mock the alert sender to capture calls
        scheduler._alert_sender.send_alert = MagicMock()

        # Run all jobs
        scheduler.run_once("eia_us_refresh")
        scheduler.run_once("bsee_refresh")
        scheduler.run_once("sodir_refresh")

        # Verify alert was sent for BSEE failure
        alert_calls = scheduler._alert_sender.send_alert.call_args_list
        failure_alerts = [
            c for c in alert_calls if "FAILED" in str(c) and "bsee_refresh" in str(c)
        ]
        assert (
            len(failure_alerts) >= 1
        ), f"Expected at least one failure alert for bsee_refresh, got: {alert_calls}"

        # Verify enriched status shows correct results
        enriched = scheduler.status()
        jobs_status = enriched["jobs"]
        assert jobs_status["eia_us_refresh"]["last_result"] == "success"
        assert jobs_status["bsee_refresh"]["last_result"] == "failure"
        assert jobs_status["sodir_refresh"]["last_result"] == "success"


class TestStalenessDetection:
    """Test staleness detection through scheduler.status()."""

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_staleness_detection(self, mock_dt, tmp_path):
        """Old timestamps make sources stale in enriched status."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        jobs_config = [
            {
                "name": "sodir_refresh",
                "interval": "daily",
                "time": "03:00",
                "enabled": True,
            },
            {
                "name": "bsee_refresh",
                "interval": "weekly",
                "time": "02:00",
                "enabled": True,
            },
        ]
        config_path = _write_config(tmp_path, jobs_config)
        scheduler = DataScheduler(config_path)

        scheduler.register_job(_SuccessJob("sodir_refresh", records=100))
        scheduler.register_job(_SuccessJob("bsee_refresh", records=200))

        # Manually set stale timestamps in job state
        # SODIR: 40 hours ago (threshold 36h) — should be stale
        scheduler._job_state["sodir_refresh"]["last_run"] = (
            FROZEN_NOW - timedelta(hours=40)
        ).isoformat()
        scheduler._job_state["sodir_refresh"]["last_result"] = "success"

        # BSEE: 5 days ago (threshold 10d) — should NOT be stale
        scheduler._job_state["bsee_refresh"]["last_run"] = (
            FROZEN_NOW - timedelta(days=5)
        ).isoformat()
        scheduler._job_state["bsee_refresh"]["last_result"] = "success"

        enriched = scheduler.status()

        assert enriched["staleness"]["sodir_refresh"]["is_stale"] is True
        assert enriched["staleness"]["bsee_refresh"]["is_stale"] is False


class TestTier2StubsSkip:
    """Test Tier 2 stubs return skipped and do not trigger alerts."""

    def test_tier2_stubs_skip(self, tmp_path):
        """Tier 2 jobs return skipped, no alerts fired."""
        jobs_config = [
            {
                "name": "brazil_anp_refresh",
                "interval": "monthly",
                "time": "05:00",
                "enabled": True,
            },
            {
                "name": "metocean_refresh",
                "interval": "daily",
                "time": "01:00",
                "enabled": True,
            },
        ]
        config_path = _write_config(tmp_path, jobs_config)
        scheduler = DataScheduler(config_path)

        scheduler.register_job(_SkippedJob("brazil_anp_refresh"))
        scheduler.register_job(_SkippedJob("metocean_refresh"))

        # Mock alert sender
        scheduler._alert_sender.send_alert = MagicMock()

        result_anp = scheduler.run_once("brazil_anp_refresh")
        result_met = scheduler.run_once("metocean_refresh")

        # Both should be skipped
        assert result_anp.status == "skipped"
        assert result_met.status == "skipped"

        # No failure alerts should have been sent (skipped != failure)
        failure_alerts = [
            c
            for c in scheduler._alert_sender.send_alert.call_args_list
            if "FAILED" in str(c)
        ]
        assert (
            len(failure_alerts) == 0
        ), f"No failure alerts expected for skipped jobs, got: {failure_alerts}"
