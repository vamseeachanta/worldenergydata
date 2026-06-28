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
from worldenergydata.field_development.subseaiq import load_subseaiq_fields


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


def test_build_showcase_html_is_self_contained_with_coverage():
    fields = load_subseaiq_fields(enrich_facilities=True)
    exemplars = [
        {"area": "Gulf of Mexico", "field_name": "Thunder Horse", "blurb": "demo"}
    ]
    html = build_showcase_html(exemplars, fields)
    assert html.startswith("<!doctype html>")
    assert "Thunder Horse" in html  # exemplar resolved + rendered
    assert "<svg" in html  # real schematic embedded
    assert "Gulf of Mexico" in html and "All areas" in html  # coverage table
    assert "https://" not in html.replace("http-equiv", "")  # no external assets


def test_build_showcase_skips_unknown_exemplar_without_error():
    fields = load_subseaiq_fields(enrich_facilities=True)
    html = build_showcase_html(
        [{"area": "Nowhere", "field_name": "Not A Real Field", "blurb": "x"}], fields
    )
    assert "Not A Real Field" not in html  # gracefully skipped
    assert "All areas" in html  # coverage still renders


def test_real_catalog_coverage_matches_known_totals():
    fields = load_subseaiq_fields(enrich_facilities=True)
    total = total_coverage(fields)
    assert total.total == len(fields) > 2000
    # The whole catalog is schematizable; most carry a depth.
    assert total.with_depth > 1500
    cov = {a.area: a for a in coverage_by_area(fields)}
    # Gulf of Mexico is the US OCS catalog (US_GOM_FLAG core = 333 fields).
    assert cov["Gulf of Mexico"].total == 333
    # Per-area totals reconcile to the grand total.
    assert sum(a.total for a in cov.values()) == total.total
