# ABOUTME: Deterministic flow-assurance risk screening for the field-dev playbook.
# ABOUTME: Issue #642 (epic #567) — hydrate/wax/slugging/erosion screen of a concept.
"""
worldenergydata.field_development.flow_assurance
================================================

Given a :class:`~worldenergydata.field_development.models.FieldConcept`, screen the
four classic subsea production-chemistry / hydraulics hazards and return a
structured :class:`FlowAssuranceAssessment`:

* **Hydrate** — gas hydrates plug cold, high-pressure flowlines. Driven by low
  seabed temperature (deep water), free/associated gas, and long tieback offsets
  that let the fluid cool into the hydrate-stability region.
* **Wax (paraffin)** — wax deposits once the fluid cools below its Wax Appearance
  Temperature (WAT, aka cloud point). Driven by ``wax_appearance_temp_c`` sitting
  above the seabed temperature; worse for long, cold offsets and heavier crudes.
* **Slugging** — unstable multiphase (gas+liquid) flow; severe/terrain slugging in
  long flowlines and risers, worst at low turndown rates and high GOR.
* **Erosional velocity** — sand-free erosion when the bulk fluid velocity exceeds
  the API RP 14E / RP 14J erosional-velocity limit (~12 ft/s for continuous-
  service carbon steel, C = 100). Worst for high rates through small-bore lines,
  high GOR (low mixture density raises velocity), and sour (erosion-corrosion).

Design notes
------------
This is a **screening tool**, not a transient multiphase simulator (OLGA / LedaFlow)
or a PVT package (PVTsim / Multiflash). It returns a *direction and a severity tier*
to flag which hazards warrant detailed study and which mitigations to scope — it does
not size insulation, predict plug locations, or compute steady-state hydraulics.

All thresholds live in :class:`FlowAssuranceThresholds` (a frozen dataclass that
mirrors :class:`recommendation.Thresholds`) so regional/operator signatures are
*data, not code branches*, and every call is overridable. Screening is fully
deterministic: identical inputs yield identical assessments. Every screen degrades
gracefully — missing :class:`FieldConcept` fields yield a ``LOW``/neutral result
with an explanatory ``note`` and never raise.

References (rules of thumb, public domain):
* API RP 14E / API RP 14J — erosional velocity. At screening fidelity we apply a
  fixed limiting velocity (:attr:`FlowAssuranceThresholds.erosional_velocity_fts`,
  default 12 ft/s for carbon steel, the ``C=100`` continuous-service value) rather
  than computing ``Ve = C / sqrt(rho_mixture)`` — there is no mixture-density model
  at this fidelity, so the limit is set directly and overridable per call.
* NORSOK / general deepwater practice — ~4 C seabed thermal floor below the
  thermocline; hydrate-stability envelope for natural gas at deepwater pressures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from worldenergydata.field_development.models import FieldConcept

# --- Unit conversions ---
_BBL_TO_M3 = 0.158987
_SEC_PER_DAY = 86400.0
_IN_TO_M = 0.0254
_M_TO_FT = 3.280839895


class RiskSeverity(str, Enum):
    """Ordered flow-assurance severity tier (serializes to a plain string)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        """Integer ordinal for comparison/aggregation (LOW=0 … CRITICAL=3)."""
        return _SEVERITY_RANK[self]


_SEVERITY_RANK: dict[RiskSeverity, int] = {
    RiskSeverity.LOW: 0,
    RiskSeverity.MEDIUM: 1,
    RiskSeverity.HIGH: 2,
    RiskSeverity.CRITICAL: 3,
}

# Map an accumulated driver-point count to a severity tier. Each independent
# physical driver (e.g. "seabed below the hydrate temperature", "long offset")
# contributes one point; the tiers keep the mapping transparent and auditable.
_POINTS_TO_SEVERITY = (
    RiskSeverity.LOW,  # 0 drivers
    RiskSeverity.MEDIUM,  # 1
    RiskSeverity.HIGH,  # 2
)  # >=3 -> CRITICAL


