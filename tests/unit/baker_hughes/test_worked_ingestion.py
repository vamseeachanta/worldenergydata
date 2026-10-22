"""Hand calculation for docs/examples/baker-hughes-ingestion.md.

Two rows dated January 1 and January 8 contain counts 2 and 3. County is the
only omitted optional header. Selecting country A keeps both rows; selecting
Z keeps none. Observed bounds are January 1–8, but the omitted County header
keeps schema completeness incomplete. These are enumerated synthetic inputs,
not empirical constants or qualified source counts (#1335, pack section 12).
"""

import pandas as pd

from worldenergydata.baker_hughes.loader import load_pivot_table, load_summary
from worldenergydata.baker_hughes.report import generate_report


def test_worked_ingestion(tmp_path):
    frame = pd.DataFrame(
        {
            "PublishDate": ["2026-01-01", "2026-01-08"],
            "RigCount": [2, 3],
            "Country": ["A", "A"],
            "StateProvince": ["X", "Y"],
            "BasinName": ["B", "B"],
            "DrillFor": ["Gas", "Gas"],
            "Location": ["Land", "Land"],
            "Trajectory": ["Vertical", "Vertical"],
            "WellType": ["Development", "Development"],
            "WellDepth": [None, None],
            "WaterDepth": [None, None],
        }
    )
    path = tmp_path / "synthetic.xlsx"
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    result = load_pivot_table(path, country="A")
    assert result["rig_count"].tolist() == [2, 3]
    assert result.attrs["schema"]["missing_optional"] == ["County"]
    report = generate_report(result, "pivot")
    assert report["record_count"] == 2
    assert report["date_range"] == {"min": "2026-01-01", "max": "2026-01-08"}
    assert report["completeness"]["status"] == "incomplete"
    assert report["completeness"]["omitted_fields"] == []
    unmatched = load_pivot_table(path, country="Z")
    assert unmatched.attrs["ingestion"]["status"] == "no_match"
    report = generate_report(unmatched, "pivot")
    assert report["record_count"] == 0
    assert report["completeness"]["omitted_fields"] == ["date_range"]
    assert report["completeness"]["date_range"]["bounds_status"] == "undefined"


def test_pivot_missing_dates_survive_to_report(tmp_path):
    """One missing date out of two remains visible; January 1 is sole bound."""
    path = tmp_path / "dates.xlsx"
    pd.DataFrame({"PublishDate": ["2026-01-01", None], "RigCount": [2, 3]}).to_excel(
        path,
        sheet_name="Pivot Table",
        index=False,
    )
    report = generate_report(load_pivot_table(path), "pivot")
    assert report["completeness"]["date_range"]["missing_count"] == 1
    assert report["completeness"]["date_range"]["reason"] == "missing_dates"
    assert report["date_range"] == {"min": "2026-01-01", "max": "2026-01-01"}


def test_empty_summary_status(tmp_path):
    """Zero state rows times one date header gives zero melted rows."""
    path = tmp_path / "summary.xlsx"
    pd.DataFrame(columns=["State", "2026-01-01"]).to_excel(
        path, sheet_name="Rigs by State", index=False
    )
    result = load_summary(path)
    assert result.empty
    assert result.attrs["ingestion"]["status"] == "empty_input"
    assert generate_report(result, "summary")["completeness"]["status"] == "incomplete"
