"""Tests for BSEE rig fleet domain model."""

from worldenergydata.bsee.data.models.rig_fleet import RigFleetEntry


class TestRigFleetEntry:
    """Tests for RigFleetEntry dataclass."""

    def test_create_with_required_fields(self):
        entry = RigFleetEntry(rig_name="Test Rig")
        assert entry.rig_name == "Test Rig"
        assert entry.rig_type is None

    def test_create_with_all_fields(self):
        entry = RigFleetEntry(
            rig_name="Ocean Star",
            rig_type="drillship",
            rig_status="active",
            owner="Company A",
            operator="Operator B",
            water_depth_rating_ft=10000.0,
            drilling_depth_rating_ft=40000.0,
            loa_m=238.0,
            beam_m=42.0,
            displacement_tonnes=97000.0,
            dp_class=3,
            year_built=2010,
            imo_number="9431752",
            flag_state="Marshall Islands",
            moonpool_diameter_m=12.0,
            wells_drilled_count=50,
            is_offshore=True,
        )
        assert entry.rig_type == "drillship"
        assert entry.dp_class == 3

    def test_is_active_with_active_status(self):
        entry = RigFleetEntry(rig_name="Test", rig_status="active")
        assert entry.is_active is True

    def test_is_active_with_none_status(self):
        entry = RigFleetEntry(rig_name="Test", rig_status=None)
        assert entry.is_active is True

    def test_is_active_with_stacked_cold(self):
        entry = RigFleetEntry(rig_name="Test", rig_status="stacked_cold")
        assert entry.is_active is False

    def test_is_active_with_stacked_warm(self):
        entry = RigFleetEntry(rig_name="Test", rig_status="stacked_warm")
        assert entry.is_active is False

    def test_is_active_with_scrapped(self):
        entry = RigFleetEntry(rig_name="Test", rig_status="scrapped")
        assert entry.is_active is False

    def test_is_deepwater_capable_above_threshold(self):
        entry = RigFleetEntry(rig_name="Test", water_depth_rating_ft=5000.0)
        assert entry.is_deepwater_capable is True

    def test_is_deepwater_capable_at_threshold(self):
        entry = RigFleetEntry(rig_name="Test", water_depth_rating_ft=4000.0)
        assert entry.is_deepwater_capable is True

    def test_is_deepwater_capable_below_threshold(self):
        entry = RigFleetEntry(rig_name="Test", water_depth_rating_ft=3999.0)
        assert entry.is_deepwater_capable is False

    def test_is_deepwater_capable_none_rating(self):
        entry = RigFleetEntry(rig_name="Test", water_depth_rating_ft=None)
        assert entry.is_deepwater_capable is False

    def test_rig_key_normalization(self):
        entry = RigFleetEntry(rig_name="  Ocean Star  ")
        assert entry.rig_key == "ocean_star"

    def test_rig_key_lowercase(self):
        entry = RigFleetEntry(rig_name="DEEPWATER HORIZON")
        assert entry.rig_key == "deepwater_horizon"

    def test_rig_type_display_known_type(self):
        entry = RigFleetEntry(rig_name="Test", rig_type="drillship")
        assert entry.rig_type_display == "Drillship"

    def test_rig_type_display_semi_submersible(self):
        entry = RigFleetEntry(rig_name="Test", rig_type="semi_submersible")
        assert entry.rig_type_display == "Semi-Submersible"

    def test_rig_type_display_unknown_type(self):
        entry = RigFleetEntry(rig_name="Test", rig_type="unknown_type")
        assert entry.rig_type_display == "Unknown"

    def test_rig_type_display_none_type(self):
        entry = RigFleetEntry(rig_name="Test", rig_type=None)
        assert entry.rig_type_display == "Unknown"

    def test_is_offshore_derived_explicit_true(self):
        entry = RigFleetEntry(rig_name="Test", is_offshore=True)
        assert entry.is_offshore_derived is True

    def test_is_offshore_derived_explicit_false(self):
        entry = RigFleetEntry(rig_name="Test", is_offshore=False)
        assert entry.is_offshore_derived is False

    def test_is_offshore_derived_land_rig(self):
        entry = RigFleetEntry(rig_name="Test", rig_type="land_rig")
        assert entry.is_offshore_derived is False

    def test_is_offshore_derived_drillship(self):
        entry = RigFleetEntry(rig_name="Test", rig_type="drillship")
        assert entry.is_offshore_derived is True

    def test_is_offshore_derived_none_type(self):
        entry = RigFleetEntry(rig_name="Test", rig_type=None)
        assert entry.is_offshore_derived is True
