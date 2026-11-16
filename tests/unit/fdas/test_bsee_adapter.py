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


@pytest.mark.parametrize("by", ["DEV_NAME", "LEASE_NUMBER", "API_WELL_NUMBER"])
@pytest.mark.parametrize("include_gas", [True, False])
def test_monthly_canonical_columns_and_deprecated_aliases(tmp_path, by, include_gas):
    """Independent hand calculation for synthetic inputs (no conversion).

    January group A: oil = 10 + 20 = 30 bbl; water = 2 + 3 = 5 bbl;
    gas = 100 + 200 = 300 Mcf. February A = 7/1/70; January B = 4/6/40.
    Units follow fdas/data/production.py:ProductionProcessor.aggregate_monthly
    and adapters/contract.py:FDAS_PRODUCTION_COLUMNS (repository F2 contract).
    Removing canonical names, changing sums, or fabricating absent gas fails.
    """
    data = pd.DataFrame(
        {
            by: ["A", "A", "A", "B"],
            "PROD_DATE": ["2024-01-01", "2024-01-15", "2024-02-01", "2024-01-01"],
            "OIL_VOLUME": [10, 20, 7, 4],
            "WATER_VOLUME": [2, 3, 1, 6],
        }
    )
    if include_gas:
        data["GAS_VOLUME"] = [100, 200, 70, 40]
    path = tmp_path / "production.csv"
    data.to_csv(path, index=False)
    adapter = ProductionAdapter(str(path))
    adapter.load()
    with pytest.warns(DeprecationWarning, match="MONTHLY_.*_VOLUME") as recorded:
        monthly = adapter.aggregate_monthly(by=by)
    assert len(recorded) == 1
    assert "MONTHLY_OIL_BBL" in str(recorded[0].message)
    assert "MONTHLY_GAS_MCF" in str(recorded[0].message)
    expected = {
        "OIL": ("BBL", [30, 7, 4]),
        "WATER": ("BBL", [5, 1, 6]),
    }
    if include_gas:
        expected["GAS"] = ("MCF", [300, 70, 40])
    else:
        assert "MONTHLY_GAS_MCF" not in monthly
        assert "MONTHLY_GAS_VOLUME" not in monthly
    assert monthly[by].tolist() == ["A", "A", "B"]
    assert monthly["YEAR_MONTH"].astype(str).tolist() == [
        "2024-01",
        "2024-02",
        "2024-01",
    ]
    for fluid, (unit, values) in expected.items():
        canonical = monthly[f"MONTHLY_{fluid}_{unit}"]
        assert canonical.tolist() == values
        pd.testing.assert_series_equal(
            canonical, monthly[f"MONTHLY_{fluid}_VOLUME"], check_names=False
        )


def test_public_development_production_cashflow_column(tmp_path):
    """Cashflow extraction uses the independent sum 10 + 20 = 30 bbl.

    Synthetic input units and extraction method follow
    analysis/cashflow.py:CashflowEngine.generate_monthly_cashflow.
    Another development's 90 bbl must not enter the selected result.
    """
    path = tmp_path / "production.csv"
    path.write_text(
        "DEV_NAME,PROD_DATE,OIL_VOLUME,WATER_VOLUME\n"
        "Dev-A,2024-01-01,10,2\n"
        "Dev-A,2024-01-15,20,3\n"
        "Dev-B,2024-01-01,90,9\n"
    )
    public = BseeAdapter(str(tmp_path))
    public.production_adapter = ProductionAdapter(str(path))
    public.production_adapter.load()
    with pytest.warns(DeprecationWarning):
        monthly = public.get_development_production("Dev-A")
    # Exact column lookup used by the unchanged cashflow engine.
    oil = monthly.set_index("YEAR_MONTH")["MONTHLY_OIL_BBL"]
    assert {str(month): value for month, value in oil.items()} == {"2024-01": 30}


@pytest.mark.parametrize("include_gas", [True, False])
def test_empty_monthly_output_preserves_schema(tmp_path, include_gas):
    """An empty synthetic CSV has no observations; no gas is invented."""
    path = tmp_path / "empty.csv"
    columns = "DEV_NAME,PROD_DATE,OIL_VOLUME,WATER_VOLUME"
    if include_gas:
        columns += ",GAS_VOLUME"
    path.write_text(columns + "\n")
    adapter = ProductionAdapter(str(path))
    adapter.load()
    with pytest.warns(DeprecationWarning):
        result = adapter.aggregate_monthly()
    assert result.empty
    assert "MONTHLY_OIL_BBL" in result
    assert "MONTHLY_WATER_BBL" in result
    assert ("MONTHLY_GAS_MCF" in result) == include_gas
    assert ("MONTHLY_GAS_VOLUME" in result) == include_gas
