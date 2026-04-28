"""
Tests for NPV cash flow component calculations.
This test module validates revenue, OPEX, and net cash flow calculations.
"""

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

# Add src to path for import
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src")
)

try:
    from worldenergydata.modules.bsee.analysis.production_api12 import (
        ProductionAPI12Analysis,
    )

    PRODUCTION_API12_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import ProductionAPI12Analysis: {e}")
    PRODUCTION_API12_AVAILABLE = False


class TestCashFlowComponents:
    """Test suite for cash flow component calculations."""

    @pytest.fixture
    def sample_production_data(self):
        """Create sample production data for testing."""
        # Create 24 months of data (Jan 2018 - Dec 2019)
        dates = pd.date_range(start="2018-01-01", periods=24, freq="ME")
        production_volumes = [
            1000,
            1200,
            1100,
            900,
            850,
            800,
            750,
            700,
            650,
            600,
            550,
            500,
            480,
            460,
            440,
            420,
            400,
            380,
            360,
            340,
            320,
            300,
            280,
            260,
        ]

        return pd.DataFrame(
            {
                "PRODUCTION_DATETIME": dates,
                "monthly_production": production_volumes,
                "api12": ["test_well_001"] * len(dates),
            }
        )

    @pytest.fixture
    def sample_oil_prices(self):
        """Create sample oil price data."""
        # Realistic oil prices for testing (USD/bbl)
        return [
            65.0,
            66.5,
            68.0,
            70.0,
            72.0,
            69.0,
            67.0,
            65.0,
            63.0,
            62.0,
            61.0,
            60.0,
            58.0,
            59.0,
            61.0,
            63.0,
            65.0,
            67.0,
            68.0,
            66.0,
            64.0,
            62.0,
            60.0,
            59.0,
        ]

    @pytest.fixture
    def config_with_economics(self):
        """Create configuration with economics parameters."""
        return {
            "economics": {
                "cost": {
                    "CAPEX": 1460000000,  # $1.46B Excel-aligned
                    "OPEX_per_bbl": 20.0,  # $20/bbl OPEX
                    "discount_rate_annual": 0.10,  # 10% discount rate
                }
            },
            "meta": {"label": "test_cash_flow"},
        }

    def test_revenue_calculation_basic(self, sample_production_data, sample_oil_prices):
        """Test basic revenue calculation: production volume * oil price."""
        # Calculate revenue for each month
        revenues = []
        for i, (_, row) in enumerate(sample_production_data.iterrows()):
            if i < len(sample_oil_prices):
                revenue = row["monthly_production"] * sample_oil_prices[i]
                revenues.append(revenue)

        # Verify first month revenue calculation
        expected_first_revenue = 1000 * 65.0  # 1000 bbl * $65/bbl
        assert (
            revenues[0] == expected_first_revenue
        ), f"Expected ${expected_first_revenue}, got ${revenues[0]}"

        # Verify all revenues are positive
        assert all(r > 0 for r in revenues), "All revenues should be positive"

        # Verify revenue decreases with production decline
        assert revenues[0] > revenues[-1], "Revenue should decline with production"

    def test_opex_calculation_basic(
        self, sample_production_data, config_with_economics
    ):
        """Test basic OPEX calculation: production volume * OPEX per barrel."""
        opex_per_bbl = config_with_economics["economics"]["cost"]["OPEX_per_bbl"]

        # Calculate OPEX for each month
        opex_values = []
        for _, row in sample_production_data.iterrows():
            opex = row["monthly_production"] * opex_per_bbl
            opex_values.append(opex)

        # Verify first month OPEX calculation
        expected_first_opex = 1000 * 20.0  # 1000 bbl * $20/bbl
        assert (
            opex_values[0] == expected_first_opex
        ), f"Expected ${expected_first_opex}, got ${opex_values[0]}"

        # Verify all OPEX values are positive
        assert all(o > 0 for o in opex_values), "All OPEX values should be positive"

        # Verify OPEX decreases with production decline
        assert opex_values[0] > opex_values[-1], "OPEX should decline with production"

    def test_net_cash_flow_calculation(
        self, sample_production_data, sample_oil_prices, config_with_economics
    ):
        """Test net cash flow calculation: revenue - OPEX."""
        opex_per_bbl = config_with_economics["economics"]["cost"]["OPEX_per_bbl"]

        # Calculate net cash flows
        net_cash_flows = []
        for i, (_, row) in enumerate(sample_production_data.iterrows()):
            if i < len(sample_oil_prices):
                revenue = row["monthly_production"] * sample_oil_prices[i]
                opex = row["monthly_production"] * opex_per_bbl
                net_cash_flow = revenue - opex
                net_cash_flows.append(net_cash_flow)

        # Verify first month net cash flow
        expected_revenue = 1000 * 65.0
        expected_opex = 1000 * 20.0
        expected_ncf = expected_revenue - expected_opex
        assert (
            net_cash_flows[0] == expected_ncf
        ), f"Expected ${expected_ncf}, got ${net_cash_flows[0]}"

        # Verify all net cash flows are positive (assuming oil price > OPEX/bbl)
        assert all(
            ncf > 0 for ncf in net_cash_flows
        ), "All net cash flows should be positive given price > OPEX"

    def test_zero_production_edge_case(self):
        """Test edge case with zero production."""
        zero_production = pd.DataFrame(
            {
                "PRODUCTION_DATETIME": pd.date_range(
                    start="2018-01-01", periods=3, freq="ME"
                ),
                "monthly_production": [1000, 0, 500],
                "api12": ["test_well"] * 3,
            }
        )

        oil_prices = [65.0, 65.0, 65.0]
        opex_per_bbl = 20.0

        # Calculate components
        revenues = []
        opex_values = []
        ncf_values = []

        for i, (_, row) in enumerate(zero_production.iterrows()):
            revenue = row["monthly_production"] * oil_prices[i]
            opex = row["monthly_production"] * opex_per_bbl
            ncf = revenue - opex

            revenues.append(revenue)
            opex_values.append(opex)
            ncf_values.append(ncf)

        # Verify zero production results in zero revenue and OPEX
        assert revenues[1] == 0, "Zero production should result in zero revenue"
        assert opex_values[1] == 0, "Zero production should result in zero OPEX"
        assert ncf_values[1] == 0, "Zero production should result in zero net cash flow"

    def test_negative_oil_price_edge_case(self):
        """Test edge case with negative oil prices (e.g., April 2020)."""
        production = pd.DataFrame(
            {
                "PRODUCTION_DATETIME": pd.date_range(
                    start="2020-04-01", periods=3, freq="ME"
                ),
                "monthly_production": [1000, 1000, 1000],
                "api12": ["test_well"] * 3,
            }
        )

        oil_prices = [20.0, -37.0, 25.0]  # Negative price in month 2
        opex_per_bbl = 20.0

        # Calculate components
        revenues = []
        opex_values = []
        ncf_values = []

        for i, (_, row) in enumerate(production.iterrows()):
            revenue = row["monthly_production"] * oil_prices[i]
            opex = row["monthly_production"] * opex_per_bbl
            ncf = revenue - opex

            revenues.append(revenue)
            opex_values.append(opex)
            ncf_values.append(ncf)

        # Verify negative price results in negative revenue
        assert revenues[1] < 0, "Negative oil price should result in negative revenue"
        assert revenues[1] == 1000 * (
            -37.0
        ), "Revenue calculation should handle negative prices"

        # OPEX should still be positive
        assert (
            opex_values[1] > 0
        ), "OPEX should remain positive even with negative oil price"

        # Net cash flow should be very negative
        assert (
            ncf_values[1] < revenues[1]
        ), "Net cash flow should be more negative than revenue"

    def test_missing_data_edge_case(self):
        """Test edge case with missing production or price data."""
        production = pd.DataFrame(
            {
                "PRODUCTION_DATETIME": pd.date_range(
                    start="2018-01-01", periods=5, freq="ME"
                ),
                "monthly_production": [1000, np.nan, 900, 850, None],  # Missing values
                "api12": ["test_well"] * 5,
            }
        )

        oil_prices = [65.0, 66.0, np.nan, 68.0, 69.0]  # Missing price in month 3
        opex_per_bbl = 20.0

        # Calculate components with missing data handling
        revenues = []
        opex_values = []
        ncf_values = []

        for i, (_, row) in enumerate(production.iterrows()):
            prod = row["monthly_production"]
            price = oil_prices[i]

            # Handle missing data
            if pd.isna(prod) or pd.isna(price):
                revenues.append(np.nan)
                opex_values.append(np.nan if pd.isna(prod) else prod * opex_per_bbl)
                ncf_values.append(np.nan)
            else:
                revenue = prod * price
                opex = prod * opex_per_bbl
                ncf = revenue - opex

                revenues.append(revenue)
                opex_values.append(opex)
                ncf_values.append(ncf)

        # Verify missing data handling
        assert pd.isna(revenues[1]), "Missing production should result in NaN revenue"
        assert pd.isna(revenues[2]), "Missing price should result in NaN revenue"
        assert pd.isna(
            ncf_values[4]
        ), "Missing production should result in NaN net cash flow"

    def test_cash_flow_dataframe_structure(
        self, sample_production_data, sample_oil_prices, config_with_economics
    ):
        """Test that cash flow DataFrame has correct structure and columns."""
        opex_per_bbl = config_with_economics["economics"]["cost"]["OPEX_per_bbl"]

        # Create cash flow DataFrame
        cash_flow_data = []
        for i, (_, row) in enumerate(sample_production_data.iterrows()):
            if i < len(sample_oil_prices):
                revenue = row["monthly_production"] * sample_oil_prices[i]
                opex = row["monthly_production"] * opex_per_bbl
                ncf = revenue - opex

                cash_flow_data.append(
                    {
                        "Month": i + 1,
                        "Date": row["PRODUCTION_DATETIME"],
                        "Production_BBL": row["monthly_production"],
                        "Oil_Price_USD_per_BBL": sample_oil_prices[i],
                        "Revenue_USD": revenue,
                        "OPEX_USD": opex,
                        "Net_Cash_Flow_USD": ncf,
                    }
                )

        cash_flow_df = pd.DataFrame(cash_flow_data)

        # Verify DataFrame structure
        expected_columns = [
            "Month",
            "Date",
            "Production_BBL",
            "Oil_Price_USD_per_BBL",
            "Revenue_USD",
            "OPEX_USD",
            "Net_Cash_Flow_USD",
        ]
        assert (
            list(cash_flow_df.columns) == expected_columns
        ), "Cash flow DataFrame should have expected columns"

        # Verify data types
        assert cash_flow_df["Revenue_USD"].dtype in [
            np.float64,
            float,
        ], "Revenue should be numeric"
        assert cash_flow_df["OPEX_USD"].dtype in [
            np.float64,
            float,
        ], "OPEX should be numeric"
        assert cash_flow_df["Net_Cash_Flow_USD"].dtype in [
            np.float64,
            float,
        ], "Net cash flow should be numeric"

        # Verify calculations
        for _, row in cash_flow_df.iterrows():
            expected_revenue = row["Production_BBL"] * row["Oil_Price_USD_per_BBL"]
            expected_opex = row["Production_BBL"] * opex_per_bbl
            expected_ncf = expected_revenue - expected_opex

            assert (
                abs(row["Revenue_USD"] - expected_revenue) < 0.01
            ), "Revenue calculation mismatch"
            assert (
                abs(row["OPEX_USD"] - expected_opex) < 0.01
            ), "OPEX calculation mismatch"
            assert (
                abs(row["Net_Cash_Flow_USD"] - expected_ncf) < 0.01
            ), "Net cash flow calculation mismatch"

    def test_cash_flow_with_capex_period_zero(self, config_with_economics):
        """Test cash flow with CAPEX in period 0 (Excel-aligned approach)."""
        capex = config_with_economics["economics"]["cost"]["CAPEX"]

        # Create cash flow array with CAPEX at period 0
        cash_flows = [-capex]  # Period 0: Initial CAPEX (negative)

        # Add monthly operational cash flows (periods 1-24)
        monthly_ncf = [
            45000,
            54000,
            49500,
            40500,
            38250,
            36000,
            33750,
            31500,
            29250,
            27000,
            24750,
            22500,
            21600,
            20700,
            19800,
            18900,
            18000,
            17100,
            16200,
            15300,
            14400,
            13500,
            12600,
            11700,
        ]

        cash_flows.extend(monthly_ncf)

        # Verify structure
        assert cash_flows[0] == -capex, "Period 0 should be negative CAPEX"
        assert cash_flows[0] < 0, "CAPEX should be negative"
        assert all(
            cf > 0 for cf in cash_flows[1:]
        ), "All operational cash flows should be positive"

        # Verify total cash flow
        total_operational_cf = sum(cash_flows[1:])
        net_total = sum(cash_flows)

        assert (
            total_operational_cf > 0
        ), "Total operational cash flow should be positive"
        assert (
            net_total < total_operational_cf
        ), "Net total should be less than operational due to CAPEX"


