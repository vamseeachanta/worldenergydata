"""Australia gas screening uses explicit prices and no assumed fiscal rates."""

from datetime import datetime

import pandas as pd
import pytest
import yaml


def test_australia_marker_and_unknown_royalty():
    """Issue #824 requires an AU gas marker; an unknown rate is not zero."""
    from worldenergydata.fdas.fiscal import available_countries, get_fiscal_terms

    assert "australia" in available_countries()
    terms = get_fiscal_terms("australia")
    assert terms.price_marker == "gas_au"
    assert terms.currency == "USD"
    assert terms.royalty.model == "not_evaluated"
    assert terms.discount_rate is None
    assert terms.income_tax == {}
    with pytest.raises(ValueError, match="NOT_EVALUATED"):
        terms.royalty.rate_for("dry")


@pytest.mark.parametrize("field", ["rate_by_dev_system", "bands"])
def test_unknown_royalty_rejects_embedded_rates(field):
    """Synthetic rates cannot be hidden inside the unknown-royalty model."""
    from importlib import resources

    from worldenergydata.fdas.fiscal import FiscalTermsValidationError, validate_deck

    raw = yaml.safe_load(
        resources.files("worldenergydata.fdas.fiscal.decks")
        .joinpath("australia.yml")
        .read_text()
    )
    raw["royalty"][field] = []
    with pytest.raises(FiscalTermsValidationError, match=field):
        validate_deck(raw)


def test_convert_aud_energy_prices_with_explicit_monthly_factors():
    """Synthetic hand calculation, not observed market or gas-property values.

    NIST SP 811 (2008), section 7.11: multiply quantities and cancel units.
    January: 10 AUD/GJ * 0.5 USD/AUD * 2 GJ/Mcf = 10 USD/Mcf.
    February: 20 AUD/GJ * 0.25 USD/AUD * 0.5 GJ/Mcf = 2.5 USD/Mcf.
    The deliberately different factors establish per-month conversion.
    """
    from worldenergydata.fdas.fiscal.gas_prices import convert_australia_gas_prices

    prices = {"2025-01": 10.0, "2025-02": 20.0}
    assert convert_australia_gas_prices(
        prices,
        usd_per_aud={"2025-01": 0.5, "2025-02": 0.25},
        gj_per_mcf={"2025-01": 2.0, "2025-02": 0.5},
    ) == {"2025-01": 10.0, "2025-02": 2.5}
    assert prices == {"2025-01": 10.0, "2025-02": 20.0}


@pytest.mark.parametrize("field", ["prices_aud_per_gj", "usd_per_aud", "gj_per_mcf"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0, True, None])
def test_conversion_rejects_invalid_values(field, value):
    """Synthetic invalid inputs; no physical acceptance limits are asserted."""
    from worldenergydata.fdas.fiscal.gas_prices import convert_australia_gas_prices

    inputs = {
        "prices_aud_per_gj": {"2025-01": 10.0},
        "usd_per_aud": {"2025-01": 0.5},
        "gj_per_mcf": {"2025-01": 2.0},
    }
    inputs[field] = {"2025-01": value}
    with pytest.raises((ValueError, TypeError), match=field):
        convert_australia_gas_prices(**inputs)


@pytest.mark.parametrize("field", ["usd_per_aud", "gj_per_mcf"])
def test_conversion_requires_positive_factors(field):
    """A zero exchange or energy factor cannot define a unit conversion."""
    from worldenergydata.fdas.fiscal.gas_prices import convert_australia_gas_prices

    inputs = {"usd_per_aud": {"2025-01": 0.5}, "gj_per_mcf": {"2025-01": 2.0}}
    inputs[field]["2025-01"] = 0.0
    with pytest.raises(ValueError, match=field):
        convert_australia_gas_prices({"2025-01": 10.0}, **inputs)


@pytest.mark.parametrize("field", ["usd_per_aud", "gj_per_mcf"])
@pytest.mark.parametrize("months", [{}, {"2025-01": 1.0, "2025-02": 1.0}])
def test_conversion_requires_exact_month_coverage(field, months):
    """Missing factors and unused factors both indicate mismatched series."""
    from worldenergydata.fdas.fiscal.gas_prices import convert_australia_gas_prices

    inputs = {"usd_per_aud": {"2025-01": 0.5}, "gj_per_mcf": {"2025-01": 2.0}}
    inputs[field] = months
    with pytest.raises(ValueError, match="months"):
        convert_australia_gas_prices({"2025-01": 10.0}, **inputs)


@pytest.mark.parametrize("month", ["2025-1", "2025-13", "0000-01", None])
def test_conversion_requires_valid_months(month):
    from worldenergydata.fdas.fiscal.gas_prices import convert_australia_gas_prices

    with pytest.raises(ValueError, match="YYYY-MM"):
        convert_australia_gas_prices(
            {month: 10.0}, usd_per_aud={month: 0.5}, gj_per_mcf={month: 2.0}
        )


def test_conversion_allows_explicit_zero_price_but_rejects_overflow():
    """Hand calculation: zero AUD/GJ times finite factors is zero USD/Mcf."""
    from worldenergydata.fdas.fiscal.gas_prices import convert_australia_gas_prices

    factors = {"usd_per_aud": {"2025-01": 0.5}, "gj_per_mcf": {"2025-01": 2.0}}
    assert convert_australia_gas_prices({"2025-01": 0.0}, **factors) == {"2025-01": 0.0}
    with pytest.raises(ValueError, match="Non-finite"):
        convert_australia_gas_prices(
            {"2025-01": 1e308},
            usd_per_aud={"2025-01": 1e308},
            gj_per_mcf={"2025-01": 1e308},
        )


