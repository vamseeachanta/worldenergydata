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
