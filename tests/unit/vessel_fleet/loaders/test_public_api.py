"""Test public API for construction vessel loader."""

from __future__ import annotations

import worldenergydata.vessel_fleet as vf


class TestPublicAPI:
    """Test that the public API is properly exposed."""

    def test_loader_importable_from_package(self):
        loader = vf.ConstructionVesselLoader()
        assert loader is not None

    def test_schema_importable_from_package(self):
        schema = vf.ConstructionVesselSchema(VESSEL_NAME="TEST")
        assert schema.VESSEL_NAME == "TEST"

    def test_model_importable_from_package(self):
        entry = vf.ConstructionVesselEntry(vessel_name="TEST")
        assert entry.vessel_name == "TEST"

    def test_basic_workflow(self):
        """Test basic usage workflow."""
        loader = vf.ConstructionVesselLoader()
        df = loader.load()
        assert len(df) >= 10

        vessel = loader.get_by_name("SLEIPNIR")
        assert vessel is not None

        crane_vessels = loader.get_crane_vessels()
        assert len(crane_vessels) >= 4
