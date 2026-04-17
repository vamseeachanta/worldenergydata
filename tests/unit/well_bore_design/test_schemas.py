"""Tests for WellBoreDesign and EcdProfile data schemas."""

import pytest

from worldenergydata.well_bore_design.schemas import (
    LARGE_BORE_MIN_BIT_SIZE_IN,
    SLIM_HOLE_MAX_BIT_SIZE_IN,
    BoreType,
    CasingString,
    EcdProfile,
    WellBoreDesign,
    bore_type_from_bit_size,
)

# ---------------------------------------------------------------------------
# BoreType enum
# ---------------------------------------------------------------------------


class TestBoreTypeEnum:
    def test_has_slim_hole_value(self):
        assert BoreType.SLIM_HOLE.value == "slim_hole"

    def test_has_standard_value(self):
        assert BoreType.STANDARD.value == "standard"

    def test_has_large_bore_value(self):
        assert BoreType.LARGE_BORE.value == "large_bore"

    def test_exactly_three_members(self):
        assert len(BoreType) == 3

    def test_slim_hole_string_value_is_slim_hole(self):
        assert BoreType.SLIM_HOLE.value == "slim_hole"

    def test_members_are_distinct(self):
        values = {b.value for b in BoreType}
        assert len(values) == 3


# ---------------------------------------------------------------------------
# CasingString enum
# ---------------------------------------------------------------------------


class TestCasingStringEnum:
    def test_has_five_members(self):
        assert len(CasingString) == 5

    def test_conductor_member(self):
        assert CasingString.CONDUCTOR.value == "conductor"

    def test_surface_member(self):
        assert CasingString.SURFACE.value == "surface"

    def test_intermediate_member(self):
        assert CasingString.INTERMEDIATE.value == "intermediate"

    def test_production_member(self):
        assert CasingString.PRODUCTION.value == "production"

    def test_liner_member(self):
        assert CasingString.LINER.value == "liner"


# ---------------------------------------------------------------------------
# bore_type_from_bit_size helper
# ---------------------------------------------------------------------------


class TestBoreTypeFromBitSize:
    def test_small_bit_size_returns_slim_hole(self):
        assert bore_type_from_bit_size(6.0) == BoreType.SLIM_HOLE

    def test_bit_size_below_threshold_returns_slim_hole(self):
        assert (
            bore_type_from_bit_size(SLIM_HOLE_MAX_BIT_SIZE_IN - 0.01)
            == BoreType.SLIM_HOLE
        )

    def test_bit_size_at_slim_threshold_returns_standard(self):
        # 8.5" is exactly the boundary — classified as STANDARD
        assert bore_type_from_bit_size(SLIM_HOLE_MAX_BIT_SIZE_IN) == BoreType.STANDARD

    def test_standard_bit_size_returns_standard(self):
        assert bore_type_from_bit_size(8.5) == BoreType.STANDARD
        assert bore_type_from_bit_size(10.0) == BoreType.STANDARD
        assert bore_type_from_bit_size(12.25) == BoreType.STANDARD

    def test_large_bore_returns_large_bore(self):
        assert (
            bore_type_from_bit_size(LARGE_BORE_MIN_BIT_SIZE_IN + 0.01)
            == BoreType.LARGE_BORE
        )

    def test_large_bit_size_returns_large_bore(self):
        assert bore_type_from_bit_size(17.5) == BoreType.LARGE_BORE


# ---------------------------------------------------------------------------
# WellBoreDesign dataclass
# ---------------------------------------------------------------------------


def _make_design(**kwargs) -> WellBoreDesign:
    defaults = dict(
        well_id="TEST-001",
        bore_type=BoreType.STANDARD,
        total_depth_m=3500.0,
        water_depth_m=0.0,
        surface_bit_size_in=17.5,
        intermediate_bit_size_in=12.25,
        production_bit_size_in=8.5,
        mud_weight_ppg=9.5,
        max_mud_weight_ppg=12.0,
        min_mud_weight_ppg=9.0,
        formation_type="shale",
    )
    defaults.update(kwargs)
    return WellBoreDesign(**defaults)