def _severity_from_points(points: int) -> RiskSeverity:
    """Deterministic points -> tier (0=LOW, 1=MEDIUM, 2=HIGH, >=3=CRITICAL)."""
    if points >= len(_POINTS_TO_SEVERITY):
        return RiskSeverity.CRITICAL
    return _POINTS_TO_SEVERITY[max(points, 0)]


@dataclass(frozen=True)
class FlowAssuranceThresholds:
    """Screening thresholds, sourced to documented offshore practice.

    Overridable per call so regional signatures / fluid systems are data, not code.
    """

    # Seabed temperature envelope (deepwater thermocline -> ~4 C floor).
    seabed_temp_surface_c: float = 22.0  # near-surface seabed/intake temp
    seabed_temp_gradient_c_per_m: float = 0.018  # falls to floor by ~1000 m
    seabed_temp_floor_c: float = 4.0  # abyssal thermal floor

    # Hydrate: natural-gas hydrate-stability temperature at deepwater pressure.
    hydrate_formation_temp_c: float = 21.0  # below this (+ gas + water) -> hydrates
    hydrate_deep_subcool_c: float = 10.0  # deep subcooling escalates risk
    hydrate_gor_scf_stb: float = 2000.0  # above this, oil is gassy enough to matter
    hydrate_long_offset_km: float = 30.0  # long offset -> more cooldown

    # Wax / paraffin.
    wax_margin_warn_c: float = 10.0  # WAT this far above seabed -> escalate
    wax_heavy_api: float = 25.0  # heavier crudes deposit more readily
    wax_long_offset_km: float = 30.0

    # Slugging (multiphase hydraulics).
    slugging_gor_scf_stb: float = 1000.0  # enough free gas for two-phase flow
    slugging_long_km: float = 15.0  # long flowline -> terrain/severe slugging
    slugging_low_rate_boed: float = 20000.0  # low turndown -> unstable flow

    # Erosional velocity (API RP 14E / RP 14J). The limit is set directly (the
    # C=100 carbon-steel continuous-service value already baked into 12 ft/s); we
    # do not compute Ve = C/sqrt(rho) — no mixture-density model at this fidelity.
    erosional_velocity_fts: float = 12.0  # carbon steel, continuous service (C=100)
    erosion_high_gor_scf_stb: float = 3000.0  # high GOR -> lower mixture density


@dataclass
class FlowAssuranceRisk:
    """One screened hazard: tier + the drivers that set it + scoped mitigations."""

    hazard: str
    severity: RiskSeverity
    drivers: list[str] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)
    note: str = ""
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class FlowAssuranceAssessment:
    """Full per-hazard screen of a concept plus an aggregated view."""

    hydrate: FlowAssuranceRisk
    wax: FlowAssuranceRisk
    slugging: FlowAssuranceRisk
    erosion: FlowAssuranceRisk
    overall_severity: RiskSeverity
    mitigations: list[str] = field(default_factory=list)

    @property
    def risks(self) -> list[FlowAssuranceRisk]:
        """The four hazard risks in a fixed, deterministic order."""
        return [self.hydrate, self.wax, self.slugging, self.erosion]


# --------------------------------------------------------------------------- #
# Seabed temperature model
# --------------------------------------------------------------------------- #
def seabed_temperature_c(
    water_depth_m: Optional[float], th: FlowAssuranceThresholds
) -> Optional[float]:
    """Estimate seabed temperature (C) from water depth.

    Simple, monotonic envelope: temperature falls linearly from a near-surface
    value through the thermocline to a ~4 C abyssal floor (reached by ~1000 m in
    the default calibration). Screening-grade — real profiles vary by basin and
    season — but captures the dominant control on hydrate/wax risk: deep water is
    cold. Returns ``None`` when depth is unknown.
    """
    if water_depth_m is None:
        return None
    temp = th.seabed_temp_surface_c - th.seabed_temp_gradient_c_per_m * water_depth_m
    return max(th.seabed_temp_floor_c, temp)


