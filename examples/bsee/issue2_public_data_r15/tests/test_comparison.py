"""Compare the displayed r12 groups even when fresh data reorders or adds rows."""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compare_r15 import compare_tables

BASE = ROOT.parent / "issue2_public_data_r12" / "data"


def test_comparison_matches_labels_and_preserves_unavailable_values(tmp_path):
    for path in BASE.glob("*.csv"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    (tmp_path / "record-counts.csv").write_text(
        "source,disposition,reason,records\nAPD,excluded,no_spud_date,12\n"
    )
    # Change a share and reorder the input rows; each metric belongs to its own group.
    name = "pies-rig.csv"
    pies = pd.read_csv(tmp_path / name)
    pick = (pies.year == 2005) & (pies.category == "Jack-up")
    pies.loc[pick, "share_percent"] += 1.5
    pies.iloc[::-1].to_csv(tmp_path / name, index=False, float_format="%.12g")
    cross = pd.read_csv(tmp_path / "subtype-activity.csv")
    cross = pd.concat([cross, pd.DataFrame([{
        "activity": "Completion", "primary": "COMP", "subtype": "New subtype", "submissions": 3
    }])])
    cross.to_csv(tmp_path / "subtype-activity.csv", index=False)

    diff = compare_tables(BASE, tmp_path).set_index(["table", "group", "metric"])
    assert diff.index.is_unique
    share = diff.loc[("pies-rig", "2005 | Jack-up", "share_percent")]
    assert share.difference == pytest.approx(1.5)
    assert share.difference_unit == "percentage points"
    assert diff.loc[("table1", "All", "New-well permits, 2005 to 2026 (-)"), "r12"] == 2895
    missing = diff.loc[("table1", "All", "Median water depth (m)")]
    assert pd.isna(missing.r12) and pd.isna(missing.difference)
    added = diff.loc[("subtype-activity", "Completion | COMP | New subtype", "submissions")]
    assert added.r15 == 3 and pd.isna(added.r12) and pd.isna(added.difference)
    headline = diff.loc["article"]
    assert headline.loc[("All years", "First permits without readable requested spud date"), "difference"] == 2
    assert headline.loc[("2005 to 2009", "New wells under 100 m (%)"), "r12"] == 68.8
    assert headline.loc[("2021 to 2025", "New wells in 500 m or more (%)"), "r12"] == 82.5
    assert headline.loc[("2005 to 2025", "First full year of sustained drillship majority"), "r12"] == 2015
    assert headline.loc[("2005 to 2025", "First full year of sustained 500 m or deeper majority"), "r12"] == 2015
    assert headline.loc[("2005 to 2025", "Changed repeat-key cell medians"), "r12"] == 12
    assert headline.loc[("2005 to 2025", "Largest absolute repeat-key median change (d)"), "r12"] == 11
