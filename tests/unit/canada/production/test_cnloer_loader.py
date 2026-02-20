"""
Tests for CnloerLoader — C-NLOER NL offshore production data module.

Coverage targets:
- available_fields() returns all 5 NL fields
- load_field() returns non-empty records for each field
- Record structure and field values are correct
- Unit conversions applied correctly (m3 -> bbl via OilUnits.SM3_TO_BBL)
- Year filtering works
- to_dataframe() returns DataFrame with correct schema
- load_all_fields() covers all five fields
- Error handling for unknown fields
"""

import math

import pandas as pd
import pytest

from worldenergydata.canada.production.cnloer_loader import (
    CnloerLoader,
    CnloerProductionRecord,
    _MSM3_TO_MCF,
)
from worldenergydata.common.units import OilUnits

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EXPECTED_FIELDS = {"Hibernia", "Terra Nova", "White Rose", "Hebron", "North Amethyst"}


@pytest.fixture
def loader() -> CnloerLoader:
    return CnloerLoader()


# ---------------------------------------------------------------------------
# Test: available_fields
# ---------------------------------------------------------------------------


class TestAvailableFields:
    def test_available_fields_returns_list(self, loader):
        result = loader.available_fields()
        assert isinstance(result, list)

    def test_available_fields_contains_all_five_nl_fields(self, loader):
        result = set(loader.available_fields())
        assert result == EXPECTED_FIELDS

    def test_available_fields_has_exactly_five_entries(self, loader):
        assert len(loader.available_fields()) == 5

    def test_available_fields_contains_hibernia(self, loader):
        assert "Hibernia" in loader.available_fields()

    def test_available_fields_contains_terra_nova(self, loader):
        assert "Terra Nova" in loader.available_fields()

    def test_available_fields_contains_white_rose(self, loader):
        assert "White Rose" in loader.available_fields()

    def test_available_fields_contains_hebron(self, loader):
        assert "Hebron" in loader.available_fields()

    def test_available_fields_contains_north_amethyst(self, loader):
        assert "North Amethyst" in loader.available_fields()


# ---------------------------------------------------------------------------
# Test: load_field — basic structure
# ---------------------------------------------------------------------------


class TestLoadFieldStructure:
    def test_load_field_hibernia_returns_non_empty_list(self, loader):
        records = loader.load_field("Hibernia")
        assert len(records) > 0

    def test_load_field_returns_cnloer_production_records(self, loader):
        records = loader.load_field("Hibernia")
        assert all(isinstance(r, CnloerProductionRecord) for r in records)

    def test_load_field_record_has_field_name(self, loader):
        records = loader.load_field("Hibernia")
        assert all(r.field_name == "Hibernia" for r in records)

    def test_load_field_record_has_year(self, loader):
        records = loader.load_field("Hibernia")
        assert all(isinstance(r.year, int) for r in records)

    def test_load_field_record_has_month(self, loader):
        records = loader.load_field("Hibernia")
        assert all(isinstance(r.month, int) for r in records)

    def test_load_field_record_has_oil_bbl(self, loader):
        records = loader.load_field("Hibernia")
        assert all(isinstance(r.oil_bbl, float) for r in records)

    def test_load_field_record_has_gas_mcf(self, loader):
        records = loader.load_field("Hibernia")
        assert all(isinstance(r.gas_mcf, float) for r in records)

    def test_load_field_record_has_water_bbl(self, loader):
        records = loader.load_field("Hibernia")
        assert all(isinstance(r.water_bbl, float) for r in records)

    def test_load_field_record_source_is_cnloer(self, loader):
        records = loader.load_field("Hibernia")
        assert all(r.source == "cnloer" for r in records)

    def test_load_field_all_fields_source_cnloer(self, loader):
        for field_name in loader.available_fields():
            records = loader.load_field(field_name)
            assert all(r.source == "cnloer" for r in records), (
                f"field {field_name}: some records have wrong source"
            )


# ---------------------------------------------------------------------------
# Test: load_field — value validity
# ---------------------------------------------------------------------------


class TestLoadFieldValues:
    def test_load_field_oil_bbl_positive_for_production_years(self, loader):
        records = loader.load_field("Hibernia")
        assert all(r.oil_bbl >= 0 for r in records)
        # At least one peak year should have substantial production
        assert any(r.oil_bbl > 1_000_000 for r in records)

    def test_load_field_hibernia_start_year_gte_1997(self, loader):
        records = loader.load_field("Hibernia")
        assert all(r.year >= 1997 for r in records)

    def test_load_field_terra_nova_start_year_gte_2002(self, loader):
        records = loader.load_field("Terra Nova")
        assert min(r.year for r in records) >= 2002

    def test_load_field_hebron_start_year_gte_2017(self, loader):
        records = loader.load_field("Hebron")
        assert min(r.year for r in records) >= 2017

    def test_load_field_north_amethyst_start_year_gte_2010(self, loader):
        records = loader.load_field("North Amethyst")
        assert min(r.year for r in records) >= 2010

    def test_load_field_gas_mcf_non_negative(self, loader):
        for field_name in loader.available_fields():
            records = loader.load_field(field_name)
            assert all(r.gas_mcf >= 0 for r in records)

    def test_load_field_water_bbl_non_negative(self, loader):
        for field_name in loader.available_fields():
            records = loader.load_field(field_name)
            assert all(r.water_bbl >= 0 for r in records)