def _is_gassy(concept: FieldConcept, gor_cutoff: float) -> bool:
    """True if the fluid carries enough gas to drive gas-phase hazards."""
    ft = concept.fluid_type.value if concept.fluid_type is not None else None
    if ft in ("gas", "gas_condensate", "condensate"):
        return True
    return concept.gor_scf_stb is not None and concept.gor_scf_stb >= gor_cutoff


# --------------------------------------------------------------------------- #
# Hydrate
# --------------------------------------------------------------------------- #
def screen_hydrate_risk(
    concept: FieldConcept, th: FlowAssuranceThresholds
) -> FlowAssuranceRisk:
    """Screen gas-hydrate plugging risk (cold + pressure + gas + water)."""
    risk = FlowAssuranceRisk(hazard="hydrate", severity=RiskSeverity.LOW)
    seabed = seabed_temperature_c(concept.water_depth_m, th)
    if seabed is None:
        risk.note = "water depth unknown — cannot estimate seabed temperature"
        return risk
    risk.metrics["seabed_temp_c"] = round(seabed, 2)

    # Hydrates need free gas + water; dead oil with little gas is low-risk.
    if not _is_gassy(concept, th.hydrate_gor_scf_stb):
        risk.note = "fluid not gas-bearing — hydrate risk minimal"
        return risk

    subcooling = th.hydrate_formation_temp_c - seabed
    risk.metrics["subcooling_c"] = round(subcooling, 2)
    points = 0
    if subcooling > 0:
        points += 1
        risk.drivers.append(
            f"seabed {seabed:.1f} C is below the ~{th.hydrate_formation_temp_c:.0f} C "
            "hydrate-stability temperature"
        )
    if subcooling >= th.hydrate_deep_subcool_c:
        points += 1
        risk.drivers.append(f"deep subcooling ({subcooling:.1f} C) into hydrate region")
    # Secondary drivers escalate only when the fluid actually cools into the
    # hydrate-stability region (subcooling > 0). Below the curve no hydrate can
    # form, so a long offset or sour gas must not raise the tier on their own —
    # mirrors the ``margin > 0`` gating in :func:`screen_wax_risk`.
    if subcooling > 0:
        if (
            concept.distance_to_host_km is not None
            and concept.distance_to_host_km >= th.hydrate_long_offset_km
        ):
            points += 1
            risk.drivers.append(
                f"long offset ({concept.distance_to_host_km:g} km) prolongs cooldown"
            )
        if concept.sour:
            points += 1
            risk.drivers.append(
                "sour (CO2/H2S) shifts the hydrate curve / adds chemistry"
            )

    risk.severity = _severity_from_points(points)
    if points == 0:
        risk.note = "gas present but conditions outside the hydrate-stability region"
    else:
        risk.mitigations = [
            "thermal insulation (wet insulation / pipe-in-pipe) for cooldown time",
            "active heating (electrically-trace-heated or DEH flowline)",
            "inhibitor injection (MEG/methanol thermodynamic or LDHI)",
            "multiphase boosting to manage backpressure and arrival temperature",
        ]
    return risk


