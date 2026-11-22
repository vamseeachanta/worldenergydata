"""Audit evidence for an upstream spar versus semisub calibration experiment.

An ELIGIBLE result means that the supplied provenance meets this audit's
protocol, not that the feature discriminates hull types or is independently
verified. Rankings and the existing in-sample calibration are unchanged.

Method: *Leakage and the Reproducibility Crisis in ML-based Science*, arXiv
2207.07048v1 (2022), section 2.4 [L2, L3.1]: justify feature legitimacy and
exclude future information. See docs/domains/field-development/calibration-v4.md
for the source, strict date ordering and remaining evidence gaps.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import Enum


class FeatureTiming(str, Enum):
    PRE_DECISION = "pre_decision"
    CO_DECIDED = "co_decided"
    POST_DECISION = "post_decision"
    UNKNOWN = "unknown"


class EvidenceStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    REJECTED = "REJECTED"
    NOT_EVALUATED = "NOT_EVALUATED"


# Research candidates, not an empirically supported discriminator. Issue #640
# and concept-selection-and-ai-cad-briefing.md sections A2/A3 identify these
# reservoir, site and experience questions. Expected counts and reserves must
# refer to their pre-decision vintage, never the as-built or revised values.
CANDIDATE_FEATURES = (
    "reservoir_compactness",
    "drill_centre_spread",
    "intervention_frequency",
    "expected_well_count",
    "hpht",
    "prior_spar_count",
    "prior_semisub_count",
    "predecision_reserves_mmboe",
    "seabed_terrain",
)

# Outcome-derived or co-decided fields: issue #640's leakage constraint and the
# concept/architecture group in models.FieldConcept. Raw well/tree counts are
# deliberately separate from a dated expected_well_count observation.
OUTCOME_FEATURES = frozenset(
    {
        "concept_type",
        "tree_type",
        "num_dry_trees",
        "num_wells",
        "num_trees",
        "num_manifolds",
        "riser_type",
        "topology",
        "tieback_distance_km",
        "flowline_diameter_in",
        "flowline_material",
        "hull_dimensions",
        "mooring_pattern",
        "installation_method",
    }
)


@dataclass(frozen=True)
class DecisionEvidence:
    """Earliest documented concept decision; source must support its date.

    The caller guarantees that this decision and every supplied observation
    describe the same field; field identity is not checked by the audit.
    """

    selected_on: date | None
    source: str | None


@dataclass(frozen=True)
class FeatureEvidence:
    """One value and its evidence, kept separate from the undated field model.

    ``available_on`` is when this exact value became public, not a retrieval
    date. ``legitimacy_basis`` explains why its derivation is independent of
    the concept choice. Sources should identify the document and location.
    The caller guarantees that this value describes the decision's field.
    Supported value types are bool, int, float and str; per-feature meaning
    and ranges are not checked. Other types are reported as unrecognised.
    """

    name: str
    value: bool | int | float | str | None
    timing: FeatureTiming
    available_on: date | None
    source: str | None
    legitimacy_basis: str | None


@dataclass(frozen=True)
class EvidenceCheck:
    status: EvidenceStatus
    reason: str


def _has_text(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


def audit_feature(
    observation: FeatureEvidence, decision: DecisionEvidence
) -> EvidenceCheck:
    """Screen a supplied observation without imputing dates, values or timing.

    Same-day evidence is rejected because calendar-date resolution cannot
    establish order. Strict ordering implements the leakage paper's section
    2.4 [L2/L3.1]; it is not a published hull-selection rule.
    The caller guarantees that observation and decision describe one field.
    """
    if observation.name in OUTCOME_FEATURES:
        return EvidenceCheck(
            EvidenceStatus.REJECTED, "known outcome or co-decided proxy"
        )
    if observation.timing in (FeatureTiming.CO_DECIDED, FeatureTiming.POST_DECISION):
        return EvidenceCheck(
            EvidenceStatus.REJECTED, "feature is co-decided or downstream"
        )
    if observation.name not in CANDIDATE_FEATURES:
        return EvidenceCheck(
            EvidenceStatus.NOT_EVALUATED, "unreviewed candidate feature"
        )
    if observation.timing != FeatureTiming.PRE_DECISION:
        return EvidenceCheck(EvidenceStatus.NOT_EVALUATED, "feature timing is unknown")
    value = observation.value
    if value is not None and not isinstance(value, (bool, int, float, str)):
        return EvidenceCheck(EvidenceStatus.NOT_EVALUATED, "value type not recognised")
    if (
        value is None
        or (isinstance(value, str) and not value.strip())
        or (isinstance(value, float) and not math.isfinite(value))
    ):
        return EvidenceCheck(
            EvidenceStatus.NOT_EVALUATED, "missing or non-finite feature value"
        )
    if not _has_text(observation.source) or not _has_text(observation.legitimacy_basis):
        return EvidenceCheck(
            EvidenceStatus.NOT_EVALUATED,
            "feature source or legitimacy basis is missing",
        )
    if not _has_text(decision.source) or type(decision.selected_on) is not date:
        return EvidenceCheck(
            EvidenceStatus.NOT_EVALUATED, "dated decision source is missing"
        )
    if type(observation.available_on) is not date:
        return EvidenceCheck(
            EvidenceStatus.NOT_EVALUATED, "feature availability date is missing"
        )
    if observation.available_on >= decision.selected_on:
        return EvidenceCheck(
            EvidenceStatus.REJECTED,
            "feature must be public strictly before the decision",
        )
    return EvidenceCheck(
        EvidenceStatus.ELIGIBLE,
        "supplied evidence meets the pre-decision audit protocol",
    )


def audit_candidates(
    observations: Iterable[FeatureEvidence], decision: DecisionEvidence
) -> dict[str, EvidenceCheck]:
    """Report missing candidates explicitly and retain rejected extra inputs.

    The caller guarantees one field per call: all observations must describe
    the same field as the decision. Field identity is not checked here.
    Duplicate feature names raise rather than silently selecting a vintage.
    No overall pass or predictive-validity conclusion is inferred from this map.
    """
    by_name: dict[str, FeatureEvidence] = {}
    for observation in observations:
        if observation.name in by_name:
            raise ValueError(
                "duplicate feature observation; select a documented vintage"
            )
        by_name[observation.name] = observation
    checks = {
        name: EvidenceCheck(
            EvidenceStatus.NOT_EVALUATED, "no candidate observation supplied"
        )
        for name in CANDIDATE_FEATURES
    }
    checks.update(
        (name, audit_feature(observation, decision))
        for name, observation in by_name.items()
    )
    return checks
