"""
ABOUTME: Disclosure-layer citation/provenance and ingest classification contract (issue #337).
ABOUTME: Defines validation primitives + accepted/duplicate/conflict/invalid partitioning
ABOUTME: with explicit conflict-reason codes for annual operator disclosure ingest.

This module is the disclosure-layer contract surface. It is intentionally
independent from the legacy sanction `CostDataPoint` schema in
`calibration_schema.py`: the sanction surface keeps its single freeform
`source` string + `confidence` enum, while annual disclosure rows must carry
structured row-level provenance (`source_title`, `source_url`,
`page_reference`, `quoted_text`, `confidence`, `source_priority`).

Conflict reasoning uses explicit reason codes; source-priority differences
are *annotated*, not silently resolved (the human/automation reviewing
conflicts decides the winner). Duplicate/conflict classification considers
both rows already in the dataset and rows already accepted earlier in the
same incoming batch.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DisclosureConfidence(str, Enum):
    """Confidence level for an annual-disclosure row.

    Mirrors the sanction-layer Confidence enum by intent but is defined
    independently so the disclosure layer can evolve its own quality rubric
    without retrofitting the sanction schema.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DisclosureScope(str, Enum):
    """Reporting scope for a disclosed metric."""

    PROJECT = "project"
    CORPORATE = "corporate"
    SEGMENT = "segment"


class SourcePriority(str, Enum):
    """Ordered hierarchy of disclosure source types.

    `rank` is monotonically increasing (lower number = stronger source).
    The hierarchy is used to *annotate* conflicts, not to auto-pick winners.
    """

    OPERATOR_ANNUAL_REPORT = "operator_annual_report"
    SEC_FILING = "sec_filing"
    REGULATOR_DOCUMENT = "regulator_document"
    INVESTOR_PRESENTATION = "investor_presentation"
    PRESS_RELEASE = "press_release"
    SECONDARY_OPERATOR_CONFIRMED = "secondary_operator_confirmed"

    @property
    def rank(self) -> int:
        return _SOURCE_PRIORITY_RANK[self]


_SOURCE_PRIORITY_RANK: dict[SourcePriority, int] = {
    SourcePriority.OPERATOR_ANNUAL_REPORT: 0,
    SourcePriority.SEC_FILING: 1,
    SourcePriority.REGULATOR_DOCUMENT: 2,
    SourcePriority.INVESTOR_PRESENTATION: 3,
    SourcePriority.PRESS_RELEASE: 4,
    SourcePriority.SECONDARY_OPERATOR_CONFIRMED: 5,
}


class DisclosureIngestStatus(str, Enum):
    """Outcome partition for an ingested disclosure row."""

    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    INVALID = "invalid"


class ConflictReasonCode(str, Enum):
    """Why two rows with the same business key disagree."""

    VALUE_MISMATCH = "value_mismatch"
    CITATION_MISMATCH = "citation_mismatch"
    SOURCE_PRIORITY_CONFLICT = "source_priority_conflict"


# ---------------------------------------------------------------------------
# Citation + row models
# ---------------------------------------------------------------------------


class DisclosureCitation(BaseModel):
    """Row-level provenance for a disclosed metric.

    All five user-facing fields are mandatory and non-blank. `source_url`
    must be an absolute http/https URL. `page_reference` is a general
    locator (PDF page, section, table, or note identifier) so web-native
    disclosures are supported without forcing a synthetic page number.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_title: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    page_reference: str = Field(..., min_length=1)
    quoted_text: str = Field(..., min_length=1)
    confidence: DisclosureConfidence
    source_priority: SourcePriority

    @field_validator("source_title", "source_url", "page_reference", "quoted_text")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be a non-blank string")
        return value

    @field_validator("source_url")
    @classmethod
    def _require_absolute_http(cls, value: str) -> str:
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("source_url must be an absolute http(s) URL")
        return value


class DisclosureRow(BaseModel):
    """Minimum disclosure-layer row shape for the ingest contract.

    Issue #334 owns the full disclosure schema/dataset. This row type is
    deliberately the smallest shape that lets the contract be exercised
    today; richer schemas can subclass or compose it once #334 lands.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    operator: str = Field(..., min_length=1)
    fiscal_year: int = Field(..., ge=1970, le=2050)
    scope_type: DisclosureScope
    normalized_metric_name: str = Field(..., min_length=1)
    metric_value: float
    metric_unit: str = Field(..., min_length=1)
    citation: DisclosureCitation
    project_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class CitationValidationResult(BaseModel):
    """Result of `validate_disclosure_citation`."""

    model_config = ConfigDict(frozen=True)

    is_valid: bool
    errors: Tuple[str, ...] = ()


