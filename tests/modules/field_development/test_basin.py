# ABOUTME: Tests for the sourced basin → concept-family affinity prior.
# ABOUTME: Issue #567 calibration v2 — regional development-culture scoring.
"""Tests for ``worldenergydata.field_development.basin``.

The basin prior encodes documented regional development practice (Brazil/West
Africa = FPSO, GoM = moored floaters + subsea with FPSO suppressed, North Sea =
fixed + FPSO). These tests pin those *qualitative* relationships, not exact
weights — the affinities are domain knowledge, so the test asserts the ordering
practice implies, which is what protects the calibration gain from drift.
"""

from __future__ import annotations

from worldenergydata.field_development.basin import (
    NEUTRAL,
    region_fit,
    region_to_basin,
)
from worldenergydata.field_development.enums import ConceptType


def test_region_maps_to_basin_archetype():
    assert region_to_basin("Brazil") == "brazil"
    assert region_to_basin("US") == "gom"
    assert region_to_basin("Angola") == "w_africa"
    assert region_to_basin("UK") == "north_sea"


def test_unknown_region_is_neutral_not_penalized():
    # An unmapped or missing region must never penalize any concept.
    assert region_to_basin("Atlantis") is None
    assert region_to_basin(None) is None
    for concept in ConceptType:
        assert region_fit(concept, "Atlantis") == NEUTRAL
        assert region_fit(concept, None) == NEUTRAL


def test_brazil_favours_fpso_over_fixed_and_spar():
    assert region_fit(ConceptType.FPSO, "Brazil") > region_fit(
        ConceptType.FIXED_JACKET, "Brazil"
    )
    assert region_fit(ConceptType.FPSO, "Brazil") > region_fit(
        ConceptType.SPAR, "Brazil"
    )


def test_gom_suppresses_fpso_and_favours_moored_floaters():
    # The historical GoM signature: spar/semisub/TLP, FPSO rare.
    assert region_fit(ConceptType.SPAR, "US") > region_fit(ConceptType.FPSO, "US")
    assert region_fit(ConceptType.SEMISUB_FPS, "US") > region_fit(
        ConceptType.FPSO, "US"
    )


def test_west_africa_and_north_sea_favour_fpso():
    assert region_fit(ConceptType.FPSO, "Angola") >= 0.9
    assert region_fit(ConceptType.FPSO, "UK") >= 0.9


def test_region_lookup_is_case_and_whitespace_insensitive():
    assert region_to_basin("  brazil ") == "brazil"
    assert region_to_basin("nORWAY") == "north_sea"