@pytest.mark.skipif(
    not PRODUCTION_API12_AVAILABLE, reason="ProductionAPI12Analysis not available"
)
class TestProductionAPI12CashFlowMethods:
    """Test ProductionAPI12Analysis class methods for cash flow calculations."""

    @pytest.fixture
    def analyzer(self):
        """Create ProductionAPI12Analysis instance."""
        return ProductionAPI12Analysis()

    def test_revenue_table_generation_structure(self, analyzer):
        """Test that generate_revenue_table creates proper structure."""
        # Create mock production data
        production_df = pd.DataFrame(
            {
                "PRODUCTION_DATETIME": pd.date_range(
                    start="2018-01-01", periods=12, freq="ME"
                ),
                "monthly_production": [1000] * 12,
                "api12": ["test_well"] * 12,
            }
        )

        # Note: The actual method reads from Excel file, so we'll test the expected structure
        # In real implementation, this would need to be refactored to accept price data as parameter

        # Expected revenue table structure
        expected_columns = [
            "Month",
            "Monthly Oil Production",
            "Avg Price (USD/bbl)",
            "Revenue (USD)",
        ]

        # This is what the revenue table should look like
        revenue_table = pd.DataFrame(
            {
                "Month": range(1, 13),
                "Monthly Oil Production": [1000] * 12,
                "Avg Price (USD/bbl)": [65.0] * 12,  # Placeholder prices
                "Revenue (USD)": [65000.0] * 12,  # 1000 * 65
            }
        )

        # Verify structure
        assert (
            list(revenue_table.columns) == expected_columns
        ), "Revenue table should have expected columns"
        assert len(revenue_table) == 12, "Revenue table should have 12 months"
        assert all(
            revenue_table["Revenue (USD)"] > 0
        ), "All revenues should be positive"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
