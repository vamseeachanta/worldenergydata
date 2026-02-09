"""Tests for Part2Report — Architecture Options Analysis HTML report.

Run with:
    PYTHONPATH=src /usr/bin/python3 -m pytest \
        tests/modules/bsee/analysis/lower_tertiary/test_report_part2.py -v \
        --override-ini="addopts=-v --tb=short" \
        -W "default::pytest.PytestRemovedIn9Warning"
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────


def _make_mock_analyzer() -> MagicMock:
    """Build a mock LTAnalyzer with architecture data from YAML schema."""
    analyzer = MagicMock()

    # architecture_data property (matches YAML architecture section)
    analyzer.architecture_data = {
        "systems": ["Subsea Tieback", "Spar", "TLP", "Semi/DDS", "FrPS"],
        "criteria": [
            "Intervention Access",
            "Recovery Potential",
            "Water Depth Range",
            "CAPEX Efficiency",
            "Operational Uptime",
            "Well Count Capacity",
        ],
        "ratings": {
            "Subsea Tieback": [1, 2, 5, 4, 3, 2],
            "Spar": [4, 4, 4, 3, 4, 3],
            "TLP": [5, 5, 2, 3, 5, 5],
            "Semi/DDS": [5, 5, 5, 2, 4, 5],
            "FrPS": [4, 4, 5, 4, 4, 4],
        },
        "depth_limits_ft": {
            "Subsea Tieback": {"min": 0, "max": 12000},
            "Spar": {"min": 2000, "max": 8000},
            "TLP": {"min": 1000, "max": 6000},
            "Semi/DDS": {"min": 3000, "max": 10000},
            "FrPS": {"min": 3000, "max": 10000},
        },
        "pros_cons": {
            "Subsea Tieback": {
                "pros": ["Lower CAPEX", "Ultra-deepwater capable", "Modular expansion"],
                "cons": [
                    "No intervention access",
                    "Low recovery 2-10%",
                    "High workover cost $100M+",
                ],
            },
            "Spar": {
                "pros": [
                    "Dry-tree wells",
                    "Good motion characteristics",
                    "Proven to 8000ft",
                ],
                "cons": ["Higher CAPEX", "Limited to ~8000ft water depth"],
            },
            "TLP": {
                "pros": [
                    "Full dry-tree access",
                    "Highest recovery 30-40%",
                    "Best intervention",
                ],
                "cons": ["Depth limited to ~5-6000ft", "Tendon fatigue in ultra-deep"],
            },
            "Semi/DDS": {
                "pros": ["Deepwater capable", "Dry-tree access", "High well count"],
                "cons": ["Highest CAPEX", "Complex risers", "New technology risk"],
            },
            "FrPS": {
                "pros": [
                    "Floating production flexibility",
                    "Deepwater capable",
                    "Redeployable",
                ],
                "cons": ["No dry-tree", "Riser complexity", "Turret challenges"],
            },
        },
    }

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

    # subsea_vs_drytree_comparison() return value
    analyzer.subsea_vs_drytree_comparison.return_value = {
        "subsea_records": 1500,
        "dry_tree_records": 3000,
        "subsea_fields": ["Jack", "St. Malo", "Julia", "Stones", "Cascade/Chinook"],
        "dry_tree_fields": ["Mars", "Ursa", "Mad Dog", "Horn Mountain"],
        "activity_data": {},
    }

    # _config with output_config for report title
    mock_config = MagicMock()
    mock_config.output_config = {
        "reports": {
            "part2": {
                "title": "Architecture Options Analysis",
                "filename": "lt_options_report.html",
                "output_dir": "frontierdeepwater/Mktg/World Oil/2026-01",
            }
        }
    }
    analyzer._config = mock_config

    return analyzer


@pytest.fixture
def mock_analyzer() -> MagicMock:
    """Provide a mock LTAnalyzer for report generation tests."""
    return _make_mock_analyzer()


@pytest.fixture
def report(mock_analyzer: MagicMock):
    """Instantiate Part2Report with mock analyzer."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_part2 import Part2Report

    return Part2Report(mock_analyzer)


@pytest.fixture
def output_path(tmp_path: Path) -> Path:
    """Provide a temporary output path for generated reports."""
    return tmp_path / "lt_options_report.html"


# ── Instantiation ────────────────────────────────────────────────────


def test_part2_report_instantiates(report) -> None:
    """Part2Report accepts an LTAnalyzer and stores it."""
    assert report is not None
    assert report._a is not None


# ── Report Generation ────────────────────────────────────────────────


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


# ── HTML Structure ───────────────────────────────────────────────────


def test_html_has_doctype(report, output_path: Path) -> None:
    """Generated HTML starts with <!DOCTYPE html>."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")


def test_html_has_report_title(report, output_path: Path) -> None:
    """Generated HTML contains the report title from config."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Architecture Options Analysis" in html


