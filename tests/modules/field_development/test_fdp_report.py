# ABOUTME: Tests for the field-development-plan HTML report generator.
# ABOUTME: Issue #567 — verifies the FDP composes engine + renderers + actuals.
"""Tests for ``worldenergydata.field_development.fdp_report``."""

from __future__ import annotations

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    FluidType,
    build_fdp_html,
)


def _julia():
    return FieldConcept(
        name="Julia",
        operator="ExxonMobil",
        water_depth_m=2160.0,
        fluid_type=FluidType.OIL,
        num_wells=5,
        num_manifolds=2,
        concept_type=ConceptType.SUBSEA_TIEBACK,
        tieback_distance_km=30.0,
        distance_to_host_km=30.0,
        host_spare_capacity=True,
    )


def test_returns_standalone_html():
    html = build_fdp_html(_julia())
    assert html.startswith("<!doctype html>")
    assert "</html>" in html
    assert "Julia" in html


def test_contains_all_sections():
    html = build_fdp_html(_julia())
    for section in (
        "Field parameters",
        "Recommended concept shortlist",
        "Economics",
        "Architecture",
    ):
        assert section in html


def test_embeds_both_visualizations():
    html = build_fdp_html(_julia())
    # Two inline SVGs (block diagram + plan-view layout).
    assert html.count("<svg") >= 2
    assert "block diagram" in html and "layout" in html.lower()


def test_actuals_rendered_when_given():
    html = build_fdp_html(_julia(), actuals={"CAPEX (as built)": "$4,700 MM"})
    assert "As built" in html and "$4,700 MM" in html


def test_actual_concept_marked_in_shortlist():
    # The field's real concept should be flagged with a star in the table.
    html = build_fdp_html(_julia())
    assert "subsea_tieback ★" in html or "subsea_tieback ★".replace(" ", "") in html


def test_renders_without_concept_type_using_recommendation():
    # A concept with only inputs (no chosen concept) still renders an architecture.
    bare = FieldConcept(name="X", water_depth_m=2000.0, num_wells=3)
    html = build_fdp_html(bare)
    assert html.startswith("<!doctype html>")
    assert html.count("<svg") >= 2
