"""Date completeness regressions for issue #1335, cases F13 and F19.

Inputs are synthetic calendar dates, not source workbook measurements. Expected
counts are independently enumerated in each test; no engineering coefficients
or acceptance tolerances are used. The contract is documented in the module
knowledge pack, section 11 (2026-10-19).
"""

import json

import pandas as pd
import pytest

from worldenergydata.baker_hughes.report import generate_report


@pytest.mark.parametrize("source", ["pivot", "summary", "custom"])
def test_complete_dates_preserve_report_fields(source):
    """Two dates, neither missing: count 2, missing 0; Jan 1 precedes Jan 8."""
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-08", "2026-01-01"]),
            "basin": ["B", "A"],
            "state": ["Y", "X"],
            "country": ["Z", "Z"],
        }
    )
    original = df.copy(deep=True)

    report = generate_report(df, source)

    assert report == {
        "source": source,
        "record_count": 2,
        "date_range": {"min": "2026-01-01", "max": "2026-01-08"},
        "basins": ["A", "B"],
        "states": ["X", "Y"],
        "countries": ["Z"],
        "completeness": {
            "date_range": {"status": "complete", "reason": None, "missing_count": 0}
        },
    }
    pd.testing.assert_frame_equal(df, original)
    assert json.loads(json.dumps(report, allow_nan=False)) == report


@pytest.mark.parametrize("with_date_column", [False, True])
def test_empty_input_reports_incomplete_dates(with_date_column):
    """No rows: count 0; missing count is 0 if measurable, otherwise unknown."""
    df = pd.DataFrame()
    if with_date_column:
        df["date"] = pd.Series(dtype="datetime64[ns]")

    report = generate_report(df, "summary")

    assert report["record_count"] == 0
    assert "date_range" not in report
    assert report["completeness"]["date_range"] == {
        "status": "incomplete",
        "reason": "empty_input",
        "missing_count": 0 if with_date_column else None,
    }


@pytest.mark.parametrize("with_state_column", [False, True])
def test_missing_date_column_reports_unknown_missing_count(with_state_column):
    """One row without the date field: bounds and missing count are unknown."""
    df = pd.DataFrame(index=["record"])
    if with_state_column:
        df["state"] = ["X"]
    report = generate_report(df, "summary")

    assert report["record_count"] == 1
    if with_state_column:
        assert report["states"] == ["X"]
    assert "date_range" not in report
    assert report["completeness"]["date_range"] == {
        "status": "incomplete",
        "reason": "missing_date_column",
        "missing_count": None,
    }


@pytest.mark.parametrize("missing", [None, pd.NaT])
def test_partial_missing_dates_flag_observed_bounds(missing):
    """Three rows: Jan 8, missing, Jan 1; missing count 1, observed Jan 1–8."""
    df = pd.DataFrame({"date": pd.to_datetime(["2026-01-08", missing, "2026-01-01"])})

    report = generate_report(df, "pivot")

    assert report["record_count"] == 3
    assert report["date_range"] == {"min": "2026-01-01", "max": "2026-01-08"}
    assert report["completeness"]["date_range"] == {
        "status": "incomplete",
        "reason": "missing_dates",
        "missing_count": 1,
    }


def test_all_missing_dates_omit_bounds():
    """Two missing entries: missing count 2; no observed dates define bounds."""
    df = pd.DataFrame({"date": pd.to_datetime([None, pd.NaT])})

    report = generate_report(df, "pivot")

    assert report["record_count"] == 2
    assert "date_range" not in report
    assert report["completeness"]["date_range"] == {
        "status": "incomplete",
        "reason": "all_dates_missing",
        "missing_count": 2,
    }
    assert json.loads(json.dumps(report, allow_nan=False)) == report
