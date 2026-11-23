# ABOUTME: Tests for the capability-showcase coverage roll-up.
# ABOUTME: Issue #567 — area grouping + per-area schematic-coverage counts.
"""Tests for ``worldenergydata.field_development.showcase``."""

from __future__ import annotations

from worldenergydata.field_development.enums import ConceptType
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.showcase import (
    REST_OF_WORLD,
    area_for_region,
    build_showcase_html,
    coverage_by_area,
    render_exemplar_card,
    total_coverage,
)


def test_area_for_region_maps_known_and_unknown():
    assert area_for_region("US") == "Gulf of Mexico"
    assert area_for_region("Brazil") == "Brazil"
    assert area_for_region("Norway") == "North Sea & NW Europe"
    assert area_for_region("Angola") == "West Africa"
    assert area_for_region("Australia") == "Asia-Pacific"
    assert area_for_region("Atlantis (made up)") == REST_OF_WORLD
    assert area_for_region(None) == REST_OF_WORLD


def test_coverage_counts_sum_back_to_input():
    sample = [
        FieldConcept(name="a", region="US", water_depth_m=1500.0),
        FieldConcept(name="b", region="US", concept_type=ConceptType.SPAR),
        FieldConcept(
            name="c",
            region="Brazil",
            water_depth_m=2000.0,
            concept_type=ConceptType.FPSO,
        ),
        FieldConcept(name="d", region="Narnia"),  # rest of world, no depth
    ]
    cov = coverage_by_area(sample)
    assert sum(a.total for a in cov) == len(sample)
    assert sum(a.with_depth for a in cov) == 2
    assert sum(a.with_concept for a in cov) == 2
    gom = next(a for a in cov if a.area == "Gulf of Mexico")
    assert gom.total == 2 and gom.with_depth == 1 and gom.with_concept == 1


def test_empty_areas_are_omitted():
    cov = coverage_by_area([FieldConcept(name="x", region="Brazil")])
    assert [a.area for a in cov] == ["Brazil"]


def test_render_exemplar_card_embeds_real_schematics():
    # A deepwater field renders a card with two inline SVG schematics and an
    # honest blind-pick badge (the engine pick made with the label stripped).
    f = FieldConcept(
        name="Demo Deepwater",
        region="US",
        water_depth_m=1500.0,
        concept_type=ConceptType.SPAR,
        num_wells=8,
    )
    card = render_exemplar_card(f, "a demo blurb")
    assert card.count("<svg") == 2  # block diagram + plan-view layout
    assert "Demo Deepwater" in card and "a demo blurb" in card
    # Badge text reflects whether the blind pick matched — one or the other.
    assert ("matches as-built" in card) or ("engine " in card)


def test_build_showcase_html_is_self_contained_with_synthetic_inputs():
    fields = [FieldConcept(name="Synthetic field", region="US", water_depth_m=1200)]
    html = build_showcase_html(
        [
            {
                "area": "Gulf of Mexico",
                "field_name": "Synthetic field",
                "blurb": "fixture",
            }
        ],
        fields,
    )
    assert html.startswith("<!doctype html>")
    assert "Synthetic field" in html and "<svg" in html
    assert "All areas" in html


def test_build_showcase_skips_unknown_exemplar_without_error():
    fields = [FieldConcept(name="Synthetic field", region="US")]
    html = build_showcase_html(
        [{"area": "Nowhere", "field_name": "Missing fixture", "blurb": "fixture"}],
        fields,
    )
    assert "Missing fixture" not in html
    assert "All areas" in html


def test_total_coverage_uses_only_supplied_rows():
    fields = [FieldConcept(name="Synthetic field", region="US", water_depth_m=1200)]
    total = total_coverage(fields)
    assert total.total == total.with_depth == 1
    assert total.with_concept == 0
