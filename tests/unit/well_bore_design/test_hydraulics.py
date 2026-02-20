"""Tests for WellBoreHydraulics calculator."""

import pytest

from worldenergydata.well_bore_design.hydraulics import WellBoreHydraulics
from worldenergydata.well_bore_design.schemas import BoreType


@pytest.fixture
def hydro():
    return WellBoreHydraulics()


# ---------------------------------------------------------------------------
# annular_velocity_fps
# ---------------------------------------------------------------------------


class TestAnnularVelocity:
    def test_returns_positive_float(self, hydro):
        av = hydro.annular_velocity_fps(500, 8.5, 5.0)
        assert isinstance(av, float)
        assert av > 0.0

    def test_known_value(self, hydro):
        # AV = 0.408 * 500 / (8.5^2 - 5.0^2) = 204 / (72.25 - 25) = 204/47.25
        expected = 0.408 * 500.0 / (8.5**2 - 5.0**2)
        assert hydro.annular_velocity_fps(500, 8.5, 5.0) == pytest.approx(expected, rel=1e-4)

    def test_larger_annular_gap_gives_lower_velocity(self, hydro):
        # Wider annulus → lower velocity for the same flow rate
        av_slim = hydro.annular_velocity_fps(500, 6.0, 3.5)
        av_std = hydro.annular_velocity_fps(500, 8.5, 5.0)
        assert av_slim > av_std

    def test_higher_flow_rate_gives_higher_velocity(self, hydro):
        av_low = hydro.annular_velocity_fps(300, 8.5, 5.0)
        av_high = hydro.annular_velocity_fps(600, 8.5, 5.0)
        assert av_high > av_low

    def test_pipe_od_equal_to_hole_od_raises(self, hydro):
        with pytest.raises(ValueError):
            hydro.annular_velocity_fps(500, 6.0, 6.0)

    def test_pipe_od_greater_than_hole_od_raises(self, hydro):
        with pytest.raises(ValueError):
            hydro.annular_velocity_fps(500, 5.0, 6.0)


# ---------------------------------------------------------------------------
# pressure_loss_psi_per_100ft
# ---------------------------------------------------------------------------


class TestPressureLoss:
    def test_returns_positive_float(self, hydro):
        dp = hydro.pressure_loss_psi_per_100ft(
            flow_rate_gpm=500,
            mud_weight_ppg=10.0,
            plastic_viscosity_cp=20,
            yield_point_lbf_100ft2=15,
            hole_od_in=8.5,
            pipe_od_in=5.0,
        )
        assert dp > 0.0

    def test_higher_flow_rate_gives_higher_pressure_loss(self, hydro):
        common = dict(
            mud_weight_ppg=10.0,
            plastic_viscosity_cp=20,
            yield_point_lbf_100ft2=15,
            hole_od_in=8.5,
            pipe_od_in=5.0,
        )
        dp_low = hydro.pressure_loss_psi_per_100ft(flow_rate_gpm=200, **common)
        dp_high = hydro.pressure_loss_psi_per_100ft(flow_rate_gpm=600, **common)
        assert dp_high > dp_low

    def test_slim_hole_higher_loss_than_standard(self, hydro):
        common = dict(
            flow_rate_gpm=500,
            mud_weight_ppg=10.0,
            plastic_viscosity_cp=20,
            yield_point_lbf_100ft2=15,
        )
        dp_slim = hydro.pressure_loss_psi_per_100ft(hole_od_in=6.0, pipe_od_in=3.5, **common)
        dp_std = hydro.pressure_loss_psi_per_100ft(hole_od_in=8.5, pipe_od_in=5.0, **common)
        assert dp_slim > dp_std

    def test_pipe_od_equal_to_hole_od_raises(self, hydro):
        with pytest.raises(ValueError):
            hydro.pressure_loss_psi_per_100ft(500, 10.0, 20, 15, 6.0, 6.0)

    def test_higher_viscosity_gives_higher_laminar_loss(self, hydro):
        common = dict(
            flow_rate_gpm=100,  # keep laminar
            mud_weight_ppg=9.0,
            yield_point_lbf_100ft2=10,
            hole_od_in=8.5,
            pipe_od_in=5.0,
        )
        dp_low_pv = hydro.pressure_loss_psi_per_100ft(plastic_viscosity_cp=10, **common)
        dp_high_pv = hydro.pressure_loss_psi_per_100ft(plastic_viscosity_cp=40, **common)
        assert dp_high_pv > dp_low_pv


# ---------------------------------------------------------------------------
# ecd_ppg
# ---------------------------------------------------------------------------


