"""Tests for SODIR monthly production loader."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from worldenergydata.sodir.production.monthly_loader import (
    MSM3_TO_MCF,
    SM3_TO_BBL,
    MonthlyProductionLoader,
)


class TestConversionConstants:
    """Test unit conversion constants are correct."""

    def test_sm3_to_bbl_conversion_factor(self):
        assert SM3_TO_BBL == 6.2898

    def test_msm3_to_mcf_conversion_factor(self):
        assert MSM3_TO_MCF == 35.3147


class TestMonthlyProductionLoader:
    """Tests for MonthlyProductionLoader."""

    @pytest.fixture
    def loader(self):
        return MonthlyProductionLoader()

    @pytest.fixture
    def mock_api_client(self):
        client = MagicMock()
        return client

    @pytest.fixture
    def loader_with_client(self, mock_api_client):
        loader = MonthlyProductionLoader(api_client=mock_api_client)
        return loader

    @pytest.fixture
    def sample_raw_production_data(self):
        return [
            {
                "fldName": "EDVARD GRIEG",
                "prfYear": 2020,
                "prfMonth": 1,
                "prfPrdOilNetMillSm3": 0.85,
                "prfPrdGasNetBillSm3": 0.12,
                "prfPrdNGLNetMillSm3": 0.05,
                "prfPrdCondensateNetMillSm3": 0.02,
                "prfPrdOeNetMillSm3": 1.04,
                "prfPrdProducedWaterInFieldMillSm3": 0.30,
            },
            {
                "fldName": "EDVARD GRIEG",
                "prfYear": 2020,
                "prfMonth": 2,
                "prfPrdOilNetMillSm3": 0.80,
                "prfPrdGasNetBillSm3": 0.11,
                "prfPrdNGLNetMillSm3": 0.04,
                "prfPrdCondensateNetMillSm3": 0.01,
                "prfPrdOeNetMillSm3": 0.96,
                "prfPrdProducedWaterInFieldMillSm3": 0.32,
            },
            {
                "fldName": "VALHALL",
                "prfYear": 2020,
                "prfMonth": 1,
                "prfPrdOilNetMillSm3": 0.40,
                "prfPrdGasNetBillSm3": 0.08,
                "prfPrdNGLNetMillSm3": 0.02,
                "prfPrdCondensateNetMillSm3": 0.00,
                "prfPrdOeNetMillSm3": 0.50,
                "prfPrdProducedWaterInFieldMillSm3": 0.55,
            },
        ]

    def test_loader_instantiation_default(self, loader):
        assert loader is not None

    def test_loader_instantiation_with_client(
        self, loader_with_client, mock_api_client
    ):
        assert loader_with_client.api_client is mock_api_client

    def test_parse_raw_record_extracts_field_name(
        self, loader, sample_raw_production_data
    ):
        record = loader.parse_raw_record(sample_raw_production_data[0])
        assert record["field_name"] == "EDVARD GRIEG"

    def test_parse_raw_record_extracts_year(self, loader, sample_raw_production_data):
        record = loader.parse_raw_record(sample_raw_production_data[0])
        assert record["year"] == 2020

    def test_parse_raw_record_extracts_month(self, loader, sample_raw_production_data):
        record = loader.parse_raw_record(sample_raw_production_data[0])
        assert record["month"] == 1

    def test_parse_raw_record_converts_oil_to_sm3(
        self, loader, sample_raw_production_data
    ):
        record = loader.parse_raw_record(sample_raw_production_data[0])
        # Input is in million Sm3, output is Sm3
        assert record["oil_sm3"] == pytest.approx(0.85 * 1e6)

    def test_parse_raw_record_converts_gas_to_sm3(
        self, loader, sample_raw_production_data
    ):
        record = loader.parse_raw_record(sample_raw_production_data[0])
        # Input is in billion Sm3, output is Sm3
        assert record["gas_sm3"] == pytest.approx(0.12 * 1e9)

    def test_parse_raw_record_converts_ngl_to_sm3(
        self, loader, sample_raw_production_data
    ):
        record = loader.parse_raw_record(sample_raw_production_data[0])
        assert record["ngl_sm3"] == pytest.approx(0.05 * 1e6)

    def test_parse_raw_record_converts_condensate_to_sm3(
        self, loader, sample_raw_production_data
    ):
        record = loader.parse_raw_record(sample_raw_production_data[0])
        assert record["condensate_sm3"] == pytest.approx(0.02 * 1e6)

    def test_parse_raw_record_extracts_water_injected(
        self, loader, sample_raw_production_data
    ):
        record = loader.parse_raw_record(sample_raw_production_data[0])
        assert record["water_injected_sm3"] == pytest.approx(0.30 * 1e6)

    def test_convert_oil_sm3_to_bbl(self, loader):
        sm3_value = 1000.0
        bbl = loader.convert_sm3_to_bbl(sm3_value)
        assert bbl == pytest.approx(6289.8)

    def test_convert_gas_msm3_to_mcf(self, loader):
        msm3_value = 1.0  # 1 million Sm3
        mcf = loader.convert_msm3_to_mcf(msm3_value)
        assert mcf == pytest.approx(35.3147)

    def test_convert_sm3_to_bbl_zero(self, loader):
        assert loader.convert_sm3_to_bbl(0.0) == 0.0

    def test_load_field_production_returns_dataframe(
        self, loader_with_client, sample_raw_production_data
    ):
        loader_with_client.api_client.get.return_value = {
            "data": sample_raw_production_data
        }
        df = loader_with_client.load_field_production("EDVARD GRIEG")
        assert isinstance(df, pd.DataFrame)

    def test_load_field_production_filters_by_field(
        self, loader_with_client, sample_raw_production_data
    ):
        loader_with_client.api_client.get.return_value = {
            "data": sample_raw_production_data
        }
        df = loader_with_client.load_field_production("EDVARD GRIEG")
        assert all(df["field_name"] == "EDVARD GRIEG")

    def test_load_field_production_has_required_columns(
        self, loader_with_client, sample_raw_production_data
    ):
        loader_with_client.api_client.get.return_value = {
            "data": sample_raw_production_data
        }
        df = loader_with_client.load_field_production("EDVARD GRIEG")
        required = [
            "field_name",
            "year",
            "month",
            "oil_sm3",
            "gas_sm3",
            "ngl_sm3",
            "condensate_sm3",
            "water_injected_sm3",
        ]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_load_all_production_returns_dataframe(
        self, loader_with_client, sample_raw_production_data
    ):
        loader_with_client.api_client.get.return_value = {
            "data": sample_raw_production_data
        }
        df = loader_with_client.load_all_production()
        assert isinstance(df, pd.DataFrame)

    def test_load_all_production_includes_all_fields(
        self, loader_with_client, sample_raw_production_data
    ):
        loader_with_client.api_client.get.return_value = {
            "data": sample_raw_production_data
        }
        df = loader_with_client.load_all_production()
        assert set(df["field_name"].unique()) == {"EDVARD GRIEG", "VALHALL"}

    def test_get_oil_bbl_column(self, loader_with_client, sample_raw_production_data):
        loader_with_client.api_client.get.return_value = {
            "data": sample_raw_production_data
        }
        df = loader_with_client.load_field_production("EDVARD GRIEG")
        assert "oil_bbl" in df.columns
        assert df["oil_bbl"].iloc[0] == pytest.approx(0.85 * 1e6 * SM3_TO_BBL)

    def test_get_gas_mcf_column(self, loader_with_client, sample_raw_production_data):
        loader_with_client.api_client.get.return_value = {
            "data": sample_raw_production_data
        }
        df = loader_with_client.load_field_production("EDVARD GRIEG")
        assert "gas_mcf" in df.columns

    def test_load_production_empty_response(self, loader_with_client):
        loader_with_client.api_client.get.return_value = {"data": []}
        df = loader_with_client.load_field_production("NONEXISTENT")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_parse_raw_record_handles_missing_fields(self, loader):
        record = loader.parse_raw_record(
            {"fldName": "TEST", "prfYear": 2020, "prfMonth": 1}
        )
        assert record["oil_sm3"] == 0.0
        assert record["gas_sm3"] == 0.0

    def test_cache_key_generation(self, loader_with_client):
        key = loader_with_client._cache_key("EDVARD GRIEG")
        assert "EDVARD GRIEG" in key or isinstance(key, str)

    def test_cached_results_are_returned(
        self, loader_with_client, sample_raw_production_data
    ):
        loader_with_client.api_client.get.return_value = {
            "data": sample_raw_production_data
        }
        df1 = loader_with_client.load_field_production("EDVARD GRIEG")
        df2 = loader_with_client.load_field_production("EDVARD GRIEG")
        # API should only be called once due to caching
        assert loader_with_client.api_client.get.call_count == 1
        pd.testing.assert_frame_equal(df1, df2)
