# ABOUTME: Public API for the offshore field-development playbook package.
# ABOUTME: Issue #568 (epic #567) — exports the FieldConcept contract + gate.
"""
worldenergydata.field_development
=================================

Offshore field-development playbook (epic #567): given field parameters, produce
a ranked concept shortlist and schematics. This package currently provides the
**shared contract** — :class:`FieldConcept` — plus its validation layers.

Design spine: the LLM reasons and specifies; deterministic code lays out and
draws. Everything downstream (recommendation engine, graph-spec mapper,
renderers, economics) consumes and produces :class:`FieldConcept`.
"""

from worldenergydata.field_development.enums import (
    ConceptType,
    FlowlineMaterial,
    FluidType,
    MetoceanRegime,
    ReservoirDistribution,
    RiserType,
    Topology,
    TreeType,
)
from worldenergydata.field_development.loader import (
    load_concept,
    load_concept_json,
    validate_concept,
)
from worldenergydata.field_development.models import SCHEMA_VERSION, FieldConcept
from worldenergydata.field_development.sanity import (
    HOST_DEPTH_ENVELOPES_M,
    SanityViolation,
    is_sane,
    sanity_check,
)

__all__ = [
    "FieldConcept",
    "SCHEMA_VERSION",
    "ConceptType",
    "TreeType",
    "FluidType",
    "Topology",
    "FlowlineMaterial",
    "RiserType",
    "MetoceanRegime",
    "ReservoirDistribution",
    "load_concept",
    "load_concept_json",
    "validate_concept",
    "sanity_check",
    "is_sane",
    "SanityViolation",
    "HOST_DEPTH_ENVELOPES_M",
]
