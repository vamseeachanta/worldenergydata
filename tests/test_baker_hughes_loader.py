# ABOUTME: TDD tests for Baker Hughes rig count loader (WRK-1190).
# ABOUTME: Tests pivot table and summary Excel parsing into standardized DataFrames.

"""Tests for Baker Hughes rig count data loader."""

from pathlib import Path

import pandas as pd

FIXTURES = Path(__file__).parent / "fixtures" / "baker_hughes"


class TestPivotTableLoader:
    """Tests for pivot table Excel parsing."""

    def test_load_pivot_returns_dataframe(self):
        from worldenergydata.baker_hughes.loader import load_pivot_table

        df = load_pivot_table(FIXTURES / "na_pivot_sample.xlsx")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_pivot_standardized_columns(self):
        from worldenergydata.baker_hughes.loader import load_pivot_table

        df = load_pivot_table(FIXTURES / "na_pivot_sample.xlsx")
        expected_cols = {
            "date",
            "country",
            "state",
            "county",
            "basin",
            "drill_for",
            "location",
            "trajectory",
            "well_type",
            "well_depth_ft",
            "water_depth_ft",
            "rig_count",
        }
        assert set(df.columns) == expected_cols

    def test_pivot_date_parsed(self):
        from worldenergydata.baker_hughes.loader import load_pivot_table

        df = load_pivot_table(FIXTURES / "na_pivot_sample.xlsx")
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_pivot_rig_count_is_numeric(self):
        from worldenergydata.baker_hughes.loader import load_pivot_table

        df = load_pivot_table(FIXTURES / "na_pivot_sample.xlsx")
        assert pd.api.types.is_numeric_dtype(df["rig_count"])

    def test_pivot_filters_by_country(self):
        from worldenergydata.baker_hughes.loader import load_pivot_table

        df = load_pivot_table(
            FIXTURES / "na_pivot_sample.xlsx", country="UNITED STATES"
        )
        assert (df["country"] == "UNITED STATES").all()
        # Fixture has 1 Canada row, should be excluded
        assert len(df) == 7

    def test_pivot_filters_by_basin(self):
        from worldenergydata.baker_hughes.loader import load_pivot_table

        df = load_pivot_table(FIXTURES / "na_pivot_sample.xlsx", basin="PERMIAN")
        assert (df["basin"] == "PERMIAN").all()

    def test_pivot_depth_columns_numeric(self):
        from worldenergydata.baker_hughes.loader import load_pivot_table

        df = load_pivot_table(FIXTURES / "na_pivot_sample.xlsx")
        assert pd.api.types.is_numeric_dtype(df["well_depth_ft"])
        # water_depth_ft should be numeric (NaN for land wells)
        assert pd.api.types.is_numeric_dtype(df["water_depth_ft"])


class TestSummaryLoader:
    """Tests for summary (rigs by state) Excel parsing."""

    def test_load_summary_returns_dataframe(self):
        from worldenergydata.baker_hughes.loader import load_summary

        df = load_summary(FIXTURES / "na_summary_sample.xlsx")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_summary_long_format(self):
        """Summary should be melted from wide to long format."""
        from worldenergydata.baker_hughes.loader import load_summary

        df = load_summary(FIXTURES / "na_summary_sample.xlsx")
        expected_cols = {"state", "date", "rig_count"}
        assert set(df.columns) == expected_cols

    def test_summary_date_parsed(self):
        from worldenergydata.baker_hughes.loader import load_summary

        df = load_summary(FIXTURES / "na_summary_sample.xlsx")
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_summary_row_count(self):
        """6 states x 3 dates = 18 rows in long format."""
        from worldenergydata.baker_hughes.loader import load_summary

        df = load_summary(FIXTURES / "na_summary_sample.xlsx")
        assert len(df) == 18

    def test_summary_texas_count(self):
        from worldenergydata.baker_hughes.loader import load_summary

        df = load_summary(FIXTURES / "na_summary_sample.xlsx")
        texas = df[df["state"] == "TEXAS"]
        assert len(texas) == 3
        assert 279 in texas["rig_count"].values


class TestIngestionReport:
    """Tests for YAML ingestion report generation."""

    def test_generate_report_from_pivot(self):
        from worldenergydata.baker_hughes.loader import load_pivot_table
        from worldenergydata.baker_hughes.report import generate_report

        df = load_pivot_table(FIXTURES / "na_pivot_sample.xlsx")
        report = generate_report(df, source="pivot")
        assert report["source"] == "pivot"
        assert report["record_count"] == len(df)
        assert "date_range" in report
        assert "min" in report["date_range"]
        assert "max" in report["date_range"]
        assert "basins" in report
        assert "states" in report
