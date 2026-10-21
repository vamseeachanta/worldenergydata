"""Bounded lift-riser screening; no design acceptance or default calibration.

Public equation sources (the companion HTML contains the sources table):
S1: Slurry Transport, section 4.4, drag balance and particle Reynolds number:
https://eng.libretexts.org/Bookshelves/Civil_Engineering/Slurry_Transport_(Miedema)/04%3A_The_Terminal_Settling_Velocity_of_Particles/4.04%3A_Terminal_Settling_Velocity_Equations
S2: Slurry Transport, section 7.8, definition of the deposit Froude number:
https://eng.libretexts.org/Bookshelves/Civil_Engineering/Slurry_Transport_(Miedema)/07%3A_The_Delft_Head_Loss_and_Limit_Deposit_Velocity_Framework/7.08%3A_The_Limit_Deposit_Velocity
S3: CO2 capture using gas-lift pumps operating under two-phase flow conditions,
2024, equation (5), isothermal lifting efficiency:
https://www.sciencedirect.com/science/article/pii/S0017931024002059
S4: Overview of Void Fraction Measurement Techniques, Databases and
Correlations for Two-Phase Flow in Small Diameter Channels, 2020, equation (6):
https://doi.org/10.3390/fluids5040216

All empirical values AND numeric applicability bounds are required inputs
with a source URL, locator and conditions. Those references are caller-attested,
not authenticated or qualified by this code. Bounds are inclusive; a point
domain is allowed for a single verified condition. No source values are bundled.
Geometry, fluid, pressure, temperature and material applicability must be
established in the calibration conditions before use. A numeric range alone
does not establish that a correlation applies to a different physical system.
"""

from dataclasses import dataclass
from math import isfinite, log1p, sqrt
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlsplit


