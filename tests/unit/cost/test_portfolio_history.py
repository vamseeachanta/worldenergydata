"""Synthetic dated reconciliation examples; expected arithmetic is stated inline."""

from dataclasses import replace
from datetime import date
from decimal import Decimal as D

import pytest

from worldenergydata.cost.portfolio.accounting import Basis, Evidence, Interval
from worldenergydata.cost.portfolio.history import (
    Event,
    WorkbookValue,
    compare_workbook,
    read_workbook_cell,
    trace,
)

BASIS = Basis("USD", "million", "real", "2020", "gross", "a", "upstream", "capex")


def event(key, year, **changes):
    return replace(
        Event(
            key,
            "p-a",
            "total",
            "revision",
            date(year, 1, 1),
            Interval(D(100), D(120)),
            BASIS,
            Evidence("example", date(year, 2, 1), "disclosed"),
            str(year),
        ),
        **changes,
    )


def test_trace_preserves_missing_native_lanes_and_availability():
    """No sums or interpolation: 2019, 2021 and unknown 2023 stay three events."""
    events = (
        event("c", 2023, amount=None, kind="not_public"),
        event("a", 2019),
        event("b", 2021, basis=replace(BASIS, currency="EUR")),
    )
    result = trace(events, date(2023, 12, 31))
    assert [e.identity for e in result] == ["a", "b", "c"]
    assert result[-1].amount is None
    assert result[1].basis.currency == "EUR"
    assert [e.identity for e in trace(events, date(2021, 1, 15))] == ["a"]


def test_trace_deduplicates_and_rejects_conflicting_identity():
    a = event("a", 2019)
    assert trace((a, a), date(2020, 1, 1)) == (a,)
    with pytest.raises(ValueError, match="duplicate"):
        trace((a, replace(a, component="host")), date(2020, 1, 1))


def test_workbook_exact_comparison_and_citation():
    """Observed [100,120] minus workbook [90,90] is [10,30]."""
    observed = event("a", 2020)
    cell = WorkbookValue(
        "p-a",
        "total",
        "assumptions!B2",
        "frozen-digest",
        Interval(D(90), D(90)),
        BASIS,
        "v-a",
        "2020",
    )
    result = compare_workbook(observed, cell, "v-a", "2020")
    assert result.status == "evaluated"
    assert result.variance == Interval(D(10), D(30))
    assert result.workbook == cell


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"basis": replace(BASIS, currency="EUR")}, "currency"),
        ({"basis": replace(BASIS, phase="b")}, "basis"),
        ({"vintage": "v-b"}, "assumption_vintage"),
        ({"period": "2021"}, "timing"),
        ({"amount": None}, "missing_evidence"),
        ({"component": "host"}, "scope"),
    ],
)
def test_workbook_incompatibility_is_explicit(change, reason):
    cell = WorkbookValue(
        "p-a",
        "total",
        "assumptions!B2",
        "frozen-digest",
        Interval(D(90), D(90)),
        BASIS,
        "v-a",
        "2020",
    )
    result = compare_workbook(event("a", 2020), replace(cell, **change), "v-a", "2020")
    assert result.status == "NOT_EVALUATED"
    assert result.variance is None
    assert result.reason == reason


def test_frozen_workbook_reader_drift_formula_cache_and_native_values(tmp_path):
    """Synthetic cell B2=90; C2 is an uncached formula, never guessed as 180."""
    from hashlib import sha256

    from openpyxl import Workbook

    path = tmp_path / "assumptions.xlsx"
    workbook = Workbook()
    workbook.active.title = "assumptions"
    workbook.active["B2"] = 90
    workbook.active["C2"] = "=B2*2"
    workbook.save(path)
    workbook.close()
    digest = sha256(path.read_bytes()).hexdigest()
    kwargs = {
        "project": "p-a",
        "component": "total",
        "basis": BASIS,
        "vintage": "v-a",
        "period": "2020",
    }
    value = read_workbook_cell(path, "assumptions", "B2", digest, **kwargs)
    assert value.amount == Interval(D(90), D(90))
    assert value.workbook_digest == digest
    assert (
        read_workbook_cell(path, "assumptions", "C2", digest, **kwargs).amount is None
    )
    with pytest.raises(ValueError, match="digest"):
        read_workbook_cell(path, "assumptions", "B2", "0" * 64, **kwargs)


def test_existing_fdas_crosswalk_remains_readable():
    """Expected cell value and digest are independently frozen in the existing CSV.

    No new workbook assumption is adopted; native units and original vintage stay
    intact. This checks a real frozen reference through the new read-only adapter.
    """
    import csv
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    with (
        root / "data/modules/cost/curated/fdas_project_cost_crosswalk.csv"
    ).open() as stream:
        row = next(
            r
            for r in csv.DictReader(stream)
            if r["WORKBOOK_VALUE"] and r["WORKBOOK_CELL"]
        )
    native_basis = Basis(
        row["CURRENCY"],
        row["VALUE_UNIT"],
        row["PRICE_BASIS"],
        row["BASIS_YEAR"] or "not_disclosed",
        row["OWNERSHIP_BASIS"],
        "frozen_reference",
        row["SCOPE_BASIS"],
        row["CAPEX_BASIS"],
    )
    path = (
        root / "docs/modules/bsee/analysis/production/FDAS_V30" / row["WORKBOOK_FILE"]
    )
    value = read_workbook_cell(
        path,
        row["WORKBOOK_SHEET"],
        row["WORKBOOK_CELL"],
        row["WORKBOOK_SHA256"],
        project=row["PROJECT_ID"],
        component=row["WORKBOOK_CATEGORY"],
        basis=native_basis,
        vintage=row["ASSUMPTION_VINTAGE"],
        period="frozen_reference",
    )
    assert value.amount == Interval(D(row["WORKBOOK_VALUE"]), D(row["WORKBOOK_VALUE"]))
    assert not value.basis.known  # The frozen crosswalk does not disclose a price year.