def validate_disclosure_citation(row: DisclosureRow) -> CitationValidationResult:
    """Validate the citation block of an already-constructed DisclosureRow.

    Construction of `DisclosureRow`/`DisclosureCitation` already enforces
    the structural rules; this function exists so callers operating on
    pre-validated objects can re-check (or extend) them without rebuilding
    the model.
    """
    errors: list[str] = []
    citation = row.citation
    for field_name in ("source_title", "source_url", "page_reference", "quoted_text"):
        value = getattr(citation, field_name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"citation.{field_name} must be a non-blank string")
    if not (
        citation.source_url.startswith("http://")
        or citation.source_url.startswith("https://")
    ):
        errors.append("citation.source_url must be an absolute http(s) URL")
    if not isinstance(citation.confidence, DisclosureConfidence):
        errors.append("citation.confidence must be a DisclosureConfidence")
    if not isinstance(citation.source_priority, SourcePriority):
        errors.append("citation.source_priority must be a SourcePriority")
    return CitationValidationResult(is_valid=not errors, errors=tuple(errors))


# ---------------------------------------------------------------------------
# Business key + classification
# ---------------------------------------------------------------------------


BusinessKey = Tuple[str, int, DisclosureScope, str, Optional[str]]


def disclosure_business_key(row: DisclosureRow) -> BusinessKey:
    """Tuple key used for duplicate/conflict detection."""
    return (
        row.operator,
        row.fiscal_year,
        row.scope_type,
        row.normalized_metric_name,
        row.project_name,
    )


class ClassificationDecision(BaseModel):
    """Outcome of comparing one new row against an existing/batch corpus."""

    model_config = ConfigDict(frozen=True)

    status: DisclosureIngestStatus
    reason_code: Optional[ConflictReasonCode] = None
    matched_row: Optional[DisclosureRow] = None
    existing_priority: Optional[SourcePriority] = None
    incoming_priority: Optional[SourcePriority] = None


def _citation_payload_equal(a: DisclosureCitation, b: DisclosureCitation) -> bool:
    """Two citations agree on every field *except* source_priority."""
    return (
        a.source_title == b.source_title
        and a.source_url == b.source_url
        and a.page_reference == b.page_reference
        and a.quoted_text == b.quoted_text
        and a.confidence == b.confidence
    )


def classify_disclosure_row(
    *,
    existing_rows: Sequence[DisclosureRow],
    batch_seen_rows: Sequence[DisclosureRow],
    new_row: DisclosureRow,
) -> ClassificationDecision:
    """Classify `new_row` against existing dataset rows + earlier batch rows.

    Search order is: dataset rows first, then earlier rows in the same
    batch. The first business-key collision determines the outcome — there
    is no merging across multiple matches.
    """
    new_key = disclosure_business_key(new_row)
    for candidate in list(existing_rows) + list(batch_seen_rows):
        if disclosure_business_key(candidate) != new_key:
            continue

        value_match = candidate.metric_value == new_row.metric_value
        unit_match = candidate.metric_unit == new_row.metric_unit
        citation_payload_match = _citation_payload_equal(
            candidate.citation, new_row.citation
        )
        priority_match = (
            candidate.citation.source_priority == new_row.citation.source_priority
        )

        if value_match and unit_match and citation_payload_match and priority_match:
            return ClassificationDecision(
                status=DisclosureIngestStatus.DUPLICATE,
                matched_row=candidate,
            )

        if not value_match or not unit_match:
            return ClassificationDecision(
                status=DisclosureIngestStatus.CONFLICT,
                reason_code=ConflictReasonCode.VALUE_MISMATCH,
                matched_row=candidate,
                existing_priority=candidate.citation.source_priority,
                incoming_priority=new_row.citation.source_priority,
            )

        if not citation_payload_match:
            return ClassificationDecision(
                status=DisclosureIngestStatus.CONFLICT,
                reason_code=ConflictReasonCode.CITATION_MISMATCH,
                matched_row=candidate,
                existing_priority=candidate.citation.source_priority,
                incoming_priority=new_row.citation.source_priority,
            )

        # Value, unit, and citation primitives all match — only source_priority differs.
        return ClassificationDecision(
            status=DisclosureIngestStatus.CONFLICT,
            reason_code=ConflictReasonCode.SOURCE_PRIORITY_CONFLICT,
            matched_row=candidate,
            existing_priority=candidate.citation.source_priority,
            incoming_priority=new_row.citation.source_priority,
        )

    return ClassificationDecision(status=DisclosureIngestStatus.ACCEPTED)


