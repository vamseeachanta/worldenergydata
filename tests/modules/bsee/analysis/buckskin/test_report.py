"""Tests for BuckskinReport — HTML report generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Shared fixtures (same synthetic data as test_analyzer.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
def production_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": ["A", "A", "B", "B", "C"],
            "BOTM_AREA_CODE": ["KC"] * 5,
            "BOTM_BLOCK_NUM": [785, 785, 829, 829, 872],
            "PROD_YEAR": [2019, 2020, 2020, 2021, 2021],
            "MON_O_PROD_VOL": [500_000, 1_200_000, 600_000, 400_000, 700_000],
            "MON_G_PROD_VOL": [250_000, 600_000, 300_000, 200_000, 350_000],
            "MON_WTR_PROD_VOL": [50_000, 120_000, 60_000, 40_000, 70_000],
        }
    )


@pytest.fixture()
def wells_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": ["A", "B", "C"],
            "WELL_NAME": ["WELL-A", "WELL-B", "WELL-C"],
            "BOTM_AREA_CODE": ["KC"] * 3,
            "BOTM_BLOCK_NUM": [785, 829, 872],
            "WATER_DEPTH": [6800.0, 6900.0, 6850.0],
            "WELL_SPUD_DATE": ["2009-04-15", "2015-07-22", "2017-11-03"],
            "WELL_TYPE_CODE": ["D", "D", "E"],
        }
    )


@pytest.fixture()
def buckskin_data(production_df, wells_df) -> dict[str, pd.DataFrame]:
    return {
        "production": production_df,
        "wells": wells_df,
        "war_activity": pd.DataFrame(),
        "leases": pd.DataFrame(),
        "completions": pd.DataFrame(),
    }


# ---------------------------------------------------------------------------
# Basic report generation
# ---------------------------------------------------------------------------


class TestGenerateHTML:
    """Tests for BuckskinReport.generate_html()."""

    def test_generates_html_file(self, buckskin_data, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        report = BuckskinReport(analyzer)
        out = report.generate_html(tmp_path / "report.html")

        assert out.exists()
        html = out.read_text()
        assert "<html" in html
        assert "Buckskin" in html

    def test_html_contains_production_section(self, buckskin_data, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        report = BuckskinReport(analyzer)
        out = report.generate_html(tmp_path / "report.html")
        html = out.read_text()

        assert "Production Summary" in html
        assert "MMBBL" in html

    def test_html_contains_boem_lease_table(self, buckskin_data, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        report = BuckskinReport(analyzer)
        out = report.generate_html(tmp_path / "report.html")
        html = out.read_text()

        assert "BOEM OCS Lease Mapping" in html
        assert "OCS-G 25806" in html
        assert "OCS-G 25823" in html

    def test_html_contains_well_count_chart(self, buckskin_data, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        report = BuckskinReport(analyzer)
        out = report.generate_html(tmp_path / "report.html")
        html = out.read_text()

        assert "Well Count Over Time" in html

    def test_html_contains_benchmark_section(self, buckskin_data, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        report = BuckskinReport(analyzer)
        out = report.generate_html(tmp_path / "report.html")
        html = out.read_text()

        assert "Benchmark Validation" in html
        assert "2019" in html

    def test_html_contains_wellbore_inventory(self, buckskin_data, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        report = BuckskinReport(analyzer)
        out = report.generate_html(tmp_path / "report.html")
        html = out.read_text()

        assert "Wellbore Inventory" in html
        assert "WELL-A" in html

    def test_html_contains_operator_history(self, buckskin_data, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        report = BuckskinReport(analyzer)
        out = report.generate_html(tmp_path / "report.html")
        html = out.read_text()

        assert "Operator History" in html
        assert "LLOG" in html
        assert "Harbour Energy" in html

    def test_html_contains_lower_tertiary(self, buckskin_data, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        report = BuckskinReport(analyzer)
        out = report.generate_html(tmp_path / "report.html")
        html = out.read_text()

        assert "Lower Tertiary" in html
        assert "Wilcox" in html

    def test_html_contains_buckskin_south(self, buckskin_data, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        report = BuckskinReport(analyzer)
        out = report.generate_html(tmp_path / "report.html")
        html = out.read_text()

        assert "Buckskin South" in html


# ---------------------------------------------------------------------------
# Empty data edge case
# ---------------------------------------------------------------------------


class TestEmptyDataReport:
    """Report generation with empty DataFrames."""

    def test_empty_data_still_generates(self, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        empty = {k: pd.DataFrame() for k in
                 ("production", "wells", "war_activity", "leases", "completions")}
        analyzer = BuckskinAnalyzer(data=empty)
        report = BuckskinReport(analyzer)
        out = report.generate_html(tmp_path / "empty_report.html")

        assert out.exists()
        html = out.read_text()
        assert "Buckskin" in html
        assert "No data" in html  # wellbore section shows "No data"


# ---------------------------------------------------------------------------
# Decline curve section
# ---------------------------------------------------------------------------


class TestDeclineCurveSection:
    """Tests for the decline curve report section."""

    def test_decline_section_absent_when_none(self, buckskin_data, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        report = BuckskinReport(analyzer)
        out = report.generate_html(tmp_path / "r.html", decline_results=None)
        html = out.read_text()

        assert "Decline Curve Analysis" not in html

    def test_decline_section_present_with_results(self, buckskin_data, tmp_path):
        from worldenergydata.bsee.analysis.buckskin.analyzer import BuckskinAnalyzer
        from worldenergydata.bsee.analysis.buckskin.report import BuckskinReport

        # Build a minimal mock decline_results dict
        from unittest.mock import MagicMock

        mock_curve = MagicMock()
        mock_curve.initial_rate = 50000
        mock_curve.decline_rate = 0.05
        mock_curve.b_factor = 0.0
        mock_curve.r_squared = 0.95
        mock_curve.rmse = 500
        mock_curve.model_type = "exponential"

        mock_fit = MagicMock()
        mock_fit.curve = mock_curve
        mock_fit.aic = 100.0

        mock_comparison = MagicMock()
        mock_comparison.best_model = "exponential"
        mock_comparison.best_fit = mock_fit
        mock_comparison.fits = {"exponential": mock_fit}

        mock_forecast = MagicMock()
        mock_forecast.forecast_values = [40000, 38000, 36100]

        decline_results = {
            "comparison": mock_comparison,
            "forecast": mock_forecast,
            "eur": {"exponential": 500_000},
        }

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        report = BuckskinReport(analyzer)
        out = report.generate_html(
            tmp_path / "r.html", decline_results=decline_results,
        )
        html = out.read_text()

        assert "Decline Curve Analysis" in html
        assert "exponential" in html
        assert "EUR" in html
