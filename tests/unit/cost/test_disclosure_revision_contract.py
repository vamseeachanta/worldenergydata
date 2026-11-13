"""Revision identity, append-only ingestion and explicit lineage failures."""

from copy import deepcopy
from datetime import date

import pytest
from pydantic import ValidationError

from worldenergydata.cost.data_collection import (
    DisclosureRevisionMetadata,
    DisclosureRow,
    classify_disclosure_row,
    disclosure_business_key,
    ingest_disclosure_rows,
)


def metadata(**changes):
    payload = dict(
        logical_disclosure_key="annual-capex-2023",
        version_id="v1",
        revision_classification="original",
    )
    payload.update(changes)
    return payload


def raw_row(revision=None, **changes):
    payload = dict(
        operator="Example operator",
        fiscal_year=2023,
        scope_type="corporate",
        normalized_metric_name="capex",
        metric_value=100.0,
        metric_unit="USD_MM",
        citation=dict(
            source_title="Annual disclosure",
            source_url="https://example.org/annual-disclosure",
            page_reference="table 1",
            quoted_text="Annual expenditure as reported.",
            confidence="high",
            source_priority="operator_annual_report",
        ),
    )
    if revision is not None:
        payload["revision"] = revision
    payload.update(changes)
    return payload


def amended(**changes):
    payload = dict(
        version_id="v2",
        supersedes_version_id="v1",
        publication_date="2024-03-01",
        revision_classification="amended",
    )
    payload.update(changes)
    return metadata(**payload)


def test_original_revision_metadata_requires_expected_fields():
    result = DisclosureRevisionMetadata(**metadata())
    assert result.publication_date is None
    assert result.effective_date is None
    assert result.supersedes_version_id is None
    for required in ("logical_disclosure_key", "version_id", "revision_classification"):
        payload = metadata()
        del payload[required]
        with pytest.raises(ValidationError):
            DisclosureRevisionMetadata(**payload)


@pytest.mark.parametrize("classification", ["amended", "restated"])
@pytest.mark.parametrize("missing", ["supersedes_version_id", "publication_date"])
def test_revised_revision_metadata_requires_backward_pointer(classification, missing):
    payload = amended(revision_classification=classification)
    payload[missing] = None
    with pytest.raises(ValidationError):
        DisclosureRevisionMetadata(**payload)


@pytest.mark.parametrize(
    "changes",
    [
        {"logical_disclosure_key": " "},
        {"version_id": " "},
        {"supersedes_version_id": "v0"},
        {"revision_classification": "unknown"},
        {"publication_date": "not-a-date"},
        {"superseded_by": "v2"},
    ],
)
def test_inconsistent_original_metadata_is_rejected(changes):
    with pytest.raises(ValidationError):
        DisclosureRevisionMetadata(**metadata(**changes))


@pytest.mark.parametrize("pointer", [" ", "v2"])
def test_revised_pointer_cannot_be_blank_or_self_referencing(pointer):
    with pytest.raises(ValidationError):
        DisclosureRevisionMetadata(**amended(supersedes_version_id=pointer))


def test_bidirectional_linkage_is_not_required():
    revision = DisclosureRevisionMetadata(**amended(revision_reason="Corrected amount"))
    assert revision.publication_date == date(2024, 3, 1)
    assert revision.revision_reason == "Corrected amount"
    assert "superseded_by" not in DisclosureRevisionMetadata.model_fields


@pytest.mark.parametrize("value", [100.0, 120.0])
def test_original_and_revised_rows_can_coexist(value):
    raw = [raw_row(metadata()), raw_row(amended(), metric_value=value)]
    snapshot = deepcopy(raw)
    result = ingest_disclosure_rows(raw_rows=raw)
    assert len(result.accepted) == 2
    assert not (result.duplicates or result.conflicts or result.invalid)
    original, revised = [entry.row for entry in result.accepted]
    assert original.revision.version_id == "v1"
    assert revised.revision.supersedes_version_id == "v1"
    assert original.metric_value == 100.0
    assert original.citation == revised.citation
    assert raw == snapshot
    assert disclosure_business_key(original) == disclosure_business_key(revised)
    assert original.revision.logical_disclosure_key == "annual-capex-2023"


