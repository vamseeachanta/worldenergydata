"""Tests for construction vessel data loader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.loaders.construction_vessel_loader import (
    ConstructionVesselLoader,
)


@pytest.fixture
def sample_construction_fleet(tmp_path):
    """Create a minimal construction vessel parquet for testing."""
    data = {
        "VESSEL_NAME": [
            "SLEIPNIR",
            "PIONEERING SPIRIT",
            "THIALF",
            "SAIPEM 7000",
            # Synthetic wind-installation fixture — NOT a real vessel. (Do not
            # reuse a real ship name here: a fabricated "AEGIR" jack-up once
            # leaked into the curated fleet from this fixture. Aegir is the
            # 211.5 m Heerema DCV, not a 169 m jack-up.)
            "TEST WTIV (SYNTHETIC)",
        ],
        "VESSEL_TYPE": [
            "crane_vessel",
            "pipelay_vessel",
            "crane_vessel",
            "crane_vessel",
            "wind_installation",
        ],
        "OWNER": ["Heerema", "Allseas", "Heerema", "Saipem", "Heerema"],
        "OPERATOR": ["Heerema", "Allseas", "Heerema", "Saipem", "Heerema"],
        "IMO_NUMBER": ["9781425", "9593505", "8803300", "7392610", "0000001"],
        "MAIN_CRANE_CAPACITY_T": [10000.0, None, 14200.0, 14000.0, 5000.0],
        "MAIN_CRANE_REACH_M": [48.0, None, 31.2, None, None],
        "AUX_CRANE_CAPACITY_T": [None, None, None, 7000.0, None],
        "PIPELAY_TENSION_T": [None, 2000.0, None, None, None],
        "PIPELAY_METHOD": [None, "reel", None, None, None],
        "DECK_AREA_M2": [11000.0, 8000.0, 7000.0, 9000.0, 5000.0],
        "DP_CLASS": [3, 3, 3, 3, 2],
        "WATER_DEPTH_RATING_M": [3000.0, 4000.0, 2500.0, 3000.0, 1500.0],
        "LOA_M": [220.0, 382.0, 201.0, 198.0, 169.0],
        "BEAM_M": [102.0, 124.0, 88.4, 87.0, 47.0],
        "YEAR_BUILT": [2019, 2014, 1985, 1987, 2022],
        "STATUS": ["active", "active", "active", "active", "active"],
        "DATA_SOURCE": ["heerema", "allseas", "heerema", "saipem", "heerema"],
    }
    df = pd.DataFrame(data)
    pq_path = tmp_path / "construction_vessels.parquet"
    df.to_parquet(pq_path)
    return tmp_path


class TestConstructionVesselLoaderBasics:
    def test_load_returns_dataframe(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        df = loader.load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5

    def test_missing_data_dir_returns_empty(self, tmp_path):
        loader = ConstructionVesselLoader(data_dir=tmp_path / "nonexistent")
        df = loader.load()
        assert df.empty

    def test_caches_on_second_load(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        loader.load()  # first load
        loader.load()  # should use cache
        assert loader._df is not None


class TestConstructionVesselLoaderQueries:
    def test_get_by_name(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        record = loader.get_by_name("SLEIPNIR")
        assert record is not None
        assert record["VESSEL_NAME"] == "SLEIPNIR"
        assert record["MAIN_CRANE_CAPACITY_T"] == 10000.0

    def test_get_by_name_case_insensitive(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        record = loader.get_by_name("sleipnir")
        assert record is not None
        assert record["VESSEL_NAME"] == "SLEIPNIR"

    def test_get_by_name_not_found(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        assert loader.get_by_name("NONEXISTENT") is None

    def test_get_by_vessel_type(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        crane_vessels = loader.get_by_vessel_type("crane_vessel")
        assert len(crane_vessels) == 3
        assert "SLEIPNIR" in crane_vessels["VESSEL_NAME"].values

    def test_get_by_operator(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        heerema = loader.get_by_operator("Heerema")
        assert len(heerema) == 3

    def test_get_by_imo(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        record = loader.get_by_imo("9781425")
        assert record is not None
        assert record["VESSEL_NAME"] == "SLEIPNIR"

    def test_get_by_imo_not_found(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        assert loader.get_by_imo("0000000") is None


class TestConstructionVesselLoaderCapabilityFilters:
    def test_filter_by_crane_capacity(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        heavy_lift = loader.filter_by_crane_capacity(min_capacity_t=10000.0)
        assert len(heavy_lift) >= 2  # SLEIPNIR, THIALF, SAIPEM 7000

    def test_filter_by_water_depth(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        deepwater = loader.filter_by_water_depth(min_depth_m=3000.0)
        assert len(deepwater) >= 2  # SLEIPNIR, PIONEERING SPIRIT, SAIPEM 7000

    def test_filter_by_dp_class(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        dp3 = loader.filter_by_dp_class(min_class=3)
        assert len(dp3) == 4

    def test_filter_by_deck_area(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        large_deck = loader.filter_by_deck_area(min_area_m2=9000.0)
        assert len(large_deck) >= 1


class TestConstructionVesselLoaderSummaries:
    def test_vessel_type_summary(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        summary = loader.vessel_type_summary()
        assert summary.get("crane_vessel") == 3
        assert summary.get("pipelay_vessel") == 1
        assert summary.get("wind_installation") == 1

    def test_operator_summary(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        summary = loader.operator_summary()
        assert summary.get("Heerema") == 3
        assert summary.get("Allseas") == 1

    def test_capability_summary(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        summary = loader.capability_summary()
        assert "total_vessels" in summary
        assert "has_crane" in summary
        assert "has_pipelay" in summary
        assert "deepwater_capable" in summary
        assert summary["total_vessels"] == 5


class TestConstructionVesselLoaderDomainLogic:
    def test_get_pipelay_vessels(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        pipelay = loader.get_pipelay_vessels()
        assert len(pipelay) >= 1
        assert "PIONEERING SPIRIT" in pipelay["VESSEL_NAME"].values

    def test_get_crane_vessels(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        crane = loader.get_crane_vessels()
        assert len(crane) >= 4  # All except maybe one

    def test_get_heavy_lift_vessels(self, sample_construction_fleet):
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        heavy_lift = loader.get_heavy_lift_vessels()
        # Vessels with crane >= 10000t
        assert len(heavy_lift) >= 2


@pytest.fixture
def pipelay_burial_fleet(tmp_path):
    """Fleet parquet carrying the #701 pipelay/burial columns with nulls."""
    data = {
        "VESSEL_NAME": ["LAY BARGE A", "BURY BARGE B", "REEL SHIP C"],
        "VESSEL_TYPE": ["pipelay_vessel"] * 3,
        "PIPELAY_TENSION_T": [100.0, None, 400.0],
        "PIPELAY_METHOD": ["S-lay", None, "reel"],
        "PIPELAY_CAPACITY_IN": [60.0, None, 18.0],
        # 701 columns — deliberately sparse (poster-style nulls)
        "WELDING_STATIONS_COUNT": [5.0, None, 1.0],
        "TOTAL_STATIONS_COUNT": [9.0, None, 1.0],
        "NDT_STATIONS_COUNT": [None, None, None],
        "WELDING_METHOD": ["manual+automatic", None, None],
        "TENSIONER_COUNT": [2.0, None, 1.0],
        "PIPELAY_MIN_DIAMETER_IN": [4.0, None, 2.0],
        "JLAY_CAPABLE": [None, None, True],
        "REEL_PERMANENT_CAPABLE": [None, None, True],
        "BURIAL_CAPABLE": [None, True, None],
        "BURIAL_MIN_DIAMETER_IN": [None, 4.0, None],
        "BURIAL_MAX_DIAMETER_IN": [None, 48.0, None],
        "BURIAL_MAX_WATER_DEPTH_M": [None, 762.0, None],
        "PIPELAY_MIN_WATER_DEPTH_M": [3.0, None, 15.2],
        "PIPELAY_MAX_WATER_DEPTH_M": [243.8, None, 1524.0],
        "EXPERIENCE_WATER_DEPTH_M": [30.5, 410.0, None],
        "PIPE_JOINT_LENGTH_MAX_M": [12.8, None, None],
        "DAVITS_COUNT": [None, None, None],
    }
    df = pd.DataFrame(data)
    df.to_parquet(tmp_path / "construction_vessels.parquet")
    return tmp_path


