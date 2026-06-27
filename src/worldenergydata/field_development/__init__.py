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

from worldenergydata.field_development.basin import (
    BASIN_AFFINITY,
    region_fit,
    region_to_basin,
)
from worldenergydata.field_development.block import render_block_diagram
from worldenergydata.field_development.calibration import (
    CalibrationReport,
    backtest_fields,
    compare_enrichment,
    concept_recall,
)
from worldenergydata.field_development.cost_estimator import (
    PerConceptCostEstimate,
    capex_adjustment_for,
    estimate_field_cost_portfolio,
    estimate_per_concept_costs,
    opex_factor_for,
)
from worldenergydata.field_development.dexpi import (
    dexpi_mapping,
    dexpi_to_graph,
    graph_to_dexpi,
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
from worldenergydata.field_development.flow_assurance import (
    FlowAssuranceAssessment,
    FlowAssuranceRisk,
    FlowAssuranceThresholds,
    RiskSeverity,
    assess_flow_assurance,
    screen_erosion_risk,
    screen_hydrate_risk,
    screen_slugging_risk,
    screen_wax_risk,
    seabed_temperature_c,
)
from worldenergydata.field_development.graph import (
    Edge,
    EdgeKind,
    GraphSpec,
    Node,
    NodeType,
    concept_to_graph,
)
from worldenergydata.field_development.host_enrichment import (
    GOM_TYPICAL_TIEBACK_KM,
    HostRecord,
    correct_satellite_labels,
    enrich_concepts,
    load_host_registry,
    match_host,
    match_tieback,
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
from worldenergydata.field_development.layout_optimization import (
    LayoutSolution,
    Well,
    improvement_vs_naive,
    naive_layout,
    optimize_layout,
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
    "compare_enrichment",
    "concept_recall",
    "CalibrationReport",
    "region_fit",
    "region_to_basin",
    "BASIN_AFFINITY",
    "load_host_registry",
    "enrich_concepts",
    "correct_satellite_labels",
    "match_tieback",
    "match_host",
    "HostRecord",
    "GOM_TYPICAL_TIEBACK_KM",
    "build_fdp_html",
    "assess_flow_assurance",
    "screen_hydrate_risk",
    "screen_wax_risk",
    "screen_slugging_risk",
    "screen_erosion_risk",
    "seabed_temperature_c",
    "FlowAssuranceAssessment",
    "FlowAssuranceRisk",
    "FlowAssuranceThresholds",
    "RiskSeverity",
    "complete_concept",
    "CompletionResult",
    "graph_to_dexpi",
    "dexpi_to_graph",
    "dexpi_mapping",
    "optimize_layout",
    "naive_layout",
    "improvement_vs_naive",
    "LayoutSolution",
    "Well",
    "PerConceptCostEstimate",
    "estimate_per_concept_costs",
    "estimate_field_cost_portfolio",
    "capex_adjustment_for",
    "opex_factor_for",
]