# ---------------------------------------------------------------------------
# Ingest contract (partitioned result)
# ---------------------------------------------------------------------------


class AcceptedRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    row: DisclosureRow


class DuplicateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    row: DisclosureRow
    decision: ClassificationDecision


class ConflictRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    row: DisclosureRow
    decision: ClassificationDecision


class InvalidRecord(BaseModel):
    """A raw input that failed citation/row construction or validation."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    index: int
    raw: Any
    errors: Tuple[str, ...]


class IngestResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    accepted: Tuple[AcceptedRecord, ...] = ()
    duplicates: Tuple[DuplicateRecord, ...] = ()
    conflicts: Tuple[ConflictRecord, ...] = ()
    invalid: Tuple[InvalidRecord, ...] = ()


def _coerce_row(raw: Any) -> DisclosureRow:
    """Coerce a dict / DisclosureRow into a DisclosureRow (raises ValidationError)."""
    if isinstance(raw, DisclosureRow):
        return raw
    if isinstance(raw, Mapping):
        payload = dict(raw)
        citation = payload.get("citation")
        if isinstance(citation, Mapping):
            payload["citation"] = DisclosureCitation(**dict(citation))
        return DisclosureRow(**payload)
    raise TypeError(f"unsupported raw row type: {type(raw).__name__}")


def ingest_disclosure_rows(
    *,
    raw_rows: Iterable[Any],
    existing_rows: Sequence[DisclosureRow] = (),
) -> IngestResult:
    """Validate + classify a batch of raw disclosure rows.

    Each raw row is parsed into a DisclosureRow. Failures land in `invalid`.
    Successfully parsed rows are classified against `existing_rows` and
    against rows already accepted earlier in the same batch, then
    partitioned into accepted/duplicates/conflicts. Within each partition,
    original input order is preserved.
    """
    accepted: list[AcceptedRecord] = []
    duplicates: list[DuplicateRecord] = []
    conflicts: list[ConflictRecord] = []
    invalid: list[InvalidRecord] = []

    accepted_rows: list[DisclosureRow] = []

    for index, raw in enumerate(raw_rows):
        try:
            row = _coerce_row(raw)
        except (ValidationError, TypeError, ValueError) as exc:
            invalid.append(
                InvalidRecord(index=index, raw=raw, errors=(str(exc),))
            )
            continue

        citation_check = validate_disclosure_citation(row)
        if not citation_check.is_valid:
            invalid.append(
                InvalidRecord(index=index, raw=raw, errors=citation_check.errors)
            )
            continue

        decision = classify_disclosure_row(
            existing_rows=existing_rows,
            batch_seen_rows=accepted_rows,
            new_row=row,
        )
        if decision.status == DisclosureIngestStatus.ACCEPTED:
            accepted.append(AcceptedRecord(index=index, row=row))
            accepted_rows.append(row)
        elif decision.status == DisclosureIngestStatus.DUPLICATE:
            duplicates.append(
                DuplicateRecord(index=index, row=row, decision=decision)
            )
        else:
            conflicts.append(
                ConflictRecord(index=index, row=row, decision=decision)
            )

    return IngestResult(
        accepted=tuple(accepted),
        duplicates=tuple(duplicates),
        conflicts=tuple(conflicts),
        invalid=tuple(invalid),
    )


__all__ = [
    "AcceptedRecord",
    "CitationValidationResult",
    "ClassificationDecision",
    "ConflictReasonCode",
    "ConflictRecord",
    "DisclosureCitation",
    "DisclosureConfidence",
    "DisclosureIngestStatus",
    "DisclosureRow",
    "DisclosureScope",
    "DuplicateRecord",
    "IngestResult",
    "InvalidRecord",
    "SourcePriority",
    "classify_disclosure_row",
    "disclosure_business_key",
    "ingest_disclosure_rows",
    "validate_disclosure_citation",
]
