"""Typed public Atlas exports and auditable attribution without network I/O."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from worldenergydata.common.fields_registry import (
    FieldsRegistry,
    normalize_lease,
    normalize_name,
)

TABLES = ("2023sands", "2023plays", "2023chronozones")
Row = dict[str, Any]


def _convert(value: str, kind: str) -> Any:
    if not value:
        return None
    if kind == "identifier":
        try:
            identifier = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("invalid numeric identifier") from error
        if (
            not identifier.is_finite()
            or identifier < 0
            or identifier != identifier.to_integral()
        ):
            raise ValueError("identifier must contain nonnegative integer digits")
        return str(int(identifier))
    if kind == "number":
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite number")
        return number
    if kind == "datetime":
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").isoformat()
    return value


def load_table(path: Path, table: str, schema_path: Path) -> list[Row]:
    """Require exact source headers and validate all non-null cells."""
    columns = json.loads(schema_path.read_text())["tables"][table]
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != [column["name"] for column in columns]:
            raise ValueError(f"{table}: columns differ from the recorded schema")
        for line, raw in enumerate(reader, 2):
            if None in raw or None in raw.values():
                raise ValueError(f"{table} row {line}: wrong column count")
            row: Row = {"_csv_row": line}
            for column in columns:
                name = column["name"]
                try:
                    row[name] = _convert(raw[name], column["type"])
                except ValueError as error:
                    raise ValueError(f"{table} row {line} {name}: {error}") from error
            rows.append(row)
    return rows


def load_atlas(directory: Path, schema_path: Path) -> dict[str, list[Row]]:
    return {
        table: load_table(directory / f"{table}.csv", table, schema_path)
        for table in TABLES
    }


def _block(value: str | None) -> str | None:
    match = re.fullmatch(r"([A-Z]{2})\s*(\d{1,4})", (value or "").strip().upper())
    return match[1] + match[2].zfill(3) if match else None


def _lookup(rows: list[Row], key: str) -> dict[str, Row]:
    result = {}
    for row in rows:
        if not row[key] or row[key] in result:
            raise ValueError(f"missing or duplicate lookup key: {key}")
        result[row[key]] = row
    return result


def _identity(
    field: Row, registry: FieldsRegistry | None
) -> tuple[str | None, set[str]]:
    field_id = registry.resolve(field["name"]) if registry else None
    registered = registry.by_id(field_id) if registry and field_id else None
    blocks = set(registered.area_blocks) if registered else set()
    if not blocks:
        block = _block(field.get("block"))
        if block:
            blocks.add(block)
    return field_id, blocks


def _candidates(sands: list[Row], plays: dict[str, Row], zones: dict[str, Row]) -> Row:
    numbers = sorted({s["PLAY_NUM"] for s in sands if s["PLAY_NUM"]})
    codes = sorted({s["CHRONOZONE"] for s in sands if s["CHRONOZONE"]})
    missing = any(n not in plays for n in numbers) or any(c not in zones for c in codes)
    missing = missing or any(not s["PLAY_NUM"] or not s["CHRONOZONE"] for s in sands)
    conflict = any(
        s["PLAY_NUM"] in plays
        and (
            plays[s["PLAY_NUM"]]["CHRONOZONE"] != s["CHRONOZONE"]
            or plays[s["PLAY_NUM"]]["PLAY"] != s["PLAY_NAME"]
        )
        for s in sands
    )
    return {
        "plays": [
            {
                "number": n,
                "code": plays.get(n, {}).get("PLAY"),
                "description": plays.get(n, {}).get("PLAY_NAME_DESCRIPTION"),
            }
            for n in numbers
        ],
        "chronozones": [
            {"code": c, "description": zones.get(c, {}).get("CHRONOZONE_DESCRIPTION")}
            for c in codes
        ],
        "qualifiers": (["multiple_plays"] if len(numbers) > 1 else [])
        + (["missing_lookup"] if missing else [])
        + (["inconsistent_lookup"] if conflict else []),
        "sand_rows": [
            {
                "csv_row": s["_csv_row"],
                "sn_formsand": s["SN_FORMSAND"],
                "sand_name": s["SAND_NAME"],
                "boem_field": s["BOEM_FIELD"],
                "play_number": s["PLAY_NUM"],
                "chronozone": s["CHRONOZONE"],
            }
            for s in sands
        ],
    }


def _unmatched_reason(verified: str | None, codes: set[str]) -> str:
    if not codes:
        return "missing_parseable_area_block"
    return (
        "no_sand_rows_for_verified_boem_field"
        if verified
        else "no_sand_rows_for_area_block"
    )


def public_xref_evidence(
    rows: list[Row], registry: FieldsRegistry
) -> tuple[dict[str, str], list[Row]]:
    """Use only unique codes linked by independent public lease/block pairs."""
    codes = {}
    public_rows: list[Row] = []
    for field in registry.fields:
        matched = []
        for row in rows:
            block = _block(
                (row.get("AREA_CODE") or "") + (row.get("BLOCK_NUMBER") or "")
            )
            code = row.get("BOEM_FIELD")
            if (
                code
                and block
                and block != code
                and block in field.area_blocks
                and normalize_lease(row.get("LEASE") or "") in field.leases
            ):
                matched.append(row)
        unique = {row["BOEM_FIELD"] for row in matched}
        if len(unique) == 1:
            codes[field.canonical_id] = next(iter(unique))
            public_rows.extend(
                {
                    "BOEM_FIELD": row["BOEM_FIELD"],
                    "LEASE_NUMBER": row["LEASE"],
                    "AREA_BLOCK": row["AREA_CODE"] + row["BLOCK_NUMBER"],
                    "_source": "2023xref_oper-comp",
                    "_lease_block_source": "2023xref_oper-comp.LEASE/AREA_CODE/BLOCK_NUMBER",
                }
                for row in matched
            )
    return codes, public_rows


def _identity_evidence(
    field: Row,
    field_id: str | None,
    registry: FieldsRegistry | None,
    verified: str | None,
    sands: list[Row],
    public_rows: list[Row],
) -> Row:
    code_match = bool(verified and any(s["BOEM_FIELD"] == verified for s in sands))
    evidence = {
        "code_match": {
            "value": code_match if verified else "not-available",
            "source_field": "2023sands.BOEM_FIELD" if verified else None,
        },
        "name_match": {"value": "not-available", "source_field": None},
        "lease_block_match": {"value": "not-available", "source_field": None},
    }
    registered = registry.by_id(field_id) if registry and field_id else None
    names = {normalize_name(field["name"])}
    if registered:
        names.update(
            normalize_name(n) for n in (registered.display_name, *registered.aliases)
        )
    for row in public_rows:
        if (
            not code_match
            or row.get("BOEM_FIELD") != verified
            or not row.get("_source")
        ):
            continue
        if row.get("FIELD_NAME"):
            value = normalize_name(row["FIELD_NAME"]) in names
            _record_evidence(
                evidence, "name_match", value, row["_source"] + ".FIELD_NAME"
            )
        if row.get("LEASE_NUMBER") and row.get("AREA_BLOCK") and registered:
            value = _lease_block_matches(row, verified, registered)
            source = row.get(
                "_lease_block_source", row["_source"] + ".LEASE_NUMBER/AREA_BLOCK"
            )
            _record_evidence(evidence, "lease_block_match", value, source)
    return evidence


def _lease_block_matches(row: Row, verified: str | None, registered: Any) -> bool:
    block = _block(row["AREA_BLOCK"])
    return bool(
        block
        and block != verified
        and block in registered.area_blocks
        and normalize_lease(row["LEASE_NUMBER"]) in registered.leases
    )


def _record_evidence(evidence: Row, key: str, value: bool, source: str) -> None:
    # Keep the source of a successful confirmation when other rows disagree.
    if evidence[key]["value"] is not True:
        evidence[key] = {"value": value, "source_field": source}


def attribute_fields(
    atlas: dict[str, list[Row]],
    roster: list[Row],
    registry: FieldsRegistry | None,
    boem_field_codes: dict[str, str] | None = None,
    public_field_rows: list[Row] | None = None,
) -> list[Row]:
    """Require exact code plus public name or independent lease/block agreement.

    Public evidence rows must cite their source in _source. A code alone and
    blocks equal to that code cannot confirm identity. No crosswalk is inferred.
    """
    plays = _lookup(atlas["2023plays"], "PLAY_NUMBER")
    zones = _lookup(atlas["2023chronozones"], "BOEM_CHRONOZONE")
    by_field: dict[str, list[Row]] = defaultdict(list)
    for sand in atlas["2023sands"]:
        by_field[sand["BOEM_FIELD"]].append(sand)
    gulf = [f for f in roster if f.get("region") == "US Gulf of Mexico"]
    block_counts = Counter(b for f in gulf for b in _identity(f, registry)[1])
    results = []
    for field in gulf:
        if field.get("play") is not None:
            continue
        results.append(
            _attribute_field(
                field,
                registry,
                boem_field_codes,
                public_field_rows,
                by_field,
                plays,
                zones,
                block_counts,
            )
        )
    return results


def _attribute_field(
    field: Row,
    registry: FieldsRegistry | None,
    boem_field_codes: dict[str, str] | None,
    public_field_rows: list[Row] | None,
    by_field: dict[str, list[Row]],
    plays: dict[str, Row],
    zones: dict[str, Row],
    block_counts: Counter,
) -> Row:
    field_id, blocks = _identity(field, registry)
    verified = (boem_field_codes or {}).get(field_id or "")
    codes = {verified} if verified else blocks
    sands = [s for code in sorted(codes) for s in by_field.get(code, [])]
    evidence = _identity_evidence(
        field, field_id, registry, verified, sands, public_field_rows or []
    )
    confirmed = evidence["code_match"]["value"] is True and any(
        evidence[key]["value"] is True for key in ("name_match", "lease_block_match")
    )
    result = {
        "name": field["name"],
        "field_id": field_id,
        "join_codes": sorted(codes),
        "join_basis": (
            "confirmed_boem_field"
            if confirmed
            else "unconfirmed_boem_field" if verified else "area_block_candidate"
        ),
        "evidence": evidence,
        "unmatched_reason": None,
        **_candidates(sands, plays, zones),
    }
    if not sands:
        result["status"] = "unmatched"
        result["unmatched_reason"] = _unmatched_reason(verified, codes)
    else:
        if not confirmed:
            result["qualifiers"].append("unverified_field_identity")
        if not confirmed and any(block_counts[b] > 1 for b in blocks):
            result["qualifiers"].append("shared_roster_block")
        result["status"] = "ambiguous" if result["qualifiers"] else "attributed"
    return result
