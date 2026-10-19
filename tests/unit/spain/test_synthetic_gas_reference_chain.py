"""Offline Spain chain tests with SYNTHETIC production and gas prices."""

import socket

import pandas as pd
import pytest

from worldenergydata.production.unified.adapters.spain_cores_adapter import (
    SpainCoresAdapter,
)
from worldenergydata.spain.production.cores_loader import GWH_TO_MCF, parse_cores_frame
from worldenergydata.spain.reference_chain import run_spain_reference_chain


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("Tests must remain offline")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


class SyntheticGasLoader:
    def load_field_production(self, field_name):
        frame = pd.DataFrame(
            {
                "Year": [2025, 2025],
                "Month": ["January", "February"],
                field_name: [1.0, 2.0],
            }
        )
        result = parse_cores_frame(frame, product="gas")
        result["oil_bbl"] = 0.0
        return result


def test_synthetic_pure_gas_chain_uses_existing_volume_conversion():
    result = run_spain_reference_chain(
        adapter=SpainCoresAdapter(loader=SyntheticGasLoader()),
        field_meta={"field_name": "Synthetic gas field", "environment": "onshore"},
        field_name="Synthetic gas field",
        gas_prices={"2025-01": 3.0, "2025-02": 3.0},
    )
    assert result["fdas_production"]["MONTHLY_GAS_MCF"].tolist() == [
        GWH_TO_MCF,
        2 * GWH_TO_MCF,
    ]
    metrics = result["pre_tax_metrics"]
    assert metrics["gross_revenue_usd"] == 3 * GWH_TO_MCF * 3.0
    assert metrics["royalty_usd"] == metrics["gross_revenue_usd"] * 0.125
    assert metrics["net_cashflow_usd"] == metrics["gross_revenue_usd"] * 0.875
    assert result["economics_label"] == "chain_plumbing_pre_tax"
    assert metrics["onshore_model_mismatch"] is True


def test_synthetic_pure_gas_chain_without_deck_retains_zero_revenue():
    result = run_spain_reference_chain(
        adapter=SpainCoresAdapter(loader=SyntheticGasLoader()),
        field_meta={"field_name": "Synthetic gas field", "environment": "onshore"},
        field_name="Synthetic gas field",
    )
    assert result["pre_tax_metrics"]["gross_revenue_usd"] == 0.0


class SyntheticVolumeLoader:
    """Synthetic, already-normalized volumes; no heating-value assumption."""

    def __init__(self, oil):
        self.oil = oil

    def load_field_production(self, field_name):
        # Deliberate test inputs, not measured data or engineering constants.
        return pd.DataFrame(
            {
                "field_name": [field_name, field_name],
                "year": [2025, 2025],
                "month": [1, 2],
                "oil_bbl": self.oil,
                "gas_mcf": [100.0, 200.0],
            }
        )


@pytest.mark.parametrize(
    "oil, deck, oil_revenue, gas_revenue, gross",
    [
        ((0.0, 0.0), {"2025-01": 3.0, "2025-02": 4.0}, 0.0, 1100.0, 1100.0),
        ((10.0, 20.0), {"2025-01": 3.0, "2025-02": 4.0}, 1500.0, 1100.0, 2600.0),
        ((10.0, 20.0), {"2025-01": 0.0, "2025-02": 0.0}, 1500.0, 0.0, 1500.0),
        ((10.0, 20.0), None, 1500.0, None, 1500.0),
        ((0.0, 0.0), None, 0.0, None, 0.0),
    ],
)
def test_revenue_components_distinguish_unpriced_gas(
    oil, deck, oil_revenue, gas_revenue, gross
):
    """Independent hand calculation for synthetic inputs, in USD.

    Basis: docs/domains/field-development/gas-revenue.md, Monthly gas revenue:
    revenue = monthly volume * realized price; gross = oil + priced gas.
    External basis: EIA Natural Gas Prices, Definitions/Sources/Explanatory
    Notes, "Average Price of Deliveries to Consumers" (undated, read 2026-10-19),
    https://www.eia.gov/dnav/ng/TblDefs/ng_pri_sum_tbldef2.asp:
    price = reported revenue / associated sales volume.
    Chosen oil price = 50 USD/bbl: (10 + 20) * 50 = 1500 (pure gas: 0).
    Chosen gas prices = 3 and 4 USD/Mcf: 100 * 3 + 200 * 4 = 1100.
    Mixed gross = 1500 + 1100 = 2600. Explicit zero gas prices yield 0;
    an omitted deck establishes no gas value, represented by None.
    No royalty/cost rate or GWh-to-Mcf conversion is assumed here.
    """
    result = run_spain_reference_chain(
        adapter=SpainCoresAdapter(loader=SyntheticVolumeLoader(oil)),
        field_meta={"field_name": "Synthetic field", "environment": "onshore"},
        field_name="Synthetic field",
        oil_price_usd_bbl=50.0,  # Synthetic input; calculation is documented above.
        gas_prices=deck,
    )
    metrics = result["pre_tax_metrics"]
    assert metrics["oil_revenue_usd"] == oil_revenue
    assert metrics["gas_revenue_usd"] == gas_revenue
    assert metrics["gross_revenue_usd"] == gross
