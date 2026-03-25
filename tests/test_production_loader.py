# ABOUTME: TDD tests for BSEE ProductionLoader (WRK-1232).
# ABOUTME: Tests loading and filtering production data from pickled DataFrames.

"""Tests for BSEE production data loader."""

import pickle

import pandas as pd


def _make_production_df():
    """Create a test production DataFrame matching BSEE binary schema."""
    return pd.DataFrame(
        [
            {
                "LEASE_NUMBER": "G12345",
                "PROD_MONTH": 1,
                "PROD_YEAR": 2024,
                "LEASE_OIL_PROD": 15000.0,
                "LEASE_GWG_PROD": 50000.0,
                "LEASE_CONDN_PROD": 500.0,
                "LEASE_OWG_PROD": 200.0,
                "LEASE_WTR_PROD": 8000.0,
                "LEASE_DPTH_CD": "S",
                "MON_PROD_CD": "P",
            },
            {
                "LEASE_NUMBER": "G12345",
                "PROD_MONTH": 2,
                "PROD_YEAR": 2024,
                "LEASE_OIL_PROD": 14500.0,
                "LEASE_GWG_PROD": 48000.0,
                "LEASE_CONDN_PROD": 450.0,
                "LEASE_OWG_PROD": 180.0,
                "LEASE_WTR_PROD": 8500.0,
                "LEASE_DPTH_CD": "S",
                "MON_PROD_CD": "P",
            },
            {
                "LEASE_NUMBER": "G67890",
                "PROD_MONTH": 1,
                "PROD_YEAR": 2024,
                "LEASE_OIL_PROD": 25000.0,
                "LEASE_GWG_PROD": 80000.0,
                "LEASE_CONDN_PROD": 800.0,
                "LEASE_OWG_PROD": 300.0,
                "LEASE_WTR_PROD": 12000.0,
                "LEASE_DPTH_CD": "D",
                "MON_PROD_CD": "P",
            },
            {
                "LEASE_NUMBER": "G67890",
                "PROD_MONTH": 2,
                "PROD_YEAR": 2024,
                "LEASE_OIL_PROD": 24000.0,
                "LEASE_GWG_PROD": 78000.0,
                "LEASE_CONDN_PROD": 750.0,
                "LEASE_OWG_PROD": 280.0,
                "LEASE_WTR_PROD": 12500.0,
                "LEASE_DPTH_CD": "D",
                "MON_PROD_CD": "P",
            },
        ]
    )


def _write_fixture(tmp_path, name, df):
    p = tmp_path / name
    with open(p, "wb") as f:
        pickle.dump(df, f)


class TestProductionLoaderInit:
    def test_creates_with_default(self):
        from worldenergydata.bsee.data.loaders.production.production_loader import (
            ProductionLoader,
        )

        loader = ProductionLoader()
        assert loader is not None

    def test_creates_with_custom_dir(self, tmp_path):
        from worldenergydata.bsee.data.loaders.production.production_loader import (
            ProductionLoader,
        )

        loader = ProductionLoader(bin_dir=str(tmp_path))
        assert loader._bin_dir == str(tmp_path)


class TestLoadProduction:
    def test_load_returns_dataframe(self, tmp_path):
        from worldenergydata.bsee.data.loaders.production.production_loader import (
            ProductionLoader,
        )

        _write_fixture(tmp_path, "mv_productiondata.bin", _make_production_df())
        loader = ProductionLoader(bin_dir=str(tmp_path))
        df = loader.load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4

    def test_load_caches(self, tmp_path):
        from worldenergydata.bsee.data.loaders.production.production_loader import (
            ProductionLoader,
        )

        _write_fixture(tmp_path, "mv_productiondata.bin", _make_production_df())
        loader = ProductionLoader(bin_dir=str(tmp_path))
        df1 = loader.load()
        df2 = loader.load()
        assert df1 is df2

    def test_load_missing_returns_none(self, tmp_path):
        from worldenergydata.bsee.data.loaders.production.production_loader import (
            ProductionLoader,
        )

        loader = ProductionLoader(bin_dir=str(tmp_path))
        assert loader.load() is None


class TestGetByLease:
    def test_existing_lease(self, tmp_path):
        from worldenergydata.bsee.data.loaders.production.production_loader import (
            ProductionLoader,
        )

        _write_fixture(tmp_path, "mv_productiondata.bin", _make_production_df())
        loader = ProductionLoader(bin_dir=str(tmp_path))
        df = loader.get_by_lease("G12345")
        assert len(df) == 2
        assert (df["LEASE_NUMBER"] == "G12345").all()

    def test_missing_lease_returns_empty(self, tmp_path):
        from worldenergydata.bsee.data.loaders.production.production_loader import (
            ProductionLoader,
        )

        _write_fixture(tmp_path, "mv_productiondata.bin", _make_production_df())
        loader = ProductionLoader(bin_dir=str(tmp_path))
        df = loader.get_by_lease("GXXXXX")
        assert len(df) == 0


class TestGetByYear:
    def test_filter_by_year(self, tmp_path):
        from worldenergydata.bsee.data.loaders.production.production_loader import (
            ProductionLoader,
        )

        _write_fixture(tmp_path, "mv_productiondata.bin", _make_production_df())
        loader = ProductionLoader(bin_dir=str(tmp_path))
        df = loader.get_by_year(2024)
        assert len(df) == 4  # All fixture data is 2024


class TestGetByLeaseAndYear:
    def test_combined_filter(self, tmp_path):
        from worldenergydata.bsee.data.loaders.production.production_loader import (
            ProductionLoader,
        )

        _write_fixture(tmp_path, "mv_productiondata.bin", _make_production_df())
        loader = ProductionLoader(bin_dir=str(tmp_path))
        df = loader.get_by_lease_and_year("G67890", 2024)
        assert len(df) == 2
        assert (df["LEASE_NUMBER"] == "G67890").all()


class TestSummarize:
    def test_annual_summary(self, tmp_path):
        from worldenergydata.bsee.data.loaders.production.production_loader import (
            ProductionLoader,
        )

        _write_fixture(tmp_path, "mv_productiondata.bin", _make_production_df())
        loader = ProductionLoader(bin_dir=str(tmp_path))
        summary = loader.annual_summary(2024)
        assert "total_oil_bbl" in summary
        assert "total_gas_mcf" in summary
        assert "lease_count" in summary
        assert summary["lease_count"] == 2
        assert summary["total_oil_bbl"] == 15000 + 14500 + 25000 + 24000
