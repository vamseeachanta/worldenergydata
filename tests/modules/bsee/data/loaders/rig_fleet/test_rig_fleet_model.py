"""Tests for RigFleetEntry dataclass model."""

from __future__ import annotations

from worldenergydata.bsee.data.models.rig_fleet import RigFleetEntry


class TestRigFleetEntry:
    """Tests for RigFleetEntry domain model."""

    def _make_entry(self, **overrides) -> RigFleetEntry:
        """Helper to create a RigFleetEntry with sensible defaults."""
        defaults = {
            "rig_name": "DEEPWATER TITAN",
            "rig_type": "drillship",
            "rig_status": "under_contract",
            "owner": "Transocean",
            "operator": "Shell",
            "water_depth_rating_ft": 12000.0,
            "drilling_depth_rating_ft": 40000.0,
            "loa_m": 238.0,
            "beam_m": 42.0,
            "displacement_tonnes": 96000.0,
            "dp_class": 3,
            "year_built": 2014,
            "imo_number": "9612345",
            "flag_state": "MHL",
            "moonpool_diameter_m": 7.6,
            "wells_drilled_count": 55,
            "last_war_date": "2024-12-15",
            "last_area_code": "GC",
        }
        defaults.update(overrides)
        return RigFleetEntry(**defaults)

    # --- is_active ---

    def test_is_active_under_contract(self):
        """Rig under contract is active."""
        entry = self._make_entry(rig_status="under_contract")
        assert entry.is_active is True

    def test_is_active_stacked_cold(self):
        """Cold-stacked rig is not active."""
        entry = self._make_entry(rig_status="stacked_cold")
        assert entry.is_active is False

    def test_is_active_scrapped(self):
        """Scrapped rig is not active."""
        entry = self._make_entry(rig_status="scrapped")
        assert entry.is_active is False

    def test_is_active_none_status(self):
        """Rig with None status is treated as active (default assumption)."""
        entry = self._make_entry(rig_status=None)
        assert entry.is_active is True

    # --- is_deepwater_capable ---

    def test_is_deepwater_capable_true(self):
        """Rig with water depth >= 4000 ft is deepwater capable."""
        entry = self._make_entry(water_depth_rating_ft=10000.0)
        assert entry.is_deepwater_capable is True

    def test_is_deepwater_capable_false(self):
        """Rig with water depth < 4000 ft is not deepwater capable."""
        entry = self._make_entry(water_depth_rating_ft=350.0)
        assert entry.is_deepwater_capable is False

    def test_is_deepwater_capable_none(self):
        """Rig with unknown water depth is not deepwater capable."""
        entry = self._make_entry(water_depth_rating_ft=None)
        assert entry.is_deepwater_capable is False

    # --- rig_key ---

    def test_rig_key_normalization(self):
        """Rig key is lowered, stripped, and spaces replaced with underscores."""
        entry = self._make_entry(rig_name="  DEEPWATER TITAN  ")
        assert entry.rig_key == "deepwater_titan"

    # --- rig_type_display ---

    def test_rig_type_display_drillship(self):
        """Drillship type maps to human-readable 'Drillship'."""
        entry = self._make_entry(rig_type="drillship")
        assert entry.rig_type_display == "Drillship"

    def test_rig_type_display_unknown(self):
        """None rig type maps to 'Unknown'."""
        entry = self._make_entry(rig_type=None)
        assert entry.rig_type_display == "Unknown"

    def test_rig_type_display_land_rig(self):
        """Land rig type maps to 'Land Rig'."""
        entry = self._make_entry(rig_type="land_rig")
        assert entry.rig_type_display == "Land Rig"

    # --- is_offshore_derived ---

    def test_is_offshore_derived_explicit_true(self):
        """Explicit is_offshore=True returns True."""
        entry = self._make_entry(is_offshore=True)
        assert entry.is_offshore_derived is True

    def test_is_offshore_derived_explicit_false(self):
        """Explicit is_offshore=False returns False."""
        entry = self._make_entry(is_offshore=False)
        assert entry.is_offshore_derived is False

    def test_is_offshore_derived_fallback_not_land(self):
        """When is_offshore is None, non-land rig type returns True."""
        entry = self._make_entry(rig_type="drillship", is_offshore=None)
        assert entry.is_offshore_derived is True

    def test_is_offshore_derived_fallback_land_rig(self):
        """When is_offshore is None, land_rig type returns False."""
        entry = self._make_entry(rig_type="land_rig", is_offshore=None)
        assert entry.is_offshore_derived is False

    def test_is_offshore_derived_fallback_none_type(self):
        """When both is_offshore and rig_type are None, returns True."""
        entry = self._make_entry(rig_type=None, is_offshore=None)
        assert entry.is_offshore_derived is True

    # --- intervention type display names ---

    def test_rig_type_display_wireline_unit(self):
        """Wireline unit type maps to 'Wireline Unit'."""
        entry = self._make_entry(rig_type="wireline_unit")
        assert entry.rig_type_display == "Wireline Unit"

    def test_rig_type_display_coil_tubing_unit(self):
        """Coil tubing unit type maps to 'Coil Tubing Unit'."""
        entry = self._make_entry(rig_type="coil_tubing_unit")
        assert entry.rig_type_display == "Coil Tubing Unit"

    def test_rig_type_display_lift_boat(self):
        """Lift boat type maps to 'Lift Boat'."""
        entry = self._make_entry(rig_type="lift_boat")
        assert entry.rig_type_display == "Lift Boat"

    def test_rig_type_display_snubbing_unit(self):
        """Snubbing unit type maps to 'Snubbing Unit'."""
        entry = self._make_entry(rig_type="snubbing_unit")
        assert entry.rig_type_display == "Snubbing Unit"

    def test_rig_type_display_workover_rig(self):
        """Workover rig type maps to 'Workover Rig'."""
        entry = self._make_entry(rig_type="workover_rig")
        assert entry.rig_type_display == "Workover Rig"

    def test_rig_type_display_support_vessel(self):
        """Support vessel type maps to 'Support Vessel'."""
        entry = self._make_entry(rig_type="support_vessel")
        assert entry.rig_type_display == "Support Vessel"

    def test_rig_type_display_pumping_unit(self):
        """Pumping unit type maps to 'Pumping Unit'."""
        entry = self._make_entry(rig_type="pumping_unit")
        assert entry.rig_type_display == "Pumping Unit"

    # --- intervention types are offshore ---

    def test_is_offshore_derived_wireline_unit(self):
        """Wireline unit defaults to offshore (True)."""
        entry = self._make_entry(rig_type="wireline_unit", is_offshore=None)
        assert entry.is_offshore_derived is True

    def test_is_offshore_derived_snubbing_unit(self):
        """Snubbing unit defaults to offshore (True)."""
        entry = self._make_entry(rig_type="snubbing_unit", is_offshore=None)
        assert entry.is_offshore_derived is True
