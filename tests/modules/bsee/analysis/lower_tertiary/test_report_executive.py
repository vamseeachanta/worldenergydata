"""Tests for ExecutiveReport — Executive Summary HTML report.

Run with:
    PYTHONPATH=src /usr/bin/python3 -m pytest \
        tests/modules/bsee/analysis/lower_tertiary/test_report_executive.py -v \
        --override-ini="addopts=-v --tb=short" \
        -W "default::pytest.PytestRemovedIn9Warning"
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest


# -- Fixtures ---------------------------------------------------------------


def _make_mock_analyzer() -> MagicMock:
    """Build a mock LTAnalyzer with data matching the YAML schema."""
    analyzer = MagicMock()

    # aggregate_metrics property
    analyzer.aggregate_metrics = {
        "total_investment_billion": 50,
        "total_modu_days": 20000,
        "total_dc_cost_billion": 20,
        "subsea_uptime_pct": 67,
        "zones_perforated_pct_range": [25, 30],
        "intervention_cost_per_well_million": 100,
    }

    # recovery_factors property
    analyzer.recovery_factors = {
        "subsea": {"range_pct": [2, 10], "label": "Subsea tieback"},
        "dry_tree": {"range_pct": [30, 40], "label": "Dry-tree (Spar/TLP)"},
    }

    # economics property
    analyzer.economics = {
        "mean_subsea_npv_billion": -1.2,
        "discount_rate": 0.10,
    }

    # source_attribution property
    analyzer.source_attribution = (
        "Frontier Deepwater analysis of BSEE data (2025)"
    )

    # report_title method
    _titles = {
        "executive": "Lower Tertiary Executive Summary",
        "part1": "Lower Tertiary Performance Analysis",
        "part2": "Architecture Options Analysis",
    }
    analyzer.report_title.side_effect = lambda key: _titles[key]

    # war_summary_table() — returns a DataFrame with expected columns
    analyzer.war_summary_table.return_value = pd.DataFrame([
        {
            "field": "Jack",
            "area": "WR",
            "records": 450,
            "category": "subsea",
            "operator": "Chevron",
            "first_oil": 2014,
        },
        {
            "field": "Julia",
            "area": "WR",
            "records": 320,
            "category": "subsea",
            "operator": "ExxonMobil",
            "first_oil": 2016,
        },
        {
            "field": "Mars",
            "area": "MC",
            "records": 2100,
            "category": "dry_tree",
            "operator": "Shell",
            "first_oil": 1996,
        },
        {
            "field": "Shenandoah",
            "area": "WR",
            "records": 85,
            "category": "subsea",
            "operator": "Beacon Offshore",
            "first_oil": None,
        },
    ])

    return analyzer


@pytest.fixture
def mock_analyzer() -> MagicMock:
    """Provide a mock LTAnalyzer for report generation tests."""
    return _make_mock_analyzer()


@pytest.fixture
def report(mock_analyzer: MagicMock):
    """Instantiate ExecutiveReport with mock analyzer."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_executive import (
        ExecutiveReport,
    )

    return ExecutiveReport(mock_analyzer)


@pytest.fixture
def output_path(tmp_path: Path) -> Path:
    """Provide a temporary output path for generated reports."""
    return tmp_path / "lt_executive_summary.html"


# -- Instantiation ----------------------------------------------------------


def test_executive_report_instantiates(report) -> None:
    """ExecutiveReport accepts an LTAnalyzer and stores it."""
    assert report is not None
    assert report._a is not None


# -- Report Generation ------------------------------------------------------


def test_generate_creates_html_file(report, output_path: Path) -> None:
    """generate() writes an HTML file to the specified path."""
    result = report.generate(output_path)
    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_generate_creates_parent_dirs(report, tmp_path: Path) -> None:
    """generate() creates parent directories if they do not exist."""
    nested = tmp_path / "deep" / "nested" / "report.html"
    report.generate(nested)
    assert nested.exists()


def test_generate_returns_path(report, output_path: Path) -> None:
    """generate() returns the output Path object."""
    result = report.generate(output_path)
    assert isinstance(result, Path)
    assert result == output_path


# -- HTML Structure ---------------------------------------------------------


def test_html_has_doctype(report, output_path: Path) -> None:
    """Generated HTML starts with <!DOCTYPE html>."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")


def test_html_has_report_title(report, output_path: Path) -> None:
    """Generated HTML contains the report title from config."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Lower Tertiary Executive Summary" in html


def test_html_has_plotly_script(report, output_path: Path) -> None:
    """Generated HTML includes the Plotly.js CDN reference."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "plotly-2.35.2.min.js" in html


def test_html_has_table_of_contents(report, output_path: Path) -> None:
    """Generated HTML includes a table of contents with 5 sections."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Contents" in html
    assert "section-1" in html
    assert "section-5" in html


# -- Section 1: Two-Decade Scorecard ---------------------------------------


def test_scorecard_stat_cards(report, output_path: Path) -> None:
    """Scorecard section contains stat cards with YAML-driven values."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Two-Decade Scorecard" in html
    assert "stat-card" in html
    assert "$50B" in html
    assert "$20B" in html
    assert "20,000" in html


def test_scorecard_recovery_ranges(report, output_path: Path) -> None:
    """Scorecard shows subsea and dry-tree recovery factor ranges."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "2-10%" in html
    assert "30-40%" in html


