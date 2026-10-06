"""Deterministic, source-scoped catalog extension; publication is a separate gate.

Legacy IDs are retained as attributes, never used as field primary keys. This
stdlib-only module can also be loaded directly by the standalone import CLI.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import io
import json
import re
from collections import Counter
from pathlib import Path

TABLES = (
    "sources",
    "field_observations",
    "cost_observations",
    "milestone_observations",
    "inherited_cost_records",
)
PRECISIONS = {
    "day",
    "month",
    "year",
    "range",
    "unknown",
    "upper_bound_day",
    "half_year",
}
TYPES = {
    "field",
    "development",
    "phase",
    "block",
    "area",
    "host",
    "well",
    "contract_bundle",
}
TYPE_MAP = {
    "development_system": "development",
    "development_phase": "phase",
    "development_area": "area",
}
if __package__:
    from . import catalog_inputs as input_contract
    from . import catalog_validation as validation
else:
    _spec = importlib.util.spec_from_file_location(
        "catalog_validation", Path(__file__).with_name("catalog_validation.py")
    )
    validation = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(validation)
    _inputs_spec = importlib.util.spec_from_file_location(
        "catalog_inputs", Path(__file__).with_name("catalog_inputs.py")
    )
    input_contract = importlib.util.module_from_spec(_inputs_spec)
    _inputs_spec.loader.exec_module(input_contract)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def row_fingerprint(values):
    return digest_bytes(canonical(values).encode("utf-8"))


def record_id(dataset, table, record):
    explicit = next(
        (
            record[k]
            for k in ("entity_id", "cost_id", "source_ref")
            if k in record and (k != "source_ref" or table == "sources")
        ),
        None,
    )
    return f"{dataset}:{table}:{explicit or row_fingerprint(record)}"


def read_csv(path):
    return input_contract.csv_input(Path(path).read_bytes())


def load_inputs(snapshot, legacy_csv, parent_csv):
    return input_contract.pinned_inputs(
        snapshot, legacy_csv, parent_csv, validate_evidence
    )


def validate_evidence(tables):
    validation.validate_evidence(tables)


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


def build_crosswalk(entities, observations, ledger, decisions):
    by_origin = {row["entity_id"]: row for row in observations}
    output = []
    for entity in entities:
        if entity.get("supplemental"):
            continue
        obs = by_origin[entity["origin_entity_id"]]
        for group in ledger:
            old = group["attributes"]
            exact = obs["name"] == old["FIELD_NAME"]
            composite = (
                obs["name"] in {"Tombua", "Landana"}
                and old["FIELD_NAME"] == "Tombua Landana"
            )
            if not exact and not composite:
                continue
            compatible = (
                str(obs["block"]) == old["BLOCK"].removeprefix("Block ")
                and entity["entity_type"] == "field"
            )
            status = "pending" if compatible or composite else "conflicting"
            relation = (
                "constituent_of"
                if composite
                else ("phase_of" if entity["entity_type"] == "phase" else "same_entity")
            )
            row = dict(
                entity_id=entity["entity_id"],
                origin_entity_id=entity["origin_entity_id"],
                legacy_row_fingerprint=group["legacy_row_fingerprint"],
                legacy_field_id=old["FIELD_ID"],
                match_status=status,
                relation_type=relation,
                evidence_refs=[obs["source_ref"]],
                rationale="candidate only; owner adjudication required",
                multiplicity=group["multiplicity"],
                schema_version=1,
            )
            row["candidate_payload"] = copy.deepcopy(row)
            row["candidate_sha256"] = row_fingerprint(row["candidate_payload"])
            output.append(row)
            group["status"] = "composite" if composite else "pending"
    return apply_decisions(output, ledger, decisions)


def apply_decisions(candidates, ledger, decisions):
    def keys(row):
        return (row["entity_id"], row["legacy_row_fingerprint"], row["relation_type"])

    updates = {keys(row): row for row in decisions}
    if len(updates) != len(decisions) or set(updates) - {
        keys(row) for row in candidates
    }:
        raise ValueError("duplicate or unknown match decision")
    accepted = {}
    for row in candidates:
        update = updates.get(keys(row))
        if not update:
            continue
        if update["match_status"] not in {
            "accepted",
            "pending",
            "conflicting",
            "rejected",
        }:
            raise ValueError("invalid match status")
        if (
            update.get("approved_by") != "Vamsee"
            or not update.get("approval_ref")
            or update.get("candidate_sha256") != row["candidate_sha256"]
        ):
            raise ValueError(
                "match disposition requires signoff evidence on candidate digest"
            )
        if update["match_status"] == "accepted":
            if (
                update.get("approved_by") != "Vamsee"
                or not update.get("approval_ref")
                or update.get("candidate_sha256") != row["candidate_sha256"]
            ):
                raise ValueError(
                    "accepted match requires owner signoff on candidate digest"
                )
            if row["match_status"] == "conflicting" and not update.get(
                "adjudication_source_refs"
            ):
                raise ValueError("conflict requires source-backed adjudication")
            if row["relation_type"] == "same_entity":
                key = row["legacy_row_fingerprint"]
                if key in accepted and accepted[key] != row["entity_id"]:
                    raise ValueError("legacy group has multiple accepted identities")
                accepted[key] = row["entity_id"]
        row.update(
            {
                k: v
                for k, v in update.items()
                if k
                in {
                    "match_status",
                    "approved_by",
                    "approval_ref",
                    "adjudication_source_refs",
                }
            }
        )
    for group in ledger:
        if group["legacy_row_fingerprint"] in accepted:
            group["status"] = "matched"
    return sorted(candidates, key=keys)


def build_links(dataset, evidence, entities, parent_csv):
    parents = parent_csv if isinstance(parent_csv, tuple) else read_csv(parent_csv)
    by_id = {e["entity_id"]: e for e in entities}
    records, parent_records = [], {}
    for table in TABLES:
        for row in evidence[table]:
            rid = record_id(dataset, table, row)
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


def eligibility_matrix(links, decisions):
    rows = links["records"] + links["parent_references"]
    known = {row["record_id"] for row in rows}
    updates = {row["record_id"]: row for row in decisions}
    if len(updates) != len(decisions) or set(updates) - known:
        raise ValueError("unknown or duplicate publication decision")
    result = []
    for row in rows:
        proposed = dict(
            record_id=row["record_id"],
            table=row["table"],
            sha256=row["sha256"],
            decision="unresolved",
            proposed_decision="unresolved",
            basis=None,
            reviewer=None,
            authority_note=input_contract.AUTHORITY_NOTE,
        )
        update = updates.get(row["record_id"], {})
        if any(
            k in update and update[k] != row[k]
            for k in ("record_id", "table", "sha256")
        ):
            raise ValueError("publication decision cannot overwrite computed identity")
        if update.get("decision", "unresolved") not in {
            "eligible_factual_derivative",
            "permission_granted",
            "unresolved",
            "prohibited",
        }:
            raise ValueError("invalid eligibility decision")
        if update.get("decision") in {
            "eligible_factual_derivative",
            "permission_granted",
        }:
            if (
                update.get("reviewer") != "Vamsee"
                or not update.get("approval_ref")
                or update.get("reviewed_sha256") != row["sha256"]
                or not update.get("basis")
            ):
                raise ValueError(
                    "eligibility requires signoff evidence claim on record digest"
                )
            if update["decision"] == "permission_granted" and not update.get(
                "permission_ref"
            ):
                raise ValueError("permission record required")
        allowed_updates = {
            "decision",
            "basis",
            "reviewer",
            "approval_ref",
            "reviewed_sha256",
            "permission_ref",
        }
        proposed.update({k: v for k, v in update.items() if k in allowed_updates})
        result.append(proposed)
    return result


def build_integration(
    snapshot_dir, legacy_csv, parent_cost_csv, decisions=None, eligibility=None
):
    original, evidence, hashes, cached_csv = load_inputs(
        snapshot_dir, legacy_csv, parent_cost_csv
    )
    dataset = original["dataset_id"]
    entities = build_registry(dataset, evidence["field_observations"])
    entities = supplement_registry(dataset, evidence, entities)
    ledger = legacy_groups(cached_csv[0])
    crosswalk = build_crosswalk(
        entities, evidence["field_observations"], ledger, decisions or []
    )
    sources = {row["source_ref"] for row in evidence["sources"]}
    if any(set(row.get("adjudication_source_refs", [])) - sources for row in crosswalk):
        raise ValueError("unknown adjudication source")
    links = build_links(dataset, evidence, entities, cached_csv[1])
    matrix = eligibility_matrix(links, eligibility or [])
    manifest = dict(
        dataset_id=dataset,
        schema_version=1,
        state="local_draft_not_for_publication",
        readiness="partial_research_only",
        as_of=original.get("as_of"),
        input_hashes=hashes,
        authority_note=input_contract.AUTHORITY_NOTE,
        decision_sha256=row_fingerprint(decisions or []),
        eligibility_sha256=row_fingerprint(matrix),
        counts={table: len(evidence[table]) for table in TABLES},
        entity_counts=dict(Counter(e["entity_type"] for e in entities)),
        research_entity_count=len(evidence["field_observations"]),
        registry_entity_count=len(entities),
        supplemental_entity_count=sum(bool(e.get("supplemental")) for e in entities),
        legacy_row_count=sum(g["multiplicity"] for g in ledger),
        raw_source_hashes="unknown_not_retained",
    )
    return dict(
        entities=entities,
        crosswalk=crosswalk,
        ledger=ledger,
        relationships=build_relationships(dataset, evidence, entities),
        links=links,
        evidence=evidence,
        eligibility=matrix,
        match_decisions=decisions or [],
        manifest=manifest,
    )


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
    exported["match_decisions"] = []
    exported["manifest"].update(
        state="eligible_derived_export",
        source_counts=dict(
            bundle["manifest"]["counts"],
            parent_reference=len(bundle["links"]["parent_references"]),
        ),
        deferred_counts=dict(
            Counter(
                r["table"]
                for r in records + bundle["links"]["parent_references"]
                if r["record_id"] not in allowed
            )
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
    return exported


def csv_bytes(rows):
    if not rows:
        return b""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=sorted(set().union(*(r.keys() for r in rows))),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(
        {k: canonical(v) if isinstance(v, (dict, list)) else v for k, v in r.items()}
        for r in rows
    )
    return stream.getvalue().encode("utf-8")


def write_bundle(bundle, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "entity_registry.csv": csv_bytes(bundle["entities"]),
        "legacy_entity_crosswalk.csv": csv_bytes(bundle["crosswalk"]),
        "legacy_catalog_ledger.csv": csv_bytes(bundle["ledger"]),
        "entity_relationships.csv": csv_bytes(bundle["relationships"]),
        "catalog_links.json": (canonical(bundle["links"]) + "\n").encode(),
        "publication_eligibility.json": (
            canonical(bundle["eligibility"]) + "\n"
        ).encode(),
        "catalog_match_decisions.json": (
            canonical(bundle["match_decisions"]) + "\n"
        ).encode(),
    }
    for table, rows in bundle["evidence"].items():
        files[table + ".json"] = (canonical(rows) + "\n").encode("utf-8")
    manifest = copy.deepcopy(bundle["manifest"])
    manifest["output_hashes"] = {
        name: digest_bytes(raw) for name, raw in sorted(files.items())
    }
    for name, raw in files.items():
        (out / name).write_bytes(raw)
    (out / "integration_manifest.json").write_bytes(
        (canonical(manifest) + "\n").encode("utf-8")
    )


def read_bundle(out_dir, public_only=False):
    out = Path(out_dir)
    manifest = input_contract.strict_json(
        (out / "integration_manifest.json").read_bytes()
    )
    if public_only and manifest["state"] != "eligible_derived_export":
        raise ValueError("local draft is not a public dataset")
    required = {t + ".json" for t in TABLES} | {
        "entity_registry.csv",
        "legacy_entity_crosswalk.csv",
        "legacy_catalog_ledger.csv",
        "entity_relationships.csv",
        "catalog_links.json",
        "publication_eligibility.json",
        "catalog_match_decisions.json",
    }
    validation.validate_manifest(manifest, required)
    pinned = {}
    for name, expected in manifest["output_hashes"].items():
        if Path(name).name != name:
            raise ValueError("unsafe artifact path")
        pinned[name] = (out / name).read_bytes()
        if digest_bytes(pinned[name]) != expected:
            raise ValueError("output digest mismatch or unsafe path")
    tables = {t: input_contract.strict_json(pinned[t + ".json"]) for t in TABLES}
    validate_evidence(tables)
    entities = validation.parsed_csv(pinned["entity_registry.csv"])
    links = input_contract.strict_json(pinned["catalog_links.json"])
    ids = {row["entity_id"] for row in entities}
    if any(
        row.get("entity_id") and row["entity_id"] not in ids for row in links["records"]
    ):
        raise ValueError("dangling entity foreign key")

    def read_optional_csv(name):
        return validation.parsed_csv(pinned[name])

    bundle = dict(
        entities=entities,
        links=links,
        evidence=tables,
        manifest=manifest,
        eligibility=input_contract.strict_json(pinned["publication_eligibility.json"]),
        match_decisions=input_contract.strict_json(
            pinned["catalog_match_decisions.json"]
        ),
        crosswalk=read_optional_csv("legacy_entity_crosswalk.csv"),
        ledger=read_optional_csv("legacy_catalog_ledger.csv"),
        relationships=read_optional_csv("entity_relationships.csv"),
    )
    validation.validate_bundle(bundle)
    return bundle
