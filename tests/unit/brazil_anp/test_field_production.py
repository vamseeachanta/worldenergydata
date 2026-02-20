"""Tests for field-level production aggregation."""

import pandas as pd
import pytest

from worldenergydata.brazil_anp.production.field_production import (
    FieldProductionAggregator,
)
from worldenergydata.brazil_anp.production.well_production import SM3_TO_BBL


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
            (result["field"] == "LULA")
            & (result["date"] == pd.Timestamp("2023-01-01"))
        ]
        assert len(lula_jan) == 1

    def test_aggregate_sums_oil_production(self, aggregator):
        result = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        lula_jan = result[
            (result["field"] == "LULA")
            & (result["date"] == pd.Timestamp("2023-01-01"))
        ]
        expected = 314490.0 + 283041.0
        assert abs(lula_jan.iloc[0]["oil_bbl"] - expected) < 1.0

    def test_aggregate_sums_water_production(self, aggregator):
        result = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        lula_jan = result[
            (result["field"] == "LULA")
            & (result["date"] == pd.Timestamp("2023-01-01"))
        ]
        expected = 125796.0 + 138375.6
        assert abs(lula_jan.iloc[0]["water_bbl"] - expected) < 1.0

    def test_aggregate_counts_wells(self, aggregator):
        result = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        lula_jan = result[
            (result["field"] == "LULA")
            & (result["date"] == pd.Timestamp("2023-01-01"))
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
        agg = aggregator.aggregate(MOCK_WELL_RECORDS.copy())
        summary = aggregator.get_field_summary(agg, "NONEXISTENT")
        assert summary["total_oil_bbl"] == 0.0

    def test_empty_input(self, aggregator):
        empty = pd.DataFrame(
            columns=["field", "well", "date", "oil_bbl", "condensate_bbl", "gas_m3", "water_bbl", "oil_bbl_per_day"]
        )
        result = aggregator.aggregate(empty)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
