"""Synthetic worked examples for the issue 344 current/history contract.

Source: the 2026-04-23 issue 344 plan, current-effective precedence. No amounts
represent a real filing. Expected amounts and differences are hand-calculated
in each test; IDs and dates are inputs rather than calibrated constants.
"""

from dataclasses import replace
from itertools import permutations

import pytest

from worldenergydata.cost.data_collection import DisclosureRevision
from worldenergydata.cost.disclosure_analytics import (
    DisclosureRecord,
    load_current_effective_disclosure_rows,
    load_disclosure_revision_history,
    load_operator_annual_capex_view,
    load_project_cost_revision_view,
)


def record(version_id="original", parent=None, **overrides):
    """Synthetic USD-million values; default source is explicitly unverified."""
    metadata = {
        "logical_disclosure_key": "annual-capex",
        "version_id": version_id,
        "supersedes_version_id": parent,
        "revision_classification": "restated" if parent else "original",
        "publication_date": "2024-04-01" if parent else None,
    }
    for name in list(overrides):
        if name in DisclosureRevision.model_fields:
            metadata[name] = overrides.pop(name)
    payload = {
        "operator": "operator",
        "project_name": "asset",
        "fiscal_year": 2023,
        "scope": "project",
        "reported_capex_usd_mm": 100.0,
        "currency": "USD",
        "revision": DisclosureRevision(**metadata),
        "provenance": {"kind": "synthetic", "review": {"verified": False}},
    }
    payload.update(overrides)
    return DisclosureRecord(**payload)


@pytest.mark.parametrize("scope", ["project", "operator"])
def test_current_series_and_full_history_preserve_restatement(scope):
    """Hand calculation: 2023=120 revised from 100; 2024=150; delta=30, 30/120=.25."""
    root = record(scope=scope, project_name="asset" if scope == "project" else None)
    revised = record(
        "revised",
        "original",
        reported_capex_usd_mm=120.0,
        scope=scope,
        project_name=root.project_name,
    )
    following = record(
        "following",
        logical_disclosure_key="next-year",
        fiscal_year=2024,
        reported_capex_usd_mm=150.0,
        scope=scope,
        project_name=root.project_name,
    )
    inputs = [following, revised, root]
    current = load_current_effective_disclosure_rows(iter(inputs))
    assert {r.revision.version_id for r in current} == {"revised", "following"}
    history = load_disclosure_revision_history(
        inputs, logical_disclosure_key="annual-capex"
    )
    assert [r.revision.version_id for r in history] == ["original", "revised"]
    loader = (
        load_project_cost_revision_view
        if scope == "project"
        else load_operator_annual_capex_view
    )
    view = loader(iter(inputs))
    assert [r.reported_capex_usd_mm for r in view] == [120.0, 150.0]
    assert view[0].revision == revised.revision
    assert view[1].yoy_delta_usd_mm == 30.0
    assert view[1].yoy_delta_pct == 0.25
    assert root.reported_capex_usd_mm == 100.0
    view[0].provenance["review"]["verified"] = True
    assert revised.provenance["review"]["verified"] is False


def test_selection_precedence_is_depth_then_dates_then_lexical_id():
    """Follow edges: deep wins over newer shallow; equal-depth ties use dates then ID."""
    root = record()
    left = record("left", "original", publication_date="2024-05-01")
    deep = record("deep", "left", publication_date="2024-04-01")
    shallow = record("shallow", "original", publication_date="2025-01-01")
    assert load_current_effective_disclosure_rows([root, left, deep, shallow]) == [deep]
    a = record("a", "original", effective_date="2024-05-01")
    b = record("b", "original", effective_date="2024-05-01")
    c = record(
        "c", "original", effective_date="2024-04-01", publication_date="2025-01-01"
    )
    for ordered in permutations([root, a, b, c]):
        assert load_current_effective_disclosure_rows(ordered) == [b]
    later = record(
        "later", "original", effective_date="2024-05-01", publication_date="2024-06-01"
    )
    assert load_current_effective_disclosure_rows([root, b, later]) == [later]


