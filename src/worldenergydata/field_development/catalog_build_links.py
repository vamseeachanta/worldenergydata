"""Catalog build links helpers."""

from __future__ import annotations

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

TABLES = common.TABLES
input_contract = common.input_contract
record_id = common.record_id
row_fingerprint = common.row_fingerprint
read_csv = common.read_csv


def build_links(dataset, evidence, entities, parent_csv):
    parents = parent_csv if isinstance(parent_csv, tuple) else read_csv(parent_csv)
    by_id = {e["entity_id"]: e for e in entities}
    records, parent_records = [], {}
    for table in TABLES:
        for row in evidence[table]:
            rid = record_id(dataset, table, row)
            name, entity = _linked_entity(dataset, table, row, entities, by_id)
            link = _record_link(dataset, table, row, rid, name, entity)
            if table == "inherited_cost_records":
                parent = input_contract.parent_link(row, parents, row_fingerprint)
                pid = parent["record_id"]
                parent_records[pid] = parent
                link.update(
                    parent_row_fingerprint=parent["sha256"],
                    parent_record_id=pid,
                    link_status="parent_reference",
                )
                link["dependencies"].append(pid)
            records.append(link)
    fingerprints = {}
    for row in records:
        previous = fingerprints.setdefault(row["record_id"], row["sha256"])
        if previous != row["sha256"]:
            raise ValueError("record identifier collision")
    counts = Counter(row["record_id"] for row in records)
    unique = {
        row["record_id"]: dict(row, multiplicity=counts[row["record_id"]])
        for row in records
    }
    return {
        "records": sorted(unique.values(), key=lambda r: r["record_id"]),
        "parent_references": sorted(
            parent_records.values(), key=lambda r: r["record_id"]
        ),
    }


def _linked_entity(dataset, table, row, entities, by_id):
    name = row.get(
        "name",
        row.get("subject", row.get("entity_or_scope", row.get("project", ""))),
    )
    entity = None
    if table == "field_observations":
        entity = by_id.get(f"{dataset}:{row['entity_id']}")
        if not entity:
            raise ValueError("missing original entity identity")
    if table == "cost_observations":
        scope = {
            "project": "development",
            "block": "block",
            "contract_bundle": "contract_bundle",
        }.get(row["scope_type"])
        entity = input_contract.name_candidate(entities, scope, name)
    if table == "milestone_observations":
        scope = next(
            (
                s
                for s in ("field", "well", "phase", "development")
                if row["scope"].startswith(s)
            ),
            None,
        )
        entity = input_contract.name_candidate(entities, scope, name)
    return name, entity


def _record_link(dataset, table, row, rid, name, entity):
    link = dict(
        record_id=rid,
        table=table,
        sha256=row_fingerprint(row),
        multiplicity=1,
        subject=name,
        entity_id=entity["entity_id"] if entity else None,
        link_status=(
            "resolved"
            if table == "field_observations"
            else "candidate" if entity else "unresolved"
        ),
        dependencies=[],
    )
    if table == "sources":
        link["link_status"] = "source"
    elif table != "inherited_cost_records":
        if not row.get("source_ref"):
            raise ValueError("missing source reference")
        link["dependencies"].append(f"{dataset}:sources:{row['source_ref']}")
    if entity and entity["evidence_record_id"] != rid:
        link["dependencies"].append(entity["evidence_record_id"])
    return link
