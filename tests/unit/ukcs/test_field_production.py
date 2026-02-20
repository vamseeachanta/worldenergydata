"""Tests for UKCS monthly/annual field production loader."""

import pandas as pd
import pytest

from worldenergydata.ukcs.production.field_production import (
    UKCSFieldProductionLoader,
    TONNES_TO_BBL,
    MMSCF_TO_MCF,
)


MOCK_CSV_DATA = {
    "FieldName": ["FORTIES", "FORTIES", "BUZZARD", "MARINER", "MARINER"],
    "Year": [2022, 2022, 2022, 2022, 2022],
    "Month": [1, 2, 1, 1, 2],
    "OilProduction (Thousand Tonnes)": [450.3, 430.0, 780.1, 120.5, 110.2],
    "GasProduction (MMscf)": [12.5, 11.0, 8.9, 5.2, 4.8],
    "WaterProduction (Thousand Tonnes)": [310.2, 295.7, 210.5, 55.3, 50.1],
}


def make_mock_df():
    return pd.DataFrame(MOCK_CSV_DATA)


class TestUnitConversionConstants:
    def test_tonnes_to_bbl_approx_7_33(self):
        assert abs(TONNES_TO_BBL - 7.33) < 0.1

    def test_mmscf_to_mcf_is_1000(self):
        assert MMSCF_TO_MCF == 1000.0


class TestUKCSFieldProductionLoaderLoad:
    @pytest.fixture
    def loader(self):
        return UKCSFieldProductionLoader()

    def test_load_returns_dataframe(self, loader):
        raw = make_mock_df()
        result = loader.load(raw)
        assert isinstance(result, pd.DataFrame)

    def test_load_converts_oil_to_bbl(self, loader):
        raw = make_mock_df()
        result = loader.load(raw)
        # 450.3 thousand tonnes * 1000 * TONNES_TO_BBL
        expected_bbl = 450.3 * 1000 * TONNES_TO_BBL
        forties_jan = result[
            (result["field"] == "FORTIES") & (result["month"] == 1)
        ]
        assert len(forties_jan) == 1
        assert forties_jan.iloc[0]["oil_bbl"] == pytest.approx(expected_bbl, rel=1e-3)

    def test_load_converts_gas_to_mcf(self, loader):
        raw = make_mock_df()
        result = loader.load(raw)
        expected_mcf = 12.5 * MMSCF_TO_MCF
        forties_jan = result[
            (result["field"] == "FORTIES") & (result["month"] == 1)
        ]
        assert forties_jan.iloc[0]["gas_mcf"] == pytest.approx(expected_mcf, rel=1e-3)

    def test_load_converts_water_to_bbl(self, loader):
        raw = make_mock_df()
        result = loader.load(raw)
        expected_bbl = 310.2 * 1000 * TONNES_TO_BBL
        forties_jan = result[
            (result["field"] == "FORTIES") & (result["month"] == 1)
        ]
        assert forties_jan.iloc[0]["water_bbl"] == pytest.approx(expected_bbl, rel=1e-3)

    def test_load_output_has_required_columns(self, loader):
        raw = make_mock_df()
        result = loader.load(raw)
        required = {"field", "year", "month", "oil_bbl", "gas_mcf", "water_bbl"}
        assert required.issubset(set(result.columns))

    def test_load_normalises_field_names_to_upper(self, loader):
        raw = make_mock_df()
        raw["FieldName"] = raw["FieldName"].str.title()
        result = loader.load(raw)
        assert result["field"].str.isupper().all()

    def test_load_empty_dataframe_returns_empty(self, loader):
        empty = pd.DataFrame(
            columns=[
                "FieldName", "Year", "Month",
                "OilProduction (Thousand Tonnes)",
                "GasProduction (MMscf)",
                "WaterProduction (Thousand Tonnes)",
            ]
        )
        result = loader.load(empty)
        assert result.empty

    def test_load_preserves_all_rows(self, loader):
        raw = make_mock_df()
        result = loader.load(raw)
        assert len(result) == len(raw)


class TestUKCSFieldProductionLoaderFilter:
    @pytest.fixture
    def loader(self):
        return UKCSFieldProductionLoader()

    def test_filter_by_field(self, loader):
        raw = make_mock_df()
        df = loader.load(raw)
        result = loader.filter_field(df, "FORTIES")
        assert all(result["field"] == "FORTIES")
        assert len(result) == 2

    def test_filter_by_field_case_insensitive(self, loader):
        raw = make_mock_df()
        df = loader.load(raw)
        result = loader.filter_field(df, "forties")
        assert len(result) == 2

    def test_filter_by_year(self, loader):
        raw = make_mock_df()
        df = loader.load(raw)
        result = loader.filter_year(df, 2022)
        assert len(result) == 5

    def test_filter_missing_field_returns_empty(self, loader):
        raw = make_mock_df()
        df = loader.load(raw)
        result = loader.filter_field(df, "ELGIN_FRANKLIN")
        assert result.empty


class TestUKCSFieldProductionLoaderAnnual:
    @pytest.fixture
    def loader(self):
        return UKCSFieldProductionLoader()

    def test_annual_aggregate_sums_oil(self, loader):
        raw = make_mock_df()
        df = loader.load(raw)
        annual = loader.annual_aggregate(df)
        forties_2022 = annual[
            (annual["field"] == "FORTIES") & (annual["year"] == 2022)
        ]
        assert len(forties_2022) == 1
        expected = (450.3 + 430.0) * 1000 * TONNES_TO_BBL
        assert forties_2022.iloc[0]["oil_bbl"] == pytest.approx(expected, rel=1e-3)

    def test_annual_aggregate_has_year_column(self, loader):
        raw = make_mock_df()
        df = loader.load(raw)
        annual = loader.annual_aggregate(df)
        assert "year" in annual.columns
        assert "field" in annual.columns
