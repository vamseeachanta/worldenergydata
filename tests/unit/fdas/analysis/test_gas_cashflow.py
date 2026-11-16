"""Offline cashflow tests using SYNTHETIC volumes and USD/Mcf prices."""

import socket
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from worldenergydata.fdas.analysis.cashflow import (
    CashflowEngine,
    CashflowError,
    generate_monthly_cashflow,
)
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.core.financial import calculate_npv
from worldenergydata.fdas.fiscal import get_fiscal_terms


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("Tests must remain offline")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def synthetic_production(oil=(0.0, 0.0), gas=(100.0, 200.0)):
    return pd.DataFrame(
        {
            "YEAR_MONTH": ["2025-01", "2025-02"],
            "MONTHLY_OIL_BBL": oil,
            "MONTHLY_GAS_MCF": gas,
        }
    )


def run_cashflow(production, gas_prices, fiscal_terms=None):
    # Synthetic price fixture; zero oil volume contributes zero oil revenue.
    oil_prices = {"2025-01": 75.0, "2025-02": 75.0}
    return CashflowEngine(
        AssumptionsManager(), "dry", fiscal_terms=fiscal_terms
    ).generate_monthly_cashflow(
        production,
        {"drilling_monthly": {"2025-01": 0.0}},
        oil_prices,
        datetime(2025, 1, 1),
        gas_prices=gas_prices,
        oil_prices_by_marker=(
            {fiscal_terms.price_marker: oil_prices} if fiscal_terms else None
        ),
    )


def test_synthetic_pure_gas_revenue_royalty_and_monthly_npv():
    flows = run_cashflow(
        synthetic_production(), dict.fromkeys(["2025-01", "2025-02"], 3.0)
    )
    assert [cf.oil_revenue_usd for cf in flows] == [0.0, 0.0]
    assert [cf.gas_production_mcf for cf in flows] == [100.0, 200.0]
    assert [cf.gas_revenue_usd for cf in flows] == [300.0, 600.0]
    assert [cf.total_revenue_usd for cf in flows] == [300.0, 600.0]
    assert [cf.royalty_usd for cf in flows] == [37.5, 75.0]
    net = np.array([cf.net_cashflow_usd for cf in flows])
    assert net.tolist() == [262.5, 525.0]
    assert calculate_npv(net, 0.12) == pytest.approx(262.5 + 525.0 / 1.12 ** (1 / 12))
    legacy = run_cashflow(synthetic_production(), None)
    assert calculate_npv(np.array([cf.net_cashflow_usd for cf in legacy]), 0.12) == 0.0


def test_synthetic_mixed_revenues_add_and_feed_fiscal_royalty():
    flows = run_cashflow(
        synthetic_production(oil=(10.0, 20.0)),
        {"2025-01": 3.0, "2025-02": 4.0},
    )
    assert [cf.oil_revenue_usd for cf in flows] == [750.0, 1500.0]
    assert [cf.gas_revenue_usd for cf in flows] == [300.0, 800.0]
    assert [cf.total_revenue_usd for cf in flows] == [1050.0, 2300.0]
    assert [cf.royalty_usd for cf in flows] == [131.25, 287.5]
    assert [cf.net_cashflow_usd for cf in flows] == [838.75, 1852.5]
    no_royalty = run_cashflow(
        synthetic_production(),
        {"2025-01": 3.0, "2025-02": 3.0},
        get_fiscal_terms("norway"),
    )
    assert [cf.net_cashflow_usd for cf in no_royalty] == [300.0, 600.0]


@pytest.mark.parametrize("price", [float("nan"), float("inf"), -1.0])
def test_invalid_gas_price_is_rejected(price):
    with pytest.raises(CashflowError, match="gas price"):
        run_cashflow(synthetic_production(), {"2025-01": price, "2025-02": 3.0})


@pytest.mark.parametrize("gas", [float("nan"), float("inf"), -1.0])
def test_invalid_gas_volume_is_rejected(gas):
    with pytest.raises(CashflowError, match="gas volume"):
        run_cashflow(
            synthetic_production(gas=(gas, 100.0)), {"2025-01": 3.0, "2025-02": 3.0}
        )


@pytest.mark.parametrize("deck", [{}, {"2025-01": 3.0}])
def test_incomplete_gas_deck_is_rejected(deck):
    with pytest.raises(CashflowError, match="gas price"):
        run_cashflow(synthetic_production(), deck)


def test_explicit_zero_price_is_allowed():
    flows = run_cashflow(synthetic_production(), {"2025-01": 0.0, "2025-02": 0.0})
    assert [cf.total_revenue_usd for cf in flows] == [0.0, 0.0]


def test_gas_deck_requires_volume_column_and_unique_periods():
    frame = synthetic_production().drop(columns="MONTHLY_GAS_MCF")
    with pytest.raises(CashflowError, match="MONTHLY_GAS_MCF"):
        run_cashflow(frame, {"2025-01": 3.0, "2025-02": 3.0})
    frame = synthetic_production()
    frame["YEAR_MONTH"] = "2025-01"
    with pytest.raises(CashflowError, match="Duplicate"):
        run_cashflow(frame, {"2025-01": 3.0})


def test_no_deck_ignores_gas_and_preserves_legacy_serialization():
    oil_only = synthetic_production(oil=(10.0, 20.0)).drop(columns="MONTHLY_GAS_MCF")
    with_gas = synthetic_production(oil=(10.0, 20.0), gas=(float("nan"), -1.0))
    assert [vars(cf) for cf in run_cashflow(oil_only, None)] == [
        vars(cf) for cf in run_cashflow(with_gas, None)
    ]
    assert "gas_revenue_usd" not in vars(run_cashflow(oil_only, None)[0])


def test_convenience_wrapper_forwards_gas_deck():
    result = generate_monthly_cashflow(
        synthetic_production(),
        AssumptionsManager(),
        "dry",
        drilling_timeline={"drilling_monthly": {"2025-01": 0.0}},
        wti_prices={},
        first_oil_date=datetime(2025, 1, 1),
        gas_prices={"2025-01": 3.0, "2025-02": 3.0},
    )
    assert result["gas_revenue_usd"].tolist() == [300.0, 600.0]
    assert result["net_cashflow_usd"].tolist() == [262.5, 525.0]