def _production():
    """Synthetic two-month, gas-only production; no measured data."""
    return pd.DataFrame(
        {
            "YEAR_MONTH": ["2025-01", "2025-02"],
            "MONTHLY_OIL_BBL": [0.0, 0.0],
            "MONTHLY_GAS_MCF": [100.0, 200.0],
        }
    )


def _engine():
    from worldenergydata.fdas.analysis.cashflow import CashflowEngine
    from worldenergydata.fdas.core.config import AssumptionsManager
    from worldenergydata.fdas.fiscal import get_fiscal_terms

    return CashflowEngine(
        AssumptionsManager(), "dry", fiscal_terms=get_fiscal_terms("australia")
    )


@pytest.mark.parametrize("rate", [None, 0.1])
def test_australia_cannot_silently_omit_gas_prices(rate):
    from worldenergydata.fdas.analysis.cashflow import CashflowError

    with pytest.raises(CashflowError, match="gas_au.*gas_prices"):
        _engine().generate_monthly_cashflow(
            _production(), {}, {}, datetime(2025, 1, 1), royalty_rate=rate
        )


def test_australia_cannot_fill_missing_gas_month_with_wti():
    from worldenergydata.fdas.analysis.cashflow import CashflowError

    with pytest.raises(CashflowError, match="Missing gas price.*2025-02"):
        _engine().generate_monthly_cashflow(
            _production(),
            {},
            {"2025-01": 999.0, "2025-02": 999.0},
            datetime(2025, 1, 1),
            gas_prices={"2025-01": 10.0},
            royalty_rate=0.1,
        )


def test_australia_requires_explicit_royalty_for_cashflow():
    with pytest.raises(ValueError, match="NOT_EVALUATED"):
        _engine().generate_monthly_cashflow(
            _production(),
            {},
            {},
            datetime(2025, 1, 1),
            gas_prices={"2025-01": 10.0, "2025-02": 2.5},
        )


@pytest.mark.parametrize("oil_price", [1.0, 999.0])
def test_australia_gas_cashflow_is_independent_of_wti(oil_price):
    """Independent synthetic hand calculation; NIST SP 811 (2008), 7.11.

    January price = 10 * 0.5 * 2 = 10 USD/Mcf; 100 Mcf gives 1000 USD.
    February price = 20 * 0.25 * 0.5 = 2.5 USD/Mcf; 200 Mcf gives 500 USD.
    A caller-supplied synthetic royalty fraction of 0.1 gives 100 and 50 USD;
    net receipts are 900 and 450 USD with dry-system zero-cost assumptions.
    This fraction is a test input, not an Australian fiscal rate. Oil volume
    is zero, so changing its price contributes zero revenue in both cases.
    """
    from worldenergydata.fdas.fiscal.gas_prices import convert_australia_gas_prices

    prices = convert_australia_gas_prices(
        {"2025-01": 10.0, "2025-02": 20.0},
        usd_per_aud={"2025-01": 0.5, "2025-02": 0.25},
        gj_per_mcf={"2025-01": 2.0, "2025-02": 0.5},
    )
    flows = _engine().generate_monthly_cashflow(
        _production(),
        {"drilling_monthly": {"2025-01": 0.0}},
        {"2025-01": oil_price, "2025-02": oil_price},
        datetime(2025, 1, 1),
        gas_prices=prices,
        royalty_rate=0.1,
    )
    assert [cf.oil_revenue_usd for cf in flows] == [0.0, 0.0]
    assert [cf.gas_revenue_usd for cf in flows] == [1000.0, 500.0]
    assert [cf.royalty_usd for cf in flows] == [100.0, 50.0]
    assert [cf.net_cashflow_usd for cf in flows] == [900.0, 450.0]


@pytest.mark.parametrize("rate", [-0.1, 1.1, float("nan"), float("inf"), True, 10**400])
def test_explicit_royalty_fraction_is_validated(rate):
    """Bounds are the existing fiscal schema's fraction contract, not tax law."""
    with pytest.raises(ValueError, match="royalty_rate"):
        _engine().calculate_royalty({"2025-01": 1000.0}, royalty_rate=rate)


def test_wrapper_passes_australia_terms_and_explicit_royalty():
    """Synthetic hand calculation: 100*10*0.9=900; 200*2.5*0.9=450 USD."""
    from worldenergydata.fdas.analysis.cashflow import generate_monthly_cashflow
    from worldenergydata.fdas.core.config import AssumptionsManager
    from worldenergydata.fdas.fiscal import get_fiscal_terms

    frame = generate_monthly_cashflow(
        _production(),
        AssumptionsManager(),
        "dry",
        fiscal_terms=get_fiscal_terms("australia"),
        gas_prices={"2025-01": 10.0, "2025-02": 2.5},
        royalty_rate=0.1,
        drilling_timeline={"drilling_monthly": {"2025-01": 0.0}},
        wti_prices={},
        first_oil_date=datetime(2025, 1, 1),
    )
    assert frame["net_cashflow_usd"].tolist() == [900.0, 450.0]
