"""NSTA fields/wells metadata, with source evidence kept outside FieldConcept.

Source contract: the public layer schemas below, inspected 2026-10-20.
The observations accepted here are ArcGIS attribute dictionaries; values in a
normalized snapshot are not an engineering qualification or recommendation.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable
from datetime import datetime
from statistics import median
from typing import Any

_SERVICE_ROOT = "https://services-eu1.arcgis.com/OZMfUznmLTnWccBc/arcgis/rest/services/"
FIELDS_URL = _SERVICE_ROOT + "Offshore_hydrocarbon_fields_(WGS84)/FeatureServer/0"
WELLS_URL = (
    _SERVICE_ROOT
    + "UKCS%20offshore%20petroleum%20wells%20top%20holes%20ETRS89/FeatureServer/0"
)


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _depth(value: Any) -> float | None:
    """Metres, finite and nonnegative, per FieldConcept's physical-value contract."""
    if isinstance(value, bool):
        return None
    try:
        depth = float(value)
    except (TypeError, ValueError):
        return None
    return depth if math.isfinite(depth) and depth >= 0 else None


def _startup_year(value: Any) -> int | None:
    # PROD_DATE is a string, not an ArcGIS epoch date (fields layer schema).
    for pattern in ("%Y/%m", "%Y-%m", "%Y-%m-%d", "%Y/%m/%d", "%Y"):
        try:
            return datetime.strptime(str(value), pattern).year
        except ValueError:
            continue
    return None


def _canonical_rows(rows: Iterable[dict]) -> list[dict]:
    return sorted(
        rows, key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False)
    )


def _evidence(rows: list[dict], url: str, columns: list[str], method: str) -> dict:
    snapshot = json.dumps(
        _canonical_rows(rows),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return {
        "source_url": url,
        "source_fields": columns,
        "method": method,
        "record_ids": sorted(
            [row["OBJECTID"] for row in rows if row.get("OBJECTID") is not None],
            key=str,
        ),
        "snapshot_sha256": hashlib.sha256(snapshot.encode()).hexdigest(),
    }


def enrich_ukcs_field_metadata(
    field_name: str,
    *,
    fields: Iterable[dict] = (),
    wells: Iterable[dict] = (),
) -> dict[str, Any]:
    """Join exact, case-insensitive field names and retain coverage/provenance.

    Field DEPTH_M takes precedence. Otherwise the median of finite nonnegative
    matching WATDEP_M observations is a labelled field-depth *estimate*. This is
    a deterministic aggregation policy, not a published NSTA field measurement.
    No datum elevation or measured drilling depth is used as water depth.
    """
    name = _text(field_name)
    if name is None:
        raise ValueError("field_name must be a nonempty string")
    matches = _matching_fields(fields, name)
    meta = _base_metadata(name, matches[0] if matches else {})
    provenance = _field_provenance(meta, matches)
    if meta["water_depth_m"] is None:
        _add_well_depth(meta, provenance, name, wells)
    keys = (
        "operator",
        "field_status",
        "production_start_date",
        "discovery_date",
        "production_start_year",
        "year_first_oil",
        "ownership",
        "water_depth_m",
    )
    meta["metadata_coverage"] = {
        key: "available" if meta[key] is not None and meta[key] != [] else "missing"
        for key in keys
    }
    # No consent field is present in the inspected fields theme; do not infer
    # FID/FDP from discovery, production start or determination status.
    meta["metadata_coverage"]["fdp_consent_date"] = "NOT_EVALUATED"
    meta["metadata_provenance"] = provenance
    return meta


def _matching_fields(fields: Iterable[dict], name: str) -> list[dict]:
    matches = [
        r
        for r in fields
        if (_text(r.get("FIELDNAME")) or "").casefold() == name.casefold()
    ]
    # Multiple field polygons can repeat attributes. Conflicting records need
    # source reconciliation; OBJECTID alone does not establish precedence.
    distinct = {
        json.dumps({k: v for k, v in r.items() if k != "OBJECTID"}, sort_keys=True)
        for r in matches
    }
    if len(distinct) > 1:
        raise ValueError("Ambiguous NSTA field metadata")
    return matches


def _base_metadata(name: str, row: dict) -> dict[str, Any]:
    return {
        "field_name": name,
        "region": "uk",
        "source": "NSTA fields/wells themes",
        "operator": _text(row.get("CURR_OPER")),
        "field_status": _text(row.get("STATUS")),
        "production_start_date": _text(row.get("PROD_DATE")),
        "discovery_date": _text(row.get("DISC_DATE")),
        "production_start_year": _startup_year(row.get("PROD_DATE")),
        # Public FIELDTYPE distinct-values query (2026-10-20): OIL, GAS, COND.
        # A gas/condensate startup does not establish an oil production date.
        "year_first_oil": (
            _startup_year(row.get("PROD_DATE"))
            if row.get("FIELDTYPE") == "OIL"
            else None
        ),
        "ownership": _ownership(row),
        "water_depth_m": _depth(row.get("DEPTH_M")),
        "fdp_consent_date": None,
    }


def _ownership(row: dict) -> list[dict]:
    """Preserve raw equity; no percentage/fraction or total is inferred."""
    # NSTA fields layer schema: CURRLIC/EQUITY then CURRLIC2/EQUITY2 ... 20.
    result = []
    for index in range(1, 21):
        suffix = "" if index == 1 else str(index)
        licensee = _text(row.get("CURRLIC" + suffix))
        equity = row.get("EQUITY" + suffix)
        if isinstance(equity, str):
            equity = _text(equity)
        if licensee is not None or equity is not None:
            result.append({"licensee": licensee, "equity_raw": equity})
    return result


def _field_provenance(meta: dict, rows: list[dict]) -> dict:
    columns = {
        "operator": ["CURR_OPER"],
        "field_status": ["STATUS"],
        "production_start_date": ["PROD_DATE"],
        "discovery_date": ["DISC_DATE"],
        "year_first_oil": ["PROD_DATE", "FIELDTYPE"],
        "production_start_year": ["PROD_DATE"],
        "water_depth_m": ["DEPTH_M"],
        "ownership": [
            k for r in rows for k in r if k.startswith(("CURRLIC", "EQUITY"))
        ],
    }
    return {
        key: _evidence(
            rows,
            FIELDS_URL,
            sorted(set(names)),
            (
                "startup_year"
                if key.endswith("year") or key == "year_first_oil"
                else "source_value"
            ),
        )
        for key, names in columns.items()
        if meta[key] is not None and meta[key] != []
    }


def _add_well_depth(meta: dict, provenance: dict, name: str, wells: Iterable[dict]):
    rows = [
        r
        for r in wells
        if (_text(r.get("TARGETFLD")) or "").casefold() == name.casefold()
        and _depth(r.get("WATDEP_M")) is not None
    ]
    if rows:
        meta["water_depth_m"] = median(_depth(r["WATDEP_M"]) for r in rows)
        provenance["water_depth_m"] = _evidence(rows, WELLS_URL, ["WATDEP_M"], "median")
