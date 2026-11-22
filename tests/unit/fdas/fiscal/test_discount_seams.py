"""Dated monthly NPV with explicit fiscal discount-rate selection."""

from dataclasses import replace

import pytest

from worldenergydata.fdas.analysis.cashflow import (
    CashflowEngine,
    CashflowError,
    MonthlyCashflowModel,
)
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.fiscal import get_fiscal_terms


def test_fiscal_discount_preserves_missing_calendar_months():
    """Synthetic hand calculation: -100 + 121/(1+0.21) = 0 USD.

    The second payment occurs twelve months later, not one period later.
    NPV = sum(CF_t/(1+r)^t): OpenStax, Principles of Finance (2022),
    section 16.2, equation 16.2. Inputs are synthetic, not a country rate.
    """
    terms = replace(get_fiscal_terms("us_gom"), discount_rate=0.21)
    engine = CashflowEngine(AssumptionsManager(), fiscal_terms=terms)
    flows = [
        MonthlyCashflowModel("2025-01", net_cashflow_usd=-100),
        MonthlyCashflowModel("2026-01", net_cashflow_usd=121),
    ]
    assert engine.calculate_npv(flows) == pytest.approx(0)


def test_published_annual_example_on_monthly_calendar():
    """OpenStax Finance (2022), section 16.2, table 16.3 and equation 16.2.

    Published inputs: -16,000 at t=0, then annual 2,000, 4,000 and four
    payments of 5,000, discounted at 9 percent. Independent decimal arithmetic:
    -16000 + 2000/1.09 + 4000/1.09**2 + 5000/1.09**3 + 5000/1.09**4
    + 5000/1.09**5 + 5000/1.09**6 rounds to 2,835.62 USD.
    The source's 2,835.63 sums individually rounded present values instead.
    """
    terms = replace(get_fiscal_terms("us_gom"), discount_rate=0.09)
    engine = CashflowEngine(AssumptionsManager(), fiscal_terms=terms)
    flows = [
        MonthlyCashflowModel(f"{2020 + year}-01", net_cashflow_usd=value)
        for year, value in enumerate([-16000, 2000, 4000, 5000, 5000, 5000, 5000])
    ]
    assert round(engine.calculate_npv(flows), 2) == 2835.62


@pytest.mark.parametrize("country", ["us_gom", "norway", "uk"])
def test_explicit_zero_discount_overrides_fiscal_rate(country):
    """Synthetic hand calculation at r=0: -100+121=21 USD in every country."""
    engine = CashflowEngine(
        AssumptionsManager(), fiscal_terms=get_fiscal_terms(country)
    )
    flows = [
        MonthlyCashflowModel("2025-01", net_cashflow_usd=-100),
        MonthlyCashflowModel("2026-01", net_cashflow_usd=121),
    ]
    assert engine.calculate_npv(flows, discount_rate_annual=0) == 21


@pytest.mark.parametrize("country", ["norway", "uk"])
def test_missing_fiscal_discount_requires_input(country):
    """Shipped decks omit discount_rate; a US assumption is not a substitute."""
    engine = CashflowEngine(
        AssumptionsManager(), fiscal_terms=get_fiscal_terms(country)
    )
    with pytest.raises(CashflowError, match="discount rate"):
        engine.calculate_npv([MonthlyCashflowModel("2025-01")])


@pytest.mark.parametrize("rate", [-1, 1.1, float("nan"), float("inf"), True])
def test_discount_rate_domain_is_checked(rate):
    """Domain follows core.financial.calculate_npv; r=-1 has undefined PV."""
    engine = CashflowEngine(AssumptionsManager())
    with pytest.raises(CashflowError, match="discount rate"):
        engine.calculate_npv([MonthlyCashflowModel("2025-01")], rate)


def test_unordered_rows_and_leading_zero_month_keep_valuation_date():
    """Synthetic hand calculation: 121/(1.21^2)=100/1.21 USD.

    The first zero-valued month is time zero. Calendar gaps are not compressed.
    Basis: OpenStax Finance (2022), section 16.2, equation 16.2.
    """
    terms = replace(get_fiscal_terms("us_gom"), discount_rate=0.21)
    engine = CashflowEngine(AssumptionsManager(), fiscal_terms=terms)
    flows = [
        MonthlyCashflowModel("2027-01", net_cashflow_usd=121),
        MonthlyCashflowModel("2025-01", net_cashflow_usd=0),
    ]
    assert engine.calculate_npv(flows) == pytest.approx(100 / 1.21)


@pytest.mark.parametrize("month", ["2025-13", "2025-1", "invalid", None])
def test_invalid_month_is_rejected(month):
    engine = CashflowEngine(AssumptionsManager())
    with pytest.raises(CashflowError, match="YYYY-MM"):
        engine.calculate_npv([MonthlyCashflowModel(month)], 0)


def test_duplicate_cashflow_months_are_rejected():
    engine = CashflowEngine(AssumptionsManager())
    with pytest.raises(CashflowError, match="Duplicate cashflow"):
        engine.calculate_npv([MonthlyCashflowModel("2025-01")] * 2, 0)


def test_empty_cashflows_are_rejected():
    engine = CashflowEngine(AssumptionsManager())
    with pytest.raises(CashflowError, match="empty"):
        engine.calculate_npv([], 0)


def test_deckless_discount_uses_supplied_assumptions():
    """Synthetic hand calculation: -100+121/1.21=0 USD at a supplied 21 percent.

    Discounting basis: OpenStax Finance (2022), section 16.2, equation 16.2.
    """
    import pandas as pd

    assumptions = AssumptionsManager(
        pd.DataFrame(
            {
                "DEV_SYSTEM": ["default"],
                "DISCOUNT_RATE_ANNUAL": [0.21],
            }
        )
    )
    engine = CashflowEngine(assumptions)
    flows = [
        MonthlyCashflowModel("2025-01", net_cashflow_usd=-100),
        MonthlyCashflowModel("2026-01", net_cashflow_usd=121),
    ]
    assert engine.calculate_npv(flows) == pytest.approx(0)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_nonfinite_or_boolean_cashflow_is_rejected(value):
    engine = CashflowEngine(AssumptionsManager())
    with pytest.raises(CashflowError, match="net cashflow"):
        engine.calculate_npv(
            [MonthlyCashflowModel("2025-01", net_cashflow_usd=value)], 0
        )


def test_npv_rejects_non_usd_currency():
    terms = replace(get_fiscal_terms("us_gom"), currency="EUR")
    engine = CashflowEngine(AssumptionsManager(), fiscal_terms=terms)
    with pytest.raises(CashflowError, match="currency"):
        engine.calculate_npv([MonthlyCashflowModel("2025-01")], 0)
