"""Tests for intervention-by-service-type detail report (WRK-115).

TDD Red phase: tests define expected report behavior before
implementation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.intervention_detail_report import (
    InterventionDetailReport,
)


# ---------------------------------------------------------------------------
# Fixtures -- synthetic data
# ---------------------------------------------------------------------------


def _make_war_df() -> pd.DataFrame:
    """Synthetic WAR DataFrame spanning multiple years with mixed activity.

    Includes intervention rigs across all 7 service types plus drilling
    rigs for contrast.  Spread across 2018-2024 and several GOM areas.
    """
    rows: list[dict] = []
    rig_configs = [
        # intervention types
        ("WIRELINE UNIT 7", "EI"),
        ("WIRELINE UNIT 12", "MC"),
        ("COIL TUBING ALPHA", "GC"),
        ("LIFT BOAT 99", "ST"),
        ("SNUBBING UNIT 3", "SS"),
        ("WORKOVER RIG 12", "SP"),
        ("DIVE SUPPORT VESSEL A", "MC"),
        ("PUMPING UNIT 5", "EI"),
        # drilling rigs for contrast
        ("DEEPWATER PATHFINDER", "GC"),
        ("ROWAN GORILLA V", "HI"),
    ]
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
    months = [1, 4, 7, 10]
    idx = 0
    for year in years:
        for rig_name, area in rig_configs:
            for month in months:
                rows.append(
                    {
                        "RIG_NAME": rig_name,
                        "WAR_START_DT": f"{month}/15/{year}",
                        "WAR_END_DT": f"{month}/21/{year}",
                        "API_WELL_NUMBER": f"W{idx % 30:04d}",
                        "BOTM_LEASE_NUM": f"L{idx % 10:02d}",
                        "AREA_CODE": area,
                        "BUS_ASC_NAME": f"OPERATOR {idx % 8}",
                    }
                )
                idx += 1
    return pd.DataFrame(rows)


def _make_fleet_df() -> pd.DataFrame:
    """Synthetic fleet DataFrame with known rig types."""
    return pd.DataFrame(
        {
            "RIG_NAME": [
                "WIRELINE UNIT 7",
                "ROWAN GORILLA V",
            ],
            "RIG_TYPE": [
                "wireline_unit",
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
        ]
    )


# ---------------------------------------------------------------------------
# Test: report generates an HTML file
# ---------------------------------------------------------------------------


class TestInterventionDetailGeneratesHtml:
    """Verify generate() produces a valid HTML file."""

    def test_generates_html_file(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = InterventionDetailReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "detail.html")
            result_path = report.generate(output_path)

            assert result_path == output_path
            assert Path(result_path).exists()
            assert Path(result_path).stat().st_size > 0

    def test_html_is_nonempty(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = InterventionDetailReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "detail.html")
            report.generate(output_path)
            content = Path(output_path).read_text()
            assert len(content) > 1000

    def test_html_references_plotly(self) -> None:
        """HTML should reference plotly.js (CDN or inline)."""
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = InterventionDetailReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "detail.html")
            report.generate(output_path)
            content = Path(output_path).read_text()
            assert "plotly" in content.lower()


# ---------------------------------------------------------------------------
# Test: report contains all 9 section titles
# ---------------------------------------------------------------------------


class TestInterventionDetailContainsSections:
    """Verify the HTML contains all expected section titles."""

    def test_contains_all_section_titles(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = InterventionDetailReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "detail.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            expected_titles = [
                "Executive Summary",
                "Service Type Deep-Dive",
                "Service Type Comparison",
                "Geographic Distribution by Service Type",
                "Operator-Service Matrix",
                "Seasonal Patterns by Service Type",
                "Duration Analysis by Service Type",
                "Market Share Trends",
                "Methodology",
            ]
            for title in expected_titles:
                assert title in content, (
                    f"Expected section title '{title}' not found in report HTML"
                )

    def test_contains_table_of_contents(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = InterventionDetailReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "detail.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            assert "Table of Contents" in content
            assert "section-1" in content

    def test_contains_back_link(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = InterventionDetailReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "detail.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            assert "intervention_dashboard.html" in content
            assert "Back to Main Report" in content


# ---------------------------------------------------------------------------
# Test: each service type name appears in output
# ---------------------------------------------------------------------------


class TestInterventionDetailContainsServiceTypes:
    """Verify each service type display name appears in the HTML."""

    def test_contains_all_service_type_names(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = InterventionDetailReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "detail.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            service_types = [
                "Wireline Unit",
                "Coil Tubing Unit",
                "Lift Boat",
                "Snubbing Unit",
                "Workover Rig",
                "Support Vessel",
                "Pumping Unit",
            ]
            for svc in service_types:
                assert svc in content, (
                    f"Service type '{svc}' not found in report HTML"
                )

    def test_contains_data_tables(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = InterventionDetailReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "detail.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            assert "data-table" in content
            assert "<table" in content
            assert "<thead" in content


# ---------------------------------------------------------------------------
# Test: empty data does not crash
# ---------------------------------------------------------------------------


class TestInterventionDetailHandlesEmptyData:
    """Empty WAR DataFrame should not crash report generation."""

    def test_handles_empty_war_df(self) -> None:
        war_df = _make_empty_war_df()
        fleet_df = _make_fleet_df()
        report = InterventionDetailReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "empty.html")
            result_path = report.generate(output_path)

            assert result_path == output_path
            assert Path(result_path).exists()

    def test_empty_data_still_has_sections(self) -> None:
        war_df = _make_empty_war_df()
        fleet_df = _make_fleet_df()
        report = InterventionDetailReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "empty.html")
            report.generate(output_path)
            content = Path(output_path).read_text()

            assert "Executive Summary" in content
            assert "Methodology" in content


# ---------------------------------------------------------------------------
# Test: output directory creation
# ---------------------------------------------------------------------------


class TestInterventionDetailOutputDirectory:
    """Generate should create output directories if they don't exist."""

    def test_creates_nested_output_directory(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        report = InterventionDetailReport(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = str(
                Path(tmpdir) / "a" / "b" / "c" / "report.html"
            )
            result_path = report.generate(nested_path)

            assert Path(result_path).exists()
