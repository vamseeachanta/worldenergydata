"""
ABOUTME: Tests for the BSEE field pipeline skill wrapper (TDD red phase first).
ABOUTME: Verifies bsee_field_pipeline(field_name) -> BseeFieldResult contract.
"""

from __future__ import annotations

import pytest
import pandas as pd


# ---------------------------------------------------------------------------
# Import the skill (will fail until implementation is created — TDD red phase)
# ---------------------------------------------------------------------------

from worldenergydata.bsee.skill import SKILL_NAME, BseeFieldResult, bsee_field_pipeline


# ---------------------------------------------------------------------------
# Tests: Module-level constants
# ---------------------------------------------------------------------------

class TestSkillConstants:
    def test_skill_name_value(self):
        """SKILL_NAME must equal the canonical skill identifier."""
        assert SKILL_NAME == "bsee_field_pipeline"

    def test_skill_name_is_string(self):
        """SKILL_NAME must be a plain string."""
        assert isinstance(SKILL_NAME, str)


# ---------------------------------------------------------------------------
# Tests: BseeFieldResult type
# ---------------------------------------------------------------------------

class TestBseeFieldResultType:
    def test_result_is_dataclass_or_class(self):
        """BseeFieldResult can be instantiated as a data container."""
        result = bsee_field_pipeline("Atlantis")
        assert isinstance(result, BseeFieldResult)

    def test_result_has_field_name(self):
        """Result must expose .field_name attribute."""
        result = bsee_field_pipeline("Atlantis")
        assert hasattr(result, "field_name")
        assert isinstance(result.field_name, str)

    def test_result_has_operator(self):
        """Result must expose .operator attribute."""
        result = bsee_field_pipeline("Atlantis")
        assert hasattr(result, "operator")
        assert isinstance(result.operator, str)

    def test_result_has_data(self):
        """Result must expose .data as a pandas DataFrame."""
        result = bsee_field_pipeline("Atlantis")
        assert hasattr(result, "data")
        assert isinstance(result.data, pd.DataFrame)

    def test_result_has_summary(self):
        """Result must expose .summary as a dict."""
        result = bsee_field_pipeline("Atlantis")
        assert hasattr(result, "summary")
        assert isinstance(result.summary, dict)

    def test_result_has_source(self):
        """Result must expose .source attribute."""
        result = bsee_field_pipeline("Atlantis")
        assert hasattr(result, "source")
        assert result.source == "bsee"


# ---------------------------------------------------------------------------
# Tests: field_name passthrough
# ---------------------------------------------------------------------------

class TestFieldNamePassthrough:
    def test_field_name_preserved(self):
        """result.field_name must match the input (case-normalized)."""
        result = bsee_field_pipeline("Atlantis")
        assert result.field_name.upper() == "ATLANTIS"

    def test_field_name_thunder_horse(self):
        """Pipeline works for Thunder Horse field."""
        result = bsee_field_pipeline("Thunder Horse")
        assert "THUNDER" in result.field_name.upper() or "HORSE" in result.field_name.upper()

    def test_field_name_mars(self):
        """Pipeline works for Mars field."""
        result = bsee_field_pipeline("Mars")
        assert isinstance(result, BseeFieldResult)
        assert result.field_name  # non-empty


# ---------------------------------------------------------------------------
# Tests: data DataFrame structure
# ---------------------------------------------------------------------------

