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
        assert hydro.annular_velocity_fps(500, 8.5, 5.0) == pytest.approx(
            expected, rel=1e-4
        )

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
        # Synthetic high-flow fixture: leave the yield-floor plateau so this
        # still checks a strict increase (agent-pack.md r1, 2026, section 5 C11).
        dp_high = hydro.pressure_loss_psi_per_100ft(flow_rate_gpm=5000, **common)
        assert dp_high > dp_low

    def test_slim_hole_higher_loss_than_standard(self, hydro):
        common = dict(
            flow_rate_gpm=500,
            mud_weight_ppg=10.0,
            plastic_viscosity_cp=20,
            yield_point_lbf_100ft2=15,
        )
        dp_slim = hydro.pressure_loss_psi_per_100ft(
            hole_od_in=6.0, pipe_od_in=3.5, **common
        )
        dp_std = hydro.pressure_loss_psi_per_100ft(
            hole_od_in=8.5, pipe_od_in=5.0, **common
        )
        assert dp_slim > dp_std

    def test_pipe_od_equal_to_hole_od_raises(self, hydro):
        with pytest.raises(ValueError):
            hydro.pressure_loss_psi_per_100ft(500, 10.0, 20, 15, 6.0, 6.0)

    def test_higher_viscosity_gives_higher_laminar_loss(self, hydro):
        common = dict(
            # Synthetic fixtures keep the legacy branch laminar and its loss
            # above the yield floor (agent-pack.md r1, 2026, section 5 C11).
            flow_rate_gpm=1,
            mud_weight_ppg=9.0,
            yield_point_lbf_100ft2=10,
            hole_od_in=8.5,
            pipe_od_in=5.0,
        )
        dp_low_pv = hydro.pressure_loss_psi_per_100ft(
            plastic_viscosity_cp=10000, **common
        )
        dp_high_pv = hydro.pressure_loss_psi_per_100ft(
            plastic_viscosity_cp=40000, **common
        )
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


# Yield-floor regressions with independent force-balance hand calculations.
#
# Source: annular laminar-flow derivation (2025), Appendix A4, A6 and A9,
# https://doi.org/10.1007/s13202-024-01919-z. With radial gap h, those equations
# give tau_wall = h/2 * dP/dL and tau_wall >= tau_y for positive flow.
# Thus dP/dL >= 4*tau_y/(hole_diameter - pipe_diameter).
# The repository agent-pack.md, revision 1 (2026), section 5, C11, writes out
# the field-unit conversion: 4*(YP/100)*12*100/(144*diameter_gap), giving
# YP/(3*diameter_gap) psi per 100 ft. The factors are unit definitions,
# not fitted coefficients. The synthetic cases below reproduce C11 and add
# a low-flow case. Expected values are rational hand results, independent
# of the implementation. Assertions pin the floor-dominated outputs; they
# do not establish exact physical pressure losses.


@pytest.mark.parametrize(
    "flow,mud,pv,yp,hole,pipe,expected_floor",
    [
        (500, 10, 20, 15, 8.5, 5.0, 10 / 7),
        (100, 9, 10, 10, 8.5, 5.0, 20 / 21),
        (100, 9, 40, 10, 8.5, 5.0, 20 / 21),
        (500, 10, 20, 15, 6.0, 3.5, 2.0),
        (1, 10, 20, 15, 8.5, 5.0, 10 / 7),
    ],
)
def test_flowing_pressure_loss_obeys_yield_floor(
    flow, mud, pv, yp, hole, pipe, expected_floor
):
    """Hand: 15/(3*3.5)=10/7; 10/(3*3.5)=20/21; 15/(3*2.5)=2.

    The first four cases exercise the existing turbulent branch; the last
    exercises its laminar branch. Table C11 in agent-pack.md r1 (2026),
    section 5, gives retained turbulent losses of 0.0487, 0.0023, 0.0029
    and 0.2497 psi/100 ft, respectively. The 1 gpm laminar estimate is
    0.0219 psi/100 ft. Each is below its hand-calculated floor above;
    these outputs are not exact physical flow solutions.
    """
    loss = WellBoreHydraulics().pressure_loss_psi_per_100ft(
        flow, mud, pv, yp, hole, pipe
    )
    assert loss == pytest.approx(expected_floor, rel=1e-12)


