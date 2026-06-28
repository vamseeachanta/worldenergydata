# ABOUTME: Tests for the BSEE-matched FDP portfolio builder.
# ABOUTME: Issue #567 — crosswalk→FieldConcept mapping, probe integrity, match rate.
"""Tests for ``worldenergydata.field_development.portfolio_matched``.

Covers the pure mapping logic (crosswalk row → :class:`FieldConcept`), the
probe-stripping that keeps the recommendation engine blind to the answer, and the
top-1 match-rate aggregation — without rendering any HTML.
"""

from __future__ import annotations

from worldenergydata.field_development import ConceptType, FieldConcept
from worldenergydata.field_development.portfolio_matched import (
    CrosswalkMatch,
    PortfolioRow,
    build_portfolio,
    load_matched_crosswalk,
    probe_of,
    summarize,
    to_concept_from_crosswalk,
    top_recommendation,
)


def _match(name="Allegheny", concept=ConceptType.TLP):
    return CrosswalkMatch(
        og_field_name=name,
        block="Green Canyon 254",
        bsee_block_code="GC254",
        host_concept=concept,
        operator="ENI (NOC)",
    )


# --------------------------------------------------------------------------- #
# Crosswalk loading
# --------------------------------------------------------------------------- #
def test_load_matched_crosswalk_returns_only_matched_rows():
    rows = load_matched_crosswalk()
    # 115 rows carry matched==1 (CSV-parsed; some ``block`` cells embed commas,
    # so a naive field split under-counts).
    assert len(rows) == 115
    assert all(isinstance(r, CrosswalkMatch) for r in rows)
    # 75 carry a host_concept (the as-built ground truth).
    assert sum(r.host_concept is not None for r in rows) == 75


def test_load_matched_crosswalk_parses_host_concept_to_enum():
    rows = {r.og_field_name: r for r in load_matched_crosswalk()}
    assert rows["Allegheny"].host_concept == ConceptType.TLP
    assert rows["Aconcagua"].host_concept == ConceptType.SUBSEA_TIEBACK
    # A matched row with no host_concept stays None (no ground truth).
    assert rows["Amethyst"].host_concept is None


# --------------------------------------------------------------------------- #
# Mapping: crosswalk row -> FieldConcept
# --------------------------------------------------------------------------- #
def test_to_concept_carries_actual_concept_and_inputs():
    base = FieldConcept(
        name="Allegheny",
        region="US",
        water_depth_m=989.0,
    )
    c = to_concept_from_crosswalk(_match(), base=base)
    assert c.name == "Allegheny"
    assert c.concept_type == ConceptType.TLP  # the actual/as-built concept
    assert c.operator == "ENI (NOC)"
    assert c.region == "US"
    assert c.water_depth_m == 989.0


def test_to_concept_without_base_has_no_depth():
    c = to_concept_from_crosswalk(_match(), base=None)
    assert c.water_depth_m is None
    assert c.concept_type == ConceptType.TLP


def test_to_concept_no_host_concept_is_none():
    c = to_concept_from_crosswalk(_match(concept=None), base=None)
    assert c.concept_type is None


# --------------------------------------------------------------------------- #
# Probe integrity — the engine must not see the answer
# --------------------------------------------------------------------------- #
def test_probe_strips_concept_type_and_operator():
    c = FieldConcept(
        name="x",
        water_depth_m=1500.0,
        concept_type=ConceptType.SPAR,
        operator="Acme",
    )
    p = probe_of(c)
    assert p.concept_type is None
    assert p.operator is None
    # Inputs the engine is allowed to see survive.
    assert p.water_depth_m == 1500.0


def test_recommendation_is_blind_to_the_actual_concept():
    # Same inputs, different (or absent) actual concept must yield the same pick:
    # proves the engine never reads concept_type.
    base = dict(name="x", region="US", water_depth_m=1500.0)
    as_spar = FieldConcept(concept_type=ConceptType.SPAR, **base)
    as_fpso = FieldConcept(concept_type=ConceptType.FPSO, **base)
    as_none = FieldConcept(**base)
    assert (
        top_recommendation(as_spar)
        == top_recommendation(as_fpso)
        == top_recommendation(as_none)
    )


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #
def test_summarize_match_rate_counts_only_known_actuals():
    rows = [
        # actual == recommended -> match
        PortfolioRow(
            concept=FieldConcept(name="a", concept_type=ConceptType.SPAR),
            match=_match("a", ConceptType.SPAR),
            recommended=ConceptType.SPAR,
        ),
        # actual != recommended -> miss
        PortfolioRow(
            concept=FieldConcept(name="b", concept_type=ConceptType.FPSO),
            match=_match("b", ConceptType.FPSO),
            recommended=ConceptType.SPAR,
        ),
        # no actual -> excluded from the denominator
        PortfolioRow(
            concept=FieldConcept(name="c"),
            match=_match("c", None),
            recommended=ConceptType.SPAR,
        ),
    ]
    s = summarize(rows)
    assert s["n_total"] == 3
    assert s["n_with_actual"] == 2
    assert s["n_matched"] == 1
    assert s["top1_match_rate"] == 0.5
    # per-field record shape
    rec = {r["name"]: r for r in s["fields"]}
    assert rec["a"]["actual"] == "spar" and rec["a"]["match"] is True
    assert rec["b"]["match"] is False
    assert rec["c"]["actual"] is None and rec["c"]["match"] is None


def test_portfolio_row_is_match_property():
    r = PortfolioRow(
        concept=FieldConcept(name="a", concept_type=ConceptType.SPAR),
        match=_match("a", ConceptType.SPAR),
        recommended=ConceptType.SPAR,
    )
    assert r.is_match is True
    r_none = PortfolioRow(
        concept=FieldConcept(name="a"),
        match=_match("a", None),
        recommended=ConceptType.SPAR,
    )
    assert r_none.is_match is None


# --------------------------------------------------------------------------- #
# End-to-end build over the real curated data
# --------------------------------------------------------------------------- #
def test_build_portfolio_over_real_data():
    rows = build_portfolio()
    assert len(rows) == 115
    # Every row keeps a recommendation (depth-less fields still rank all concepts).
    assert all(r.recommended is not None for r in rows)
    s = summarize(rows)
    # 75 fields carry a ground-truth concept (correct_satellite_labels may
    # relabel some to subsea_tieback, but never drops the count).
    assert s["n_with_actual"] == 75
    # The engine lands a non-trivial share of top-1 picks: 36/75 = 48% measured
    # on current main. Pin n_matched exactly so an engine change that shifts the
    # rate fails loudly instead of passing under a wide band. (GoM-only subset,
    # the engine's hardest — spar/semisub/TLP confusion — so below the global
    # ~55%; in-sample, see calibration-v2.md.)
    assert s["n_matched"] == 36
    assert s["top1_match_rate"] == 36 / 75
