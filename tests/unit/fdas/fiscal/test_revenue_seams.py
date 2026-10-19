"""Fiscal revenue seams; prices and volumes below are synthetic inputs."""

import pytest

from worldenergydata.fdas.analysis.cashflow import CashflowEngine, CashflowError
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.fiscal import get_fiscal_terms


def test_brent_deck_selects_explicit_marker_prices():
    """Hand calculation: 100 bbl * (80 - 2) USD/bbl = 7,800 USD.

    Inputs are synthetic, not observed market prices. Revenue = price * quantity:
    OpenStax, Principles of Economics 3e (2022), section 8.2.
    """
    engine = CashflowEngine(
        AssumptionsManager(), fiscal_terms=get_fiscal_terms("norway")
    )
    result = engine.calculate_revenue(
        {"2025-01": 100},
        {"2025-01": 60},
        oil_differential=-2,
        oil_prices_by_marker={"brent": {"2025-01": 80}},
    )
    assert result == {"2025-01": 7800}


@pytest.mark.parametrize("country", ["us_gom", "norway", "uk"])
def test_deck_requires_price_for_every_production_month(country):
    """A missing observation cannot be replaced by an assumed market price."""
    terms = get_fiscal_terms(country)
    engine = CashflowEngine(AssumptionsManager(), fiscal_terms=terms)
    with pytest.raises(CashflowError, match="2025-01"):
        engine.calculate_revenue(
            {"2025-01": 100}, {}, oil_prices_by_marker={terms.price_marker: {}}
        )


@pytest.mark.parametrize(
    "field, value",
    [
        ("volume", -1),
        ("volume", float("nan")),
        ("volume", float("inf")),
        ("volume", True),
        ("price", float("nan")),
        ("price", float("inf")),
        ("price", None),
        ("price", True),
        ("differential", float("nan")),
        ("differential", float("inf")),
    ],
)
def test_fiscal_revenue_rejects_invalid_inputs(field, value):
    """Invalid inputs cannot produce a finite, qualified revenue observation."""
    inputs = {"volume": 100, "price": 80, "differential": 0}
    inputs[field] = value
    engine = CashflowEngine(
        AssumptionsManager(), fiscal_terms=get_fiscal_terms("us_gom")
    )
    with pytest.raises(CashflowError, match=field):
        engine.calculate_revenue(
            {"2025-01": inputs["volume"]},
            {"2025-01": inputs["price"]},
            inputs["differential"],
        )


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"currency": "EUR"}, "currency"),
        ({"price_marker": "gas_hh"}, "oil price_marker"),
        ({"price_marker": "gas_ttf"}, "oil price_marker"),
    ],
)
def test_fiscal_revenue_rejects_incompatible_units(changes, message):
    from dataclasses import replace

    terms = replace(get_fiscal_terms("us_gom"), **changes)
    engine = CashflowEngine(AssumptionsManager(), fiscal_terms=terms)
    with pytest.raises(CashflowError, match=message):
        engine.calculate_revenue(
            {"2025-01": 100},
            {"2025-01": 80},
            oil_prices_by_marker={terms.price_marker: {"2025-01": 80}},
        )


def test_marker_prices_reach_combined_gas_cashflow_and_wrapper():
    """Hand calculation: oil 100*80=8,000; gas 50*4=200; total=8,200 USD.

    All inputs are synthetic. Costs and royalties are explicitly zero here.
    Revenue = price * quantity: OpenStax, Economics 3e (2022), section 8.2.
    """
    from datetime import datetime

    import pandas as pd

    from worldenergydata.fdas.analysis.cashflow import generate_monthly_cashflow

    assumptions = AssumptionsManager(
        pd.DataFrame(
            {
                "DEV_SYSTEM": ["default"],
                "HOST_CAPEX_MM": [0],
                "MODU_LOADED_DAYRATE_MM": [0],
                "VARIABLE_OPEX_$/BBL": [0],
            }
        )
    )
    production = pd.DataFrame(
        {
            "YEAR_MONTH": ["2025-01"],
            "MONTHLY_OIL_BBL": [100],
            "MONTHLY_GAS_MCF": [50],
        }
    )
    frame = generate_monthly_cashflow(
        production,
        assumptions,
        fiscal_terms=get_fiscal_terms("norway"),
        drilling_timeline={"drilling_monthly": {"2025-01": 0}},
        first_oil_date=datetime(2025, 1, 1),
        wti_prices={"2025-01": 60},
        oil_prices_by_marker={"brent": {"2025-01": 80}},
        gas_prices={"2025-01": 4},
    )
    assert frame["oil_revenue_usd"].tolist() == [8000]
    assert frame["gas_revenue_usd"].tolist() == [200]
    assert frame["net_cashflow_usd"].tolist() == [8200]


def test_fiscal_cashflow_rejects_duplicate_production_months():
    """Two rows for the same month must not overwrite one volume silently."""
    from datetime import datetime

    import pandas as pd

    engine = CashflowEngine(
        AssumptionsManager(), fiscal_terms=get_fiscal_terms("us_gom")
    )
    production = pd.DataFrame(
        {
            "YEAR_MONTH": ["2025-01", "2025-01"],
            "MONTHLY_OIL_BBL": [100, 200],
        }
    )
    with pytest.raises(CashflowError, match="Duplicate production"):
        engine.generate_monthly_cashflow(
            production,
            {"drilling_monthly": {"2025-01": 0}},
            {"2025-01": 80},
            datetime(2025, 1, 1),
        )


@pytest.mark.parametrize("marker_prices", [None, {}, {"wti": {"2025-01": 60}}])
def test_brent_cannot_fall_back_to_wti(marker_prices):
    engine = CashflowEngine(
        AssumptionsManager(), fiscal_terms=get_fiscal_terms("norway")
    )
    with pytest.raises(CashflowError, match="brent"):
        engine.calculate_revenue(
            {"2025-01": 100},
            {"2025-01": 60},
            oil_prices_by_marker=marker_prices,
        )


@pytest.mark.parametrize("price, expected", [(0, 0), (-10, -1000)])
def test_zero_and_negative_oil_prices_are_explicit_inputs(price, expected):
    """Synthetic hand calculation: 100 bbl * 0 or -10 USD/bbl = 0 or -1,000 USD.

    Revenue identity: OpenStax, Economics 3e (2022), section 8.2.
    """
    engine = CashflowEngine(
        AssumptionsManager(), fiscal_terms=get_fiscal_terms("us_gom")
    )
    assert engine.calculate_revenue({"2025-01": 100}, {"2025-01": price}) == {
        "2025-01": expected
    }
