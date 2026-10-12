"""Strict BSEE lease layouts and lossless owner-history curation."""

from __future__ import annotations

import csv
import io
import math
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from worldenergydata.common.fields_registry import FieldsRegistry

Row = dict[str, Any]


def _value(raw: str, field: Row) -> Any:
    value = raw.strip()
    if not value:
        return None
    kind = field["type"]
    if kind == "date":
        if not re.fullmatch(r"\d{8}", value):
            raise ValueError(f"Invalid date in {field['name']}: {value}")
        return datetime.strptime(value, "%Y%m%d").date().isoformat()
    if kind == "decimal":
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"Non-finite number in {field['name']}")
        if field["name"] == "ASSIGNMENT_PCT" and not 0 <= number <= 100:
            raise ValueError("ASSIGNMENT_PCT outside percentage range")
        return number
    return value


def _record_values(record: list[str], spec: Row, line_num: int) -> list[str]:
    fields = spec["fields"]
    if spec["format"] == "fixed":
        line = record[0]
        width = max(f["start"] - 1 + f["length"] for f in fields)
        required = max(
            f["start"] - 1 + f["length"] for f in fields if f["name"] != "Filler"
        )
        if not required <= len(line) <= width:
            raise ValueError(f"Wrong fixed record width at line {line_num}")
        values = [line[f["start"] - 1 : f["start"] - 1 + f["length"]] for f in fields]
    else:
        values = record
        if len(values) != len(fields):
            raise ValueError(f"Wrong column count at line {line_num}")
        if any(len(v) > f["length"] for v, f in zip(values, fields)):
            raise ValueError(f"Column exceeds layout width at line {line_num}")
    return values


