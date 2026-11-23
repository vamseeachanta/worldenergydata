"""ProductionAPI12 NPV migration tests for issue #367."""

from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis import production_api12
from worldenergydata.bsee.analysis.production_api12 import ProductionAPI12Analysis


def test_production_api12_does_not_instantiate_legacy_npv_calculator():
    analyzer = ProductionAPI12Analysis()

    assert not hasattr(analyzer, "_npv_calculator")
    assert not hasattr(production_api12, "NPVCalculator")


def test_generate_revenue_table_uses_lower_tertiary_wti_prices(monkeypatch, tmp_path):
    prices = pd.DataFrame(
        {
            "Month": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "WTI_USD": [71.25, 73.50],
            "source": ["test", "test"],
        }
    )
    monkeypatch.setattr(
        production_api12, "load_extended_wti_prices", lambda **_: prices
    )

    analyzer = ProductionAPI12Analysis()
    api12_df = pd.DataFrame(
        {
            "PRODUCTION_DATE": [202401, 202402],
            "MON_O_PROD_VOL": [100.0, 200.0],
        }
    )
    cfg = {"Analysis": {"result_folder": str(tmp_path)}}

    revenue_df = analyzer.generate_revenue_table(cfg, api12_df)

    assert revenue_df["Avg Price (USD/bbl)"].tolist()[:2] == ["$71.25", "$73.50"]
    assert revenue_df["Revenue (USD)"].tolist()[:2] == ["$7,125.00", "$14,700.00"]


def test_calculate_npv_delegates_to_fdas_financial_layer(monkeypatch):
    fdas_npv = Mock(return_value=123.45)
    monkeypatch.setattr(production_api12, "fdas_calculate_npv", fdas_npv)

    analyzer = ProductionAPI12Analysis()
    cfg = {
        "economics": {
            "cost": {
                "discount_rate_annual": 0.12,
                "CAPEX": 1_000.0,
                "OPEX": 2.0,
            }
        }
    }
    revenue_df = pd.DataFrame(
        {
            "Month": [202401, 202402, ""],
            "Monthly Oil Production": [100.0, 200.0, ""],
            "Revenue (USD)": ["$1,000.00", "$3,000.00", "$4,000.00"],
        }
    )

    result = analyzer.calculate_npv(cfg, revenue_df)

    assert result == pytest.approx(123.45)
    fdas_npv.assert_called_once()
    cashflows, discount_rate = fdas_npv.call_args.args[:2]
    assert np.array_equal(cashflows, np.array([-1000.0, 800.0, 2600.0]))
    assert discount_rate == pytest.approx(0.12)
    assert fdas_npv.call_args.kwargs == {"period": "monthly"}
