# ABOUTME: Unit tests for the FieldConcept contract, sanity gate, and JSON schema.
# ABOUTME: Issue #568 (epic #567) — TDD coverage for the playbook's shared model.
"""Tests for ``worldenergydata.field_development``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    FluidType,
    SCHEMA_VERSION,
    TreeType,
    is_sane,
    load_concept,
    load_concept_json,
    sanity_check,
    validate_concept,
)
from worldenergydata.field_development.schema.export_schema import (
    SCHEMA_PATH,
    build_schema,
)


# --------------------------------------------------------------------------- #
# Construction & per-field validators
# --------------------------------------------------------------------------- #
def test_minimal_concept_requires_only_name():
    c = FieldConcept(name="Perdido")
    assert c.name == "Perdido"
    assert c.schema_version == SCHEMA_VERSION
    assert c.water_depth_m is None  # everything else optional


def test_rich_concept_constructs_and_keeps_enums():
    c = FieldConcept(
        name="Aasta Hansteen",
        operator="Equinor",
        region="Norwegian Sea",
        water_depth_m=1300.0,
        concept_type=ConceptType.SPAR,
        tree_type=TreeType.WET,
        fluid_type=FluidType.GAS,
        num_wells=12,
        num_trees=12,
        tieback_distance_km=0.0,
        discount_rate=0.10,
        api_gravity=45.0,
    )
    assert c.concept_type is ConceptType.SPAR
    assert c.fluid_type is FluidType.GAS


def test_name_is_required():
    with pytest.raises(ValidationError):
        FieldConcept()  # type: ignore[call-arg]


def test_blank_name_rejected():
    with pytest.raises(ValidationError):
        FieldConcept(name="   ")


def test_negative_water_depth_rejected():
    with pytest.raises(ValidationError):
        FieldConcept(name="X", water_depth_m=-5.0)


def test_api_gravity_out_of_range_rejected():
    with pytest.raises(ValidationError):
        FieldConcept(name="X", api_gravity=150.0)


def test_discount_rate_must_be_fraction():
    with pytest.raises(ValidationError):
        FieldConcept(name="X", discount_rate=10.0)  # 10 != 0.10


def test_unknown_field_forbidden():
    with pytest.raises(ValidationError):
        FieldConcept(name="X", bogus_attr=1)  # type: ignore[call-arg]


def test_negative_count_rejected():
    with pytest.raises(ValidationError):
        FieldConcept(name="X", num_wells=-1)


# --------------------------------------------------------------------------- #
# Sanity gate (cross-field — returns violations, never raises)
# --------------------------------------------------------------------------- #
def test_clean_concept_has_no_violations():
    c = FieldConcept(
        name="Whale",
        concept_type=ConceptType.SEMISUB_FPS,
        tree_type=TreeType.WET,
        water_depth_m=2600.0,
        num_wells=15,
        num_trees=15,
    )
    assert sanity_check(c) == []
    assert is_sane(c) is True


def test_wet_tree_well_count_must_equal_tree_count():
    c = FieldConcept(
        name="X",
        concept_type=ConceptType.SUBSEA_TIEBACK,
        num_wells=6,
        num_trees=4,
        tieback_distance_km=18.0,
    )
    codes = {v.code for v in sanity_check(c)}
    assert "wet_tree_well_tree_mismatch" in codes


def test_subsea_tieback_requires_positive_distance():
    c = FieldConcept(name="X", concept_type=ConceptType.SUBSEA_TIEBACK)
    codes = {v.code for v in sanity_check(c)}
    assert "tieback_missing_distance" in codes


def test_depth_outside_host_envelope_flagged():
    # Fixed jacket beyond ~450 m is outside its practical band.
    c = FieldConcept(
        name="X", concept_type=ConceptType.FIXED_JACKET, water_depth_m=1200.0
    )
    codes = {v.code for v in sanity_check(c)}
    assert "depth_outside_host_envelope" in codes


def test_depth_within_envelope_not_flagged():
    c = FieldConcept(name="X", concept_type=ConceptType.SPAR, water_depth_m=2400.0)
    codes = {v.code for v in sanity_check(c)}
    assert "depth_outside_host_envelope" not in codes


def test_tree_type_conflict_flagged():
    # Spar is a dry-tree host; declaring wet trees is inconsistent.
    c = FieldConcept(
        name="X",
        concept_type=ConceptType.SPAR,
        tree_type=TreeType.WET,
        water_depth_m=2000.0,
    )
    codes = {v.code for v in sanity_check(c)}
    assert "tree_type_concept_conflict" in codes


def test_sparse_concept_produces_no_spurious_violations():
    # Only a name — no cross-field check should fire.
    assert sanity_check(FieldConcept(name="EarlyStage")) == []


# --------------------------------------------------------------------------- #
# Loader helpers
# --------------------------------------------------------------------------- #
def test_validate_concept_returns_concept_and_violations():
    concept, violations = validate_concept(
        {"name": "X", "concept_type": "subsea_tieback"}
    )
    assert isinstance(concept, FieldConcept)
    assert any(v.code == "tieback_missing_distance" for v in violations)


def test_load_concept_from_dict():
    c = load_concept({"name": "Stones", "concept_type": "fpso", "water_depth_m": 2900})
    assert c.concept_type is ConceptType.FPSO


def test_load_concept_json_roundtrip(tmp_path: Path):
    src = FieldConcept(
        name="Mensa", concept_type=ConceptType.SUBSEA_TIEBACK, tieback_distance_km=109.0
    )
    p = tmp_path / "concept.json"
    p.write_text(src.model_dump_json(), encoding="utf-8")
    loaded = load_concept_json(p)
    assert loaded == src


# --------------------------------------------------------------------------- #
# JSON Schema stays in sync with the model
# --------------------------------------------------------------------------- #
def test_committed_json_schema_matches_model():
    assert (
        SCHEMA_PATH.exists()
    ), "field_concept.schema.json missing — run export_schema.py"
    committed = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert (
        committed == build_schema()
    ), "Committed JSON schema is stale — re-run export_schema.py"
