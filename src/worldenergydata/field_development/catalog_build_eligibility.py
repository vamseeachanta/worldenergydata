"""Catalog build eligibility helpers."""

from __future__ import annotations

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

input_contract = common.input_contract


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
        _validate_eligibility_update(row, update)
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


def _validate_eligibility_update(row, update):
    if any(
        k in update and update[k] != row[k] for k in ("record_id", "table", "sha256")
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
