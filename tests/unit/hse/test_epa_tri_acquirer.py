"""Tests for EPA TRI acquirer module."""

import pytest
import pandas as pd

from worldenergydata.hse.acquirers.epa_tri_acquirer import (
    DEFAULT_END_YEAR,
    DEFAULT_START_YEAR,
    EPATRIAcquirer,
    OIL_GAS_NAICS_PREFIXES,
    OIL_GAS_SIC_CODES,
    parse_years,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_sic_codes(self):
        assert "1311" in OIL_GAS_SIC_CODES
        assert "2911" in OIL_GAS_SIC_CODES
        assert len(OIL_GAS_SIC_CODES) > 5

    def test_naics_prefixes(self):
        assert "211" in OIL_GAS_NAICS_PREFIXES
        assert "324" in OIL_GAS_NAICS_PREFIXES

    def test_default_years(self):
        assert DEFAULT_START_YEAR == 2020
        assert DEFAULT_END_YEAR == 2024


# ---------------------------------------------------------------------------
# parse_years
# ---------------------------------------------------------------------------

class TestParseYears:
    def test_single_year(self):
        assert parse_years("2020") == [2020]

    def test_range(self):
        result = parse_years("2020-2023")
        assert result == [2020, 2021, 2022, 2023]

    def test_comma_separated(self):
        result = parse_years("2020,2022,2024")
        assert result == [2020, 2022, 2024]

    def test_mixed(self):
        result = parse_years("2018,2020-2022")
        assert result == [2018, 2020, 2021, 2022]

    def test_sorted(self):
        result = parse_years("2024,2020")
        assert result == [2020, 2024]

    def test_deduplicates(self):
        result = parse_years("2020,2020-2022")
        assert result == [2020, 2021, 2022]

    def test_whitespace(self):
        result = parse_years(" 2020 , 2021 ")
        assert result == [2020, 2021]


# ---------------------------------------------------------------------------
# EPATRIAcquirer init
# ---------------------------------------------------------------------------

class TestEPATRIAcquirerInit:
    def test_defaults(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path)
        assert acq.output_dir == tmp_path
        assert acq.force is False
        assert acq.filter_industry is True
        assert len(acq.years) == DEFAULT_END_YEAR - DEFAULT_START_YEAR + 1

    def test_custom_years(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path, years=[2020, 2021])
        assert acq.years == [2020, 2021]

    def test_force_flag(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path, force=True)
        assert acq.force is True


# ---------------------------------------------------------------------------
# _filter_oil_gas
# ---------------------------------------------------------------------------

class TestFilterOilGas:
    def test_filter_by_sic(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path)
        df = pd.DataFrame({
            "PRIMARY SIC": ["1311", "9999", "2911", "3333"],
            "FACILITY_NAME": ["Oil Co", "Unrelated", "Refinery", "Other"],
        })
        result = acq._filter_oil_gas(df, 2023)
        assert len(result) == 2
        assert "Oil Co" in result["FACILITY_NAME"].values
        assert "Refinery" in result["FACILITY_NAME"].values

    def test_filter_by_naics(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path)
        df = pd.DataFrame({
            "PRIMARY NAICS": ["211120", "999999", "324110"],
            "FACILITY_NAME": ["Extraction", "Unrelated", "Petroleum"],
        })
        result = acq._filter_oil_gas(df, 2023)
        assert len(result) == 2

    def test_filter_by_industry_desc(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path)
        df = pd.DataFrame({
            "INDUSTRY SECTOR": ["Petroleum Refining", "Chemical Manufacturing", "Oil and Gas Extraction"],
            "FACILITY_NAME": ["Refinery", "Chemical", "Driller"],
        })
        result = acq._filter_oil_gas(df, 2023)
        assert len(result) == 2

    def test_no_matching_columns(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path)
        df = pd.DataFrame({
            "RANDOM_COL": ["A", "B"],
        })
        result = acq._filter_oil_gas(df, 2023)
        assert len(result) == 0

    def test_case_insensitive_column_matching(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path)
        df = pd.DataFrame({
            "primary sic": ["1311", "9999"],
            "FACILITY_NAME": ["Oil Co", "Other"],
        })
        result = acq._filter_oil_gas(df, 2023)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _combine_years
# ---------------------------------------------------------------------------

class TestCombineYears:
    def test_basic(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path, years=[2020, 2021])
        f1 = tmp_path / "year1.csv"
        f2 = tmp_path / "year2.csv"
        pd.DataFrame({"col": [1, 2]}).to_csv(f1, index=False)
        pd.DataFrame({"col": [3]}).to_csv(f2, index=False)
        result = acq._combine_years([f1, f2])
        assert result is not None
        combined = pd.read_csv(result)
        assert len(combined) == 3

    def test_empty_files(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path, years=[2020])
        result = acq._combine_years([])
        assert result is None

    def test_nonexistent_files(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path, years=[2020])
        result = acq._combine_years([tmp_path / "missing.csv"])
        assert result is None


# ---------------------------------------------------------------------------
# _acquire_year (skip existing)
# ---------------------------------------------------------------------------

class TestAcquireYear:
    def test_skips_existing(self, tmp_path):
        acq = EPATRIAcquirer(output_dir=tmp_path, years=[2023], force=False)
        existing = tmp_path / "tri_basic_2023_oil_gas.csv"
        existing.write_text("col1\n1\n")
        result = acq._acquire_year(2023)
        assert result == existing
