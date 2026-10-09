"""Expose typed catalog evidence without treating research as current design input."""

from collections import defaultdict


def _research_entry(entity, bundle, legacy, duplicate):
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
    }


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
            row, bundle, legacy.get(row["entity_id"], []), row["entity_id"] in possible
        )
        for row in fields
    )
    counts = {
        "legacy_rows": len(pairs),
        "registered_fields": len(fields),
        "registered_nonfields": len(bundle["entities"]) - len(fields),
        "accepted_reconciled_identities": len(legacy),
        "possible_duplicates": len(possible),
    }
    return result, counts