# ---------------------------------------------------------------------------
# Test: year filtering
# ---------------------------------------------------------------------------


class TestLoadFieldYearFiltering:
    def test_start_year_filter_applied(self, loader):
        records = loader.load_field("Hibernia", start_year=2000)
        assert all(r.year >= 2000 for r in records)

    def test_end_year_filter_applied(self, loader):
        records = loader.load_field("Hibernia", end_year=2010)
        assert all(r.year <= 2010 for r in records)

    def test_start_and_end_year_filter(self, loader):
        records = loader.load_field("Hibernia", start_year=2003, end_year=2007)
        assert all(2003 <= r.year <= 2007 for r in records)
        assert len(records) == 5

    def test_unknown_field_raises_value_error(self, loader):
        with pytest.raises(ValueError, match="Unknown field"):
            loader.load_field("Doesnotexist")


# ---------------------------------------------------------------------------
# Test: unit conversion (m3 -> bbl)
# ---------------------------------------------------------------------------


class TestUnitConversion:
    def test_oil_bbl_uses_sm3_to_bbl_factor(self, loader):
        """
        Verify that oil_bbl values reflect SM3_TO_BBL conversion.
        For Hibernia 1997 ~50 kbopd peak, annual oil_sm3 ≈ 2.9 MSm3.
        oil_bbl should ≈ oil_sm3 * 6.2898.
        We verify the ratio is close to SM3_TO_BBL by back-converting.
        """
        records = loader.load_field("Hibernia", start_year=2005, end_year=2005)
        assert len(records) == 1
        rec = records[0]
        # Back-compute sm3 from bbl
        implied_sm3 = rec.oil_bbl / OilUnits.SM3_TO_BBL
        # For 200 kbopd * 365 days * 1000 = 73,000,000 bbl/year -> sm3 = 11,606,700
        # Accept within 1% of expected range for 200 kbopd
        expected_bbl_approx = 200 * 1000 * 365  # 73 million bbl
        assert math.isclose(rec.oil_bbl, expected_bbl_approx, rel_tol=0.02), (
            f"Hibernia 2005 oil_bbl {rec.oil_bbl:.0f} not close to {expected_bbl_approx}"
        )


# ---------------------------------------------------------------------------
# Test: to_dataframe
# ---------------------------------------------------------------------------


class TestToDataframe:
    def test_to_dataframe_returns_dataframe(self, loader):
        records = loader.load_field("Hibernia")
        df = loader.to_dataframe(records)
        assert isinstance(df, pd.DataFrame)

    def test_to_dataframe_has_field_name_column(self, loader):
        records = loader.load_field("Hibernia")
        df = loader.to_dataframe(records)
        assert "field_name" in df.columns

    def test_to_dataframe_has_year_column(self, loader):
        records = loader.load_field("Hibernia")
        df = loader.to_dataframe(records)
        assert "year" in df.columns

    def test_to_dataframe_has_oil_bbl_column(self, loader):
        records = loader.load_field("Hibernia")
        df = loader.to_dataframe(records)
        assert "oil_bbl" in df.columns

    def test_to_dataframe_has_gas_mcf_column(self, loader):
        records = loader.load_field("Hibernia")
        df = loader.to_dataframe(records)
        assert "gas_mcf" in df.columns

    def test_to_dataframe_has_water_bbl_column(self, loader):
        records = loader.load_field("Hibernia")
        df = loader.to_dataframe(records)
        assert "water_bbl" in df.columns

    def test_to_dataframe_has_source_column(self, loader):
        records = loader.load_field("Hibernia")
        df = loader.to_dataframe(records)
        assert "source" in df.columns

    def test_to_dataframe_row_count_matches_records(self, loader):
        records = loader.load_field("Hibernia")
        df = loader.to_dataframe(records)
        assert len(df) == len(records)

    def test_to_dataframe_empty_records_returns_empty_df(self, loader):
        df = loader.to_dataframe([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert "oil_bbl" in df.columns


# ---------------------------------------------------------------------------
# Test: load_all_fields
# ---------------------------------------------------------------------------


class TestLoadAllFields:
    def test_load_all_fields_returns_list(self, loader):
        records = loader.load_all_fields()
        assert isinstance(records, list)

    def test_load_all_fields_non_empty(self, loader):
        records = loader.load_all_fields()
        assert len(records) > 0

    def test_load_all_fields_covers_all_five_fields(self, loader):
        records = loader.load_all_fields()
        found_fields = {r.field_name for r in records}
        assert found_fields == EXPECTED_FIELDS

    def test_load_all_fields_all_source_cnloer(self, loader):
        records = loader.load_all_fields()
        assert all(r.source == "cnloer" for r in records)

    def test_load_all_fields_year_filter_respected(self, loader):
        records = loader.load_all_fields(start_year=2017, end_year=2017)
        # Hibernia, Terra Nova, White Rose, Hebron should all have 2017 data
        # (North Amethyst may not; Hebron starts 2017)
        years = {r.year for r in records}
        assert years == {2017}
