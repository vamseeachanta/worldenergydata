"""Tests for staleness detection with per-source cadence thresholds."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from worldenergydata.scheduler.staleness import (
    STALENESS_THRESHOLDS,
    check_staleness,
    get_staleness_details,
)

FROZEN_NOW = datetime(2026, 3, 25, 12, 0, 0)


def _make_status(jobs: dict) -> dict:
    """Helper to build a status dict matching StatusReporter.build_report() shape."""
    return {"jobs": jobs}


def _job_entry(start_time_iso: str | None, status: str = "success") -> dict:
    return {
        "status": status,
        "start_time": start_time_iso,
        "records_updated": 10,
        "error_msg": None,
    }


class TestCheckStaleness:
    """Tests for check_staleness function."""

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_all_within_threshold_returns_empty(self, mock_dt):
        """Test 1: check_staleness returns empty list when all jobs within thresholds."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        # SODIR ran 12 hours ago (threshold 36h) — OK
        # BSEE ran 5 days ago (threshold 10d) — OK
        # EIA ran 20 days ago (threshold 45d) — OK
        status = _make_status(
            {
                "sodir_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(hours=12)).isoformat()
                ),
                "bsee_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=5)).isoformat()
                ),
                "eia_us_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=20)).isoformat()
                ),
            }
        )
        result = check_staleness(status)
        assert result == []

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_sodir_stale_at_40_hours(self, mock_dt):
        """Test 2: SODIR stale when last_run is 40 hours ago (threshold 36h)."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        status = _make_status(
            {
                "sodir_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(hours=40)).isoformat()
                ),
                "bsee_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=1)).isoformat()
                ),
                "eia_us_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=1)).isoformat()
                ),
            }
        )
        result = check_staleness(status)
        assert result == ["sodir_refresh"]

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_bsee_stale_at_11_days(self, mock_dt):
        """Test 3: BSEE stale when last_run is 11 days ago (threshold 10d)."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        status = _make_status(
            {
                "sodir_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(hours=1)).isoformat()
                ),
                "bsee_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=11)).isoformat()
                ),
                "eia_us_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=1)).isoformat()
                ),
            }
        )
        result = check_staleness(status)
        assert result == ["bsee_refresh"]

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_eia_stale_at_50_days(self, mock_dt):
        """Test 4: EIA stale when last_run is 50 days ago (threshold 45d)."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        status = _make_status(
            {
                "sodir_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(hours=1)).isoformat()
                ),
                "bsee_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=1)).isoformat()
                ),
                "eia_us_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=50)).isoformat()
                ),
            }
        )
        result = check_staleness(status)
        assert result == ["eia_us_refresh"]

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_none_last_run_is_stale(self, mock_dt):
        """Test 5: Job with None last_run (never run) is always stale."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        status = _make_status(
            {
                "sodir_refresh": _job_entry(None),
                "bsee_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=1)).isoformat()
                ),
                "eia_us_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=1)).isoformat()
                ),
            }
        )
        result = check_staleness(status)
        assert result == ["sodir_refresh"]

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_ignores_untracked_jobs(self, mock_dt):
        """Test 6: Jobs not in STALENESS_THRESHOLDS are ignored (tier 2 sources)."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        # Only tracked jobs present, plus an untracked one
        status = _make_status(
            {
                "sodir_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(hours=1)).isoformat()
                ),
                "bsee_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=1)).isoformat()
                ),
                "eia_us_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=1)).isoformat()
                ),
                "brazil_anp_refresh": _job_entry(
                    None
                ),  # untracked, stale, but should be ignored
            }
        )
        result = check_staleness(status)
        assert result == []

    @patch("worldenergydata.scheduler.staleness.datetime")
    def test_get_staleness_details_returns_all_tracked(self, mock_dt):
        """Test 7: get_staleness_details returns dict for each tracked job."""
        mock_dt.now.return_value = FROZEN_NOW
        mock_dt.fromisoformat = datetime.fromisoformat

        status = _make_status(
            {
                "sodir_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(hours=40)).isoformat()
                ),
                "bsee_refresh": _job_entry(
                    (FROZEN_NOW - timedelta(days=1)).isoformat()
                ),
                "eia_us_refresh": _job_entry(None),
            }
        )
        details = get_staleness_details(status)
        assert len(details) == 3

        # Check structure
        for d in details:
            assert "job_name" in d
            assert "hours_since_last_run" in d
            assert "threshold_hours" in d
            assert "is_stale" in d

        # SODIR: 40h > 36h => stale
        sodir = next(d for d in details if d["job_name"] == "sodir_refresh")
        assert sodir["is_stale"] is True
        assert sodir["threshold_hours"] == 36.0
        assert sodir["hours_since_last_run"] == pytest.approx(40.0, abs=0.1)

        # BSEE: 1 day < 10 days => not stale
        bsee = next(d for d in details if d["job_name"] == "bsee_refresh")
        assert bsee["is_stale"] is False

        # EIA: None last_run => stale, hours_since is None
        eia = next(d for d in details if d["job_name"] == "eia_us_refresh")
        assert eia["is_stale"] is True
        assert eia["hours_since_last_run"] is None


class TestStalenessThresholds:
    """Verify threshold values match D-13 cadences."""

    def test_sodir_threshold_36_hours(self):
        assert STALENESS_THRESHOLDS["sodir_refresh"] == timedelta(hours=36)

    def test_bsee_threshold_10_days(self):
        assert STALENESS_THRESHOLDS["bsee_refresh"] == timedelta(days=10)

    def test_eia_threshold_45_days(self):
        assert STALENESS_THRESHOLDS["eia_us_refresh"] == timedelta(days=45)
