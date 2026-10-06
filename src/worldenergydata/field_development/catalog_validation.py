"""Semantic checks for catalog extension artifacts, independent of hash checks."""
import hashlib
import datetime
import csv
import io
import json
import re
from collections import Counter

PRECISIONS = {"day", "month", "year", "range", "unknown", "upper_bound_day", "half_year"}
TYPES = {"field", "development", "phase", "block", "area", "host", "well", "contract_bundle"}
TYPE_MAP = {"development_system": "development", "development_phase": "phase", "development_area": "area"}
HASH = re.compile(r"^[a-f0-9]{64}$")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def unique(rows, key):
    identifiers = [row[key] for row in rows]
    require(all(identifiers) and len(identifiers) == len(set(identifiers)), "blank or duplicate identity")
    return set(identifiers)


def validate_date(row):
    precision, value = row.get('precision'), row.get('event_date')
    require(precision in PRECISIONS, 'unsupported date precision')
    require(value or precision == 'unknown', 'blank date requires unknown precision')
    if precision in {'day', 'upper_bound_day'}:
        try:
            require(isinstance(value, str) and len(value) == 10, 'invalid day date')
            datetime.date.fromisoformat(value)
        except (TypeError, ValueError):
            raise ValueError('invalid day date') from None
    patterns = {'year': r'\d{4}', 'month': r'\d{4}-(0[1-9]|1[0-2])', 'half_year': r'\d{4}-H[12]'}
    if precision in patterns:
        require(isinstance(value, str) and re.fullmatch(patterns[precision], value), 'date does not match precision')


def validate_evidence(tables):
    require(isinstance(tables, dict) and all(isinstance(rows, list) and all(isinstance(r, dict) for r in rows) for rows in tables.values()), 'invalid evidence table type')
    sources = unique(tables.get('sources', []), 'source_ref')
    for row in tables.get('milestone_observations', []):
        validate_date(row)
    for table in ('field_observations', 'cost_observations', 'milestone_observations'):
        for row in tables.get(table, []):
            require(isinstance(row.get('source_ref'), str) and row['source_ref'].strip() and row['source_ref'] in sources, 'missing source reference')
    for row in tables.get('field_observations', []):
        require(all(isinstance(row.get(k), str) and row[k].strip() for k in ('entity_id', 'name', 'country')), 'invalid field identity/name/country')
        require(TYPE_MAP.get(row.get('entity_type'), row.get('entity_type')) in TYPES, 'unsupported entity scope')
        require(row.get('current_configuration_verified') is False, 'snapshot cannot assert verified current configuration')
    for row in tables.get('cost_observations', []):
        require(row.get('scope_type') in {'project', 'block', 'contract_bundle'}, 'unsupported cost scope')
        require(all(isinstance(row.get(k), str) and row[k].strip() for k in ('cost_id', 'entity_or_scope', 'unit')), 'invalid cost identity/unit')
        require(type(row.get('value')) in {int, float} and row['value'] >= 0, 'invalid cost value')
    for row in tables.get('inherited_cost_records', []):
        require(all(isinstance(row.get(k), str) and row[k].strip() for k in ('project', 'source_url')), 'invalid inherited parent identity')


def decode_csv(rows):
    json_fields = {"attributes", "evidence_refs", "source_refs", "dependencies", "adjudication_source_refs", "original_header", "candidate_payload"}
    for row in rows:
        for key in json_fields & row.keys():
            row[key] = json.loads(row[key]) if row[key] else []
        for key in {"multiplicity", "schema_version"} & row.keys():
            row[key] = int(row[key])
        for key in {"supplemental", "current_configuration_verified"} & row.keys():
            require(row[key] in {"True", "False", ""}, "invalid Boolean")
            row[key] = row[key] == "True"
    return rows


def parsed_csv(raw):
    if not raw:
        return []
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
    rows = list(reader)
    header = reader.fieldnames
    require(header and len(header) == len(set(header)) and not any(None in r or None in r.values() for r in rows), "invalid CSV header/row width")
    return decode_csv(rows)


