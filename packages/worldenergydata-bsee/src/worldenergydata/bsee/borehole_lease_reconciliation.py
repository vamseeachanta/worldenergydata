"""Reconcile caller-supplied borehole attribution and dated lease snapshots.

Presence on a bottom lease is neither current ownership nor a plugging obligation.
Registry evidence is compared as recorded; no current registry is loaded. Digests
and retrieval times are caller-supplied claims, not authenticated source bytes.
"""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime
from typing import Any

from worldenergydata.common.fields_registry import normalize_lease

DISPOSITIONS = (
    "agreement",
    "lease_absent_from_snapshot",
    "field_assignment_conflict",
    "missing_identity",
    "registry_basis_unverified",
)


def _provenance_time(provenance: dict[str, Any]) -> datetime:
    if (
        not isinstance(provenance.get("source_id"), str)
        or not provenance["source_id"].strip()
    ):
        raise ValueError("source_id must be a nonblank string")
    for key in ("source_sha256", "registry_sha256"):
        digest = provenance.get(key)
        if key == "registry_sha256" and digest in (None, ""):
            continue  # Missing registry evidence is reported, never inferred.
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"{key} must be a lowercase SHA-256 digest")
    try:
        instant = datetime.fromisoformat(provenance["source_retrieved_at_utc"])
        if instant.utcoffset() is None:
            raise ValueError("timezone required")
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "source_retrieved_at_utc requires an aware timestamp"
        ) from error
    return instant


def _lease(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("Lease identifiers must be strings")
    return normalize_lease(value)


def _index(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    index = {}
    for row in rows:
        key = _lease(row.get("lease_num"))
        if not key:
            raise ValueError(f"Missing {label} identifier")
        if key in index:
            raise ValueError(f"Duplicate {label}")
        index[key] = row
    return index


def reconcile_borehole_leases(
    boreholes: list[dict[str, Any]],
    leases: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    *,
    borehole_provenance: dict[str, Any],
    lease_provenance: dict[str, Any],
) -> dict[str, Any]:
    """Return one disposition per API12, sorted by the full identifier.

    Rows use the existing attributed.json, leases.json and registry.json keys.
    Provenance requires source_id, source_sha256 and source_retrieved_at_utc;
    registry_sha256 may be absent. Different registry digests cannot establish
    agreement; an observed field conflict remains a conflict across vintages.
    Unknown statuses are retained verbatim and never converted to obligations.
    Missing bottom leases never fall back to surface leases. No I/O occurs.
    """
    borehole_time = _provenance_time(borehole_provenance)
    lease_time = _provenance_time(lease_provenance)
    digests = [
        p.get("registry_sha256") for p in (borehole_provenance, lease_provenance)
    ]
    basis = (
        "missing"
        if not all(digests)
        else ("matching" if digests[0] == digests[1] else "different")
    )
    lease_index = _index(leases, "normalized lease")
    registry_index = _index(registry, "normalized registry lease")
    seen = set()
    for row in boreholes:
        api = row.get("api12")
        if not isinstance(api, str) or not re.fullmatch(r"[0-9]{12}", api):
            raise ValueError("API12 must be a 12-digit string")
        if api in seen:
            raise ValueError("Duplicate API12")
        seen.add(api)

    counts = dict.fromkeys(DISPOSITIONS, 0)
    records = []
    for row in sorted(boreholes, key=lambda item: item["api12"]):
        bottom = _lease(row.get("bottom_lease"))
        mapping = registry_index.get(bottom)
        lease_field = mapping.get("field_id") if mapping is not None else None
        field = row.get("field_id")
        disposition = "missing_identity"
        if not bottom:
            reason = "missing_bottom_lease"
        elif not isinstance(field, str) or not field.strip():
            reason = "missing_borehole_field_id"
        elif bottom not in lease_index:
            disposition = reason = "lease_absent_from_snapshot"
        elif mapping is None:
            reason = "missing_registry_mapping"
        elif (
            not isinstance(lease_field, str)
            or not lease_field.strip()
            or mapping.get("reason")
        ):
            reason = "unresolved_registry_mapping"
        elif lease_field != field:
            disposition = reason = "field_assignment_conflict"
        elif basis != "matching":
            disposition = "registry_basis_unverified"
            reason = f"{basis}_registry_basis"
        else:
            disposition, reason = "agreement", "bottom_lease_and_field_agree"
        item = deepcopy(row)
        item.update(
            attribution_reason=row.get("reason"),
            normalized_bottom_lease=bottom,
            lease_field_id=deepcopy(lease_field),
            disposition=disposition,
            reason=reason,
        )
        records.append(item)
        counts[disposition] += 1
    return {
        "records": records,
        "summary": {
            "input_boreholes": len(boreholes),
            "availability": "records_present" if boreholes else "empty_input",
            "disposition_counts": counts,
        },
        "registry_basis": basis,
        "different_retrieval_times": borehole_time != lease_time,
        "provenance": {
            "verification": "caller_supplied_not_authenticated",
            "boreholes": deepcopy(borehole_provenance),
            "leases": deepcopy(lease_provenance),
        },
    }
