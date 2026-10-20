"""Calendar reporting regression tests; synthetic dates use hand arithmetic."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]


def _script(name):
    spec = importlib.util.spec_from_file_location(
        name, REPO / "scripts/lower_tertiary" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_saved_benchmark_migration_preserves_values(tmp_path):
    """Synthetic 60-day span: January 31 + leap-February 29 = 60.

    Renaming a header must preserve every cell, including blank and zero.
    """
    mod = _script("build_well_benchmark")
    path = tmp_path / "benchmark.csv"
    path.write_text("api12,drilling_days,completion_days\n001,60,100\n002,,0\n")
    frame = mod.read_saved_benchmark(path)
    assert frame.columns.tolist() == [
        "api12",
        "spud_to_completion_calendar_days",
        "completion_days",
    ]
    assert frame.to_dict("list") == {
        "api12": ["001", "002"],
        "spud_to_completion_calendar_days": ["60", ""],
        "completion_days": ["100", "0"],
    }


def test_benchmark_table_calls_calendar_time_by_name():
    mod = _script("build_well_benchmark")
    frame = pd.DataFrame(
        [
            {
                "spud_to_completion_calendar_days": 60,
                "uptime_flag": None,
                "revenue_flag": None,
                "decline_flag": None,
            }
        ]
    )
    text = mod.render_markdown(frame, mod.BenchmarkConfig(), "2020-06-30")
    assert "Spud to completion (calendar days)" in text
    assert mod._fmt("") == "—"
    assert "Drill days" not in text
    assert "not rig-days" in text


def test_insight_uses_dates_not_legacy_days(tmp_path):
    """Jan 1 to Mar 1 2020 = 31 + 29 = 60; same day = 0.

    Legacy values 999 and 888 deliberately disagree. Missing and reversed
    dates have no derivable span; they must stay null, never become zero.
    """
    mod = _script("build_drilling_insights")
    source = tmp_path / "source.xlsx"
    pd.DataFrame(
        {
            "LEASE_NAME": ["Synthetic"] * 4,
            "WELL_SPUD_DATE": ["01/01/2020"] * 4,
            "TOTAL_DEPTH_DATE": ["03/01/2020", "01/01/2020", None, "12/31/2019"],
            "DRILLING_DAYS": [999, 888, 777, 666],
            "COMPLETION_DAYS": [1] * 4,
            "MAX_DRILL_FLUID_WGT": [15] * 4,
        }
    ).to_excel(source, sheet_name="Sheet1", index=False)
    frame = mod.load_wells(source)
    assert frame["calendar_days"].iloc[:2].tolist() == [60, 0]
    assert frame["calendar_days"].iloc[2:].isna().all()


def test_insight_csv_and_page_state_definition_and_population(tmp_path):
    """Spans 60 and 0 total 60; missing span excluded: n=2 of 3.

    Synthetic TVDs are illustrative input only, not acceptance limits.
    """
    mod = _script("build_drilling_insights")
    frame = pd.DataFrame(
        {
            "LEASE_NAME": ["Synthetic"] * 3,
            "WELL_NAME": ["A", "B", "C"],
            "API_WELL_NUMBER": ["001", "002", "003"],
            "SURF_LEASE_NUM": ["G1"] * 3,
            "WATER_DEPTH": [1000] * 3,
            "WELL_SPUD_DATE": pd.to_datetime(["2020-01-01"] * 3),
            "TOTAL_DEPTH_DATE": pd.to_datetime(["2020-03-01", "2020-01-01", None]),
            "calendar_days": [60, 0, None],
            "MAX_WELL_BORE_TVD": [10000, 20000, 30000],
            "DRILLING_DAYS": [999, 888, 0],
        }
    )
    stats = mod.compute_stats(frame)
    assert stats["total_calendar_days"] == 60
    assert stats["n_calendar"] == 2
    target = tmp_path / "out.csv"
    mod.write_csv(frame, target)
    saved = pd.read_csv(target)
    assert "drilling_days" not in saved
    assert saved["spud_to_td_calendar_days"].iloc[:2].tolist() == [60, 0]
    page = mod.render_html(stats, mod.DEFAULT_SOURCE)
    assert "Calendar cycle time" in page
    assert "184" in page and "211" in page
    assert "not rig-days" in page
    assert "2 of 3" in page
    assert "among 217 workbook wellbores" not in page
    assert "Current population: 3 workbook wellbores" in page
    assert "Revision history" in page


def test_saved_benchmark_rejects_conflicting_aliases(tmp_path):
    mod = _script("build_well_benchmark")
    path = tmp_path / "bad.csv"
    path.write_text("drilling_days,spud_to_completion_calendar_days\n60,61\n")
    with pytest.raises(ValueError, match="conflict"):
        mod.read_saved_benchmark(path)


@pytest.mark.parametrize(
    "source",
    json.loads((REPO / "reports/lower_tertiary/lifecycle/_norms.json").read_text())[
        "provenance"
    ]["sources"],
)
def test_phase_norm_source_digests_match_committed_bytes(source):
    assert (
        hashlib.sha256((REPO / source["path"]).read_bytes()).hexdigest()
        == source["sha256"]
    )


@pytest.mark.parametrize("name", ["build_well_benchmark", "build_drilling_insights"])
def test_report_revisions_are_rendered_from_versioned_history(name, monkeypatch):
    mod = _script(name)
    previous = tuple(mod.REVISION_HISTORY)
    monkeypatch.setattr(
        mod,
        "REVISION_HISTORY",
        (*previous, (99, "2030-01-01", "Synthetic revision reason")),
    )
    if name == "build_well_benchmark":
        frame = pd.DataFrame(columns=["uptime_flag", "revenue_flag", "decline_flag"])
        page = mod.render_markdown(frame, mod.BenchmarkConfig(), "2020-06-30")
        assert "completion_days" in page
        assert "compatibility" in page
    else:
        frame = pd.DataFrame(
            columns=["calendar_days", "MAX_WELL_BORE_TVD", "LEASE_NAME"]
        )
        page = mod.render_html(mod.compute_stats(frame), mod.DEFAULT_SOURCE)
    assert "Synthetic revision reason" in page
    for revision, issued, reason in previous:
        assert str(revision) in page
        assert issued in page
        assert reason in page
