"""Tests for EITI multi-country production data loader."""

import pytest
from unittest.mock import MagicMock, patch

from worldenergydata.west_africa.eiti.country_production import (
    CountryProductionLoader,
    ProductionRecord,
    aggregate_annual_production,
    SUPPORTED_EITI_COUNTRIES,
)


SAMPLE_PRODUCTION = [
    ProductionRecord(
        country="Nigeria",
        year=2022,
        company="NNPC",
        volume_bbl=450_000_000,
        commodity="crude_oil",
    ),
    ProductionRecord(
        country="Nigeria",
        year=2022,
        company="Shell Nigeria",
        volume_bbl=120_000_000,
        commodity="crude_oil",
    ),
    ProductionRecord(
        country="Ghana",
        year=2022,
        company="Tullow Oil",
        volume_bbl=55_000_000,
        commodity="crude_oil",
    ),
    ProductionRecord(
        country="Nigeria",
        year=2021,
        company="NNPC",
        volume_bbl=430_000_000,
        commodity="crude_oil",
    ),
]


class TestSupportedEitiCountries:
    def test_is_list(self):
        assert isinstance(SUPPORTED_EITI_COUNTRIES, list)

    def test_nigeria_included(self):
        assert "Nigeria" in SUPPORTED_EITI_COUNTRIES

    def test_angola_included(self):
        assert "Angola" in SUPPORTED_EITI_COUNTRIES

    def test_at_least_four_countries(self):
        assert len(SUPPORTED_EITI_COUNTRIES) >= 4


class TestProductionRecord:
    def test_record_creation(self):
        r = ProductionRecord(
            country="Nigeria",
            year=2022,
            company="NNPC",
            volume_bbl=500_000_000,
            commodity="crude_oil",
        )
        assert r.country == "Nigeria"
        assert r.volume_bbl == 500_000_000

    def test_volume_non_negative(self):
        with pytest.raises(ValueError):
            ProductionRecord(
                country="Nigeria",
                year=2022,
                company="NNPC",
                volume_bbl=-1,
                commodity="crude_oil",
            )

    def test_year_reasonable(self):
        with pytest.raises(ValueError):
            ProductionRecord(
                country="Nigeria",
                year=1800,
                company="NNPC",
                volume_bbl=100,
                commodity="crude_oil",
            )

    def test_volume_kbd_property(self):
        r = ProductionRecord(
            country="Nigeria",
            year=2022,
            company="NNPC",
            volume_bbl=365_000,
            commodity="crude_oil",
        )
        # 365,000 bbl / 365 days = 1 kbd
        assert r.volume_kbd == pytest.approx(1.0, abs=0.01)


class TestAggregateAnnualProduction:
    def test_returns_dict(self):
        result = aggregate_annual_production(SAMPLE_PRODUCTION)
        assert isinstance(result, dict)

    def test_nigeria_2022_sums_both_companies(self):
        result = aggregate_annual_production(SAMPLE_PRODUCTION)
        assert result[("Nigeria", 2022)] == pytest.approx(
            450_000_000 + 120_000_000, abs=1
        )

    def test_ghana_present(self):
        result = aggregate_annual_production(SAMPLE_PRODUCTION)
        assert ("Ghana", 2022) in result

    def test_empty_returns_empty_dict(self):
        assert aggregate_annual_production([]) == {}


class TestCountryProductionLoader:
    @patch("worldenergydata.west_africa.eiti.country_production.EitiApiClient")
    def test_loader_init(self, mock_cls):
        loader = CountryProductionLoader()
        assert loader is not None

    @patch("worldenergydata.west_africa.eiti.country_production.EitiApiClient")
    def test_load_returns_list(self, mock_cls):
        mock_client = MagicMock()
        mock_client.get_production_data.return_value = [
            {
                "country": "Nigeria",
                "year": 2022,
                "company": "NNPC",
                "volume_bbl": 500_000_000,
                "commodity": "crude_oil",
            }
        ]
        mock_cls.return_value = mock_client

        loader = CountryProductionLoader()
        result = loader.load(country="Nigeria", year=2022)
        assert isinstance(result, list)

    @patch("worldenergydata.west_africa.eiti.country_production.EitiApiClient")
    def test_load_unsupported_country_raises(self, mock_cls):
        loader = CountryProductionLoader()
        with pytest.raises(ValueError):
            loader.load(country="Atlantis", year=2022)

    @patch("worldenergydata.west_africa.eiti.country_production.EitiApiClient")
    def test_load_multiple_countries(self, mock_cls):
        mock_client = MagicMock()
        mock_client.get_production_data.return_value = []
        mock_cls.return_value = mock_client

        loader = CountryProductionLoader()
        result = loader.load_multiple(
            countries=["Nigeria", "Ghana"], year=2022
        )
        assert isinstance(result, list)
