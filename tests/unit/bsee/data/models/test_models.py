"""Tests for BSEE data models (pipeline, platform, deepwater, rig fleet)."""

import pytest

from worldenergydata.bsee.data.models.pipeline import (
    PipelineLocation,
    PipelinePermit,
)
from worldenergydata.bsee.data.models.platform import PlatformStructure
from worldenergydata.bsee.data.models.deepwater_structure import DeepwaterStructure
from worldenergydata.bsee.data.models.rig_fleet import RigFleetEntry


class TestPipelinePermit:
    def test_defaults(self):
        p = PipelinePermit()
        assert p.segment_num is None
        assert p.status_code is None

    def test_is_active_none_status(self):
        p = PipelinePermit()
        assert p.is_active is False

    def test_is_active_true(self):
        p = PipelinePermit(status_code="ACT")
        assert p.is_active is True

    def test_is_active_abandoned(self):
        p = PipelinePermit(status_code="ABN")
        assert p.is_active is False

    def test_is_active_out(self):
        p = PipelinePermit(status_code="OUT")
        assert p.is_active is False

    def test_is_active_removed(self):
        p = PipelinePermit(status_code="RMV")
        assert p.is_active is False

    def test_is_deepwater_true(self):
        p = PipelinePermit(max_wtr_dpth=1500.0)
        assert p.is_deepwater is True

    def test_is_deepwater_false(self):
        p = PipelinePermit(max_wtr_dpth=500.0)
        assert p.is_deepwater is False

    def test_is_deepwater_none(self):
        p = PipelinePermit()
        assert p.is_deepwater is False

    def test_is_deepwater_boundary(self):
        p = PipelinePermit(max_wtr_dpth=1000.0)
        assert p.is_deepwater is False  # must exceed, not equal

    def test_segment_key(self):
        p = PipelinePermit(
            area_code="MC", block_number="100", segment_num="SEG001",
        )
        assert p.segment_key == "MC_100_SEG001"


class TestPipelineLocation:
    def test_defaults(self):
        loc = PipelineLocation()
        assert loc.segment_num is None
        assert loc.latitude is None

    def test_all_fields(self):
        loc = PipelineLocation(
            segment_num="SEG001", point_num=1,
            latitude=29.5, longitude=-90.0,
            water_depth=500.0, area_code="MC", block_number="100",
        )
        assert loc.point_num == 1
        assert loc.water_depth == 500.0


class TestPlatformStructure:
    def test_required_fields(self):
        p = PlatformStructure(
            area_code="MC", block_number="100", structure_number="A001",
        )
        assert p.area_code == "MC"

    def test_is_active_no_removal(self):
        p = PlatformStructure(
            area_code="MC", block_number="100", structure_number="A001",
        )
        assert p.is_active is True

    def test_is_active_with_removal(self):
        p = PlatformStructure(
            area_code="MC", block_number="100", structure_number="A001",
            removal_date="2020-01-15",
        )
        assert p.is_active is False

    def test_structure_key(self):
        p = PlatformStructure(
            area_code="MC", block_number="100", structure_number="A001",
        )
        assert p.structure_key == "MC_100_A001"

    def test_structure_type_known(self):
        p = PlatformStructure(
            area_code="MC", block_number="100", structure_number="A001",
            struc_type_code="FP",
        )
        assert p.structure_type == "Fixed Platform"

    def test_structure_type_tlp(self):
        p = PlatformStructure(
            area_code="MC", block_number="100", structure_number="A001",
            struc_type_code="TLP",
        )
        assert p.structure_type == "Tension Leg Platform"

    def test_structure_type_spar(self):
        p = PlatformStructure(
            area_code="MC", block_number="100", structure_number="A001",
            struc_type_code="SPAR",
        )
        assert p.structure_type == "Spar"

    def test_structure_type_unknown(self):
        p = PlatformStructure(
            area_code="MC", block_number="100", structure_number="A001",
            struc_type_code="XYZ",
        )
        assert p.structure_type == "Unknown"

    def test_structure_type_none(self):
        p = PlatformStructure(
            area_code="MC", block_number="100", structure_number="A001",
        )
        assert p.structure_type == "Unknown"


