"""Gas revenue input contract; all quantities below are synthetic.

Arithmetic basis: docs/domains/field-development/gas-revenue.md, monthly
revenue definition at revision 648d6de4. Independent hand calculation:
January 100 Mcf * 3 USD/Mcf = 300 USD; February 200 * 4 = 800 USD;
zero volume or zero price gives zero revenue. These are no market assumptions.
Public basis: EIA Natural Gas Prices, Definitions/Sources/Explanatory Notes,
Average Price of Deliveries to Consumers (undated, accessed 2026-10-19):
https://www.eia.gov/dnav/ng/TblDefs/ng_pri_sum_tbldef2.asp
The published price definition is revenue divided by associated sales volume.
Calendar basis: Python 3.11 datetime documentation, date.fromisoformat and
date constructor (https://docs.python.org/3.11/library/datetime.html).
The existing API requires YYYY-MM keys and finite nonnegative quantities;
Boolean flags are not measured volumes or realized prices.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from worldenergydata.fdas.analysis.cashflow import CashflowEngine, CashflowError
from worldenergydata.fdas.analysis.gas_revenue import monthly_gas_revenue
from worldenergydata.fdas.core.config import AssumptionsManager


def production(months=("2025-01", "2025-02"), volumes=(100.0, 200.0)):
    return pd.DataFrame(
        {
            "YEAR_MONTH": months,
            "MONTHLY_OIL_BBL": 0.0,
            "MONTHLY_GAS_MCF": pd.Series(volumes, dtype=object),
        }
    )


@pytest.mark.parametrize(
    "month",
    [
        None,
        float("nan"),
        "",
        "2025-1",
        "2025-00",
        "2025-13",
        "0000-01",
        "2025-01-01",
        " 2025-01",
        "2025-01\n",
        "２０２５-01",
    ],
)
def test_invalid_period_is_not_a_priced_month(month):
    frame = production(months=(month,), volumes=(100.0,))
    with pytest.raises(ValueError, match="production month.*YYYY-MM"):
        monthly_gas_revenue(frame, {str(month): 3.0})


def test_missing_month_column_has_a_validation_error():
    with pytest.raises(ValueError, match="YEAR_MONTH"):
        monthly_gas_revenue(production().drop(columns="YEAR_MONTH"), {})


@pytest.mark.parametrize("value", [True, False, np.bool_(True), np.bool_(False)])
@pytest.mark.parametrize("quantity", ["volume", "price"])
def test_boolean_is_not_a_gas_quantity(value, quantity):
    frame = production(volumes=(value, 200.0) if quantity == "volume" else (100, 200))
    prices = {"2025-01": value if quantity == "price" else 3.0, "2025-02": 4.0}
    with pytest.raises(ValueError, match=f"gas {quantity}"):
        monthly_gas_revenue(frame, prices)


@pytest.mark.parametrize("quantity", ["volume", "price"])
def test_unrepresentable_integer_has_a_validation_error(quantity):
    # Synthetic stress input, deliberately beyond binary64's finite range.
    huge = 10**400
    frame = production(volumes=(huge, 200.0) if quantity == "volume" else (100, 200))
    prices = {"2025-01": huge if quantity == "price" else 3.0, "2025-02": 4.0}
    with pytest.raises(ValueError, match=f"gas {quantity}"):
        monthly_gas_revenue(frame, prices)


def test_hand_calculated_revenues_keep_month_alignment():
    volumes, revenues = monthly_gas_revenue(
        production(months=("2025-02", "2025-01"), volumes=(200.0, 100.0)),
        {"2025-01": 3.0, "2025-02": 4.0},
    )
    assert volumes == {"2025-01": 100.0, "2025-02": 200.0}
    assert revenues == {"2025-01": 300.0, "2025-02": 800.0}


def test_explicit_zero_volume_and_price_remain_valid():
    _, revenues = monthly_gas_revenue(
        production(volumes=(0.0, 200.0)), {"2025-01": 3.0, "2025-02": 0.0}
    )
    assert revenues == {"2025-01": 0.0, "2025-02": 0.0}


@pytest.mark.parametrize("month", ["0001-01", "9999-12"])
def test_calendar_bounds_are_valid_priced_months(month):
    # Source for bounds: Python 3.11 datetime docs, MINYEAR and MAXYEAR.
    _, revenues = monthly_gas_revenue(
        production(months=(month,), volumes=(100.0,)), {month: 3.0}
    )
    assert revenues == {month: 300.0}


def test_numeric_strings_remain_compatible():
    _, revenues = monthly_gas_revenue(
        production(volumes=("100.0", "200.0")), {"2025-01": "3.0", "2025-02": "4.0"}
    )
    assert revenues == {"2025-01": 300.0, "2025-02": 800.0}


@pytest.mark.parametrize("price", [True, np.bool_(False), 10**400])
def test_cashflow_reports_invalid_price_as_cashflow_error(price):
    with pytest.raises(CashflowError, match="gas price"):
        CashflowEngine(AssumptionsManager(), "dry").generate_monthly_cashflow(
            production(),
            {"drilling_monthly": {"2025-01": 0.0}},
            {},
            datetime(2025, 1, 1),
            gas_prices={"2025-01": price, "2025-02": 4.0},
        )


def test_cashflow_reports_invalid_period_as_cashflow_error():
    with pytest.raises(CashflowError, match="production month.*YYYY-MM"):
        CashflowEngine(AssumptionsManager(), "dry").generate_monthly_cashflow(
            production(months=("2025-13",), volumes=(100.0,)),
            {"drilling_monthly": {"2025-01": 0.0}},
            {},
            datetime(2025, 1, 1),
            gas_prices={"2025-13": 3.0},
        )