def test_version_aware_ingest_bypasses_plain_duplicate_collapse():
    original = DisclosureRow(**raw_row(metadata()))
    revised = DisclosureRow(**raw_row(amended()))
    decision = classify_disclosure_row(
        existing_rows=[original], batch_seen_rows=[], new_row=revised
    )
    assert decision.status == "accepted"
    assert ingest_disclosure_rows(raw_rows=[revised], existing_rows=[original]).accepted
    assert original.revision.supersedes_version_id is None


def test_repeated_version_is_duplicate_but_changed_evidence_is_conflict():
    original = DisclosureRow(**raw_row(metadata()))
    result = ingest_disclosure_rows(
        existing_rows=[original],
        raw_rows=[raw_row(metadata()), raw_row(metadata(), metric_value=120)],
    )
    assert len(result.duplicates) == len(result.conflicts) == 1
    assert result.conflicts[0].decision.reason_code == "version_id_conflict"
    assert not result.accepted


def test_changed_version_metadata_is_conflict_even_with_equal_values():
    result = ingest_disclosure_rows(
        existing_rows=[DisclosureRow(**raw_row(metadata()))],
        raw_rows=[raw_row(metadata(publication_date="2024-01-01"))],
    )
    assert len(result.conflicts) == 1


@pytest.mark.parametrize(
    "revision,changes",
    [
        (amended(supersedes_version_id="absent"), {}),
        (amended(logical_disclosure_key="different"), {}),
        (amended(), {"fiscal_year": 2022}),
        (amended(), {"operator": "Another operator"}),
        (metadata(version_id="other-original"), {}),
    ],
)
def test_invalid_lineage_is_reported_without_accepting_a_row(revision, changes):
    result = ingest_disclosure_rows(
        existing_rows=[DisclosureRow(**raw_row(metadata()))],
        raw_rows=[raw_row(revision, **changes)],
    )
    assert len(result.invalid) == 1
    assert result.invalid[0].errors
    assert not (result.accepted or result.conflicts or result.duplicates)


def test_revision_cannot_precede_its_parent_in_an_ingest_batch():
    result = ingest_disclosure_rows(raw_rows=[raw_row(amended()), raw_row(metadata())])
    assert [entry.index for entry in result.invalid] == [0]
    assert [entry.index for entry in result.accepted] == [1]


def test_version_ids_cannot_be_reused_for_another_logical_disclosure():
    result = ingest_disclosure_rows(
        raw_rows=[
            raw_row(metadata()),
            raw_row(metadata(logical_disclosure_key="other")),
        ]
    )
    assert len(result.conflicts) == 1
    assert result.conflicts[0].decision.reason_code == "version_id_conflict"


def test_non_revision_rows_follow_existing_ingest_behavior():
    plain = raw_row()
    result = ingest_disclosure_rows(
        raw_rows=[plain, plain, raw_row(metric_value=200), {"revision": metadata()}]
    )
    assert [
        len(getattr(result, name))
        for name in ("accepted", "duplicates", "conflicts", "invalid")
    ] == [1, 1, 1, 1]
    assert result.accepted[0].row.revision is None


def test_invalid_metadata_is_reported_in_invalid_partition():
    result = ingest_disclosure_rows(raw_rows=[raw_row(amended(publication_date=None))])
    assert len(result.invalid) == 1
    assert result.invalid[0].errors


@pytest.mark.parametrize("field", ["publication_date", "effective_date"])
@pytest.mark.parametrize("value", [0, 86400, 0.0, True, "0", "86400"])
def test_revision_dates_do_not_infer_epoch_units(field, value):
    with pytest.raises(ValidationError):
        DisclosureRevisionMetadata(**metadata(**{field: value}))


def test_revision_ingest_result_serialization_retains_metadata():
    from worldenergydata.cost.data_collection import IngestResult

    result = ingest_disclosure_rows(raw_rows=[raw_row(metadata()), raw_row(amended())])
    restored = IngestResult.model_validate_json(result.model_dump_json())
    assert restored == result
    assert restored.accepted[1].row.revision.version_id == "v2"
