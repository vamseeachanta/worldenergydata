"""Public BSEE borehole snapshot counts on registry-defined field leases.

For the headered DataFrame source, use data.loaders.well.borehole_acquirer;
see the borehole_status dataset README for the distinct loader contracts.
"""

from __future__ import annotations

import csv
import math
import re
from collections import Counter
from datetime import datetime
from typing import Any, TextIO

from worldenergydata.common.fields_registry import FieldsRegistry

COUNT_BASIS = (
    "API12 boreholes on registered Lower Tertiary field bottom leases; "
    "not geological targeting, current ownership or outstanding liability"
)
LAYOUT_URL = "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=borehole"
STATUS_URL = "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields"
# Headerless delimited source: documented aliases, not invented source headers.
# Location cells combine three fixed-layout elements; area/block cells combine two.
COLUMNS = (
    "API Well Number",
    "Well Name",
    "Well Name Suffix",
    "Operator Number",
    "Bottom Field Name Code",
    "Spud Date",
    "Bottom Lease Number",
    "RKB Elevation",
    "BH Total MD",
    "True Vertical Depth",
    "Surface N/S Distance + Code + E/W Distance + Code",
    "Surface Area + Block",
    "Bottom N/S Distance + Code + E/W Distance + Code",
    "Bottom Area + Block",
    "Total Depth Date",
    "Status Date",
    "Type Code",
    "District Code",
    "Status Code",
    "Water Depth",
    "Surface Longitude",
    "Surface Latitude",
    "Bottom Longitude",
    "Bottom Latitude",
    "Surface Lease Number",
    "Complex ID Num",
    "Structure Number",
    "Update Date",
    "Well Class Code",
)
DATE_COLUMNS = {"Spud Date", "Total Depth Date", "Status Date", "Update Date"}
INTEGER_COLUMNS = {"RKB Elevation", "BH Total MD", "True Vertical Depth", "Water Depth"}
FLOAT_COLUMNS = {
    "Surface Longitude",
    "Surface Latitude",
    "Bottom Longitude",
    "Bottom Latitude",
}
SOURCE_MASKS = {
    "BH Total MD": "#####",
    "True Vertical Depth": "#####",
    "Bottom Longitude": "################",
    "Bottom Latitude": "################",
}
STATUS_MEANINGS = {
    "APD": "Application for permit to drill",
    "AST": "Approved sidetrack",
    "BP": "Bypass",
    "CNL": "Borehole cancelled after approval",
    "COM": "Borehole completed",
    "CT": "Core test well",
    "DRL": "Drilling active",
    "DSI": "Drilling suspended",
    "PA": "Permanently abandoned",
    "ST": "Borehole side tracked",
    "TA": "Temporarily abandoned",
    "VCW": "Volume chamber well",
}


def source_schema() -> dict[str, Any]:
    """Describe observed positional cells with types and documentation aliases."""

    def cell_type(name: str) -> str:
        if name in DATE_COLUMNS:
            return "date_YYYYMMDD"
        if name in INTEGER_COLUMNS:
            return "integer_feet"
        if name in FLOAT_COLUMNS:
            return "number_degrees"
        return "string"

    return {
        "version": 1,
        "layout_url": LAYOUT_URL,
        "status_url": STATUS_URL,
        "encoding": "utf-8-sig",
        "format": "headerless quoted comma-delimited 5010.txt; 29 cells",
        "null_encoding": "whitespace or empty cell",
        "source_numeric_masks": SOURCE_MASKS,
        "mask_meaning": "Source hash mask; cause not established; retained, never numerical",
        "columns": [
            {
                "position": i,
                "alias": name,
                "type": cell_type(name),
                "nullable": name != "API Well Number",
            }
            for i, name in enumerate(COLUMNS, 1)
        ],
        "status_meanings": STATUS_MEANINGS,
    }