def validate_manifest(manifest, expected_files):
    require(manifest.get("dataset_id") == "angola-field-development-evidence", "invalid dataset identity")
    require(manifest.get("schema_version") == 1, "unsupported schema version")
    require(manifest.get("state") in {"local_draft_not_for_publication", "eligible_derived_export"}, "invalid publication state")
    require(manifest.get("readiness") == "partial_research_only", "invalid readiness")
    require(set(manifest.get("output_hashes", {})) == expected_files, "missing or unexpected output pin")
    expected_inputs = {name + ".json" for name in ("sources", "field_observations", "cost_observations", "milestone_observations", "inherited_cost_records")} | {"legacy_catalog", "inherited_cost_parent", "original_manifest"}
    require(set(manifest.get("input_hashes", {})) == expected_inputs, "missing or unexpected input pin")
    hashes = list(manifest["output_hashes"].values()) + list(manifest["input_hashes"].values()) + [manifest.get("decision_sha256"), manifest.get("eligibility_sha256")]
    require(all(isinstance(value, str) and HASH.fullmatch(value) for value in hashes), "invalid digest")
    require(all(type(v) is int and v >= 0 for v in manifest.get("counts", {}).values()), "invalid record counts")


def validate_links(bundle, entity_ids, source_ids):
    records = bundle["links"]["records"]
    ids = unique(records, "record_id")
    parent_ids = unique(bundle["links"]["parent_references"], "record_id")
    parents = {r["record_id"]: r for r in bundle["links"]["parent_references"]}
    for row in records:
        require(row.get("entity_id") is None or row["entity_id"] in entity_ids, "dangling entity foreign key")
        require(set(row["dependencies"]) <= ids | parent_ids, "dangling dependency")
        require(type(row["multiplicity"]) is int and row["multiplicity"] > 0, "invalid record multiplicity")
        if row['table'] == 'inherited_cost_records':
            require(row.get('link_status') == 'parent_reference' and row.get('parent_record_id') in parent_ids and row['parent_record_id'] in row['dependencies'], 'inherited cost missing parent reference')
            parent = parents[row['parent_record_id']]
            require(parent.get('table') == 'parent_reference' and row.get('parent_row_fingerprint') == parent.get('sha256') and parent['record_id'] == 'sanctioned_projects:row:' + parent['sha256'], 'inherited parent fingerprint mismatch')
        elif row['table'] != 'sources':
            require(any(d in ids and d.startswith(bundle['manifest']['dataset_id'] + ':sources:') for d in row['dependencies']), 'missing source dependency')
    for entity in bundle["entities"]:
        require(entity["evidence_record_id"] in ids and entity["source_ref"] in source_ids, "dangling entity evidence/source")
    return ids


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_record_closure(bundle):
    expected = {}
    dataset = bundle["manifest"]["dataset_id"]
    for table, rows in bundle["evidence"].items():
        for row in rows:
            explicit = next((row[k] for k in ("entity_id", "cost_id", "source_ref") if k in row and (k != "source_ref" or table == "sources")), None)
            identifier = f"{dataset}:{table}:{explicit or fingerprint(row)}"
            digest = fingerprint(row)
            prior, count = expected.get(identifier, (digest, 0))
            require(prior == digest, "evidence identity collision")
            expected[identifier] = (digest, count + 1)
    records = bundle["links"]["records"]
    actual = {r["record_id"]: (r["sha256"], r["multiplicity"]) for r in records}
    require(actual == expected, "evidence/link content closure mismatch")
    require(bundle["manifest"]["supplemental_entity_count"] == sum(bool(e.get("supplemental")) for e in bundle["entities"]), "supplemental count mismatch")
    require(bundle["manifest"]["legacy_row_count"] == sum(r["multiplicity"] for r in bundle["ledger"]), "legacy count mismatch")
    require(bundle["manifest"]["decision_sha256"] == fingerprint(bundle["match_decisions"]), "decision digest mismatch")
    require(bundle["manifest"]["eligibility_sha256"] == fingerprint(bundle["eligibility"]), "eligibility digest mismatch")


