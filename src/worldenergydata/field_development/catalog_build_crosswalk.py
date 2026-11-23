"""Catalog build crosswalk helpers."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

if __package__:
    from . import catalog_build_common as common
else:
    _spec = importlib.util.spec_from_file_location(
        "catalog_build_common", Path(__file__).with_name("catalog_build_common.py")
    )
    common = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(common)

row_fingerprint = common.row_fingerprint


def build_crosswalk(entities, observations, ledger, decisions):
    validate_decision_scopes(entities, decisions)
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
            row = _crosswalk_candidate(entity, obs, group, old, status, relation)
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
        _validate_match_update(row, update, accepted)
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


def _crosswalk_candidate(entity, obs, group, old, status, relation):
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
    return row


def _validate_match_update(row, update, accepted):
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


def validate_decision_scopes(entities, decisions):
    scopes = {row["entity_id"]: row["entity_type"] for row in entities}
    for decision in decisions:
        if (
            decision.get("match_status") == "accepted"
            and decision.get("relation_type") == "same_entity"
            and scopes.get(decision.get("entity_id")) != "field"
        ):
            raise ValueError("same_entity requires field scope")