def _number(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite SI number")
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")


def _positive(**values: float) -> None:
    for name, value in values.items():
        _number(name, value)
        if value <= 0:
            raise ValueError(f"{name} must be positive")


def _fraction(name: str, value: float) -> None:
    _number(name, value)
    if not 0 < value < 1:
        raise ValueError(f"{name} must be strictly between zero and one")


@dataclass(frozen=True)
class Interval:
    """Finite inclusive calibration limits, in the unit of the named input.

    Equal endpoints specify one calibration condition. Numeric order is a
    mathematical condition, not an engineering limit. No defaults are provided.
    """

    lower: float
    upper: float

    def __post_init__(self) -> None:
        _number("lower", self.lower)
        _number("upper", self.upper)
        if self.lower > self.upper:
            raise ValueError("calibration interval order is reversed")

    def require(self, name: str, value: float) -> None:
        """Refuse nonfinite values or values outside this inclusive interval."""
        _number(name, value)
        if not self.lower <= value <= self.upper:
            raise ValueError(f"{name} outside calibration interval")


@dataclass(frozen=True)
class Calibration:
    """Required, immutable, caller-attested source and applicability envelope.

    Every numeric input must have an Interval under its exact SI argument name.
    Settling also requires a particle_reynolds interval for drag consistency.
    The model discriminator prevents reuse of a horizontal deposition envelope
    as vertical transport evidence. conditions identifies geometry, fluid,
    temperature, pressure, particle shape/distribution and other restrictions.
    A source string is traceability, not proof of a valid calibration.
    """

    model: str
    source_url: str
    source_locator: str
    conditions: str
    ranges: Mapping[str, Interval]

    def __post_init__(self) -> None:
        for name in ("model", "source_url", "source_locator", "conditions"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"calibration {name} is required")
        parsed = urlsplit(self.source_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username:
            raise ValueError("calibration requires a public HTTPS source reference")
        if not self.ranges or any(
            not isinstance(key, str) or not isinstance(value, Interval)
            for key, value in self.ranges.items()
        ):
            raise ValueError("calibration requires named intervals")
        object.__setattr__(self, "ranges", MappingProxyType(dict(self.ranges)))

    def require(self, model: str, values: Mapping[str, float], *, derived=()) -> None:
        """Require the matching model and exact fields; then check all values."""
        if self.model != model:
            raise ValueError("calibration model does not match the screen")
        if set(self.ranges) != set(values) | set(derived):
            raise ValueError("calibration fields must match all SI inputs exactly")
        for name, value in values.items():
            self.ranges[name].require(name, value)


def settling_velocity_m_s(
    *,
    particle_diameter_m: float,
    solids_density_kg_m3: float,
    liquid_density_kg_m3: float,
    dynamic_viscosity_pa_s: float,
    gravity_m_s2: float,
    drag_coefficient: float,
    calibration: Calibration,
) -> float:
    """Isolated sphere terminal speed [m/s], NOT hindered slurry settling.

    S1 gives w=sqrt(4*g*d*(rho_s/rho_l-1)/(3*Cd)). The factors 4/3
    arise from sphere volume / projected area and the dynamic-pressure 1/2.
    Cd must be sourced for the returned Re=rho_l*w*d/mu and particle shape;
    the mandatory particle_reynolds interval rejects inconsistent Cd use.
    Valid only for steady settling of a heavier isolated sphere in Newtonian
    liquid under the supplied calibration. No wall or particle interaction
    correction is assumed. All inputs positive; rho_s must exceed rho_l.
    """
    values = dict(
        particle_diameter_m=particle_diameter_m,
        solids_density_kg_m3=solids_density_kg_m3,
        liquid_density_kg_m3=liquid_density_kg_m3,
        dynamic_viscosity_pa_s=dynamic_viscosity_pa_s,
        gravity_m_s2=gravity_m_s2,
        drag_coefficient=drag_coefficient,
    )
    calibration.require("isolated_sphere", values, derived=("particle_reynolds",))
    _positive(**values)
    if solids_density_kg_m3 <= liquid_density_kg_m3:
        raise ValueError("solids density must exceed liquid density")
    velocity = sqrt(
        4
        * gravity_m_s2
        * particle_diameter_m
        * (solids_density_kg_m3 / liquid_density_kg_m3 - 1)
        / (3 * drag_coefficient)
    )
    _positive(settling_velocity_m_s=velocity)
    reynolds = (
        liquid_density_kg_m3 * velocity * particle_diameter_m / dynamic_viscosity_pa_s
    )
    calibration.ranges["particle_reynolds"].require("particle_reynolds", reynolds)
    return velocity


def critical_deposition_velocity_m_s(
    *,
    pipe_id_m: float,
    particle_diameter_m: float,
    solids_density_kg_m3: float,
    liquid_density_kg_m3: float,
    dynamic_viscosity_pa_s: float,
    solids_volume_fraction: float,
    gravity_m_s2: float,
    deposition_factor: float,
    calibration: Calibration,
) -> float:
    """Horizontal slurry deposition threshold [m/s]; not a vertical-riser limit.

    S2 defines FL=v/sqrt(2*g*D*(rho_s/rho_l-1)); hence the factor 2.
    FL is REQUIRED, with source covering d, D, concentration, fluid and size
    distribution in this calibration. No empirical FL default or safety margin
    is supplied. Positive Newtonian fluid data, 0<C<1 and 0<d<D are necessary;
    the cited calibration must impose narrower applicable bounds. Operation
    must exceed this threshold with a separately established margin.
    """
    values = dict(
        pipe_id_m=pipe_id_m,
        particle_diameter_m=particle_diameter_m,
        solids_density_kg_m3=solids_density_kg_m3,
        liquid_density_kg_m3=liquid_density_kg_m3,
        dynamic_viscosity_pa_s=dynamic_viscosity_pa_s,
        solids_volume_fraction=solids_volume_fraction,
        gravity_m_s2=gravity_m_s2,
        deposition_factor=deposition_factor,
    )
    calibration.require("horizontal_slurry", values)
    _positive(**values)
    _fraction("solids_volume_fraction", solids_volume_fraction)
    if particle_diameter_m >= pipe_id_m or solids_density_kg_m3 <= liquid_density_kg_m3:
        raise ValueError(
            "require particle diameter < pipe ID and solids > liquid density"
        )
    velocity = deposition_factor * sqrt(
        2 * gravity_m_s2 * pipe_id_m * (solids_density_kg_m3 / liquid_density_kg_m3 - 1)
    )
    _positive(critical_deposition_velocity_m_s=velocity)
    return velocity


def minimum_vertical_velocity_m_s(
    *,
    slip_velocity_m_s: float,
    solids_volume_fraction: float,
    required_solids_velocity_m_s: float,
    calibration: Calibration,
) -> float:
    """Minimum upward mixture flux [m/s] for specified positive solids speed.

    Area-averaged continuity: j=(1-C)*v_l+C*v_s; phase slip w=v_l-v_s,
    so j=(1-C)*w+v_s. These unit coefficients are kinematic identities, not
    empirical constants. C is IN-SITU volume fraction, not delivered fraction.
    Valid only for steady vertical upward two-phase liquid/solid flow with a
    sourced effective phase slip for the calibration's geometry and slurry.
    Isolated settling speed may be used only where dilute applicability is
    independently established. All inputs positive, 0<C<1; no gas, transient,
    heterogeneous bed, cohesion or arbitrary inclined-pipe extrapolation.
    """
    values = dict(
        slip_velocity_m_s=slip_velocity_m_s,
        solids_volume_fraction=solids_volume_fraction,
        required_solids_velocity_m_s=required_solids_velocity_m_s,
    )
    calibration.require("vertical_slip", values)
    _positive(**values)
    _fraction("solids_volume_fraction", solids_volume_fraction)
    velocity = (
        1 - solids_volume_fraction
    ) * slip_velocity_m_s + required_solids_velocity_m_s
    _positive(minimum_vertical_velocity_m_s=velocity)
    return velocity


@dataclass(frozen=True)
class AirliftScreen:
    """Energy-balance estimate, not a hydraulic operating point or capacity."""

    injection_pressure_abs_pa: float
    isothermal_gas_power_w: float
    energy_limited_liquid_flow_m3_s: float


def airlift_screen(
    *,
    injection_depth_m: float,
    submerged_length_m: float,
    lift_above_surface_m: float,
    gas_flow_at_outlet_m3_s: float,
    outlet_pressure_abs_pa: float,
    liquid_density_kg_m3: float,
    gravity_m_s2: float,
    lift_efficiency: float,
    calibration: Calibration,
) -> AirliftScreen:
    """Simple isothermal gas-lift energy screen, using S3 equation (5).

    Pin=Pout+rho*g*depth; gas power=Pout*Qg_out*ln(Pin/Pout);
    Qliquid=eta*power/(rho*g*lift). Hydrostatics and pressure ratio use no
    empirical constants. eta (0<eta<=1) must cover all expansion-to-lift losses
    at the sourced condition; it is NOT compressor efficiency. Gas rate is
    volumetric at outlet ABSOLUTE pressure and the same isothermal temperature,
    not an unspecified standard volume. Depth is below the reservoir surface;
    lift is above it; outlet and reservoir surface pressures are equal.
    Valid for ideal isothermal gas, constant-density liquid, positive lift,
    steady operation within calibration, and injection inside submerged length.
    Excludes solids, dissolution, nonideal deep-pressure gas, dynamics and a
    hydraulic pressure-loss solution. This is not a deep-sea capacity prediction.
    """
    values = dict(
        injection_depth_m=injection_depth_m,
        submerged_length_m=submerged_length_m,
        lift_above_surface_m=lift_above_surface_m,
        gas_flow_at_outlet_m3_s=gas_flow_at_outlet_m3_s,
        outlet_pressure_abs_pa=outlet_pressure_abs_pa,
        liquid_density_kg_m3=liquid_density_kg_m3,
        gravity_m_s2=gravity_m_s2,
        lift_efficiency=lift_efficiency,
    )
    calibration.require("isothermal_airlift", values)
    _positive(**values)
    if injection_depth_m > submerged_length_m or lift_efficiency > 1:
        raise ValueError(
            "require injection within submerged length and efficiency <= 1"
        )
    pressure_head = liquid_density_kg_m3 * gravity_m_s2 * injection_depth_m
    injection_pressure = outlet_pressure_abs_pa + pressure_head
    _positive(injection_pressure_abs_pa=injection_pressure)
    power = (
        outlet_pressure_abs_pa
        * gas_flow_at_outlet_m3_s
        * log1p(pressure_head / outlet_pressure_abs_pa)
    )
    flow = (
        lift_efficiency
        * power
        / (liquid_density_kg_m3 * gravity_m_s2 * lift_above_surface_m)
    )
    _positive(isothermal_gas_power_w=power, energy_limited_liquid_flow_m3_s=flow)
    return AirliftScreen(injection_pressure, power, flow)


@dataclass(frozen=True)
class SluggingScreen:
    """Local void-fraction indication; no severe-slugging or stability verdict."""

    void_fraction: float
    indication: str


def slugging_screen(
    *,
    superficial_gas_velocity_m_s: float,
    superficial_liquid_velocity_m_s: float,
    distribution_parameter: float,
    drift_velocity_m_s: float,
    bubble_slug_void_fraction: float,
    maximum_void_fraction: float,
    calibration: Calibration,
) -> SluggingScreen:
    """Local bubble/possible-slug screen from upward superficial speeds, S4 (6).

    alpha=jg/(C0*(jg+jl)+Vgj). C0, Vgj and BOTH void-fraction limits must
    be supplied from a calibration covering the geometry, fluid, pressure,
    temperature and velocities. No universal threshold is assumed. Both phase
    fluxes are positive; drift may be zero (the calibrated homogeneous limit).
    Refuses alpha outside (0, maximum], or maximum outside (transition, 1).
    Valid only for calibrated local steady vertical gas/liquid flow. Above the
    maximum it refuses classification: churn/annular transitions require a
    fuller map. Excludes solids, countercurrent flow and severe riser slugging.
    """
    values = dict(
        superficial_gas_velocity_m_s=superficial_gas_velocity_m_s,
        superficial_liquid_velocity_m_s=superficial_liquid_velocity_m_s,
        distribution_parameter=distribution_parameter,
        drift_velocity_m_s=drift_velocity_m_s,
        bubble_slug_void_fraction=bubble_slug_void_fraction,
        maximum_void_fraction=maximum_void_fraction,
    )
    calibration.require("vertical_drift_flux", values)
    _positive(**{k: v for k, v in values.items() if k != "drift_velocity_m_s"})
    if drift_velocity_m_s < 0:
        raise ValueError("drift velocity must be nonnegative")
    _fraction("bubble_slug_void_fraction", bubble_slug_void_fraction)
    _fraction("maximum_void_fraction", maximum_void_fraction)
    if maximum_void_fraction <= bubble_slug_void_fraction:
        raise ValueError("void fraction calibration limits are reversed")
    denominator = (
        distribution_parameter
        * (superficial_gas_velocity_m_s + superficial_liquid_velocity_m_s)
        + drift_velocity_m_s
    )
    _positive(drift_flux_denominator_m_s=denominator)
    alpha = superficial_gas_velocity_m_s / denominator
    _fraction("computed_void_fraction", alpha)
    if alpha > maximum_void_fraction:
        raise ValueError(
            "computed void fraction exceeds calibration; regime unresolved"
        )
    indication = (
        "slugging_possible"
        if alpha >= bubble_slug_void_fraction
        else "bubble_indicated"
    )
    return SluggingScreen(alpha, indication)