class TestDeepwaterStructure:
    def test_required_fields(self):
        d = DeepwaterStructure(
            area_code="GC", block_number="200", structure_number="B002",
        )
        assert d.area_code == "GC"

    def test_permit_fields(self):
        d = DeepwaterStructure(
            area_code="GC", block_number="200", structure_number="B002",
            permit_number="P12345", bus_asc_name="Shell",
        )
        assert d.permit_number == "P12345"
        assert d.bus_asc_name == "Shell"

    def test_is_active(self):
        d = DeepwaterStructure(
            area_code="GC", block_number="200", structure_number="B002",
        )
        assert d.is_active is True

    def test_is_active_removed(self):
        d = DeepwaterStructure(
            area_code="GC", block_number="200", structure_number="B002",
            removal_date="2023-06-01",
        )
        assert d.is_active is False

    def test_structure_key(self):
        d = DeepwaterStructure(
            area_code="GC", block_number="200", structure_number="B002",
        )
        assert d.structure_key == "GC_200_B002"

    def test_structure_type_fps(self):
        d = DeepwaterStructure(
            area_code="GC", block_number="200", structure_number="B002",
            struc_type_code="FPS",
        )
        assert d.structure_type == "Floating Production System"

    def test_structure_type_fpso(self):
        d = DeepwaterStructure(
            area_code="GC", block_number="200", structure_number="B002",
            struc_type_code="FPSO",
        )
        assert d.structure_type == "FPSO"

    def test_structure_type_subsea(self):
        d = DeepwaterStructure(
            area_code="GC", block_number="200", structure_number="B002",
            struc_type_code="SS",
        )
        assert d.structure_type == "Subsea Structure"


class TestRigFleetEntry:
    def test_required(self):
        r = RigFleetEntry(rig_name="DEEPWATER NAUTILUS")
        assert r.rig_name == "DEEPWATER NAUTILUS"

    def test_defaults(self):
        r = RigFleetEntry(rig_name="TEST")
        assert r.rig_type is None
        assert r.rig_status is None
        assert r.water_depth_rating_ft is None

    def test_is_active_none_status(self):
        r = RigFleetEntry(rig_name="TEST")
        assert r.is_active is True

    def test_is_active_operating(self):
        r = RigFleetEntry(rig_name="TEST", rig_status="operating")
        assert r.is_active is True

    def test_is_active_stacked_cold(self):
        r = RigFleetEntry(rig_name="TEST", rig_status="stacked_cold")
        assert r.is_active is False

    def test_is_active_stacked_warm(self):
        r = RigFleetEntry(rig_name="TEST", rig_status="stacked_warm")
        assert r.is_active is False

    def test_is_active_scrapped(self):
        r = RigFleetEntry(rig_name="TEST", rig_status="scrapped")
        assert r.is_active is False

    def test_is_deepwater_capable_true(self):
        r = RigFleetEntry(rig_name="TEST", water_depth_rating_ft=10000.0)
        assert r.is_deepwater_capable is True

    def test_is_deepwater_capable_false(self):
        r = RigFleetEntry(rig_name="TEST", water_depth_rating_ft=3000.0)
        assert r.is_deepwater_capable is False

    def test_is_deepwater_capable_boundary(self):
        r = RigFleetEntry(rig_name="TEST", water_depth_rating_ft=4000.0)
        assert r.is_deepwater_capable is True

    def test_is_deepwater_capable_none(self):
        r = RigFleetEntry(rig_name="TEST")
        assert r.is_deepwater_capable is False

    def test_rig_key(self):
        r = RigFleetEntry(rig_name="DEEPWATER NAUTILUS")
        assert r.rig_key == "deepwater_nautilus"

    def test_rig_key_strips(self):
        r = RigFleetEntry(rig_name="  Test Rig  ")
        assert r.rig_key == "test_rig"

    def test_rig_type_display_drillship(self):
        r = RigFleetEntry(rig_name="TEST", rig_type="drillship")
        assert r.rig_type_display == "Drillship"

    def test_rig_type_display_semi(self):
        r = RigFleetEntry(rig_name="TEST", rig_type="semi_submersible")
        assert r.rig_type_display == "Semi-Submersible"

    def test_rig_type_display_jack_up(self):
        r = RigFleetEntry(rig_name="TEST", rig_type="jack_up")
        assert r.rig_type_display == "Jack-Up"

    def test_rig_type_display_unknown(self):
        r = RigFleetEntry(rig_name="TEST", rig_type="xyz")
        assert r.rig_type_display == "Unknown"

    def test_rig_type_display_none(self):
        r = RigFleetEntry(rig_name="TEST")
        assert r.rig_type_display == "Unknown"

    def test_is_offshore_derived_explicit_true(self):
        r = RigFleetEntry(rig_name="TEST", is_offshore=True)
        assert r.is_offshore_derived is True

    def test_is_offshore_derived_explicit_false(self):
        r = RigFleetEntry(rig_name="TEST", is_offshore=False)
        assert r.is_offshore_derived is False

    def test_is_offshore_derived_land_rig(self):
        r = RigFleetEntry(rig_name="TEST", rig_type="land_rig")
        assert r.is_offshore_derived is False

    def test_is_offshore_derived_default(self):
        r = RigFleetEntry(rig_name="TEST", rig_type="drillship")
        assert r.is_offshore_derived is True

    def test_is_offshore_derived_none_type(self):
        r = RigFleetEntry(rig_name="TEST")
        assert r.is_offshore_derived is True
