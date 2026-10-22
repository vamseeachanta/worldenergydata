"""Synthetic schema examples for #1335, knowledge pack section 12.

Expected fields are enumerated from the declared input contract. No measured
quantities or numerical tolerance are used. Each frame contains one state and
one date unless stated otherwise; reshape cardinality is thus one times one.
"""

from datetime import datetime

import pandas as pd
import pytest

from worldenergydata.baker_hughes import loader


def read_frame(monkeypatch, frame):
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: frame.copy())


def pivot():
    return pd.DataFrame(
        {"PublishDate": ["2026-01-01"], "RigCount": [2], "Country": ["A"]}
    )


@pytest.mark.parametrize("column", ["PublishDate", "RigCount"])
def test_pivot_missing_required(monkeypatch, column):
    read_frame(monkeypatch, pivot().drop(columns=column))
    with pytest.raises(ValueError, match="missing_required"):
        loader.load_pivot_table("synthetic.xlsx")


def test_pivot_missing_optional_reported(monkeypatch):
    read_frame(monkeypatch, pivot())
    result = loader.load_pivot_table("synthetic.xlsx")
    assert result.attrs["schema"]["status"] == "incomplete"
    assert result.attrs["schema"]["missing_optional"] == [
        "StateProvince",
        "County",
        "BasinName",
        "DrillFor",
        "Location",
        "Trajectory",
        "WellType",
        "WellDepth",
        "WaterDepth",
    ]
    assert set(result.columns) == {"date", "rig_count", "country"}


def test_pivot_extra_rejected(monkeypatch):
    read_frame(monkeypatch, pivot().assign(Surprise="unexpected"))
    with pytest.raises(ValueError, match="unexpected"):
        loader.load_pivot_table("synthetic.xlsx")


@pytest.mark.parametrize("header", ["Other", "state", "StateProvince"])
def test_summary_wrong_identifier(monkeypatch, header):
    read_frame(monkeypatch, pd.DataFrame({header: ["X"], "2026-01-01": [2]}))
    with pytest.raises(ValueError, match="identifier"):
        loader.load_summary("synthetic.xlsx")


@pytest.mark.parametrize(
    "header", ["Total", "2026", "2026-01", 2026, None, "2026-02-30", "01/01/26"]
)
def test_summary_non_date_headers(monkeypatch, header):
    read_frame(monkeypatch, pd.DataFrame({"State": ["X"], header: [2]}))
    with pytest.raises(ValueError, match="invalid_date_headers"):
        loader.load_summary("synthetic.xlsx")


@pytest.mark.parametrize("header", ["2026-01-01", "1/1/2026", datetime(2026, 1, 1)])
def test_summary_date_header_selection(monkeypatch, header):
    """One state times one accepted date gives one record dated January 1."""
    read_frame(monkeypatch, pd.DataFrame({"State": ["X"], header: [2]}))
    result = loader.load_summary("synthetic.xlsx")
    assert result.to_dict("records") == [
        {"state": "X", "date": pd.Timestamp("2026-01-01"), "rig_count": 2}
    ]
    assert result.attrs["schema"]["status"] == "complete"


@pytest.mark.parametrize("frame", [pd.DataFrame(), pd.DataFrame({"State": ["X"]})])
def test_summary_missing_date_headers(monkeypatch, frame):
    read_frame(monkeypatch, frame)
    with pytest.raises(ValueError, match="missing_required"):
        loader.load_summary("synthetic.xlsx")


@pytest.mark.parametrize("summary", [False, True])
def test_duplicate_columns_rejected(monkeypatch, summary):
    frame = pd.DataFrame([["X", 2, 3]], columns=["State", "2026-01-01", "2026-01-01"])
    if not summary:
        frame.columns = ["PublishDate", "RigCount", "RigCount"]
    read_frame(monkeypatch, frame)
    with pytest.raises(ValueError, match="duplicate"):
        (loader.load_summary if summary else loader.load_pivot_table)("synthetic.xlsx")


def test_summary_equivalent_dates_rejected(monkeypatch):
    read_frame(
        monkeypatch, pd.DataFrame({"State": ["X"], "2026-01-01": [2], "1/1/2026": [3]})
    )
    with pytest.raises(ValueError, match="duplicate_dates"):
        loader.load_summary("synthetic.xlsx")
