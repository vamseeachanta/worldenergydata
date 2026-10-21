"""Tests for field-level production aggregation."""

import pandas as pd
import pytest

from worldenergydata.brazil_anp.production.field_production import (
    FieldProductionAggregator,
)

MOCK_WELL_RECORDS = pd.DataFrame(
    {
        "field": ["LULA", "LULA", "LULA", "BUZIOS", "MARLIM"],
        "well": ["7LL55", "7LL56", "7LL55", "7BUZ1", "7MRL1"],
        "date": pd.to_datetime(
            ["2023-01-01", "2023-01-01", "2023-02-01", "2023-01-01", "2023-01-01"]
        ),
        "oil_bbl": [314490.0, 283041.0, 300000.0, 377388.0, 188694.0],
        "condensate_bbl": [6289.8, 7547.76, 6000.0, 5031.84, 3144.9],
        "gas_m3": [8500.0, 7200.0, 8000.0, 10100.0, 5000.0],
        "water_bbl": [125796.0, 138375.6, 120000.0, 94347.0, 251592.0],
        "oil_bbl_per_day": [10145.0, 9130.0, 10714.0, 12174.0, 6087.0],
    }
)


class TestFieldProductionAggregator:
    @pytest.fixture
    def aggregator(self):
        return FieldProductionAggregator()

    def test_aggregate_returns_dataframe(self, aggregator):
        result = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        assert isinstance(result, pd.DataFrame)

    def test_aggregate_groups_by_field_and_date(self, aggregator):
        result = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        lula_jan = result[
            (result["field"] == "LULA") & (result["date"] == pd.Timestamp("2023-01-01"))
        ]
        assert len(lula_jan) == 1

    def test_aggregate_sums_oil_production(self, aggregator):
        result = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        lula_jan = result[
            (result["field"] == "LULA") & (result["date"] == pd.Timestamp("2023-01-01"))
        ]
        expected = 314490.0 + 283041.0
        assert abs(lula_jan.iloc[0]["oil_bbl"] - expected) < 1.0

    def test_aggregate_sums_water_production(self, aggregator):
        result = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        lula_jan = result[
            (result["field"] == "LULA") & (result["date"] == pd.Timestamp("2023-01-01"))
        ]
        expected = 125796.0 + 138375.6
        assert abs(lula_jan.iloc[0]["water_bbl"] - expected) < 1.0

    def test_aggregate_sums_current_schema_gas_mcf(self, aggregator):
        records = MOCK_WELL_RECORDS.copy()
        records["gas_mcf"] = [100.0, 200.0, 300.0, 400.0, 500.0]

        result = aggregator.aggregate(records)
        lula_jan = result[
            (result["field"] == "LULA") & (result["date"] == pd.Timestamp("2023-01-01"))
        ]

        assert "gas_mcf" in result.columns
        assert lula_jan.iloc[0]["gas_mcf"] == pytest.approx(300.0)

    def test_aggregate_counts_wells(self, aggregator):
        result = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        lula_jan = result[
            (result["field"] == "LULA") & (result["date"] == pd.Timestamp("2023-01-01"))
        ]
        assert lula_jan.iloc[0]["well_count"] == 2

    def test_aggregate_single_well_field(self, aggregator):
        result = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        buzios = result[result["field"] == "BUZIOS"]
        assert len(buzios) == 1
        assert buzios.iloc[0]["well_count"] == 1

    def test_water_cut_calculation(self, aggregator):
        result = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        marlim = result[result["field"] == "MARLIM"]
        water_cut = marlim.iloc[0]["water_cut"]
        expected = 251592.0 / (188694.0 + 251592.0)
        assert abs(water_cut - expected) < 0.01

    def test_get_field_summary(self, aggregator):
        agg = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        summary = aggregator.get_field_summary(agg, "LULA")
        assert isinstance(summary, dict)
        assert "total_oil_bbl" in summary
        assert "avg_daily_rate" in summary

    def test_get_field_summary_unknown_field(self, aggregator):
        """An absent label has no observations; it is not measured zero oil."""
        agg = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        with pytest.raises(ValueError, match="No production records for field"):
            aggregator.get_field_summary(agg, "NONEXISTENT")

    def test_get_field_summary_empty_aggregate(self, aggregator):
        """No input rows means no field observations, so no summary exists."""
        agg = aggregator.aggregate(pd.DataFrame())
        with pytest.raises(ValueError, match="No production records for field"):
            aggregator.get_field_summary(agg, "FIELD_A")

    def test_get_field_summary_recorded_zero(self, aggregator):
        """Hand calculation: one observed month, all measured quantities zero.

        Sum, mean, maximum and peak of the single zero observation are zero;
        the observed month count is one. These are synthetic inputs, not limits.
        """
        agg = pd.DataFrame(
            {
                "field": ["FIELD_A"],
                "oil_bbl": [0.0],
                "oil_bbl_per_day": [0.0],
                "water_cut": [0.0],
            }
        )

        assert aggregator.get_field_summary(agg, "FIELD_A") == {
            "total_oil_bbl": 0.0,
            "avg_daily_rate": 0.0,
            "max_water_cut": 0.0,
            "total_months": 1,
            "peak_oil_bbl": 0.0,
        }

    def test_get_field_summary_hand_calculated(self, aggregator):
        """Independent arithmetic for synthetic, already aggregated months.

        FIELD_A: total = 4 + 8 = 12 bbl; mean daily rate = (2 + 4) / 2
        = 3 bbl/day; max water cut = max(0.25, 0.5) = 0.5; month count = 2;
        peak = max(4, 8) = 8 bbl. FIELD_B's 16 bbl, 8 bbl/day and 0.75 water
        cut are excluded. No conversion coefficients or tolerance are used.
        """
        agg = pd.DataFrame(
            {
                "field": ["FIELD_A", "FIELD_B", "FIELD_A"],
                "oil_bbl": [4.0, 16.0, 8.0],
                "oil_bbl_per_day": [2.0, 8.0, 4.0],
                "water_cut": [0.25, 0.75, 0.5],
            }
        )

        assert aggregator.get_field_summary(agg, "FIELD_A") == {
            "total_oil_bbl": 12.0,
            "avg_daily_rate": 3.0,
            "max_water_cut": 0.5,
            "total_months": 2,
            "peak_oil_bbl": 8.0,
        }

    def test_empty_input(self, aggregator):
        empty = pd.DataFrame(
            columns=[
                "field",
                "well",
                "date",
                "oil_bbl",
                "condensate_bbl",
                "gas_mcf",
                "water_bbl",
                "oil_bbl_per_day",
            ]
        )
        result = aggregator.aggregate(empty)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
