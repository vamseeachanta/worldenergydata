# ABOUTME: TDD tests for BSEE CompanyLoader (WRK-1231).
# ABOUTME: Tests loading, filtering by operator ID and company name from pickled DataFrames.

"""Tests for BSEE company data loader."""

import pickle

import pandas as pd


def _make_company_df(active_only=True):
    """Create a test company DataFrame matching BSEE binary schema."""
    data = [
        {
            "MMS_COMPANY_NUM": 100,
            "BUS_ASC_NAME": "Acme Offshore Inc.",
            "SORT_NAME": "ACME OFFSHORE INC",
            "MMS_START_DATE": "1/15/2000",
            "MMS_TERM_DATE": pd.NA if active_only else "6/30/2020",
            "GOM_REGION_CODE": "G",
            "PAC_REGION_CODE": "P",
            "ALASKA_RGN_CODE": "Y",
            "ATL_REGION_CODE": "A",
            "CITY_NAME": "Houston",
            "POSTAL_ST_CODE": "TX",
        },
        {
            "MMS_COMPANY_NUM": 200,
            "BUS_ASC_NAME": "Gulf Drilling LLC",
            "SORT_NAME": "GULF DRILLING LLC",
            "MMS_START_DATE": "3/10/2010",
            "MMS_TERM_DATE": pd.NA,
            "GOM_REGION_CODE": "G",
            "PAC_REGION_CODE": pd.NA,
            "ALASKA_RGN_CODE": pd.NA,
            "ATL_REGION_CODE": pd.NA,
            "CITY_NAME": "New Orleans",
            "POSTAL_ST_CODE": "LA",
        },
        {
            "MMS_COMPANY_NUM": 300,
            "BUS_ASC_NAME": "Pacific Energy Corp.",
            "SORT_NAME": "PACIFIC ENERGY CORP",
            "MMS_START_DATE": "7/1/2015",
            "MMS_TERM_DATE": pd.NA,
            "GOM_REGION_CODE": pd.NA,
            "PAC_REGION_CODE": "P",
            "ALASKA_RGN_CODE": pd.NA,
            "ATL_REGION_CODE": pd.NA,
            "CITY_NAME": "Los Angeles",
            "POSTAL_ST_CODE": "CA",
        },
    ]
    return pd.DataFrame(data)


def _write_fixture(tmp_path, name, df):
    """Write a pickled DataFrame fixture."""
    p = tmp_path / name
    with open(p, "wb") as f:
        pickle.dump(df, f)
    return p


class TestCompanyLoaderInit:
    """Tests for CompanyLoader construction."""

    def test_creates_with_default_bin_dir(self):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        loader = CompanyLoader()
        assert loader is not None

    def test_creates_with_custom_bin_dir(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        loader = CompanyLoader(bin_dir=str(tmp_path))
        assert loader._bin_dir == str(tmp_path)


class TestLoadActive:
    """Tests for loading active companies."""

    def test_load_active_returns_dataframe(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(tmp_path, "mv_companies_active.bin", _make_company_df())
        loader = CompanyLoader(bin_dir=str(tmp_path))
        df = loader.load_active()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    def test_load_active_caches(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(tmp_path, "mv_companies_active.bin", _make_company_df())
        loader = CompanyLoader(bin_dir=str(tmp_path))
        df1 = loader.load_active()
        df2 = loader.load_active()
        assert df1 is df2

    def test_load_active_empty_dir_returns_none(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        loader = CompanyLoader(bin_dir=str(tmp_path))
        assert loader.load_active() is None


class TestLoadAll:
    """Tests for loading all companies (active + terminated)."""

    def test_load_all_returns_dataframe(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(
            tmp_path, "mv_companies_all.bin", _make_company_df(active_only=False)
        )
        loader = CompanyLoader(bin_dir=str(tmp_path))
        df = loader.load_all()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3


class TestGetByOperatorId:
    """Tests for filtering by MMS company number."""

    def test_find_existing_operator(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(tmp_path, "mv_companies_active.bin", _make_company_df())
        loader = CompanyLoader(bin_dir=str(tmp_path))
        df = loader.get_by_operator_id(200)
        assert len(df) == 1
        assert df.iloc[0]["BUS_ASC_NAME"] == "Gulf Drilling LLC"

    def test_missing_operator_returns_empty(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(tmp_path, "mv_companies_active.bin", _make_company_df())
        loader = CompanyLoader(bin_dir=str(tmp_path))
        df = loader.get_by_operator_id(999)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestGetByCompanyName:
    """Tests for searching by company name."""

    def test_exact_match(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(tmp_path, "mv_companies_active.bin", _make_company_df())
        loader = CompanyLoader(bin_dir=str(tmp_path))
        df = loader.get_by_company_name("Gulf Drilling")
        assert len(df) == 1

    def test_case_insensitive(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(tmp_path, "mv_companies_active.bin", _make_company_df())
        loader = CompanyLoader(bin_dir=str(tmp_path))
        df = loader.get_by_company_name("gulf drilling")
        assert len(df) == 1

    def test_partial_match(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(tmp_path, "mv_companies_active.bin", _make_company_df())
        loader = CompanyLoader(bin_dir=str(tmp_path))
        df = loader.get_by_company_name("Pacific")
        assert len(df) == 1

    def test_no_match_returns_empty(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(tmp_path, "mv_companies_active.bin", _make_company_df())
        loader = CompanyLoader(bin_dir=str(tmp_path))
        df = loader.get_by_company_name("Nonexistent Corp")
        assert len(df) == 0


class TestGetByRegion:
    """Tests for filtering by region code."""

    def test_gom_region(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(tmp_path, "mv_companies_active.bin", _make_company_df())
        loader = CompanyLoader(bin_dir=str(tmp_path))
        df = loader.get_by_region("GOM")
        assert len(df) == 2  # Acme + Gulf

    def test_pacific_region(self, tmp_path):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(tmp_path, "mv_companies_active.bin", _make_company_df())
        loader = CompanyLoader(bin_dir=str(tmp_path))
        df = loader.get_by_region("PAC")
        assert len(df) == 2  # Acme + Pacific