def validate_crosswalk(bundle, entity_ids, source_ids):
    ledger_ids = unique(bundle["ledger"], "legacy_row_fingerprint")
    for group in bundle["ledger"]:
        require(type(group["multiplicity"]) is int and group["multiplicity"] > 0, "invalid legacy multiplicity")
        require(group["status"] in {"matched", "legacy_only", "composite", "pending"}, "invalid legacy status")
        header = group.get("original_header", [])
        require(header and len(header) == len(set(header)) and set(header) == set(group["attributes"]), "invalid legacy header")
        require(fingerprint([group["attributes"][column] for column in header]) == group["legacy_row_fingerprint"], "legacy fingerprint mismatch")
    keys, accepted = set(), {}
    for row in bundle["crosswalk"]:
        key = (row["entity_id"], row["legacy_row_fingerprint"], row["relation_type"])
        require(key not in keys, "duplicate crosswalk key")
        keys.add(key)
        require(row["entity_id"] in entity_ids and row["legacy_row_fingerprint"] in ledger_ids, "dangling crosswalk")
        require(row["match_status"] in {"accepted", "pending", "conflicting", "rejected"}, "invalid match status")
        require(row["relation_type"] in {"same_entity", "constituent_of", "phase_of"}, "invalid relation type")
        require(set(row["evidence_refs"]) | set(row.get("adjudication_source_refs", [])) <= source_ids, "unknown adjudication/evidence source")
        candidate = row.get("candidate_payload", {})
        require(candidate and fingerprint(candidate) == row["candidate_sha256"], "candidate fingerprint mismatch")
        require(all(candidate[k] == row[k] for k in ("entity_id", "legacy_row_fingerprint", "relation_type", "evidence_refs")), "candidate identity mismatch")
        if row["match_status"] == "accepted":
            require(row.get("approved_by") == "Vamsee" and row.get("approval_ref"), "accepted link requires signoff evidence")
            if candidate["match_status"] == "conflicting":
                require(row.get("adjudication_source_refs"), "conflict requires adjudication evidence")
            if row["relation_type"] == "same_entity":
                require(next(e for e in bundle["entities"] if e["entity_id"] == row["entity_id"])["entity_type"] == "field", "same_entity requires field scope")
                prior = accepted.setdefault(row["legacy_row_fingerprint"], row["entity_id"])
                require(prior == row["entity_id"], "multiple accepted equivalences")


def validate_relationships(bundle, entity_ids, source_ids, record_ids):
    unique(bundle["relationships"], "relationship_id")
    for row in bundle["relationships"]:
        require(row["subject_entity_id"] in entity_ids and row["object_entity_id"] in entity_ids, "dangling relationship")
        require(row["predicate"] in {"part_of", "phase_of", "located_in", "hosted_by"}, "invalid relationship predicate")
        require(row["status"] in {"supported", "conflicting", "unresolved"}, "invalid relationship status")
        require(row["date_precision"] in PRECISIONS, "invalid relationship precision")
        require(row.get("effective_date") or row["date_precision"] == "unknown", "blank relationship date")
        require(set(row["source_refs"]) <= source_ids and set(row.get("dependencies", [])) <= record_ids, "dangling relationship evidence")


def validate_bundle(bundle):
    entities = bundle["entities"]
    ids = unique(entities, "entity_id")
    sources = unique(bundle["evidence"]["sources"], "source_ref")
    for row in entities:
        require(row.get("primary_name", "").strip() and row["entity_type"] in TYPES, "invalid entity name/type")
        require(row["readiness"] == "partial_research_only" and row["current_configuration_verified"] is False, "invalid entity readiness")
    manifest = bundle["manifest"]
    require(manifest["registry_entity_count"] == len(entities), "registry count mismatch")
    require(manifest["research_entity_count"] == sum(not e.get("supplemental") for e in entities), "research count mismatch")
    require(manifest["entity_counts"] == dict(Counter(e["entity_type"] for e in entities)), "entity type count mismatch")
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
    require(set(source_counts) == set(bundle["evidence"]) | {"parent_reference"}, "missing eligibility source counts")
    exported_counts = dict(bundle["manifest"]["counts"], parent_reference=len(bundle["links"]["parent_references"]))
    deferred = bundle["manifest"].get("deferred_counts", {})
    require(set(deferred) <= set(source_counts), "unexpected deferred table")
    require(all(type(count) is int and count >= 0 and count == exported_counts[table] + deferred.get(table, 0) for table, count in source_counts.items()), "export/deferred count closure mismatch")
    for row in records:
        decision = by_id.get(row["record_id"], {})
        require(decision.get("decision") in {"eligible_factual_derivative", "permission_granted"}, "missing publication eligibility")
        require(decision.get("reviewer") == "Vamsee" and decision.get("approval_ref") and decision.get("basis"), "missing owner eligibility evidence")
        require(decision.get("reviewed_sha256") == row["sha256"], "stale eligibility digest")
        if decision["decision"] == "permission_granted":
            require(decision.get("permission_ref"), "missing eligibility permission evidence")
