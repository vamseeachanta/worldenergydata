"""Filter and completeness hand checks for #1335, pack section 12.

Synthetic dates and dimensions are explicitly enumerated, with no source
workbook qualification or engineering acceptance limits.
"""

import json

import pandas as pd
import pytest

from worldenergydata.baker_hughes.loader import load_pivot_table
from worldenergydata.baker_hughes.report import generate_report


@pytest.mark.parametrize(
    "dimension,header", [("country", "Country"), ("basin", "BasinName")]
)
def test_unmatched_filter(monkeypatch, dimension, header):
    """One A and one null cannot equal B: zero matches, one null source value."""
    frame = pd.DataFrame(
        {"PublishDate": ["2026-01-01"] * 2, "RigCount": [2, 3], header: ["A", None]}
    )
    monkeypatch.setattr(pd, "read_excel", lambda *a, **kw: frame.copy())
    result = load_pivot_table("synthetic.xlsx", **{dimension: "B"})
    assert result.empty
    assert result.attrs["ingestion"]["status"] == "no_match"
    assert result.attrs["ingestion"]["filters"] == {dimension: "B"}
    assert result.attrs["ingestion"]["null_dimensions"][dimension] == 1
    assert (
        generate_report(result, "pivot")["completeness"]["ingestion"]["status"]
        == "no_match"
    )


@pytest.mark.parametrize("dimension", ["country", "basin"])
def test_filter_absent_dimension(monkeypatch, dimension):
    frame = pd.DataFrame({"PublishDate": ["2026-01-01"], "RigCount": [2]})
    monkeypatch.setattr(pd, "read_excel", lambda *a, **kw: frame.copy())
    with pytest.raises(ValueError, match="absent_dimension"):
        load_pivot_table("synthetic.xlsx", **{dimension: "A"})


def test_empty_input_status(monkeypatch):
    """A schema-valid frame with no rows is empty input, not a failed match."""
    frame = pd.DataFrame(columns=["PublishDate", "RigCount", "Country"])
    monkeypatch.setattr(pd, "read_excel", lambda *a, **kw: frame.copy())
    result = load_pivot_table("synthetic.xlsx", country="A")
    assert result.attrs["ingestion"]["status"] == "empty_input"


def test_matched_filter_status(monkeypatch):
    frame = pd.DataFrame(
        {"PublishDate": ["2026-01-01"], "RigCount": [2], "Country": ["A"]}
    )
    monkeypatch.setattr(pd, "read_excel", lambda *a, **kw: frame.copy())
    assert (
        load_pivot_table("synthetic.xlsx", country="A").attrs["ingestion"]["status"]
        == "matched"
    )


@pytest.mark.parametrize("dimension", ["basin", "state", "country"])
@pytest.mark.parametrize("absent", [False, True])
def test_dimension_completeness(dimension, absent):
    """An absent dimension is unknown; one null among two rows is missing 1."""
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-01-08"]),
            "basin": ["A", "B"],
            "state": ["X", "Y"],
            "country": ["C", "C"],
        }
    )
    if absent:
        df = df.drop(columns=dimension)
    else:
        df.loc[0, dimension] = None
    report = generate_report(df, "pivot")
    completeness = report["completeness"]
    assert completeness["status"] == "incomplete"
    assert completeness["dimensions"][dimension] == {
        "status": "undefined" if absent else "incomplete",
        "reason": "missing_column" if absent else "missing_values",
        "missing_count": None if absent else 1,
    }
    field = {"basin": "basins", "state": "states", "country": "countries"}[dimension]
    assert (field in completeness["omitted_fields"]) == absent
    assert json.loads(json.dumps(report, allow_nan=False)) == report


def test_undefined_bounds():
    """Two missing dates give no bounds, no NaT strings, and undefined bounds."""
    report = generate_report(
        pd.DataFrame({"date": pd.to_datetime([None, None])}), "pivot"
    )
    assert report["completeness"]["date_range"]["bounds_status"] == "undefined"
    assert "date_range" in report["completeness"]["omitted_fields"]
    assert "NaT" not in json.dumps(report)


def test_complete_report():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01"]),
            "basin": ["A"],
            "state": ["X"],
            "country": ["C"],
        }
    )
    assert generate_report(df, "pivot")["completeness"]["status"] == "complete"


def test_schema_missing_optional_makes_report_incomplete():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01"]),
            "basin": ["A"],
            "state": ["X"],
            "country": ["C"],
        }
    )
    df.attrs["schema"] = {"status": "incomplete", "missing_optional": ["County"]}
    report = generate_report(df, "pivot")
    assert report["completeness"]["status"] == "incomplete"
    assert report["completeness"]["schema"] == df.attrs["schema"]


def test_summary_dimensions_explicitly_omitted():
    """Summary observes only state; two other inventories remain undefined."""
    df = pd.DataFrame({"date": pd.to_datetime(["2026-01-01"]), "state": ["X"]})
    report = generate_report(df, "summary")
    assert report["completeness"]["omitted_fields"] == ["basins", "countries"]
    assert report["completeness"]["status"] == "incomplete"
