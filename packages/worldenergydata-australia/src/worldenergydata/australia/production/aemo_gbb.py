"""Inspect local AEMO actual-flow reports without qualifying gas production.

Schema reference: AEMO GasBBActualFlowStorageLast31.CSV, header and date text
observed 2026-10-19 at SOURCE_URL. The legal and data-guide pages could not be
opened. Supply remains in unqualified report units: it is neither Mcf nor field
production. No rows, physical conversion coefficients or facility allocations
are bundled. This module performs no network requests.
"""

from __future__ import annotations

import calendar
import csv
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import (
    MAX_EMAX,
    MIN_EMIN,
    Context,
    Decimal,
    Inexact,
    InvalidOperation,
    Overflow,
    localcontext,
)
from pathlib import Path

SOURCE_URL = (
    "https://nemweb.com.au/Reports/Current/GBB/GasBBActualFlowStorageLast31.CSV"
)
_SUPPLY_PATTERN = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")
_REQUIRED_COLUMNS = frozenset(
    {
        "GasDate",
        "FacilityName",
        "FacilityId",
        "FacilityType",
        "Supply",
        "LocationName",
        "LocationId",
        "LastUpdated",
    }
)


@dataclass(frozen=True)
class ActualFlowRecord:
    """One facility/location gas day; Supply may be unknown, including a blank."""

    gas_date: date
    facility_name: str
    facility_id: str
    facility_type: str
    location_name: str
    location_id: str
    supply: Decimal | None
    last_updated: datetime


@dataclass(frozen=True)
class MonthlySupply:
    """Sum of observed readings, with no zero filling or physical interpretation.

    A total is absent if any reported Supply is blank. Missing dates are listed
    separately, so even a numeric total may cover only part of the month.
    Completeness describes date/value coverage only, never source qualification.
    """

    facility_id: str
    location_id: str
    year: int
    month: int
    observed_supply_total: Decimal | None
    reported_days: int
    calendar_days: int
    missing_supply_days: int
    missing_dates: tuple[date, ...]

    @property
    def complete(self) -> bool:
        return not self.missing_dates and not self.missing_supply_days

    # No source-specific units, reuse permission or field allocation has been
    # qualified; a complete month must not silently promote any of these states.
    unit_status: str = field(default="NOT_EVALUATED", init=False)
    reuse_status: str = field(default="NOT_EVALUATED", init=False)
    production_status: str = field(default="NOT_EVALUATED", init=False)


def read_actual_flow_csv(path: str | Path) -> tuple[ActualFlowRecord, ...]:
    """Read an explicitly supplied CSV; reject ambiguous schema or daily keys.

    The key is (GasDate, FacilityId, LocationId), retaining separate locations.
    Duplicate keys are rejected even when LastUpdated differs: authoritative
    revision precedence has not been established from source documentation.
    Errors report row numbers and columns without echoing source values.
    """
    records = []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        header = reader.fieldnames
        if not header or any(not column for column in header):
            raise ValueError("missing or empty CSV header")
        if len(header) != len(set(header)):
            raise ValueError("duplicate CSV header")
        missing = _REQUIRED_COLUMNS.difference(header)
        if missing:
            raise ValueError(
                "missing CSV header columns: " + ", ".join(sorted(missing))
            )
        for row_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"row {row_number}: incorrect column count")
            for column in _REQUIRED_COLUMNS.difference({"Supply"}):
                if not row[column].strip():
                    raise ValueError(f"row {row_number}: missing {column}")
            # Date formats come directly from the report text cited above.
            gas_date = _parse_timestamp(
                row["GasDate"], "%Y/%m/%d", row_number, "GasDate"
            )
            last_updated = _parse_timestamp(
                row["LastUpdated"], "%Y/%m/%d %H:%M:%S", row_number, "LastUpdated"
            )
            supply_text = row["Supply"].strip()
            supply = None
            if supply_text:
                if _SUPPLY_PATTERN.fullmatch(supply_text) is None:
                    raise ValueError(f"row {row_number}: invalid Supply")
                try:
                    supply = Decimal(supply_text)
                except InvalidOperation:
                    raise ValueError(f"row {row_number}: invalid Supply") from None
                if not supply.is_finite():
                    raise ValueError(f"row {row_number}: nonfinite Supply")
            records.append(
                ActualFlowRecord(
                    gas_date=gas_date.date(),
                    facility_name=row["FacilityName"].strip(),
                    facility_id=row["FacilityId"].strip(),
                    facility_type=row["FacilityType"].strip(),
                    location_name=row["LocationName"].strip(),
                    location_id=row["LocationId"].strip(),
                    supply=supply,
                    last_updated=last_updated,
                )
            )
    _check_unique_days(records)
    return tuple(records)


