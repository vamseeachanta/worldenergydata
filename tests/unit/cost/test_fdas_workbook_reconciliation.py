"""Read-only reconciliation examples; all amounts below are synthetic inputs.

Hand calculations: W=[100,120], C=[80,90] gives W-C=[10,40]. With
M=25 that straddles materiality; M=40 encloses it and M=9 excludes it.
No financial assumption or acceptance threshold is inferred from these fixtures.
"""

from dataclasses import replace
from decimal import Decimal

import pytest

from worldenergydata.cost.workbook_reconciliation.models import (
    Basis,
    Interval,
    MaterialityPolicy,
    Observation,
)
from worldenergydata.cost.workbook_reconciliation.reconcile import reconcile


@pytest.fixture
def basis():
    return Basis(
        project_id="project-001",
        component="host",
        start="2024-01",
        end="2024-12",
        currency="USD",
        unit="USD",
        price_basis="nominal",
        basis_year="not_applicable",
        ownership="gross",
        scope="development",
        capex_basis="capex",
        assumption_vintage="frozen",
        normalization_vintage="native",
    )


def observation(basis, low="100", high="120", provenance="workbook_assumption"):
    return Observation(
        basis, Interval(Decimal(low), Decimal(high)), provenance, "fixture:1"
    )


def policy(limit):
    return MaterialityPolicy(Decimal(limit), Decimal(0), "synthetic test policy", True)


@pytest.mark.parametrize(
    "limit,expected",
    [("25", "uncertain_materiality"), ("40", "immaterial"), ("9", "material")],
)
def test_interval_subtraction_and_boundary(basis, limit, expected):
    result = reconcile(
        observation(basis), observation(basis, "80", "90", "mapped"), policy(limit)
    )
    assert result.variance == Interval(Decimal(10), Decimal(40))
    assert result.materiality == expected
    assert result.status == ("PASS" if expected == "immaterial" else "FAIL")


@pytest.mark.parametrize(
    "field,value",
    [
        ("project_id", "project-002"),
        ("component", "surf"),
        ("start", "2023-01"),
        ("end", "2025-12"),
        ("currency", "EUR"),
        ("unit", "USD MM"),
        ("price_basis", "real"),
        ("basis_year", "2020"),
        ("ownership", "net"),
        ("scope", "operations"),
        ("capex_basis", "opex"),
        ("assumption_vintage", "alternative"),
        ("normalization_vintage", "alternative"),
    ],
)
def test_incompatible_values_are_not_subtracted(basis, field, value):
    result = reconcile(
        observation(basis), observation(replace(basis, **{field: value}))
    )
    assert result.status == "NOT_EVALUATED"
    assert result.variance is None
    assert field in result.reason


def test_no_policy_preserves_variance_without_acceptance(basis):
    result = reconcile(observation(basis), observation(basis, "80", "90", "modeled"))
    assert result.status == "NOT_EVALUATED"
    assert result.variance.high == Decimal(40)


def test_approved_policy_and_evidenced_explanation_required(basis):
    w, c = observation(basis), observation(basis, "80", "90", "disclosed")
    assert reconcile(w, c, policy("9"), "scope").status == "FAIL"
    assert reconcile(w, c, policy("9"), "scope", "fixture:scope").status == "PASS"
    assert (
        reconcile(w, c, replace(policy("9"), approved=False)).status == "NOT_EVALUATED"
    )
    with pytest.raises(ValueError, match="classification"):
        reconcile(w, c, policy("9"), "guess")


def test_unknown_basis_and_open_bounds_fail_closed(basis):
    missing = observation(replace(basis, basis_year=""))
    assert reconcile(missing, missing).variance is None
    unknown = observation(replace(basis, ownership="unknown"))
    assert reconcile(unknown, unknown).variance is None
    open_value = replace(observation(basis), amount=Interval(None, Decimal(120)))
    assert (
        reconcile(open_value, observation(basis), policy("9")).status == "NOT_EVALUATED"
    )


def test_zero_crossing_is_not_midpoint_test(basis):
    """[80,120]-[90,110]=[-30,30], outside M=25 despite midpoint zero."""
    result = reconcile(
        observation(basis, "80", "120"), observation(basis, "90", "110"), policy("25")
    )
    assert result.variance == Interval(Decimal(-30), Decimal(30))
    assert result.materiality == "uncertain_materiality"
    assert result.status == "FAIL"


@pytest.mark.parametrize("low,high", [("NaN", "1"), ("2", "1"), ("0", "Infinity")])
def test_invalid_intervals(low, high):
    with pytest.raises(ValueError):
        Interval(Decimal(low), Decimal(high))


def test_relative_threshold_uses_entire_reference_interval(basis):
    """M=max(1,0.1*max(|100|,|120|))=12; [10,40] straddles it."""
    p = MaterialityPolicy(Decimal(1), Decimal("0.1"), "synthetic policy", True)
    result = reconcile(observation(basis), observation(basis, "80", "90"), p)
    assert result.threshold == Decimal(12)
    assert result.materiality == "uncertain_materiality"


def test_workbook_cannot_be_labeled_disclosure(basis):
    with pytest.raises(ValueError, match="provenance"):
        reconcile(observation(basis, provenance="disclosed"), observation(basis))
