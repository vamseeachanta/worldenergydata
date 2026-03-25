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
            "RJ-21-75-BARE",
            "RJ-21-75-BUOY",
            "RJ-21-50-PUP",
            "BOP-SUB-18.75-15K",
            "BOP-SURF-13.625-5K",
            "LMRP-18.75-15K",
            "FJ-UPPER-21",
            "FJ-LOWER-21",
            "TJ-21-50",
        ],
        "COMPONENT_TYPE": [
            "riser_joint",
            "riser_joint",
            "riser_joint",
            "bop",
            "bop",
            "lmrp",
            "flex_joint",
            "flex_joint",
            "telescopic_joint",
        ],
        "MANUFACTURER": [
            None,
            None,
            None,
            "Cameron",
            None,
            "Cameron",
            None,
            None,
            None,
        ],
        "OD_IN": [21.0, 21.0, 21.0, None, None, None, None, None, 21.0],
        "LENGTH_FT": [75.0, 75.0, 50.0, None, None, None, None, None, None],
        "WEIGHT_AIR_KIPS": [22.5, 22.5, 15.0, 400.0, 45.0, 180.0, 8.5, 12.0, 35.0],
        "PRESSURE_RATING_PSI": [
            5000.0,
            5000.0,
            5000.0,
            15000.0,
            5000.0,
            15000.0,
            5000.0,
            5000.0,
            5000.0,
        ],
        "BOP_TYPE": [
            None,
            None,
            None,
            "subsea",
            "surface",
            None,
            None,
            None,
            None,
        ],
        "BORE_SIZE_IN": [
            None,
            None,
            None,
            18.75,
            13.625,
            18.75,
            None,
            None,
            None,
        ],
        "BUOYANCY_COVERAGE_PCT": [0, 100, 0, None, None, None, None, None, None],
        "MAX_ANGLE_DEG": [None, None, None, None, None, None, 10.0, 10.0, None],
        "POSITION": [None, None, None, None, None, None, "upper", "lower", None],
        "STROKE_FT": [None, None, None, None, None, None, None, None, 50.0],
        "HEIGHT_FT": [None, None, None, 35.0, 18.0, 18.0, None, None, None],
        "CONNECTOR_TYPE": [
            None,
            None,
            None,
            None,
            None,
            "H-4 collet",
            None,
            None,
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

    def test_filter_by_size_tolerance_orcaflex_od(self, sample_riser_data):
        """OrcaFlex OD in meters converted to inches may differ by <0.1in."""
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        # 0.5334m / 0.0254 = 20.9999... — should match 21" with default tolerance
        od_approx = 0.5334 / 0.0254
        result = loader.filter_by_size(od_approx)
        assert len(result) == 3

    def test_filter_by_size_zero_tolerance_rejects_far_off(self, sample_riser_data):
        """Exact match with tolerance=0 rejects values more than 0.5" off."""
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.filter_by_size(21.6, tolerance_in=0.0)  # 21.6 != 21.0
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


class TestDrillingRiserLoaderQuery:
    def test_query_by_component_type(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.query(component_type="riser_joint")
        assert not result.empty
        assert all(result["COMPONENT_TYPE"] == "riser_joint")

    def test_query_by_manufacturer(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.query(manufacturer="Cameron")
        assert not result.empty
        assert all(result["MANUFACTURER"] == "Cameron")

    def test_query_combined_type_and_od(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.query(component_type="riser_joint", od_in=21.0)
        assert not result.empty
        assert all(result["COMPONENT_TYPE"] == "riser_joint")
        assert all((result["OD_IN"] - 21.0).abs() <= 0.1)

    def test_query_with_pressure_filter(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.query(min_pressure_psi=10000.0)
        assert not result.empty
        assert all(result["PRESSURE_RATING_PSI"] >= 10000.0)

    def test_query_no_match_returns_empty(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        result = loader.query(manufacturer="NonExistentMfr")
        assert result.empty

    def test_query_empty_kwargs_returns_all(self, sample_riser_data):
        loader = DrillingRiserLoader(data_dir=sample_riser_data)
        all_data = loader.load()
        result = loader.query()
        assert len(result) == len(all_data)


class TestDrillingRisersIntegration:
    """Integration tests against the live curated CSV (read-only)."""

    def test_curated_csv_has_sufficient_riser_joints(self):
        loader = DrillingRiserLoader()
        joints = loader.get_riser_joints()
        assert len(joints) >= 20, f"Expected ≥20 riser joints, got {len(joints)}"

    def test_curated_csv_has_21in_joints(self):
        loader = DrillingRiserLoader()
        result = loader.filter_by_size(21.0)
        assert not result.empty, 'No 21" riser joints found in curated dataset'

    def test_curated_csv_has_18_75in_joints(self):
        loader = DrillingRiserLoader()
        result = loader.filter_by_size(18.75)
        assert not result.empty, 'No 18.75" riser joints found in curated dataset'

    def test_curated_query_riser_joint_returns_results(self):
        loader = DrillingRiserLoader()
        result = loader.query(component_type="riser_joint")
        assert not result.empty

    def test_curated_component_ids_are_unique(self):
        loader = DrillingRiserLoader()
        df = loader.load()
        assert df["COMPONENT_ID"].nunique() == len(df), "Duplicate COMPONENT_IDs found"

    def test_drilling_rigs_csv_exists(self):
        from pathlib import Path

        # parents[4] = worldenergydata/ repo root (test is at tests/unit/vessel_fleet/loaders/)
        rigs_path = (
            Path(__file__).resolve().parents[4]
            / "data"
            / "modules"
            / "vessel_fleet"
            / "curated"
            / "drilling_rigs.csv"
        )
        assert rigs_path.exists(), f"drilling_rigs.csv not found at {rigs_path}"
        import pandas as pd

        df = pd.read_csv(rigs_path)
        assert len(df) > 100, f"Expected >100 rigs, got {len(df)}"
        assert "RIG_NAME" in df.columns
        drillships = df[df["RIG_TYPE"] == "drillship"]
        assert len(drillships) >= 50, f"Expected ≥50 drillships, got {len(drillships)}"
