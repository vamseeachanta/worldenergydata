"""
Unit tests for drilling and completion data processing
Tests D&C cost processing logic from SME V20
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd

from src.worldenergydata.modules.bsee.analysis.financial.drilling_completion import (
    DrillingCompletionProcessor,
    allocate_dc_costs_monthly,
    build_dc_day_maps,
    calculate_completion_costs,
    calculate_drilling_costs,
)


class TestDrillingCompletionProcessor(unittest.TestCase):
    """Test suite for drilling and completion data processing"""

    def setUp(self):
        """Set up test fixtures"""
        self.processor = DrillingCompletionProcessor()

        # Sample drilling and completion data
        self.dc_totals = pd.DataFrame(
            {
                "WELL_NAME": ["WELL_A", "WELL_B", "WELL_C"],
                "DRILL_DAYS": [30, 45, 60],
                "COMP_DAYS": [15, 20, 25],
                "WELL_SPUD_DATE": pd.to_datetime(
                    ["2023-01-01", "2023-02-01", "2023-03-01"]
                ),
                "TOTAL_DEPTH_DATE": pd.to_datetime(
                    ["2023-01-31", "2023-03-17", "2023-05-01"]
                ),
                "LEASE_NUM": ["G12345", "G12345", "G23456"],
                "DEV_NAME": ["DEV_1", "DEV_1", "DEV_2"],
            }
        )

        # Sample monthly drilling/completion data
        self.dc_monthly = pd.DataFrame(
            {
                "YearMonth": pd.date_range("2023-01-01", periods=5, freq="MS").tolist()
                * 3,
                "WELL_NAME": ["WELL_A"] * 5 + ["WELL_B"] * 5 + ["WELL_C"] * 5,
                "DRILL_DAYS": [10, 10, 10, 0, 0, 0, 15, 15, 15, 0, 0, 0, 20, 20, 20],
                "COMP_DAYS": [0, 0, 0, 7, 8, 0, 0, 0, 10, 10, 0, 0, 0, 12, 13],
            }
        )

        # Cost assumptions
        self.cost_assumptions = {
            "DRILL_COST_PER_DAY": 100000,  # $100k per day
            "COMP_COST_PER_DAY": 75000,  # $75k per day
            "SUBSEA_DRILL_COST_PER_DAY": 150000,
            "SUBSEA_COMP_COST_PER_DAY": 100000,
        }

    def test_initialization(self):
        """Test processor initialization"""
        processor = DrillingCompletionProcessor(self.cost_assumptions)
        self.assertEqual(processor.drill_cost_per_day, 100000)
        self.assertEqual(processor.comp_cost_per_day, 75000)
        self.assertIsInstance(processor._cache, dict)

    def test_calculate_drilling_costs(self):
        """Test drilling cost calculation"""
        costs = self.processor.calculate_drilling_costs(
            self.dc_totals, self.cost_assumptions["DRILL_COST_PER_DAY"]
        )

        # Check calculated costs
        self.assertEqual(costs["WELL_A"], 30 * 100000)  # 30 days * $100k
        self.assertEqual(costs["WELL_B"], 45 * 100000)  # 45 days * $100k
        self.assertEqual(costs["WELL_C"], 60 * 100000)  # 60 days * $100k

    def test_calculate_completion_costs(self):
        """Test completion cost calculation"""
        costs = self.processor.calculate_completion_costs(
            self.dc_totals, self.cost_assumptions["COMP_COST_PER_DAY"]
        )

        # Check calculated costs
        self.assertEqual(costs["WELL_A"], 15 * 75000)  # 15 days * $75k
        self.assertEqual(costs["WELL_B"], 20 * 75000)  # 20 days * $75k
        self.assertEqual(costs["WELL_C"], 25 * 75000)  # 25 days * $75k

    def test_build_day_maps_for_development(self):
        """Test building day maps for a specific development"""
        drill_map, comp_map, all_wells = self.processor.build_day_maps_for_development(
            "DEV_1", self.dc_totals, self.dc_monthly
        )

        # Check drill map structure
        self.assertIn("2023-01", drill_map)
        self.assertIn("2023-02", drill_map)

        # Check completion map
        self.assertIn("2023-01", comp_map)

        # Check well list
        self.assertIn("WELL_A", all_wells)
        self.assertIn("WELL_B", all_wells)
        self.assertNotIn("WELL_C", all_wells)  # Different development

    def test_allocate_costs_monthly(self):
        """Test monthly cost allocation"""
        monthly_allocation = self.processor.allocate_costs_monthly(
            self.dc_monthly, self.cost_assumptions
        )

        # Check structure
        self.assertIn("YearMonth", monthly_allocation.columns)
        self.assertIn("DRILL_COST", monthly_allocation.columns)
        self.assertIn("COMP_COST", monthly_allocation.columns)
        self.assertIn("TOTAL_DC_COST", monthly_allocation.columns)

        # Verify cost allocation
        jan_2023 = monthly_allocation[
            monthly_allocation["YearMonth"] == pd.Timestamp("2023-01-01")
        ]
        # WELL_A: 10 drill days in Jan
        expected_drill = 10 * 100000
        self.assertIn(expected_drill, jan_2023["DRILL_COST"].values)

    def test_process_totals_with_monthly_override(self):
        """Test that monthly data overrides totals when both exist"""
        totals_map, has_monthly = self.processor.process_dc_totals(
            self.dc_totals, self.dc_monthly
        )

        # Monthly data should take precedence
        self.assertTrue(has_monthly["WELL_A"])

        # Totals from monthly should match sum
        self.assertEqual(totals_map["WELL_A"]["drill_days"], 30)  # Sum of monthly
        self.assertEqual(totals_map["WELL_A"]["comp_days"], 15)  # Sum of monthly

    def test_subsea_vs_dry_tree_costs(self):
        """Test different costs for subsea vs dry tree systems"""
        # Add system type
        dc_with_system = self.dc_totals.copy()
        dc_with_system["DEV_TYPE"] = ["subsea", "subsea", "dry tree"]

        costs = self.processor.calculate_system_specific_costs(
            dc_with_system, self.cost_assumptions
        )

        # Subsea should have higher costs
        self.assertGreater(costs["WELL_A"], costs["WELL_C"])
        self.assertGreater(costs["WELL_B"], costs["WELL_C"])

    def test_date_validation(self):
        """Test validation of spud and TD dates"""
        invalid_dates = pd.DataFrame(
            {
                "WELL_NAME": ["WELL_X"],
                "DRILL_DAYS": [30],
                "COMP_DAYS": [15],
                "WELL_SPUD_DATE": pd.to_datetime("2023-03-01"),
                "TOTAL_DEPTH_DATE": pd.to_datetime("2023-02-01"),  # TD before spud!
            }
        )

        with self.assertRaises(ValueError):
            self.processor.validate_dates(invalid_dates)

    def test_capex_schedule_generation(self):
        """Test generation of CAPEX schedule"""
        capex_schedule = self.processor.generate_capex_schedule(
            self.dc_monthly,
            self.cost_assumptions,
            start_date="2023-01-01",
            end_date="2023-12-31",
        )

        # Should have monthly CAPEX values
        self.assertEqual(len(capex_schedule), 12)  # 12 months
        self.assertIn("DRILL_CAPEX", capex_schedule.columns)
        self.assertIn("COMP_CAPEX", capex_schedule.columns)
        self.assertIn("TOTAL_CAPEX", capex_schedule.columns)

    def test_calculate_first_oil_impact(self):
        """Test calculation of time to first oil from completion"""
        # Sample production data
        production = pd.DataFrame(
            {
                "YearMonth": pd.date_range("2023-01-01", periods=12, freq="MS"),
                "WELL_A": [0, 0, 0, 100, 200, 300, 250, 200, 150, 100, 50, 25],
            }
        )

        first_oil = self.processor.calculate_first_oil_dates(self.dc_totals, production)

        # WELL_A completed end of Jan, first oil in April
        self.assertEqual(first_oil["WELL_A"], pd.Timestamp("2023-04-01"))

    def test_drilling_efficiency_metrics(self):
        """Test calculation of drilling efficiency metrics"""
        metrics = self.processor.calculate_efficiency_metrics(self.dc_totals)

        # Check metrics structure
        self.assertIn("avg_drill_days", metrics)
        self.assertIn("avg_comp_days", metrics)
        self.assertIn("total_drill_days", metrics)
        self.assertIn("total_comp_days", metrics)
        self.assertIn("drill_days_std", metrics)

        # Verify calculations
        self.assertEqual(metrics["avg_drill_days"], 45)  # (30+45+60)/3
        self.assertEqual(metrics["avg_comp_days"], 20)  # (15+20+25)/3
        self.assertEqual(metrics["total_drill_days"], 135)
        self.assertEqual(metrics["total_comp_days"], 60)

    def test_empty_data_handling(self):
        """Test handling of empty dataframes"""
        empty_df = pd.DataFrame()

        drill_map, comp_map, wells = self.processor.build_day_maps_for_development(
            "DEV_1", empty_df, empty_df
        )

        self.assertEqual(len(drill_map), 0)
        self.assertEqual(len(comp_map), 0)
        self.assertEqual(len(wells), 0)

    def test_partial_data_handling(self):
        """Test handling of partial/missing data"""
        partial_data = pd.DataFrame(
            {
                "WELL_NAME": ["WELL_X", "WELL_Y"],
                "DRILL_DAYS": [30, np.nan],
                "COMP_DAYS": [np.nan, 20],
                "WELL_SPUD_DATE": [pd.to_datetime("2023-01-01"), pd.NaT],
            }
        )

        # Should handle NaN values gracefully
        costs = self.processor.calculate_drilling_costs(partial_data, 100000, fill_na=0)

        self.assertEqual(costs["WELL_X"], 30 * 100000)
        self.assertEqual(costs["WELL_Y"], 0)  # NaN filled with 0


class TestDCMapBuilder(unittest.TestCase):
    """Test building drilling/completion maps for financial calculations"""

    def setUp(self):
        """Set up test fixtures"""
        self.processor = DrillingCompletionProcessor()

    def test_build_monthly_dc_map(self):
        """Test building monthly D&C map from daily data"""
        daily_data = pd.DataFrame(
            {
                "Date": pd.date_range("2023-01-01", periods=90, freq="D"),
                "WELL_NAME": ["WELL_A"] * 90,
                "DRILL_ACTIVITY": [1] * 30 + [0] * 60,  # 30 days drilling
                "COMP_ACTIVITY": [0] * 30 + [1] * 15 + [0] * 45,  # 15 days completion
            }
        )

        monthly_map = self.processor.build_monthly_dc_map(daily_data)

        # Check January drilling days
        jan_drill = monthly_map[("2023-01", "WELL_A", "DRILL")]
        self.assertEqual(jan_drill, 30)

        # Check February completion days
        feb_comp = monthly_map[("2023-02", "WELL_A", "COMP")]
        self.assertEqual(feb_comp, 15)

    def test_aggregate_dc_by_lease(self):
        """Test aggregating D&C data by lease"""
        dc_by_well = pd.DataFrame(
            {
                "WELL_NAME": ["WELL_A", "WELL_B", "WELL_C"],
                "LEASE_NUM": ["G12345", "G12345", "G23456"],
                "DRILL_DAYS": [30, 25, 40],
                "COMP_DAYS": [15, 12, 20],
                "DRILL_COST": [3000000, 2500000, 4000000],
                "COMP_COST": [1125000, 900000, 1500000],
            }
        )

        lease_aggregates = self.processor.aggregate_dc_by_lease(dc_by_well)

        # Check lease G12345 totals
        lease1 = lease_aggregates[lease_aggregates["LEASE_NUM"] == "G12345"]
        self.assertEqual(lease1["TOTAL_DRILL_DAYS"].iloc[0], 55)  # 30 + 25
        self.assertEqual(lease1["TOTAL_DRILL_COST"].iloc[0], 5500000)  # 3M + 2.5M


if __name__ == "__main__":
    unittest.main()
