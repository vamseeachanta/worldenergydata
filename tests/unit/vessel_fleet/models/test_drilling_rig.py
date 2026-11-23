"""Tests for drilling rig domain model."""

from worldenergydata.vessel_fleet.models.drilling_rig import DrillingRigEntry


class TestDrillingRigEntry:
    def test_required(self):
        r = DrillingRigEntry(vessel_name="Deepwater Nautilus")
        assert r.vessel_name == "Deepwater Nautilus"

    def test_defaults(self):
        r = DrillingRigEntry(vessel_name="T")
        assert r.rig_type is None
        assert r.water_depth_rating_ft is None
        assert r.is_offshore is None

    def test_is_deepwater_capable_true(self):
        r = DrillingRigEntry(
            vessel_name="T",
            water_depth_rating_ft=10000.0,
        )
        assert r.is_deepwater_capable is True

    def test_is_deepwater_capable_false(self):
        r = DrillingRigEntry(
            vessel_name="T",
            water_depth_rating_ft=3000.0,
        )
        assert r.is_deepwater_capable is False

    def test_is_deepwater_capable_boundary(self):
        r = DrillingRigEntry(
            vessel_name="T",
            water_depth_rating_ft=4000.0,
        )
        assert r.is_deepwater_capable is True

    def test_is_deepwater_capable_none(self):
        r = DrillingRigEntry(vessel_name="T")
        assert r.is_deepwater_capable is False

    def test_is_ultra_deepwater_true(self):
        r = DrillingRigEntry(
            vessel_name="T",
            water_depth_rating_ft=10000.0,
        )
        assert r.is_ultra_deepwater is True

    def test_is_ultra_deepwater_false(self):
        r = DrillingRigEntry(
            vessel_name="T",
            water_depth_rating_ft=5000.0,
        )
        assert r.is_ultra_deepwater is False

    def test_is_ultra_deepwater_boundary(self):
        r = DrillingRigEntry(
            vessel_name="T",
            water_depth_rating_ft=7500.0,
        )
        assert r.is_ultra_deepwater is True

    def test_is_ultra_deepwater_none(self):
        r = DrillingRigEntry(vessel_name="T")
        assert r.is_ultra_deepwater is False

    def test_rig_type_display_drillship(self):
        r = DrillingRigEntry(vessel_name="T", rig_type="drillship")
        assert r.rig_type_display == "Drillship"

    def test_rig_type_display_semi(self):
        r = DrillingRigEntry(vessel_name="T", rig_type="semi_submersible")
        assert r.rig_type_display == "Semi-Submersible"

    def test_rig_type_display_jackup(self):
        r = DrillingRigEntry(vessel_name="T", rig_type="jack_up")
        assert r.rig_type_display == "Jack-Up"

    def test_rig_type_display_unknown(self):
        r = DrillingRigEntry(vessel_name="T", rig_type="xyz")
        assert r.rig_type_display == "Unknown"

    def test_rig_type_display_none(self):
        r = DrillingRigEntry(vessel_name="T")
        assert r.rig_type_display == "Unknown"

    def test_is_offshore_derived_explicit_true(self):
        r = DrillingRigEntry(vessel_name="T", is_offshore=True)
        assert r.is_offshore_derived is True

    def test_is_offshore_derived_explicit_false(self):
        r = DrillingRigEntry(vessel_name="T", is_offshore=False)
        assert r.is_offshore_derived is False

    def test_is_offshore_derived_drillship(self):
        r = DrillingRigEntry(vessel_name="T", rig_type="drillship")
        assert r.is_offshore_derived is True

    def test_is_offshore_derived_land_rig(self):
        r = DrillingRigEntry(vessel_name="T", rig_type="land_rig")
        assert r.is_offshore_derived is False

    def test_is_offshore_derived_none(self):
        r = DrillingRigEntry(vessel_name="T")
        assert r.is_offshore_derived is True

    def test_is_jackup_true(self):
        r = DrillingRigEntry(vessel_name="T", rig_type="jack_up")
        assert r.is_jackup is True

    def test_is_jackup_false(self):
        r = DrillingRigEntry(vessel_name="T", rig_type="drillship")
        assert r.is_jackup is False

    def test_is_floater_drillship(self):
        r = DrillingRigEntry(vessel_name="T", rig_type="drillship")
        assert r.is_floater is True

    def test_is_floater_semi(self):
        r = DrillingRigEntry(vessel_name="T", rig_type="semi_submersible")
        assert r.is_floater is True

    def test_is_floater_jackup(self):
        r = DrillingRigEntry(vessel_name="T", rig_type="jack_up")
        assert r.is_floater is False

    def test_display_name_rig_name(self):
        r = DrillingRigEntry(vessel_name="V1", rig_name="RigName")
        assert r.display_name == "RigName"

    def test_display_name_vessel_name(self):
        r = DrillingRigEntry(vessel_name="V1")
        assert r.display_name == "V1"

    def test_inherits_base_active(self):
        r = DrillingRigEntry(vessel_name="T", status="active")
        assert r.is_active is True

    def test_inherits_base_inactive(self):
        r = DrillingRigEntry(vessel_name="T", status="cold_stacked")
        assert r.is_active is False
