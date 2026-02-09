"""Tests for Part1Report -- Lower Tertiary Performance Analysis HTML report.

Run with:
    PYTHONPATH=src /usr/bin/python3 -m pytest \
        tests/modules/bsee/analysis/lower_tertiary/test_report_part1.py -v \
        --override-ini="addopts=-v --tb=short" \
        -W "default::pytest.PytestRemovedIn9Warning"
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest


# -- Fixtures ----------------------------------------------------------------


def _make_mock_analyzer() -> MagicMock:
    """Build a mock LTAnalyzer with performance data for Part 1."""
    analyzer = MagicMock()

    # aggregate_metrics property
    analyzer.aggregate_metrics = {
        "total_investment_billion": 50,
        "total_modu_days": 20000,
        "total_dc_cost_billion": 20,
        "subsea_uptime_pct": 67,
        "intervention_cost_per_well_million": 100,
        "zones_perforated_pct_range": [25, 30],
    }

    # validation_table property
    analyzer.validation_table = [
        {
            "name": "Jack/St. Malo",
            "appraisal_wells": 8,
            "discovery_to_fo_years": 12,
            "recovery_factor_pct": 5,
        },
        {
            "name": "Julia",
            "appraisal_wells": 6,
            "discovery_to_fo_years": 15,
            "recovery_factor_pct": 3,
        },
    ]

    # recovery_factors property
    analyzer.recovery_factors = {
        "subsea": {"range_pct": [2, 10], "label": "Subsea tieback"},
        "dry_tree": {"range_pct": [30, 40], "label": "Dry-tree (Spar/TLP)"},
    }

    # julia_deep_dive property
    analyzer.julia_deep_dive = {
        "oip_billion_bbl": 6.0,
        "sanctioned_billion_bbl": 0.8,
        "actual_recovery_mmbbl": 25,
        "legacy_csv_mmbbl": 18,
    }

    # drilling_activity_by_year() return value
    analyzer.drilling_activity_by_year.return_value = pd.DataFrame(
        {
            "field": ["Julia", "Julia", "Stones", "Stones"],
            "year": [2020, 2021, 2020, 2021],
            "records": [50, 60, 30, 40],
        }
    )

    # rig_utilization() return value
    analyzer.rig_utilization.return_value = pd.DataFrame(
        {
            "rig_name": ["Deepwater Proteus", "Deepwater Proteus", "West Vela"],
            "field": ["Julia", "Stones", "Julia"],
            "records": [100, 80, 120],
        }
    )

    # production_comparison() return value
    analyzer.production_comparison.return_value = {
        "julia": pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-01", "2020-02-01"]),
                "total_rate": [5000.0, 5500.0],
            }
        ),
        "stones": pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-01", "2020-02-01"]),
                "total_rate": [3000.0, 3200.0],
            }
        ),
    }

    # cumulative_comparison() return value
    analyzer.cumulative_comparison.return_value = {
        "julia": pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-01", "2020-02-01"]),
                "cumulative_mmbbl": [10.0, 20.0],
            }
        ),
        "stones": pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-01", "2020-02-01"]),
                "cumulative_mmbbl": [5.0, 10.0],
            }
        ),
    }

    # well_inventory() return value
    analyzer.well_inventory.return_value = {
        "julia": pd.DataFrame(
            {
                "API12": ["608114001", "608114002"],
                "COMPLETION_NAME": ["JUL-001", "JUL-002"],
                "O_CUMMULATIVE_PROD_MMBBL": [12.5, 8.3],
                "O_MEAN_PROD_RATE_BOPD": [4500.0, 3200.0],
                "START_PRODUCTION_DATE": ["2016-01-01", "2017-03-15"],
                "LAST_PRODUCTION_DATE": ["2024-06-01", "2024-06-01"],
            }
        ),
    }

    # source_attribution property
    analyzer.source_attribution = (
        "World Oil October 2025 -- "
        "America's Promising Lower Tertiary Frontier"
    )

    # _config with output_config for report title
    mock_config = MagicMock()
    mock_config.output_config = {
        "reports": {
            "part1": {
                "title": "Lower Tertiary Performance Analysis",
                "filename": "lt_performance_report.html",
                "output_dir": "frontierdeepwater/Mktg/World Oil/2026-01",
            }
        }
    }
    analyzer._config = mock_config

    return analyzer


@pytest.fixture()
def mock_analyzer() -> MagicMock:
    """Provide a mock LTAnalyzer for report generation tests."""
    return _make_mock_analyzer()


@pytest.fixture()
def report(mock_analyzer: MagicMock):
    """Instantiate Part1Report with mock analyzer."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_part1 import (
        Part1Report,
    )

    return Part1Report(mock_analyzer)


@pytest.fixture()
def output_path(tmp_path: Path) -> Path:
    """Provide a temporary output path for generated reports."""
    return tmp_path / "test_report.html"


@pytest.fixture()
def report_html(report, output_path: Path) -> str:
    """Generate the report and return the HTML string."""
    report.generate(output_path)
    return output_path.read_text(encoding="utf-8")


# -- Instantiation -----------------------------------------------------------


def test_part1_report_instantiates(report) -> None:
    """Part1Report accepts an LTAnalyzer and stores it."""
    assert report is not None
    assert report._a is not None


# -- Report Generation -------------------------------------------------------


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


