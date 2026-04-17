"""Tests for fdas.adapters.bsee_adapter adapter classes."""

import pandas as pd
import pytest

from worldenergydata.fdas.adapters.bsee_adapter import (
    AdapterError,
    BseeAdapter,
    LeaseMapping,
    ProductionAdapter,
    WellDataAdapter,
)

# ---------------------------------------------------------------------------
# LeaseMapping
# ---------------------------------------------------------------------------


class TestLeaseMapping:
    def test_init(self):
        lm = LeaseMapping(
            lease_number="G09868",
            lease_name="MC 941",
            dev_name="Anchor",
            dev_system="subsea15",
            water_depth=5183.0,
        )
        assert lm.lease_number == "G09868"
        assert lm.dev_system == "subsea15"

    def test_to_dict(self):
        lm = LeaseMapping("G09868", "MC 941", "Anchor", "subsea15", 5183.0)
        d = lm.to_dict()
        assert d["LEASE_NUMBER"] == "G09868"
        assert d["DEV_NAME"] == "Anchor"
        assert d["WATER_DEPTH"] == 5183.0


# ---------------------------------------------------------------------------
# WellDataAdapter
# ---------------------------------------------------------------------------


class TestWellDataAdapter:
    def test_init(self):
        adapter = WellDataAdapter("/tmp/fake.csv")
        assert adapter.well_data is None

    def test_load_success(self, tmp_path):
        csv = tmp_path / "well_data.csv"
        csv.write_text(
            "LEASE_NUMBER,COMPLEX_ID_NUMBER,WATER_DEPTH\nG001,C001,3000\nG002,C001,5000\n"
        )
        adapter = WellDataAdapter(str(csv))
        df = adapter.load()
        assert len(df) == 2
        assert adapter.well_data is not None

    def test_load_missing_file(self):
        adapter = WellDataAdapter("/nonexistent/path.csv")
        with pytest.raises(AdapterError, match="Failed to load"):
            adapter.load()

    def test_add_dev_system_not_loaded(self):
        adapter = WellDataAdapter("/tmp/fake.csv")
        with pytest.raises(AdapterError, match="not loaded"):
            adapter.add_dev_system_classification()

    def test_add_dev_system(self, tmp_path):
        csv = tmp_path / "well_data.csv"
        csv.write_text(
            "LEASE_NUMBER,COMPLEX_ID_NUMBER,WATER_DEPTH\nG001,C001,3000\nG002,C001,5000\n"
        )
        adapter = WellDataAdapter(str(csv))
        adapter.load()
        result = adapter.add_dev_system_classification()
        assert "DEV_SYSTEM" in result.columns

    def test_create_lease_mapping_not_loaded(self):
        adapter = WellDataAdapter("/tmp/fake.csv")
        with pytest.raises(AdapterError, match="not loaded"):
            adapter.create_lease_mapping()

    def test_create_lease_mapping(self, tmp_path):
        csv = tmp_path / "well_data.csv"
        csv.write_text(
            "LEASE_NUMBER,COMPLEX_ID_NUMBER,WATER_DEPTH\nG001,C001,3000\nG002,C001,5000\n"
        )
        adapter = WellDataAdapter(str(csv))
        adapter.load()
        adapter.add_dev_system_classification()
        mappings = adapter.create_lease_mapping()
        assert len(mappings) == 2
        assert all(isinstance(m, LeaseMapping) for m in mappings)

    def test_create_lease_mapping_missing_columns(self, tmp_path):
        csv = tmp_path / "well_data.csv"
        csv.write_text("LEASE_NUMBER,OTHER_COL\nG001,X\n")
        adapter = WellDataAdapter(str(csv))
        adapter.load()
        with pytest.raises(AdapterError, match="Missing required columns"):
            adapter.create_lease_mapping()

    def test_save_enhanced_not_enhanced(self, tmp_path):
        csv = tmp_path / "well_data.csv"
        csv.write_text("LEASE_NUMBER,WATER_DEPTH\nG001,3000\n")
        adapter = WellDataAdapter(str(csv))
        adapter.load()
        with pytest.raises(AdapterError, match="not enhanced"):
            adapter.save_enhanced_well_data(str(tmp_path / "out.csv"))

    def test_save_enhanced(self, tmp_path):
        csv = tmp_path / "well_data.csv"
        csv.write_text("LEASE_NUMBER,COMPLEX_ID_NUMBER,WATER_DEPTH\nG001,C001,3000\n")
        adapter = WellDataAdapter(str(csv))
        adapter.load()
        adapter.add_dev_system_classification()
        out = tmp_path / "out.csv"
        adapter.save_enhanced_well_data(str(out))
        assert out.exists()


