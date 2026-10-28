"""Tests for staleness detection with per-source cadence thresholds."""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from worldenergydata.scheduler.staleness import (
    STALENESS_THRESHOLDS,
    check_staleness,
    get_staleness_details,
)
from worldenergydata.scheduler.status_enricher import enrich_status

FROZEN_NOW = datetime(2026, 3, 25, 12, 0, 0)


@pytest.fixture
def synthetic_utc_cadence(monkeypatch):
    """Synthetic example: noon UTC on the existing fixture date, six-hour cadence.

    All expected hours below are hand calculations from these fixed instants,
    independent of the production thresholds and elapsed-time implementation.
    """
    instant = FROZEN_NOW.replace(tzinfo=timezone.utc)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return instant.astimezone().replace(tzinfo=None)
            return instant.astimezone(tz)

    monkeypatch.setattr("worldenergydata.scheduler.staleness.datetime", FrozenDatetime)
    monkeypatch.setattr(
        "worldenergydata.scheduler.staleness.STALENESS_THRESHOLDS",
        {"synthetic_refresh": timedelta(hours=6)},
    )


@pytest.mark.parametrize(
    "consumer", [check_staleness, get_staleness_details, enrich_status]
)
@pytest.mark.parametrize("offset_index", [0, 1, 2])  # The three encodings below.
@pytest.mark.parametrize(
    "timestamps, expected_hours, expected_stale",
    [
        # Noon minus 07:00 UTC = five hours; +05:30 and -07:00 preserve that instant.
        (
            [
                "2026-03-25T07:00:00+00:00",
                "2026-03-25T12:30:00+05:30",
                "2026-03-25T00:00:00-07:00",
            ],
            5.0,
            False,
        ),
        # Noon minus 05:00 UTC = seven hours; the negative offset crosses midnight.
        (
            [
                "2026-03-25T05:00:00+00:00",
                "2026-03-25T10:30:00+05:30",
                "2026-03-24T22:00:00-07:00",
            ],
            7.0,
            True,
        ),
    ],
)
def test_staleness_equivalent_offset_instants(
    synthetic_utc_cadence,
    consumer,
    offset_index,
    timestamps,
    expected_hours,
    expected_stale,
):
    """Equivalent UTC and offset strings give identical ages and stale flags."""
    results = []
    for timestamp in [timestamps[offset_index], timestamps[0]]:
        status = _make_status({"synthetic_refresh": _job_entry(timestamp)})
        result = consumer(status)
        results.append(result)
        if consumer is check_staleness:
            assert result == (["synthetic_refresh"] if expected_stale else [])
        elif consumer is get_staleness_details:
            (detail,) = result
            assert detail["is_stale"] is expected_stale
            assert detail["hours_since_last_run"] == expected_hours
        else:
            detail = result["staleness"]["synthetic_refresh"]
            assert detail["is_stale"] is expected_stale
            assert detail["hours_since_last_success"] == expected_hours
    # Enrichment preserves the original timestamp in jobs; compare derived fields.
    if consumer is enrich_status:
        results = [result["staleness"] for result in results]
    assert all(result == results[0] for result in results)


def _assert_synthetic_staleness(status, expected_hours, expected_stale):
    """Assert all consumers agree for the fixture's synthetic six-hour cadence."""
    assert check_staleness(status) == (["synthetic_refresh"] if expected_stale else [])
    (detail,) = get_staleness_details(status)
    assert detail["job_name"] == "synthetic_refresh"
    assert detail["threshold_hours"] == 6.0
    assert detail["is_stale"] is expected_stale
    if expected_hours is None:
        assert detail["hours_since_last_run"] is None
    else:
        assert detail["hours_since_last_run"] == pytest.approx(expected_hours)
    assert enrich_status(status)["staleness"]["synthetic_refresh"] == {
        "threshold_hours": detail["threshold_hours"],
        "is_stale": detail["is_stale"],
        "hours_since_last_success": detail["hours_since_last_run"],
    }


@pytest.mark.parametrize("timestamp_key", ["start_time", "last_run"])
@pytest.mark.parametrize(
    "timestamp, expected_hours, expected_stale",
    [
        # Hand calculation: noon UTC minus 07:00/05:00 UTC = five/seven hours.
        ("2026-03-25T07:00:00", 5.0, False),
        ("2026-03-25T05:00:00", 7.0, True),
    ],
)
def test_legacy_naive_status_is_utc_without_tzset(
    synthetic_utc_cadence,
    monkeypatch,
    timestamp_key,
    timestamp,
    expected_hours,
    expected_stale,
):
    """Both legacy timestamp keys mean UTC even when timezone control is absent."""
    monkeypatch.delattr(time, "tzset", raising=False)
    entry = _job_entry(None)
    entry[timestamp_key] = timestamp
    status = _make_status({"synthetic_refresh": entry})
    _assert_synthetic_staleness(status, expected_hours, expected_stale)


