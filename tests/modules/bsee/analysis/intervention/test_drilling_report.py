"""Tests for drilling analysis report (WRK-115).

TDD Red phase: tests define expected report behavior before
implementation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.drilling_report import (
    DrillingAnalysisReport,
)


# ---------------------------------------------------------------------------
# Fixtures -- synthetic data
# ---------------------------------------------------------------------------


def _make_war_df() -> pd.DataFrame:
    """Synthetic WAR DataFrame with drilling rigs, water depth, and areas."""
    rows = []
    rig_configs = [
        # (rig_name, area_code, well_prefix, lease_prefix, water_depth)
        ("DEEPWATER PATHFINDER", "GC", "W1", "L1", 4500.0),
        ("OCEAN STAR", "WR", "W2", "L2", 7200.0),
        ("ROWAN GORILLA V", "HI", "W3", "L3", 300.0),
        ("ENSCO 8506", "MC", "W4", "L4", 3200.0),
        ("HELMERICH & PAYNE 201", "EI", "W5", "L5", None),
        ("INLAND BARGE 10", "SP", "W6", "L6", 15.0),
        ("DEEPWATER MILLENNIUM", "GB", "W7", "L7", 2800.0),
        ("ROWAN GORILLA VI", "EC", "W8", "L8", 350.0),
    ]
    years = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
    months = [1, 4, 7, 10]
    idx = 0
    for year in years:
        for rig_name, area, wp, lp, wd in rig_configs:
            for month in months[:3]:  # 3 WAR records per rig per year
                rows.append(
                    {
                        "RIG_NAME": rig_name,
                        "WAR_START_DT": f"{month}/15/{year}",
                        "WAR_END_DT": f"{month}/21/{year}",
                        "API_WELL_NUMBER": f"{wp}{idx % 4:04d}",
                        "BOTM_LEASE_NUM": f"{lp}{idx % 3:02d}",
                        "AREA_CODE": area,
                        "BUS_ASC_NAME": f"OPERATOR {idx % 5}",
                        "WATER_DEPTH": wd,
                    }
                )
                idx += 1
    return pd.DataFrame(rows)


def _make_fleet_df() -> pd.DataFrame:
    """Synthetic fleet DataFrame with known drilling rig types."""
    return pd.DataFrame(
        {
            "RIG_NAME": [
                "ROWAN GORILLA V",
                "ROWAN GORILLA VI",
                "ENSCO 8506",
            ],
            "RIG_TYPE": [
                "jack_up",
                "jack_up",
                "jack_up",
            ],
        }
    )


def _make_empty_war_df() -> pd.DataFrame:
    """Empty WAR DataFrame with required columns."""
    return pd.DataFrame(
        columns=[
            "RIG_NAME",
            "WAR_START_DT",
            "WAR_END_DT",
            "API_WELL_NUMBER",
            "BOTM_LEASE_NUM",
            "AREA_CODE",
            "BUS_ASC_NAME",
            "WATER_DEPTH",
        ]
    )


# ---------------------------------------------------------------------------
# Test: report generates an HTML file
# ---------------------------------------------------------------------------


class TestDrillingReportGeneratesHtml:
    """Verify generate() produces a valid HTML file."""

    def test_report_generates_html_file(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = DrillingAnalysisReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_drilling.html")
            result_path = report.generate(output_path)

            assert result_path == output_path
            assert Path(result_path).exists()
            assert Path(result_path).stat().st_size > 0

    def test_report_html_references_plotly(self) -> None:
        """HTML should reference plotly.js (CDN or inline)."""
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = DrillingAnalysisReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_drilling.html")
            report.generate(output_path)

            content = Path(output_path).read_text()
            assert "plotly" in content.lower()

    def test_report_html_is_not_empty(self) -> None:
        """Generated HTML should have substantial content."""
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = DrillingAnalysisReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_drilling.html")
            report.generate(output_path)

            content = Path(output_path).read_text()
            # Should have a reasonable amount of content
            assert len(content) > 1000


# ---------------------------------------------------------------------------
# Test: report contains expected section titles
# ---------------------------------------------------------------------------


class TestDrillingReportContainsSections:
    """Verify the HTML contains all 9 expected section titles."""

    def test_report_contains_all_section_titles(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = DrillingAnalysisReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_drilling.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            expected_titles = [
                "Executive Summary",
                "Drilling Fleet Composition",
                "Water Depth Analysis",
                "Drilling Activity by Year",
                "Drilling Duration Analysis",
                "Geographic Analysis",
                "Operator Intelligence",
                "Drilling Parameters Summary",
                "Methodology",
            ]
            for title in expected_titles:
                assert title in content, (
                    f"Expected section title '{title}' not found in report HTML"
                )

    def test_report_contains_table_of_contents(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = DrillingAnalysisReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_drilling.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            assert "Table of Contents" in content
            assert "section-1" in content

    def test_report_contains_back_link(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = DrillingAnalysisReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_drilling.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            assert "intervention_dashboard.html" in content
            assert "Back to Main Report" in content


# ---------------------------------------------------------------------------
# Test: report contains expected chart titles
# ---------------------------------------------------------------------------


class TestDrillingReportContainsCharts:
    """Verify the HTML contains key chart titles."""

    def test_report_contains_key_chart_titles(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = DrillingAnalysisReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_drilling.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            expected_chart_titles = [
                "Drilling Rig Type Distribution",
                "Water Depth Distribution",
                "Drilling Activity by Rig Type",
                "Well Drilling Duration",
                "Drilling by Geological Province",
                "Top Drilling Operators",
            ]
            for title in expected_chart_titles:
                assert title in content, (
                    f"Expected chart title '{title}' not found in report HTML"
                )

    def test_report_contains_data_tables(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = DrillingAnalysisReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_drilling.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            assert "data-table" in content
            assert "<table" in content
            assert "<thead" in content


# ---------------------------------------------------------------------------
# Test: report handles empty data gracefully
# ---------------------------------------------------------------------------


class TestDrillingReportHandlesEmptyData:
    """Empty WAR DataFrame should not crash the report generation."""

    def test_report_handles_empty_data(self) -> None:
        war_df = _make_empty_war_df()
        fleet_df = _make_fleet_df()
        report = DrillingAnalysisReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_empty.html")
            result_path = report.generate(output_path)

            assert result_path == output_path
            assert Path(result_path).exists()

    def test_empty_data_still_has_sections(self) -> None:
        war_df = _make_empty_war_df()
        fleet_df = _make_fleet_df()
        report = DrillingAnalysisReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_empty.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            assert "Executive Summary" in content
            assert "Methodology" in content


# ---------------------------------------------------------------------------
# Test: output directory creation
# ---------------------------------------------------------------------------


class TestDrillingReportOutputDirectory:
    """Generate should create output directories if they don't exist."""

    def test_creates_nested_output_directory(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = DrillingAnalysisReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = str(
                Path(tmpdir) / "sub" / "deep" / "drilling.html"
            )
            result_path = report.generate(nested_path)

            assert Path(result_path).exists()
