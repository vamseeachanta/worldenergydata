# ABOUTME: Tests for the deterministic flow-assurance screening module (issue #642).
# ABOUTME: Per-hazard unit cases + integration + graceful degradation + determinism.
"""Tests for ``worldenergydata.field_development.flow_assurance``.

The module is *screening-grade* (not OLGA/PVTsim simulation), so assertions check
the direction of the heuristics (cold deepwater gas → hydrate risk; flow above the
API RP 14J erosional velocity → erosion risk) and the contract (never raises on
missing inputs, deterministic, threshold-overridable) rather than precise values.
"""

from __future__ import annotations

from worldenergydata.field_development import (
    FieldConcept,
    FluidType,
)
from worldenergydata.field_development.flow_assurance import (
    FlowAssuranceAssessment,
    FlowAssuranceRisk,
    FlowAssuranceThresholds,
    RiskSeverity,
    assess_flow_assurance,
    screen_erosion_risk,
    screen_hydrate_risk,
    screen_slugging_risk,
    screen_wax_risk,
    seabed_temperature_c,
)

TH = FlowAssuranceThresholds()


# --------------------------------------------------------------------------- #
# Seabed temperature model
# --------------------------------------------------------------------------- #
def test_seabed_temperature_floors_in_deep_water():
    # Deep water (>~1000 m) sits near the ~4 C thermal floor.
    assert seabed_temperature_c(1500.0, TH) == TH.seabed_temp_floor_c
    assert seabed_temperature_c(2500.0, TH) == TH.seabed_temp_floor_c


def test_seabed_temperature_warmer_in_shallow_water():
    shallow = seabed_temperature_c(50.0, TH)
    deep = seabed_temperature_c(900.0, TH)
    assert shallow > deep > TH.seabed_temp_floor_c


# --------------------------------------------------------------------------- #
# Hydrate
# --------------------------------------------------------------------------- #
def test_hydrate_high_for_cold_deepwater_gas():
    c = FieldConcept(
        name="ColdGas",
        water_depth_m=2000.0,
        fluid_type=FluidType.GAS,
        gor_scf_stb=5000.0,
        distance_to_host_km=40.0,
    )
    risk = screen_hydrate_risk(c, TH)
    assert risk.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
    assert any("inhibitor" in m for m in risk.mitigations)


def test_hydrate_low_for_warm_shallow_dead_oil():
    c = FieldConcept(
        name="WarmOil",
        water_depth_m=60.0,
        fluid_type=FluidType.OIL,
        gor_scf_stb=50.0,
    )
    risk = screen_hydrate_risk(c, TH)
    assert risk.severity == RiskSeverity.LOW


def test_hydrate_unknown_depth_is_low_and_noted():
    risk = screen_hydrate_risk(FieldConcept(name="X"), TH)
    assert risk.severity == RiskSeverity.LOW
    assert risk.note


# --------------------------------------------------------------------------- #
# Wax
# --------------------------------------------------------------------------- #
def test_wax_high_when_seabed_below_wat():
    c = FieldConcept(
        name="Waxy",
        water_depth_m=1800.0,  # seabed ~4 C
        fluid_type=FluidType.OIL,
        wax_appearance_temp_c=35.0,  # well above seabed temp
        distance_to_host_km=30.0,
    )
    risk = screen_wax_risk(c, TH)
    assert risk.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
    assert any("insulation" in m for m in risk.mitigations)


def test_wax_low_when_wat_below_seabed():
    c = FieldConcept(
        name="NoWax",
        water_depth_m=40.0,  # warm, shallow
        wax_appearance_temp_c=5.0,
    )
    risk = screen_wax_risk(c, TH)
    assert risk.severity == RiskSeverity.LOW


def test_wax_unknown_wat_is_low_and_noted():
    risk = screen_wax_risk(FieldConcept(name="X", water_depth_m=1500.0), TH)
    assert risk.severity == RiskSeverity.LOW
    assert risk.note


# --------------------------------------------------------------------------- #
# Slugging
# --------------------------------------------------------------------------- #
def test_slugging_high_for_long_gassy_low_rate_line():
    c = FieldConcept(
        name="Slugger",
        fluid_type=FluidType.GAS_CONDENSATE,
        gor_scf_stb=4000.0,
        distance_to_host_km=45.0,
        plateau_rate_boed=8000.0,
    )
    risk = screen_slugging_risk(c, TH)
    assert risk.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
    assert any("boosting" in m for m in risk.mitigations)