def load_table(path: Path, spec: Row) -> list[Row]:
    """Read a raw member or ZIP, validating exact source layout and scalar types."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            text = archive.read(spec["member"]).decode("cp1252")
    else:
        text = path.read_bytes().decode("cp1252")
    fields = spec["fields"]
    rows = []
    records = (
        ([line] for line in text.splitlines())
        if spec["format"] == "fixed"
        else csv.reader(io.StringIO(text), strict=True)
    )
    for line_num, record in enumerate(records, 1):
        if not record:
            raise ValueError(f"Empty record at line {line_num}")
        values = _record_values(record, spec, line_num)
        row = {
            f["name"]: _value(v, f)
            for v, f in zip(values, fields)
            if f["name"] != "Filler"
        }
        lease = row.get("LEASE_NUMBER", row.get("Lease Number"))
        if lease is not None and not re.fullmatch(r"[A-Z]?\d{5,6}", lease):
            raise ValueError(f"Invalid lease identifier at line {line_num}")
        if "ASGN_STATUS_CODE" in row and row["ASGN_STATUS_CODE"] not in {
            None,
            "C",
            "H",
            "P",
            "T",
        }:
            raise ValueError(f"Invalid assignment status at line {line_num}")
        rows.append(row)
    return rows


def registry_check(leases: list[str], registry: FieldsRegistry) -> list[Row]:
    """Report every lease; never drop an unregistered identifier."""
    return [
        {
            "lease_num": lease,
            "field_id": registry.by_lease(lease),
            "reason": (
                None
                if registry.by_lease(lease)
                else "Lease absent from canonical registry"
            ),
        }
        for lease in leases
    ]


def poster_leases(registry: FieldsRegistry) -> list[str]:
    """Select the canonical Lower Tertiary lifecycle-poster lease set."""
    return sorted(
        {
            lease
            for field in registry.fields
            if field.surfaces.get("lifecycle_poster")
            and "lower tertiary" in field.play.lower()
            for lease in field.leases
        }
    )


def _name(row: Row, companies: dict[str, str | None], key: str, prefix: str) -> Row:
    number = row.get(key)
    name = companies.get(number) if number else None
    return {
        f"{prefix}_name": name,
        f"{prefix}_name_basis": "Unique unterminated Company (All) name at retrieval",
        f"{prefix}_name_reason": (
            None
            if name
            else (
                "No unique current Company (All) name"
                if number in companies
                else (
                    "Company number absent from Company (All)"
                    if number
                    else "Company number missing in source"
                )
            )
        ),
    }


def _lease_result(
    lease: Row, owners: list[Row], operators: list[Row]
) -> tuple[Row, Row]:
    current = [row for row in owners if row["ASGN_STATUS_CODE"] == "C"]
    active_ops = [row for row in operators if row["ASGN_STATUS_CODE"] == "C"]
    operator_names = sorted(
        {row["operator_name"] for row in active_ops if row["operator_name"]}
    )
    block = lease["Block Number"]
    area_block = (lease["Area Code"] or "") + (block.zfill(3) if block else "")
    result = {
        "lease_num": lease["Lease Number"],
        "area_block": area_block,
        "status": lease["Lease Status Code"],
        "effective_date": lease["Lease Effective Date"],
        "approval_date": [row["ASGN_APRV_DATE"] for row in current],
        "operator": operator_names,
        "gwi_pct": [row["ASSIGNMENT_PCT"] for row in current],
        "royalty_system": lease["Bid System Code"],
    }
    panel = {
        "lease_num": lease["Lease Number"],
        "current_owners": current,
        "current_operators": active_ops,
        "expiration_date": lease["Lease Expiration Date"],
        "expected_expiration_date": lease["Lease Expected Expiration Date"],
        "expiration_reason": (
            None
            if lease["Lease Expiration Date"]
            else "No actual expiration date in Lease Data; expected date is distinct"
        ),
        "surface_area": lease["Current Area"],
        "surface_area_unit_code": lease["System Measure Flag"],
        "owner_reason": None if current else "No current owner rows in package",
        "operator_reason": (
            None
            if operator_names
            else "No resolved current designated operator names in package"
        ),
    }
    return result, panel


def curate(tables: dict[str, list[Row]], leases: list[str]) -> dict[str, list[Row]]:
    """Produce required lease columns and separate owner/operator history tables."""
    candidates: dict[str, set[str]] = {}
    for company in tables["company"]:
        number, name = company["MMS_COMPANY_NUM"], company["BUS_ASC_NAME"]
        candidates.setdefault(number, set())
        if company["MMS_TERM_DATE"] is None and name:
            candidates[number].add(name)
    companies = {
        number: next(iter(names)) if len(names) == 1 else None
        for number, names in candidates.items()
    }
    selected = set(leases)
    result: dict[str, list[Row]] = {
        key: [] for key in ("leases", "owners", "operators", "panel_values", "missing")
    }
    indexes: dict[str, dict[str, list[Row]]] = {"owners": {}, "operators": {}}
    for source, target in (("owner", "owners"), ("operator", "operators")):
        for row in tables[source]:
            if row["LEASE_NUMBER"] not in selected:
                continue
            enriched = dict(row, **_name(row, companies, "MMS_COMPANY_NUM", "owner"))
            if source == "operator":
                enriched.update(_name(row, companies, "OPERATOR_NUM", "operator"))
            result[target].append(enriched)
            indexes[target].setdefault(row["LEASE_NUMBER"], []).append(enriched)
    lease_index = {}
    for row in tables["lease"]:
        number = row["Lease Number"]
        if number in lease_index:
            raise ValueError(f"Duplicate lease in Lease Data: {number}")
        lease_index[number] = row
    for number in leases:
        lease = lease_index.get(number)
        if lease is None:
            result["missing"].append(
                {"lease_num": number, "reason": "Lease absent from Lease Data package"}
            )
            continue
        curated, panel = _lease_result(
            lease,
            indexes["owners"].get(number, []),
            indexes["operators"].get(number, []),
        )
        result["leases"].append(curated)
        result["panel_values"].append(panel)
    return result
