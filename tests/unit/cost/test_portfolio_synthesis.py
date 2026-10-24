"""Independent accounting examples; all amounts below are synthetic inputs.

Contract: docs/plans/2026-07-16-issue-1038-cost-map-program.md,
Shared Contract to Freeze (2026). No empirical cost factors are assumed.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal as D

import pytest

from worldenergydata.cost.portfolio.accounting import (
    Basis,
    CostItem,
    Evidence,
    Interval,
    Scenario,
    allocate,
    reconcile,
)


def basis(**changes):
    return replace(
        Basis(
            "USD",
            "million",
            "real",
            "2020",
            "gross",
            "phase-a",
            "upstream",
            "development_capex",
        ),
        **changes,
    )


def evidence(key="source-a", kind="award_derived"):
    return Evidence(key, date(2020, 1, 1), kind)


def item(key="award-a", **changes):
    return replace(
        CostItem(
            key,
            ("host", "installation"),
            Interval(D(20), D(30)),
            basis(),
            evidence(),
            "included",
            "range",
        ),
        **changes,
    )


def test_range_residual_bundle_and_coverage():
    """[100,120]-([20,30]+[10,10])=[60,90]; coverage=[30/120,40/100]."""
    a = item()
    b = item("award-b", requirements=("wells",), amount=Interval(D(10), D(10)))
    result = reconcile(
        Interval(D(100), D(120)),
        basis(),
        (a, a, b),
        ("host", "installation", "wells", "controls"),
    )
    assert result.eligible == Interval(D(30), D(40))
    assert result.residual == Interval(D(60), D(90))
    assert result.coverage == Interval(D("0.25"), D("0.4"))
    assert result.residual_fraction == Interval(D("0.6"), D("0.75"))
    assert result.covered_requirements == ("host", "installation", "wells")
    assert result.missing_requirements == ("controls",)


@pytest.mark.parametrize(
    "total,amount,expected",
    [
        ((0, 10), (0, 0), None),
        ((10, 10), (20, 30), ("-2", "-1")),
        ((90, 110), (80, 100), (D(1) - D(100) / D(90), D(1) - D(80) / D(110))),
        ((100, 120), (0, 0), (1, 1)),
    ],
)
def test_residual_fraction_preserves_total_dependence(total, amount, expected):
    result = reconcile(
        Interval(*map(D, total)),
        basis(),
        (item(amount=Interval(*map(D, amount))),),
        ("host", "installation"),
    )
    assert result.residual_fraction == (
        None if expected is None else Interval(*map(D, expected))
    )


def test_portfolio_uses_shared_closed_interval_and_residual():
    from worldenergydata.cost.portfolio.accounting import interval_residual
    from worldenergydata.cost.timeseries import cost_map

    assert issubclass(Interval, cost_map.ClosedInterval)
    assert interval_residual is cost_map.interval_residual
    interval = Interval(D(1), D(2))
    with pytest.raises(FrozenInstanceError):
        interval.low = D(0)
    with pytest.raises(FrozenInstanceError):
        interval.extra = D(0)


@pytest.mark.parametrize(
    "low,high", [("NaN", "1"), ("0", "Infinity"), ("-Infinity", "1")]
)
def test_portfolio_interval_rejects_nonfinite_bounds(low, high):
    with pytest.raises(ValueError, match="finite"):
        Interval(D(low), D(high))


@pytest.mark.parametrize(
    "field,value",
    [
        ("currency", "EUR"),
        ("unit", "unit"),
        ("price_basis", "nominal"),
        ("price_vintage", "2021"),
        ("ownership", "net"),
        ("phase", "phase-b"),
        ("scope", "midstream"),
        ("capex_basis", "lease"),
    ],
)
def test_each_basis_dimension_fails_closed(field, value):
    with pytest.raises(ValueError, match="basis"):
        reconcile(
            Interval(D(100), D(100)),
            basis(),
            (item(basis=basis(**{field: value})),),
            ("host", "installation"),
        )


def test_exclusions_unknowns_and_overlap_do_not_inflate_total():
    """Only [20,30] contributes; foreign exclusions cannot be summed in USD."""
    rows = (
        item(),
        item("excluded", disposition="excluded", basis=basis(currency="EUR")),
        item("overlap", disposition="overlap", overlap_group="bundle-a"),
        item("silent", amount=None, value_basis="not_public"),
    )
    result = reconcile(
        Interval(D(100), D(100)), basis(), rows, ("host", "installation")
    )
    assert result.eligible == Interval(D(20), D(30))
    assert result.unavailable == ("silent",)
    assert result.excluded_ids == ("excluded",)
    assert result.overlap_ids == ("overlap",)


def test_distinct_awards_in_same_overlap_group_are_rejected():
    with pytest.raises(ValueError, match="overlap"):
        reconcile(
            Interval(D(100), D(100)),
            basis(),
            (item(overlap_group="bundle"), item("b", overlap_group="bundle")),
            ("host", "installation"),
        )


def test_conflicting_duplicate_or_unknown_requirement_is_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        reconcile(
            Interval(D(100), D(100)),
            basis(),
            (item(), item(amount=Interval(D(1), D(1)))),
            ("host", "installation"),
        )
    with pytest.raises(ValueError, match="requirement"):
        reconcile(Interval(D(100), D(100)), basis(), (item(),), ("host",))


def test_allocations_conserve_joint_scenarios_and_show_unallocated():
    """Input shares .5/.3/.2 of 100 give 50/30/20, last share is unmapped."""
    scenarios = (
        Scenario(
            "s-a",
            "subsea",
            {"host": D(".5"), "wells": D(".3"), "unallocated": D(".2")},
            "example",
        ),
    )
    result = allocate(D(100), "subsea", scenarios, ("host", "wells"), D(".01"))
    assert result.scenarios["s-a"] == {
        "host": D(50),
        "unallocated": D(20),
        "wells": D(30),
    }
    assert result.unallocated == Interval(D(20), D(20))
    assert result.derivation == "allocated"
    assert not result.marginals_additive
    with pytest.raises(ValueError, match="architecture"):
        allocate(D(100), "dry_tree", scenarios, ("host", "wells"), D(".01"))


def test_marginals_are_not_summed_and_rounding_is_deterministic():
    """Two 100-unit scenarios (.2,.8)/(.8,.2) give marginals [20,80] each."""
    scenarios = tuple(
        Scenario(k, "subsea", s, "example")
        for k, s in (
            ("a", {"host": D(".2"), "wells": D(".8")}),
            ("b", {"host": D(".8"), "wells": D(".2")}),
        )
    )
    result = allocate(D(100), "subsea", scenarios, ("host", "wells"), D(".01"))
    assert result.bands == {
        "host": Interval(D(20), D(80)),
        "wells": Interval(D(20), D(80)),
    }
    tie = (Scenario("tie", "subsea", {"wells": D(".5"), "host": D(".5")}, "example"),)
    assert allocate(D(".01"), "subsea", tie, ("host", "wells"), D(".01")).scenarios[
        "tie"
    ] == {"host": D(".01"), "wells": D("0.00"), "unallocated": D("0.00")}


@pytest.mark.parametrize("low,high", [("NaN", "1"), ("0", "Infinity"), ("2", "1")])
def test_invalid_intervals(low, high):
    with pytest.raises(ValueError):
        Interval(D(low), D(high))


def test_missing_provenance_and_inferred_awards_are_rejected():
    with pytest.raises(ValueError):
        Evidence("", date(2020, 1, 1), "disclosed")
    with pytest.raises(ValueError, match="observed"):
        reconcile(
            Interval(D(100), D(100)),
            basis(),
            (item(evidence=evidence(kind="modeled")),),
            ("host", "installation"),
        )


def test_scope_coverage_and_value_coverage_stay_separate():
    """A linked but not-public award covers scope without supplying any value."""
    result = reconcile(
        Interval(D(100), D(100)),
        basis(),
        (item(amount=None, value_basis="not_public"),),
        ("host", "installation", "wells"),
    )
    assert result.linked_requirements == ("host", "installation")
    assert result.covered_requirements == ()
    assert result.coverage == Interval(D(0), D(0))
    assert result.total == Interval(D(100), D(100))
    assert result.basis == basis()


def test_zero_total_overrun_and_unknown_basis():
    """Zero denominators stay unavailable; 10-[20,30]=[-20,-10] is an overrun."""
    assert reconcile(Interval(D(0), D(0)), basis(), (), ("host",)).coverage is None
    overrun = reconcile(
        Interval(D(10), D(10)), basis(), (item(),), ("host", "installation")
    )
    assert overrun.residual == Interval(D(-20), D(-10))
    with pytest.raises(ValueError, match="basis"):
        reconcile(
            Interval(D(100), D(100)),
            basis(price_vintage="not_disclosed"),
            (),
            ("host",),
        )


@pytest.mark.parametrize(
    "value_basis", ["backlog", "lease_contract", "combined", "midstream"]
)
def test_nonadditive_commercial_bases_cannot_be_relabelled(value_basis):
    with pytest.raises(ValueError, match="basis"):
        reconcile(
            Interval(D(100), D(100)),
            basis(),
            (item(value_basis=value_basis),),
            ("host", "installation"),
        )


@pytest.mark.parametrize("field", tuple(Basis.__dataclass_fields__))
@pytest.mark.parametrize("sentinel", [" UNKNOWN ", " unavailable\t", " not_disclosed "])
def test_padded_unknown_basis_rejects_reconciliation(field, sentinel):
    unknown = basis(**{field: sentinel})
    with pytest.raises(ValueError, match="basis"):
        reconcile(
            Interval(D(100), D(100)),
            unknown,
            (item(basis=unknown),),
            ("host", "installation"),
        )
