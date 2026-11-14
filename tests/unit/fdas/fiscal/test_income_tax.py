"""Annual tax bridge tests with independent, synthetic hand calculations.

The example rates are sourced to Instructions for Form 1120 (2025):
Schedule J, line 1a (corporate tax) and line 30, Net operating loss (NOL).
https://www.irs.gov/instructions/i1120
All dollar amounts and years below are synthetic test inputs, not cost estimates.
"""

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from worldenergydata.fdas.fiscal.income_tax import (
    AnnualTaxInput,
    IncomeTaxPolicy,
    calculate_annual_income_tax,
)

# IRS Instructions for Form 1120 (2025), Schedule J line 1a and line 30 NOL.
TAX_RATE = 0.21
NOL_LIMIT = 0.80
SOURCE = "IRS Instructions for Form 1120 (2025), Schedule J line 1a; line 30 NOL"


def _policy(**changes):
    return replace(
        IncomeTaxPolicy(TAX_RATE, NOL_LIMIT, SOURCE, "test-basis"), **changes
    )


def _year(**changes):
    return replace(AnnualTaxInput(2025, 1000, 1000, 0), **changes)


def test_loss_then_limited_recovery_and_exhaustion():
    """Hand calculation, arbitrary USD: loss 1000, then incomes 500, 1000.

    Opening loss 0. First year: eligible new loss 1000, tax 0, cash -1000.
    Next: min(1000, .8*500)=400 used; taxable=100; tax=.21*100=21;
    closing loss=600; cash=500-21=479.
    Last: min(600, .8*1000)=600 used; taxable=400; tax=.21*400=84;
    closing loss=0; cash=1000-84=916. No refund is credited for the loss.
    Rates: IRS Instructions for Form 1120 (2025), line 30 and Schedule J 1a.
    """
    inputs = [
        AnnualTaxInput(2025, -1000, 0, 1000),
        AnnualTaxInput(2026, 500, 500, 0),
        AnnualTaxInput(2027, 1000, 1000, 0),
    ]
    snapshot = inputs.copy()
    result = calculate_annual_income_tax(inputs, policy=_policy(), opening_nol_usd=0)
    assert inputs == snapshot
    assert result.policy == _policy()
    assert result.opening_nol_usd == 0
    assert [r.year for r in result.years] == [2025, 2026, 2027]
    assert [r.nol_opening_usd for r in result.years] == [0, 1000, 600]
    assert [r.nol_generated_usd for r in result.years] == [1000, 0, 0]
    assert [r.nol_used_usd for r in result.years] == [0, 400, 600]
    assert [r.nol_closing_usd for r in result.years] == [1000, 600, 0]
    assert [r.taxable_income_usd for r in result.years] == [0, 100, 400]
    assert [r.income_tax_usd for r in result.years] == [0, 21, 84]
    assert [r.after_tax_cashflow_usd for r in result.years] == [-1000, 479, 916]


def test_tax_basis_is_separate_from_cashflow():
    """Cash 300, taxable income 1000, no losses: tax=1000*.21=210;
    after-tax cash=300-210=90. CAPEX must not become an automatic deduction.
    Rate: IRS Instructions for Form 1120 (2025), Schedule J line 1a.
    """
    row = _year(pre_tax_cashflow_usd=300)
    result = calculate_annual_income_tax([row], policy=_policy(), opening_nol_usd=0)
    assert result.years[0].income_tax_usd == 210
    assert result.years[0].after_tax_cashflow_usd == 90
    assert result.years[0].taxable_income_before_nol_usd == 1000
    assert result.years[0].pre_tax_cashflow_usd == 300


def test_cash_loss_does_not_implicitly_generate_a_tax_loss():
    """Synthetic cash loss -1000, eligible NOL explicitly 200: closing NOL=200.
    Taxable income is 0, so tax is 0 and after-tax cash stays -1000.
    Eligible losses require caller adjustments; cash expenditure is not a tax base.
    """
    row = _year(
        pre_tax_cashflow_usd=-1000,
        taxable_income_before_nol_usd=0,
        nol_generated_usd=200,
    )
    result = calculate_annual_income_tax([row], policy=_policy(), opening_nol_usd=0)
    assert result.years[0].nol_closing_usd == 200
    assert result.years[0].after_tax_cashflow_usd == -1000