class TestEcdPpg:
    def test_ecd_greater_than_mud_weight(self, hydro):
        ecd = hydro.ecd_ppg(
            mud_weight_ppg=9.5,
            annular_pressure_loss_psi=200.0,
            depth_ft=5000.0,
        )
        assert ecd > 9.5

    def test_zero_pressure_loss_gives_mud_weight(self, hydro):
        ecd = hydro.ecd_ppg(
            mud_weight_ppg=9.5,
            annular_pressure_loss_psi=0.0,
            depth_ft=5000.0,
        )
        assert ecd == pytest.approx(9.5)

    def test_known_ecd_calculation(self, hydro):
        # ECD = 9.5 + 100 / (0.052 * 5000) = 9.5 + 100/260 = 9.5 + 0.3846
        expected = 9.5 + 100.0 / (0.052 * 5000.0)
        assert hydro.ecd_ppg(9.5, 100.0, 5000.0) == pytest.approx(expected, rel=1e-5)

    def test_zero_depth_raises(self, hydro):
        with pytest.raises(ValueError):
            hydro.ecd_ppg(9.5, 100.0, 0.0)

    def test_negative_depth_raises(self, hydro):
        with pytest.raises(ValueError):
            hydro.ecd_ppg(9.5, 100.0, -100.0)

    def test_deeper_well_gives_lower_ecd_for_same_loss(self, hydro):
        ecd_shallow = hydro.ecd_ppg(9.5, 100.0, 2000.0)
        ecd_deep = hydro.ecd_ppg(9.5, 100.0, 8000.0)
        assert ecd_shallow > ecd_deep


# ---------------------------------------------------------------------------
# hole_cleaning_index
# ---------------------------------------------------------------------------


class TestHoleCleaningIndex:
    def test_adequate_conditions_return_greater_than_one(self, hydro):
        # AV = 3.0 fps, mud weight = 10 ppg, cutting density = 21.7 ppg → HCI > 1
        hci = hydro.hole_cleaning_index(
            annular_velocity_fps=3.0,
            mud_weight_ppg=10.0,
        )
        assert hci > 1.0

    def test_low_av_gives_hci_below_one(self, hydro):
        hci = hydro.hole_cleaning_index(
            annular_velocity_fps=0.5,
            mud_weight_ppg=9.0,
        )
        assert hci < 1.0

    def test_known_hci_calculation(self, hydro):
        # HCI = 2.0 * 10.0 / 21.7
        expected = 2.0 * 10.0 / 21.7
        assert hydro.hole_cleaning_index(2.0, 10.0) == pytest.approx(expected, rel=1e-5)

    def test_custom_cutting_density_used(self, hydro):
        hci_default = hydro.hole_cleaning_index(2.0, 10.0)
        hci_custom = hydro.hole_cleaning_index(2.0, 10.0, cutting_density_ppg=25.0)
        assert hci_default != hci_custom

    def test_zero_cutting_density_raises(self, hydro):
        with pytest.raises(ValueError):
            hydro.hole_cleaning_index(2.0, 10.0, cutting_density_ppg=0.0)


# ---------------------------------------------------------------------------
# compare_bore_types
# ---------------------------------------------------------------------------


class TestCompareBoreTypes:
    def test_returns_dict_with_three_keys(self, hydro):
        result = hydro.compare_bore_types(
            flow_rate_gpm=500,
            mud_weight_ppg=10.0,
            depth_ft=8000.0,
        )
        assert set(result.keys()) == {
            BoreType.SLIM_HOLE.value,
            BoreType.STANDARD.value,
            BoreType.LARGE_BORE.value,
        }

    def test_each_entry_has_required_keys(self, hydro):
        result = hydro.compare_bore_types(500, 10.0, 8000.0)
        required = {
            "ecd_ppg",
            "annular_velocity_fps",
            "pressure_loss_psi_per_100ft",
            "hole_cleaning_index",
            "total_pressure_loss_psi",
        }
        for bore_val, data in result.items():
            assert required.issubset(data.keys()), f"Missing keys for {bore_val}"

    def test_slim_hole_higher_annular_velocity(self, hydro):
        result = hydro.compare_bore_types(500, 10.0, 8000.0)
        av_slim = result[BoreType.SLIM_HOLE.value]["annular_velocity_fps"]
        av_std = result[BoreType.STANDARD.value]["annular_velocity_fps"]
        assert av_slim > av_std

    def test_slim_hole_higher_ecd_than_standard(self, hydro):
        result = hydro.compare_bore_types(500, 10.0, 8000.0)
        ecd_slim = result[BoreType.SLIM_HOLE.value]["ecd_ppg"]
        ecd_std = result[BoreType.STANDARD.value]["ecd_ppg"]
        assert ecd_slim > ecd_std

    def test_slim_hole_higher_pressure_loss_than_standard(self, hydro):
        result = hydro.compare_bore_types(500, 10.0, 8000.0)
        dp_slim = result[BoreType.SLIM_HOLE.value]["pressure_loss_psi_per_100ft"]
        dp_std = result[BoreType.STANDARD.value]["pressure_loss_psi_per_100ft"]
        assert dp_slim > dp_std

    def test_all_ecd_values_greater_than_mud_weight(self, hydro):
        mw = 10.0
        result = hydro.compare_bore_types(500, mw, 8000.0)
        for key, data in result.items():
            assert data["ecd_ppg"] >= mw, f"ECD below mud weight for {key}"

    def test_all_hci_values_are_positive(self, hydro):
        result = hydro.compare_bore_types(500, 10.0, 8000.0)
        for key, data in result.items():
            assert data["hole_cleaning_index"] > 0.0, f"Non-positive HCI for {key}"
