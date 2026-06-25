# ABOUTME: Tests for the concept recommendation engine (issue #570).
# ABOUTME: Exercises the briefing archetypes + determinism + config overrides.
"""Tests for ``worldenergydata.field_development.recommendation``."""

from __future__ import annotations

from worldenergydata.field_development import (
    ConceptType,
    CriteriaWeights,
    FieldConcept,
    ScoredConcept,
    Thresholds,
    TreeType,
    feasible_concepts,
    recommend,
)
from worldenergydata.field_development.enums import (
    MetoceanRegime,
    ReservoirDistribution,
    Topology,
)


# --------------------------------------------------------------------------- #
# Feasibility (water-depth envelope)
# --------------------------------------------------------------------------- #
def test_feasible_concepts_shallow_includes_jacket_not_spar():
    c = FieldConcept(name="Shallow", water_depth_m=80.0)
    feasible = feasible_concepts(c, Thresholds())
    assert ConceptType.FIXED_JACKET in feasible
    assert ConceptType.SPAR not in feasible


def test_feasible_concepts_ultradeep_includes_spar_not_jacket():
    c = FieldConcept(name="UltraDeep", water_depth_m=2400.0)
    feasible = feasible_concepts(c, Thresholds())
    assert ConceptType.SPAR in feasible
    assert ConceptType.FIXED_JACKET not in feasible


def test_unknown_depth_keeps_all_concepts_feasible():
    feasible = feasible_concepts(FieldConcept(name="X"), Thresholds())
    assert ConceptType.FPSO in feasible and ConceptType.FIXED_JACKET in feasible


# --------------------------------------------------------------------------- #
# Archetypes from the briefing (§A6)
# --------------------------------------------------------------------------- #
def test_marginal_near_host_field_recommends_tieback():
    c = FieldConcept(
        name="Marginal-Near",
        water_depth_m=1400.0,
        recoverable_reserves_mmboe=20.0,
        distance_to_host_km=18.0,
        host_spare_capacity=True,
        num_wells=3,
    )
    ranked = recommend(c)
    assert ranked[0].concept_type == ConceptType.SUBSEA_TIEBACK
    assert any("spare capacity" in r for r in ranked[0].rationale)


def test_large_ultradeep_far_field_prefers_standalone_over_tieback():
    c = FieldConcept(
        name="Big-Deep",
        water_depth_m=2500.0,
        recoverable_reserves_mmboe=600.0,
        distance_to_host_km=140.0,   # far
        host_spare_capacity=False,
        num_wells=20,
    )
    ranked = recommend(c)
    top = ranked[0].concept_type
    assert top != ConceptType.SUBSEA_TIEBACK
    assert top in {ConceptType.SEMISUB_FPS, ConceptType.FPSO, ConceptType.SPAR}


def test_shallow_high_well_count_recommends_jacket():
    c = FieldConcept(
        name="Shelf",
        water_depth_m=90.0,
        recoverable_reserves_mmboe=300.0,
        num_wells=24,
        reservoir_distribution=ReservoirDistribution.COMPACT_STACKED,
    )
    ranked = recommend(c)
    assert ranked[0].concept_type == ConceptType.FIXED_JACKET


# --------------------------------------------------------------------------- #
# Output contract
# --------------------------------------------------------------------------- #
def test_scores_are_bounded_and_total_present():
    ranked = recommend(FieldConcept(name="X", water_depth_m=1200.0))
    assert ranked, "expected at least one feasible concept"
    for sc in ranked:
        assert isinstance(sc, ScoredConcept)
        assert 0.0 <= sc.total_score <= 1.0
        assert set(sc.scores) == {"capex", "opex", "schedule", "recovery",
                                  "flexibility", "risk", "depth_fit"}
        assert all(0.0 <= v <= 1.0 for v in sc.scores.values())


def test_ranked_descending_by_total_score():
    ranked = recommend(FieldConcept(name="X", water_depth_m=1200.0))
    totals = [s.total_score for s in ranked]
    assert totals == sorted(totals, reverse=True)


def test_top_n_limits_results():
    ranked = recommend(FieldConcept(name="X", water_depth_m=1200.0), top_n=2)
    assert len(ranked) == 2


