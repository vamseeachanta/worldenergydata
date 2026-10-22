"""Synthetic arithmetic checks; calibration fixtures are NOT design data.

Formula references are the public sources cited in lift_flow_screening.
No expected result is computed by another production function.
"""

import math

import pytest

from worldenergydata.vessel_fleet.lift_flow_screening import (
    Calibration,
    Interval,
    airlift_screen,
    critical_deposition_velocity_m_s,
    minimum_vertical_velocity_m_s,
    settling_velocity_m_s,
    slugging_screen,
)


def calibration(model, values):
    """Synthetic input points and a derived Re interval have no physical basis."""
    ranges = {key: Interval(value, value) for key, value in values.items()}
    if model == "isolated_sphere":
        ranges.setdefault("particle_reynolds", Interval(1089.0, 1091.0))
    return Calibration(
        model=model,
        source_url="https://example.org/synthetic",
        source_locator="Synthetic arithmetic fixture; not source measurements",
        conditions="Synthetic test of validation and arithmetic only",
        ranges=ranges,
    )


CASES = [
    (
        settling_velocity_m_s,
        "isolated_sphere",
        dict(
            particle_diameter_m=0.003,
            solids_density_kg_m3=2650.0,
            liquid_density_kg_m3=1000.0,
            dynamic_viscosity_pa_s=0.001,
            gravity_m_s2=10.0,
            drag_coefficient=0.5,
        ),
    ),
    (
        critical_deposition_velocity_m_s,
        "horizontal_slurry",
        dict(
            pipe_id_m=0.2,
            particle_diameter_m=0.001,
            solids_density_kg_m3=2650.0,
            liquid_density_kg_m3=1000.0,
            dynamic_viscosity_pa_s=0.001,
            solids_volume_fraction=0.1,
            gravity_m_s2=10.0,
            deposition_factor=1.5,
        ),
    ),
    (
        minimum_vertical_velocity_m_s,
        "vertical_slip",
        dict(
            slip_velocity_m_s=0.2,
            solids_volume_fraction=0.1,
            required_solids_velocity_m_s=0.02,
        ),
    ),
    (
        airlift_screen,
        "isothermal_airlift",
        dict(
            injection_depth_m=10.0,
            submerged_length_m=20.0,
            lift_above_surface_m=2.0,
            gas_flow_at_outlet_m3_s=0.01,
            outlet_pressure_abs_pa=100000.0,
            liquid_density_kg_m3=1000.0,
            gravity_m_s2=10.0,
            lift_efficiency=0.2,
        ),
    ),
    (
        slugging_screen,
        "vertical_drift_flux",
        dict(
            superficial_gas_velocity_m_s=0.3,
            superficial_liquid_velocity_m_s=0.7,
            distribution_parameter=1.2,
            drift_velocity_m_s=0.2,
            bubble_slug_void_fraction=0.2,
            maximum_void_fraction=0.6,
        ),
    ),
]


def test_settling_hand_balance():
    """w=sqrt(4*10*.003*(2650/1000-1)/(3*.5))=sqrt(.132) m/s.

    Re=1000*sqrt(.132)*.003/.001 is about 1090; source S1, section 4.4.
    The 1089-1091 interval permits roundoff without hiding a missing term.
    """
    fn, model, values = CASES[0]
    domain = calibration(model, values)
    assert fn(**values, calibration=domain) == pytest.approx(math.sqrt(0.132))


def test_deposition_hand_calculation():
    """1.5*sqrt(2*10*.2*(2650/1000-1))=1.5*sqrt(6.6) m/s."""
    fn, model, values = CASES[1]
    assert fn(**values, calibration=calibration(model, values)) == pytest.approx(
        1.5 * math.sqrt(6.6)
    )


def test_vertical_minimum_hand_calculation():
    """j=(1-C)*w+v_s=.9*.2+.02=.20; this is a positive solids flux."""
    fn, model, values = CASES[2]
    assert fn(**values, calibration=calibration(model, values)) == pytest.approx(0.2)


def test_airlift_hand_energy_balance():
    """Pin=100000+1000*10*10=200000 Pa; Pgas=1000*ln(2) W.

    Q=.2*1000*ln(2)/(1000*10*2)=.01*ln(2) m3/s.
    Published efficiency relation: source S3, equation (5), in module docs.
    """
    fn, model, values = CASES[3]
    result = fn(**values, calibration=calibration(model, values))
    assert result.injection_pressure_abs_pa == 200000.0
    assert result.isothermal_gas_power_w == pytest.approx(1000 * math.log(2))
    assert result.energy_limited_liquid_flow_m3_s == pytest.approx(0.01 * math.log(2))


def test_slug_boundary_hand_calculation():
    """alpha=.3/(1.2*(.3+.7)+.2)=3/14, above the .2 threshold."""
    fn, model, values = CASES[4]
    result = fn(**values, calibration=calibration(model, values))
    assert result.void_fraction == pytest.approx(3 / 14)
    assert result.indication == "slugging_possible"
    changed = {**values, "superficial_gas_velocity_m_s": 0.1}
    result = fn(**changed, calibration=calibration(model, changed))
    # .1/(1.2*(.1+.7)+.2)=5/58 < .2, independent hand calculation.
    assert result.void_fraction == pytest.approx(5 / 58)
    assert result.indication == "bubble_indicated"