# --------------------------------------------------------------------------- #
# Wax / paraffin
# --------------------------------------------------------------------------- #
def screen_wax_risk(
    concept: FieldConcept, th: FlowAssuranceThresholds
) -> FlowAssuranceRisk:
    """Screen wax (paraffin) deposition risk (fluid cooling below the WAT)."""
    risk = FlowAssuranceRisk(hazard="wax", severity=RiskSeverity.LOW)
    seabed = seabed_temperature_c(concept.water_depth_m, th)
    if seabed is None:
        risk.note = "water depth unknown — cannot estimate seabed temperature"
        return risk
    if concept.wax_appearance_temp_c is None:
        risk.note = "wax appearance temperature unknown — cannot screen wax risk"
        return risk
    risk.metrics["seabed_temp_c"] = round(seabed, 2)

    margin = concept.wax_appearance_temp_c - seabed  # >0 => fluid cools into WAT region
    risk.metrics["wat_margin_c"] = round(margin, 2)
    points = 0
    if margin > 0:
        points += 1
        risk.drivers.append(
            f"seabed {seabed:.1f} C is below the WAT "
            f"({concept.wax_appearance_temp_c:g} C) — fluid cools into deposition"
        )
    if margin >= th.wax_margin_warn_c:
        points += 1
        risk.drivers.append(
            f"large WAT margin ({margin:.1f} C) over seabed temperature"
        )
    if (
        concept.api_gravity is not None
        and concept.api_gravity < th.wax_heavy_api
        and margin > 0
    ):
        points += 1
        risk.drivers.append(
            f"heavier crude ({concept.api_gravity:g} API) deposits more readily"
        )
    if (
        concept.distance_to_host_km is not None
        and concept.distance_to_host_km >= th.wax_long_offset_km
        and margin > 0
    ):
        points += 1
        risk.drivers.append(
            f"long offset ({concept.distance_to_host_km:g} km) gives more cool-down "
            "for deposition"
        )

    risk.severity = _severity_from_points(points)
    if points == 0:
        risk.note = "WAT at or below seabed temperature — wax deposition unlikely"
    else:
        risk.mitigations = [
            "thermal insulation to keep arrival temperature above the WAT",
            "active heating (electrically-trace-heated flowline)",
            "wax inhibitor / pour-point-depressant injection",
            "routine pigging program to remove deposited wax",
        ]
    return risk


# --------------------------------------------------------------------------- #
# Slugging (multiphase hydraulics)
# --------------------------------------------------------------------------- #
def screen_slugging_risk(
    concept: FieldConcept, th: FlowAssuranceThresholds
) -> FlowAssuranceRisk:
    """Screen multiphase slugging risk (gas+liquid, long line, low turndown)."""
    risk = FlowAssuranceRisk(hazard="slugging", severity=RiskSeverity.LOW)

    # Slugging needs two-phase (gas+liquid) flow; near-single-phase is stable.
    if not _is_gassy(concept, th.slugging_gor_scf_stb):
        risk.note = "near single-phase flow — slugging unlikely"
        return risk

    points = 0
    if (
        concept.gor_scf_stb is not None
        and concept.gor_scf_stb >= th.slugging_gor_scf_stb
    ):
        points += 1
        risk.drivers.append(
            f"high GOR ({concept.gor_scf_stb:g} scf/stb) gives strong gas-liquid "
            "interaction"
        )
    elif concept.gor_scf_stb is None:
        # Gassy by fluid type but GOR unknown — still a multiphase candidate.
        risk.drivers.append("gas-bearing fluid — two-phase flow expected")
        points += 1
    if (
        concept.distance_to_host_km is not None
        and concept.distance_to_host_km >= th.slugging_long_km
    ):
        points += 1
        risk.drivers.append(
            f"long flowline ({concept.distance_to_host_km:g} km) promotes "
            "terrain/severe slugging"
        )
    if (
        concept.plateau_rate_boed is not None
        and concept.plateau_rate_boed < th.slugging_low_rate_boed
    ):
        points += 1
        risk.drivers.append(
            f"low throughput ({concept.plateau_rate_boed:g} boed) -> unstable, "
            "slug-prone flow"
        )

    risk.severity = _severity_from_points(points)
    if points == 0:
        risk.note = "gas present but geometry/rate not conducive to slugging"
    else:
        risk.mitigations = [
            "multiphase boosting to stabilise flow and lift liquids",
            "topside slug catcher sized for the expected slug volume",
            "active choke / topside slug-control",
            "gas-lift or a pigging-loop topology for liquids management",
        ]
    return risk


# --------------------------------------------------------------------------- #
# Erosional velocity (API RP 14E / RP 14J)
# --------------------------------------------------------------------------- #
def _bulk_velocity_fts(rate_boed: float, diameter_in: float) -> Optional[float]:
    """Bulk fluid velocity (ft/s) from volumetric rate through a circular bore."""
    if diameter_in <= 0:
        return None
    q_m3_s = rate_boed * _BBL_TO_M3 / _SEC_PER_DAY
    area_m2 = math.pi / 4.0 * (diameter_in * _IN_TO_M) ** 2
    if area_m2 <= 0:
        return None
    return (q_m3_s / area_m2) * _M_TO_FT


