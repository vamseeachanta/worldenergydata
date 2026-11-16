# ABOUTME: Tests for the SubseaIQ og_host enrichment layer (calibration v2).
# ABOUTME: Issue #567 — host registry load + tieback/host input enrichment.
"""Tests for ``worldenergydata.field_development.host_enrichment``.

The enrichment layer turns the curated SubseaIQ host registry into *input*
features for the recommendation engine: a known subsea-tieback satellite gains a
distance-to-host and a reachable host; a host field gains its real reserves and
well count. It must **never** set ``concept_type`` (that would leak the answer
into a calibration that scores concept prediction).
"""

from __future__ import annotations

from worldenergydata.field_development.enums import ConceptType
from worldenergydata.field_development.host_enrichment import (
    GOM_TYPICAL_TIEBACK_KM,
    HostRecord,
    enrich_concepts,
    load_host_registry,
    match_host,
    match_tieback,
)
from worldenergydata.field_development.models import FieldConcept


def _registry() -> list[HostRecord]:
    """A tiny synthetic registry: one spar host with two tieback satellites."""
    return [
        HostRecord(
            host_name="SYNTHETIC ALPHA",
            host_concept=ConceptType.SPAR,
            general_location="GOM",
            block_raw="GC 901, 902",
            bsee_block_key="GC901",
            water_depth_m=1234.0,
            reserves_mmboe=300.0,
            total_wells=15,
            dry_tree_wells=15,
            wet_tree_wells=0,
            throughput_mboed=135.0,
            tieback_fields=["Synthetic Alpha (15)"],  # self-reference, must be dropped
        ),
        HostRecord(
            host_name="SYNTHETIC BETA",
            host_concept=ConceptType.SPAR,
            general_location="GOM",
            block_raw="AC 903",
            bsee_block_key="AC903",
            water_depth_m=2345.0,
            reserves_mmboe=None,
            total_wells=35,
            dry_tree_wells=0,
            wet_tree_wells=35,
            throughput_mboed=133.0,
            tieback_fields=["Synthetic Satellite (30)", "Synthetic Minor (1)"],
        ),
    ]


# --------------------------------------------------------------------------- #
# Registry parsing helpers
# --------------------------------------------------------------------------- #
def test_match_tieback_resolves_satellite_to_host_and_wells():
    link = match_tieback("Synthetic Satellite", _registry())
    assert link is not None
    assert link.host_name == "SYNTHETIC BETA"
    assert link.wells == 30


def test_self_referential_tieback_is_dropped():
    # SYNTHETIC ALPHA lists "Synthetic Alpha (15)" as its own tieback — not a real satellite.
    assert match_tieback("Synthetic Alpha", _registry()) is None


def test_match_host_prefix_matches_field_to_vessel_name():
    rec = match_host("Synthetic Beta", _registry())
    assert rec is not None and rec.host_concept == ConceptType.SPAR


def test_match_host_requires_minimum_specificity():
    # A 2-char field name must not spuriously prefix-match a host vessel name.
    assert match_host("AC", _registry()) is None


# --------------------------------------------------------------------------- #
# Enrichment semantics
# --------------------------------------------------------------------------- #
def test_tieback_satellite_gains_distance_and_reachable_host():
    fields = [FieldConcept(name="Synthetic Satellite", water_depth_m=2500.0)]
    out = enrich_concepts(fields, registry=_registry())
    gw = out[0]
    assert gw.distance_to_host_km == GOM_TYPICAL_TIEBACK_KM
    assert gw.host_spare_capacity is True
    assert gw.num_wells == 30
    assert gw.concept_type is None  # never leak the answer


def test_host_field_gains_reserves_and_wells_but_no_distance():
    fields = [FieldConcept(name="Synthetic Beta", water_depth_m=2345.0)]
    out = enrich_concepts(fields, registry=_registry())
    p = out[0]
    assert p.num_wells == 35
    # A host field is standalone — no tieback distance is invented for it.
    assert p.distance_to_host_km is None
    assert p.concept_type is None


def test_enrichment_never_overwrites_existing_inputs():
    fields = [
        FieldConcept(
            name="Synthetic Satellite",
            water_depth_m=2500.0,
            num_wells=7,
            distance_to_host_km=99.0,
        )
    ]
    out = enrich_concepts(fields, registry=_registry())
    assert out[0].num_wells == 7  # real input preserved
    assert out[0].distance_to_host_km == 99.0


def test_host_branch_never_overwrites_existing_inputs():
    # The host-match branch (not the tieback branch) has its own None-guards on
    # reserves and well count — exercise them with a host field that already
    # carries real values. "Synthetic Alpha" matches the host SYNTHETIC ALPHA (reserves 300,
    # wells 15 in the registry); the pre-set values must survive.
    fields = [
        FieldConcept(
            name="Synthetic Alpha",
            water_depth_m=1234.0,
            recoverable_reserves_mmboe=42.0,
            num_wells=9,
        )
    ]
    out = enrich_concepts(fields, registry=_registry())
    assert out[0].recoverable_reserves_mmboe == 42.0  # real input preserved
    assert out[0].num_wells == 9


def test_unknown_field_is_returned_unchanged():
    fields = [FieldConcept(name="Nowhere", water_depth_m=1000.0)]
    out = enrich_concepts(fields, registry=_registry())
    assert out[0].distance_to_host_km is None
    assert out[0].num_wells is None


# --------------------------------------------------------------------------- #
# The withheld default registry
# --------------------------------------------------------------------------- #
def test_default_registry_is_withheld():
    import pytest

    with pytest.raises(RuntimeError, match="redistribution-terms review"):
        load_host_registry()


def test_default_enrichment_cannot_silently_skip_withheld_registry():
    import pytest

    with pytest.raises(RuntimeError, match="redistribution-terms review"):
        enrich_concepts([FieldConcept(name="Synthetic satellite", water_depth_m=1200)])
