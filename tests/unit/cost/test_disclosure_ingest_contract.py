"""
ABOUTME: Tests for the disclosure-layer citation/provenance and ingest classification contract.
ABOUTME: Validates citation completeness, source-priority ordering, and accepted/duplicate/conflict/invalid partitioning.

This contract sits on the disclosure-layer boundary (issue #337) and is intentionally
independent from the legacy sanction CostDataPoint surface (issue #334 owns the
disclosure schema; this module owns the validation/classification contract that
will sit on top of it).
"""

from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from worldenergydata.cost.data_collection.disclosure_ingest_contract import (
    ConflictReasonCode,
    DisclosureCitation,
    DisclosureConfidence,
    DisclosureIngestStatus,
    DisclosureRow,
    DisclosureScope,
    SourcePriority,
    classify_disclosure_row,
    disclosure_business_key,
    ingest_disclosure_rows,
    validate_disclosure_citation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_citation_kwargs() -> dict:
    return {
        "source_title": "BP 2024 Annual Report and Form 20-F",
        "source_url": "https://www.bp.com/content/dam/bp/2024-annual-report.pdf",
        "page_reference": "p. 142",
        "quoted_text": "Mad Dog Phase 2 total project cost was $9.0 billion at completion.",
        "confidence": DisclosureConfidence.HIGH,
        "source_priority": SourcePriority.OPERATOR_ANNUAL_REPORT,
    }


def _valid_row_kwargs(**overrides) -> dict:
    base = {
        "operator": "BP",
        "fiscal_year": 2024,
        "scope_type": DisclosureScope.PROJECT,
        "project_name": "Mad Dog Phase 2",
        "normalized_metric_name": "total_project_cost_usd_mm",
        "metric_value": 9000.0,
        "metric_unit": "USD_MM",
        "citation": DisclosureCitation(**_valid_citation_kwargs()),
    }
    base.update(overrides)
    return base


def _valid_row(**overrides) -> DisclosureRow:
    return DisclosureRow(**_valid_row_kwargs(**overrides))


# ---------------------------------------------------------------------------
# Citation validation
# ---------------------------------------------------------------------------


def test_citation_contract_requires_title_url_page_quote_and_confidence():
    """All five citation fields are mandatory at construction time."""
    base = _valid_citation_kwargs()
    for required_field in (
        "source_title",
        "source_url",
        "page_reference",
        "quoted_text",
        "confidence",
    ):
        kwargs = dict(base)
        kwargs.pop(required_field)
        with pytest.raises(ValidationError):
            DisclosureCitation(**kwargs)


def test_citation_contract_rejects_blank_fields():
    """Whitespace-only string citation fields fail validation."""
    base = _valid_citation_kwargs()
    for blank_field in ("source_title", "source_url", "page_reference", "quoted_text"):
        kwargs = dict(base)
        kwargs[blank_field] = "   "
        with pytest.raises(ValidationError):
            DisclosureCitation(**kwargs)


def test_valid_disclosure_row_is_accepted():
    """A fully populated disclosure row passes the citation validator."""
    row = _valid_row()
    result = validate_disclosure_citation(row)
    assert result.is_valid is True
    assert result.errors == ()


def test_citation_contract_requires_absolute_http_source_url():
    """Relative or non-http(s) source_urls fail validation."""
    base = _valid_citation_kwargs()
    for bad_url in ("/relative/path.pdf", "ftp://example.com/file.pdf", "example.com/file.pdf", ""):
        kwargs = dict(base)
        kwargs["source_url"] = bad_url
        with pytest.raises(ValidationError):
            DisclosureCitation(**kwargs)


def test_confidence_must_use_declared_enum():
    """confidence is enum-typed; arbitrary strings are rejected."""
    base = _valid_citation_kwargs()
    base["confidence"] = "very-high"
    with pytest.raises(ValidationError):
        DisclosureCitation(**base)


def test_non_pdf_locators_are_accepted_in_page_reference():
    """page_reference is a general locator — section/table identifiers are valid."""
    base = _valid_citation_kwargs()
    for locator in ("Section 4.2", "Table 12", "Note 7", "Item 1A — Risk Factors"):
        kwargs = dict(base)
        kwargs["page_reference"] = locator
        citation = DisclosureCitation(**kwargs)
        assert citation.page_reference == locator


# ---------------------------------------------------------------------------
# Source priority
# ---------------------------------------------------------------------------


def test_source_priority_values_are_explicit_and_ordered():
    """SourcePriority is a deterministic, ordered hierarchy."""
    expected_order = [
        SourcePriority.OPERATOR_ANNUAL_REPORT,
        SourcePriority.SEC_FILING,
        SourcePriority.REGULATOR_DOCUMENT,
        SourcePriority.INVESTOR_PRESENTATION,
        SourcePriority.PRESS_RELEASE,
        SourcePriority.SECONDARY_OPERATOR_CONFIRMED,
    ]
    sorted_by_rank = sorted(SourcePriority, key=lambda p: p.rank)
    assert sorted_by_rank == expected_order
    ranks = [p.rank for p in expected_order]
    assert ranks == sorted(ranks), "ranks must be monotonically increasing"
    assert len(set(ranks)) == len(ranks), "ranks must be unique"


# ---------------------------------------------------------------------------
# Business key
# ---------------------------------------------------------------------------


def test_disclosure_business_key_includes_required_dimensions():
    """The business key disambiguates rows by operator + fiscal_year + scope + metric (+ optional project)."""
    row = _valid_row()
    key = disclosure_business_key(row)
    assert key == (
        "BP",
        2024,
        DisclosureScope.PROJECT,
        "total_project_cost_usd_mm",
        "Mad Dog Phase 2",
    )


def test_disclosure_business_key_omits_optional_project_for_corporate_scope():
    """Corporate-scope rows omit project_name from the key."""
    row = _valid_row(scope_type=DisclosureScope.CORPORATE, project_name=None)
    key = disclosure_business_key(row)
    assert key == (
        "BP",
        2024,
        DisclosureScope.CORPORATE,
        "total_project_cost_usd_mm",
        None,
    )


# ---------------------------------------------------------------------------
# Row-level classification
# ---------------------------------------------------------------------------


def test_duplicate_classification_for_identical_business_key_and_payload():
    """Same business key + identical metric value and citation → DUPLICATE, no reason code."""
    existing = _valid_row()
    incoming = _valid_row()
    decision = classify_disclosure_row(
        existing_rows=[existing], batch_seen_rows=[], new_row=incoming
    )
    assert decision.status == DisclosureIngestStatus.DUPLICATE
    assert decision.reason_code is None


def test_conflict_classification_for_same_business_key_different_value():
    """Same key, different metric_value → CONFLICT with VALUE_MISMATCH."""
    existing = _valid_row()
    incoming = _valid_row(metric_value=9500.0)
    decision = classify_disclosure_row(
        existing_rows=[existing], batch_seen_rows=[], new_row=incoming
    )
    assert decision.status == DisclosureIngestStatus.CONFLICT
    assert decision.reason_code == ConflictReasonCode.VALUE_MISMATCH


def test_conflict_classification_for_same_business_key_different_citation():
    """Same key + same value, different citation (different source_url) → CITATION_MISMATCH."""
    existing = _valid_row()
    differing_citation = DisclosureCitation(
        **{**_valid_citation_kwargs(), "source_url": "https://www.bp.com/another-2024.pdf"}
    )
    incoming = _valid_row(citation=differing_citation)
    decision = classify_disclosure_row(
        existing_rows=[existing], batch_seen_rows=[], new_row=incoming
    )
    assert decision.status == DisclosureIngestStatus.CONFLICT
    assert decision.reason_code == ConflictReasonCode.CITATION_MISMATCH


def test_source_priority_affects_conflict_reasoning():
    """Same key + same value + same provenance fields but DIFFERENT source_priority → SOURCE_PRIORITY_CONFLICT."""
    existing = _valid_row()
    lower_priority_citation = DisclosureCitation(
        **{
            **_valid_citation_kwargs(),
            "source_priority": SourcePriority.PRESS_RELEASE,
        }
    )
    incoming = _valid_row(citation=lower_priority_citation)
    decision = classify_disclosure_row(
        existing_rows=[existing], batch_seen_rows=[], new_row=incoming
    )
    assert decision.status == DisclosureIngestStatus.CONFLICT
    assert decision.reason_code == ConflictReasonCode.SOURCE_PRIORITY_CONFLICT
    # Annotation must record both priorities so a reviewer can adjudicate later.
    assert decision.existing_priority == SourcePriority.OPERATOR_ANNUAL_REPORT
    assert decision.incoming_priority == SourcePriority.PRESS_RELEASE


def test_source_priority_does_not_auto_select_winner():
    """Source-priority differences are annotated, not silently resolved.

    The plan is explicit: 'Source-priority affects conflict annotation, not
    automatic winner selection.' Even when the incoming row carries a higher
    priority than the existing row, the result must still be CONFLICT (not
    ACCEPTED or DUPLICATE).
    """
    lower_priority_existing = _valid_row(
        citation=DisclosureCitation(
            **{**_valid_citation_kwargs(), "source_priority": SourcePriority.PRESS_RELEASE}
        )
    )
    higher_priority_incoming = _valid_row()  # OPERATOR_ANNUAL_REPORT (rank 0)
    decision = classify_disclosure_row(
        existing_rows=[lower_priority_existing],
        batch_seen_rows=[],
        new_row=higher_priority_incoming,
    )
    assert decision.status == DisclosureIngestStatus.CONFLICT
    assert decision.reason_code == ConflictReasonCode.SOURCE_PRIORITY_CONFLICT


def test_classification_returns_accepted_for_unique_key():
    """A row with a fresh business key against existing rows → ACCEPTED."""
    existing = _valid_row()
    incoming = _valid_row(fiscal_year=2023)
    decision = classify_disclosure_row(
        existing_rows=[existing], batch_seen_rows=[], new_row=incoming
    )
    assert decision.status == DisclosureIngestStatus.ACCEPTED
    assert decision.reason_code is None


# ---------------------------------------------------------------------------
# Within-batch classification
# ---------------------------------------------------------------------------


def test_within_batch_duplicate_and_conflict_behavior_is_defined():
    """Classification must consider rows already accepted earlier in the same batch."""
    earlier = _valid_row()
    duplicate_incoming = _valid_row()
    decision_dup = classify_disclosure_row(
        existing_rows=[], batch_seen_rows=[earlier], new_row=duplicate_incoming
    )
    assert decision_dup.status == DisclosureIngestStatus.DUPLICATE

    conflicting_incoming = _valid_row(metric_value=9500.0)
    decision_conf = classify_disclosure_row(
        existing_rows=[], batch_seen_rows=[earlier], new_row=conflicting_incoming
    )
    assert decision_conf.status == DisclosureIngestStatus.CONFLICT
    assert decision_conf.reason_code == ConflictReasonCode.VALUE_MISMATCH


# ---------------------------------------------------------------------------
# Ingest contract — partitioned result
# ---------------------------------------------------------------------------


def test_ingest_contract_returns_partitioned_result_sets():
    """ingest_disclosure_rows returns four explicit partitions with conflict annotations."""
    existing = _valid_row()

    # raw_rows: dict payloads (as a real ingest pipeline would deliver them)
    accepted_raw = _valid_row_kwargs(fiscal_year=2023)  # fresh key → accepted
    duplicate_raw = _valid_row_kwargs()  # exact match of existing → duplicate
    conflict_raw = _valid_row_kwargs(metric_value=9500.0)  # value conflict

    invalid_raw = _valid_row_kwargs(fiscal_year=2022)
    # break citation: blank quoted_text → invalid
    invalid_raw["citation"] = {**_valid_citation_kwargs(), "quoted_text": "   "}

    result = ingest_disclosure_rows(
        raw_rows=[accepted_raw, duplicate_raw, conflict_raw, invalid_raw],
        existing_rows=[existing],
    )

    assert len(result.accepted) == 1
    assert len(result.duplicates) == 1
    assert len(result.conflicts) == 1
    assert len(result.invalid) == 1

    # Conflict annotation carries the reason code.
    conflict_record = result.conflicts[0]
    assert conflict_record.decision.status == DisclosureIngestStatus.CONFLICT
    assert conflict_record.decision.reason_code == ConflictReasonCode.VALUE_MISMATCH

    # Invalid record carries non-empty error messages.
    invalid_record = result.invalid[0]
    assert invalid_record.errors  # tuple of error strings, non-empty


def test_ingest_contract_handles_within_batch_partitioning():
    """Two identical raw rows in the same batch → first ACCEPTED, second DUPLICATE."""
    raw_a = _valid_row_kwargs()
    raw_b = deepcopy(raw_a)

    result = ingest_disclosure_rows(raw_rows=[raw_a, raw_b], existing_rows=[])
    assert len(result.accepted) == 1
    assert len(result.duplicates) == 1
    assert len(result.conflicts) == 0
    assert len(result.invalid) == 0


def test_ingest_contract_preserves_input_order_within_partitions():
    """Partitioned output preserves the original ingest order so audit trails are reproducible."""
    raw_first = _valid_row_kwargs(fiscal_year=2020)
    raw_second = _valid_row_kwargs(fiscal_year=2021)
    raw_third = _valid_row_kwargs(fiscal_year=2022)

    result = ingest_disclosure_rows(
        raw_rows=[raw_first, raw_second, raw_third], existing_rows=[]
    )
    accepted_years = [r.row.fiscal_year for r in result.accepted]
    assert accepted_years == [2020, 2021, 2022]


# ---------------------------------------------------------------------------
# Boundary: legacy sanction schema is unchanged
# ---------------------------------------------------------------------------


def test_legacy_sanction_schema_is_unchanged():
    """#337 must not contaminate the legacy sanction CostDataPoint schema.

    Specifically, CostDataPoint must NOT have grown disclosure-citation fields
    (source_title, source_url, page_reference, quoted_text). The legacy `source`
    string and `confidence` enum remain the only provenance surface there.
    """
    from worldenergydata.cost.data_collection.calibration_schema import CostDataPoint

    field_names = set(CostDataPoint.model_fields.keys())
    forbidden = {"source_title", "source_url", "page_reference", "quoted_text"}
    leaked = field_names & forbidden
    assert not leaked, f"sanction schema must not carry disclosure-citation fields: {leaked}"
