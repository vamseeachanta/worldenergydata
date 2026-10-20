"""Synthetic hand calculations for the portfolio accounting contract (2026).

All monetary values and shares below are invented test inputs, not estimates.
Expected results are derived in each test independently of the implementation.
"""

from dataclasses import replace
from decimal import Decimal as D

import pytest

from worldenergydata.cost.portfolio.basis import Basis, Contribution, Project
from worldenergydata.cost.portfolio.intervals import Interval
from worldenergydata.cost.portfolio.scenarios import Scenario, allocate, comparable
from worldenergydata.cost.portfolio.synthesis import synthesize


@pytest.fixture
def basis():
    return Basis("USD", "nominal", "gross", "development", "project_capex", "FID")


@pytest.fixture
def project(basis):
    # Synthetic total 100 monetary units, two physical work packages.
    return Project(
        "prj-demo",
        "subsea_tieback",
        Interval.point(D(100)),
        basis,
        ("req-host", "req-wells"),
        "synthetic hand calculation",
    )


def row(basis, **kwargs):
    values = {
        "award_id": "awd-a",
        "requirement_ids": ("req-host",),
        "amount": Interval(D(20), D(30)),
        "basis": basis,
        "disposition": "included",
        "value_basis": "range",
        "source": "synthetic",
    }
    return Contribution(**(values | kwargs))


def test_cost_envelope_rejects_low_above_high():
    with pytest.raises(ValueError):
        Interval(D(2), D(1))
    for value in (D("NaN"), D("Infinity")):
        with pytest.raises(ValueError):
            Interval.point(value)
    with pytest.raises(TypeError):
        Interval(1, 2)


def test_range_residual_and_percentage(project, basis):
    """E=[20,30]+[10,10]=[30,40]; R=100-E=[60,70]; R/T=[.6,.7]."""
    rows = (row(basis), row(basis, award_id="awd-b", amount=Interval.point(D(10))))
    result = synthesize(project, rows)
    assert result.eligible == Interval(D(30), D(40))
    assert result.residual == Interval(D(60), D(70))
    assert result.residual_fraction == Interval(D(".6"), D(".7"))
    assert result.coverage == Interval(D(".3"), D(".4"))
    assert result.top_down_status == "NOT_EVALUATED"
    assert result.allocations == ()


@pytest.mark.parametrize(
    "field,value",
    [
        ("currency", "EUR"),
        ("price_basis", "real-2020"),
        ("ownership", "net"),
        ("scope", "combined"),
        ("capex", "lease"),
        ("phase", "outturn"),
    ],
)
def test_basis_mismatch_fails_closed(project, basis, field, value):
    with pytest.raises(ValueError, match="basis"):
        synthesize(project, (row(replace(basis, **{field: value})),))


@pytest.mark.parametrize(
    "field", ["currency", "price_basis", "ownership", "scope", "capex", "phase"]
)
def test_unknown_basis_rejected(basis, field):
    with pytest.raises(ValueError, match="known"):
        replace(basis, **{field: "unknown"})


def test_count_once_and_bundle_not_split(project, basis):
    """One 20..30 award linked to both requirements still contributes 20..30."""
    bundled = row(basis, requirement_ids=project.requirement_ids)
    result = synthesize(project, (bundled, bundled))
    assert result.eligible == bundled.amount
    assert len(result.contributions) == 1
    with pytest.raises(ValueError, match="conflicting"):
        synthesize(project, (bundled, replace(bundled, amount=Interval.point(D(50)))))


def test_overlap_and_non_capex_not_added(project, basis):
    """Only 20..30 counts; excluded lease 50 and overlap 15 stay diagnostic."""
    rows = (
        row(basis, overlap_group="epci"),
        row(
            basis,
            award_id="awd-lease",
            amount=Interval.point(D(50)),
            value_basis="lease_contract",
            disposition="excluded",
            reason="non_capex",
        ),
        row(
            basis,
            award_id="awd-overlap",
            amount=Interval.point(D(15)),
            disposition="overlap",
            overlap_group="epci",
            reason="overlap_avoidance",
        ),
        row(basis, award_id="awd-secret", amount=None, value_basis="not_public"),
    )
    result = synthesize(project, rows)
    assert result.eligible == Interval(D(20), D(30))
    assert result.excluded == Interval.point(D(50))
    assert result.overlap == Interval.point(D(15))
    assert result.not_public == ("awd-secret",)
    with pytest.raises(ValueError, match="overlap"):
        synthesize(project, (rows[0], replace(rows[0], award_id="awd-c")))


@pytest.mark.parametrize(
    "value_basis", ["lease_contract", "combined", "midstream", "backlog"]
)
def test_unsafe_value_basis_requires_exclusion(project, basis, value_basis):
    with pytest.raises(ValueError, match="value basis"):
        synthesize(project, (row(basis, value_basis=value_basis),))


def test_open_bounds_and_nonpositive_denominator():
    """[90,110]-[80,+inf)=(-inf,30]; 0/positive unbounded is exactly 0."""
    residual = Interval(D(90), D(110)) - Interval(D(80), D("Infinity"), high_open=True)
    assert residual == Interval(D("-Infinity"), D(30), low_open=True)
    ratio = Interval(D(2), D(4)).divide(Interval(D(2), D("Infinity"), high_open=True))
    assert ratio == Interval(D(0), D(2), low_open=True)
    assert Interval.point(D(0)).divide(
        Interval(D(2), D("Infinity"), high_open=True)
    ) == Interval.point(D(0))
    assert Interval(D(-1), D(2)).divide(Interval(D(0), D(2))) is None


