"""Catalog export helpers."""

from __future__ import annotations

import copy
import importlib.util
from collections import Counter
from pathlib import Path

if __package__:
    from . import catalog_build_common as common
else:
    _spec = importlib.util.spec_from_file_location(
        "catalog_build_common", Path(__file__).with_name("catalog_build_common.py")
    )
    common = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(common)

record_id = common.record_id
row_fingerprint = common.row_fingerprint


def public_export(bundle):
    allowed = {
        row["record_id"]
        for row in bundle["eligibility"]
        if row["decision"] in {"eligible_factual_derivative", "permission_granted"}
    }
    records = bundle["links"]["records"]
    changed = True
    while changed:
        denied = {
            row["record_id"] for row in records if set(row["dependencies"]) - allowed
        }
        changed = bool(denied & allowed)
        allowed -= denied
    exported = copy.deepcopy(bundle)
    dataset = bundle["manifest"]["dataset_id"]
    exported["entities"] = [
        e for e in exported["entities"] if e["evidence_record_id"] in allowed
    ]
    if not exported["entities"]:
        raise ValueError(
            "all entities deferred; empty export is not integration success"
        )
    _filter_export_relationships(exported, dataset, allowed)
    _update_ledger_status(exported)
    _filter_export_records(exported, dataset, records, allowed)
    _update_export_manifest(bundle, exported, records, allowed)
    return exported


def _update_ledger_status(exported):
    for group in exported["ledger"]:
        matches = [
            r
            for r in exported["crosswalk"]
            if r["legacy_row_fingerprint"] == group["legacy_row_fingerprint"]
        ]
        group["status"] = (
            "matched"
            if any(
                r["match_status"] == "accepted" and r["relation_type"] == "same_entity"
                for r in matches
            )
            else (
                "composite"
                if any(r["relation_type"] == "constituent_of" for r in matches)
                else "pending" if matches else "legacy_only"
            )
        )


def _update_export_manifest(bundle, exported, records, allowed):
    exported["manifest"].update(
        state="eligible_derived_export",
        source_counts=dict(
            bundle["manifest"]["counts"],
            parent_reference=len(bundle["links"]["parent_references"]),
        ),
        deferred_counts=_deferred_counts(
            records + bundle["links"]["parent_references"], allowed
        ),
        counts={t: len(rows) for t, rows in exported["evidence"].items()},
        entity_counts=dict(Counter(e["entity_type"] for e in exported["entities"])),
    )
    exported["manifest"].update(
        research_entity_count=sum(
            not e.get("supplemental") for e in exported["entities"]
        ),
        registry_entity_count=len(exported["entities"]),
        supplemental_entity_count=sum(
            bool(e.get("supplemental")) for e in exported["entities"]
        ),
        decision_sha256=row_fingerprint(exported["match_decisions"]),
        eligibility_sha256=row_fingerprint(exported["eligibility"]),
    )


def _filter_export_records(exported, dataset, records, allowed):
    exported["links"]["records"] = [r for r in records if r["record_id"] in allowed]
    exported["links"]["parent_references"] = [
        r for r in exported["links"]["parent_references"] if r["record_id"] in allowed
    ]
    exported["evidence"] = {
        t: [r for r in rows if record_id(dataset, t, r) in allowed]
        for t, rows in exported["evidence"].items()
    }
    exported["eligibility"] = [
        r for r in exported["eligibility"] if r["record_id"] in allowed
    ]
    matches = {
        (row["entity_id"], row["legacy_row_fingerprint"], row["relation_type"])
        for row in exported["crosswalk"]
    }
    exported["match_decisions"] = [
        row
        for row in exported["match_decisions"]
        if (row["entity_id"], row["legacy_row_fingerprint"], row["relation_type"])
        in matches
    ]


def _filter_export_relationships(exported, dataset, allowed):
    entity_ids = {e["entity_id"] for e in exported["entities"]}
    exported["relationships"] = [
        r
        for r in exported["relationships"]
        if r["subject_entity_id"] in entity_ids
        and r["object_entity_id"] in entity_ids
        and not set(r["dependencies"]) - allowed
    ]
    source_ids = {
        r["source_ref"]
        for r in exported["evidence"]["sources"]
        if record_id(dataset, "sources", r) in allowed
    }
    exported["crosswalk"] = [
        r
        for r in exported["crosswalk"]
        if r["entity_id"] in entity_ids
        and (set(r["evidence_refs"]) | set(r.get("adjudication_source_refs", [])))
        <= source_ids
    ]


def _deferred_counts(records, allowed):
    counts = Counter()
    for row in records:
        if row["record_id"] not in allowed:
            counts[row["table"]] += (
                1 if row["table"] == "parent_reference" else row["multiplicity"]
            )
    return dict(counts)
