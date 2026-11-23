"""Unit tests for AllFieldsReport HTML enrichment (access/concentration)."""

import numpy as np
import pandas as pd

from tests.test_markers import unit


def _make_result_df():
    """Per-field result frame with the enriched atlas columns."""
    return pd.DataFrame(
        {
            "FIELD_CODE": ["100", "200", "300", "400", "500", "600"],
            "FIELD_NAME": [
                "Thunder Horse",
                "Mars",
                "Cascade",
                "Auger",
                "Stones",
                "Shelf Field",
            ],
            "GEOLOGICAL_ERA": [
                "Miocene",
                "Miocene",
                "Paleocene",
                "Pliocene",
                "Paleocene",
                "Pleistocene",
            ],
            "IS_LOWER_TERTIARY": [False, False, True, False, True, False],
            "WATER_DEPTH_AVG": [6300.0, 2940.0, 8200.0, 2860.0, 9500.0, 300.0],
            "WELL_COUNT": [25, 60, 5, 40, 4, 12],
            "FIRST_PRODUCTION": [2008, 1996, 2012, 1994, 2016, 1998],
            "CUM_OIL_MMBBL": [350.0, 900.0, 60.0, 500.0, 45.0, 20.0],
            "CUM_GAS_BCF": [200.0, 600.0, 30.0, 400.0, 25.0, 15.0],
            "PEAK_OIL_BOPD": [80000.0, 120000.0, 20000.0, 90000.0, 18000.0, 5000.0],
            "REC_PER_WELL_MMBBL": [14.0, 15.0, 12.0, 12.5, 11.25, 1.7],
            "AVG_BOPD_PER_WELL": [10000.0, 8000.0, 7000.0, 9000.0, 6500.0, 1500.0],
            "PROD_SPAN_YRS": [16, 28, 10, 30, 8, 25],
            "WOR_CUM": [0.14, 0.22, 0.12, 0.20, 0.10, 0.40],
            "N_OPERATORS": [2, 1, 1, 3, 1, 2],
            "TOP_OPERATOR_SHARE": [0.9, 1.0, 1.0, 0.6, 1.0, 0.8],
            "DOMINANT_OPERATOR": ["BP", "Shell", "Chevron", "Shell", "Shell", "BP"],
            "STILL_PRODUCING": [False, False, True, False, True, False],
            "NPV10_MM_USD": [None] * 6,
            "IRR_PCT": [None] * 6,
            "PAYBACK_YRS": [None] * 6,
        }
    )


@unit
class TestAllFieldsReportHtmlEnrichment:
    def _report(self):
        from worldenergydata.bsee.reports.all_fields_report import AllFieldsReport

        return AllFieldsReport(_make_result_df())

    def test_html_has_new_section_titles(self, tmp_path):
        out = tmp_path / "dash.html"
        self._report().generate_html(out)
        content = out.read_text()
        # Headline access/concentration scatter
        assert "Recovery per Well vs Water Depth" in content
        # Recovery per well by era cohort
        assert "Median Recovery per Well by Geological Era" in content
        # Water depth distribution
        assert "Water Depth" in content

    def test_html_has_header_and_footnote(self, tmp_path):
        out = tmp_path / "dash.html"
        self._report().generate_html(out)
        content = out.read_text()
        assert "BSEE OGOR-A" in content
        assert "1996" in content and "2025" in content
        # Honest caveat footnote
        assert "composite proxy" in content
        assert "subsea" in content.lower()

    def test_html_keeps_existing_charts(self, tmp_path):
        out = tmp_path / "dash.html"
        self._report().generate_html(out)
        content = out.read_text()
        assert "Top 15 Fields by Cumulative Oil Production" in content
        assert "Cumulative Oil Production by Geological Era" in content
        assert "Top 10 Operators by Cumulative Oil Production" in content

    def test_html_well_formed(self, tmp_path):
        out = tmp_path / "dash.html"
        self._report().generate_html(out)
        content = out.read_text()
        assert "<html" in content.lower()
        assert "</html>" in content.lower()

    def test_html_empty_dataframe(self, tmp_path):
        from worldenergydata.bsee.reports.all_fields_report import AllFieldsReport

        empty = pd.DataFrame(
            columns=[
                "FIELD_CODE",
                "FIELD_NAME",
                "GEOLOGICAL_ERA",
                "IS_LOWER_TERTIARY",
                "WATER_DEPTH_AVG",
                "WELL_COUNT",
                "CUM_OIL_MMBBL",
                "CUM_GAS_BCF",
                "REC_PER_WELL_MMBBL",
                "AVG_BOPD_PER_WELL",
                "DOMINANT_OPERATOR",
            ]
        )
        out = tmp_path / "dash.html"
        AllFieldsReport(empty).generate_html(out)
        assert out.exists()

    def test_html_handles_all_null_water_depth(self, tmp_path):
        from worldenergydata.bsee.reports.all_fields_report import AllFieldsReport

        df = _make_result_df()
        df["WATER_DEPTH_AVG"] = np.nan
        out = tmp_path / "dash.html"
        AllFieldsReport(df).generate_html(out)
        assert out.exists()