def test_slugging_low_for_short_oil_line():
    c = FieldConcept(
        name="Stable",
        fluid_type=FluidType.OIL,
        gor_scf_stb=100.0,
        distance_to_host_km=2.0,
        plateau_rate_boed=60000.0,
    )
    risk = screen_slugging_risk(c, TH)
    assert risk.severity == RiskSeverity.LOW


# --------------------------------------------------------------------------- #
# Erosion (API RP 14J / 14E erosional velocity)
# --------------------------------------------------------------------------- #
def test_erosion_high_for_high_rate_small_bore():
    c = FieldConcept(
        name="Erosive",
        plateau_rate_boed=400000.0,  # very high
        flowline_diameter_in=6.0,  # small bore
        gor_scf_stb=6000.0,
        sour=True,
    )
    risk = screen_erosion_risk(c, TH)
    assert risk.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
    assert risk.metrics.get("velocity_fts", 0.0) > TH.erosional_velocity_fts


def test_erosion_low_for_modest_rate_large_bore():
    c = FieldConcept(
        name="Gentle",
        plateau_rate_boed=20000.0,
        flowline_diameter_in=16.0,
        gor_scf_stb=200.0,
    )
    risk = screen_erosion_risk(c, TH)
    assert risk.severity == RiskSeverity.LOW


def test_erosion_unknown_inputs_low_and_noted():
    risk = screen_erosion_risk(FieldConcept(name="X"), TH)
    assert risk.severity == RiskSeverity.LOW
    assert risk.note


# --------------------------------------------------------------------------- #
# Integration / assessment
# --------------------------------------------------------------------------- #
def test_assess_returns_all_hazards_and_overall():
    c = FieldConcept(
        name="DeepGas",
        water_depth_m=2000.0,
        fluid_type=FluidType.GAS_CONDENSATE,
        gor_scf_stb=6000.0,
        wax_appearance_temp_c=30.0,
        distance_to_host_km=50.0,
        plateau_rate_boed=120000.0,
        flowline_diameter_in=8.0,
    )
    a = assess_flow_assurance(c)
    assert isinstance(a, FlowAssuranceAssessment)
    assert all(isinstance(r, FlowAssuranceRisk) for r in a.risks)
    assert len(a.risks) == 4
    # Overall is the max severity over the hazards.
    assert a.overall_severity == max(
        (r.severity for r in a.risks), key=lambda s: s.rank
    )
    # Aggregated mitigations are de-duplicated and non-empty for a risky field.
    assert a.mitigations and len(a.mitigations) == len(set(a.mitigations))


def test_assess_empty_concept_never_raises_all_low():
    a = assess_flow_assurance(FieldConcept(name="Bare"))
    assert isinstance(a, FlowAssuranceAssessment)
    assert a.overall_severity == RiskSeverity.LOW
    assert all(r.severity == RiskSeverity.LOW for r in a.risks)


def test_assessment_is_deterministic():
    c = FieldConcept(
        name="Repeat",
        water_depth_m=1500.0,
        fluid_type=FluidType.GAS,
        gor_scf_stb=3000.0,
        wax_appearance_temp_c=25.0,
        plateau_rate_boed=80000.0,
        flowline_diameter_in=10.0,
        distance_to_host_km=35.0,
    )
    a1 = assess_flow_assurance(c)
    a2 = assess_flow_assurance(c)
    assert a1 == a2


def test_threshold_override_changes_outcome():
    c = FieldConcept(
        name="Borderline",
        plateau_rate_boed=60000.0,
        flowline_diameter_in=10.0,
    )
    strict = FlowAssuranceThresholds(erosional_velocity_fts=1.0)  # trip easily
    lax = FlowAssuranceThresholds(erosional_velocity_fts=1000.0)  # never trips
    strict_risk = screen_erosion_risk(c, strict)
    lax_risk = screen_erosion_risk(c, lax)
    assert strict_risk.severity.rank > lax_risk.severity.rank


def test_severity_rank_ordering():
    assert (
        RiskSeverity.LOW.rank
        < RiskSeverity.MEDIUM.rank
        < RiskSeverity.HIGH.rank
        < RiskSeverity.CRITICAL.rank
    )
