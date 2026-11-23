"""Legacy row fingerprints and owner-adjudicated crosswalk contracts."""

import importlib.util
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

require = common.require
unique = common.unique
fingerprint = common.fingerprint


def validate_ledger(ledger):
    ledger_ids = unique(ledger, "legacy_row_fingerprint")
    for group in ledger:
        require(
            type(group["multiplicity"]) is int and group["multiplicity"] > 0,
            "invalid legacy multiplicity",
        )
        require(
            group["status"] in {"matched", "legacy_only", "composite", "pending"},
            "invalid legacy status",
        )
        header = group.get("original_header", [])
        require(
            header
            and len(header) == len(set(header))
            and set(header) == set(group["attributes"]),
            "invalid legacy header",
        )
        require(
            fingerprint([group["attributes"][column] for column in header])
            == group["legacy_row_fingerprint"],
            "legacy fingerprint mismatch",
        )
    return ledger_ids


def validate_candidate(row):
    candidate = row.get("candidate_payload", {})
    require(
        candidate and fingerprint(candidate) == row["candidate_sha256"],
        "candidate fingerprint mismatch",
    )
    require(
        all(
            candidate[k] == row[k]
            for k in (
                "entity_id",
                "legacy_row_fingerprint",
                "relation_type",
                "evidence_refs",
            )
        ),
        "candidate identity mismatch",
    )
    require(
        candidate.get("match_status") in {"pending", "conflicting"},
        "match decision candidate must retain original pending/conflicting status",
    )
    return candidate


def validate_accepted(row, candidate, entities, accepted):
    require(
        row.get("approved_by") == "Vamsee" and row.get("approval_ref"),
        "accepted link requires signoff evidence",
    )
    if candidate["match_status"] == "conflicting":
        require(
            row.get("adjudication_source_refs"),
            "conflict requires adjudication evidence",
        )
    if row["relation_type"] == "same_entity":
        require(
            next(e for e in entities if e["entity_id"] == row["entity_id"])[
                "entity_type"
            ]
            == "field",
            "same_entity requires field scope",
        )
        prior = accepted.setdefault(row["legacy_row_fingerprint"], row["entity_id"])
        require(prior == row["entity_id"], "multiple accepted equivalences")


def validate_crosswalk(bundle, entity_ids, source_ids):
    ledger_ids = validate_ledger(bundle["ledger"])
    decisions = decision_index(bundle)
    keys, accepted = set(), {}
    for row in bundle["crosswalk"]:
        key = (row["entity_id"], row["legacy_row_fingerprint"], row["relation_type"])
        require(key not in keys, "duplicate crosswalk key")
        keys.add(key)
        require(
            row["entity_id"] in entity_ids
            and row["legacy_row_fingerprint"] in ledger_ids,
            "dangling crosswalk",
        )
        require(
            row["match_status"] in {"accepted", "pending", "conflicting", "rejected"},
            "invalid match status",
        )
        require(
            row["relation_type"] in {"same_entity", "constituent_of", "phase_of"},
            "invalid relation type",
        )
        require(
            set(row["evidence_refs"]) | set(row.get("adjudication_source_refs", []))
            <= source_ids,
            "unknown adjudication/evidence source",
        )
        candidate = validate_candidate(row)
        validate_decision_binding(row, candidate, decisions.get(key))
        if row["match_status"] == "accepted":
            validate_accepted(row, candidate, bundle["entities"], accepted)


def decision_key(row):
    return (row["entity_id"], row["legacy_row_fingerprint"], row["relation_type"])


def decision_index(bundle):
    decisions = bundle["match_decisions"]
    updates = {decision_key(row): row for row in decisions}
    require(len(updates) == len(decisions), "duplicate match decision")
    require(
        set(updates) <= {decision_key(row) for row in bundle["crosswalk"]},
        "unknown match decision",
    )
    return updates


def validate_decision_binding(row, candidate, decision):
    changed = row["match_status"] != candidate["match_status"] or row[
        "match_status"
    ] in {"accepted", "rejected"}
    require(not changed or decision is not None, "missing bound match decision")
    if decision is None:
        return
    require(
        decision.get("candidate_sha256") == row["candidate_sha256"],
        "stale match decision candidate digest",
    )
    require(
        decision.get("approved_by") == "Vamsee" and decision.get("approval_ref"),
        "match decision requires recorded signoff evidence",
    )
    require(
        all(
            decision.get(key) == row.get(key)
            for key in ("match_status", "approved_by", "approval_ref")
        )
        and decision.get("adjudication_source_refs", [])
        == row.get("adjudication_source_refs", []),
        "match decision disposition/signoff mismatch",
    )
