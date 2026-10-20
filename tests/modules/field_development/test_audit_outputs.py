"""Executable numeric and output gates for audit sections 1, 5–7 and 9."""

import math
from xml.etree import ElementTree as ET

import pytest
from pydantic import ValidationError

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    FluidType,
    fdp_report,
)
from worldenergydata.field_development.flow_assurance import (
    FlowAssuranceThresholds,
    _bulk_velocity_fts,
    screen_erosion_risk,
    seabed_temperature_c,
)
from worldenergydata.field_development.layout import compute_positions, render_layout


def liquid_concept(**changes):
    values = dict(
        name="Synthetic",
        fluid_type=FluidType.OIL,
        gor_scf_stb=0,
        flowline_liquid_rate_bpd=20000,
        flowline_diameter_in=8,
    )
    return FieldConcept(**(values | changes))


def test_numeric_temperature_and_liquid_velocity():
    assert seabed_temperature_c(1000, FlowAssuranceThresholds()) == 4.0
    # Pack E1: (20000*.158987/86400)/(pi/4*(8*.0254)**2)*3.280839895.
    assert _bulk_velocity_fts(20000, 8) == pytest.approx(3.723, abs=0.001)


def test_per_line_liquid_rate_independent_of_field_boe():
    first = screen_erosion_risk(
        liquid_concept(plateau_rate_boed=20000), FlowAssuranceThresholds()
    )
    second = screen_erosion_risk(
        liquid_concept(plateau_rate_boed=400000), FlowAssuranceThresholds()
    )
    assert first == second
    assert first.metrics["velocity_fts"] == 3.72
    assert first.severity.value == "low"
    assert "screening" in first.note


def test_no_per_line_rate_is_not_evaluated():
    result = screen_erosion_risk(
        liquid_concept(flowline_liquid_rate_bpd=None), FlowAssuranceThresholds()
    )
    assert result.severity.value == "not_evaluated"
    assert "flowline_liquid_rate_bpd" in result.note


@pytest.mark.parametrize("gor", [None, 1, 2999, 3000])
def test_unproven_liquid_service_is_not_evaluated(gor):
    result = screen_erosion_risk(
        liquid_concept(gor_scf_stb=gor), FlowAssuranceThresholds()
    )
    assert result.severity.value == "not_evaluated"


@pytest.mark.parametrize("value", [-1, math.inf, math.nan])
def test_per_line_rate_requires_finite_nonnegative_volume(value):
    with pytest.raises(ValidationError):
        liquid_concept(flowline_liquid_rate_bpd=value)


@pytest.mark.parametrize("value", [0, -1, math.inf, math.nan])
def test_invalid_erosion_threshold_raises(value):
    with pytest.raises(ValueError, match="erosional_velocity_fts"):
        screen_erosion_risk(
            FieldConcept(name="Synthetic"),
            FlowAssuranceThresholds(erosional_velocity_fts=value),
        )


def test_erosion_ratios_are_configurable():
    c = liquid_concept()
    result = screen_erosion_risk(
        c,
        FlowAssuranceThresholds(
            erosion_warn_ratio=0.1, erosion_high_ratio=0.2, erosion_critical_ratio=0.3
        ),
    )
    assert result.severity.value == "critical"
    assert all("RP 14" not in driver for driver in result.drivers)


@pytest.mark.parametrize("ratios", [(0, 1, 2), (1, 1, 2), (2, 1, 3), (1, 2, math.inf)])
def test_invalid_tier_ratios_rejected(ratios):
    with pytest.raises(ValueError, match="ratio"):
        FlowAssuranceThresholds(
            erosion_warn_ratio=ratios[0],
            erosion_high_ratio=ratios[1],
            erosion_critical_ratio=ratios[2],
        )


@pytest.mark.parametrize(
    "tieback,host,expected", [(None, 12, 12), (5, 12, 5), (0, 12, 0), (None, 0, 0)]
)
def test_layout_host_offset_precedence(tieback, host, expected):
    c = FieldConcept(
        name="Synthetic",
        concept_type=ConceptType.SUBSEA_TIEBACK,
        tieback_distance_km=tieback,
        distance_to_host_km=host,
    )
    assert compute_positions(c)["host"].y_km == expected


def test_default_layout_and_report_disclose_schematic_offset():
    c = FieldConcept(name="Synthetic", concept_type=ConceptType.SUBSEA_TIEBACK)
    svg = render_layout(c)
    assert "schematic" in svg.lower() and "1.5 km" in svg
    html = fdp_report.build_fdp_html(c)
    assert "Plan-view field layout (schematic" in html
    assert "Plan-view field layout (to scale)" not in html


def test_report_embeds_renderer_outputs_by_identity(monkeypatch):
    monkeypatch.setattr(
        fdp_report, "render_block_diagram", lambda c: '<svg id="block-output"/>'
    )
    monkeypatch.setattr(
        fdp_report, "render_layout", lambda c: '<svg id="layout-output"/>'
    )
    html = fdp_report.build_fdp_html(FieldConcept(name="Synthetic"))
    assert '<svg id="block-output"/>' in html
    assert '<svg id="layout-output"/>' in html


def test_layout_svg_is_parsed_and_contains_geometry():
    root = ET.fromstring(render_layout(FieldConcept(name="Synthetic")))
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert len(list(root)) > 2
