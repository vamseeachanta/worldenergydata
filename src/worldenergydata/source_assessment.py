"""Evidence-based source triage, independent of ingestion or economic readiness.

Gate basis: https://github.com/vamseeachanta/worldenergydata/issues/753 (2026),
Decision gate: field/well production OR field metadata usable by the adapters.
Monthly resolution is additionally required for the monthly FDAS input branch.
Concessions require a verified field mapping; public access does not grant reuse.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceCapabilities:
    """Task-scoped evidence flags, not an authoritative dataset registration.

    ``production_verified`` refers to the declared structure and resolution.
    For absent/aggregate production it means that the selected source has been
    inspected, not that the country has no production. ``field_metadata`` refers
    to structured field-level inputs, not isolated exploration-well descriptions.
    A HEAD response alone cannot verify workbook structure.
    """

    production_granularity: str
    production_frequency: str
    production_verified: bool
    field_metadata: str
    reuse: str
    concession_field_mapping: bool = False

    def __post_init__(self):
        allowed = {
            "production_granularity": {
                "field",
                "well",
                "concession",
                "aggregate",
                "none",
                "unknown",
            },
            "production_frequency": {"monthly", "annual", "none", "unknown"},
            "field_metadata": {"verified", "absent", "unverified"},
            "reuse": {"cc_by_4_0", "permission_required", "unspecified"},
        }
        for name, values in allowed.items():
            value = getattr(self, name)
            if not isinstance(value, str) or value not in values:
                raise ValueError(f"Invalid {name}: {value!r}")
        for name in ("production_verified", "concession_field_mapping"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be a boolean evidence flag")


@dataclass(frozen=True)
class SourceAssessment:
    """Capability disposition; PROMOTE is a candidate, not execution approval."""

    decision: str
    fdas_production: str
    field_concept: str
    raw_redistribution: str
    reason: str


def _production_fit(source: SourceCapabilities) -> str:
    if not source.production_verified:
        return "NOT_EVALUATED"
    if source.production_granularity in {"aggregate", "none"}:
        return "UNAVAILABLE"
    if (
        source.production_frequency == "unknown"
        or source.production_granularity == "unknown"
    ):
        return "NOT_EVALUATED"
    if source.production_frequency != "monthly":
        return "UNAVAILABLE"
    if (
        source.production_granularity == "concession"
        and not source.concession_field_mapping
    ):
        return "REQUIRES_MAPPING"
    return "CANDIDATE"


def assess_source(source: SourceCapabilities) -> SourceAssessment:
    """Apply the issue gate and report reuse separately, without network or I/O.

    CANDIDATE means only that the relevant capability has been established.
    Units, completeness, freshness, fiscal terms and adapter conformance remain
    ingestion requirements. Reuse flags describe published terms; they do not
    assert that written permission has been obtained.
    """
    production = _production_fit(source)
    metadata = {
        "verified": "CANDIDATE",
        "absent": "UNAVAILABLE",
        "unverified": "NOT_EVALUATED",
    }[source.field_metadata]
    mapped_asset = source.production_granularity in {"field", "well"} or (
        source.production_granularity == "concession"
        and source.concession_field_mapping
    )
    verified_series = (
        source.production_verified and source.production_frequency != "none"
    )
    if (verified_series and mapped_asset) or metadata == "CANDIDATE":
        decision = "PROMOTE"
        reason = "Verified asset production or structured field metadata."
    elif verified_series and source.production_granularity == "concession":
        decision = "REVIEW_MAPPING"
        reason = "Concession production needs a verified field mapping."
    elif "NOT_EVALUATED" in (production, metadata):
        decision = "NOT_EVALUATED"
        reason = "Evidence does not establish the current source structure or metadata."
    else:
        decision = "COVERAGE_ONLY"
        reason = "The inspected source provides neither qualifying production nor field metadata."
    reuse = {
        "cc_by_4_0": "ATTRIBUTION_REQUIRED",
        "permission_required": "PERMISSION_REQUIRED",
        "unspecified": "NOT_EVALUATED",
    }[source.reuse]
    return SourceAssessment(decision, production, metadata, reuse, reason)
