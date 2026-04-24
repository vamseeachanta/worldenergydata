"""Multi-source vessel fleet deduplication and merge."""

from __future__ import annotations

import logging
from typing import Any

from worldenergydata.vessel_fleet.dedup.normalizer import normalize_vessel_name

logger = logging.getLogger(__name__)

# Source priority: higher index = higher priority (wins on merge conflicts)
_SOURCE_PRIORITY: dict[str, int] = {
    "bsee_war": 1,
    "boem": 2,
    "baker_hughes": 2,
    "equasis": 3,
    "abs_register": 3,
    "dnv_register": 3,
    "lloyd_register": 3,
    "xls_historical": 4,
    "contractor_fleet_page": 5,
    "contractor_fsr": 5,
    "contractor_spec_pdf": 6,
    "manual": 7,
}


def deduplicate_fleet(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate vessel records using IMO + normalized name.

    Merge strategy: Most-populated record wins per field, with source
    priority used as tiebreaker.

    Returns a new list of deduplicated records.
    """
    # Index by IMO number (primary key)
    by_imo: dict[str, list[dict[str, Any]]] = {}
    # Index by normalized name (fallback key)
    by_name: dict[str, list[dict[str, Any]]] = {}
    # Records without either key
    orphans: list[dict[str, Any]] = []

    for record in records:
        imo = record.get("IMO_NUMBER")
        name = normalize_vessel_name(record.get("VESSEL_NAME"))

        if imo:
            by_imo.setdefault(imo, []).append(record)
        elif name:
            by_name.setdefault(name, []).append(record)
        else:
            orphans.append(record)

    # Merge groups
    merged: list[dict[str, Any]] = []

    for imo, group in by_imo.items():
        merged.append(_merge_records(group))

    # Check if any name-indexed records match IMO-indexed ones
    imo_names = {
        normalize_vessel_name(r.get("VESSEL_NAME"))
        for r in merged
        if r.get("VESSEL_NAME")
    }

    for name, group in by_name.items():
        if name in imo_names:
            # Find the IMO record and merge into it
            for m in merged:
                if normalize_vessel_name(m.get("VESSEL_NAME")) == name:
                    merged_record = _merge_records([m] + group)
                    m.update(merged_record)
                    break
        else:
            merged.append(_merge_records(group))

    merged.extend(orphans)

    logger.info(
        "Dedup: %d records → %d unique vessels",
        len(records),
        len(merged),
    )
    return merged


def _merge_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple records for the same vessel.

    For each field, prefer the value from the highest-priority source.
    If priorities are equal, prefer the non-None value.
    """
    if len(records) == 1:
        return dict(records[0])

    # Sort by source priority (highest priority last → wins)
    sorted_records = sorted(
        records,
        key=lambda r: _SOURCE_PRIORITY.get(
            r.get("DATA_SOURCE", ""),
            0,
        ),
    )

    merged: dict[str, Any] = {}
    for record in sorted_records:
        for key, value in record.items():
            if value is not None:
                merged[key] = value

    return merged