def test_raw_ingest_rows_are_supported_by_current_and_history_selectors():
    """The same parent edges apply to ingest rows and analytics input records."""
    from tests.unit.cost.test_disclosure_revision_contract import disclosure, revision
    from worldenergydata.cost.data_collection import ingest_disclosure_rows

    root = disclosure(revision())
    child = disclosure(revision("child", "original"), metric_value=120.0)
    result = ingest_disclosure_rows(raw_rows=[root, child])
    rows = [item.row for item in result.accepted]
    assert load_current_effective_disclosure_rows(rows) == [child]
    assert load_disclosure_revision_history(reversed(rows)) == [root, child]


def test_invalid_imported_corpus_is_rejected():
    """An orphan is not a current value, even when the missing original is older."""
    orphan = record("child", "missing")
    with pytest.raises(ValueError, match="missing"):
        load_current_effective_disclosure_rows([orphan])
    with pytest.raises(ValueError, match="missing"):
        load_disclosure_revision_history([orphan])


def test_legacy_rows_remain_explicit_and_mixed_identity_is_rejected():
    """No identity is guessed for legacy rows; unrelated rows remain available."""
    root = record()
    legacy = replace(root, revision=None)
    with pytest.raises(ValueError, match="unversioned"):
        load_current_effective_disclosure_rows([legacy, root])
    assert load_current_effective_disclosure_rows([legacy]) == [legacy]
    assert load_disclosure_revision_history([legacy]) == [legacy]
    assert (
        load_disclosure_revision_history([legacy], logical_disclosure_key="unknown")
        == []
    )


def test_cycle_and_reused_identity_in_imported_history_are_rejected():
    """Edges a->b->a never reach an original; one ID cannot carry two amounts."""
    a = record("a", "b")
    b = record("b", "a")
    with pytest.raises(ValueError, match="cycle"):
        load_disclosure_revision_history([a, b])
    root = record()
    with pytest.raises(ValueError, match="reused"):
        load_current_effective_disclosure_rows(
            [root, replace(root, reported_capex_usd_mm=120.0)]
        )


def test_history_includes_forks_and_deduplicates_exact_replays():
    """Hand order: root, a, b. b wins a lexical tie; both branches remain auditable."""
    root, a, b = record(), record("a", "original"), record("b", "original")
    rows = [b, root, a, a]
    assert load_disclosure_revision_history(rows) == [root, a, b]
    assert load_current_effective_disclosure_rows(rows) == [b]


def test_long_lineage_does_not_depend_on_python_recursion_limit():
    """A synthetic chain longer than the usual recursion limit ends at its last node."""
    import sys

    # Length is a stress-test input derived from the running interpreter limit.
    count = sys.getrecursionlimit() + 1
    rows = [record()]
    for index in range(count):
        rows.append(record(f"revision-{index}", rows[-1].revision.version_id))
    assert load_current_effective_disclosure_rows(reversed(rows)) == [rows[-1]]
    assert load_disclosure_revision_history(reversed(rows)) == rows


def test_unrelated_legacy_rows_remain_available_in_mixed_corpus():
    """A different fiscal year is a separate business key, not an inferred original."""
    root = record()
    legacy = replace(root, revision=None, fiscal_year=2024)
    assert load_current_effective_disclosure_rows([root, legacy]) == [legacy, root]


def test_revision_metadata_dicts_are_validated_and_public_exports_exist():
    """The analytics boundary validates metadata supplied by serialized callers."""
    from worldenergydata import cost
    from worldenergydata.cost import data_collection

    root = record()
    restored = replace(root, revision=root.revision.model_dump(mode="json"))
    assert restored == root
    assert cost.load_current_effective_disclosure_rows([restored]) == [root]
    assert cost.load_disclosure_revision_history([restored]) == [root]
    assert data_collection.DisclosureRevision is DisclosureRevision
    with pytest.raises(ValueError):
        replace(root, revision={"version_id": "missing-fields"})


def test_documented_worked_example_runs_through_ingest_and_analytics():
    """Hand result: retain 100 and 120; current 120 then 150 => 30 and 30/120=.25."""
    import runpy
    from pathlib import Path

    script = (
        Path(__file__).resolve().parents[3] / "examples/cost/disclosure_revisions.py"
    )
    example = runpy.run_path(str(script))
    assert example["worked_example"]() == {
        "history_values_usd_mm": [100.0, 120.0, 150.0],
        "current_values_usd_mm": [120.0, 150.0],
        "selected_classifications": ["restated", "original"],
        "latest_delta_usd_mm": 30.0,
        "latest_delta_ratio": 0.25,
    }
