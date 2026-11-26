"""Compare the displayed r12 groups even when fresh data reorders or adds rows."""

import sys
from shutil import copytree
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compare_r15 import compare_tables, majority_start

BASE = ROOT.parent / "issue2_public_data_r12" / "data"
DATA = ROOT / "data"


def test_committed_comparison_recomputes_from_both_revisions():
    comparison = compare_tables(BASE, DATA)
    encoded = comparison.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode("utf-8")
    assert encoded == (DATA / "r12-vs-r15.csv").read_bytes()


def test_published_headlines_are_unchanged():
    cells = pd.read_csv(DATA / "r12-vs-r15.csv").set_index(["table", "group", "metric"], verify_integrity=True)
    # Named r12 readings in the README, PR, article and figure notes (value at printed precision).
    headlines = [
        ("table1", "All", "New-well permits, 2005 to 2026 (-)", 2895),
        ("fig-p1-new-well-permits-by-rig-type", "2026", "total", 47),
        ("pies-rig", "2025 | Drillship", "share_percent", 93.6),
        ("article", "All years", "First permits without readable requested spud date", 10),
        ("article", "2005 to 2025", "New wells started", 2913),
        ("article", "2005 to 2009", "New wells under 100 m (%)", 68.8),
        ("article", "2005 to 2009", "New wells in 500 m or more (%)", 23.3),
        ("article", "2021 to 2025", "New wells under 100 m (%)", 13.4),
        ("article", "2021 to 2025", "New wells in 500 m or more (%)", 82.5),
        ("article", "2012 to 2014", "New wells/year under 100 m (figure note)", 62.0),
        ("article", "2012 to 2014", "New wells/year under 100 m (rounded in text)", 62),
        ("article", "2012 to 2014", "New wells/year in 500 m or more (figure note)", 75.7),
        ("article", "2012 to 2014", "New wells/year in 500 m or more (rounded in text)", 76),
        ("article", "2015 to 2017", "New wells/year under 100 m (figure note)", 12.3),
        ("article", "2015 to 2017", "New wells/year under 100 m (rounded in text)", 12),
        ("article", "2015 to 2017", "New wells/year in 500 m or more (figure note)", 59.3),
        ("article", "2015 to 2017", "New wells/year in 500 m or more (rounded in text)", 59),
        ("article", "2005 to 2025", "First full year of sustained drillship majority", 2015),
        ("article", "2005 to 2025", "First full year of sustained 500 m or deeper majority", 2015),
        ("article", "2005 to 2025", "Comparable repeat-key cell medians", 16),
        ("article", "2005 to 2025", "Changed repeat-key cell medians", 12),
        ("article", "2005 to 2025", "Largest absolute repeat-key median change (d)", 11),
    ]
    for table, group, metric, published in headlines:
        row = cells.loc[(table, group, metric)]
        assert row.difference == 0, (table, group, metric, row.to_dict())
        value = round(row.r15, 1) if metric == "share_percent" else row.r15
        assert value == published, (table, group, metric)


def test_only_seven_input_and_exclusion_counts_changed():
    """Permit counts, rig/depth shares, map aggregates and duration statistics retain every available r12 value."""
    cells = pd.read_csv(DATA / "r12-vs-r15.csv").set_index(["table", "group", "metric"], verify_integrity=True)
    # Unavailable statistics must stay unavailable on both sides.
    pd.testing.assert_series_equal(cells.r12.isna(), cells.r15.isna(), check_names=False)
    pd.testing.assert_series_equal(cells.r12.isna(), cells.difference.isna(), check_names=False)
    available = cells.difference.dropna()
    assert available[available.ne(0)].to_dict() == {
        ("exclusions", "APM | raw_records", "records"): 137,
        ("exclusions", "APM | outside_years", "records"): 137,
        ("exclusions", "Borehole | raw_records", "records"): 5,
        ("exclusions", "Borehole | non_gulf", "records"): 1,
        ("exclusions", "Borehole | non_original", "records"): 4,
        ("exclusions", "Borehole | missing_spud_date", "records"): -1,
        ("exclusions", "Borehole | outside_years", "records"): 1,
    }


def test_partial_2026_majority_does_not_count():
    totals = pd.Series([10, 10], index=[2025, 2026])
    assert majority_start(pd.Series([5, 9], index=totals.index), totals) is None


