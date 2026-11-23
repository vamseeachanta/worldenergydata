# ABOUTME: TDD tests for BSEE CompanyLoader (WRK-1231).
# ABOUTME: Tests loading, filtering by operator ID and company name from pickled DataFrames.

"""Tests for BSEE company data loader."""

import logging
import pickle
from unittest.mock import call, patch

import pandas as pd
import pytest


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


def _write_fixture(tmp_path, name, payload):
    """Write a trusted, locally created pickle fixture."""
    p = tmp_path / name
    with open(p, "wb") as f:
        pickle.dump(payload, f)
    return p


@pytest.fixture
def boundary_company_frames():
    """Create independently enumerated active/all company fixtures."""
    # Synthetic truth table for #128; all numeric expectations below cite this table.
    # ID | label     | membership  | ALASKA | ATL | termination date
    # 11 | company-a | active,all  | Y      | -   | absent
    # 22 | company-b | active,all  | -      | A   | absent
    # 33 | company-c | active,all  | Y      | A   | absent
    # 44 | company-d | all         | -      | -   | 2000-01-01
    # Hand enumeration: active=3, all=4, ALASKA=(11,33), ATL=(22,33).
    columns = [
        "MMS_COMPANY_NUM",
        "BUS_ASC_NAME",
        "ALASKA_RGN_CODE",
        "ATL_REGION_CODE",
        "MMS_TERM_DATE",
    ]
    active_rows = [
        (11, "company-a", "Y", pd.NA, pd.NA),
        (22, "company-b", pd.NA, "A", pd.NA),
        (33, "company-c", "Y", "A", pd.NA),
    ]
    all_rows = active_rows + [(44, "company-d", pd.NA, pd.NA, "2000-01-01")]
    return pd.DataFrame(active_rows, columns=columns), pd.DataFrame(
        all_rows, columns=columns
    )


class TestLoadBin:
    """Tests for rejected payloads from trusted temporary pickle fixtures."""

    @pytest.mark.parametrize(
        "method,filename",
        [
            ("load_active", "mv_companies_active.bin"),
            ("load_all", "mv_companies_all.bin"),
        ],
    )
    def test_non_dataframe_returns_none_with_warning(
        self, tmp_path, caplog, method, filename
    ):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        _write_fixture(tmp_path, filename, {"payload": "synthetic"})
        loader = CompanyLoader(bin_dir=tmp_path)
        with caplog.at_level(logging.WARNING, logger=CompanyLoader.__module__):
            assert getattr(loader, method)() is None
        assert caplog.record_tuples == [
            (
                CompanyLoader.__module__,
                logging.WARNING,
                f"Unexpected type in {filename}: dict",
            )
        ]


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

    def test_missing_all_input_returns_none(self, tmp_path, boundary_company_frames):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        active, _ = boundary_company_frames
        _write_fixture(tmp_path, "mv_companies_active.bin", active)
        loader = CompanyLoader(bin_dir=tmp_path)
        assert loader.load_all() is None
        loaded_active = loader.load_active()
        assert loaded_active["MMS_COMPANY_NUM"].tolist() == [11, 22, 33]
        assert len(loaded_active) == 3  # Active rows in the synthetic truth table.
        assert loader.load_all() is None


class TestCompanyCaches:
    """Tests for independent caches with real, distinct temporary file reads."""

    @pytest.mark.parametrize(
        "first_method,second_method",
        [("load_active", "load_all"), ("load_all", "load_active")],
    )
    def test_active_and_all_caches_are_independent(
        self, tmp_path, boundary_company_frames, first_method, second_method
    ):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        active, all_companies = boundary_company_frames
        filenames = {
            "load_active": "mv_companies_active.bin",
            "load_all": "mv_companies_all.bin",
        }
        _write_fixture(tmp_path, filenames["load_active"], active)
        _write_fixture(tmp_path, filenames["load_all"], all_companies)
        loader = CompanyLoader(bin_dir=tmp_path)
        loaded = {}
        # Wrap the real reader: each distinct file is read once, then cached.
        with patch.object(loader, "_load_bin", wraps=loader._load_bin) as reader:
            for method in (first_method, second_method):
                loaded[method] = getattr(loader, method)()
                assert getattr(loader, method)() is loaded[method]
            assert loader.load_active() is loaded["load_active"]
            assert loader.load_all() is loaded["load_all"]
            assert reader.call_args_list == [
                call(filenames[first_method]),
                call(filenames[second_method]),
            ]
        assert loaded["load_active"] is not loaded["load_all"]
        # IDs and cardinalities are hand-enumerated from the synthetic truth table.
        assert loaded["load_active"]["MMS_COMPANY_NUM"].tolist() == [11, 22, 33]
        assert len(loaded["load_active"]) == 3
        assert loaded["load_all"]["MMS_COMPANY_NUM"].tolist() == [11, 22, 33, 44]
        assert len(loaded["load_all"]) == 4
        pd.testing.assert_frame_equal(loaded["load_active"], active)
        pd.testing.assert_frame_equal(loaded["load_all"], all_companies)


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

    @pytest.mark.parametrize(
        "region,expected_ids",
        [
            ("ALASKA", [11, 33]),
            ("alaska", [11, 33]),
            ("AlAsKa", [11, 33]),
            ("ATL", [22, 33]),
            ("atl", [22, 33]),
            ("AtL", [22, 33]),
        ],
    )
    def test_alaska_and_atl_case_insensitive(
        self, tmp_path, boundary_company_frames, region, expected_ids
    ):
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        active, _ = boundary_company_frames
        _write_fixture(tmp_path, "mv_companies_active.bin", active)
        loader = CompanyLoader(bin_dir=tmp_path)
        result = loader.get_by_region(region)
        # Membership and count come from the synthetic truth table for #128.
        assert result["MMS_COMPANY_NUM"].tolist() == expected_ids
        assert len(result) == len(expected_ids)

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
