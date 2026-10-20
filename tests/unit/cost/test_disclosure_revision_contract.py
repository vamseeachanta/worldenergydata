"""Revision contract examples use synthetic evidence, never production inputs.

Source: issue 344 and the 2026-04-23 revision plan, Scope Boundaries.
Identifiers and dates below are arbitrary test inputs. Expected lineage is
worked out by following the explicit parent pointers, without the implementation.
"""

import pytest
from pydantic import ValidationError

from worldenergydata.cost.data_collection.disclosure_revision_contract import (
    DisclosureRevision,
)


def test_original_and_revised_metadata_roundtrip():
    """original <- amended retains two identities and one backward edge."""
    original = DisclosureRevision(
        logical_disclosure_key="annual-capex",
        version_id="original",
        revision_classification="original",
    )
    amended = DisclosureRevision(
        logical_disclosure_key="annual-capex",
        version_id="amended",
        supersedes_version_id="original",
        publication_date="2024-04-01",
        effective_date="2024-03-01",
        revision_classification="amended",
        revision_reason="Disclosure wording corrected",
    )
    assert original.supersedes_version_id is None
    assert amended.supersedes_version_id == original.version_id
    assert amended != original
    assert DisclosureRevision.model_validate_json(amended.model_dump_json()) == amended
    with pytest.raises(ValidationError):
        original.version_id = "changed"


def revision(version_id="original", parent=None, **overrides):
    """Synthetic metadata: parent pointers, rather than ID order, define age."""
    payload = {
        "logical_disclosure_key": "annual-capex",
        "version_id": version_id,
        "revision_classification": "restated" if parent else "original",
        "supersedes_version_id": parent,
        "publication_date": "2024-04-01" if parent else None,
    }
    payload.update(overrides)
    return DisclosureRevision(**payload)


def disclosure(version=None, **overrides):
    """Synthetic amount 100 is an input, with no asserted real filing evidence."""
    from worldenergydata.cost.data_collection import DisclosureRow

    payload = {
        "operator": "operator",
        "fiscal_year": 2023,
        "scope_type": "project",
        "project_name": "asset",
        "normalized_metric_name": "capex",
        "metric_value": 100.0,
        "metric_unit": "USD_MM",
        "citation": {
            "source_title": "Synthetic disclosure for contract tests",
            "source_url": "https://example.org/synthetic-disclosure",
            "page_reference": "Synthetic input",
            "quoted_text": "Synthetic amount; no production evidence.",
            "confidence": "low",
            "source_priority": "operator_annual_report",
        },
        "revision": version,
    }
    payload.update(overrides)
    return DisclosureRow(**payload)


def test_ingest_preserves_original_and_identical_value_revision():
    """By hand: two distinct IDs => two accepted rows; repeat ID => duplicate."""
    from worldenergydata.cost.data_collection import ingest_disclosure_rows

    original = disclosure(revision())
    revised = disclosure(revision("corrected", "original"))
    result = ingest_disclosure_rows(
        existing_rows=[original],
        raw_rows=[revised.model_dump(mode="json"), revised],
    )
    assert [r.row for r in result.accepted] == [revised]
    assert [r.row for r in result.duplicates] == [revised]
    assert not result.conflicts
    assert not result.invalid
    assert original.revision.supersedes_version_id is None
    assert original.metric_value == 100.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"logical_disclosure_key": " "},
        {"version_id": " "},
        {"revision_reason": " "},
        {"revision_classification": "unknown"},
        {"supersedes_version_id": "original"},
        {"revision_classification": "amended"},
        {"revision_classification": "restated", "supersedes_version_id": "prior"},
        {
            "revision_classification": "restated",
            "supersedes_version_id": "original",
            "publication_date": "2024-04-01",
        },
        {"superseded_by": "changed"},
    ],
)
def test_inconsistent_revision_metadata_is_rejected(overrides):
    """The issue 344 contract forbids blank IDs, invalid kinds and forward edges."""
    with pytest.raises(ValidationError):
        revision(**overrides)


