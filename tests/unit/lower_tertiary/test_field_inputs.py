"""
Tests for Lower Tertiary NPV field configuration loading and financial calculations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tests.test_markers import unit  # noqa: E402
from worldenergydata.lower_tertiary.npv import (  # noqa: E402
    calculate_monthly_financials,
    load_field_inputs,
    load_lease_mapping,
    summarize_field_financials,
)


@unit
class TestLowerTertiaryFieldInputs:
    """Validate modular field inputs and lease mappings."""

    @pytest.fixture(scope="class")
    def config_paths(cls):  # type: ignore[override]
        fields_dir = PROJECT_ROOT / "config/analysis/lower_tertiary/fields"
        lease_mapping_path = (
            PROJECT_ROOT / "config/analysis/lower_tertiary/lease_mapping_fdas.yml"
        )
        return fields_dir, lease_mapping_path

    @pytest.fixture(scope="class")
    def econ_config(cls):  # type: ignore[override]
        return {
            "commodity_prices": {
                "oil": {"base_case": {"wti_usd_per_bbl": 75.0}},
                "gas": {"base_case": {"henry_hub_usd_per_mcf": 3.50}},
            },
            "fiscal_terms": {
                "royalty": {"rate": 0.1875},
                "taxes": {"federal_income_tax": {"rate": 0.21}},
            },
            "financial_metrics": {
                "discount_rates": {"primary_discount_rate": 0.10},
            },
        }

    def test_load_field_inputs_merges_verified_leases(self, config_paths):
        fields_dir, lease_mapping_path = config_paths
        lease_mapping = load_lease_mapping(lease_mapping_path)

        field_inputs = load_field_inputs(
            fields_dir, lease_mapping, status_filter="producing"
        )

        assert "jack_st_malo" in field_inputs
        leases = field_inputs["jack_st_malo"]["leases"]
        expected_leases = {
            "G21245",
            "G18753",
            "G18745",
            "G17015",
            "G17016",
            "G20394",
        }
        assert set(leases) == expected_leases

    def test_status_filter_excludes_non_producing_fields(self, config_paths):
        fields_dir, lease_mapping_path = config_paths
        lease_mapping = load_lease_mapping(lease_mapping_path)

        field_inputs = load_field_inputs(
            fields_dir, lease_mapping, status_filter="producing"
        )

        assert "kaskida" not in field_inputs
        assert "tiber" not in field_inputs
        assert "shenandoah" not in field_inputs

    def test_calculate_monthly_financials_returns_expected_components(
        self, econ_config
    ):
        monthly = pd.DataFrame(
            {
                "field": ["Sample", "Sample"],
                "date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
                "oil_bbl": [1000.0, 500.0],
                "gas_mcf": [6000.0, 3000.0],
            }
        )

        result = calculate_monthly_financials(monthly, econ_config, opex_per_boe=15.0)

        assert {
            "oil_revenue",
            "gas_revenue",
            "total_revenue",
            "royalty",
            "operating_cash_flow",
        }.issubset(result.columns)
        total_revenue = result["total_revenue"].sum()
        expected_revenue = (1500.0 * 75.0) + (9000.0 * 3.50)
        assert total_revenue == pytest.approx(expected_revenue)

    def test_summarize_field_financials_computes_discounted_cash_flow(
        self, econ_config
    ):
        monthly = pd.DataFrame(
            {
                "field": ["Sample", "Sample"],
                "date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
                "oil_bbl": [0.0, 0.0],
                "gas_mcf": [0.0, 0.0],
                "total_revenue": [0.0, 0.0],
                "royalty": [0.0, 0.0],
                "opex": [0.0, 0.0],
                "operating_cash_flow": [120_000_000.0, 100_000_000.0],
            }
        )

        field_info = {
            "field_id": "sample",
            "display_name": "Sample Field",
            "first_oil": pd.Timestamp("2024-01-01"),
            "capex": {"total_mm_usd": 150.0},
        }

        summary = summarize_field_financials(monthly, field_info, econ_config)

        monthly_discount = (
            1
            + econ_config["financial_metrics"]["discount_rates"][
                "primary_discount_rate"
            ]
        ) ** (1 / 12) - 1
        expected_pv = 120_000_000.0 + (100_000_000.0 / (1 + monthly_discount))
        expected_npv_ops = expected_pv / 1_000_000.0
        expected_project_npv = expected_npv_ops - 150.0

        assert summary["NPV Operations ($MM)"] == pytest.approx(
            expected_npv_ops, rel=1e-6
        )
        assert summary["NPV Project ($MM)"] == pytest.approx(
            expected_project_npv, rel=1e-6
        )
        assert summary["Field"] == "Sample Field"
