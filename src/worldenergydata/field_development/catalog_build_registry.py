"""Catalog build registry helpers."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

if __package__:
    from . import catalog_build_common as common
else:
    _spec = importlib.util.spec_from_file_location(
        "catalog_build_common", Path(__file__).with_name("catalog_build_common.py")
    )
    common = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(common)

input_contract = common.input_contract
TYPE_MAP = common.TYPE_MAP
record_id = common.record_id
row_fingerprint = common.row_fingerprint
read_csv = common.read_csv


def legacy_groups(legacy_csv):
    header, rows = legacy_csv if isinstance(legacy_csv, tuple) else read_csv(legacy_csv)
    grouped = {}
    for row in rows:
        if row["COUNTRY"] != "Angola":
            continue
        fingerprint = row_fingerprint([row[column] for column in header])
        group = grouped.setdefault(
            fingerprint,
            dict(
                legacy_row_fingerprint=fingerprint,
                legacy_field_id=row["FIELD_ID"],
                multiplicity=0,
                status="legacy_only",
                attributes=row,
                original_header=header,
            ),
        )
        group["multiplicity"] += 1
    return [grouped[key] for key in sorted(grouped)]


def build_registry(dataset, observations):
    entities = []
    for row in observations:
        entities.append(
            dict(
                entity_id=f"{dataset}:{row['entity_id']}",
                entity_type=TYPE_MAP.get(row["entity_type"], row["entity_type"]),
                country=row["country"],
                primary_name=row["name"],
                origin_dataset_id=dataset,
                origin_entity_id=row["entity_id"],
                readiness="partial_research_only",
                evidence_record_id=record_id(dataset, "field_observations", row),
                source_ref=row["source_ref"],
                source_vintage=row.get("source_vintage"),
                current_configuration_verified=False,
            )
        )
    if len({e["entity_id"] for e in entities}) != len(entities):
        raise ValueError("entity identity collision")
    return sorted(entities, key=lambda row: row["entity_id"])


def supplement_registry(dataset, evidence, entities):
    """Retain typed scopes; ambiguous names or parent scopes never merge silently."""
    parent_scopes = {}
    for scope, name, table, row in input_contract.scope_claims(evidence):
        parent = row.get("parent_entity_id", row.get("development", row.get("project")))
        key = scope, name
        if scope in {"well", "phase"}:
            if key in parent_scopes and parent_scopes[key] != parent:
                raise ValueError("supplemental parent scope identity collision")
            parent_scopes[key] = parent
        existing = input_contract.name_candidate(entities, scope, name)
        if existing:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        entity = dict(
            entity_id=f"{dataset}:{scope}:{slug}",
            entity_type=scope,
            country="Angola",
            primary_name=name,
            origin_dataset_id=dataset,
            origin_entity_id=None,
            supplemental=True,
            readiness="partial_research_only",
            evidence_record_id=record_id(dataset, table, row),
            source_ref=row["source_ref"],
            source_vintage=row.get("source_vintage"),
            current_configuration_verified=False,
        )
        if entity["entity_id"] in {e["entity_id"] for e in entities}:
            raise ValueError("supplemental entity identity collision")
        entities.append(entity)
    return sorted(entities, key=lambda e: e["entity_id"])


def build_relationships(dataset, evidence, entities):
    output = []
    for row in evidence["field_observations"]:
        target = input_contract.name_candidate(
            entities, "development", row.get("development")
        )
        subject = f"{dataset}:{row['entity_id']}"
        if not target or subject == target["entity_id"]:
            continue
        relation = dict(
            subject_entity_id=subject,
            object_entity_id=target["entity_id"],
            predicate=(
                "phase_of"
                if TYPE_MAP.get(row["entity_type"], row["entity_type"]) == "phase"
                else "part_of"
            ),
            source_refs=[row["source_ref"]],
            source_vintage=row.get("source_vintage"),
            effective_date=None,
            date_precision="unknown",
            status="supported",
            dependencies=[
                record_id(dataset, "field_observations", row),
                target["evidence_record_id"],
            ],
        )
        relation["relationship_id"] = (
            f"{dataset}:relationship:{row_fingerprint(relation)}"
        )
        output.append(relation)
    return sorted(output, key=lambda r: r["relationship_id"])
