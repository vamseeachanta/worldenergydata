"""Calendar reporting regression tests; synthetic dates use hand arithmetic."""

import hashlib
import importlib.util
import json
import os
import subprocess
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
    population = mod.read_population_counts()
    assert f"<b>{population['article_bores']}</b> wellbores" in page
    assert "<b>2</b> positive legacy" in page
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


def test_benchmark_digest_survives_autocrlf_checkout(tmp_path):
    """The provenance digest must survive a checkout with autocrlf enabled."""
    source = json.loads(
        (REPO / "reports/lower_tertiary/lifecycle/_norms.json").read_text()
    )["provenance"]["sources"][1]
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    git_dir = subprocess.run(
        ["git", "rev-parse", "--absolute-git-dir"],
        cwd=REPO,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    index = Path(git_dir) / "index"
    index_before = index.read_bytes()
    head_before = (Path(git_dir) / "HEAD").read_bytes()
    subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=true",
            "checkout-index",
            f"--prefix={tmp_path.as_posix()}/",
            "--",
            source["path"],
        ],
        cwd=REPO,
        env=env,
        check=True,
        capture_output=True,
    )
    assert index.read_bytes() == index_before
    assert (Path(git_dir) / "HEAD").read_bytes() == head_before
    data = (tmp_path / source["path"]).read_bytes()
    assert b"\r\n" not in data
    assert hashlib.sha256(data).hexdigest() == source["sha256"]


def test_phase_norm_rebuild_preserves_provenance_note(tmp_path, monkeypatch):
    """A rebuild must retain the issued digest revision and unchanged norm values."""
    mod = _script("build_phase_norms")
    monkeypatch.setattr(mod, "LIFECYCLE", tmp_path)
    monkeypatch.setattr(mod, "NORMS_DIR", tmp_path / "norms")
    previous = json.loads(
        (REPO / "reports/lower_tertiary/lifecycle/_norms.json").read_text()
    )
    write_text = Path.write_text

    def legacy_write_text(path, data, encoding=None, **kwargs):
        return write_text(path, data, encoding=encoding or "cp1252", **kwargs)

    monkeypatch.setattr(Path, "write_text", legacy_write_text)
    assert mod.main() == 0
    rebuilt = json.loads((tmp_path / "_norms.json").read_text(encoding="utf-8"))
    assert (
        rebuilt["provenance"]["revision_note"]
        == previous["provenance"]["revision_note"]
    )
    assert rebuilt["entries"] == previous["entries"]
    assert rebuilt["chips"] == previous["chips"]


def test_insight_date_matches_latest_issued_revision(monkeypatch):
    """Regeneration must keep the issued revision date independent of wall time."""
    mod = _script("build_drilling_insights")
    monkeypatch.setattr(
        mod,
        "REVISION_HISTORY",
        (*mod.REVISION_HISTORY, (99, "2030-01-01", "Synthetic revision reason")),
    )
    frame = pd.DataFrame(columns=["calendar_days", "MAX_WELL_BORE_TVD", "LEASE_NAME"])
    page = mod.render_html(mod.compute_stats(frame), mod.DEFAULT_SOURCE)
    assert "Report revision date 2030-01-01." in page


def test_population_note_reads_committed_inputs(tmp_path):
    """Hand count: one positive, one zero, one absent legacy entry = 1 of 3.

    Synthetic article table totals 2 bores and 9 D&C days; benchmark has one
    producing row. Changing the files must change the rendered note, not code.
    """
    mod = _script("build_drilling_insights")
    article = tmp_path / "article.md"
    article.write_text(
        "| Development | Bores (WO) | D&C (WO) |\n"
        "|---|---:|---:|\n| **Total** | **2** | **9** |\n"
    )
    benchmark = tmp_path / "benchmark.csv"
    benchmark.write_text("api12\n001\n")
    frame = pd.DataFrame(
        {
            "calendar_days": [60, 0, None],
            "DRILLING_DAYS": [60, 0, None],
            "MAX_WELL_BORE_TVD": [None] * 3,
            "LEASE_NAME": ["Synthetic"] * 3,
        }
    )
    population = mod.read_population_counts(article, benchmark)
    page = mod.render_html(mod.compute_stats(frame), mod.DEFAULT_SOURCE, population)
    assert "<b>1</b> positive legacy" in page
    assert "remaining 2" in page
    assert "<b>2</b> wellbores and 9 days" in page
    assert "1 producing wells" in page
    article.write_text(article.read_text().replace("**2**", "**4**"))
    benchmark.write_text("api12\n001\n002\n")
    population = mod.read_population_counts(article, benchmark)
    page = mod.render_html(mod.compute_stats(frame), mod.DEFAULT_SOURCE, population)
    assert "<b>4</b> wellbores" in page
    assert "2 producing wells" in page


def test_public_calendar_files_do_not_publish_legacy_schema():
    """Only calendar surfaces are checked; activity-coded drilling days stay valid."""
    files = list((REPO / "reports").rglob("lt_well_benchmark*.csv"))
    files += [REPO / "reports/lower_tertiary/lt_drilling_insights.csv"]
    for path in files:
        assert "drilling_days" not in pd.read_csv(path, nrows=0).columns, path
    for path in (REPO / "reports/lower_tertiary").glob("lt_well_benchmark*.md"):
        text = path.read_text()
        assert "Drill days" not in text
        assert "Spud to completion (calendar days)" in text
    page = (REPO / "reports/lower_tertiary/drilling_insights.html").read_text()
    assert "Calendar cycle time (days)" in page
    assert "Drilling days (days)" not in page


@pytest.mark.parametrize("total_rows", ["", "| Total | 2 | 9 |\n" * 2])
def test_population_note_rejects_missing_or_duplicate_totals(tmp_path, total_rows):
    mod = _script("build_drilling_insights")
    article = tmp_path / "article.md"
    article.write_text("| Development | Bores (WO) | D&C (WO) |\n" + total_rows)
    benchmark = tmp_path / "benchmark.csv"
    benchmark.write_text("api12\n")
    with pytest.raises(ValueError, match="one population total"):
        mod.read_population_counts(article, benchmark)


def test_committed_calendar_page_matches_builder():
    mod = _script("build_drilling_insights")
    frame = mod.load_wells(mod.DEFAULT_SOURCE)
    expected = (
        mod.site_nav.inject_for(
            mod.render_html(mod.compute_stats(frame), mod.DEFAULT_SOURCE),
            "drilling_insights",
        ).rstrip()
        + "\n"
    )
    assert mod.HTML_PATH.read_text(encoding="utf-8") == expected


def test_benchmark_page_links_worked_calendar_example():
    mod = _script("build_well_benchmark")
    frame = pd.DataFrame(columns=["uptime_flag", "revenue_flag", "decline_flag"])
    page = mod.render_markdown(frame, mod.BenchmarkConfig(), "2020-06-30")
    assert "benchmark_calendar_spans.md" in page
    doc = REPO / "docs/data-sources/bsee/analysis/rig_days/benchmark_calendar_spans.md"
    assert "60 + 100 = 160" in doc.read_text()