def test_trend_article_cells_follow_changed_three_year_means(tmp_path):
    fresh = copytree(DATA, tmp_path / "fresh")
    path = fresh / "new-wells-trend.csv"
    trend = pd.read_csv(path).set_index("year")
    columns = ["Under 100 m (3-year mean)", "500 to 1,500 m (3-year mean)", "1,500 m and deeper (3-year mean)"]
    trend.loc[2014, columns] = [50.67, 20.12, 11.22]
    trend.loc[2017, columns] = [19.24, 35.31, 12.47]
    trend.to_csv(path)
    article = compare_tables(BASE, fresh).set_index(["table", "group", "metric"]).loc["article"]
    for period, band, figure, text in [
        ("2012 to 2014", "under 100 m", 50.7, 51),
        ("2012 to 2014", "in 500 m or more", 31.3, 31),
        ("2015 to 2017", "under 100 m", 19.2, 19),
        ("2015 to 2017", "in 500 m or more", 47.8, 48),
    ]:
        assert article.loc[(period, f"New wells/year {band} (figure note)"), "r15"] == figure
        assert article.loc[(period, f"New wells/year {band} (rounded in text)"), "r15"] == text


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
    pies.loc[pick, "share_percent"] -= 1.5
    pies.iloc[::-1].to_csv(tmp_path / name, index=False, float_format="%.12g")
    cross = pd.read_csv(tmp_path / "subtype-activity.csv")
    cross = cross[~((cross.activity == "Completion") & (cross.primary == "COMP") & (cross.subtype == "ACIDIZE"))]
    cross = pd.concat([cross, pd.DataFrame([{
        "activity": "Completion", "primary": "COMP", "subtype": "New subtype", "submissions": 3
    }])])
    cross.to_csv(tmp_path / "subtype-activity.csv", index=False)

    diff = compare_tables(BASE, tmp_path).set_index(["table", "group", "metric"])
    assert diff.index.is_unique
    share = diff.loc[("pies-rig", "2005 | Jack-up", "share_percent")]
    assert share.difference == pytest.approx(-1.5)
    assert share.difference_unit == "percentage points"
    assert diff.loc[("table1", "All", "New-well permits, 2005 to 2026 (-)"), "r12"] == 2895
    missing = diff.loc[("table1", "All", "Median water depth (m)")]
    assert pd.isna(missing.r12) and pd.isna(missing.difference)
    added = diff.loc[("subtype-activity", "Completion | COMP | New subtype", "submissions")]
    assert added.r15 == 3 and pd.isna(added.r12) and pd.isna(added.difference)
    removed = diff.loc[("subtype-activity", "Completion | COMP | ACIDIZE", "submissions")]
    assert removed.r12 == 58 and pd.isna(removed.r15) and pd.isna(removed.difference)
    headline = diff.loc["article"]
    assert headline.loc[("All years", "First permits without readable requested spud date"), "difference"] == 2


@pytest.mark.parametrize("column", ["iqr_days", "precipitation (3-year mean)"])
def test_comparison_rejects_unlisted_metric(tmp_path, column):
    fresh = copytree(DATA, tmp_path / "fresh")
    path = fresh / "days-summary.csv"
    days = pd.read_csv(path)
    days[column] = 1
    days.to_csv(path, index=False)
    with pytest.raises(ValueError, match="days-summary") as error:
        compare_tables(BASE, fresh)
    assert column in str(error.value)


@pytest.mark.parametrize("has_record", [False, True], ids=["counting-rules", "record-counts"])
def test_comparison_uses_baseline_no_spud_source(tmp_path, has_record):
    baseline = copytree(BASE, tmp_path / "data")
    (tmp_path / "counting-rules.md").write_text(
        "1,008 wells whose first New Well permit gives no requested spud date.", encoding="utf-8"
    )
    if has_record:
        (baseline / "record-counts.csv").write_text(
            "source,disposition,reason,records\nAPD,excluded,no_spud_date,9\n", encoding="utf-8"
        )
    diff = compare_tables(baseline, DATA).set_index(["table", "group", "metric"])
    row = diff.loc[("article", "All years", "First permits without readable requested spud date")]
    assert row.r12 == (9 if has_record else 1008)
    assert row.difference == row.r15 - row.r12


def test_malformed_baseline_no_spud_count_fails_closed(tmp_path):
    baseline = copytree(BASE, tmp_path / "data")
    (tmp_path / "counting-rules.md").write_text(
        "1,08 wells whose first New Well permit gives no requested spud date.", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="counting-rules.md"):
        compare_tables(baseline, DATA)
