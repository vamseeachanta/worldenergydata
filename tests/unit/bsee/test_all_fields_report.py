"""Unit tests for the all_fields_report module."""

from pathlib import Path

import pandas as pd
import pytest

from tests.test_markers import unit


def _make_result_df():
    """Create sample AllFieldsRunner result DataFrame."""
    return pd.DataFrame(
        {
            "FIELD_CODE": ["100", "200", "300", "400"],
            "FIELD_NAME": ["Thunder Horse", "Mars", "Atlantis", "Auger"],
            "GEOLOGICAL_ERA": ["Miocene", "Miocene", "Eocene", "Pliocene"],
            "WATER_DEPTH_AVG": [6300.0, 2940.0, 7070.0, 2860.0],
            "WELL_COUNT": [25, 60, 10, 40],
            "FIRST_PRODUCTION": [2008, 1996, 2007, 1994],
            "LAST_PRODUCTION": [2023, 2023, 2023, 2023],
            "CUM_OIL_MMBBL": [350.0, 900.0, 180.0, 500.0],
            "CUM_GAS_BCF": [200.0, 600.0, 100.0, 400.0],
            "CUM_WATER_MMBBL": [50.0, 200.0, 30.0, 100.0],
            "PEAK_OIL_BOPD": [80000.0, 120000.0, 50000.0, 90000.0],
            "REC_PER_WELL_MMBBL": [14.0, 15.0, 18.0, 12.5],
            "AVG_BOPD_PER_WELL": [10000.0, 8000.0, 12000.0, 9000.0],
            "PROD_SPAN_YRS": [16, 28, 17, 30],
            "WOR_CUM": [0.14, 0.22, 0.17, 0.20],
            "PEAK_TO_CUM": [0.08, 0.05, 0.10, 0.07],
            "N_OPERATORS": [2, 1, 1, 3],
            "TOP_OPERATOR_SHARE": [0.9, 1.0, 1.0, 0.6],
            "DOMINANT_OPERATOR": ["BP", "Shell", "BP", "Shell"],
            "STILL_PRODUCING": [False, False, False, False],
            "NPV10_MM_USD": [None, None, None, None],
            "IRR_PCT": [None, None, None, None],
            "PAYBACK_YRS": [None, None, None, None],
        }
    )


@unit
class TestAllFieldsReport:
    """Tests for AllFieldsReport class."""

    @pytest.fixture
    def report_df(self):
        return _make_result_df()

    @pytest.fixture
    def report(self, report_df):
        from worldenergydata.bsee.reports.all_fields_report import (
            AllFieldsReport,
        )

        return AllFieldsReport(report_df)

    def test_init(self, report_df):
        """Test report initialization."""
        from worldenergydata.bsee.reports.all_fields_report import (
            AllFieldsReport,
        )

        rpt = AllFieldsReport(report_df)
        assert rpt._df is not None
        assert len(rpt._df) == 4

    def test_generate_markdown(self, report, tmp_path):
        """Test markdown report generation."""
        output = tmp_path / "report.md"
        report.generate_markdown(output)

        assert output.exists()
        content = output.read_text()
        assert "# BSEE All-Fields Analysis" in content
        assert "Thunder Horse" in content
        assert "Mars" in content
        assert "Miocene" in content

    def test_markdown_has_era_grouping(self, report, tmp_path):
        """Test markdown report groups by geological era."""
        output = tmp_path / "report.md"
        report.generate_markdown(output)

        content = output.read_text()
        assert "Miocene" in content
        assert "Eocene" in content
        assert "Pliocene" in content

    def test_markdown_has_executive_summary(self, report, tmp_path):
        """Test markdown report has executive summary section."""
        output = tmp_path / "report.md"
        report.generate_markdown(output)

        content = output.read_text()
        assert "Summary" in content
        assert "4" in content  # total fields

    def test_generate_csv(self, report, tmp_path):
        """Test CSV export."""
        output = tmp_path / "report.csv"
        report.generate_csv(output)

        assert output.exists()
        df = pd.read_csv(output)
        assert len(df) == 4
        assert "FIELD_CODE" in df.columns
        assert "FIELD_NAME" in df.columns
        assert "CUM_OIL_MMBBL" in df.columns

    def test_csv_sorted_by_oil(self, report, tmp_path):
        """Test CSV is sorted by cumulative oil descending."""
        output = tmp_path / "report.csv"
        report.generate_csv(output)

        df = pd.read_csv(output)
        assert df.iloc[0]["FIELD_NAME"] == "Mars"  # highest CUM_OIL

    def test_generate_html(self, report, tmp_path):
        """Test HTML dashboard generation."""
        output = tmp_path / "dashboard.html"
        report.generate_html(output)

        assert output.exists()
        content = output.read_text()
        assert "<html" in content.lower() or "plotly" in content.lower()

    def test_get_era_summary(self, report):
        """Test era summary statistics."""
        summary = report.get_era_summary()

        assert isinstance(summary, pd.DataFrame)
        assert len(summary) == 3  # Miocene, Eocene, Pliocene
        assert "FIELD_COUNT" in summary.columns
        assert "TOTAL_OIL_MMBBL" in summary.columns

    def test_era_summary_sorted_by_production(self, report):
        """Test era summary is sorted by total production."""
        summary = report.get_era_summary()
        # Miocene fields have most oil (350 + 900 = 1250)
        assert summary.iloc[0].name == "Miocene"

    def test_operator_concentration_hhi(self, report):
        """HHI / shares from dominant-operator oil totals."""
        conc = report.get_operator_concentration()
        # Shell oil = 900+500 = 1400; BP oil = 350+180 = 530; total = 1930.
        total = 1930.0
        shell, bp = 1400.0 / total, 530.0 / total
        assert conc["n_operators"] == 2
        assert conc["top1_share"] == pytest.approx(shell, abs=1e-3)
        assert conc["top5_share"] == pytest.approx(1.0, abs=1e-3)
        assert conc["hhi"] == pytest.approx(shell**2 + bp**2, abs=1e-3)
        assert conc["operator_oil"]["Shell"] == pytest.approx(1400.0)
        assert conc["operator_oil"]["BP"] == pytest.approx(530.0)

    def test_operator_concentration_empty(self):
        from worldenergydata.bsee.reports.all_fields_report import (
            AllFieldsReport,
        )

        rpt = AllFieldsReport(pd.DataFrame(columns=["FIELD_CODE"]))
        conc = rpt.get_operator_concentration()
        assert conc["hhi"] is None
        assert conc["operator_oil"] == {}

    def test_markdown_has_operator_section_and_columns(self, report, tmp_path):
        output = tmp_path / "report.md"
        report.generate_markdown(output)
        content = output.read_text()
        assert "Operator Concentration" in content
        assert "Basin HHI" in content
        assert "Rec/Well" in content
        assert "BOPD/Well" in content

    def test_empty_dataframe(self, tmp_path):
        """Test report generation with empty data."""
        from worldenergydata.bsee.reports.all_fields_report import (
            AllFieldsReport,
        )

        empty_df = pd.DataFrame(
            columns=[
                "FIELD_CODE",
                "FIELD_NAME",
                "GEOLOGICAL_ERA",
                "CUM_OIL_MMBBL",
                "CUM_GAS_BCF",
            ]
        )
        rpt = AllFieldsReport(empty_df)

        md_out = tmp_path / "report.md"
        rpt.generate_markdown(md_out)
        assert md_out.exists()

        csv_out = tmp_path / "report.csv"
        rpt.generate_csv(csv_out)
        assert csv_out.exists()
