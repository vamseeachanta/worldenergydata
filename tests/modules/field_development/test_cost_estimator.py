# ABOUTME: Tests for the parametric per-concept CAPEX/OPEX estimator (issue #643).
# ABOUTME: Verifies reuse of FDAS economics + recommendation priors, not new factors.
"""Tests for ``worldenergydata.field_development.cost_estimator``.

The estimator layers a *per-concept* adjustment on top of the field-level,
depth-driven FDAS CAPEX (``integrations.estimate_economics``) and scales OPEX by
the FDAS fixed-OPEX assumption. Tests assert the documented behaviours from the
issue acceptance criteria: tieback cheaper than FPSO, measurable depth-fit and
long-tieback penalties, reserves-scaled OPEX, bounded factors, graceful degrade,
and ordered portfolios with costs rounded to 0.1 MM.
"""

from __future__ import annotations

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    PerConceptCostEstimate,
    capex_adjustment_for,
    estimate_field_cost_portfolio,
    estimate_per_concept_costs,
    opex_factor_for,
    recommend,
)
from worldenergydata.field_development.enums import TreeType
from worldenergydata.field_development.recommendation import (
    ScoredConcept,
    Thresholds,
)


def _scored(concept_type: ConceptType, tree: TreeType = TreeType.WET) -> ScoredConcept:
    return ScoredConcept(concept_type=concept_type, tree_type=tree)


# --------------------------------------------------------------------------- #
# capex_adjustment_for — bounds and the documented penalties
# --------------------------------------------------------------------------- #
def test_capex_adjustment_in_band_range():
    # Across every concept at a perfect depth fit and no tieback, the multiplier
    # stays inside the documented ~[0.8, 1.5] envelope.
    for ct in ConceptType:
        adj = capex_adjustment_for(ct, depth_fit=1.0)
        assert 0.8 <= adj <= 1.5


def test_capex_adjustment_orders_by_concept_prior():
    # Non-tautological: exercises the concept CAPEX-prior mapping (not the clamp).
    # A cheaper concept (subsea tieback, high capex prior) must price below a
    # costlier one (FPSO) at the same perfect depth fit, and both land strictly
    # inside the clamp envelope so the ordering is the logic, not the boundary.
    tieback = capex_adjustment_for(ConceptType.SUBSEA_TIEBACK, depth_fit=1.0)
    fpso = capex_adjustment_for(ConceptType.FPSO, depth_fit=1.0)
    assert tieback < fpso
    assert 0.8 < tieback < fpso < 1.5  # neither pinned to the clamp


def test_capex_clamp_actually_engages():
    # Drive the raw multiplier past the ceiling (worst depth fit + a very long
    # tieback) and confirm the clamp pulls it exactly to the boundary — so the
    # clamp itself is exercised, not merely restated by the in-band assertions.
    extreme = capex_adjustment_for(ConceptType.FPSO, depth_fit=0.0, tieback_km=400.0)
    assert extreme == 1.5  # _CAPEX_ADJ_MAX


def test_depth_misfit_raises_capex_adjustment():
    # A poor depth fit must add a measurable CAPEX penalty.
    good = capex_adjustment_for(ConceptType.FPSO, depth_fit=1.0)
    bad = capex_adjustment_for(ConceptType.FPSO, depth_fit=0.0)
    assert bad > good


def test_tieback_beyond_threshold_is_penalised():
    warn = Thresholds().flow_assurance_warn_km
    near = capex_adjustment_for(ConceptType.SUBSEA_TIEBACK, tieback_km=warn)
    far = capex_adjustment_for(ConceptType.SUBSEA_TIEBACK, tieback_km=warn + 40)
    assert far > near


def test_tieback_within_threshold_no_penalty():
    warn = Thresholds().flow_assurance_warn_km
    base = capex_adjustment_for(ConceptType.SUBSEA_TIEBACK)
    within = capex_adjustment_for(ConceptType.SUBSEA_TIEBACK, tieback_km=warn - 5)
    assert within == base


# --------------------------------------------------------------------------- #
# opex_factor_for — reserves scaling and bounds
# --------------------------------------------------------------------------- #
def test_opex_factor_scales_with_reserves():
    small = opex_factor_for(ConceptType.FPSO, reserves_mmboe=25.0)
    large = opex_factor_for(ConceptType.FPSO, reserves_mmboe=400.0)
    assert large > small


def test_opex_factor_in_range():
    for ct in ConceptType:
        for res in (None, 10.0, 100.0, 1000.0):
            assert 0.5 <= opex_factor_for(ct, reserves_mmboe=res) <= 2.0


def test_opex_factor_orders_by_concept_prior():
    # Non-tautological: a concept with a stronger OPEX prior (fixed jacket, 0.80)
    # must carry a lower OPEX factor than a costlier one (FPSO, 0.55) at the same
    # reserves — exercises the concept mapping, not the clamp.
    jacket = opex_factor_for(ConceptType.FIXED_JACKET, reserves_mmboe=150.0)
    fpso = opex_factor_for(ConceptType.FPSO, reserves_mmboe=150.0)
    assert jacket < fpso
    assert 0.5 < jacket < fpso < 2.0  # neither pinned to the clamp


