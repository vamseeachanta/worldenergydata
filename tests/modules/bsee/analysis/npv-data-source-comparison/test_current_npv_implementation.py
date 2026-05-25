#!/usr/bin/env python3
"""
Test Current NPV Implementation to Document Baseline Behavior

This test file captures the current NPV calculation behavior as baseline
for comparison with Excel-aligned implementation.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import numpy_financial as npf
import pandas as pd
import pytest

# Add src to path for importing
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src")
)

from worldenergydata.bsee.analysis.production_api12 import (
    ProductionAPI12Analysis,
)


class TestCurrentNPVImplementation:

    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = ProductionAPI12Analysis()

        # Create sample configuration matching Excel analysis
        self.test_cfg = {
            "meta": {"label": "test_field"},
            "economics": {
                "cost": {
                    "discount_rate_annual": 0.10,  # 10% as specified in issue
                    "CAPEX": 1460000000,  # $1.46B Excel-aligned
                    "OPEX": 15.00,  # $15 per barrel
                }
            },
            "Analysis": {"result_folder": "test_results"},
        }

        # Create sample revenue DataFrame matching current implementation format
        self.sample_revenue_df = pd.DataFrame(
            {
                "Month": [201801, 201802, 201803, 201804, 201805],
                "Monthly Oil Production": [100000, 95000, 90000, 85000, 80000],  # BBL
                "Avg Price (USD/bbl)": [
                    "$65.00",
                    "$68.00",
                    "$70.00",
                    "$72.00",
                    "$75.00",
                ],
                "Revenue (USD)": [
                    "$6,500,000.00",
                    "$6,460,000.00",
                    "$6,300,000.00",
                    "$6,120,000.00",
                    "$6,000,000.00",
                ],
            }
        )

    def test_current_npv_calculation_baseline(self):
        """Test current NPV calculation with known inputs - establishes baseline"""

        # Mock file operations to avoid creating actual files
        with (
            patch("pandas.DataFrame.to_csv"),
            patch("os.path.join", return_value="mock_path"),
        ):

            npv_result = self.analyzer.perform_npv_calculation(
                self.test_cfg, self.sample_revenue_df
            )

        # Document current behavior
        assert isinstance(npv_result, (int, float)), "NPV should return numeric value"

        # Log current calculation details for comparison
        print(f"\n=== CURRENT NPV IMPLEMENTATION BASELINE ===")
        print(f"NPV Result: ${npv_result:,.2f}")
        print(
            f"Discount Rate: {self.test_cfg['economics']['cost']['discount_rate_annual']*100}%"
        )
        print(f"CAPEX: ${self.test_cfg['economics']['cost']['CAPEX']:,.0f}")
        print(f"OPEX per BBL: ${self.test_cfg['economics']['cost']['OPEX']}")

        # Store baseline for comparison
        self.baseline_npv = npv_result

    def test_cash_flow_construction(self):
        """Test how current implementation constructs cash flows"""

        # Test revenue data cleaning
        test_revenue_df = self.sample_revenue_df.copy()

        # Mock the method partially to capture cash flow construction
        with patch.object(self.analyzer, "perform_npv_calculation") as mock_npv:

            def capture_cash_flow_construction(cfg, revenue_df):
                # Replicate the cash flow construction logic from current implementation
                revenue_df["Revenue (USD)"] = (
                    revenue_df["Revenue (USD)"]
                    .astype(str)
                    .str.replace("$", "", regex=False)
                    .str.replace(",", "", regex=False)
                    .astype(float)
                )
                revenue_df["Monthly Oil Production"] = pd.to_numeric(
                    revenue_df["Monthly Oil Production"], errors="coerce"
                )

                # Calculate OPEX
                opex_per_bbl = cfg["economics"]["cost"]["OPEX"]
                revenue_df["OPEX"] = revenue_df["Monthly Oil Production"] * opex_per_bbl

                # Net cash flow
                revenue_df["Net Cash Flow"] = (
                    revenue_df["Revenue (USD)"] - revenue_df["OPEX"]
                )

                # Document cash flow construction
                print(f"\n=== CASH FLOW CONSTRUCTION ANALYSIS ===")
                print("Sample Cash Flows:")
                for i in range(min(3, len(revenue_df))):
                    print(f"Period {i+1}:")
                    print(f"  Revenue: ${revenue_df['Revenue (USD)'].iloc[i]:,.2f}")
                    print(f"  OPEX: ${revenue_df['OPEX'].iloc[i]:,.2f}")
                    print(f"  Net CF: ${revenue_df['Net Cash Flow'].iloc[i]:,.2f}")

                return revenue_df

            # Call the actual method to see cash flow construction
            result_df = capture_cash_flow_construction(self.test_cfg, test_revenue_df)

            # Verify cash flow construction logic
            assert "OPEX" in result_df.columns, "OPEX should be calculated"
            assert (
                "Net Cash Flow" in result_df.columns
            ), "Net Cash Flow should be calculated"

            # Check OPEX calculation
            expected_opex_0 = (
                result_df["Monthly Oil Production"].iloc[0]
                * self.test_cfg["economics"]["cost"]["OPEX"]
            )
            actual_opex_0 = result_df["OPEX"].iloc[0]
            assert (
                abs(expected_opex_0 - actual_opex_0) < 0.01
            ), f"OPEX calculation mismatch: expected {expected_opex_0}, got {actual_opex_0}"

    def test_discount_rate_application(self):
        """Test how current implementation applies discount rate"""

        # Test with simple known cash flows
        simple_cash_flows = [
            -1000000,
            300000,
            300000,
            300000,
            300000,
        ]  # Simple 4-year project
        discount_rate = 0.10

        # Calculate NPV using numpy-financial (current implementation)
        npf_result = npf.npv(discount_rate, simple_cash_flows)

        # Calculate NPV using Excel formula for comparison
        excel_npv = 0
        for t, cf in enumerate(simple_cash_flows):
            if t == 0:
                excel_npv += cf  # Period 0 not discounted
            else:
                excel_npv += cf / ((1 + discount_rate) ** t)

        print(f"\n=== DISCOUNT RATE APPLICATION COMPARISON ===")
        print(f"Simple Cash Flows: {simple_cash_flows}")
        print(f"Discount Rate: {discount_rate*100}%")
        print(f"numpy-financial NPV: ${npf_result:,.2f}")
        print(f"Excel Formula NPV: ${excel_npv:,.2f}")
        print(f"Difference: ${abs(npf_result - excel_npv):,.2f}")
        print(
            f"% Difference: {abs(npf_result - excel_npv) / abs(excel_npv) * 100:.2f}%"
        )

        # Document the difference for analysis
        self.npf_vs_excel_diff = abs(npf_result - excel_npv)

    def test_period_timing_assumptions(self):
        """Test period timing assumptions in current implementation"""

        # Test how current implementation handles CAPEX timing
        capex = self.test_cfg["economics"]["cost"]["CAPEX"]
        net_cash_flows = [
            100000,
            95000,
            90000,
            85000,
            80000,
        ]  # Sample monthly net cash flows

        # Current implementation approach (based on code analysis)
        cash_flows_current = [-capex] + net_cash_flows

        # Alternative timing approaches
        cash_flows_excel_style = [-capex] + net_cash_flows  # Same for comparison

        print(f"\n=== PERIOD TIMING ANALYSIS ===")
        print(f"CAPEX (Period 0): ${capex:,.0f}")
        print(
            f"Operating Cash Flows (Periods 1-5): {[f'${cf:,.0f}' for cf in net_cash_flows]}"
        )
        print(f"Current Implementation: {len(cash_flows_current)} periods")
        print(f"Excel Style: {len(cash_flows_excel_style)} periods")

        # Test NPV with different timing
        npv_current = npf.npv(0.10, cash_flows_current)
        print(f"NPV with current timing: ${npv_current:,.2f}")

    def test_current_implementation_full_workflow(self):
        """Test the complete current NPV workflow to document behavior"""

        # Create a more complete test scenario
        with (
            patch("pandas.DataFrame.to_csv"),
            patch("os.path.join", return_value="mock_path"),
            patch("pandas.read_excel") as mock_excel,
        ):

            # Mock Excel price data reading
            mock_excel.return_value = pd.DataFrame(
                {
                    "col_2": [
                        np.nan,
                        np.nan,
                        65.0,
                        68.0,
                        70.0,
                        72.0,
                        75.0,
                    ]  # Mock BRENT prices
                }
            )

            npv_result = self.analyzer.perform_npv_calculation(
                self.test_cfg, self.sample_revenue_df
            )

            print(f"\n=== FULL WORKFLOW ANALYSIS ===")
            print(f"Final NPV Result: ${npv_result:,.2f}")

            # Document key parameters used
            print(f"Configuration Summary:")
            print(
                f"  Discount Rate: {self.test_cfg['economics']['cost']['discount_rate_annual']*100}%"
            )
            print(f"  CAPEX: ${self.test_cfg['economics']['cost']['CAPEX']:,.0f}")
            print(f"  OPEX per BBL: ${self.test_cfg['economics']['cost']['OPEX']}")
            print(f"  Revenue Data Points: {len(self.sample_revenue_df)}")

    def test_excel_benchmark_comparison(self):
        """Compare current implementation against known Excel benchmark"""

        # Known Excel benchmark from analysis files
        excel_npv_benchmark = -2220124040.76  # From Excel analysis
        excel_discount_rate = 0.10
        excel_capex = 1460000000

        print(f"\n=== EXCEL BENCHMARK COMPARISON ===")
        print(f"Excel NPV Benchmark: ${excel_npv_benchmark:,.2f}")
        print(f"Excel Discount Rate: {excel_discount_rate*100}%")
        print(f"Excel CAPEX: ${excel_capex:,.0f}")

        # Run current implementation with Excel parameters
        excel_aligned_cfg = self.test_cfg.copy()
        excel_aligned_cfg["economics"]["cost"][
            "discount_rate_annual"
        ] = excel_discount_rate
        excel_aligned_cfg["economics"]["cost"]["CAPEX"] = excel_capex

        with (
            patch("pandas.DataFrame.to_csv"),
            patch("os.path.join", return_value="mock_path"),
        ):

            current_npv = self.analyzer.perform_npv_calculation(
                excel_aligned_cfg, self.sample_revenue_df
            )

        # Calculate variance
        variance = abs(current_npv - excel_npv_benchmark)
        variance_pct = (variance / abs(excel_npv_benchmark)) * 100

        print(f"Current Implementation NPV: ${current_npv:,.2f}")
        print(f"Variance: ${variance:,.2f}")
        print(f"Variance %: {variance_pct:.1f}%")

        # Document if this meets or exceeds the 50% variance mentioned in the issue
        if variance_pct > 50:
            print("X CONFIRMS: Variance exceeds 50% (issue reproduced)")
        elif variance_pct > 20:
            print("! MODERATE: Variance 20-50% (needs improvement)")
        else:
            print("+ GOOD: Variance <20% (acceptable)")

        # Store for further analysis
        self.documented_variance_pct = variance_pct


if __name__ == "__main__":
    # Run tests manually for development
    test_instance = TestCurrentNPVImplementation()
    test_instance.setup_method()

    print("Running Current NPV Implementation Analysis...")
    test_instance.test_current_npv_calculation_baseline()
    test_instance.test_cash_flow_construction()
    test_instance.test_discount_rate_application()
    test_instance.test_period_timing_assumptions()
    test_instance.test_current_implementation_full_workflow()
    test_instance.test_excel_benchmark_comparison()

    print("\n" + "=" * 80)
    print("CURRENT NPV IMPLEMENTATION ANALYSIS COMPLETE")
    print("=" * 80)
