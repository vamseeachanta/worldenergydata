"""Tests for cross_basin analytics functions."""

import pandas as pd
import pytest

from worldenergydata.production.unified.cross_basin import (
    _FISCAL_REGIMES,
    _GENERIC_DEFAULT_REGIME,
    compare_cumulative_eur,
    compare_peak_rates,
    fiscal_regime_source,
    fiscal_sensitivity,
)
from worldenergydata.production.unified.query import ProductionQuery, ProductionResult


def _make_result(rows):
    """Build a minimal ProductionResult from raw row dicts."""
    q = ProductionQuery(regions=["ncs", "gom"])
    data = pd.DataFrame(rows)
    summary = pd.DataFrame()
    return ProductionResult(
        query=q,
        data=data,
        summary=summary,
        sources_used=["sodir_mock", "bsee_mock"],
        coverage_gaps=[],
    )


_SAMPLE_ROWS = [
    {
        "region": "ncs",
        "field_name": "Edvard Grieg",
        "year": 2020,
        "month": 1,
        "oil_bbl": 5_800_000.0,
        "gas_mcf": 2_100_000.0,
        "water_bbl": 420_000.0,
        "condensate_bbl": 180_000.0,
        "source": "sodir_mock",
    },
    {
        "region": "ncs",
        "field_name": "Edvard Grieg",
        "year": 2020,
        "month": 2,
        "oil_bbl": 5_200_000.0,
        "gas_mcf": 1_900_000.0,
        "water_bbl": 450_000.0,
        "condensate_bbl": 160_000.0,
        "source": "sodir_mock",
    },
    {
        "region": "gom",
        "field_name": "Atlantis",
        "year": 2020,
        "month": 1,
        "oil_bbl": 8_000_000.0,
        "gas_mcf": 10_000_000.0,
        "water_bbl": 1_200_000.0,
        "condensate_bbl": 200_000.0,
        "source": "bsee_mock",
    },
    {
        "region": "gom",
        "field_name": "Atlantis",
        "year": 2020,
        "month": 2,
        "oil_bbl": 7_500_000.0,
        "gas_mcf": 9_500_000.0,
        "water_bbl": 1_300_000.0,
        "condensate_bbl": 190_000.0,
        "source": "bsee_mock",
    },
]


class TestComparePeakRates:
    def test_returns_dataframe(self):
        result = _make_result(_SAMPLE_ROWS)
        df = compare_peak_rates(result)
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self):
        result = _make_result(_SAMPLE_ROWS)
        df = compare_peak_rates(result)
        assert "region" in df.columns
        assert "field_name" in df.columns
        assert "peak_oil_bbl" in df.columns

    def test_sorted_descending(self):
        result = _make_result(_SAMPLE_ROWS)
        df = compare_peak_rates(result)
        assert df.iloc[0]["peak_oil_bbl"] >= df.iloc[1]["peak_oil_bbl"]

    def test_atlantis_is_peak(self):
        result = _make_result(_SAMPLE_ROWS)
        df = compare_peak_rates(result)
        assert df.iloc[0]["field_name"] == "Atlantis"

    def test_empty_data_returns_empty(self):
        q = ProductionQuery(regions=["ncs"])
        result = ProductionResult(
            query=q,
            data=pd.DataFrame(
                columns=[
                    "region",
                    "field_name",
                    "year",
                    "month",
                    "oil_bbl",
                    "gas_mcf",
                    "water_bbl",
                    "condensate_bbl",
                    "source",
                ]
            ),
            summary=pd.DataFrame(),
            sources_used=[],
            coverage_gaps=[],
        )
        df = compare_peak_rates(result)
        assert df.empty

    def test_correct_peak_value_per_field(self):
        result = _make_result(_SAMPLE_ROWS)
        df = compare_peak_rates(result)
        edvard = df[df["field_name"] == "Edvard Grieg"]["peak_oil_bbl"].iloc[0]
        assert edvard == 5_800_000.0


class TestCompareCumulativeEur:
    def test_returns_dataframe(self):
        result = _make_result(_SAMPLE_ROWS)
        df = compare_cumulative_eur(result)
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self):
        result = _make_result(_SAMPLE_ROWS)
        df = compare_cumulative_eur(result)
        assert "cumulative_oil_bbl" in df.columns
        assert "cumulative_gas_mcf" in df.columns
        assert "eur_boe" in df.columns

    def test_eur_is_oil_plus_gas_over_six(self):
        result = _make_result(_SAMPLE_ROWS)
        df = compare_cumulative_eur(result)
        row = df[df["field_name"] == "Edvard Grieg"].iloc[0]
        expected_eur = row["cumulative_oil_bbl"] + row["cumulative_gas_mcf"] / 6.0
        assert abs(row["eur_boe"] - expected_eur) < 1.0

    def test_sorted_descending_by_eur(self):
        result = _make_result(_SAMPLE_ROWS)
        df = compare_cumulative_eur(result)
        assert df.iloc[0]["eur_boe"] >= df.iloc[1]["eur_boe"]

    def test_empty_data_returns_empty(self):
        q = ProductionQuery(regions=["ncs"])
        result = ProductionResult(
            query=q,
            data=pd.DataFrame(
                columns=[
                    "region",
                    "field_name",
                    "year",
                    "month",
                    "oil_bbl",
                    "gas_mcf",
                    "water_bbl",
                    "condensate_bbl",
                    "source",
                ]
            ),
            summary=pd.DataFrame(),
            sources_used=[],
            coverage_gaps=[],
        )
        df = compare_cumulative_eur(result)
        assert df.empty


