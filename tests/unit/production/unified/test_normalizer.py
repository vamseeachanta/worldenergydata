"""Tests for Normalizer — schema validation, normalization, and gap detection."""

import pandas as pd
import pytest

from worldenergydata.production.unified.normalizer import Normalizer
from worldenergydata.production.unified.query import STANDARD_COLUMNS


def _make_df(**overrides):
    """Build a minimal valid production DataFrame."""
    base = {
        "region": ["ncs", "ncs"],
        "field_name": ["Edvard Grieg", "Edvard Grieg"],
        "year": [2020, 2020],
        "month": [1, 2],
        "oil_bbl": [5_800_000.0, 5_600_000.0],
        "gas_mcf": [2_100_000.0, 2_050_000.0],
        "water_bbl": [420_000.0, 440_000.0],
        "condensate_bbl": [180_000.0, 175_000.0],
        "source": ["sodir_mock", "sodir_mock"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


class TestNormalizerValidate:
    def test_validate_passes_complete_df(self):
        normalizer = Normalizer()
        df = _make_df()
        normalizer.validate(df)  # should not raise

    def test_validate_raises_on_missing_column(self):
        normalizer = Normalizer()
        df = _make_df()
        df = df.drop(columns=["oil_bbl"])
        with pytest.raises(ValueError, match="oil_bbl"):
            normalizer.validate(df)

    def test_validate_raises_on_multiple_missing(self):
        normalizer = Normalizer()
        df = _make_df()
        df = df.drop(columns=["oil_bbl", "gas_mcf"])
        with pytest.raises(ValueError):
            normalizer.validate(df)


class TestNormalizerNormalize:
    def test_normalize_casts_numerics(self):
        normalizer = Normalizer()
        df = _make_df(oil_bbl=["5800000", "5600000"])
        out = normalizer.normalize(df)
        assert out["oil_bbl"].dtype == "float64"

    def test_normalize_sorts_by_region_field_year_month(self):
        normalizer = Normalizer()
        df = _make_df()
        # Shuffle order
        df = df.iloc[::-1].reset_index(drop=True)
        out = normalizer.normalize(df)
        assert out.iloc[0]["month"] == 1
        assert out.iloc[1]["month"] == 2

    def test_normalize_empty_df_returns_empty(self):
        normalizer = Normalizer()
        df = pd.DataFrame(columns=list(STANDARD_COLUMNS))
        out = normalizer.normalize(df)
        assert out.empty

    def test_normalize_does_not_mutate_input(self):
        normalizer = Normalizer()
        df = _make_df(oil_bbl=["5800000", "5600000"])
        original_dtype = df["oil_bbl"].dtype
        normalizer.normalize(df)
        assert df["oil_bbl"].dtype == original_dtype


class TestNormalizerSummary:
    def test_build_summary_peak_rate(self):
        normalizer = Normalizer()
        df = _make_df()
        summary = normalizer.build_summary(df)
        assert summary.iloc[0]["peak_rate"] == 5_800_000.0

    def test_build_summary_cumulative(self):
        normalizer = Normalizer()
        df = _make_df()
        summary = normalizer.build_summary(df)
        assert summary.iloc[0]["cumulative_oil_bbl"] == 5_800_000.0 + 5_600_000.0

    def test_build_summary_empty_input_returns_empty(self):
        normalizer = Normalizer()
        df = pd.DataFrame(columns=list(STANDARD_COLUMNS))
        summary = normalizer.build_summary(df)
        assert summary.empty

    def test_build_summary_columns_present(self):
        normalizer = Normalizer()
        df = _make_df()
        summary = normalizer.build_summary(df)
        assert "peak_rate" in summary.columns
        assert "cumulative_oil_bbl" in summary.columns
        assert "avg_monthly_oil_bbl" in summary.columns
        assert "total_months" in summary.columns


class TestNormalizerCoverageGaps:
    def test_no_gaps_for_contiguous_series(self):
        normalizer = Normalizer()
        df = _make_df()
        gaps = normalizer.find_coverage_gaps(df)
        assert gaps == []

    def test_detects_gap_in_series(self):
        normalizer = Normalizer()
        # month 2 is missing → gap of 1
        df = pd.DataFrame(
            {
                "region": ["ncs", "ncs"],
                "field_name": ["Edvard Grieg", "Edvard Grieg"],
                "year": [2020, 2020],
                "month": [1, 3],
                "oil_bbl": [5_800_000.0, 5_600_000.0],
                "gas_mcf": [2_100_000.0, 2_050_000.0],
                "water_bbl": [420_000.0, 440_000.0],
                "condensate_bbl": [180_000.0, 175_000.0],
                "source": ["sodir_mock", "sodir_mock"],
            }
        )
        gaps = normalizer.find_coverage_gaps(df)
        assert len(gaps) == 1
        assert gaps[0]["gap_months"] == 1

    def test_empty_df_returns_no_gaps(self):
        normalizer = Normalizer()
        df = pd.DataFrame(columns=list(STANDARD_COLUMNS))
        gaps = normalizer.find_coverage_gaps(df)
        assert gaps == []
