"""Multi-source vessel fleet deduplication and merge."""

from __future__ import annotations

import logging
from typing import Any, Optional

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
    # Off-repo brochure-digitized sources: trusted for specs, but their IMOs
    # are lower-trust than the curated WED contractor-fleet records, so they
    # sit *below* the contractor_*_fleet curated tags on IMO conflicts.
    "acma_msiv_md": 4,
    "frontier_heavy_lift_csv": 4,
    "frontier_pipelay_csv": 4,
    "contractor_fleet_page": 5,
    "contractor_fsr": 5,
    "contractor_spec_pdf": 6,
    "manual": 7,
}

# Curated WED construction-fleet provenance tags (as they appear in the
# committed ``construction_vessels.csv``). These carry the canonical IMO and
# must out-prioritise the off-repo brochure sources on IMO conflicts.
_CURATED_FLEET_PRIORITY: int = 8
for _curated in (
    "heerema_fleet",
    "allseas_fleet",
    "saipem_fleet",
    "subsea7_fleet",
    "mcdermott_fleet",
    "technipfmc_fleet",
):
    _SOURCE_PRIORITY[_curated] = _CURATED_FLEET_PRIORITY


def deduplicate_fleet(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate vessel records using IMO + normalized name.

    Merge strategy: Most-populated record wins per field, with source
    priority used as tiebreaker.

    A normalized-name fallback also reconciles records that describe the same
    vessel under *conflicting* IMO numbers (e.g. a stale brochure IMO vs. the
    canonical registry IMO): these are merged into a single vessel rather than
    silently duplicated, and the conflict is logged. See
    :func:`deduplicate_fleet_with_report` to capture the conflicts.
    """
    merged, _conflicts = deduplicate_fleet_with_report(records)
    return merged


def deduplicate_fleet_with_report(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deduplicate and also return a list of IMO-conflict reports.

    Each conflict report is a dict::

        {
            "VESSEL_NAME": <normalized name>,
            "kept_imo": <IMO retained on the merged vessel>,
            "discarded_imos": [<other IMOs seen for this name>],
            "sources": [<DATA_SOURCE values involved>],
        }

    The retained IMO is chosen by source priority (highest wins), which keeps
    the canonical / higher-trust IMO and demotes brochure-derived ones. No IMO
    is ever invented.
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

    # Merge IMO groups
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

    # Reconcile vessels that share a normalized name but carry conflicting IMOs.
    merged, conflicts = _reconcile_name_collisions(merged)

    merged.extend(orphans)

    logger.info(
        "Dedup: %d records → %d unique vessels (%d IMO conflicts reconciled)",
        len(records),
        len(merged),
        len(conflicts),
    )
    return merged, conflicts


def _reconcile_name_collisions(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge records that share a normalized name but differ by IMO.

    For each colliding group the retained IMO is the one from the
    highest-priority source. The merge otherwise follows the standard
    field-merge rules but the kept IMO is forced onto the result so a lower
    priority record cannot overwrite it via the generic merge.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for rec in records:
        name = normalize_vessel_name(rec.get("VESSEL_NAME"))
        if not name:
            # Keep unnamed records as-is under unique keys.
            key = f"__unnamed__{id(rec)}"
            groups[key] = [rec]
            order.append(key)
            continue
        if name not in groups:
            groups[name] = []
            order.append(name)
        groups[name].append(rec)

    out: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    for key in order:
        group = groups[key]
        if len(group) == 1:
            out.append(group[0])
            continue

        imos = {r.get("IMO_NUMBER") for r in group if r.get("IMO_NUMBER")}
        merged = _merge_records(group)

        if len(imos) > 1:
            # Conflicting IMOs for the same vessel name. Keep the IMO from the
            # highest-priority source and flag the rest.
            kept_imo = _highest_priority_imo(group)
            if kept_imo is not None:
                merged["IMO_NUMBER"] = kept_imo
            discarded = sorted(i for i in imos if i != kept_imo)
            conflict = {
                "VESSEL_NAME": key,
                "kept_imo": kept_imo,
                "discarded_imos": discarded,
                "sources": sorted(
                    {str(r.get("DATA_SOURCE")) for r in group if r.get("DATA_SOURCE")}
                ),
            }
            conflicts.append(conflict)
            logger.warning(
                "IMO conflict for '%s': kept %s, discarded %s (sources: %s)",
                key,
                kept_imo,
                discarded,
                conflict["sources"],
            )

        out.append(merged)

    return out, conflicts


def _highest_priority_imo(records: list[dict[str, Any]]) -> Optional[str]:
    """Return the IMO from the highest-priority source in the group."""
    best_imo: Optional[str] = None
    best_priority = -1
    for rec in records:
        imo = rec.get("IMO_NUMBER")
        if not imo:
            continue
        priority = _SOURCE_PRIORITY.get(rec.get("DATA_SOURCE", ""), 0)
        if priority > best_priority:
            best_priority = priority
            best_imo = imo
    return best_imo


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
