# ABOUTME: Cross-field engineering sanity gate for FieldConcept objects.
# ABOUTME: Issue #568 — returns violations (does not raise) so callers can repair.
"""
worldenergydata.field_development.sanity
========================================

The **engineering sanity gate** for a :class:`FieldConcept`. Unlike the per-field
Pydantic validators (which raise at construction for impossible *single* values),
these checks are *cross-field* and *engineering* in nature — they encode the
physical envelopes and consistency rules from the concept-selection briefing.

They **return a list of violations** rather than raising. That is deliberate:
the deterministic pipeline can hard-gate on a non-empty list, while the Phase-2
LLM concept-completion step (issue #577) can inspect the violations and attempt
a repair before re-checking.

Host water-depth envelopes are first-pass bands from the briefing §A3 (anchored
on real platforms, e.g. Bullwinkle jacket 412 m, Big Foot ETLP 1,580 m, Perdido
spar ~2,450 m, Whale semisub ~2,600 m, Stones FPSO >2,900 m). They are
*screening* bands, not hard physics — hence a flag, not an exception.
"""

from __future__ import annotations

from dataclasses import dataclass

from worldenergydata.field_development.enums import ConceptType, TreeType
from worldenergydata.field_development.models import FieldConcept

# Concept -> (min_m, max_m) practical water-depth envelope (briefing §A3).
HOST_DEPTH_ENVELOPES_M: dict[ConceptType, tuple[float, float]] = {
    ConceptType.NUI: (0.0, 150.0),
    ConceptType.FIXED_JACKET: (0.0, 450.0),
    ConceptType.COMPLIANT_TOWER: (400.0, 900.0),
    ConceptType.TLP: (300.0, 1580.0),
    ConceptType.SPAR: (600.0, 2450.0),
    ConceptType.SEMISUB_FPS: (600.0, 2600.0),
    ConceptType.FPSO: (0.0, 3000.0),
    ConceptType.SUBSEA_TIEBACK: (0.0, 3000.0),
    ConceptType.SUBSEA_TO_SHORE: (0.0, 3000.0),
}

# Concepts whose trees are necessarily wet (subsea).
_WET_TREE_CONCEPTS = {
    ConceptType.SEMISUB_FPS,
    ConceptType.FPSO,
    ConceptType.SUBSEA_TIEBACK,
    ConceptType.SUBSEA_TO_SHORE,
}
# Concepts whose trees are necessarily dry (surface, on the host).
_DRY_TREE_CONCEPTS = {ConceptType.TLP, ConceptType.SPAR}


@dataclass(frozen=True)
class SanityViolation:
    """A single cross-field engineering inconsistency.

    Attributes:
        code: Stable machine identifier for the rule (for tests / repair logic).
        field: The primary field implicated.
        message: Human-readable explanation.
    """

    code: str
    field: str
    message: str


def sanity_check(concept: FieldConcept) -> list[SanityViolation]:
    """Run all cross-field engineering checks on a concept.

    Checks only fire when the fields they depend on are populated, so a sparse
    (early-stage) concept produces no spurious violations.

    Args:
        concept: The :class:`FieldConcept` to check.

    Returns:
        A list of :class:`SanityViolation`; empty if the concept is consistent.
    """
    violations: list[SanityViolation] = []
    violations += _check_wet_tree_well_tree_parity(concept)
    violations += _check_tieback_distance(concept)
    violations += _check_depth_envelope(concept)
    violations += _check_tree_type_consistency(concept)
    return violations


def is_sane(concept: FieldConcept) -> bool:
    """Convenience boolean: True iff the concept has no sanity violations."""
    return not sanity_check(concept)


def _check_wet_tree_well_tree_parity(c: FieldConcept) -> list[SanityViolation]:
    """Wet-tree fields: one subsea tree per well → num_trees == num_wells."""
    is_wet = c.tree_type == TreeType.WET or c.concept_type in _WET_TREE_CONCEPTS
    if is_wet and c.num_wells is not None and c.num_trees is not None:
        if c.num_trees != c.num_wells:
            return [
                SanityViolation(
                    code="wet_tree_well_tree_mismatch",
                    field="num_trees",
                    message=(
                        f"wet-tree concept expects one subsea tree per well "
                        f"(num_trees={c.num_trees} != num_wells={c.num_wells})"
                    ),
                )
            ]
    return []


def _check_tieback_distance(c: FieldConcept) -> list[SanityViolation]:
    """A subsea tieback must have a positive tieback distance."""
    if c.concept_type == ConceptType.SUBSEA_TIEBACK:
        if not c.tieback_distance_km or c.tieback_distance_km <= 0:
            return [
                SanityViolation(
                    code="tieback_missing_distance",
                    field="tieback_distance_km",
                    message=("subsea_tieback concept requires tieback_distance_km > 0"),
                )
            ]
    return []


def _check_depth_envelope(c: FieldConcept) -> list[SanityViolation]:
    """Water depth must lie within the chosen host concept's practical band."""
    if c.concept_type is None or c.water_depth_m is None:
        return []
    band = HOST_DEPTH_ENVELOPES_M.get(c.concept_type)
    if band is None:
        return []
    lo, hi = band
    if not (lo <= c.water_depth_m <= hi):
        return [
            SanityViolation(
                code="depth_outside_host_envelope",
                field="water_depth_m",
                message=(
                    f"water_depth_m={c.water_depth_m} outside the practical band "
                    f"[{lo}, {hi}] m for concept '{c.concept_type.value}'"
                ),
            )
        ]
    return []


def _check_tree_type_consistency(c: FieldConcept) -> list[SanityViolation]:
    """tree_type must agree with concepts that fix it (TLP/Spar dry; subsea wet)."""
    if c.tree_type is None or c.concept_type is None:
        return []
    if c.concept_type in _DRY_TREE_CONCEPTS and c.tree_type != TreeType.DRY:
        return [
            SanityViolation(
                code="tree_type_concept_conflict",
                field="tree_type",
                message=(
                    f"concept '{c.concept_type.value}' uses dry trees, "
                    f"got tree_type='{c.tree_type.value}'"
                ),
            )
        ]
    if c.concept_type in _WET_TREE_CONCEPTS and c.tree_type != TreeType.WET:
        return [
            SanityViolation(
                code="tree_type_concept_conflict",
                field="tree_type",
                message=(
                    f"concept '{c.concept_type.value}' uses wet (subsea) trees, "
                    f"got tree_type='{c.tree_type.value}'"
                ),
            )
        ]
    return []