class TestPipelayBurialColumns:
    """#701 — loader behaviour for the pipelay/burial capability columns."""

    def test_loads_new_columns_with_nulls(self, pipelay_burial_fleet):
        loader = ConstructionVesselLoader(data_dir=pipelay_burial_fleet)
        df = loader.load()
        assert "TENSIONER_COUNT" in df.columns
        record = loader.get_by_name("BURY BARGE B")
        assert record["BURIAL_CAPABLE"] is True
        assert record["BURIAL_MAX_DIAMETER_IN"] == 48.0
        assert pd.isna(record["TENSIONER_COUNT"])

    def test_get_burial_capable_vessels(self, pipelay_burial_fleet):
        loader = ConstructionVesselLoader(data_dir=pipelay_burial_fleet)
        burial = loader.get_burial_capable_vessels()
        assert list(burial["VESSEL_NAME"]) == ["BURY BARGE B"]

    def test_burial_query_tolerates_legacy_dataset(
        self, sample_construction_fleet
    ):
        """Datasets predating #701 (no burial columns) must not raise."""
        loader = ConstructionVesselLoader(data_dir=sample_construction_fleet)
        burial = loader.get_burial_capable_vessels()
        assert burial.empty

    def test_curated_data_carries_new_columns(self):
        loader = ConstructionVesselLoader()  # real committed curated data
        df = loader.load()
        for col in (
            "WELDING_STATIONS_COUNT",
            "TOTAL_STATIONS_COUNT",
            "TENSIONER_COUNT",
            "PIPELAY_MIN_DIAMETER_IN",
            "BURIAL_CAPABLE",
            "PIPELAY_MAX_WATER_DEPTH_M",
            "PIPE_JOINT_LENGTH_MAX_M",
        ):
            assert col in df.columns, col
        # 2011 poster backfill landed on poster-derived rows
        assert df["PIPELAY_MIN_DIAMETER_IN"].notna().sum() >= 40
        assert len(loader.get_burial_capable_vessels()) >= 10


class TestAegirRegression:
    """Guard against the fabricated 'Aegir wind-installation jack-up' regression.

    The real Aegir is Heerema's deepwater construction vessel (DCV) — a 211.5 m
    monohull, IMO 9605396 — not a 169 m jack-up. A synthetic test fixture once
    leaked a fabricated jack-up 'AEGIR' (IMO 9918390) into the curated fleet.
    """

    def test_curated_aegir_is_dcv_not_jackup(self):
        loader = ConstructionVesselLoader()  # real committed curated data
        v = loader.get_by_name("Aegir")
        assert v is not None, "Aegir missing from curated construction fleet"
        assert v["VESSEL_TYPE"] == "crane_vessel"
        assert v.get("VESSEL_SUBTYPE") != "jack_up"
        assert str(v["IMO_NUMBER"]) == "9605396"
        assert abs(float(v["LOA_M"]) - 211.5) < 1.0
        # the fabricated 169 m / IMO 9918390 values must be gone
        assert str(v["IMO_NUMBER"]) != "9918390"