def test_yield_floor_reaches_ecd_and_pressure_window():
    """C11 hand calculation, agent-pack.md r1 (2026), section 5.

    Standard annulus: loss >= 10/7 psi/100 ft, so at 10000 ft total loss
    >= 1000/7 psi. The existing ECD definition (pack R2) uses 0.052:
    ECD >= 10 + (1000/7)/(0.052*10000) = 10 + 25/91 ppg.
    The synthetic fracture limit 10.2 is below this bound. The existing
    pressure-window function rounds its returned ECD; the comparison
    interface exposes the unrounded result for the numerical assertion.
    """
    from worldenergydata.well_bore_design.decision_framework import BoreTypeDecision

    comparison = WellBoreHydraulics().compare_bore_types(500, 10, 10000)
    standard = comparison[BoreType.STANDARD.value]
    assert standard["total_pressure_loss_psi"] == pytest.approx(1000 / 7, rel=1e-12)
    assert standard["ecd_ppg"] == pytest.approx(10 + 25 / 91, rel=1e-12)
    result = BoreTypeDecision().pressure_window_check(
        BoreType.STANDARD, 10, 10.2, 9.5, 500, 10000
    )
    assert result["compatible"] is False
    assert result["limiting_factor"] == "ecd_exceeds_fracture_gradient"


@pytest.mark.parametrize("plastic_viscosity_cp", [10, 20, 80])
def test_realistic_flow_and_viscosity_remain_on_yield_floor(plastic_viscosity_cp):
    """Record the unresolved plateau tracked by #1288, not physical invariance.

    At 200 and 600 gpm with 10, 20 or 80 cP, the standard-annulus estimate
    stays below the 10/7 psi/100 ft floor. Its ECD therefore also stays fixed.
    Independent evaluation of the retained formulas gives the largest of
    these six estimates at 600 gpm and 80 cP: AV = 5.181 ft/s, Re = 14639
    (turbulent), f = 0.006756 and loss = 0.0884 psi/100 ft, approximately
    16 times below the floor. Table C11 in agent-pack.md r1 (2026),
    section 5, records the same comparison for the four turbulent fixtures.
    """
    hydro = WellBoreHydraulics()
    for flow_rate_gpm in (200, 600):
        comparison = hydro.compare_bore_types(
            flow_rate_gpm, 10, 10000, plastic_viscosity_cp, 15
        )
        standard = comparison[BoreType.STANDARD.value]
        assert standard["pressure_loss_psi_per_100ft"] == pytest.approx(
            10 / 7, rel=1e-12
        )
        assert standard["ecd_ppg"] == pytest.approx(10 + 25 / 91, rel=1e-12)


def test_zero_flow_has_no_circulating_loss():
    """Zero imposed flow has no circulating loss; the yield floor is inactive."""
    assert WellBoreHydraulics().pressure_loss_psi_per_100ft(0, 10, 20, 15, 8.5, 5) == 0


def test_zero_yield_point_still_has_viscous_loss():
    """A synthetic yield-free viscous fluid has positive loss at positive flow."""
    assert WellBoreHydraulics().pressure_loss_psi_per_100ft(500, 10, 20, 0, 8.5, 5) > 0


def test_zero_density_is_invalid():
    """Zero density is outside the retained correlation's physical domain."""
    with pytest.raises(ValueError, match="mud_weight_ppg"):
        WellBoreHydraulics().pressure_loss_psi_per_100ft(500, 0, 20, 15, 8.5, 5)


def test_zero_viscosity_and_yield_point_are_invalid():
    """The retained correlation has no inviscid, yield-free fluid model."""
    with pytest.raises(ValueError, match="rheology"):
        WellBoreHydraulics().pressure_loss_psi_per_100ft(500, 10, 0, 0, 8.5, 5)


@pytest.mark.parametrize(
    "parameter",
    [
        "flow_rate_gpm",
        "mud_weight_ppg",
        "plastic_viscosity_cp",
        "yield_point_lbf_100ft2",
        "hole_od_in",
        "pipe_od_in",
    ],
)
@pytest.mark.parametrize("invalid", [-1.0, float("nan"), float("inf")])
def test_invalid_inputs_cannot_bypass_yield_floor(parameter, invalid):
    """Synthetic invalid scalars violate finite, nonnegative physical inputs."""
    inputs = {
        "flow_rate_gpm": 500,
        "mud_weight_ppg": 10,
        "plastic_viscosity_cp": 20,
        "yield_point_lbf_100ft2": 15,
        "hole_od_in": 8.5,
        "pipe_od_in": 5,
    }
    inputs[parameter] = invalid
    with pytest.raises(ValueError, match=parameter):
        WellBoreHydraulics().pressure_loss_psi_per_100ft(**inputs)
