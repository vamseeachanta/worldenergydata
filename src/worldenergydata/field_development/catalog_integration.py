"""Deterministic, source-scoped catalog extension; publication is a separate gate.

This stdlib-only facade preserves package and standalone CLI imports.
"""

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

input_contract = common.input_contract
validation = common.validation
TABLES = common.TABLES
PRECISIONS = common.PRECISIONS
TYPES = common.TYPES
TYPE_MAP = common.TYPE_MAP
canonical = common.canonical
digest_bytes = common.digest_bytes
row_fingerprint = common.row_fingerprint
record_id = common.record_id
read_csv = common.read_csv
load_inputs = common.load_inputs
validate_evidence = common.validate_evidence
_registry = common.load_peer("catalog_build_registry")
legacy_groups = _registry.legacy_groups
build_registry = _registry.build_registry
supplement_registry = _registry.supplement_registry
build_relationships = _registry.build_relationships
_crosswalk = common.load_peer("catalog_build_crosswalk")
build_crosswalk = _crosswalk.build_crosswalk
apply_decisions = _crosswalk.apply_decisions
build_links = common.load_peer("catalog_build_links")
build_links = build_links.build_links
build_eligibility = common.load_peer("catalog_build_eligibility")
eligibility_matrix = build_eligibility.eligibility_matrix
export = common.load_peer("catalog_export")
public_export = export.public_export
storage = common.load_peer("catalog_storage")
csv_bytes = storage.csv_bytes
write_bundle = storage.write_bundle
read_bundle = storage.read_bundle


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