# --------------------------------------------------------------------------- #
# estimate_per_concept_costs — structure, relative CAPEX, rounding
# --------------------------------------------------------------------------- #
def test_per_concept_returns_populated_struct():
    c = FieldConcept(name="X", water_depth_m=1500.0, num_wells=6)
    est = estimate_per_concept_costs(c, _scored(ConceptType.FPSO))
    assert isinstance(est, PerConceptCostEstimate)
    assert est.concept_type == ConceptType.FPSO
    assert est.capex_mm is not None and est.capex_mm > 0
    assert est.annual_opex_mm is not None and est.annual_opex_mm > 0
    assert 0.8 <= est.capex_adjustment <= 1.5
    assert 0.5 <= est.opex_factor <= 2.0
    assert est.rationale


def test_subsea_tieback_cheaper_than_fpso_same_depth():
    # Same field/depth; the tieback's favourable CAPEX prior should make it
    # 5–15% cheaper than a dedicated FPSO host (issue acceptance).
    c = FieldConcept(
        name="X",
        water_depth_m=1500.0,
        num_wells=6,
        distance_to_host_km=15.0,
        host_spare_capacity=True,
    )
    tb = estimate_per_concept_costs(c, _scored(ConceptType.SUBSEA_TIEBACK))
    fpso = estimate_per_concept_costs(c, _scored(ConceptType.FPSO))
    assert tb.capex_mm < fpso.capex_mm
    ratio = tb.capex_mm / fpso.capex_mm
    assert 0.85 <= ratio <= 0.95


def test_opex_scales_with_reserves_in_estimate():
    base = dict(name="X", water_depth_m=1500.0, num_wells=6)
    small = estimate_per_concept_costs(
        FieldConcept(recoverable_reserves_mmboe=25.0, **base),
        _scored(ConceptType.FPSO),
    )
    large = estimate_per_concept_costs(
        FieldConcept(recoverable_reserves_mmboe=400.0, **base),
        _scored(ConceptType.FPSO),
    )
    assert large.annual_opex_mm > small.annual_opex_mm


def test_long_tieback_records_penalty():
    c = FieldConcept(
        name="X",
        water_depth_m=1500.0,
        num_wells=4,
        distance_to_host_km=80.0,
        host_spare_capacity=True,
    )
    est = estimate_per_concept_costs(c, _scored(ConceptType.SUBSEA_TIEBACK))
    assert est.tieback_penalty_pct > 0


def test_costs_rounded_to_point_one():
    c = FieldConcept(name="X", water_depth_m=1500.0, num_wells=7)
    est = estimate_per_concept_costs(c, _scored(ConceptType.FPSO))
    assert est.capex_mm == round(est.capex_mm, 1)
    assert est.annual_opex_mm == round(est.annual_opex_mm, 1)


# --------------------------------------------------------------------------- #
# Graceful degradation
# --------------------------------------------------------------------------- #
def test_graceful_degrade_unknown_depth():
    # No water depth → FDAS cannot classify a dev system → no CAPEX, but the
    # estimator must return a noted struct rather than raise.
    est = estimate_per_concept_costs(FieldConcept(name="X"), _scored(ConceptType.FPSO))
    assert est.capex_mm is None
    assert est.annual_opex_mm is None
    assert est.note


# --------------------------------------------------------------------------- #
# Portfolio
# --------------------------------------------------------------------------- #
def test_portfolio_keys_match_concepts_and_ordered():
    c = FieldConcept(
        name="X",
        water_depth_m=1500.0,
        num_wells=6,
        recoverable_reserves_mmboe=120.0,
        distance_to_host_km=20.0,
        host_spare_capacity=True,
    )
    ranked = recommend(c)
    portfolio = estimate_field_cost_portfolio(c, ranked)
    assert set(portfolio.keys()) == {sc.concept_type for sc in ranked}
    # Ordered by ascending lifecycle cost (CAPEX + OPEX×life; None last).
    life = c.field_life_years or 20.0

    def lifecycle(e):
        if e.capex_mm is None:
            return float("inf")
        return e.capex_mm + (e.annual_opex_mm or 0.0) * life

    costs = [lifecycle(e) for e in portfolio.values()]
    assert costs == sorted(costs)


# --------------------------------------------------------------------------- #
# Optional report wiring
# --------------------------------------------------------------------------- #
def test_fdp_report_includes_cost_comparison():
    from worldenergydata.field_development import build_fdp_html

    html = build_fdp_html(FieldConcept(name="X", water_depth_m=1500.0, num_wells=6))
    assert "Per-concept cost comparison" in html
    # Existing render is intact.
    assert "<!doctype html>" in html and "Architecture" in html