@pytest.mark.parametrize(
    "new_row",
    [
        lambda: disclosure(revision("orphan", "missing")),
        lambda: disclosure(revision("changed", "original"), fiscal_year=2024),
        lambda: disclosure(
            revision("changed", "original", logical_disclosure_key="other")
        ),
        lambda: disclosure(revision("second-root")),
        lambda: disclosure(revision("other-root", logical_disclosure_key="other")),
        lambda: disclosure(),
    ],
)
def test_invalid_lineage_is_conflict_not_silent_replacement(new_row):
    """Hand audit: missing/cross-key parent, second root or unknown lineage fails."""
    from worldenergydata.cost.data_collection import ingest_disclosure_rows

    original = disclosure(revision())
    result = ingest_disclosure_rows(existing_rows=[original], raw_rows=[new_row()])
    assert len(result.conflicts) == 1
    assert not result.accepted
    assert not result.invalid
    assert result.conflicts[0].decision.reason_code.value == "revision_lineage_conflict"


def test_same_version_with_changed_evidence_is_conflict():
    """A reused identity cannot replace 100 with the synthetic input 120."""
    from worldenergydata.cost.data_collection import ingest_disclosure_rows

    original = disclosure(revision())
    changed = disclosure(revision(), metric_value=120.0)
    result = ingest_disclosure_rows(existing_rows=[original], raw_rows=[changed])
    assert len(result.conflicts) == 1
    assert result.conflicts[0].decision.reason_code.value == "version_id_conflict"
    assert not result.accepted


def test_versioned_original_cannot_hide_unversioned_evidence():
    """An unversioned row requires explicit migration, even for identical amounts."""
    from worldenergydata.cost.data_collection import ingest_disclosure_rows

    result = ingest_disclosure_rows(
        existing_rows=[disclosure()], raw_rows=[disclosure(revision())]
    )
    assert len(result.conflicts) == 1
    assert not result.accepted


def test_parent_must_be_accepted_before_child_in_batch():
    """Input [child, root, child] accepts root then child; the orphan stays recorded."""
    from worldenergydata.cost.data_collection import ingest_disclosure_rows

    root = disclosure(revision())
    child = disclosure(revision("child", "original"), metric_value=120.0)
    result = ingest_disclosure_rows(raw_rows=[child, root, child])
    assert [r.index for r in result.accepted] == [1, 2]
    assert [r.index for r in result.conflicts] == [0]


def test_project_linkage_is_stable_across_revisions():
    """Changing an amount does not alter the exact sanction-side match key."""
    from worldenergydata.cost.data_collection import (
        CostDataPoint,
        disclosure_row_is_linkable,
        resolve_cost_datapoint_link,
    )

    sanctioned = CostDataPoint(
        project_name="asset",
        operator="operator",
        region="GOM",
        water_depth_m=1000.0,
        well_depth_m=4000.0,
        cost_usd_mm=100.0,
        year_sanction=2023,
        source="Synthetic sanction input",
        water_depth_band="deep",
        rig_type="drillship",
        activity_type="drilling",
        hpht=False,
        subsea="subsea",
        cost_type="total_capex",
        confidence="low",
    )
    root = disclosure(revision())
    child = disclosure(revision("child", "original"), metric_value=120.0)
    for row in (root, child):
        assert disclosure_row_is_linkable(row.scope_type)
        link = resolve_cost_datapoint_link(row.operator, row.project_name, [sanctioned])
        assert link.matched_record == sanctioned
        assert link.matched_count == 1


def test_invalid_raw_revision_lands_in_invalid_partition():
    """A malformed revision must not become an unversioned accepted row."""
    from worldenergydata.cost.data_collection import ingest_disclosure_rows

    raw = disclosure().model_dump(mode="json")
    raw["revision"] = {"version_id": "incomplete"}
    result = ingest_disclosure_rows(raw_rows=[raw])
    assert len(result.invalid) == 1
    assert not result.accepted
    assert not result.conflicts


def test_incomplete_existing_corpus_is_rejected_before_ingest():
    """An imported orphan cannot establish a trusted corpus for subsequent ingest."""
    from worldenergydata.cost.data_collection import ingest_disclosure_rows

    orphan = disclosure(revision("orphan", "missing"))
    with pytest.raises(ValueError, match="missing"):
        ingest_disclosure_rows(existing_rows=[orphan], raw_rows=[])


def test_direct_classifier_applies_revision_semantics():
    """Calling classification directly preserves the same append-only decision."""
    from worldenergydata.cost.data_collection import classify_disclosure_row

    root = disclosure(revision())
    child = disclosure(revision("child", "original"))
    decision = classify_disclosure_row(
        existing_rows=[root], batch_seen_rows=[], new_row=child
    )
    assert decision.status.value == "accepted"
