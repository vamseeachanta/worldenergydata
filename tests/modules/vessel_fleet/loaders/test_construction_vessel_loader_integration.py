"""Integration tests for construction vessel loader with real seed data."""

from __future__ import annotations

from worldenergydata.vessel_fleet.loaders.construction_vessel_loader import (
    ConstructionVesselLoader,
)


class TestConstructionVesselLoaderIntegration:
    """Tests using the real seed data from curated directory."""

    def test_load_seed_data(self):
        loader = ConstructionVesselLoader()
        df = loader.load()
        assert len(df) >= 10  # At least 10 seed vessels

    def test_known_vessel_sleipnir(self):
        loader = ConstructionVesselLoader()
        vessel = loader.get_by_name("SLEIPNIR")
        assert vessel is not None
        assert vessel["OWNER"] == "Heerema Marine Contractors"
        assert vessel["MAIN_CRANE_CAPACITY_T"] == 10000.0
        assert vessel["DP_CLASS"] == 3

    def test_known_vessel_pioneering_spirit(self):
        loader = ConstructionVesselLoader()
        vessel = loader.get_by_name("PIONEERING SPIRIT")
        assert vessel is not None
        assert vessel["OPERATOR"] == "Allseas Group"
        assert vessel["PIPELAY_METHOD"] == "reel"
        assert vessel["LOA_M"] == 382.0

    def test_known_vessel_thialf(self):
        loader = ConstructionVesselLoader()
        vessel = loader.get_by_name("THIALF")
        assert vessel is not None
        assert vessel["MAIN_CRANE_CAPACITY_T"] == 14200.0
        assert str(vessel["IMO_NUMBER"]) == "8803300"

    def test_heerema_fleet(self):
        loader = ConstructionVesselLoader()
        heerema = loader.get_by_operator("Heerema Marine Contractors")
        assert len(heerema) >= 4  # SLEIPNIR, THIALF, BALDER, AEGIR

    def test_allseas_fleet(self):
        loader = ConstructionVesselLoader()
        allseas = loader.get_by_operator("Allseas Group")
        assert len(allseas) >= 3  # PIONEERING SPIRIT, AUDACIA, SOLITAIRE

    def test_saipem_fleet(self):
        loader = ConstructionVesselLoader()
        saipem = loader.get_by_operator("Saipem")
        assert len(saipem) >= 3  # SAIPEM 7000, SAIPEM FDS, SAIPEM FDS2

    def test_crane_vessels_present(self):
        loader = ConstructionVesselLoader()
        crane = loader.get_crane_vessels()
        assert len(crane) >= 7

    def test_pipelay_vessels_present(self):
        loader = ConstructionVesselLoader()
        pipelay = loader.get_pipelay_vessels()
        assert len(pipelay) >= 5

    def test_heavy_lift_vessels_present(self):
        loader = ConstructionVesselLoader()
        heavy_lift = loader.get_heavy_lift_vessels()
        assert len(heavy_lift) >= 4

    def test_deepwater_vessels_present(self):
        loader = ConstructionVesselLoader()
        deepwater = loader.filter_by_water_depth(min_depth_m=2500.0)
        assert len(deepwater) >= 5

    def test_dp3_vessels_present(self):
        loader = ConstructionVesselLoader()
        dp3 = loader.filter_by_dp_class(min_class=3)
        assert len(dp3) >= 7

    def test_vessel_type_coverage(self):
        loader = ConstructionVesselLoader()
        summary = loader.vessel_type_summary()
        assert "crane_vessel" in summary
        assert "pipelay_vessel" in summary
        assert summary["crane_vessel"] >= 4
        assert summary["pipelay_vessel"] >= 5

    def test_capability_summary_realistic(self):
        loader = ConstructionVesselLoader()
        summary = loader.capability_summary()
        assert summary["total_vessels"] >= 10
        assert summary["has_crane"] >= 7
        assert summary["has_pipelay"] >= 5
        assert summary["deepwater_capable"] >= 5
        assert summary["heavy_lift_capable"] >= 4

    def test_all_vessels_have_name(self):
        loader = ConstructionVesselLoader()
        df = loader.load()
        assert df["VESSEL_NAME"].notna().all()

    def test_all_vessels_have_operator(self):
        loader = ConstructionVesselLoader()
        df = loader.load()
        assert df["OPERATOR"].notna().all()

    def test_all_vessels_have_imo(self):
        loader = ConstructionVesselLoader()
        df = loader.load()
        assert df["IMO_NUMBER"].notna().all()

    def test_no_duplicate_imo_numbers(self):
        loader = ConstructionVesselLoader()
        df = loader.load()
        imo_counts = df["IMO_NUMBER"].value_counts()
        assert (imo_counts <= 1).all()
