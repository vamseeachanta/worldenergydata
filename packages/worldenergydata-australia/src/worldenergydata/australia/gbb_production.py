"""Offline inspection of AEMO Gas Bulletin Board actual-flow CSV bytes.

Schema source: AEMO GasBBActualFlowStorageLast31.CSV, observed 2026-10-19.
This is a facility/location report, not a field production series. Units and
reuse rights are unconfirmed; values are retained without conversion. No live
retrieval, aggregation, field allocation or economics is performed here.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

SOURCE_URL = (
    "https://nemweb.com.au/Reports/Current/GBB/GasBBActualFlowStorageLast31.CSV"
)
# Publisher header at SOURCE_URL, observed 2026-10-19; no inferred unit suffixes.
MEASURES = (
    "Demand",
    "Supply",
    "TransferIn",
    "TransferOut",
    "HeldInStorage",
    "CushionGasStorage",
)
COLUMNS = (
    "GasDate",
    "FacilityName",
    "FacilityId",
    "FacilityType",
    *MEASURES,
    "State",
    "LocationName",
    "LocationId",
    "LastUpdated",
)


@dataclass(frozen=True)
class EconomicsCheck:
    name: str
    reason: str
    status: str = "NOT_EVALUATED"


@dataclass(frozen=True)
class GBBFlow:
    """Source values; blank amounts are unknown, timestamps have no inferred zone."""

    gas_date: date
    facility_id: str
    facility_name: str
    facility_type: str
    location_id: str
    location_name: str
    state: str
    last_updated: datetime
    demand: Decimal | None
    supply: Decimal | None
    transfer_in: Decimal | None
    transfer_out: Decimal | None
    held_in_storage: Decimal | None
    cushion_gas_storage: Decimal | None


@dataclass(frozen=True)
class GBBInspection:
    records: tuple[GBBFlow, ...]
    source_sha256: str
    source_size_bytes: int
    source_url: str = SOURCE_URL

    @property
    def units(self) -> None:
        """The CSV header does not establish units; no engineering use is qualified."""
        return None

    @property
    def date_range(self) -> tuple[date | None, date | None]:
        dates = [record.gas_date for record in self.records]
        return (min(dates), max(dates)) if dates else (None, None)

    @property
    def economics_status(self) -> str:
        return "NOT_EVALUATED"

    @property
    def economics_checks(self) -> tuple[EconomicsCheck, ...]:
        return (
            EconomicsCheck("source_units", "Publisher unit definitions are required."),
            EconomicsCheck(
                "reuse_rights", "Source-specific reuse rights are required."
            ),
            EconomicsCheck(
                "field_allocation", "Facility/location flows are not field allocations."
            ),
            EconomicsCheck(
                "gas_volume_conversion",
                "A sourced conversion basis is required before emitting gas_mcf.",
            ),
        )


def _amount(value: str, column: str) -> Decimal | None:
    if not value.strip():
        return None
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"invalid {column} amount") from exc
    if not number.is_finite():
        raise ValueError(f"non-finite {column} amount")
    return number


def _record(row: dict[str, str]) -> GBBFlow:
    if any(not row[column].strip() for column in COLUMNS if column not in MEASURES):
        raise ValueError("missing record identity or date")
    if any(
        not re.fullmatch(r"[0-9]+", row[col]) for col in ("FacilityId", "LocationId")
    ):
        raise ValueError("invalid source identifier")
    try:
        gas_date = datetime.strptime(row["GasDate"], "%Y/%m/%d").date()
        updated = datetime.strptime(row["LastUpdated"], "%Y/%m/%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError("invalid source date or timestamp") from exc
    return GBBFlow(
        gas_date=gas_date,
        facility_id=row["FacilityId"],
        facility_name=row["FacilityName"],
        facility_type=row["FacilityType"],
        location_id=row["LocationId"],
        location_name=row["LocationName"],
        state=row["State"],
        last_updated=updated,
        **{
            name: _amount(row[column], column)
            for name, column in zip(
                (
                    "demand",
                    "supply",
                    "transfer_in",
                    "transfer_out",
                    "held_in_storage",
                    "cushion_gas_storage",
                ),
                MEASURES,
            )
        },
    )


def inspect_gbb_csv(raw: bytes, *, max_bytes: int, max_rows: int) -> GBBInspection:
    """Validate a bounded snapshot; resource budgets are required caller inputs.

    Header drift, malformed rows and duplicate date/facility/location keys fail
    instead of returning partial output. Source row order and Decimal values are
    retained. No interpretation of missing values or revisions is inferred.
    """
    for name, budget in (("byte", max_bytes), ("row", max_rows)):
        if type(budget) is not int or budget <= 0:
            raise ValueError(f"{name} budget must be a positive integer")
    if len(raw) > max_bytes:
        raise ValueError("source byte budget exceeded")
    try:
        stream = io.StringIO(raw.decode("utf-8-sig"), newline="")
    except UnicodeDecodeError as exc:
        raise ValueError("source is not UTF-8 CSV") from exc
    reader = csv.DictReader(stream, strict=True)
    records: list[GBBFlow] = []
    seen: set[tuple[date, str, str]] = set()
    try:
        header = reader.fieldnames
        if header is None or len(header) != len(COLUMNS) or set(header) != set(COLUMNS):
            raise ValueError("unrecognized source header")
        for row in reader:
            if len(records) >= max_rows:
                raise ValueError("source row budget exceeded")
            if None in row or any(value is None for value in row.values()):
                raise ValueError("malformed source row")
            record = _record(row)
            key = (record.gas_date, record.facility_id, record.location_id)
            if key in seen:
                raise ValueError("duplicate date/facility/location key")
            seen.add(key)
            records.append(record)
    except csv.Error as exc:
        raise ValueError("malformed source CSV") from exc
    return GBBInspection(tuple(records), hashlib.sha256(raw).hexdigest(), len(raw))
