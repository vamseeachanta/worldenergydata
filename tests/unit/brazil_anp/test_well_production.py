"""Tests for well-level production loader."""

import pandas as pd
import pytest

from worldenergydata.brazil_anp.production.well_production import (
    SM3_TO_BBL,
    WellProductionLoader,
    convert_mm3_to_m3,
    convert_sm3_to_bbl,
)
from worldenergydata.common.units import GasUnits

MOCK_WELL_DATA = pd.DataFrame(
    {
        "campo": ["LULA", "LULA", "BUZIOS", "MARLIM"],
        "poco": ["7LL55", "7LL56", "7BUZ1", "7MRL1"],
        "data": ["2023-01-01", "2023-01-01", "2023-01-01", "2023-01-01"],
        "oleo_sm3": [50000.0, 45000.0, 60000.0, 30000.0],
        "condensado_sm3": [1000.0, 1200.0, 800.0, 500.0],
        "gas_mm3": [8.5, 7.2, 10.1, 5.0],
        "agua_sm3": [20000.0, 22000.0, 15000.0, 40000.0],
    }
)


class TestUnitConversions:
    def test_sm3_to_bbl_constant(self):
        assert abs(SM3_TO_BBL - 6.2898) < 0.001

    def test_convert_sm3_to_bbl(self):
        result = convert_sm3_to_bbl(1.0)
        assert abs(result - 6.2898) < 0.001

    def test_convert_sm3_to_bbl_zero(self):
        assert convert_sm3_to_bbl(0.0) == 0.0

    def test_convert_mm3_to_m3(self):
        assert convert_mm3_to_m3(1.0) == 1000.0

    def test_convert_mm3_to_m3_zero(self):
        assert convert_mm3_to_m3(0.0) == 0.0


class TestWellProductionLoader:
    @pytest.fixture
    def loader(self):
        return WellProductionLoader()

    def test_load_from_dataframe(self, loader):
        result = loader.load(MOCK_WELL_DATA.copy())
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4

    def test_oil_conversion_to_bbl(self, loader):
        result = loader.load(MOCK_WELL_DATA.copy())
        assert "oil_bbl" in result.columns
        expected = 50000.0 * SM3_TO_BBL
        assert abs(result.iloc[0]["oil_bbl"] - expected) < 1.0

    def test_condensate_conversion(self, loader):
        result = loader.load(MOCK_WELL_DATA.copy())
        assert "condensate_bbl" in result.columns
        expected = 1000.0 * SM3_TO_BBL
        assert abs(result.iloc[0]["condensate_bbl"] - expected) < 1.0

    def test_gas_conversion(self, loader):
        result = loader.load(MOCK_WELL_DATA.copy())
        assert "gas_m3" in result.columns
        expected = 8.5 * 1000.0
        assert abs(result.iloc[0]["gas_m3"] - expected) < 1.0

    def test_water_conversion(self, loader):
        result = loader.load(MOCK_WELL_DATA.copy())
        assert "water_bbl" in result.columns
        expected = 20000.0 * SM3_TO_BBL
        assert abs(result.iloc[0]["water_bbl"] - expected) < 1.0

    def test_daily_rate_calculation(self, loader):
        result = loader.load(MOCK_WELL_DATA.copy())
        assert "oil_bbl_per_day" in result.columns
        expected_monthly = 50000.0 * SM3_TO_BBL
        expected_daily = expected_monthly / 31  # January has 31 days
        assert abs(result.iloc[0]["oil_bbl_per_day"] - expected_daily) < 10.0

    def test_field_name_preserved(self, loader):
        result = loader.load(MOCK_WELL_DATA.copy())
        assert "field" in result.columns
        assert result.iloc[0]["field"] == "LULA"

    def test_well_name_preserved(self, loader):
        result = loader.load(MOCK_WELL_DATA.copy())
        assert "well" in result.columns
        assert result.iloc[0]["well"] == "7LL55"

    def test_date_parsed(self, loader):
        result = loader.load(MOCK_WELL_DATA.copy())
        assert "date" in result.columns
        assert pd.api.types.is_datetime64_any_dtype(result["date"])

    def test_empty_dataframe(self, loader):
        empty = pd.DataFrame(
            columns=[
                "campo",
                "poco",
                "data",
                "oleo_sm3",
                "condensado_sm3",
                "gas_mm3",
                "agua_sm3",
            ]
        )
        result = loader.load(empty)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


CURRENT_ANP_DATA = pd.DataFrame(
    [
        {
            "Estado": "Rio de Janeiro",
            "Bacia": "Santos",
            "Nome Poço ANP": "7-TUPI-1",
            "Campo": "TUPI",
            "Operador": "Petrobras",
            "Ambiente": "Mar",
            "Período": "2023/01",
            "Óleo (bbl/dia)": "1.000,5000",
            "Condensado (bbl/dia)": "10,0000",
            "Gás Natural (Mm³/dia) Gás Total": "5,5000",
            "Água (bbl/dia)": "20,2500",
            "location_source": "presal",
        }
    ]
)


class TestCurrentAnpWellProductionSchema:
    @pytest.fixture
    def loader(self):
        return WellProductionLoader()

    def test_current_portuguese_schema_parses_decimal_comma_rates(self, loader):
        result = loader.load(CURRENT_ANP_DATA.copy())
        row = result.iloc[0]

        assert row["field"] == "TUPI"
        assert row["well"] == "7-TUPI-1"
        assert row["year"] == 2023
        assert row["month"] == 1
        assert row["date"] == pd.Timestamp("2023-01-01")
        assert row["oil_bbl"] == pytest.approx(1000.5 * 31)
        assert row["condensate_bbl"] == pytest.approx(10.0 * 31)
        assert row["water_bbl"] == pytest.approx(20.25 * 31)

    def test_current_gas_thousand_m3_per_day_converts_to_monthly_mcf(self, loader):
        result = loader.load(CURRENT_ANP_DATA.copy())

        # ANP's Brazilian "Mm³/dia" is thousand m³/day, so the 1000 m³ and
        # 1000 scf/Mcf factors cancel: value * 35.3147 * days.
        expected = 5.5 * GasUnits.SM3_TO_SCF * 31
        assert result.iloc[0]["gas_mcf"] == pytest.approx(expected)

    def test_current_schema_preserves_source_metadata(self, loader):
        result = loader.load(CURRENT_ANP_DATA.copy())
        row = result.iloc[0]

        assert row["operator"] == "Petrobras"
        assert row["basin"] == "Santos"
        assert row["environment"] == "Mar"
        assert row["location_source"] == "presal"