def test_dry_tree_concepts_get_dry_tree_and_no_topology():
    ranked = recommend(FieldConcept(name="X", water_depth_m=2000.0))
    spar = next(s for s in ranked if s.concept_type == ConceptType.SPAR)
    assert spar.tree_type == TreeType.DRY
    assert spar.topology is None


def test_subsea_concepts_get_wet_tree_and_topology():
    c = FieldConcept(name="X", water_depth_m=2000.0, num_wells=8)
    ranked = recommend(c)
    fps = next(s for s in ranked if s.concept_type == ConceptType.SEMISUB_FPS)
    assert fps.tree_type == TreeType.WET
    assert fps.topology == Topology.CLUSTER  # >3 wells


# --------------------------------------------------------------------------- #
# Flow-assurance + metocean overlays surface as warnings
# --------------------------------------------------------------------------- #
def test_long_tieback_warns_on_flow_assurance():
    c = FieldConcept(
        name="Long-TB",
        water_depth_m=1000.0,
        distance_to_host_km=120.0,
        host_spare_capacity=True,
        recoverable_reserves_mmboe=30.0,
    )
    ranked = recommend(c)
    tb = next(s for s in ranked if s.concept_type == ConceptType.SUBSEA_TIEBACK)
    assert any("flow-assurance" in w for w in tb.warnings)


def test_hurricane_penalises_fpso():
    base = FieldConcept(name="GoM", water_depth_m=1500.0)
    storm = FieldConcept(name="GoM", water_depth_m=1500.0,
                         metocean_regime=MetoceanRegime.HURRICANE_CYCLONE)
    fpso_calm = next(s for s in recommend(base)
                     if s.concept_type == ConceptType.FPSO)
    fpso_storm = next(s for s in recommend(storm)
                      if s.concept_type == ConceptType.FPSO)
    assert fpso_storm.scores["risk"] < fpso_calm.scores["risk"]
    assert any("disconnectable turret" in w for w in fpso_storm.warnings)


# --------------------------------------------------------------------------- #
# Determinism + config-as-data
# --------------------------------------------------------------------------- #
def test_deterministic_same_input_same_ranking():
    c = FieldConcept(name="X", water_depth_m=1300.0, num_wells=10,
                     distance_to_host_km=25.0, host_spare_capacity=True)
    r1 = recommend(c)
    r2 = recommend(c)
    assert [s.concept_type for s in r1] == [s.concept_type for s in r2]
    assert [s.total_score for s in r1] == [s.total_score for s in r2]


def test_weights_are_config_not_magic_numbers():
    # Crank CAPEX weight to the exclusion of all else -> cheapest concept wins.
    c = FieldConcept(name="X", water_depth_m=1300.0,
                     distance_to_host_km=15.0, host_spare_capacity=True,
                     recoverable_reserves_mmboe=10.0)
    capex_only = CriteriaWeights(capex=1.0, opex=0.0, schedule=0.0,
                                 recovery=0.0, flexibility=0.0, risk=0.0)
    ranked = recommend(c, weights=capex_only)
    # Subsea tieback has the highest capex sub-score (0.95).
    assert ranked[0].concept_type == ConceptType.SUBSEA_TIEBACK


def test_thresholds_override_changes_tieback_attractiveness():
    c = FieldConcept(name="X", water_depth_m=1200.0, distance_to_host_km=50.0,
                     host_spare_capacity=True, recoverable_reserves_mmboe=30.0)
    # Default tieback_max_km=60 -> 50 km is attractive (no "not attractive" warn).
    tb_default = next(s for s in recommend(c)
                      if s.concept_type == ConceptType.SUBSEA_TIEBACK)
    assert not any("not clearly attractive" in w for w in tb_default.warnings)
    # Tighten the threshold below 50 km -> now flagged as not clearly attractive.
    tight = Thresholds(tieback_max_km=40.0)
    tb_tight = next(s for s in recommend(c, thresholds=tight)
                    if s.concept_type == ConceptType.SUBSEA_TIEBACK)
    assert any("not clearly attractive" in w for w in tb_tight.warnings)
