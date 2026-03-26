"""Tests for status enricher and scheduler alerting integration."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from worldenergydata.scheduler.staleness import STALENESS_THRESHOLDS


FROZEN_NOW = datetime(2026, 3, 25, 12, 0, 0)


def _make_status(jobs: dict) -> dict:
    """Build a status dict matching StatusReporter.build_report() shape."""
    return {"jobs": jobs}


def _job_entry(start_time: datetime | None, status: str = "success") -> dict:
    return {
        "status": status,
        "start_time": start_time.isoformat() if start_time else None,
        "end_time": (start_time + timedelta(minutes=5)).isoformat() if start_time else None,
        "records_updated": 10,
        "error_msg": None,
    }


class TestEnrichStatus:
    """Tests for the enrich_status function."""

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_adds_staleness_key(self, mock_dt):
        """Test 1: enrich_status adds 'staleness' key to status dict."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        from worldenergydata.scheduler.status_enricher import enrich_status

        status = _make_status({
            "sodir_refresh": _job_entry(FROZEN_NOW - timedelta(hours=12)),
            "bsee_refresh": _job_entry(FROZEN_NOW - timedelta(days=5)),
            "eia_us_refresh": _job_entry(FROZEN_NOW - timedelta(days=20)),
        })
        result = enrich_status(status)
        assert "staleness" in result
        # Should have per-source details
        assert "sodir_refresh" in result["staleness"]
        assert "bsee_refresh" in result["staleness"]
        assert "eia_us_refresh" in result["staleness"]

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_staleness_entry_has_required_keys(self, mock_dt):
        """Test 2: staleness entry has threshold_hours, is_stale, hours_since_last_success."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        from worldenergydata.scheduler.status_enricher import enrich_status

        status = _make_status({
            "sodir_refresh": _job_entry(FROZEN_NOW - timedelta(hours=40)),
            "bsee_refresh": _job_entry(FROZEN_NOW - timedelta(days=1)),
            "eia_us_refresh": _job_entry(FROZEN_NOW - timedelta(days=1)),
        })
        result = enrich_status(status)
        sodir = result["staleness"]["sodir_refresh"]
        assert "threshold_hours" in sodir
        assert "is_stale" in sodir
        assert "hours_since_last_success" in sodir
        # SODIR at 40h > 36h threshold should be stale
        assert sodir["is_stale"] is True
        assert sodir["threshold_hours"] == 36.0

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_adds_alerts_key_empty_when_no_alerts(self, mock_dt):
        """Test 3: enrich_status adds 'alerts' key as empty list when no alerts."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        from worldenergydata.scheduler.status_enricher import enrich_status

        status = _make_status({
            "sodir_refresh": _job_entry(FROZEN_NOW - timedelta(hours=12)),
        })
        result = enrich_status(status)
        assert "alerts" in result
        assert result["alerts"] == []

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_scheduler_run_once_calls_check_and_alert(self, mock_dt):
        """Test 4: DataScheduler.run_once calls check_and_alert after job execution."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        import tempfile
        import os

        import yaml

        from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

        # Create minimal config in temp dir
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "config.yml")
            config = {
                "jobs": [
                    {"name": "test_job", "interval": "daily", "time": "00:00", "enabled": True}
                ],
                "monitoring": {
                    "log_dir": os.path.join(tmp, "logs"),
                    "status_file": os.path.join(tmp, "status.json"),
                },
            }
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            from worldenergydata.scheduler.scheduler import DataScheduler

            scheduler = DataScheduler(config_path)

            # Mock check_and_alert on the status reporter
            scheduler._status_reporter.check_and_alert = MagicMock()

            # Create and register a mock job
            class MockJob(AbstractJob):
                name = "test_job"

                def run(self, config: dict) -> JobResult:
                    now = datetime.now()
                    return JobResult(
                        job_name="test_job",
                        start_time=now,
                        end_time=now,
                        status="success",
                        records_updated=5,
                        error_msg=None,
                    )

            scheduler.register_job(MockJob())
            scheduler.run_once("test_job")

            # Verify check_and_alert was called
            scheduler._status_reporter.check_and_alert.assert_called_once()
            call_args = scheduler._status_reporter.check_and_alert.call_args
            # First arg should be list of results
            assert len(call_args[0][0]) == 1
            assert call_args[0][0][0].job_name == "test_job"
