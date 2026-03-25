"""Tests for DPR basin production loader (Permian, Bakken, Eagle Ford, etc.)."""

import pandas as pd
import pytest

from worldenergydata.eia_us.production.basin_production import (
    BasinProductionLoader,
    DPR_BASINS,
    BasinRecord,
)


def make_mock_dpr_response(basin: str, n_months: int = 12):
    """Mock DPR data — rig count, new well IP, legacy decline."""
    records = []
    for i in range(n_months):
        year = 2023 + i // 12
        month = (i % 12) + 1
        records.append({
            "period": f"{year}-{month:02d}",
            "basin": basin,
            "rig_count": 200 - i,
            "new_well_ip_bopd": 800.0 - i * 2.0,
            "legacy_decline_bopd": -50000.0 - i * 100.0,
            "total_production_bopd": 4_500_000.0 + i * 1000.0,
        })
    return records


class TestDPRBasins:
    def test_permian_in_basins(self):
        assert "Permian" in DPR_BASINS

    def test_bakken_in_basins(self):
        assert "Bakken" in DPR_BASINS

    def test_eagle_ford_in_basins(self):
        assert "Eagle Ford" in DPR_BASINS

    def test_dj_basin_in_basins(self):
        assert "DJ Basin" in DPR_BASINS or "Niobrara" in DPR_BASINS

    def test_appalachian_in_basins(self):
        assert "Appalachian" in DPR_BASINS

    def test_haynesville_in_basins(self):
        assert "Haynesville" in DPR_BASINS

    def test_anadarko_in_basins(self):
        assert "Anadarko" in DPR_BASINS

    def test_at_least_7_basins(self):
        assert len(DPR_BASINS) >= 7


class TestBasinRecord:
    def test_basin_record_fields(self):
        rec = BasinRecord(
            period="2024-01",
            basin="Permian",
            rig_count=200,
            new_well_ip_bopd=850.0,
            legacy_decline_bopd=-60000.0,
            total_production_bopd=4_600_000.0,
        )
        assert rec.basin == "Permian"
        assert rec.rig_count == 200
        assert rec.new_well_ip_bopd == pytest.approx(850.0)

    def test_basin_record_net_change(self):
        rec = BasinRecord(
            period="2024-01",
            basin="Bakken",
            rig_count=40,
            new_well_ip_bopd=500.0,
            legacy_decline_bopd=-20000.0,
            total_production_bopd=1_100_000.0,
        )
        # net = new well additions + legacy decline (decline is negative)
        net = rec.new_well_ip_bopd + rec.legacy_decline_bopd
        assert net < rec.new_well_ip_bopd


class TestBasinProductionLoader:
    @pytest.fixture
    def loader(self):
        return BasinProductionLoader()

    def test_load_returns_dataframe(self, loader):
        raw = make_mock_dpr_response("Permian", 12)
        df = loader.load(raw)
        assert isinstance(df, pd.DataFrame)

    def test_load_has_required_columns(self, loader):
        raw = make_mock_dpr_response("Permian", 6)
        df = loader.load(raw)
        for col in ["period", "basin", "rig_count", "new_well_ip_bopd",
                    "legacy_decline_bopd", "total_production_bopd"]:
            assert col in df.columns

    def test_load_empty_returns_empty_dataframe(self, loader):
        df = loader.load([])
        assert df.empty

    def test_load_multiple_basins(self, loader):
        all_records = []
        for basin in ["Permian", "Bakken", "Eagle Ford", "Appalachian"]:
            all_records.extend(make_mock_dpr_response(basin, 6))
        df = loader.load(all_records)
        basins_found = df["basin"].unique()
        assert "Permian" in basins_found
        assert "Bakken" in basins_found

    def test_filter_by_basin(self, loader):
        all_records = []
        for basin in ["Permian", "Bakken"]:
            all_records.extend(make_mock_dpr_response(basin, 6))
        df = loader.load(all_records)
        permian_only = loader.filter_basin(df, "Permian")
        assert all(permian_only["basin"] == "Permian")

    def test_rig_count_is_integer_or_float(self, loader):
        raw = make_mock_dpr_response("Permian", 3)
        df = loader.load(raw)
        assert df["rig_count"].dtype in ("int64", "float64")

    def test_legacy_decline_is_negative(self, loader):
        raw = make_mock_dpr_response("Bakken", 12)
        df = loader.load(raw)
        assert all(df["legacy_decline_bopd"] <= 0)
