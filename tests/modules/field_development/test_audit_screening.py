"""Regression criteria for audit sections 1–3 (synthetic inputs only)."""

import pytest

from worldenergydata.field_development import FieldConcept, FluidType
from worldenergydata.field_development.flow_assurance import (
    FlowAssuranceThresholds,
    assess_flow_assurance,
    screen_erosion_risk,
    screen_hydrate_risk,
    screen_slugging_risk,
)
from worldenergydata.field_development.integrations import estimate_economics


@pytest.mark.parametrize(
    "fluid", [FluidType.GAS, FluidType.GAS_CONDENSATE, FluidType.CONDENSATE]
)
def test_gas_erosion_is_not_evaluated(fluid):
    concept = FieldConcept(
        name="Synthetic",
        fluid_type=fluid,
        plateau_rate_boed=20000,
        flowline_diameter_in=8,
    )
    risk = screen_erosion_risk(concept, FlowAssuranceThresholds())
    assert risk.severity.value == "not_evaluated"
    assert "liquid" in risk.note
    assert "velocity_fts" not in risk.metrics


def test_high_gor_erosion_is_not_evaluated():
    concept = FieldConcept(
        name="Synthetic",
        fluid_type=FluidType.OIL,
        gor_scf_stb=3000,
        plateau_rate_boed=20000,
        flowline_diameter_in=8,
    )
    assert (
        screen_erosion_risk(concept, FlowAssuranceThresholds()).severity.value
        == "not_evaluated"
    )


@pytest.mark.parametrize("screen", [screen_hydrate_risk, screen_slugging_risk])
def test_unknown_fluid_is_not_evaluated(screen):
    risk = screen(
        FieldConcept(name="Synthetic", water_depth_m=1000), FlowAssuranceThresholds()
    )
    assert risk.severity.value == "not_evaluated"
    assert "fluid_type" in risk.note and "gor_scf_stb" in risk.note


def test_empty_assessment_cannot_report_low():
    result = assess_flow_assurance(FieldConcept(name="Synthetic"))
    assert result.overall_severity.value == "not_evaluated"
    assert all(r.severity.value == "not_evaluated" for r in result.risks)


def test_shallow_economics_rejects_zero_capex_basis():
    pytest.importorskip("worldenergydata.fdas.core.config")
    concept = FieldConcept(
        name="Synthetic",
        water_depth_m=100,
        num_wells=6,
        plateau_rate_boed=60000,
        oil_price_usd_bbl=70,
        field_life_years=15,
    )
    result = estimate_economics(concept)
    assert result.dev_system == "dry"
    assert result.capex_mm is None and result.npv_mm is None
    assert "CAPEX" in result.note and "zero" in result.note
