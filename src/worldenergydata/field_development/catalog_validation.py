"""Semantic checks for catalog extension artifacts, independent of hash checks."""

import importlib.util
from collections import Counter
from pathlib import Path

if __package__:
    from . import catalog_validation_common as common
else:
    _spec = importlib.util.spec_from_file_location(
        "catalog_validation_common",
        Path(__file__).with_name("catalog_validation_common.py"),
    )
    common = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(common)

PRECISIONS = common.PRECISIONS
TYPES = common.TYPES
TYPE_MAP = common.TYPE_MAP
HASH = common.HASH
require = common.require
unique = common.unique
fingerprint = common.fingerprint


if __package__:
    from . import catalog_validation_crosswalk as crosswalk
    from . import catalog_validation_evidence as evidence
    from . import catalog_validation_links as links
else:
    crosswalk = common.load_sibling("catalog_validation_crosswalk")
    evidence = common.load_sibling("catalog_validation_evidence")
    links = common.load_sibling("catalog_validation_links")

validate_date = evidence.validate_date
validate_evidence = evidence.validate_evidence
decode_csv = evidence.decode_csv
parsed_csv = evidence.parsed_csv
validate_links = links.validate_links
validate_record_closure = links.validate_record_closure
validate_crosswalk = crosswalk.validate_crosswalk


def validate_manifest(manifest, expected_files):
    require(
        manifest.get("dataset_id") == "angola-field-development-evidence",
        "invalid dataset identity",
    )
    require(manifest.get("schema_version") == 1, "unsupported schema version")
    require(
        manifest.get("state")
        in {"local_draft_not_for_publication", "eligible_derived_export"},
        "invalid publication state",
    )
    require(manifest.get("readiness") == "partial_research_only", "invalid readiness")
    require(
        set(manifest.get("output_hashes", {})) == expected_files,
        "missing or unexpected output pin",
    )
    expected_inputs = {
        name + ".json"
        for name in (
            "sources",
            "field_observations",
            "cost_observations",
            "milestone_observations",
            "inherited_cost_records",
        )
    } | {"legacy_catalog", "inherited_cost_parent", "original_manifest"}
    require(
        set(manifest.get("input_hashes", {})) == expected_inputs,
        "missing or unexpected input pin",
    )
    hashes = (
        list(manifest["output_hashes"].values())
        + list(manifest["input_hashes"].values())
        + [manifest.get("decision_sha256"), manifest.get("eligibility_sha256")]
        + gate_input_digests(manifest)
    )
    require(
        all(isinstance(value, str) and HASH.fullmatch(value) for value in hashes),
        "invalid digest",
    )
    require(
        all(type(v) is int and v >= 0 for v in manifest.get("counts", {}).values()),
        "invalid record counts",
    )


def gate_input_digests(manifest):
    pins = manifest.get("gate_input_sha256", {})
    require(
        isinstance(pins, dict) and set(pins) <= {"match_decisions", "eligibility"},
        "invalid gate input digest names",
    )
    return list(pins.values())


def validate_relationships(bundle, entity_ids, source_ids, record_ids):
    unique(bundle["relationships"], "relationship_id")
    for row in bundle["relationships"]:
        require(
            row["subject_entity_id"] in entity_ids
            and row["object_entity_id"] in entity_ids,
            "dangling relationship",
        )
        require(
            row["predicate"] in {"part_of", "phase_of", "located_in", "hosted_by"},
            "invalid relationship predicate",
        )
        require(
            row["status"] in {"supported", "conflicting", "unresolved"},
            "invalid relationship status",
        )
        require(row["date_precision"] in PRECISIONS, "invalid relationship precision")
        require(
            row.get("effective_date") or row["date_precision"] == "unknown",
            "blank relationship date",
        )
        require(
            set(row["source_refs"]) <= source_ids
            and set(row.get("dependencies", [])) <= record_ids,
            "dangling relationship evidence",
        )


def validate_bundle(bundle):
    entities = bundle["entities"]
    ids = unique(entities, "entity_id")
    sources = unique(bundle["evidence"]["sources"], "source_ref")
    for row in entities:
        require(
            row.get("primary_name", "").strip() and row["entity_type"] in TYPES,
            "invalid entity name/type",
        )
        require(
            row["readiness"] == "partial_research_only"
            and row["current_configuration_verified"] is False,
            "invalid entity readiness",
        )
    manifest = bundle["manifest"]
    require(
        manifest["registry_entity_count"] == len(entities), "registry count mismatch"
    )
    require(
        manifest["research_entity_count"]
        == sum(not e.get("supplemental") for e in entities),
        "research count mismatch",
    )
    require(
        manifest["entity_counts"] == dict(Counter(e["entity_type"] for e in entities)),
        "entity type count mismatch",
    )
    for table, rows in bundle["evidence"].items():
        require(manifest["counts"].get(table) == len(rows), "evidence count mismatch")
    record_ids = validate_links(bundle, ids, sources)
    validate_record_closure(bundle)
    validate_crosswalk(bundle, ids, sources)
    validate_relationships(bundle, ids, sources, record_ids)
    if manifest["state"] == "eligible_derived_export":
        validate_public_eligibility(bundle)


def validate_public_eligibility(bundle):
    matrix = bundle["eligibility"]
    unique(matrix, "record_id")
    by_id = {r["record_id"]: r for r in matrix}
    records = bundle["links"]["records"] + bundle["links"]["parent_references"]
    source_counts = bundle["manifest"].get("source_counts", {})
    require(
        set(source_counts) == set(bundle["evidence"]) | {"parent_reference"},
        "missing eligibility source counts",
    )
    exported_counts = dict(
        bundle["manifest"]["counts"],
        parent_reference=len(bundle["links"]["parent_references"]),
    )
    deferred = bundle["manifest"].get("deferred_counts", {})
    require(set(deferred) <= set(source_counts), "unexpected deferred table")
    require(
        all(
            type(count) is int
            and count >= 0
            and count == exported_counts[table] + deferred.get(table, 0)
            for table, count in source_counts.items()
        ),
        "export/deferred count closure mismatch",
    )
    for row in records:
        decision = by_id.get(row["record_id"], {})
        require(
            decision.get("decision")
            in {"eligible_factual_derivative", "permission_granted"},
            "missing publication eligibility",
        )
        require(
            decision.get("reviewer") == "Vamsee"
            and decision.get("approval_ref")
            and decision.get("basis"),
            "missing owner eligibility evidence",
        )
        require(
            decision.get("reviewed_sha256") == row["sha256"], "stale eligibility digest"
        )
        if decision["decision"] == "permission_granted":
            require(
                decision.get("permission_ref"),
                "missing eligibility permission evidence",
            )
