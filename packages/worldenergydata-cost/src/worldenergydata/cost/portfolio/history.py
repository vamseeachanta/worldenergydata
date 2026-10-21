"""As-of event traces and frozen workbook-cell comparisons.

Events are observations, never cumulative cash flows. Revision events replace
neither earlier evidence nor missing years. Accounting definitions follow the
Shared Contract to Freeze, cost-map program plan (2026).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from .accounting import Basis, Evidence, Interval


@dataclass(frozen=True)
class Event:
    identity: str
    project: str
    component: str
    kind: str
    occurred_on: date
    amount: Interval | None
    basis: Basis
    evidence: Evidence
    period: str

    def __post_init__(self):
        if not all(
            x.strip()
            for x in (self.identity, self.project, self.component, self.period)
        ):
            raise ValueError("event identity, scope and period are required")
        if self.kind not in {
            "sanction",
            "award",
            "revision",
            "outturn",
            "new_scope",
            "basis_change",
            "not_public",
        }:
            raise ValueError("unknown event kind")
        if self.kind == "not_public" and self.amount is not None:
            raise ValueError("not_public event has a value")
        if self.amount is not None and self.amount.low < 0:
            raise ValueError("negative event amount")


def trace(events: tuple[Event, ...], as_of: date) -> tuple[Event, ...]:
    unique = {}
    for event in events:
        if event.identity in unique and unique[event.identity] != event:
            raise ValueError("conflicting duplicate event")
        unique[event.identity] = event
    return tuple(
        sorted(
            (
                e
                for e in unique.values()
                if e.occurred_on <= as_of and e.evidence.available_on <= as_of
            ),
            key=lambda e: (e.occurred_on, e.identity),
        )
    )


@dataclass(frozen=True)
class WorkbookValue:
    """Caller-verified frozen cell value, never a disclosure or a live formula.

    The adapter must verify the workbook digest, cached value and cell crosswalk
    before constructing this record. A missing formula cache stays unavailable.
    """

    project: str
    component: str
    cell: str
    workbook_digest: str
    amount: Interval | None
    basis: Basis
    vintage: str
    period: str

    def __post_init__(self):
        if not all(
            x.strip()
            for x in (
                self.project,
                self.component,
                self.cell,
                self.workbook_digest,
                self.vintage,
                self.period,
            )
        ):
            raise ValueError(
                "frozen workbook identity, cell, vintage and period required"
            )


@dataclass(frozen=True)
class WorkbookComparison:
    status: str
    reason: str
    variance: Interval | None
    observation: Event
    workbook: WorkbookValue


def read_workbook_cell(
    path: Path,
    sheet: str,
    cell: str,
    expected_digest: str,
    *,
    project: str,
    component: str,
    basis: Basis,
    vintage: str,
    period: str,
) -> WorkbookValue:
    """Verify frozen bytes and read a native numeric or cached formula value.

    No spreadsheet application is started. Missing formula caches remain unknown;
    text, booleans and spreadsheet errors cannot become monetary values.
    """
    from openpyxl import load_workbook

    content = path.read_bytes()
    if sha256(content).hexdigest() != expected_digest:
        raise ValueError("workbook digest mismatch")
    book = load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        value = book[sheet][cell].value
    finally:
        book.close()
    amount = None
    if value is not None:
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError("workbook cell is not a numeric cached value")
        number = Decimal(str(value))
        amount = Interval(number, number)
    return WorkbookValue(
        project,
        component,
        f"{sheet}!{cell}",
        expected_digest,
        amount,
        basis,
        vintage,
        period,
    )


def compare_workbook(
    observed: Event, workbook: WorkbookValue, vintage: str, period: str
) -> WorkbookComparison:
    reason = ""
    if (observed.project, observed.component) != (workbook.project, workbook.component):
        reason = "scope"
    elif observed.basis.currency != workbook.basis.currency:
        reason = "currency"
    elif (
        not observed.basis.known
        or not workbook.basis.known
        or observed.basis != workbook.basis
    ):
        reason = "basis"
    elif workbook.vintage != vintage:
        reason = "assumption_vintage"
    elif workbook.period != period or observed.period != period:
        reason = "timing"
    elif observed.amount is None or workbook.amount is None:
        reason = "missing_evidence"
    if reason:
        return WorkbookComparison("NOT_EVALUATED", reason, None, observed, workbook)
    # Interval subtraction: program plan (2026), Shared Contract to Freeze.
    variance = Interval(
        observed.amount.low - workbook.amount.high,
        observed.amount.high - workbook.amount.low,
    )
    reason = "matched" if variance.low == variance.high == 0 else "unexplained"
    return WorkbookComparison("evaluated", reason, variance, observed, workbook)
