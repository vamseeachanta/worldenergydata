"""Synthetic Canada gas-chain examples with independent hand calculations.

All volumes, prices, dates and depth here are invented test inputs. No source
production is reproduced, and no gas-equivalent conversion is performed.
"""

import pandas as pd
import pytest

from worldenergydata.canada.reference_chain import run_canada_reference_chain
from worldenergydata.fdas.analysis.cashflow import CashflowError
from worldenergydata.production.unified.adapters.canada_adapter import CanadaAdapter
from worldenergydata.production.unified.query import ProductionQuery


class SyntheticGasLoader:
    def __init__(self, oil=(0.0, 0.0)):
        self.oil = oil

    def load_field_production(self, field_name):
        return pd.DataFrame(
            {
                "field_name": [field_name, field_name],
                "year": [2018, 2018],
                "month": [1, 2],
                "oil_bbl": self.oil,
                "gas_mcf": [100.0, 200.0],
                "water_bbl": [0.0, 0.0],
                "source": ["synthetic", "synthetic"],
            }
        )


def run_chain(gas_prices=None, oil=(0.0, 0.0)):
    return run_canada_reference_chain(
        adapter=CanadaAdapter(loader=SyntheticGasLoader(oil)),
        field_meta={"field_name": "Synthetic gas field", "water_depth_m": 0.0},
        field_name="Synthetic gas field",
        oil_price_usd_bbl=2.0,
        gas_prices=gas_prices,
    )


def test_pure_gas_revenue_reaches_chain_metrics():
    """Hand calculation: 100 Mcf * 3 USD/Mcf + 200 * 4 = 1100 USD.

    Oil is zero, so combined revenue is also 1100 USD. No royalty or cost
    expectation is asserted from the default non-Canadian assumptions.
    """
    metrics = run_chain({"2018-01": 3.0, "2018-02": 4.0})["pre_tax_metrics"]
    assert metrics["oil_revenue_usd"] == 0.0
    assert metrics["gas_revenue_usd"] == 1100.0
    assert metrics["gross_revenue_usd"] == 1100.0


def test_mixed_revenues_sum_without_double_counting():
    """Hand calculation: oil = (10 + 20) * 2 = 60 USD; gas = 1100 USD.

    Total revenue is 60 + 1100 = 1160 USD, independently of cashflow costs.
    """
    metrics = run_chain({"2018-01": 3.0, "2018-02": 4.0}, (10.0, 20.0))[
        "pre_tax_metrics"
    ]
    assert metrics["oil_revenue_usd"] == 60.0
    assert metrics["gas_revenue_usd"] == 1100.0
    assert metrics["gross_revenue_usd"] == 1160.0


def test_absent_gas_deck_preserves_oil_only_revenue():
    """Hand calculation: no priced gas; oil = (10 + 20) * 2 = 60 USD."""
    metrics = run_chain(oil=(10.0, 20.0))["pre_tax_metrics"]
    assert metrics["gross_revenue_usd"] == 60.0
    assert metrics["gas_revenue_usd"] is None


@pytest.mark.parametrize("deck", [{}, {"2018-01": 3.0}, {"2018-01": -1.0}])
def test_explicit_deck_keeps_existing_strict_gas_price_validation(deck):
    with pytest.raises(CashflowError, match="gas price"):
        run_chain(deck)


def test_explicit_zero_gas_prices_are_evaluated_as_zero_revenue():
    """Hand calculation: 100 * 0 + 200 * 0 = 0 USD."""
    metrics = run_chain({"2018-01": 0.0, "2018-02": 0.0})["pre_tax_metrics"]
    assert metrics["gross_revenue_usd"] == 0.0
    assert metrics["gas_revenue_usd"] == 0.0


@pytest.mark.parametrize("gas", ["missing", float("nan"), "bad", 0.0, 100.0])
@pytest.mark.parametrize("priced", [True, False])
def test_unknown_gas_is_rejected_only_when_priced(gas, priced):
    """Synthetic single-month inputs distinguish unknown gas from measured zero."""

    class GasInputLoader:
        def load_field_production(self, field_name):
            frame = (
                SyntheticGasLoader(oil=(10.0, 20.0))
                .load_field_production(field_name)
                .iloc[:1]
                .copy()
            )
            if gas == "missing":
                return frame.drop(columns="gas_mcf")
            frame["gas_mcf"] = gas
            return frame

    def evaluate():
        return run_canada_reference_chain(
            adapter=CanadaAdapter(loader=GasInputLoader()),
            field_meta={"field_name": "Synthetic gas field", "water_depth_m": 0.0},
            field_name="Synthetic gas field",
            oil_price_usd_bbl=2.0,
            gas_prices={"2018-01": 3.0} if priced else None,
        )["pre_tax_metrics"]

    if priced and (isinstance(gas, str) or pd.isna(gas)):
        with pytest.raises(CashflowError, match="gas"):
            evaluate()
    else:
        metrics = evaluate()
        expected_gas = gas * 3.0 if priced else None
        assert metrics["gas_revenue_usd"] == expected_gas
        assert metrics["gross_revenue_usd"] == 20.0 + (
            0.0 if expected_gas is None else expected_gas
        )


@pytest.mark.parametrize("gas", ["missing", float("nan"), "bad", 0.0, 100.0])
def test_adapter_preserves_unknown_gas_and_measured_volumes(gas):
    """Unknown gas stays NaN; measured 0 and 100 Mcf retain their values."""

    class GasInputLoader(SyntheticGasLoader):
        def load_field_production(self, field_name):
            frame = super().load_field_production(field_name)
            if gas == "missing":
                return frame.drop(columns="gas_mcf")
            frame["gas_mcf"] = gas
            return frame

    out = CanadaAdapter(loader=GasInputLoader()).fetch(
        ProductionQuery(regions=["canada"], fields=["Synthetic gas field"])
    )

    assert len(out) == 2
    if isinstance(gas, str) or pd.isna(gas):
        assert out["gas_mcf"].isna().all()
    else:
        assert out["gas_mcf"].tolist() == [gas, gas]
