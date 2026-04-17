"""Tests for international country-level production (EIA INTL series)."""

import pandas as pd
import pytest

from worldenergydata.eia_us.international.country_production import (
    MOCK_COUNTRY_PRODUCTION,
    TOP_PRODUCERS,
    CountryProductionLoader,
)


class TestMockCountryProduction:
    def test_mock_data_has_at_least_20_countries(self):
        assert len(MOCK_COUNTRY_PRODUCTION) >= 20

    def test_mock_data_includes_saudi_arabia(self):
        countries = [r["country"] for r in MOCK_COUNTRY_PRODUCTION]
        assert "Saudi Arabia" in countries

    def test_mock_data_includes_russia(self):
        countries = [r["country"] for r in MOCK_COUNTRY_PRODUCTION]
        assert "Russia" in countries

    def test_mock_data_includes_usa(self):
        countries = [r["country"] for r in MOCK_COUNTRY_PRODUCTION]
        assert "United States" in countries

    def test_mock_data_includes_iraq(self):
        countries = [r["country"] for r in MOCK_COUNTRY_PRODUCTION]
        assert "Iraq" in countries

    def test_mock_data_has_production_values(self):
        for record in MOCK_COUNTRY_PRODUCTION[:5]:
            assert "production_kbd" in record
            assert record["production_kbd"] > 0

    def test_mock_data_has_year_field(self):
        for record in MOCK_COUNTRY_PRODUCTION[:5]:
            assert "year" in record


class TestTopProducers:
    def test_top_producers_is_list(self):
        assert isinstance(TOP_PRODUCERS, list)

    def test_top_producers_has_entries(self):
        assert len(TOP_PRODUCERS) >= 10

    def test_usa_in_top_producers(self):
        assert "United States" in TOP_PRODUCERS


class TestCountryProductionLoader:
    @pytest.fixture
    def loader(self):
        return CountryProductionLoader()

    def test_load_returns_dataframe(self, loader):
        df = loader.load(MOCK_COUNTRY_PRODUCTION)
        assert isinstance(df, pd.DataFrame)

    def test_load_has_required_columns(self, loader):
        df = loader.load(MOCK_COUNTRY_PRODUCTION)
        for col in ["country", "year", "production_kbd"]:
            assert col in df.columns

    def test_load_empty_returns_empty_dataframe(self, loader):
        df = loader.load([])
        assert df.empty

    def test_load_20_plus_countries(self, loader):
        df = loader.load(MOCK_COUNTRY_PRODUCTION)
        assert df["country"].nunique() >= 20

    def test_production_values_positive(self, loader):
        df = loader.load(MOCK_COUNTRY_PRODUCTION)
        assert all(df["production_kbd"] > 0)

    def test_filter_by_country(self, loader):
        df = loader.load(MOCK_COUNTRY_PRODUCTION)
        saudi = loader.filter_country(df, "Saudi Arabia")
        assert all(saudi["country"] == "Saudi Arabia")

    def test_top_n_producers(self, loader):
        df = loader.load(MOCK_COUNTRY_PRODUCTION)
        top5 = loader.top_producers(df, n=5)
        assert len(top5) == 5
        # Verify sorted descending
        assert (
            top5["production_kbd"].is_monotonic_decreasing
            or top5["production_kbd"].iloc[0] >= top5["production_kbd"].iloc[-1]
        )

    def test_usa_among_top_3(self, loader):
        df = loader.load(MOCK_COUNTRY_PRODUCTION)
        top3 = loader.top_producers(df, n=3)
        assert "United States" in top3["country"].values

    def test_filter_by_year(self, loader):
        df = loader.load(MOCK_COUNTRY_PRODUCTION)
        year = df["year"].iloc[0]
        filtered = loader.filter_year(df, year)
        assert all(filtered["year"] == year)
