"""AU gas marker tests with independently calculated synthetic examples.

All market, heating-value and exchange-rate numbers below are test inputs,
not observations or recommended assumptions. Expected values are derived in
individual docstrings; no published market price is embedded in these tests.
"""

from dataclasses import asdict
from datetime import datetime

import pandas as pd
import pytest

from worldenergydata.fdas.analysis.cashflow import CashflowEngine, CashflowError
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.fiscal import (
    DEV_SYSTEMS,
    FiscalTermsValidationError,
    available_countries,
    get_fiscal_terms,
    validate_deck,
)
from worldenergydata.fdas.fiscal.gas_prices import au_gas_prices_usd_per_mcf


def test_australia_deck_has_gas_marker_and_explicit_limits():
    terms = get_fiscal_terms("australia")
    assert "australia" in available_countries()
    assert terms.price_marker == "gas_au"
    assert terms.currency == "USD"
    assert terms.discount_rate is None
    assert terms.income_tax == {}
    assert "NOT_EVALUATED" in terms.notes
    assert terms.royalty.model == "not_evaluated"
    with pytest.raises(ValueError, match="caller-supplied royalty"):
        terms.royalty.rate_for("dry")


def test_convert_monthly_marker_prices_by_dimensional_cancellation():
    """Hand calculation: (AUD/GJ)*(GJ/Mcf)*(USD/AUD) = USD/Mcf.

    January: 10 * 1.5 * 0.8 = 12 USD/Mcf.
    February: 20 * 2 * 0.5 = 20 USD/Mcf.
    Inputs deliberately vary each month to detect constant-factor reuse.
    """
    assert au_gas_prices_usd_per_mcf(
        {"2025-01": 10.0, "2025-02": 20.0},
        gj_per_mcf={"2025-01": 1.5, "2025-02": 2.0},
        usd_per_aud={"2025-01": 0.8, "2025-02": 0.5},
    ) == {"2025-01": 12.0, "2025-02": 20.0}


@pytest.mark.parametrize("field", ["prices", "gj_per_mcf", "usd_per_aud"])
@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf"), True, None, "10"])
def test_conversion_rejects_invalid_inputs(field, bad):
    inputs = {
        "prices": {"2025-01": 10.0},
        "gj_per_mcf": {"2025-01": 1.5},
        "usd_per_aud": {"2025-01": 0.8},
    }
    inputs[field]["2025-01"] = bad
    with pytest.raises(ValueError, match="finite"):
        au_gas_prices_usd_per_mcf(
            inputs["prices"],
            gj_per_mcf=inputs["gj_per_mcf"],
            usd_per_aud=inputs["usd_per_aud"],
        )


@pytest.mark.parametrize("field", ["gj_per_mcf", "usd_per_aud"])
def test_conversion_requires_positive_heat_content_and_fx(field):
    inputs = {"gj_per_mcf": {"2025-01": 1.5}, "usd_per_aud": {"2025-01": 0.8}}
    inputs[field]["2025-01"] = 0.0
    with pytest.raises(ValueError, match="positive"):
        au_gas_prices_usd_per_mcf({"2025-01": 10.0}, **inputs)


@pytest.mark.parametrize("field", ["gj_per_mcf", "usd_per_aud"])
@pytest.mark.parametrize("periods", [{}, {"2025-02": 1.0}])
def test_conversion_requires_matching_months(field, periods):
    inputs = {"gj_per_mcf": {"2025-01": 1.5}, "usd_per_aud": {"2025-01": 0.8}}
    inputs[field] = periods
    with pytest.raises(ValueError, match="months"):
        au_gas_prices_usd_per_mcf({"2025-01": 10.0}, **inputs)


def test_zero_marker_price_and_empty_decks():
    """Hand calculation: zero price times finite positive factors is zero."""
    assert au_gas_prices_usd_per_mcf(
        {"2025-01": 0.0},
        gj_per_mcf={"2025-01": 1.5},
        usd_per_aud={"2025-01": 0.8},
    ) == {"2025-01": 0.0}
    assert au_gas_prices_usd_per_mcf({}, gj_per_mcf={}, usd_per_aud={}) == {}


def test_conversion_rejects_overflow():
    """Synthetic inputs whose product exceeds binary float range must fail."""
    with pytest.raises(ValueError, match="finite"):
        au_gas_prices_usd_per_mcf(
            {"2025-01": 1e300},
            gj_per_mcf={"2025-01": 1e300},
            usd_per_aud={"2025-01": 1.0},
        )


def _cashflow(gas_prices, oil_price, *, royalty=None):
    terms = get_fiscal_terms("australia")
    if royalty is not None:
        raw = asdict(terms)
        raw["royalty"] = royalty
        terms = validate_deck(raw)
    return CashflowEngine(
        AssumptionsManager(), "dry", fiscal_terms=terms
    ).generate_monthly_cashflow(
        pd.DataFrame(
            {
                "YEAR_MONTH": ["2025-01"],
                "MONTHLY_OIL_BBL": [0.0],
                "MONTHLY_GAS_MCF": [100.0],
            }
        ),
        {"drilling_monthly": {"2025-01": 0.0}},
        {"2025-01": oil_price},
        datetime(2025, 1, 1),
        gas_prices=gas_prices,
    )


def test_au_gas_revenue_uses_converted_marker_and_is_independent_of_oil():
    """Hand calculation: 10 AUD/GJ * 1.5 GJ/Mcf * 0.8 USD/AUD = 12
    USD/Mcf; 100 Mcf * 12 USD/Mcf = 1200 USD gross revenue.
    A caller-supplied synthetic 0.1 royalty rate yields 120 USD royalty.
    The two synthetic oil prices must have no effect on a pure-gas case.
    """
    prices = au_gas_prices_usd_per_mcf(
        {"2025-01": 10.0},
        gj_per_mcf={"2025-01": 1.5},
        usd_per_aud={"2025-01": 0.8},
    )
    royalty = {"model": "flat", "rate_by_dev_system": dict.fromkeys(DEV_SYSTEMS, 0.1)}
    low = _cashflow(prices, 1.0, royalty=royalty)
    high = _cashflow(prices, 999.0, royalty=royalty)
    assert [vars(cf) for cf in low] == [vars(cf) for cf in high]
    assert low[0].gas_revenue_usd == 1200.0
    assert low[0].total_revenue_usd == 1200.0
    assert low[0].royalty_usd == 120.0


@pytest.mark.parametrize("prices", [None, {}])
def test_au_gas_deck_cannot_silently_ignore_gas(prices):
    with pytest.raises(CashflowError, match="gas price"):
        _cashflow(prices, 999.0)


def test_au_gas_cashflow_requires_caller_supplied_royalty():
    with pytest.raises(ValueError, match="caller-supplied royalty"):
        _cashflow({"2025-01": 12.0}, 999.0)


@pytest.mark.parametrize(
    "field,value",
    [
        ("rate_by_dev_system", dict.fromkeys(DEV_SYSTEMS, 0.1)),
        ("bands", [{"max_rate_bpd": None, "rate": 0.1}]),
    ],
)
def test_unevaluated_royalty_cannot_carry_rates(field, value):
    raw = asdict(get_fiscal_terms("australia"))
    raw["royalty"] = {"model": "not_evaluated"}
    assert validate_deck(raw).royalty.model == "not_evaluated"
    raw["royalty"][field] = value
    with pytest.raises(FiscalTermsValidationError, match="must be omitted"):
        validate_deck(raw)
