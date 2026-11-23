"""Report completeness checks on synthetic records, independent of source accuracy."""

import json

import pandas as pd
import pytest

from worldenergydata.baker_hughes.report import generate_report

DIMENSIONS = [("basin", "basins"), ("state", "states"), ("country", "countries")]


def complete_frame():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-08", "2026-01-01"]),
            "basin": ["B", "A"],
            "state": ["Y", "X"],
            "country": ["Z", "Z"],
        }
    )


@pytest.mark.parametrize("column,output", DIMENSIONS)
def test_absent_dimension_has_unknown_missing_count(column, output):
    report = generate_report(complete_frame().drop(columns=column), "pivot")
    assert output not in report
    assert report["completeness"]["dimensions"][output] == {
        "status": "incomplete",
        "reason": "missing_dimension_column",
        "missing_count": None,
    }
    assert report["completeness"]["status"] == "incomplete"


@pytest.mark.parametrize("column,output", DIMENSIONS)
@pytest.mark.parametrize("missing", [None, pd.NA, float("nan"), "", "  "])
@pytest.mark.parametrize("all_missing", [False, True])
def test_null_dimension_values_are_counted(column, output, missing, all_missing):
    frame = complete_frame()
    frame[column] = [missing, missing] if all_missing else ["A", missing]
    original = frame.copy(deep=True)
    report = generate_report(frame, "pivot")
    assert report[output] == ([] if all_missing else ["A"])
    assert report["completeness"]["dimensions"][output] == {
        "status": "incomplete",
        "reason": "all_values_missing" if all_missing else "missing_values",
        "missing_count": 2 if all_missing else 1,
    }
    assert report["completeness"]["status"] == "incomplete"
    assert json.loads(json.dumps(report, allow_nan=False)) == report
    pd.testing.assert_frame_equal(frame, original)


def test_summary_absent_pivot_dimensions_are_not_applicable():
    frame = complete_frame().drop(columns=["basin", "country"])
    report = generate_report(frame, "summary")
    assert report["completeness"]["status"] == "complete"
    for output in ("basins", "countries"):
        assert output not in report
        assert report["completeness"]["dimensions"][output] == {
            "status": "not_applicable",
            "reason": "not_in_summary_schema",
            "missing_count": None,
        }
    assert report["completeness"]["schema"] == {
        "status": "not_evaluated",
        "reason": "loader_metadata_unavailable",
    }


def test_summary_still_requires_state_dimension():
    report = generate_report(complete_frame().drop(columns="state"), "summary")
    assert report["completeness"]["status"] == "incomplete"
    assert (
        report["completeness"]["dimensions"]["states"]["reason"]
        == "missing_dimension_column"
    )


def test_literal_na_is_a_dimension_value():
    frame = complete_frame()
    frame["state"] = ["NA", "X"]
    report = generate_report(frame, "pivot")
    assert report["states"] == ["NA", "X"]
    assert report["completeness"]["dimensions"]["states"]["status"] == "complete"


def test_empty_dimension_inventory_is_explicitly_incomplete():
    report = generate_report(complete_frame().iloc[:0], "pivot")
    assert report["completeness"]["status"] == "incomplete"
    for _, output in DIMENSIONS:
        assert report[output] == []
        assert report["completeness"]["dimensions"][output] == {
            "status": "incomplete",
            "reason": "empty_input",
            "missing_count": 0,
        }


@pytest.mark.parametrize("dates", [["2026-01-01"], ["bad"], [42]])
def test_unparsed_dates_raise_descriptive_error(dates):
    with pytest.raises(ValueError, match="date.*parsed"):
        generate_report(pd.DataFrame({"date": dates}), "pivot")
