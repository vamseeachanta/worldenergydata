"""Diagnostics count affected synthetic rows without changing the day basis."""

import pandas as pd
import pytest
from test_production_defects import load_reference


def test_b6_blank_post_td_is_diagnostic_only():
    """Two post-TD rows, one with text: one affected row; no day inference."""
    extractor = load_reference("extract_drilling_completion_days")
    war = pd.DataFrame(
        {
            "SN_WAR": [1, 2, 3],
            "API_WELL_NUMBER": ["101"] * 3,
            "WAR_END_DT": pd.to_datetime(["2025-01-02", "2025-01-04", "2025-01-05"]),
        }
    )
    bore = pd.DataFrame(
        {"API_WELL_NUMBER": ["101"], "TOTAL_DEPTH_DATE": pd.to_datetime(["2025-01-03"])}
    )
    remarks = pd.DataFrame({"SN_WAR": [1, 2, 3], "TEXT_REMARK": ["", "  ", "activity"]})
    result = extractor.diagnose_blank_post_td(war, bore, remarks)
    assert result == {"status": "NOT_EVALUATED", "post_td_blank_remark_rows": 1}


def test_b12_diagnostic_rejects_ambiguous_bore_dates():
    extractor = load_reference("extract_drilling_completion_days")
    war = pd.DataFrame(
        {
            "SN_WAR": [1],
            "API_WELL_NUMBER": ["101"],
            "WAR_END_DT": pd.to_datetime(["2025-01-04"]),
        }
    )
    bore = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["101", "101"],
            "TOTAL_DEPTH_DATE": pd.to_datetime(["2025-01-02", "2025-01-03"]),
        }
    )
    remarks = pd.DataFrame({"SN_WAR": [], "TEXT_REMARK": []})
    with pytest.raises(pd.errors.MergeError):
        extractor.diagnose_blank_post_td(war, bore, remarks)


def test_b6_null_source_remark_is_blank(tmp_path):
    extractor = load_reference("extract_drilling_completion_days")
    path = tmp_path / "remarks.bin"
    pd.DataFrame({"SN_WAR": [1], "TEXT_REMARK": [None]}).to_pickle(path)
    result = extractor.load_remarks(path)
    assert result["TEXT_REMARK"].tolist() == [""]