class TestWellBoreDesign:
    def test_well_id_stored(self):
        d = _make_design(well_id="W-100")
        assert d.well_id == "W-100"

    def test_bore_type_stored(self):
        d = _make_design(bore_type=BoreType.SLIM_HOLE)
        assert d.bore_type == BoreType.SLIM_HOLE

    def test_total_depth_m_stored(self):
        d = _make_design(total_depth_m=4200.0)
        assert d.total_depth_m == 4200.0

    def test_water_depth_zero_for_land(self):
        d = _make_design(water_depth_m=0.0)
        assert d.is_offshore() is False

    def test_water_depth_positive_for_offshore(self):
        d = _make_design(water_depth_m=500.0)
        assert d.is_offshore() is True

    def test_sections_defaults_to_empty_list(self):
        d = _make_design()
        assert d.sections == []

    def test_sections_can_hold_casing_dicts(self):
        section = {
            "casing": CasingString.PRODUCTION,
            "bit_size_in": 8.5,
            "depth_from_m": 2500.0,
            "depth_to_m": 3500.0,
        }
        d = _make_design(sections=[section])
        assert len(d.sections) == 1
        assert d.sections[0]["casing"] == CasingString.PRODUCTION

    def test_mud_weight_ppg_stored(self):
        d = _make_design(mud_weight_ppg=10.5)
        assert d.mud_weight_ppg == 10.5

    def test_formation_type_stored(self):
        d = _make_design(formation_type="carbonate")
        assert d.formation_type == "carbonate"

    def test_notes_defaults_to_empty_string(self):
        d = _make_design()
        assert d.notes == ""

    def test_pressure_window_ppg_is_positive(self):
        d = _make_design(max_mud_weight_ppg=14.0, min_mud_weight_ppg=10.0)
        assert d.pressure_window_ppg() == pytest.approx(4.0)

    def test_pressure_window_ppg_returns_zero_when_unset(self):
        d = _make_design(max_mud_weight_ppg=0.0, min_mud_weight_ppg=0.0)
        assert d.pressure_window_ppg() == 0.0

    def test_bore_type_matches_slim_bit_size_convention(self):
        d = _make_design(bore_type=BoreType.SLIM_HOLE, production_bit_size_in=6.0)
        assert d.bore_type == BoreType.SLIM_HOLE
        assert d.production_bit_size_in < SLIM_HOLE_MAX_BIT_SIZE_IN


# ---------------------------------------------------------------------------
# EcdProfile dataclass
# ---------------------------------------------------------------------------


def _make_ecd_profile(**kwargs) -> EcdProfile:
    depths = [500.0, 1000.0, 2000.0, 3000.0]
    defaults = dict(
        well_id="TEST-001",
        bore_type=BoreType.STANDARD,
        depths_m=depths,
        ecd_ppg=[9.6, 9.7, 9.9, 10.1],
        mud_weight_ppg=9.5,
        flow_rate_gpm=450.0,
        annular_velocity_fps=[2.1, 2.1, 2.1, 2.1],
        pressure_window_ppg=[2.4, 2.3, 2.1, 1.9],
        bottleneck_depth_m=3000.0,
        min_pressure_window_ppg=1.9,
    )
    defaults.update(kwargs)
    return EcdProfile(**defaults)


class TestEcdProfile:
    def test_well_id_stored(self):
        p = _make_ecd_profile(well_id="ECD-001")
        assert p.well_id == "ECD-001"

    def test_bore_type_stored(self):
        p = _make_ecd_profile(bore_type=BoreType.SLIM_HOLE)
        assert p.bore_type == BoreType.SLIM_HOLE

    def test_ecd_ppg_list_stored(self):
        p = _make_ecd_profile()
        assert len(p.ecd_ppg) == 4

    def test_mud_weight_ppg_stored(self):
        p = _make_ecd_profile(mud_weight_ppg=10.0)
        assert p.mud_weight_ppg == 10.0

    def test_pressure_window_positive_means_safe(self):
        p = _make_ecd_profile(pressure_window_ppg=[1.0, 0.5, 0.8, 1.2])
        assert p.is_safe_at_all_depths() is True

    def test_pressure_window_negative_means_unsafe(self):
        p = _make_ecd_profile(pressure_window_ppg=[1.0, -0.1, 0.8, 1.2])
        assert p.is_safe_at_all_depths() is False

    def test_bottleneck_depth_is_optional(self):
        p = _make_ecd_profile(bottleneck_depth_m=None)
        assert p.bottleneck_depth_m is None

    def test_min_pressure_window_stored(self):
        p = _make_ecd_profile(min_pressure_window_ppg=0.75)
        assert p.min_pressure_window_ppg == 0.75

    def test_safe_depth_fraction_all_safe(self):
        p = _make_ecd_profile(pressure_window_ppg=[1.0, 0.5, 0.3, 0.8])
        assert p.safe_depth_fraction() == pytest.approx(1.0)

    def test_safe_depth_fraction_partial(self):
        p = _make_ecd_profile(pressure_window_ppg=[1.0, -0.1, 0.5, -0.2])
        assert p.safe_depth_fraction() == pytest.approx(0.5)

    def test_notes_defaults_to_empty_string(self):
        p = _make_ecd_profile()
        assert p.notes == ""