def test_scorecard_npv(report, output_path: Path) -> None:
    """Scorecard shows mean subsea NPV with discount rate."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "$-1.2B" in html
    assert "@10%" in html


# -- Section 2: The Performance Gap ----------------------------------------


def test_performance_gap_section(report, output_path: Path) -> None:
    """Performance Gap section has a chart container with bar chart."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "The Performance Gap" in html
    assert "chart-container" in html


def test_performance_gap_labels(report, output_path: Path) -> None:
    """Performance Gap chart references subsea and dry-tree labels."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Subsea tieback" in html
    # Plotly may HTML-escape the slash in JSON; check the label is present
    assert "Dry-tree" in html
    assert "Spar" in html


# -- Section 3: Live WAR Data Snapshot -------------------------------------


def test_war_snapshot_table(report, output_path: Path) -> None:
    """WAR Snapshot section has a data table with field data."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Live WAR Data Snapshot" in html
    assert "data-table" in html


def test_war_snapshot_field_names(report, output_path: Path) -> None:
    """WAR Snapshot table contains field names from mock data."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Jack" in html
    assert "Julia" in html
    assert "Mars" in html


def test_war_snapshot_total_records(report, output_path: Path) -> None:
    """WAR Snapshot shows total record count across all fields."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    # 450 + 320 + 2100 + 85 = 2955
    assert "2,955" in html


def test_war_snapshot_null_first_oil_shows_tbd(
    report, output_path: Path,
) -> None:
    """Fields with null first_oil display TBD."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "TBD" in html


def test_war_snapshot_first_oil_year(report, output_path: Path) -> None:
    """Fields with known first_oil show the year."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "2014" in html
    assert "2016" in html


def test_war_snapshot_categories(report, output_path: Path) -> None:
    """WAR Snapshot table shows formatted category labels."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Subsea" in html
    assert "Dry Tree" in html


def test_war_snapshot_empty_returns_no_data_message(
    mock_analyzer: MagicMock, tmp_path: Path,
) -> None:
    """When WAR data is empty, section shows a no-data message."""
    mock_analyzer.war_summary_table.return_value = pd.DataFrame()

    from worldenergydata.bsee.analysis.lower_tertiary.report_executive import (
        ExecutiveReport,
    )

    rpt = ExecutiveReport(mock_analyzer)
    out = tmp_path / "empty_war.html"
    rpt.generate(out)
    html = out.read_text(encoding="utf-8")
    assert "No WAR data available" in html


# -- Section 4: Investment Implications ------------------------------------


def test_investment_section(report, output_path: Path) -> None:
    """Investment Implications section has a chart with cost data."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Investment Implications" in html
    assert "chart-container" in html


def test_investment_annotation(report, output_path: Path) -> None:
    """Investment chart includes annotation about negative NPV."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "value destruction" in html


# -- Section 5: Path Forward -----------------------------------------------


def test_path_forward_highlight_boxes(report, output_path: Path) -> None:
    """Path Forward section has three highlight boxes."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Path Forward" in html
    assert "Architecture Matters Most" in html
    assert "Next-Generation Options" in html
    assert "Industry Implications" in html


def test_path_forward_source_attribution(report, output_path: Path) -> None:
    """Path Forward section includes the source attribution."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Frontier Deepwater analysis of BSEE data (2025)" in html


# -- CSS and Footer ---------------------------------------------------------


def test_html_has_css_styles(report, output_path: Path) -> None:
    """Generated HTML embeds CSS styles for all visual elements."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "<style>" in html
    assert "stats-grid" in html
    assert "stat-card" in html
    assert "highlight" in html
    assert "data-note" in html


def test_html_has_footer(report, output_path: Path) -> None:
    """Generated HTML has a footer with generation timestamp."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "footer" in html
    assert "Generated" in html
    assert "worldenergydata pipeline" in html


# -- All five sections present ----------------------------------------------


def test_all_sections_present(report, output_path: Path) -> None:
    """All 5 report sections appear in the output."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    expected_sections = [
        "Two-Decade Scorecard",
        "The Performance Gap",
        "Live WAR Data Snapshot",
        "Investment Implications",
        "Path Forward",
    ]
    for section in expected_sections:
        assert section in html, f"Missing section: {section}"


# -- Subtitle ---------------------------------------------------------------


def test_subtitle_references_combined_insights(
    report, output_path: Path,
) -> None:
    """Report subtitle references combined insights from both articles."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Combined Insights" in html
    assert "World Oil" in html


# -- Helper functions -------------------------------------------------------


def test_card_helper_produces_html() -> None:
    """_card helper generates stat-card HTML."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_executive import (
        _card,
    )

    html = _card("Test Title", "42", "units")
    assert "stat-card" in html
    assert "Test Title" in html
    assert "42" in html
    assert "units" in html


def test_card_helper_no_unit() -> None:
    """_card helper omits unit span when unit is empty."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_executive import (
        _card,
    )

    html = _card("Title", "99")
    assert "unit" not in html
    assert "99" in html


def test_tbl_helper_produces_table() -> None:
    """_tbl helper generates a data-table HTML."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_executive import (
        _tbl,
    )

    html = _tbl(["Col A", "Col B"], [["v1", "v2"], ["v3", "v4"]])
    assert "data-table" in html
    assert "Col A" in html
    assert "v1" in html
    assert "<thead>" in html
    assert "<tbody>" in html
