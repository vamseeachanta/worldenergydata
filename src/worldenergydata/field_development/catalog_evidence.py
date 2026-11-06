"""Read-only evidence views of validated issue 1144 catalog bundles.

Pass a bundle from catalog_integration.read_bundle; this projection does not
authenticate decisions or replace publication validation. Scope, precision,
units and multiplicity follow data/modules/offshore_assets/schema.yaml.
"""

from __future__ import annotations

import copy
import importlib.util
from collections import defaultdict
from pathlib import Path

if __package__:
    from . import catalog_build_common as common
else:
    _spec = importlib.util.spec_from_file_location(
        "catalog_build_common", Path(__file__).with_name("catalog_build_common.py")
    )
    common = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(common)


class CatalogEvidence:
    """Index exact identifiers; never resolve subjects by name or legacy ID."""

    def __init__(self, bundle):
        self.bundle = bundle
        self.entities = {e["entity_id"]: e for e in bundle["entities"]}
        self.links = {r["record_id"]: r for r in bundle["links"]["records"]}
        self.parents = {r["record_id"]: r for r in bundle["links"]["parent_references"]}
        dataset = bundle["manifest"]["dataset_id"]
        self.observations = {
            common.record_id(dataset, table, row): row
            for table, rows in bundle["evidence"].items()
            for row in rows
        }
        self.by_entity = defaultdict(set)
        for row in self.links.values():
            if row["entity_id"]:
                self.by_entity[row["entity_id"]].add(row["record_id"])

    def record(self, record_id):
        """Return one record group with original values and parent pins."""
        link = self.links[record_id]
        return copy.deepcopy(
            dict(
                link,
                observation=self.observations[record_id],
                parent_references=[
                    self.parents[key]
                    for key in sorted(link["dependencies"])
                    if key in self.parents
                ],
            )
        )

    def entity(self, entity_id):
        """Return direct evidence only; relationships do not allocate evidence."""
        entity = self.entities[entity_id]
        record_ids = self.by_entity[entity_id] | {entity["evidence_record_id"]}
        records = [self.record(key) for key in sorted(record_ids)]
        relationships = [
            row
            for row in self.bundle["relationships"]
            if entity_id in (row["subject_entity_id"], row["object_entity_id"])
        ]
        crosswalk = [
            row for row in self.bundle["crosswalk"] if row["entity_id"] == entity_id
        ]
        accepted = {
            row["legacy_row_fingerprint"]
            for row in crosswalk
            if row["match_status"] == "accepted"
            and row["relation_type"] == "same_entity"
        }
        sources = self._sources(entity, record_ids, relationships, crosswalk)
        return copy.deepcopy(
            {
                "entity": entity,
                "records": records,
                "relationships": relationships,
                "crosswalk": crosswalk,
                "sources": sources,
                "legacy_groups": [
                    row
                    for row in self.bundle["ledger"]
                    if row["legacy_row_fingerprint"] in accepted
                ],
                "legacy_catalog_sha256": self.bundle["manifest"]["input_hashes"][
                    "legacy_catalog"
                ],
            }
        )

    def _sources(self, entity, record_ids, relationships, crosswalk):
        refs = {entity["source_ref"]}
        for row in relationships:
            refs.update(row["source_refs"])
        for row in crosswalk:
            refs.update(row["evidence_refs"])
            refs.update(row.get("adjudication_source_refs", []))
        pending, visited = list(record_ids), set()
        while pending:
            key = pending.pop()
            if key in visited or key in self.parents:
                continue
            visited.add(key)
            link = self.links[key]
            if link["table"] == "sources":
                refs.add(self.observations[key]["source_ref"])
            pending.extend(link["dependencies"])
        return sorted(
            (
                row
                for row in self.bundle["evidence"]["sources"]
                if row["source_ref"] in refs
            ),
            key=lambda row: row["source_ref"],
        )