class TestFiscalSensitivity:
    def test_returns_dataframe(self):
        result = _make_result(_SAMPLE_ROWS)
        df = fiscal_sensitivity(result, oil_price_usd=80.0)
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self):
        result = _make_result(_SAMPLE_ROWS)
        df = fiscal_sensitivity(result, oil_price_usd=80.0)
        assert "total_revenue_usd" in df.columns
        assert "govt_take_usd" in df.columns
        assert "operator_npv_usd" in df.columns
        assert "effective_govt_take_pct" in df.columns

    def test_govt_take_less_than_revenue(self):
        result = _make_result(_SAMPLE_ROWS)
        df = fiscal_sensitivity(result, oil_price_usd=80.0)
        assert (df["govt_take_usd"] < df["total_revenue_usd"]).all()

    def test_effective_govt_take_pct_in_range(self):
        result = _make_result(_SAMPLE_ROWS)
        df = fiscal_sensitivity(result, oil_price_usd=80.0)
        assert (df["effective_govt_take_pct"] >= 0).all()
        assert (df["effective_govt_take_pct"] <= 100).all()

    def test_higher_price_raises_npv(self):
        result = _make_result(_SAMPLE_ROWS)
        df_low = fiscal_sensitivity(result, oil_price_usd=40.0)
        df_high = fiscal_sensitivity(result, oil_price_usd=100.0)
        # NPV at $100 should exceed NPV at $40 for same field
        low_npv = df_low["operator_npv_usd"].sum()
        high_npv = df_high["operator_npv_usd"].sum()
        assert high_npv > low_npv

    def test_empty_data_returns_empty(self):
        q = ProductionQuery(regions=["ncs"])
        result = ProductionResult(
            query=q,
            data=pd.DataFrame(
                columns=[
                    "region",
                    "field_name",
                    "year",
                    "month",
                    "oil_bbl",
                    "gas_mcf",
                    "water_bbl",
                    "condensate_bbl",
                    "source",
                ]
            ),
            summary=pd.DataFrame(),
            sources_used=[],
            coverage_gaps=[],
        )
        df = fiscal_sensitivity(result, oil_price_usd=80.0)
        assert df.empty

    def test_norway_higher_govt_take_than_gom(self):
        """NCS has ~78% govt take vs GoM ~36% — NCS effective pct should be higher."""
        result = _make_result(_SAMPLE_ROWS)
        df = fiscal_sensitivity(result, oil_price_usd=80.0)
        ncs_pct = df[df["region"] == "ncs"]["effective_govt_take_pct"].values[0]
        gom_pct = df[df["region"] == "gom"]["effective_govt_take_pct"].values[0]
        assert ncs_pct > gom_pct


# ---------------------------------------------------------------------------
# Fiscal-regime coverage (#831)
# ---------------------------------------------------------------------------


class TestFiscalRegimeCoverage:
    """Every routed region must resolve to a country-specific fiscal regime.

    Spain and Australia were silently falling through to the generic default
    (royalty 0.15 / tax 0.25), so Spain's published government take was a
    placeholder rather than its actual regime (#831).
    """

    def test_spain_has_country_specific_regime(self):
        assert _FISCAL_REGIMES["spain"]["tax_rate"] == 0.30

    def test_australia_has_country_specific_regime(self):
        assert _FISCAL_REGIMES["australia"]["tax_rate"] == 0.58

    def test_unknown_region_reports_generic_default(self):
        assert fiscal_regime_source("nowhereland") == "generic-default"

    def test_spain_reports_country_specific(self):
        assert fiscal_regime_source("spain") == "country-specific"

    def test_generic_default_regime_is_a_named_constant(self):
        assert _GENERIC_DEFAULT_REGIME["royalty_rate"] == 0.15

    def test_every_routed_region_has_a_country_specific_regime(self):
        """Guard against recurrence: a new region must not silently inherit
        the generic default the way spain and australia did."""
        from worldenergydata.production.unified.router import RegionRouter

        missing = [
            region
            for region in RegionRouter().list_regions()
            if fiscal_regime_source(region) != "country-specific"
        ]
        assert missing == []

    def test_spain_effective_govt_take_uses_its_own_regime(self):
        """0.02 royalty + 0.30 tax on the remainder = 31.4%, NOT the 36.25%
        the generic default produced."""
        rows = [
            {
                "region": "spain",
                "field_name": "Ayoluengo",
                "year": 2020,
                "month": 1,
                "oil_bbl": 10_000.0,
                "gas_mcf": 0.0,
                "water_bbl": 0.0,
                "condensate_bbl": 0.0,
                "source": "cores",
            }
        ]
        df = fiscal_sensitivity(_make_result(rows), oil_price_usd=70.0)
        assert round(float(df["effective_govt_take_pct"].values[0]), 2) == 31.40
