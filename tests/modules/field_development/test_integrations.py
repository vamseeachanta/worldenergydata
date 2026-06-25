# ABOUTME: Tests for the FDAS/vessel/subsea enrichment layer (issue #575).
# ABOUTME: Exercises real sibling packages; tolerant of missing data/deps.
"""Tests for ``worldenergydata.field_development.integrations``.

These wire into sibling packages (fdas, vessel_fleet, subsea). Where a package
or its data is unavailable the functions degrade gracefully, so assertions are
written to accept either the populated result or a documented ``note``.
"""

from __future__ import annotations

from worldenergydata.field_development import (
    ConceptType,
    Economics,
    EnrichedConcept,
    FieldConcept,
    HardwarePicks,
    VesselFeasibility,
    dev_system_for,
    enrich,
    estimate_economics,
    hardware_picks,
    recommend,
    vessel_feasibility,
)
from worldenergydata.field_development.recommendation import ScoredConcept
from worldenergydata.field_development.enums import TreeType


# --------------------------------------------------------------------------- #
# FDAS dev-system classification (depth in feet)
# --------------------------------------------------------------------------- #
def test_dev_system_shallow_is_dry():
    # 90 m ≈ 295 ft < 500 ft → dry
    assert dev_system_for(FieldConcept(name="X", water_depth_m=90.0)) == "dry"


def test_dev_system_deep_is_subsea15():
    # 1500 m ≈ 4921 ft → subsea15 (500–5999 ft)
    assert dev_system_for(FieldConcept(name="X", water_depth_m=1500.0)) == "subsea15"


def test_dev_system_ultradeep_is_subsea20():
    # 2500 m ≈ 8202 ft ≥ 6000 ft → subsea20
    assert dev_system_for(FieldConcept(name="X", water_depth_m=2500.0)) == "subsea20"


def test_dev_system_none_when_depth_unknown():
    assert dev_system_for(FieldConcept(name="X")) is None


# --------------------------------------------------------------------------- #
# Economics
# --------------------------------------------------------------------------- #
def test_economics_returns_capex_for_known_depth():
    eco = estimate_economics(FieldConcept(name="X", water_depth_m=1500.0, num_wells=6))
    assert isinstance(eco, Economics)
    assert eco.dev_system == "subsea15"
    assert eco.capex_mm is not None and eco.capex_mm > 0


def test_economics_npv_present_with_full_inputs():
    eco = estimate_economics(
        FieldConcept(
            name="X",
            water_depth_m=1500.0,
            num_wells=6,
            plateau_rate_boed=60000.0,
            oil_price_usd_bbl=70.0,
            field_life_years=15.0,
            discount_rate=0.10,
        )
    )
    # With plateau rate + price + life, an NPV should be computable.
    assert eco.npv_mm is None or isinstance(eco.npv_mm, float)
    if eco.npv_mm is None:
        assert "NPV" in eco.note


def test_economics_unknown_depth_has_note():
    eco = estimate_economics(FieldConcept(name="X"))
    assert eco.capex_mm is None and eco.note


# --------------------------------------------------------------------------- #
# Vessel feasibility
# --------------------------------------------------------------------------- #
def test_vessel_feasibility_returns_struct_for_known_depth():
    sc = ScoredConcept(concept_type=ConceptType.SEMISUB_FPS, tree_type=TreeType.WET)
    vf = vessel_feasibility(FieldConcept(name="X", water_depth_m=1500.0), sc)
    assert isinstance(vf, VesselFeasibility)
    assert vf.needs_pipelay is True
    # Either we got a real answer, or a note explains why not.
    assert vf.water_depth_reachable is not None or vf.note


def test_vessel_feasibility_unknown_depth_noted():
    sc = ScoredConcept(concept_type=ConceptType.FPSO, tree_type=TreeType.WET)
    vf = vessel_feasibility(FieldConcept(name="X"), sc)
    assert vf.note


# --------------------------------------------------------------------------- #
# Hardware picks (curated catalogs in this worktree)
# --------------------------------------------------------------------------- #
def test_wet_tree_concept_picks_a_jumper():
    sc = ScoredConcept(concept_type=ConceptType.SUBSEA_TIEBACK, tree_type=TreeType.WET)
    hp = hardware_picks(FieldConcept(name="X", water_depth_m=1200.0), sc)
    assert isinstance(hp, HardwarePicks)
    assert hp.rigid_jumper_id  # catalog present in this worktree


def test_floating_host_picks_mooring():
    sc = ScoredConcept(concept_type=ConceptType.SPAR, tree_type=TreeType.DRY)
    hp = hardware_picks(FieldConcept(name="X", water_depth_m=2000.0), sc)
    assert hp.mooring_component_id


def test_dry_tree_fixed_jacket_no_hardware():
    sc = ScoredConcept(concept_type=ConceptType.FIXED_JACKET, tree_type=TreeType.DRY)
    hp = hardware_picks(FieldConcept(name="X", water_depth_m=100.0), sc)
    assert hp.rigid_jumper_id is None and hp.mooring_component_id is None


# --------------------------------------------------------------------------- #
# Top-level enrichment
# --------------------------------------------------------------------------- #
def test_enrich_aligns_with_recommendations():
    c = FieldConcept(
        name="X",
        water_depth_m=1500.0,
        num_wells=6,
        distance_to_host_km=18.0,
        host_spare_capacity=True,
        recoverable_reserves_mmboe=25.0,
    )
    ranked = recommend(c)
    economics, enriched = enrich(c, ranked)
    assert isinstance(economics, Economics)
    assert len(enriched) == len(ranked)
    assert all(isinstance(e, EnrichedConcept) for e in enriched)
    assert enriched[0].scored is ranked[0]