def screen_erosion_risk(
    concept: FieldConcept, th: FlowAssuranceThresholds
) -> FlowAssuranceRisk:
    """Screen erosional-velocity risk vs the API RP 14E/14J limit."""
    risk = FlowAssuranceRisk(hazard="erosion", severity=RiskSeverity.LOW)
    if concept.plateau_rate_boed is None or concept.flowline_diameter_in is None:
        risk.note = "plateau rate or flowline diameter unknown — cannot screen erosion"
        return risk

    velocity = _bulk_velocity_fts(
        concept.plateau_rate_boed, concept.flowline_diameter_in
    )
    if velocity is None:
        risk.note = "invalid flowline geometry — cannot screen erosion"
        return risk
    risk.metrics["velocity_fts"] = round(velocity, 2)
    risk.metrics["erosional_velocity_fts"] = th.erosional_velocity_fts
    ratio = velocity / th.erosional_velocity_fts if th.erosional_velocity_fts else 0.0
    risk.metrics["velocity_ratio"] = round(ratio, 3)

    points = 0
    if ratio >= 0.7:
        points += 1
        risk.drivers.append(
            f"bulk velocity {velocity:.1f} ft/s approaches the "
            f"~{th.erosional_velocity_fts:g} ft/s erosional limit (API RP 14J)"
        )
    if ratio >= 1.0:
        points += 1
        risk.drivers.append("bulk velocity exceeds the erosional-velocity limit")
    if ratio >= 1.5:
        points += 1
        risk.drivers.append("velocity well above the limit — severe erosion expected")
    if (
        concept.gor_scf_stb is not None
        and concept.gor_scf_stb >= th.erosion_high_gor_scf_stb
    ):
        points += 1
        risk.drivers.append(
            f"high GOR ({concept.gor_scf_stb:g} scf/stb) lowers mixture density / "
            "raises actual velocity"
        )
    if concept.sour:
        points += 1
        risk.drivers.append("sour service adds erosion-corrosion synergy")

    risk.severity = _severity_from_points(points)
    if points == 0:
        risk.note = "bulk velocity comfortably below the erosional-velocity limit"
    else:
        risk.mitigations = [
            "increase flowline diameter to lower bulk velocity",
            "corrosion-resistant alloy / higher API RP 14E C-factor material",
            "flow-rate management / choking to stay below the erosional limit",
            "erosion-corrosion monitoring (ER probes / sand detection)",
        ]
    return risk


# --------------------------------------------------------------------------- #
# Top-level assessment
# --------------------------------------------------------------------------- #
def _dedup(items: list[str]) -> list[str]:
    """Order-preserving de-duplication."""
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def assess_flow_assurance(
    concept: FieldConcept, thresholds: Optional[FlowAssuranceThresholds] = None
) -> FlowAssuranceAssessment:
    """Screen all four flow-assurance hazards for a concept.

    Args:
        concept: The field concept (input parameters; need not be complete).
        thresholds: Screening thresholds; defaults to :class:`FlowAssuranceThresholds`.

    Returns:
        A :class:`FlowAssuranceAssessment` with per-hazard risks, the overall
        (max) severity, and de-duplicated aggregated mitigations. Never raises on
        missing inputs — unscreenable hazards return ``LOW`` with an explanatory
        note.
    """
    th = thresholds or FlowAssuranceThresholds()
    hydrate = screen_hydrate_risk(concept, th)
    wax = screen_wax_risk(concept, th)
    slugging = screen_slugging_risk(concept, th)
    erosion = screen_erosion_risk(concept, th)

    risks = [hydrate, wax, slugging, erosion]
    overall = max((r.severity for r in risks), key=lambda s: s.rank)
    mitigations = _dedup([m for r in risks for m in r.mitigations])
    return FlowAssuranceAssessment(
        hydrate=hydrate,
        wax=wax,
        slugging=slugging,
        erosion=erosion,
        overall_severity=overall,
        mitigations=mitigations,
    )