def test_opening_loss_and_zero_income_year_are_preserved():
    """Opening 100 plus explicit new 50 gives 150; next zero-income year
    uses no losses, leaving 150. Tax and cash are zero in both years.
    """
    rows = [AnnualTaxInput(2025, 0, 0, 50), AnnualTaxInput(2026, 0, 0, 0)]
    result = calculate_annual_income_tax(
        iter(rows), policy=_policy(), opening_nol_usd=100
    )
    assert [r.nol_closing_usd for r in result.years] == [150, 150]
    assert [r.income_tax_usd for r in result.years] == [0, 0]


@pytest.mark.parametrize(
    "rate,limit,used,tax", [(0, 0.8, 800, 0), (1, 1, 1000, 0), (0.21, 0, 0, 210)]
)
def test_required_policy_controls_the_result(rate, limit, used, tax):
    """Synthetic policy boundaries (not legal defaults): income 1000, NOL 1000.
    Used=min(1000, limit*1000); tax=rate*(1000-used).
    Fractions 0 and 1 test algebraic bounds; .21/.8 have the IRS citation above.
    """
    policy = _policy(corporate_tax_rate=rate, nol_offset_limit=limit)
    result = calculate_annual_income_tax([_year()], policy=policy, opening_nol_usd=1000)
    assert result.years[0].nol_used_usd == used
    assert result.years[0].income_tax_usd == tax


@pytest.mark.parametrize("field", ["corporate_tax_rate", "nol_offset_limit"])
@pytest.mark.parametrize(
    "bad", [-0.1, 1.1, float("nan"), float("inf"), True, "0.21", None]
)
def test_invalid_policy_fraction_rejected(field, bad):
    expected = TypeError if isinstance(bad, (bool, str)) or bad is None else ValueError
    with pytest.raises(expected, match=field):
        _policy(**{field: bad})


@pytest.mark.parametrize("field", ["source", "assumption_version"])
@pytest.mark.parametrize("bad", ["", "   ", None, 1])
def test_policy_provenance_is_required(field, bad):
    with pytest.raises(ValueError, match=field):
        _policy(**{field: bad})


@pytest.mark.parametrize(
    "field",
    ["pre_tax_cashflow_usd", "taxable_income_before_nol_usd", "nol_generated_usd"],
)
@pytest.mark.parametrize(
    "bad", [float("nan"), float("inf"), -float("inf"), True, "100", None]
)
def test_invalid_annual_amount_rejected(field, bad):
    expected = TypeError if isinstance(bad, (bool, str)) or bad is None else ValueError
    with pytest.raises(expected, match=field):
        _year(**{field: bad})


@pytest.mark.parametrize(
    "field", ["taxable_income_before_nol_usd", "nol_generated_usd"]
)
def test_negative_tax_amount_rejected(field):
    with pytest.raises(ValueError, match=field):
        _year(**{field: -1})


def test_simultaneous_taxable_profit_and_new_loss_rejected():
    with pytest.raises(ValueError, match="both"):
        _year(nol_generated_usd=100)


@pytest.mark.parametrize("year_type", [np.int32, np.int64, np.uint64])
def test_numpy_integer_years_support_consecutive_schedule(year_type):
    """DataFrame-style integer scalars retain the annual ordering contract."""
    rows = [_year(year=year_type(year)) for year in (2025, 2026)]
    result = calculate_annual_income_tax(rows, policy=_policy(), opening_nol_usd=0)
    assert [row.year for row in result.years] == [2025, 2026]
    assert [row.income_tax_usd for row in result.years] == [210, 210]


@pytest.mark.parametrize(
    "bad",
    [
        True,
        0,
        -1,
        2025.0,
        "2025",
        None,
        np.bool_(True),
        np.int64(0),
        np.int64(-1),
        np.uint64(0),
        np.float64(2025),
    ],
)
def test_invalid_year_rejected(bad):
    with pytest.raises(ValueError, match="year"):
        _year(year=bad)


