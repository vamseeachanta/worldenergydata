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

from worldenergydata.field_development.block import render_block_diagram
from worldenergydata.field_development.calibration import (
    CalibrationReport,
    backtest_fields,
)
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
from worldenergydata.field_development.fdp_report import build_fdp_html
from worldenergydata.field_development.graph import (
    Edge,
    EdgeKind,
    GraphSpec,
    Node,
    NodeType,
    concept_to_graph,
)
from worldenergydata.field_development.integrations import (
    Economics,
    EnrichedConcept,
    HardwarePicks,
    VesselFeasibility,
    dev_system_for,
    enrich,
    estimate_economics,
    hardware_picks,
    vessel_feasibility,
)
from worldenergydata.field_development.layout import (
    compute_pixel_positions,
    compute_positions,
    render_layout,
)
from worldenergydata.field_development.llm_completion import (
    CompletionResult,
    complete_concept,
)
from worldenergydata.field_development.loader import (
    load_concept,
    load_concept_json,
    validate_concept,
)
from worldenergydata.field_development.models import SCHEMA_VERSION, FieldConcept
from worldenergydata.field_development.recommendation import (
    CriteriaWeights,
    ScoredConcept,
    Thresholds,
    feasible_concepts,
    recommend,
)
from worldenergydata.field_development.sanity import (
    HOST_DEPTH_ENVELOPES_M,
    SanityViolation,
    is_sane,
    sanity_check,
)
from worldenergydata.field_development.subseaiq import (
    CrosswalkRow,
    bsee_block_key,
    build_bsee_crosswalk,
    crosswalk_summary,
    load_subseaiq_fields,
)
from worldenergydata.field_development.symbols import (
    available_symbols,
    has_symbol,
    render_symbol,
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
    "recommend",
    "feasible_concepts",
    "ScoredConcept",
    "CriteriaWeights",
    "Thresholds",
    "concept_to_graph",
    "GraphSpec",
    "Node",
    "Edge",
    "NodeType",
    "EdgeKind",
    "render_layout",
    "compute_positions",
    "compute_pixel_positions",
    "render_block_diagram",
    "render_symbol",
    "available_symbols",
    "has_symbol",
    "enrich",
    "estimate_economics",
    "dev_system_for",
    "vessel_feasibility",
    "hardware_picks",
    "Economics",
    "VesselFeasibility",
    "HardwarePicks",
    "EnrichedConcept",
    "load_subseaiq_fields",
    "build_bsee_crosswalk",
    "bsee_block_key",
    "crosswalk_summary",
    "CrosswalkRow",
    "sanity_check",
    "is_sane",
    "SanityViolation",
    "HOST_DEPTH_ENVELOPES_M",
    "backtest_fields",
    "CalibrationReport",
    "build_fdp_html",
    "complete_concept",
    "CompletionResult",
]