class TestDataFrame:
    def test_data_is_dataframe(self):
        """data attribute must be a pandas DataFrame."""
        result = bsee_field_pipeline("Atlantis")
        assert isinstance(result.data, pd.DataFrame)

    def test_data_has_year_column(self):
        """DataFrame must include a year column."""
        result = bsee_field_pipeline("Atlantis")
        assert "year" in result.data.columns

    def test_data_has_month_column(self):
        """DataFrame must include a month column."""
        result = bsee_field_pipeline("Atlantis")
        assert "month" in result.data.columns

    def test_data_has_oil_column(self):
        """DataFrame must include oil_bbl column."""
        result = bsee_field_pipeline("Atlantis")
        assert "oil_bbl" in result.data.columns

    def test_data_has_gas_column(self):
        """DataFrame must include gas_mcf column."""
        result = bsee_field_pipeline("Atlantis")
        assert "gas_mcf" in result.data.columns

    def test_data_has_water_column(self):
        """DataFrame must include water_bbl column."""
        result = bsee_field_pipeline("Atlantis")
        assert "water_bbl" in result.data.columns

    def test_data_not_empty(self):
        """Synthetic data must have at least one row."""
        result = bsee_field_pipeline("Atlantis")
        assert len(result.data) > 0


# ---------------------------------------------------------------------------
# Tests: summary dict structure
# ---------------------------------------------------------------------------

class TestSummaryDict:
    def test_summary_has_peak_oil(self):
        """summary must contain peak_oil_bbl key."""
        result = bsee_field_pipeline("Atlantis")
        assert "peak_oil_bbl" in result.summary

    def test_summary_has_cumulative_oil(self):
        """summary must contain cumulative_oil_bbl key."""
        result = bsee_field_pipeline("Atlantis")
        assert "cumulative_oil_bbl" in result.summary

    def test_summary_has_decline_rate(self):
        """summary must contain decline_rate_pct key."""
        result = bsee_field_pipeline("Atlantis")
        assert "decline_rate_pct" in result.summary

    def test_summary_has_first_date(self):
        """summary must contain first_date key."""
        result = bsee_field_pipeline("Atlantis")
        assert "first_date" in result.summary

    def test_summary_has_last_date(self):
        """summary must contain last_date key."""
        result = bsee_field_pipeline("Atlantis")
        assert "last_date" in result.summary

    def test_summary_peak_oil_numeric(self):
        """peak_oil_bbl must be a numeric value."""
        result = bsee_field_pipeline("Atlantis")
        assert isinstance(result.summary["peak_oil_bbl"], (int, float))

    def test_summary_cumulative_oil_positive(self):
        """cumulative_oil_bbl must be >= 0."""
        result = bsee_field_pipeline("Atlantis")
        assert result.summary["cumulative_oil_bbl"] >= 0


# ---------------------------------------------------------------------------
# Tests: optional kwargs
# ---------------------------------------------------------------------------

class TestOptionalKwargs:
    def test_parameters_subset_oil_only(self):
        """Passing parameters=['oil_bbl'] returns DataFrame with oil_bbl column."""
        result = bsee_field_pipeline("Atlantis", parameters=["oil_bbl"])
        assert "oil_bbl" in result.data.columns

    def test_start_date_kwarg_accepted(self):
        """Passing start='2010-01' does not raise."""
        result = bsee_field_pipeline("Atlantis", start="2010-01")
        assert isinstance(result, BseeFieldResult)

    def test_end_date_kwarg_accepted(self):
        """Passing end='2020-12' does not raise."""
        result = bsee_field_pipeline("Atlantis", end="2020-12")
        assert isinstance(result, BseeFieldResult)

    def test_start_and_end_together(self):
        """start + end together do not raise."""
        result = bsee_field_pipeline("Atlantis", start="2005-01", end="2015-12")
        assert isinstance(result, BseeFieldResult)


# ---------------------------------------------------------------------------
# Tests: export from worldenergydata.bsee
# ---------------------------------------------------------------------------

class TestPackageExport:
    def test_bsee_field_pipeline_importable_from_bsee(self):
        """bsee_field_pipeline must be importable from worldenergydata.bsee."""
        from worldenergydata.bsee import bsee_field_pipeline as fn
        assert callable(fn)

    def test_bsee_field_result_importable_from_bsee(self):
        """BseeFieldResult must be importable from worldenergydata.bsee."""
        from worldenergydata.bsee import BseeFieldResult as cls
        assert cls is not None