def monthly_supply(
    records: Iterable[ActualFlowRecord], *, facility_id: str, location_id: str
) -> tuple[MonthlySupply, ...]:
    """Summarize one explicit facility/location in Gregorian calendar months.

    Arithmetic only: total = sum(observed Supply); missing dates = calendar dates
    minus observed GasDate. No rate integration, unit conversion, threshold,
    facility-to-field mapping or production-facility classification is assumed.
    Months with no records are absent, never synthesized with zero supply.
    """
    facility_id = facility_id.strip()
    location_id = location_id.strip()
    if not facility_id or not location_id:
        raise ValueError("facility_id and location_id are required")
    selected = tuple(
        record
        for record in records
        if record.facility_id == facility_id and record.location_id == location_id
    )
    # Also catches callers combining overlapping local exports after parsing.
    _check_unique_days(selected)
    groups = defaultdict(list)
    for record in selected:
        groups[(record.gas_date.year, record.gas_date.month)].append(record)

    summaries = []
    for (year, month), group in sorted(groups.items()):
        calendar_days = calendar.monthrange(year, month)[1]
        observed_dates = {record.gas_date for record in group}
        # Gregorian month days are numbered from one; these are calendar/index
        # identities, not engineering coefficients or acceptance limits.
        missing_dates = tuple(
            date(year, month, day)
            for day in range(1, calendar_days + 1)
            if date(year, month, day) not in observed_dates
        )
        missing_supply_days = sum(record.supply is None for record in group)
        # Zero is the additive identity, not an assumed reading for a missing day.
        total = (
            None
            if missing_supply_days
            else _sum_exact(
                tuple(record.supply for record in group if record.supply is not None)
            )
        )
        summaries.append(
            MonthlySupply(
                facility_id=facility_id,
                location_id=location_id,
                year=year,
                month=month,
                observed_supply_total=total,
                reported_days=len(group),
                calendar_days=calendar_days,
                missing_supply_days=missing_supply_days,
                missing_dates=missing_dates,
            )
        )
    return tuple(summaries)


def _sum_exact(values: tuple[Decimal, ...]) -> Decimal:
    """Sum a nonempty group with enough places for every input and any carry."""
    lowest_place = min(value.as_tuple().exponent for value in values)
    highest_place = max(value.adjusted() for value in values)
    # Aligned coefficients occupy at most this many places. A sum of n such
    # coefficients needs at most len(str(n)) further places, even before
    # cancellation. Precision and exponent bounds never inherit caller state.
    precision = highest_place - lowest_place + 1 + len(str(len(values)))
    context = Context(
        prec=precision,
        Emax=MAX_EMAX,
        Emin=MIN_EMIN,
        clamp=0,
        traps=[Inexact, InvalidOperation, Overflow],
    )
    with localcontext(context):
        return sum(values, Decimal(0))


def _parse_timestamp(
    value: str, format_: str, row_number: int, column: str
) -> datetime:
    try:
        return datetime.strptime(value.strip(), format_)
    except ValueError:
        raise ValueError(f"row {row_number}: invalid {column}") from None


def _check_unique_days(records: Iterable[ActualFlowRecord]) -> None:
    seen = set()
    for record in records:
        key = (record.gas_date, record.facility_id, record.location_id)
        if key in seen:
            raise ValueError("duplicate facility/location gas day")
        seen.add(key)
