"""Tests for FleetRouter query filtering and fleet summary."""

from unittest.mock import patch, MagicMock

import pytest

from worldenergydata.vessel_fleet.router import FleetRouter


MOCK_RIGS = [
    {"RIG_TYPE": "Drillship", "OWNER": "Transocean", "WATER_DEPTH_RATING_FT": 10000, "STATUS": "Active"},
    {"RIG_TYPE": "Semi", "OWNER": "Diamond Offshore", "WATER_DEPTH_RATING_FT": 5000, "STATUS": "Active"},
    {"RIG_TYPE": "Drillship", "OWNER": "Valaris", "WATER_DEPTH_RATING_FT": 8000, "STATUS": "Stacked"},
    {"RIG_TYPE": "Jackup", "OWNER": "Borr Drilling", "WATER_DEPTH_RATING_FT": 400, "STATUS": "Active"},
]

MOCK_VESSELS = [
    {"VESSEL_TYPE": "Pipelay", "OWNER": "Allseas", "MAIN_CRANE_CAPACITY_T": 14000},
    {"VESSEL_TYPE": "HLV", "OWNER": "Heerema", "MAIN_CRANE_CAPACITY_T": 10000},
    {"VESSEL_TYPE": "Pipelay", "OWNER": "Saipem", "MAIN_CRANE_CAPACITY_T": 5000},
]


@pytest.fixture
def router():
    with patch("worldenergydata.vessel_fleet.router.ParquetStore") as MockStore:
        instance = MockStore.return_value
        instance.load = MagicMock(side_effect=lambda name: {
            "drilling_rigs.parquet": MOCK_RIGS,
            "construction_vessels.parquet": MOCK_VESSELS,
        }.get(name, []))
        r = FleetRouter(data_dir=None)
        yield r


class TestQueryDrillingRigs:
    def test_no_filters(self, router):
        results = router.query_drilling_rigs()
        assert len(results) == 4

    def test_filter_by_rig_type(self, router):
        results = router.query_drilling_rigs(rig_type="Drillship")
        assert len(results) == 2
        assert all(r["RIG_TYPE"] == "Drillship" for r in results)

    def test_filter_by_owner(self, router):
        results = router.query_drilling_rigs(owner="transocean")
        assert len(results) == 1
        assert results[0]["OWNER"] == "Transocean"

    def test_filter_by_min_water_depth(self, router):
        results = router.query_drilling_rigs(min_water_depth_ft=6000)
        assert len(results) == 2

    def test_filter_by_status(self, router):
        results = router.query_drilling_rigs(status="Stacked")
        assert len(results) == 1
        assert results[0]["OWNER"] == "Valaris"

    def test_combined_filters(self, router):
        results = router.query_drilling_rigs(
            rig_type="Drillship", status="Active"
        )
        assert len(results) == 1
        assert results[0]["OWNER"] == "Transocean"

    def test_no_matches(self, router):
        results = router.query_drilling_rigs(rig_type="Nonexistent")
        assert results == []


class TestQueryConstructionVessels:
    def test_no_filters(self, router):
        results = router.query_construction_vessels()
        assert len(results) == 3

    def test_filter_by_vessel_type(self, router):
        results = router.query_construction_vessels(vessel_type="Pipelay")
        assert len(results) == 2

    def test_filter_by_owner(self, router):
        results = router.query_construction_vessels(owner="heerema")
        assert len(results) == 1

    def test_filter_by_min_crane_capacity(self, router):
        results = router.query_construction_vessels(min_crane_capacity_t=8000)
        assert len(results) == 2


class TestFleetSummary:
    def test_summary_counts(self, router):
        summary = router.fleet_summary()
        assert summary["drilling_rigs"] == 4
        assert summary["construction_vessels"] == 3
