"""Evidence row contracts and CSV decoding."""

import csv
import datetime
import importlib.util
import io
import json
import re
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

PRECISIONS = common.PRECISIONS
TYPE_MAP = common.TYPE_MAP
TYPES = common.TYPES
require = common.require
unique = common.unique


def validate_date(row):
    precision, value = row.get("precision"), row.get("event_date")
    require(precision in PRECISIONS, "unsupported date precision")
    require(value or precision == "unknown", "blank date requires unknown precision")
    if precision in {"day", "upper_bound_day"}:
        try:
            require(isinstance(value, str) and len(value) == 10, "invalid day date")
            datetime.date.fromisoformat(value)
        except (TypeError, ValueError):
            raise ValueError("invalid day date") from None
    patterns = {
        "year": r"\d{4}",
        "month": r"\d{4}-(0[1-9]|1[0-2])",
        "half_year": r"\d{4}-H[12]",
    }
    if precision in patterns:
        require(
            isinstance(value, str) and re.fullmatch(patterns[precision], value),
            "date does not match precision",
        )


def validate_evidence(tables):
    require(
        isinstance(tables, dict)
        and all(
            isinstance(rows, list) and all(isinstance(r, dict) for r in rows)
            for rows in tables.values()
        ),
        "invalid evidence table type",
    )
    sources = unique(tables.get("sources", []), "source_ref")
    for row in tables.get("milestone_observations", []):
        validate_date(row)
    for table in ("field_observations", "cost_observations", "milestone_observations"):
        for row in tables.get(table, []):
            require(
                isinstance(row.get("source_ref"), str)
                and row["source_ref"].strip()
                and row["source_ref"] in sources,
                "missing source reference",
            )
    for row in tables.get("field_observations", []):
        validate_field(row)
    for row in tables.get("cost_observations", []):
        validate_cost(row)
    for row in tables.get("inherited_cost_records", []):
        validate_inherited_parent(row)


def validate_field(row):
    require(
        all(
            isinstance(row.get(k), str) and row[k].strip()
            for k in ("entity_id", "name", "country")
        ),
        "invalid field identity/name/country",
    )
    require(
        TYPE_MAP.get(row.get("entity_type"), row.get("entity_type")) in TYPES,
        "unsupported entity scope",
    )
    require(
        row.get("current_configuration_verified") is False,
        "snapshot cannot assert verified current configuration",
    )


def validate_cost(row):
    require(
        row.get("scope_type") in {"project", "block", "contract_bundle"},
        "unsupported cost scope",
    )
    require(
        all(
            isinstance(row.get(k), str) and row[k].strip()
            for k in ("cost_id", "entity_or_scope", "unit")
        ),
        "invalid cost identity/unit",
    )
    require(
        type(row.get("value")) in {int, float} and row["value"] >= 0,
        "invalid cost value",
    )


def validate_inherited_parent(row):
    require(
        all(
            isinstance(row.get(k), str) and row[k].strip()
            for k in ("project", "source_url")
        ),
        "invalid inherited parent identity",
    )


def decode_csv(rows):
    json_fields = {
        "attributes",
        "evidence_refs",
        "source_refs",
        "dependencies",
        "adjudication_source_refs",
        "original_header",
        "candidate_payload",
    }
    for row in rows:
        for key in json_fields & row.keys():
            row[key] = json.loads(row[key]) if row[key] else []
        for key in {"multiplicity", "schema_version"} & row.keys():
            row[key] = int(row[key])
        for key in {"supplemental", "current_configuration_verified"} & row.keys():
            require(row[key] in {"True", "False", ""}, "invalid Boolean")
            row[key] = row[key] == "True"
    return rows


def parsed_csv(raw):
    if not raw:
        return []
    reader = csv.DictReader(
        io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True
    )
    rows = list(reader)
    header = reader.fieldnames
    require(
        header
        and len(header) == len(set(header))
        and not any(None in r or None in r.values() for r in rows),
        "invalid CSV header/row width",
    )
    return decode_csv(rows)