def _validate_cell(name: str, value: str) -> None:
    if not value:
        if name == "API Well Number":
            raise ValueError("Missing API Well Number")
        return
    if name in SOURCE_MASKS and value == SOURCE_MASKS[name]:
        return
    if name == "API Well Number" and not re.fullmatch(r"[0-9]{12}", value):
        raise ValueError("API Well Number must be a 12-digit string")
    if name in DATE_COLUMNS:
        if not re.fullmatch(r"[0-9]{8}", value):
            raise ValueError(f"Invalid {name}: expected YYYYMMDD")
        datetime.strptime(value, "%Y%m%d")
    if name in INTEGER_COLUMNS and not re.fullmatch(r"-?[0-9]+", value):
        raise ValueError(f"Invalid integer {name}")
    if name in FLOAT_COLUMNS:
        number = float(value)
        limit = 90 if "Latitude" in name else 180
        if not math.isfinite(number) or abs(number) > limit:
            raise ValueError(f"Invalid coordinate {name}")


def load_boreholes(stream: TextIO) -> list[dict[str, str]]:
    """Validate each source row, retaining identifiers as strings and blank as ''."""
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for line, cells in enumerate(csv.reader(stream, strict=True), 1):
        if len(cells) != len(COLUMNS):
            raise ValueError(f"Row {line}: expected 29 cells, got {len(cells)}")
        row = dict(zip(COLUMNS, (value.strip() for value in cells)))
        for name, value in row.items():
            try:
                _validate_cell(name, value)
            except ValueError as error:
                raise ValueError(f"Row {line}, {name}: {error}") from error
        api = row["API Well Number"]
        if api in seen:
            raise ValueError(f"Duplicate API Well Number at row {line}: {api}")
        seen.add(api)
        rows.append(row)
    if not rows:
        raise ValueError("Empty borehole source")
    return rows


def _status_meaning(code: str) -> str:
    return STATUS_MEANINGS.get(
        code, "undocumented_status_code" if code else "missing_status_code"
    )


def _attribution(
    row: dict[str, str], registry: FieldsRegistry, ids: set[str]
) -> dict[str, Any]:
    lease = row["Bottom Lease Number"]
    field_id = registry.by_lease(lease)
    reason = None
    if not lease:
        reason = "missing_bottom_lease"
    elif field_id is None:
        reason = "lease_not_in_registry"
    elif field_id not in ids:
        reason = "field_outside_lower_tertiary"
    return {
        "api12": row["API Well Number"],
        "bottom_lease": lease,
        "surface_lease": row["Surface Lease Number"],
        "field_id": field_id,
        "status_code": row["Status Code"],
        "status_date": row["Status Date"],
        "status_meaning": _status_meaning(row["Status Code"]),
        "reason": reason,
    }


def aggregate_status(
    rows: list[dict[str, str]],
    registry: FieldsRegistry,
    *,
    play_filter: str = "lower tertiary",
) -> dict[str, Any]:
    """Count API12 boreholes by bottom lease; never substitute surface lease."""
    fields = [f for f in registry.fields if play_filter.lower() in f.play.lower()]
    ids = {f.canonical_id for f in fields}
    attributed, unmatched = [], []
    counts: dict[str, Counter[str]] = {f.canonical_id: Counter() for f in fields}
    for row in rows:
        item = _attribution(row, registry, ids)
        if item["reason"]:
            unmatched.append(item)
        else:
            attributed.append(item)
            counts[item["field_id"]][item["status_code"] or "MISSING"] += 1
    summaries = []
    for field in fields:
        statuses = counts[field.canonical_id]
        summaries.append(
            {
                "field_id": field.canonical_id,
                "registered_leases": list(field.leases),
                "borehole_count": sum(statuses.values()),
                "status_counts": dict(sorted(statuses.items())),
                "availability": (
                    "boreholes_present"
                    if statuses
                    else "no_boreholes_on_registered_leases"
                ),
            }
        )
    return {
        "basis": (
            COUNT_BASIS
            if play_filter == "lower tertiary"
            else COUNT_BASIS.replace("Lower Tertiary", play_filter)
        ),
        "play_filter": play_filter,
        "masked_numeric_cells": {
            name: sum(row[name] == mask for row in rows)
            for name, mask in SOURCE_MASKS.items()
        },
        "source_boreholes": len(rows),
        "joined_boreholes": len(attributed),
        "unmatched_counts": dict(
            sorted(Counter(x["reason"] for x in unmatched).items())
        ),
        "fields": summaries,
        "attributed": attributed,
        "unmatched": unmatched,
        "status_meanings": STATUS_MEANINGS,
        "status_definitions_url": STATUS_URL,
    }