def test_html_has_plotly_script(report, output_path: Path) -> None:
    """Generated HTML includes the Plotly.js library."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "plotly" in html.lower()


def test_html_has_table_of_contents(report, output_path: Path) -> None:
    """Generated HTML includes a table of contents."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Contents" in html
    assert "section-1" in html
    assert "section-8" in html


# ── Section Content ──────────────────────────────────────────────────


def test_executive_summary_stat_cards(report, output_path: Path) -> None:
    """Executive Summary contains stat cards with YAML data."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Systems Compared" in html
    assert "Criteria Evaluated" in html
    assert "stat-card" in html
    # Check specific values from mock
    assert "5" in html  # 5 systems
    assert "6" in html  # 6 criteria


def test_architecture_heatmap_section(report, output_path: Path) -> None:
    """Architecture Comparison section contains a heatmap chart."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Architecture Comparison" in html
    # Plotly heatmap will be rendered as div with chart data
    assert "chart-container" in html


def test_water_depth_section(report, output_path: Path) -> None:
    """Water Depth Feasibility section references depth values."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Water Depth Feasibility" in html


def test_recovery_by_arch_section(report, output_path: Path) -> None:
    """Recovery by Architecture section shows subsea vs dry-tree ranges."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Recovery by Architecture" in html
    assert "2-10%" in html
    assert "30-40%" in html


def test_intervention_cost_section(report, output_path: Path) -> None:
    """Intervention Cost section references cost per well."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Intervention Cost" in html
    assert "$100M" in html


def test_subsea_vs_drytree_section(report, output_path: Path) -> None:
    """Subsea vs Dry-Tree section uses WAR comparison data."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Subsea vs Dry-Tree" in html
    assert "1,500" in html  # subsea_records
    assert "3,000" in html  # dry_tree_records


def test_pros_cons_table(report, output_path: Path) -> None:
    """Pros/Cons section contains a styled table with all systems."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Pros &amp; Cons" in html or "Pros & Cons" in html
    assert "data-table" in html
    assert "Lower CAPEX" in html
    assert "No intervention access" in html


def test_conclusions_section(report, output_path: Path) -> None:
    """Conclusions section has highlight boxes."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Conclusions" in html
    assert "highlight" in html
    assert "Architecture Drives Recovery" in html


# ── CSS and Footer ───────────────────────────────────────────────────


def test_html_has_css_styles(report, output_path: Path) -> None:
    """Generated HTML embeds CSS styles."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "<style>" in html
    assert "stats-grid" in html
    assert "stat-card" in html


def test_html_has_footer(report, output_path: Path) -> None:
    """Generated HTML has a footer with generation timestamp."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "footer" in html
    assert "Generated" in html


# ── All eight sections present ───────────────────────────────────────


def test_all_sections_present(report, output_path: Path) -> None:
    """All 8 report sections appear in the output."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    expected_sections = [
        "Executive Summary",
        "Architecture Comparison",
        "Water Depth Feasibility",
        "Recovery by Architecture",
        "Intervention Cost",
        "Subsea vs Dry-Tree",
        "Pros",
        "Conclusions",
    ]
    for section in expected_sections:
        assert section in html, f"Missing section: {section}"


# ── Subtitle ─────────────────────────────────────────────────────────


def test_subtitle_references_article(report, output_path: Path) -> None:
    """Report subtitle references the World Oil article."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "World Oil" in html
    assert "The Options" in html


# ── Disclaimer ───────────────────────────────────────────────────────


def test_disclaimer_present(report, output_path: Path) -> None:
    """Report includes a data disclaimer noting article sources."""
    report.generate(output_path)
    html = output_path.read_text(encoding="utf-8")
    assert "Disclaimer" in html
    assert "Frontier Deepwater" in html


# ── Helper functions ─────────────────────────────────────────────────


def test_card_helper_produces_html() -> None:
    """_card helper generates stat-card HTML."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_part2 import _card

    html = _card("Test Title", "42", "units")
    assert "stat-card" in html
    assert "Test Title" in html
    assert "42" in html
    assert "units" in html


def test_card_helper_no_unit() -> None:
    """_card helper omits unit span when unit is empty."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_part2 import _card

    html = _card("Title", "99", "")
    assert "unit" not in html
    assert "99" in html


def test_tbl_helper_produces_table() -> None:
    """_tbl helper generates a data-table HTML."""
    from worldenergydata.bsee.analysis.lower_tertiary.report_part2 import _tbl

    html = _tbl(["Col A", "Col B"], [["v1", "v2"], ["v3", "v4"]])
    assert "data-table" in html
    assert "Col A" in html
    assert "v1" in html
    assert "<thead>" in html
    assert "<tbody>" in html
