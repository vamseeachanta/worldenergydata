# ABOUTME: Deterministic flow-assurance risk screening for the field-dev playbook.
# ABOUTME: Issue #642 (epic #567) — hydrate/wax/slugging/erosion screen of a concept.
"""Deterministic hydrate, wax, slugging and liquid-erosion screening.

Missing essential inputs return NOT_EVALUATED; invalid threshold configuration
raises ValueError. Incomplete assessments cannot report an overall LOW result.
Governing equations and conventions: docs/agent-pack.md section 3 (E1 / S1).
This screen does not calculate multiphase hydraulics or establish API compliance.
"""

from __future__ import annotations

import math
from typing import Optional

from worldenergydata.field_development.flow_assurance_types import (
    FlowAssuranceAssessment,
    FlowAssuranceRisk,
    FlowAssuranceThresholds,
    RiskSeverity,
)
from worldenergydata.field_development.models import FieldConcept

_BBL_TO_M3 = 0.158987
_SEC_PER_DAY = 86400.0
_IN_TO_M = 0.0254
_M_TO_FT = 3.280839895


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


# Seabed temperature model
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


def _unknown_fluid(concept: FieldConcept) -> bool:
    return concept.fluid_type is None and concept.gor_scf_stb is None


# Hydrate
def screen_hydrate_risk(
    concept: FieldConcept, th: FlowAssuranceThresholds
) -> FlowAssuranceRisk:
    """Screen gas-hydrate plugging risk (cold + pressure + gas + water)."""
    risk = FlowAssuranceRisk(hazard="hydrate", severity=RiskSeverity.LOW)
    if _unknown_fluid(concept):
        risk.severity = RiskSeverity.NOT_EVALUATED
        risk.note = "fluid_type and gor_scf_stb unknown — cannot screen hydrate risk"
        return risk
    seabed = seabed_temperature_c(concept.water_depth_m, th)
    if seabed is None:
        risk.severity = RiskSeverity.NOT_EVALUATED
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


# Wax / paraffin
def screen_wax_risk(
    concept: FieldConcept, th: FlowAssuranceThresholds
) -> FlowAssuranceRisk:
    """Screen wax (paraffin) deposition risk (fluid cooling below the WAT)."""
    risk = FlowAssuranceRisk(hazard="wax", severity=RiskSeverity.LOW)
    seabed = seabed_temperature_c(concept.water_depth_m, th)
    if seabed is None:
        risk.severity = RiskSeverity.NOT_EVALUATED
        risk.note = "water depth unknown — cannot estimate seabed temperature"
        return risk
    if concept.wax_appearance_temp_c is None:
        risk.severity = RiskSeverity.NOT_EVALUATED
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


# Slugging (multiphase hydraulics)
def screen_slugging_risk(
    concept: FieldConcept, th: FlowAssuranceThresholds
) -> FlowAssuranceRisk:
    """Screen multiphase slugging risk (gas+liquid, long line, low turndown)."""
    risk = FlowAssuranceRisk(hazard="slugging", severity=RiskSeverity.LOW)
    if _unknown_fluid(concept):
        risk.severity = RiskSeverity.NOT_EVALUATED
        risk.note = "fluid_type and gor_scf_stb unknown — cannot screen slugging risk"
        return risk

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


# Liquid velocity screening
def _bulk_velocity_fts(rate_bpd: float, diameter_in: float) -> Optional[float]:
    """Pack E1: Q/A for liquid bbl/day at line conditions (never gas boe/day)."""
    if (
        not math.isfinite(diameter_in)
        or diameter_in <= 0
        or not math.isfinite(rate_bpd)
        or rate_bpd < 0
    ):
        return None
    q_m3_s = rate_bpd * _BBL_TO_M3 / _SEC_PER_DAY
    area_m2 = math.pi / 4.0 * (diameter_in * _IN_TO_M) ** 2
    if area_m2 <= 0:
        return None
    return (q_m3_s / area_m2) * _M_TO_FT


