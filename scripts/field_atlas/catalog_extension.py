"""Expose typed catalog evidence without treating research as current design input."""

import importlib.util
from collections import defaultdict
from pathlib import Path


def _research_entry(entity, bundle, legacy, duplicate, reader=None):
    identifier = entity["entity_id"]
    origin = entity.get("origin_entity_id")
    observations = [
        row
        for row in bundle.get("evidence", {}).get("field_observations", [])
        if origin and row.get("entity_id") == origin
    ]
    return {
        "catalog_id": identifier,
        "name": entity["primary_name"],
        "country": entity["country"],
        "domain": "offshore",
        "region": entity["country"],
        "block": None,
        "status": None,
        "reserve_type": None,
        "water_depth_ft": None,
        "density_tier": "roadmap",
        "gom": False,
        "readiness": entity["readiness"],
        "current_configuration_verified": False,
        "entity_type": entity["entity_type"],
        "possible_duplicate": duplicate,
        "source_dataset_id": entity.get("origin_dataset_id"),
        "source_vintage": entity.get("source_vintage"),
        "research_as_of": bundle.get("manifest", {}).get("as_of"),
        "legacy_attributes": legacy,
        "research_observations": observations,
        **({"research_evidence": reader.entity(identifier)} if reader else {}),
    }


def _evidence_reader(bundle):
    # Older programmatic callers supply identity-only bundles. Evidence fields
    # are optional for these callers; the CLI always uses a validated bundle.
    if "links" not in bundle:
        return None
    source = (
        Path(__file__).resolve().parents[2]
        / "src/worldenergydata/field_development/catalog_evidence.py"
    )
    spec = importlib.util.spec_from_file_location("catalog_evidence", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CatalogEvidence(bundle)


def _identity_matches(crosswalk, ids):
    accepted, possible = {}, set()
    for row in crosswalk:
        identifier = row["entity_id"]
        if identifier not in ids:
            continue
        if row["relation_type"] != "same_entity":
            if row["match_status"] != "rejected":
                possible.add(identifier)
            continue
        if row["match_status"] == "accepted":
            key = row["legacy_row_fingerprint"]
            if key in accepted and accepted[key] != identifier:
                raise ValueError("conflicting accepted atlas identities")
            accepted[key] = identifier
        elif row["match_status"] in ("pending", "conflicting"):
            possible.add(identifier)
    return accepted, possible


def extend_fields(pairs, bundle, fingerprint):
    """Merge accepted fingerprint groups; retain pending/composite identities."""
    fields = [row for row in bundle["entities"] if row["entity_type"] == "field"]
    reader = _evidence_reader(bundle)
    accepted, possible = _identity_matches(
        bundle["crosswalk"], {row["entity_id"] for row in fields}
    )
    legacy, result = defaultdict(list), []
    for source, entry in pairs:
        identifier = accepted.get(fingerprint(source))
        if identifier:
            legacy[identifier].append(dict(entry))
        else:
            result.append(entry)
    result.extend(
        _research_entry(
            row,
            bundle,
            legacy.get(row["entity_id"], []),
            row["entity_id"] in possible,
            reader,
        )
        for row in fields
    )
    counts = {
        "legacy_rows": len(pairs),
        "registered_fields": len(fields),
        "registered_nonfields": len(bundle["entities"]) - len(fields),
        "accepted_reconciled_identities": len(legacy),
        "possible_duplicates": len(possible),
        "nonfield_entities": [
            _research_entry(row, bundle, [], False, reader)
            for row in bundle["entities"]
            if row["entity_type"] != "field"
        ],
        **(
            {"state": bundle["manifest"]["state"]}
            if "state" in bundle["manifest"]
            else {}
        ),
    }
    return result, counts
