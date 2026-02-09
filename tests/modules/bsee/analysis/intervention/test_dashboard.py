"""Tests for intervention market intelligence report (WRK-115 Phase 2).

TDD Red phase: tests define expected report behavior before
implementation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.dashboard import (
    InterventionDashboard,
)


# ---------------------------------------------------------------------------
# Fixtures -- synthetic data
# ---------------------------------------------------------------------------


def _make_war_df() -> pd.DataFrame:
    """Synthetic WAR DataFrame spanning multiple years with mixed activity."""
    rows = []
    rig_configs = [
        # (rig_name, area_code, well_prefix, lease_prefix)
        ("DEEPWATER PATHFINDER", "GC", "W1", "L1"),
        ("OCEAN STAR", "WR", "W2", "L2"),
        ("ROWAN GORILLA V", "HI", "W3", "L3"),
        ("WIRELINE UNIT 7", "GC", "W4", "L4"),
        ("COIL TUBING ALPHA", "MC", "W5", "L5"),
        ("LIFT BOAT 99", "ST", "W6", "L6"),
        ("SNUBBING UNIT 3", "EI", "W7", "L7"),
        ("WORKOVER RIG 12", "SP", "W8", "L8"),
    ]
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
    months = [1, 3, 6, 9, 11]
    idx = 0
    for year in years:
        for rig_name, area, wp, lp in rig_configs:
            for month in months[:3]:  # 3 records per rig per year
                rows.append(
                    {
                        "RIG_NAME": rig_name,
                        "WAR_START_DT": f"{month}/15/{year}",
                        "WAR_END_DT": f"{month}/28/{year}",
                        "API_WELL_NUMBER": f"{wp}{idx:04d}",
                        "BOTM_LEASE_NUM": f"{lp}{idx % 5:02d}",
                        "AREA_CODE": area,
                        "BUS_ASC_NAME": f"OPERATOR {idx % 6}",
                    }
                )
                idx += 1
    return pd.DataFrame(rows)


def _make_fleet_df() -> pd.DataFrame:
    """Synthetic fleet DataFrame with known rig types."""
    return pd.DataFrame(
        {
            "RIG_NAME": [
                "ROWAN GORILLA V",
                "WIRELINE UNIT 7",
                "SOME OTHER RIG",
            ],
            "RIG_TYPE": [
                "jack_up",
                "wireline_unit",
                "platform_rig",
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
# Test: dashboard generates an HTML file
# ---------------------------------------------------------------------------


class TestDashboardGeneratesHtml:
    """Verify generate() produces a valid HTML file."""

    def test_dashboard_generates_html_file(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        dashboard = InterventionDashboard(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_dashboard.html")
            result_path = dashboard.generate(output_path)

            assert result_path == output_path
            assert Path(result_path).exists()
            assert Path(result_path).stat().st_size > 0

    def test_dashboard_html_references_plotly(self) -> None:
        """HTML should reference plotly.js (CDN or inline)."""
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        dashboard = InterventionDashboard(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_dashboard.html")
            dashboard.generate(output_path)

            content = Path(output_path).read_text()
            assert "plotly" in content.lower()


# ---------------------------------------------------------------------------
# Test: report contains expected section titles
# ---------------------------------------------------------------------------


class TestDashboardContainsExpectedSections:
    """Verify the HTML contains all 10 expected section titles."""

    def test_dashboard_contains_expected_section_titles(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        dashboard = InterventionDashboard(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_dashboard.html")
            dashboard.generate(output_path)
            content = Path(output_path).read_text()

            expected_titles = [
                "Executive Summary",
                "Market Structure",
                "Service Line Analysis",
                "Operator",
                "Equipment",
                "Contact Intelligence",
                "Geographic Market Intelligence",
                "Addressable Market",
                "Engineering Marketing Services Opportunities",
                "Methodology",
            ]
            for title in expected_titles:
                assert title in content, (
                    f"Expected section title '{title}' not found in report HTML"
                )

    def test_dashboard_contains_expected_chart_titles(self) -> None:
        """Charts from the original dashboard should still appear."""
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        dashboard = InterventionDashboard(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_dashboard.html")
            dashboard.generate(output_path)
            content = Path(output_path).read_text()

            expected_titles = [
                "GOM Has Become an Intervention Basin",
                "Intervention-to-Drilling Ratio",
                "Intervention Activity by Service Type",
                "Service Type Growth",
                "Top Operators",
                "Addressable Market",
                "Seasonal Intervention Activity",
                "Intervention Activity by GOM Area",
            ]
            for title in expected_titles:
                assert title in content, (
                    f"Expected chart title '{title}' not found in report HTML"
                )


# ---------------------------------------------------------------------------
# Test: report contains data tables and reference content
# ---------------------------------------------------------------------------


class TestDashboardContainsTablesAndReferences:
    """Verify the HTML contains data tables and reference sections."""

    def test_report_contains_data_tables(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        dashboard = InterventionDashboard(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_dashboard.html")
            dashboard.generate(output_path)
            content = Path(output_path).read_text()

            assert "data-table" in content
            assert "<table" in content
            assert "<thead" in content

    def test_report_contains_service_type_reference(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        dashboard = InterventionDashboard(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_dashboard.html")
            dashboard.generate(output_path)
            content = Path(output_path).read_text()

            assert "Wireline Unit" in content
            assert "Coil Tubing Unit" in content
            assert "Lift Boat" in content

    def test_report_contains_area_reference(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        dashboard = InterventionDashboard(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_dashboard.html")
            dashboard.generate(output_path)
            content = Path(output_path).read_text()

            assert "Eugene Island" in content
            assert "Mississippi Canyon" in content
            assert "Green Canyon" in content

    def test_report_contains_table_of_contents(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        dashboard = InterventionDashboard(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_dashboard.html")
            dashboard.generate(output_path)
            content = Path(output_path).read_text()

            assert "Table of Contents" in content
            assert "section-1" in content


# ---------------------------------------------------------------------------
# Test: dashboard handles empty data gracefully
# ---------------------------------------------------------------------------


class TestDashboardHandlesEmptyData:
    """Empty WAR DataFrame should not crash the dashboard generation."""

    def test_dashboard_handles_empty_data(self) -> None:
        war_df = _make_empty_war_df()
        fleet_df = _make_fleet_df()
        dashboard = InterventionDashboard(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test_empty.html")
            result_path = dashboard.generate(output_path)

            assert result_path == output_path
            assert Path(result_path).exists()


# ---------------------------------------------------------------------------
# Test: output directory creation
# ---------------------------------------------------------------------------


class TestOutputDirectoryCreation:
    """Generate should create output directories if they don't exist."""

    def test_creates_output_directory(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        dashboard = InterventionDashboard(war_df, fleet_df)

        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = str(
                Path(tmpdir) / "sub" / "dir" / "dashboard.html"
            )
            result_path = dashboard.generate(nested_path)

            assert Path(result_path).exists()
