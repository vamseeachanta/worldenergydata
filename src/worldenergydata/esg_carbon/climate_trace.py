"""Read a local Climate TRACE emissions_sources.csv, without network access.

Schema source: Climate TRACE Inventory September 2026, v5.11.0, Data Licensing,
Schema, and Citation Guide, section emissions_sources.csv metadata:
https://media.climatetrace.org/about_the_data_latest_b6e7b8d419.pdf

Temporal-granularity enum: Climate TRACE Data Schema, tools schema README,
revision 61dbefb85a9eb759036c17e02ca59f0015a7c7dc (2024-07-26), Descriptions,
source_information_external.temporal_granularity: month, day, hour, week,
annual, other. The v5.11.0 guide defines resolution without listing this enum.

Compatibility mapping: co2e_100yr -> co2e_100gwp and co2e_20yr -> co2e_20gwp.
Both spellings use the existing canonical horizon labels without mass conversion.
This mapping is not evidence of the labels in a particular source-file release.
Inputs shall be pre-filtered to supported GHG labels and nonnegative emissions;
removals and unsupported pollutants abort the import rather than being skipped.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path

from .inventory import _GAS_ALIASES, EmissionInventory, EmissionRecord

_REQUIRED = (
    "source_id",
    "source_name",
    "iso3_country",
    "sector",
    "subsector",
    "start_time",
    "end_time",
    "gas",
    "emissions_quantity",
    "temporal_granularity",
)
# Internal canonical species/horizon labels, with compatibility aliases below.
# Real v5.11.0 source-file spellings are unverified; no GWP factors are inferred.
_GASES = frozenset({"co2", "ch4", "n2o", "co2e_100gwp", "co2e_20gwp"})
# Supported resolution labels from the schema revision cited above.
_TEMPORAL_GRANULARITIES = frozenset({"month", "day", "hour", "week", "annual", "other"})
# Guide v5.11.0, emissions_quantity metadata; slash spelling is also accepted.
_MISSING = frozenset({"", "null", "n-a", "n/a"})


def _timestamp(value: str, field: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO datetime") from error
    # Guide v5.11.0 defines start_time and end_time in UTC, including CSV
    # timestamps without an explicit offset. A date alone is not a timestamp.
    if "T" not in value and " " not in value:
        raise ValueError(f"{field} must include a time")
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _record(row: dict[str, str]) -> EmissionRecord:
    for field in _REQUIRED:
        if field != "emissions_quantity" and not row[field]:
            raise ValueError(f"{field} must be nonempty")
    if row["temporal_granularity"] not in _TEMPORAL_GRANULARITIES:
        raise ValueError("temporal_granularity must be supported")
    if not re.fullmatch(r"[A-Z]{3}", row["iso3_country"]):
        raise ValueError("iso3_country must be three uppercase letters")
    gas = _GAS_ALIASES.get(row["gas"], row["gas"])
    if gas not in _GASES:
        raise ValueError("gas must be a supported greenhouse-gas label")
    # Guide v5.11.0 fixes source emissions_quantity to metric tonnes. An
    # additional explicit unit column shall not silently contradict that basis.
    if row.get("emissions_quantity_units", "") not in {"", "tonnes"}:
        raise ValueError("emissions_quantity_units must be tonnes when supplied")
    mass = None
    if row["emissions_quantity"].casefold() not in _MISSING:
        try:
            mass = float(row["emissions_quantity"])
        except ValueError as error:
            raise ValueError("emissions_quantity must be numeric or missing") from error
        # Domain of this slice: reported emissions, excluding carbon removals.
        if not isfinite(mass) or mass < 0:
            raise ValueError("emissions_quantity must be finite and nonnegative")
    start = _timestamp(row["start_time"], "start_time")
    end = _timestamp(row["end_time"], "end_time")
    if end <= start:
        raise ValueError("end_time must follow start_time")
    return EmissionRecord(
        iso3_country=row["iso3_country"],
        sector=row["sector"],
        subsector=row["subsector"],
        start_time=start,
        end_time=end,
        temporal_granularity=row["temporal_granularity"],
        gas=gas,
        source_id=row["source_id"],
        source_name=row["source_name"],
        emissions_quantity=mass,
    )


def read_climate_trace_csv(path: str | Path, *, edition: str) -> EmissionInventory:
    """Load one UTF-8 source-level CSV and retain its original-byte digest.

    Additional published columns are ignored. Required fields, rectangular rows
    and unique (source_id, gas, start_time, end_time) observations are enforced.
    Errors identify the last physical line reached in the CSV record,
    without echoing raw field contents.
    The caller shall retain the input file and obtain its declared edition.
    Country-level downloads and legacy asset_id schemas are outside this slice.
    """
    if not isinstance(edition, str) or not edition.strip():
        raise ValueError("edition must be supplied")
    payload = Path(path).read_bytes()
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), strict=True)
    try:
        fields = reader.fieldnames
        if (
            not fields
            or len(fields) != len(set(fields))
            or set(_REQUIRED) - set(fields)
        ):
            raise ValueError("CSV requires unique headers and all required columns")
        records = []
        seen = set()
        for row in reader:
            number = reader.line_num
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"CSV row {number}: column count differs from header")
            try:
                record = _record({key: value.strip() for key, value in row.items()})
            except ValueError as error:
                raise ValueError(f"CSV row {number}: {error}") from error
            key = (record.source_id, record.gas, record.start_time, record.end_time)
            if key in seen:
                raise ValueError(f"CSV row {number}: duplicate source/gas/period")
            seen.add(key)
            records.append(record)
    except csv.Error as error:
        # DictReader.line_num is stale when its underlying reader raises.
        line = reader.reader.line_num
        raise ValueError(f"CSV row {line}: malformed CSV") from error
    return EmissionInventory(
        tuple(records), edition.strip(), hashlib.sha256(payload).hexdigest()
    )
