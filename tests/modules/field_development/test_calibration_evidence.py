"""Independent truth-table tests for the calibration evidence gate.

All dates, values and references below are synthetic, rather than field data.
The date ordering is hand checked: 2000-01-01 < 2001-01-01 < 2002-01-01.
Same-day evidence is rejected because calendar-date resolution cannot establish
order, as documented in calibration-v4.md, based on the 2022 leakage paper,
section 2.4 [L2/L3.1].
No numerical hull discriminator or empirical acceptance limit is assumed.
Candidate and outcome names below independently transcribe the research
protocol in calibration-v4.md and the concept/architecture field group in
models.py; expected statuses do not come from the gate's registries.
"""

from dataclasses import replace
from datetime import date, datetime

import numpy as np
import pytest

from worldenergydata.field_development.calibration_evidence import (
    DecisionEvidence,
    EvidenceStatus,
    FeatureEvidence,
    FeatureTiming,
    audit_candidates,
    audit_feature,
)

EARLY = date(2000, 1, 1)
DECISION = date(2001, 1, 1)
LATE = date(2002, 1, 1)
CANDIDATES = (
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
OUTCOMES = (
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
)


def decision():
    return DecisionEvidence(selected_on=DECISION, source="synthetic decision record")


def feature(**updates):
    observation = FeatureEvidence(
        name="hpht",
        value=False,
        timing=FeatureTiming.PRE_DECISION,
        available_on=EARLY,
        source="synthetic discovery record",
        legitimacy_basis="synthetic appraisal finding independent of host choice",
    )
    return replace(observation, **updates)


@pytest.mark.parametrize(
    "name,value",
    [("hpht", False), ("prior_spar_count", 0), ("reservoir_compactness", "compact")],
)
def test_false_and_zero_are_observed_values(name, value):
    """Each explicit value is present; an earlier date satisfies the protocol."""
    assert (
        audit_feature(feature(name=name, value=value), decision()).status
        is EvidenceStatus.ELIGIBLE
    )


@pytest.mark.parametrize("name", CANDIDATES)
def test_each_candidate_requires_the_same_provenance(name):
    assert (
        audit_feature(feature(name=name), decision()).status is EvidenceStatus.ELIGIBLE
    )


@pytest.mark.parametrize("name", OUTCOMES)
def test_known_outcomes_cannot_be_admitted_by_backdating_or_reclassification(name):
    """A declared pre-decision date does not make an outcome proxy legitimate."""
    check = audit_feature(feature(name=name), decision())
    assert check.status is EvidenceStatus.REJECTED
    assert "outcome" in check.reason


@pytest.mark.parametrize(
    "timing", [FeatureTiming.CO_DECIDED, FeatureTiming.POST_DECISION]
)
def test_co_decided_and_post_decision_features_are_rejected(timing):
    assert (
        audit_feature(feature(timing=timing), decision()).status
        is EvidenceStatus.REJECTED
    )


@pytest.mark.parametrize("available_on", [DECISION, LATE])
def test_same_day_and_later_evidence_is_rejected(available_on):
    """Neither equality nor a later date satisfies available_on < selected_on."""
    check = audit_feature(feature(available_on=available_on), decision())
    assert check.status is EvidenceStatus.REJECTED
    assert "strictly before" in check.reason


@pytest.mark.parametrize(
    "updates",
    [
        {"value": None},
        {"value": " "},
        {"value": float("nan")},
        {"value": float("inf")},
        {"value": -float("inf")},
        {"value": []},
        {"source": None},
        {"source": " "},
        {"available_on": None},
        {"available_on": "2000-01-01"},
        {"available_on": datetime(2000, 1, 1)},
        {"legitimacy_basis": None},
        {"legitimacy_basis": " "},
        {"timing": FeatureTiming.UNKNOWN},
        {"name": "unreviewed_proxy"},
    ],
)
def test_incomplete_or_unreviewed_evidence_is_not_evaluated(updates):
    check = audit_feature(feature(**updates), decision())
    assert check.status is EvidenceStatus.NOT_EVALUATED
    assert check.reason


@pytest.mark.parametrize(
    "record",
    [
        DecisionEvidence(selected_on=None, source="synthetic decision record"),
        DecisionEvidence(selected_on=DECISION, source=None),
        DecisionEvidence(selected_on=DECISION, source=" "),
        DecisionEvidence(selected_on="2001-01-01", source="synthetic decision record"),
    ],
)
def test_missing_decision_evidence_is_not_evaluated(record):
    assert audit_feature(feature(), record).status is EvidenceStatus.NOT_EVALUATED


def test_empty_audit_exposes_every_missing_candidate():
    """No observations provide no evidence; every registered candidate is unknown."""
    checks = audit_candidates([], decision())
    assert tuple(checks) == CANDIDATES
    assert all(c.status is EvidenceStatus.NOT_EVALUATED for c in checks.values())


def test_outcome_rejection_does_not_require_complete_provenance():
    """A known outcome remains unsuitable even when its dates are absent."""
    observation = feature(name="tree_type", available_on=None, source=None)
    assert audit_feature(observation, decision()).status is EvidenceStatus.REJECTED


def test_batch_preserves_good_missing_and_rejected_results():
    checks = audit_candidates([feature(), feature(name="tree_type")], decision())
    assert checks["hpht"].status is EvidenceStatus.ELIGIBLE
    assert checks["reservoir_compactness"].status is EvidenceStatus.NOT_EVALUATED
    assert checks["tree_type"].status is EvidenceStatus.REJECTED


def test_duplicate_observations_are_not_silently_overwritten():
    with pytest.raises(ValueError, match="duplicate"):
        audit_candidates([feature(), feature(value=True)], decision())


def test_batch_accepts_a_single_pass_iterable():
    checks = audit_candidates((f for f in [feature()]), decision())
    assert checks["hpht"].status is EvidenceStatus.ELIGIBLE


def test_audit_does_not_mutate_evidence():
    observation, record = feature(), decision()
    before = (replace(observation), replace(record))
    audit_candidates([observation], record)
    assert (observation, record) == before


@pytest.mark.parametrize("value", [np.int64(2), []])
def test_unrecognised_value_types_are_reported_without_implying_absence(value):
    check = audit_feature(feature(name="prior_spar_count", value=value), decision())
    assert check.status is EvidenceStatus.NOT_EVALUATED
    assert check.reason == "value type not recognised"


@pytest.mark.parametrize("value", [None, " ", float("nan"), float("inf")])
def test_missing_or_nonfinite_values_have_a_distinct_reason(value):
    check = audit_feature(feature(value=value), decision())
    assert check.status is EvidenceStatus.NOT_EVALUATED
    assert check.reason == "missing or non-finite feature value"


@pytest.mark.parametrize(
    "name,value",
    [("prior_spar_count", -3), ("prior_spar_count", True), ("hpht", "maybe")],
)
def test_gate_does_not_claim_to_validate_feature_semantics(name, value):
    """A provenance result does not establish that a value is meaningful."""
    check = audit_feature(feature(name=name, value=value), decision())
    assert check.status is EvidenceStatus.ELIGIBLE