# ---------------------------------------------------------------------------
# ProductionAdapter
# ---------------------------------------------------------------------------


class TestProductionAdapter:
    def _make_csv(self, tmp_path):
        csv = tmp_path / "production.csv"
        csv.write_text(
            "LEASE_NUMBER,PROD_DATE,OIL_VOLUME,WATER_VOLUME,GAS_VOLUME\n"
            "G001,2024-01-01,1000,200,5000\n"
            "G001,2024-02-01,950,210,4800\n"
            "G002,2024-01-01,800,150,4000\n"
        )
        return csv

    def _make_mappings(self):
        return [
            LeaseMapping("G001", "MC 100", "Dev-A", "subsea15", 3000),
            LeaseMapping("G002", "MC 200", "Dev-B", "dry", 500),
        ]

    def test_init(self):
        adapter = ProductionAdapter("/tmp/fake.csv")
        assert adapter.production_data is None
        assert adapter.lease_mappings == []

    def test_load_success(self, tmp_path):
        csv = self._make_csv(tmp_path)
        adapter = ProductionAdapter(str(csv))
        df = adapter.load()
        assert len(df) == 3

    def test_load_missing_file(self):
        adapter = ProductionAdapter("/nonexistent/path.csv")
        with pytest.raises(AdapterError, match="Failed to load"):
            adapter.load()

    def test_enhance_not_loaded(self):
        adapter = ProductionAdapter("/tmp/fake.csv")
        with pytest.raises(AdapterError, match="not loaded"):
            adapter.enhance_with_lease_info()

    def test_enhance_with_lease_info(self, tmp_path):
        csv = self._make_csv(tmp_path)
        adapter = ProductionAdapter(str(csv), self._make_mappings())
        adapter.load()
        result = adapter.enhance_with_lease_info()
        assert "DEV_NAME" in result.columns
        assert "LEASE_NAME" in result.columns

    def test_aggregate_monthly_not_loaded(self):
        adapter = ProductionAdapter("/tmp/fake.csv")
        with pytest.raises(AdapterError, match="not loaded"):
            adapter.aggregate_monthly()

    def test_aggregate_monthly(self, tmp_path):
        csv = self._make_csv(tmp_path)
        adapter = ProductionAdapter(str(csv), self._make_mappings())
        adapter.load()
        adapter.enhance_with_lease_info()
        result = adapter.aggregate_monthly(by="LEASE_NUMBER")
        assert "MONTHLY_OIL_VOLUME" in result.columns


# ---------------------------------------------------------------------------
# BseeAdapter
# ---------------------------------------------------------------------------


class TestBseeAdapter:
    def test_init(self):
        adapter = BseeAdapter("/tmp/bsee_data")
        assert adapter.well_adapter is None
        assert adapter.production_adapter is None

    def test_get_lease_mappings_not_loaded(self):
        adapter = BseeAdapter("/tmp/bsee_data")
        with pytest.raises(AdapterError, match="not created"):
            adapter.get_lease_mappings_df()

    def test_get_development_production_not_loaded(self):
        adapter = BseeAdapter("/tmp/bsee_data")
        with pytest.raises(AdapterError, match="not initialized"):
            adapter.get_development_production("Dev-A")
