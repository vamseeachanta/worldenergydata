"""Tests for WTI prices helper functions."""

import pandas as pd
import pytest

from worldenergydata.lower_tertiary.wti_prices import (
    V30_LAST_MONTH,
    V30_LAST_PRICE,
    _append,
    _covered_periods,
    _needed_months,
    get_wti_source_summary,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_v30_last_price(self):
        assert V30_LAST_PRICE == 68.39

    def test_v30_last_month(self):
        assert V30_LAST_MONTH == pd.Timestamp("2025-07-01")


# ---------------------------------------------------------------------------
# _covered_periods
# ---------------------------------------------------------------------------


class TestCoveredPeriods:
    def test_none(self):
        assert _covered_periods(None) == set()

    def test_empty(self):
        df = pd.DataFrame({"Month": pd.DatetimeIndex([])})
        assert _covered_periods(df) == set()

    def test_basic(self):
        df = pd.DataFrame({"Month": pd.to_datetime(["2025-08-01", "2025-09-01"])})
        result = _covered_periods(df)
        assert len(result) == 2
        assert pd.Period("2025-08", "M") in result
        assert pd.Period("2025-09", "M") in result


# ---------------------------------------------------------------------------
# _needed_months
# ---------------------------------------------------------------------------


class TestNeededMonths:
    def test_basic(self):
        result = _needed_months(pd.Timestamp("2025-07-01"), pd.Timestamp("2025-10-01"))
        assert len(result) == 3
        assert result[0] == pd.Timestamp("2025-08-01")
        assert result[1] == pd.Timestamp("2025-09-01")
        assert result[2] == pd.Timestamp("2025-10-01")

    def test_same_month(self):
        result = _needed_months(pd.Timestamp("2025-07-01"), pd.Timestamp("2025-07-01"))
        assert len(result) == 0

    def test_single_month(self):
        result = _needed_months(pd.Timestamp("2025-07-01"), pd.Timestamp("2025-08-01"))
        assert len(result) == 1
        assert result[0] == pd.Timestamp("2025-08-01")


# ---------------------------------------------------------------------------
# _append
# ---------------------------------------------------------------------------


class TestAppend:
    def test_none_base(self):
        new = pd.DataFrame({"a": [1, 2]})
        result = _append(None, new)
        assert len(result) == 2

    def test_with_base(self):
        base = pd.DataFrame({"a": [1]})
        new = pd.DataFrame({"a": [2, 3]})
        result = _append(base, new)
        assert len(result) == 3

    def test_reset_index(self):
        base = pd.DataFrame({"a": [1]}, index=[5])
        new = pd.DataFrame({"a": [2]}, index=[10])
        result = _append(base, new)
        assert list(result.index) == [0, 1]


# ---------------------------------------------------------------------------
# get_wti_source_summary
# ---------------------------------------------------------------------------


class TestGetWtiSourceSummary:
    def test_all_sources(self):
        df = pd.DataFrame(
            {
                "source": [
                    "v30_xlsx",
                    "v30_xlsx",
                    "eia_github",
                    "fred_api",
                    "flat_forward",
                    "flat_forward",
                ],
            }
        )
        result = get_wti_source_summary(df)
        assert result["v30_xlsx"] == 2
        assert result["eia_github"] == 1
        assert result["fred_api"] == 1
        assert result["flat_forward"] == 2

    def test_missing_sources_zero(self):
        df = pd.DataFrame({"source": ["v30_xlsx"]})
        result = get_wti_source_summary(df)
        assert result["eia_github"] == 0
        assert result["fred_api"] == 0
        assert result["flat_forward"] == 0

    def test_includes_all_keys(self):
        df = pd.DataFrame({"source": []})
        result = get_wti_source_summary(df)
        assert set(result.keys()) == {
            "v30_xlsx",
            "eia_github",
            "fred_api",
            "flat_forward",
        }