@pytest.mark.skipif(
    not hasattr(time, "tzset"), reason="Requires POSIX timezone control"
)
@pytest.mark.parametrize("local_zone", ["UTC0", "EST5"])
@pytest.mark.parametrize("timestamp_key", ["start_time", "last_run"])
@pytest.mark.parametrize(
    "timestamp, expected_hours, expected_stale",
    [
        # Hand calculation: noon UTC minus 07:00/05:00 UTC = five/seven hours.
        ("2026-03-25T07:00:00", 5.0, False),
        ("2026-03-25T05:00:00", 7.0, True),
    ],
)
def test_legacy_naive_status_is_utc(
    synthetic_utc_cadence,
    monkeypatch,
    local_zone,
    timestamp_key,
    timestamp,
    expected_hours,
    expected_stale,
):
    """Legacy timestamps mean UTC, including under a UTC-minus-five local clock."""
    with monkeypatch.context() as context:
        context.setenv("TZ", local_zone)
        time.tzset()
        try:
            entry = _job_entry(None)
            entry[timestamp_key] = timestamp
            status = _make_status({"synthetic_refresh": entry})
            _assert_synthetic_staleness(status, expected_hours, expected_stale)
        finally:
            # Restore the environment before resetting the process timezone.
            context.undo()
            time.tzset()


@pytest.mark.parametrize(
    "timestamps, expected_hours, expected_stale",
    [
        # Noon minus 06:00 UTC = exactly six hours: equality is not stale.
        (
            [
                "2026-03-25T06:00:00",
                "2026-03-25T06:00:00+00:00",
                "2026-03-25T11:30:00+05:30",
                "2026-03-24T23:00:00-07:00",
            ],
            6.0,
            False,
        ),
        # One minute inside: 5 h 59 min = (5 * 60 + 59) / 60 hours.
        (
            [
                "2026-03-25T06:01:00",
                "2026-03-25T06:01:00+00:00",
                "2026-03-25T11:31:00+05:30",
                "2026-03-24T23:01:00-07:00",
            ],
            359 / 60,
            False,
        ),
        # One minute outside: 6 h 1 min = (6 * 60 + 1) / 60 hours.
        (
            [
                "2026-03-25T05:59:00",
                "2026-03-25T05:59:00+00:00",
                "2026-03-25T11:29:00+05:30",
                "2026-03-24T22:59:00-07:00",
            ],
            361 / 60,
            True,
        ),
    ],
)
def test_staleness_threshold_boundary(
    synthetic_utc_cadence, timestamps, expected_hours, expected_stale
):
    """Hand-calculated boundary cases preserve the strict greater-than rule."""
    for timestamp in timestamps:
        status = _make_status({"synthetic_refresh": _job_entry(timestamp)})
        _assert_synthetic_staleness(status, expected_hours, expected_stale)


@pytest.mark.parametrize(
    "entry",
    [
        {},
        {"start_time": None},
        {"start_time": ""},
        {"start_time": "invalid"},
        {"start_time": 42},  # Synthetic integer sentinel, not an ISO timestamp.
    ],
)
def test_missing_or_invalid_timestamp_is_stale_with_unknown_age(
    synthetic_utc_cadence, entry
):
    """Missing values and synthetic malformed strings/types retain unknown ages."""
    status = _make_status({"synthetic_refresh": entry, "untracked_refresh": entry})
    _assert_synthetic_staleness(status, None, True)


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
                "hse_refresh": _job_entry((FROZEN_NOW - timedelta(days=5)).isoformat()),
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
                "hse_refresh": _job_entry((FROZEN_NOW - timedelta(days=5)).isoformat()),
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
                "hse_refresh": _job_entry((FROZEN_NOW - timedelta(days=5)).isoformat()),
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
                "hse_refresh": _job_entry((FROZEN_NOW - timedelta(days=5)).isoformat()),
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
                "hse_refresh": _job_entry((FROZEN_NOW - timedelta(days=5)).isoformat()),
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
                "hse_refresh": _job_entry((FROZEN_NOW - timedelta(days=5)).isoformat()),
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
                "hse_refresh": _job_entry((FROZEN_NOW - timedelta(days=5)).isoformat()),
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
        assert len(details) == 4  # sodir, bsee, hse, eia

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

    def test_hse_threshold_10_days(self):
        assert STALENESS_THRESHOLDS["hse_refresh"] == timedelta(days=10)

    def test_eia_threshold_45_days(self):
        assert STALENESS_THRESHOLDS["eia_us_refresh"] == timedelta(days=45)