# -- HTML Structure ----------------------------------------------------------


def test_html_has_doctype(report_html: str) -> None:
    """Generated HTML starts with <!DOCTYPE html>."""
    assert report_html.startswith("<!DOCTYPE html>")


def test_html_has_report_title(report_html: str) -> None:
    """Generated HTML contains the report title from config."""
    assert "Lower Tertiary Performance Analysis" in report_html


def test_html_has_plotly_script(report_html: str) -> None:
    """Generated HTML includes the Plotly.js library."""
    assert "plotly" in report_html.lower()


def test_html_has_table_of_contents(report_html: str) -> None:
    """Generated HTML includes a table of contents."""
    assert "Contents" in report_html
    assert "section-1" in report_html
    assert "section-10" in report_html


# -- Section Content ---------------------------------------------------------


def test_executive_summary_stat_cards(report_html: str) -> None:
    """Executive Summary contains stat cards with aggregate metrics."""
    assert "stat-card" in report_html
    assert "stats-grid" in report_html
    assert "$50B" in report_html
    assert "20,000" in report_html
    assert "$20B" in report_html


def test_validation_metrics_table(report_html: str) -> None:
    """Validation Metrics section contains a data table with field names."""
    assert "Validation Metrics" in report_html
    assert "data-table" in report_html
    assert "Jack/St. Malo" in report_html
    assert "Julia" in report_html


def test_recovery_factors_section(report_html: str) -> None:
    """Recovery Factor section shows subsea vs dry-tree ranges."""
    assert "Recovery Factor Comparison" in report_html
    assert "2-10%" in report_html
    assert "30-40%" in report_html


def test_julia_deep_dive_section(report_html: str) -> None:
    """Julia Deep-Dive section references OIP and recovery figures."""
    assert "Julia Field Deep-Dive" in report_html
    assert "6.0B bbl OIP" in report_html
    assert "25 MMBBL" in report_html


def test_war_activity_section(report_html: str) -> None:
    """WAR Drilling Activity section contains a stacked bar chart."""
    assert "WAR Drilling Activity by Field" in report_html
    assert "chart-container" in report_html


def test_rig_utilization_section(report_html: str) -> None:
    """Rig Utilization section renders a horizontal bar chart."""
    assert "Rig Utilization" in report_html
    assert "chart-container" in report_html


def test_production_curves_section(report_html: str) -> None:
    """Subsea Production Curves section renders line charts."""
    assert "Subsea Production Curves" in report_html
    assert "chart-container" in report_html


def test_cumulative_production_section(report_html: str) -> None:
    """Cumulative Production section renders cumulative line charts."""
    assert "Cumulative Production" in report_html
    assert "chart-container" in report_html


def test_well_summary_section(report_html: str) -> None:
    """Well Summary section contains a per-field data table."""
    assert "Well Summary" in report_html
    assert "data-table" in report_html
    assert "JUL-001" in report_html
    assert "608114001" in report_html


def test_methodology_section(report_html: str) -> None:
    """Methodology section includes source attribution text."""
    assert "Methodology &amp; Attribution" in report_html or \
        "Methodology & Attribution" in report_html
    assert "World Oil" in report_html
    assert "BSEE eWellWARRawData" in report_html


# -- CSS and Footer ----------------------------------------------------------


def test_html_has_css_styles(report_html: str) -> None:
    """Generated HTML embeds CSS styles."""
    assert "<style>" in report_html
    assert "stats-grid" in report_html
    assert "stat-card" in report_html


def test_html_has_footer(report_html: str) -> None:
    """Generated HTML has a footer with generation timestamp."""
    assert "footer" in report_html
    assert "Generated" in report_html


# -- All ten sections present ------------------------------------------------


def test_all_sections_present(report_html: str) -> None:
    """All 10 report sections appear in the output."""
    expected_sections = [
        "Executive Summary",
        "Validation Metrics",
        "Recovery Factor Comparison",
        "Julia Field Deep-Dive",
        "WAR Drilling Activity by Field",
        "Rig Utilization",
        "Subsea Production Curves",
        "Cumulative Production",
        "Well Summary",
        "Methodology",
    ]
    for section in expected_sections:
        assert section in report_html, f"Missing section: {section}"


# -- Subtitle ----------------------------------------------------------------


def test_subtitle_references_article(report_html: str) -> None:
    """Report subtitle references the World Oil article."""
    assert "World Oil" in report_html
    assert "Lower Tertiary Frontier" in report_html


# -- Helper functions --------------------------------------------------------


def test_card_helper_produces_html() -> None:
    """_card helper generates stat-card HTML."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_part1 import _card

    html = _card("Test Title", "42", "units")
    assert "stat-card" in html
    assert "Test Title" in html
    assert "42" in html
    assert "units" in html


def test_card_helper_no_unit() -> None:
    """_card helper omits unit span when unit is empty."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_part1 import _card

    html = _card("Title", "99", "")
    assert "unit" not in html
    assert "99" in html


def test_tbl_helper_produces_table() -> None:
    """_tbl helper generates a data-table HTML."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_part1 import _tbl

    html = _tbl(["Col A", "Col B"], [["v1", "v2"], ["v3", "v4"]])
    assert "data-table" in html
    assert "Col A" in html
    assert "v1" in html
    assert "<thead>" in html
    assert "<tbody>" in html