@pytest.mark.parametrize(
    "offset,indication", [(-1e-9, "slugging_possible"), (1e-9, "bubble_indicated")]
)
def test_slug_classification_near_threshold(offset, indication):
    """Bracket alpha=3/14 without requiring bit-exact boundary arithmetic."""
    fn, model, values = CASES[4]
    changed = {**values, "bubble_slug_void_fraction": 3 / 14 + offset}
    result = fn(**changed, calibration=calibration(model, changed))
    assert result.void_fraction == pytest.approx(3 / 14)
    assert result.indication == indication


@pytest.mark.parametrize("fn,model,values", CASES)
@pytest.mark.parametrize("invalid", [-1.0, float("nan"), float("inf"), True, "1"])
def test_invalid_numeric_inputs(fn, model, values, invalid):
    changed = {**values, next(iter(values)): invalid}
    with pytest.raises((ValueError, TypeError)):
        fn(**changed, calibration=calibration(model, values))


@pytest.mark.parametrize("fn,model,values", CASES)
def test_negative_inputs_rejected_within_calibration(fn, model, values):
    name = next(iter(values))
    changed = {**values, name: -1.0}
    with pytest.raises(ValueError, match=f"{name} must be positive"):
        fn(**changed, calibration=calibration(model, changed))


@pytest.mark.parametrize("fn,model,values", CASES)
def test_outside_calibration_refused(fn, model, values):
    changed = {**values, next(iter(values)): values[next(iter(values))] * 2}
    with pytest.raises(ValueError, match="calibration"):
        fn(**changed, calibration=calibration(model, values))


@pytest.mark.parametrize(
    "index,changes",
    [
        (0, {"solids_density_kg_m3": 900.0}),
        (1, {"particle_diameter_m": 0.3}),
        (1, {"solids_volume_fraction": 1.0}),
        (2, {"required_solids_velocity_m_s": 0.0}),
        (2, {"solids_volume_fraction": 1.0}),
        (3, {"injection_depth_m": 21.0}),
        (3, {"lift_efficiency": 1.01}),
        (3, {"lift_above_surface_m": 0.0}),
        (3, {"outlet_pressure_abs_pa": 0.0}),
        (4, {"maximum_void_fraction": 0.2}),
        (4, {"maximum_void_fraction": 1.0}),
        (4, {"distribution_parameter": 0.01, "drift_velocity_m_s": 0.0}),
    ],
)
def test_physical_sign_and_order_even_if_calibration_permits(index, changes):
    fn, model, values = CASES[index]
    values = {**values, **changes}
    with pytest.raises(ValueError):
        fn(**values, calibration=calibration(model, values))


def test_wrong_units_and_missing_ranges_refused():
    fn, model, values = CASES[1]
    domain_values = dict(values)
    domain_values["pipe_id_mm"] = domain_values.pop("pipe_id_m")
    with pytest.raises(ValueError, match="fields"):
        fn(**values, calibration=calibration(model, domain_values))


def test_settling_inconsistent_drag_reynolds_refused():
    fn, model, values = CASES[0]
    domain = calibration(model, {**values, "particle_reynolds": 1.0})
    with pytest.raises(ValueError, match="particle_reynolds"):
        fn(**values, calibration=domain)


def test_wrong_model_refused():
    fn, _, values = CASES[1]
    with pytest.raises(ValueError, match="model"):
        fn(**values, calibration=calibration("vertical_slip", values))


@pytest.mark.parametrize("low,high", [(2.0, 1.0), (0.0, math.inf), (True, 1.0)])
def test_invalid_interval(low, high):
    with pytest.raises(ValueError):
        Interval(low, high)


def test_calibration_requires_provenance_and_is_immutable():
    values = {"x_m": Interval(1.0, 2.0)}
    with pytest.raises(ValueError):
        Calibration("vertical_slip", "", "", "", values)
    domain = calibration("vertical_slip", {"x_m": 1.0})
    with pytest.raises(TypeError):
        domain.ranges["x_m"] = Interval(0.0, 2.0)


@pytest.mark.parametrize("userinfo", ["user@", ":pass@", "user:pass@"])
def test_calibration_rejects_url_credentials(userinfo):
    """Synthetic URL userinfo exercises rejection; no credential is used."""
    with pytest.raises(ValueError, match="public HTTPS source reference"):
        Calibration(
            model="vertical_slip",
            source_url=f"https://{userinfo}example.org/synthetic",
            source_locator="Synthetic fixture",
            conditions="Synthetic validation only",
            ranges={"x_m": Interval(1.0, 2.0)},
        )


def test_unresolved_upper_regime_refused():
    fn, model, values = CASES[4]
    changed = {**values, "superficial_gas_velocity_m_s": 4.0}
    with pytest.raises(ValueError, match="void"):
        fn(**changed, calibration=calibration(model, changed))