def screen_erosion_risk(
    concept: FieldConcept, th: FlowAssuranceThresholds
) -> FlowAssuranceRisk:
    """Screen one liquid flowline against configured limits; pack E1 / S1."""
    risk = FlowAssuranceRisk(hazard="erosion", severity=RiskSeverity.NOT_EVALUATED)
    # Pack section 3, E1: Q/A needs operating volume for one bore, not field boe/d.
    if (
        concept.fluid_type is None
        or concept.fluid_type.value != "oil"
        or concept.gor_scf_stb != 0
    ):
        risk.note = (
            "liquid-only screen requires oil fluid_type and explicit zero gor_scf_stb; "
            "gas/multiphase service not evaluated"
        )
        return risk
    if concept.flowline_liquid_rate_bpd is None or concept.flowline_diameter_in is None:
        risk.note = "flowline_liquid_rate_bpd or flowline diameter unknown — cannot screen erosion"
        return risk

    velocity = _bulk_velocity_fts(
        concept.flowline_liquid_rate_bpd, concept.flowline_diameter_in
    )
    if velocity is None:
        risk.note = "invalid flowline geometry — cannot screen erosion"
        return risk
    risk.metrics["velocity_fts"] = round(velocity, 2)
    risk.metrics["erosional_velocity_fts"] = th.erosional_velocity_fts
    ratio = velocity / th.erosional_velocity_fts
    risk.metrics["velocity_ratio"] = round(ratio, 3)

    points = 0
    if ratio >= th.erosion_warn_ratio:
        points += 1
        risk.drivers.append(
            f"bulk velocity {velocity:.1f} ft/s approaches the "
            f"~{th.erosional_velocity_fts:g} ft/s configured screening limit"
        )
    if ratio >= th.erosion_high_ratio:
        points += 1
        risk.drivers.append("bulk velocity reaches the configured high screening ratio")
    if ratio >= th.erosion_critical_ratio:
        points += 1
        risk.drivers.append(
            "bulk velocity reaches the configured critical screening ratio"
        )
    if concept.sour:
        points += 1
        risk.drivers.append("sour service adds erosion-corrosion synergy")

    risk.severity = _severity_from_points(points)
    if points == 0:
        risk.note = (
            "liquid velocity below the configured screening warning ratio; "
            "no code-compliance finding"
        )
    else:
        risk.mitigations = [
            "increase flowline diameter to lower bulk velocity",
            "review materials and corrosion allowance for the service",
            "flow-rate management / choking to stay below the erosional limit",
            "erosion-corrosion monitoring (ER probes / sand detection)",
        ]
    return risk


# Top-level assessment
def assess_flow_assurance(
    concept: FieldConcept, thresholds: Optional[FlowAssuranceThresholds] = None
) -> FlowAssuranceAssessment:
    """Screen all four flow-assurance hazards for a concept.

    Args:
        concept: The field concept (input parameters; need not be complete).
        thresholds: Screening thresholds; defaults to :class:`FlowAssuranceThresholds`.

    Returns:
        A :class:`FlowAssuranceAssessment` with per-hazard risks, the overall
        maximum evaluated severity, and aggregated mitigations. An incomplete
        assessment with no elevated hazard returns NOT_EVALUATED. Never raises on
        missing inputs — unscreenable hazards return ``NOT_EVALUATED`` with an explanatory
        note.
    """
    th = thresholds or FlowAssuranceThresholds()
    hydrate = screen_hydrate_risk(concept, th)
    wax = screen_wax_risk(concept, th)
    slugging = screen_slugging_risk(concept, th)
    erosion = screen_erosion_risk(concept, th)

    risks = [hydrate, wax, slugging, erosion]
    overall = max((r.severity for r in risks), key=lambda s: s.rank)
    if overall == RiskSeverity.LOW and any(
        r.severity == RiskSeverity.NOT_EVALUATED for r in risks
    ):
        overall = RiskSeverity.NOT_EVALUATED
    mitigations = list(dict.fromkeys(m for r in risks for m in r.mitigations))
    return FlowAssuranceAssessment(
        hydrate=hydrate,
        wax=wax,
        slugging=slugging,
        erosion=erosion,
        overall_severity=overall,
        mitigations=mitigations,
    )
