# ABOUTME: Load/validate helpers for FieldConcept objects (dict / JSON / file).
# ABOUTME: Issue #568 — single entry points used across the playbook.
"""
worldenergydata.field_development.loader
========================================

Thin load/validate helpers around :class:`FieldConcept`. ``validate_concept``
combines the two validation layers — Pydantic construction (raises on impossible
single values) and the engineering sanity gate (returns cross-field violations).
"""

from __future__ import annotations

import json
from pathlib import Path

from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.sanity import SanityViolation, sanity_check


def load_concept(data: dict) -> FieldConcept:
    """Construct a :class:`FieldConcept` from a dict (raises on invalid fields)."""
    return FieldConcept(**data)


def load_concept_json(path: str | Path) -> FieldConcept:
    """Load a :class:`FieldConcept` from a JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        return FieldConcept(**json.load(fh))


def validate_concept(data: dict) -> tuple[FieldConcept, list[SanityViolation]]:
    """Construct and sanity-check a concept in one call.

    Args:
        data: Raw concept dict.

    Returns:
        ``(concept, violations)`` — the validated model plus any cross-field
        engineering violations. An empty ``violations`` list means the concept
        passes the full gate. Pydantic construction errors still raise.
    """
    concept = FieldConcept(**data)
    return concept, sanity_check(concept)