@pytest.mark.parametrize("years", [[2025, 2025], [2026, 2025], [2025, 2027]])
def test_nonconsecutive_or_unordered_years_rejected(years):
    with pytest.raises(ValueError, match="consecutive"):
        calculate_annual_income_tax(
            [_year(year=y) for y in years], policy=_policy(), opening_nol_usd=0
        )


@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), True, None])
def test_invalid_opening_loss_rejected(bad):
    expected = TypeError if isinstance(bad, bool) or bad is None else ValueError
    with pytest.raises(expected, match="opening_nol_usd"):
        calculate_annual_income_tax([_year()], policy=_policy(), opening_nol_usd=bad)


def test_empty_schedule_rejected():
    with pytest.raises(ValueError, match="at least one"):
        calculate_annual_income_tax([], policy=_policy(), opening_nol_usd=0)


def test_loss_overflow_rejected():
    """Synthetic finite values whose sum exceeds floating-point range must fail."""
    row = _year(taxable_income_before_nol_usd=0, nol_generated_usd=1e308)
    with pytest.raises(ValueError, match="finite"):
        calculate_annual_income_tax([row], policy=_policy(), opening_nol_usd=1e308)


def test_cashflow_overflow_rejected():
    """Synthetic finite cash and tax values whose difference overflows fail."""
    row = _year(pre_tax_cashflow_usd=-1.7e308, taxable_income_before_nol_usd=1.7e308)
    with pytest.raises(ValueError, match="finite"):
        calculate_annual_income_tax([row], policy=_policy(), opening_nol_usd=0)


def test_large_integer_cannot_overflow_validation():
    with pytest.raises(ValueError, match="finite"):
        _year(pre_tax_cashflow_usd=10**1000)


def test_invalid_policy_type_rejected():
    with pytest.raises(TypeError, match="policy"):
        calculate_annual_income_tax([_year()], policy=None, opening_nol_usd=0)


def test_invalid_year_row_type_rejected():
    with pytest.raises(TypeError, match="AnnualTaxInput"):
        calculate_annual_income_tax([None], policy=_policy(), opening_nol_usd=0)


def test_policy_and_opening_balance_have_no_default():
    with pytest.raises(TypeError, match="policy"):
        calculate_annual_income_tax([_year()], opening_nol_usd=0)
    with pytest.raises(TypeError, match="opening_nol_usd"):
        calculate_annual_income_tax([_year()], policy=_policy())


def test_policy_change_uses_explicit_closing_balance():
    """Synthetic two-year split: opening 1000, first income 500 uses 400,
    leaving 600. Next income 1000 uses 600 at a full-offset scenario limit;
    tax=(1000-600)*.21=84, cash=916. Unity is a synthetic fraction boundary.
    Rate: IRS Instructions for Form 1120 (2025), Schedule J line 1a.
    """
    first = calculate_annual_income_tax(
        [_year(taxable_income_before_nol_usd=500)],
        policy=_policy(),
        opening_nol_usd=1000,
    )
    second_policy = _policy(
        nol_offset_limit=1, assumption_version="synthetic-next-basis"
    )
    second = calculate_annual_income_tax(
        [_year(year=2026)],
        policy=second_policy,
        opening_nol_usd=first.years[-1].nol_closing_usd,
    )
    assert first.years[0].nol_closing_usd == 600
    assert second.years[0].nol_opening_usd == 600
    assert second.years[0].nol_closing_usd == 0
    assert second.years[0].income_tax_usd == 84
    assert second.years[0].after_tax_cashflow_usd == 916
    assert second.policy.assumption_version == "synthetic-next-basis"
    assert first.policy.assumption_version == "test-basis"


def test_results_are_immutable():
    result = calculate_annual_income_tax([_year()], policy=_policy(), opening_nol_usd=0)
    with pytest.raises(FrozenInstanceError):
        result.years[0].income_tax_usd = 0
    with pytest.raises(FrozenInstanceError):
        result.policy.source = "changed"
    with pytest.raises(FrozenInstanceError):
        result.years = ()
