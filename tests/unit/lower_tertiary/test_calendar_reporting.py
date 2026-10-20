"""Calendar reporting regression cases; all dates and quantities are synthetic."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "lower_tertiary"))
import build_drilling_insights as insights
import build_well_benchmark as benchmark


def _source(tmp_path):
    """Jan 1 to Mar 1 = 31 + 29 = 60; same-day span = 0 (2020 leap year).

    Missing dates and Jan 2 -> Jan 1 cannot yield valid nonnegative spans.
    The legacy DRILLING_DAYS deliberately disagrees with these dates.
    """
    source = tmp_path / "synthetic.xlsx"
    pd.DataFrame(
        {
            "LEASE_NAME": ["Synthetic"] * 4 + [None],
            "API_WELL_NUMBER": ["111111111100"] * 5,
            "WELL_NAME": ["A", "B", "C", "D", None],
            "WELL_SPUD_DATE": ["01/01/2020", "01/01/2020", None, "01/02/2020", None],
            "TOTAL_DEPTH_DATE": [
                "03/01/2020",
                "01/01/2020",
                "03/01/2020",
                "01/01/2020",
                None,
            ],
            "DRILLING_DAYS": [999] * 5,
        }
    ).to_excel(source, sheet_name="Sheet1", index=False)
    return source


def test_calendar_dates_override_legacy_days_and_preserve_zero(tmp_path):
    frame = insights.load_wells(_source(tmp_path))
    assert len(frame) == 4
    spans = frame["spud_to_td_calendar_days"]
    assert spans.iloc[:2].tolist() == [60, 0]
    assert spans.iloc[2:].isna().all()
    assert "drill_days" not in frame


def test_export_definitions_and_missing_values(tmp_path):
    """The two valid date differences are 60 and 0 days; other cells stay blank."""
    path = tmp_path / "calendar.csv"
    insights.write_csv(insights.load_wells(_source(tmp_path)), path)
    with path.open() as stream:
        reader = csv.DictReader(stream)
        assert "drilling_days" not in reader.fieldnames
        rows = list(reader)
    assert [r["spud_to_td_calendar_days"] for r in rows] == ["60.0", "0.0", "", ""]
    assert {r["basis"] for r in rows} == {"calendar_elapsed_spud_to_td"}


def test_page_population_definition_and_no_rig_time_claim(tmp_path):
    """Four named rows, two valid spans: 60 + 0 = 60; median = 30 days."""
    frame = insights.load_wells(_source(tmp_path))
    stats = insights.compute_stats(frame)
    assert stats["n_wellbores"] == 4
    assert stats["n_calendar"] == 2
    assert stats["total_calendar_days"] == 60
    assert stats["median_calendar_days"] == 30
    page = insights.render_html(stats, Path("synthetic.xlsx"))
    assert "calendar cycle time" in page
    assert "184" in page and "211" in page and "27" in page
    assert "membership" in page
    assert "NOT_EVALUATED" in page
    assert "rig-days</" not in page
    assert "learning is" not in page


def test_empty_calendar_population_is_reported(tmp_path):
    frame = insights.load_wells(_source(tmp_path)).iloc[2:]
    stats = insights.compute_stats(frame)
    assert stats["n_calendar"] == 0
    assert pd.isna(stats["median_calendar_days"])
    assert "NOT_EVALUATED" in insights.render_html(stats, Path("synthetic.xlsx"))


def test_saved_schema_migration_preserves_all_other_cells(tmp_path):
    """Structural migration copies source strings without recalculating values."""
    source = tmp_path / "benchmark.csv"
    source.write_text(
        "api12,drilling_days,completion_days\nsynthetic,60.0,100.0\nmissing,,\n"
    )
    benchmark.migrate_saved_csv(source)
    assert source.read_text() == (
        "api12,spud_to_completion_calendar_days,completion_days\n"
        "synthetic,60.0,100.0\nmissing,,\n"
    )
    original = source.read_bytes()
    benchmark.migrate_saved_csv(source)
    assert source.read_bytes() == original


def test_migration_rejects_conflicting_alias_without_writing(tmp_path):
    source = tmp_path / "benchmark.csv"
    source.write_text("spud_to_completion_calendar_days,drilling_days\n60,61\n")
    original = source.read_bytes()
    with pytest.raises(ValueError, match="disagree"):
        benchmark.migrate_saved_csv(source)
    assert source.read_bytes() == original


def test_benchmark_markdown_labels_calendar_components():
    frame = pd.DataFrame(
        [
            {
                "spud_to_completion_calendar_days": 60,
                "completion_days": 100,
                "uptime_flag": None,
                "revenue_flag": None,
                "decline_flag": None,
            }
        ]
    )
    text = benchmark.render_markdown(frame, benchmark.BenchmarkConfig(), "2020-06-09")
    assert "Spud to completion (calendar days)" in text
    assert "Completion to first oil (calendar days)" in text
    assert "Drill days" not in text
    assert "not active drilling" in text
