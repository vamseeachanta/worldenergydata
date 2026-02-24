"""Tests for DrillingRiserLoader."""

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.loaders.drilling_riser_loader import (
    DrillingRiserLoader,
)


@pytest.fixture
def sample_riser_data(tmp_path):
    """Create a minimal drilling riser CSV for testing."""
    data = {
        "COMPONENT_ID": [
            "RJ-21-75-BARE", "RJ-21-75-BUOY", "RJ-21-50-PUP",
            "BOP-SUB-18.75-15K", "BOP-SURF-13.625-5K",
            "LMRP-18.75-15K",
            "FJ-UPPER-21", "FJ-LOWER-21",
            "TJ-21-50",
        ],
        "COMPONENT_TYPE": [
            "riser_joint", "riser_joint", "riser_joint",
            "bop", "bop",
            "lmrp",
            "flex_joint", "flex_joint",
            "telescopic_joint",
        ],
        "MANUFACTURER": [
            None, None, None,
            "Cameron", None,
            "Cameron",
            None, None,
            None,
        ],
        "OD_IN": [21.0, 21.0, 21.0, None, None, None, None, None, 21.0],
        "LENGTH_FT": [75.0, 75.0, 50.0, None, None, None, None, None, None],
        "WEIGHT_AIR_KIPS": [22.5, 22.5, 15.0, 400.0, 45.0, 180.0, 8.5, 12.0, 35.0],
        "PRESSURE_RATING_PSI": [
            5000.0, 5000.0, 5000.0,
            15000.0, 5000.0,
            15000.0,
            5000.0, 5000.0,
            5000.0,
        ],
        "BOP_TYPE": [
            None, None, None,
            "subsea", "surface",
            None,
            None, None,
            None,
        ],
        "BORE_SIZE_IN": [
            None, None, None,
            18.75, 13.625,
            18.75,
            None, None,
            None,
        ],
        "BUOYANCY_COVERAGE_PCT": [0, 100, 0, None, None, None, None, None, None],
        "MAX_ANGLE_DEG": [None, None, None, None, None, None, 10.0, 10.0, None],
        "POSITION": [None, None, None, None, None, None, "upper", "lower", None],
        "STROKE_FT": [None, None, None, None, None, None, None, None, 50.0],
        "HEIGHT_FT": [None, None, None, 35.0, 18.0, 18.0, None, None, None],
        "CONNECTOR_TYPE": [
            None, None, None,
            None, None,
            "H-4 collet",
            None, None,
            None,
        ],
        "DATA_SOURCE": ["API 16R"] * 9,
        "NOTES": [None] * 9,
    }
    df = pd.DataFrame(data)
    csv_path = tmp_path / "drilling_riser_components.csv"
    df.to_csv(csv_path, index=False)
    return tmp_path


class TestDrillingRiserLoaderBasics:
    def test_load_returns_dataframe(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        df = loader.load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 9

    def test_missing_data_dir_returns_empty(self, tmp_path):
        loader = DrillingRiserLoader(data_dir=tmp_path / "nonexistent")
        df = loader.load()
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_caches_on_second_load(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        df1 = loader.load()
        df2 = loader.load()
        assert df1 is df2

    def test_get_by_id_found(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.get_by_id("RJ-21-75-BARE")
        assert result is not None
        assert result["COMPONENT_TYPE"] == "riser_joint"

    def test_get_by_id_not_found(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.get_by_id("DOES-NOT-EXIST")
        assert result is None


class TestDrillingRiserLoaderByType:
    def test_get_riser_joints(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        joints = loader.get_riser_joints()
        assert len(joints) == 3
        assert all(joints["COMPONENT_TYPE"] == "riser_joint")

    def test_get_bops(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        bops = loader.get_bops()
        assert len(bops) == 2

    def test_get_lmrps(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        lmrps = loader.get_lmrps()
        assert len(lmrps) == 1

    def test_get_flex_joints(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        fjs = loader.get_flex_joints()
        assert len(fjs) == 2

    def test_get_telescopic_joints(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        tjs = loader.get_telescopic_joints()
        assert len(tjs) == 1


class TestDrillingRiserLoaderFilters:
    def test_filter_by_size_21in(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.filter_by_size(21.0)
        assert len(result) == 3

    def test_filter_by_size_no_match(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.filter_by_size(18.75)
        assert len(result) == 0

    def test_filter_by_pressure_rating_min(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.filter_by_pressure_rating(10000.0)
        assert len(result) == 2  # BOP 15K + LMRP 15K

    def test_filter_by_pressure_rating_range(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.filter_by_pressure_rating(4000.0, 6000.0)
        assert len(result) == 7  # All 5K components

    def test_filter_bops_by_bore(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.filter_bops_by_bore(18.75)
        assert len(result) == 1
        assert result.iloc[0]["COMPONENT_ID"] == "BOP-SUB-18.75-15K"

    def test_filter_subsea_bops(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.filter_subsea_bops()
        assert len(result) == 1
        assert result.iloc[0]["BOP_TYPE"] == "subsea"


class TestDrillingRiserLoaderSummary:
    def test_component_type_summary(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        summary = loader.component_type_summary()
        assert summary["riser_joint"] == 3
        assert summary["bop"] == 2
        assert summary["lmrp"] == 1
        assert summary["flex_joint"] == 2
        assert summary["telescopic_joint"] == 1

    def test_manufacturer_summary(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        summary = loader.manufacturer_summary()
        assert summary["Cameron"] == 2

    def test_empty_data_summary(self, tmp_path):
        loader = DrillingRiserLoader(data_dir=tmp_path / "empty")
        summary = loader.component_type_summary()
        assert summary == {}