def test_negative_residual_ratios_use_all_corners():
    """[-10,30]/[90,110] encloses [-1/9,1/3] with directed rounding."""
    from fractions import Fraction

    answer = Interval(D(-10), D(30)).divide(Interval(D(90), D(110)))
    assert Fraction(answer.low) <= -Fraction(1, 9)
    assert Fraction(answer.high) >= Fraction(1, 3)
    assert answer.low < 0 < answer.high


def scenario(**kwargs):
    values = {
        "scenario_id": "scn-demo",
        "architecture": "subsea_tieback",
        "shares": (("req-host", D(".6")), ("req-wells", D(".3"))),
        "unallocated_share": D(".1"),
        "source": "synthetic hand calculation",
        "derivation": "allocated",
    }
    return Scenario(**(values | kwargs))


def test_scenario_accounting_distinguishes_residual_and_unallocated(project, basis):
    """T=100, observed=20..30, R=70..80; shares .6,.3,.1 give 60+30+10=100."""
    result = synthesize(project, (row(basis),), (scenario(),), quantum=D(".01"))
    allocation = result.allocations[0]
    assert result.residual == Interval(D(70), D(80))
    assert dict(allocation.amounts) == {"req-host": D(60), "req-wells": D(30)}
    assert allocation.unallocated == D(10)
    assert allocation.unreconciled_variance == 0
    assert allocation.derivation == "allocated"


def test_largest_remainder_quantization():
    """.03*.5=.015 each; floor=.01 each, spare .01 goes to lexical first ID."""
    split = scenario(
        shares=(("req-b", D(".5")), ("req-a", D(".5"))), unallocated_share=D(0)
    )
    result = allocate(D(".03"), split, D(".01"))
    assert dict(result.amounts) == {"req-a": D(".02"), "req-b": D(".01")}
    assert result.unreconciled_variance == 0
    with pytest.raises(ValueError, match="aligned"):
        allocate(D(".031"), split, D(".01"))


def test_architecture_cohorts_and_requirements_fail_closed(project):
    assert comparable(project, (scenario(), scenario(architecture="fpso"))) == (
        scenario(),
    )
    with pytest.raises(ValueError, match="architecture"):
        synthesize(project, (), (scenario(architecture="fpso"),), quantum=D(".01"))
    with pytest.raises(ValueError, match="requirement"):
        synthesize(
            project, (), (scenario(shares=(("req-other", D(".9")),)),), quantum=D(".01")
        )


def test_ranges_are_marginal_and_scenarios_conserve(project):
    """Joint .6/.3/.1 and .2/.7/.1: host [20,60], wells [30,70]; lows not additive."""
    other = scenario(
        scenario_id="scn-other",
        shares=(("req-host", D(".2")), ("req-wells", D(".7"))),
        derivation="modeled",
    )
    result = synthesize(project, (), (scenario(), other), quantum=D(".01"))
    assert dict(result.bands)["req-host"] == Interval(D(20), D(60))
    assert dict(result.bands)["req-wells"] == Interval(D(30), D(70))
    assert result.bands_additive is False
    for allocation in result.allocations:
        assert sum(dict(allocation.amounts).values()) + allocation.unallocated == D(100)


def test_uncertain_total_preserved(project):
    """Scenario .6/.3/.1 at total endpoints 90 and 110 gives host [54,66]."""
    result = synthesize(
        replace(project, total=Interval(D(90), D(110))),
        (),
        (scenario(),),
        quantum=D(".01"),
    )
    assert dict(result.bands)["req-host"] == Interval(D(54), D(66))
    assert {a.total for a in result.allocations} == {D(90), D(110)}


def test_scenario_validates_shares_and_provenance():
    with pytest.raises(ValueError):
        scenario(shares=(("req-host", D(".9")), ("req-wells", D(".9"))))
    with pytest.raises(ValueError):
        scenario(source="")
    with pytest.raises(ValueError):
        scenario(derivation="disclosed")


def test_marginal_bounds_enclose_rounding_between_total_endpoints(project):
    """Largest remainder can be nonmonotonic (the apportionment paradox).

    Synthetic shares 1/7, 3/7, 3/7 are replaced here by exact finite shares
    .14,.43,.43. At T=3, host .42 rounds to 1; at T=4, host .56 rounds to 0.
    A [2,4] target therefore needs host [0,1], despite endpoint allocations 0.
    """
    p = replace(
        project, total=Interval(D(2), D(4)), requirement_ids=("req-a", "req-b", "req-c")
    )
    s = scenario(
        shares=(("req-a", D(".14")), ("req-b", D(".43")), ("req-c", D(".43"))),
        unallocated_share=D(0),
    )
    result = synthesize(p, (), (s,), quantum=D(1))
    assert dict(result.bands)["req-a"] == Interval(D(0), D(1))


def test_excluded_foreign_basis_is_visible_but_not_summed(project, basis):
    """A EUR 10 exclusion cannot enter a USD subtotal: compatible excluded=0."""
    excluded = row(
        replace(basis, currency="EUR"),
        amount=Interval.point(D(10)),
        disposition="excluded",
        reason="out_of_scope",
    )
    result = synthesize(project, (excluded,))
    assert result.excluded == Interval.point(D(0))
    assert result.contributions == (excluded,)


@pytest.mark.parametrize(
    "architecture", ["dry_tree", "subsea_tieback", "fpso", "platform", "lng_heavy"]
)
def test_architectures_remain_separate(project, architecture):
    p = replace(project, architecture=architecture)
    pool = tuple(
        scenario(scenario_id=f"scn-{a}", architecture=a)
        for a in ("dry_tree", "subsea_tieback", "fpso", "platform", "lng_heavy")
    )
    assert tuple(s.architecture for s in comparable(p, pool)) == (architecture,)
