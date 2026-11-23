"""
Tests for the Executive Template in the Comprehensive Report System.
"""

import json
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from worldenergydata.modules.bsee.reports.comprehensive.templates.executive_template import (
    BusinessHighlight,
    ExecutiveKPI,
    ExecutiveSummary,
    ExecutiveTemplate,
    PerformanceScore,
    RiskIndicator,
    StrategicInitiative,
    StrategicMetric,
)


class TestExecutiveTemplateKPIs(unittest.TestCase):
    """Tests for ExecutiveTemplate KPI functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.template = ExecutiveTemplate()
        self.sample_data = self._create_sample_data()

    def _create_sample_data(self):
        """Create sample data for testing."""
        return {
            "report_date": datetime(2024, 1, 1),
            "organization_level": "block",
            "organization_id": "BLOCK-525",
            "organization_name": "Green Canyon Block 525",
            "production": {
                "oil_bbls": 1500000,
                "gas_mcf": 850000,
                "water_bbls": 200000,
                "total_boe": 1641667,
            },
            "financial": {
                "revenue": Decimal("125000000"),
                "operating_cost": Decimal("45000000"),
                "capital_cost": Decimal("15000000"),
                "net_income": Decimal("65000000"),
                "ebitda": Decimal("75000000"),
            },
            "operational": {
                "active_wells": 25,
                "producing_wells": 22,
                "shut_in_wells": 3,
                "uptime_percentage": 94.5,
                "efficiency_rate": 88.2,
            },
            "safety": {"trir": 0.45, "ltir": 0.15, "incidents": 2, "near_misses": 5},
            "environmental": {
                "emissions_tons_co2": 12500,
                "water_recycled_percentage": 78.5,
                "spills": 0,
                "compliance_score": 98.5,
            },
        }

    def test_executive_kpi_creation(self):
        """Test creation of ExecutiveKPI objects."""
        kpi = ExecutiveKPI(
            name="Production Efficiency",
            value=92.5,
            unit="%",
            target=90.0,
            trend="up",
            status="green",
            category="Operational",
        )

        self.assertEqual(kpi.name, "Production Efficiency")
        self.assertEqual(kpi.value, 92.5)
        self.assertEqual(kpi.unit, "%")
        self.assertEqual(kpi.target, 90.0)
        self.assertEqual(kpi.trend, "up")
        self.assertEqual(kpi.status, "green")
        self.assertEqual(kpi.category, "Operational")

        # Test KPI performance calculation
        self.assertEqual(kpi.get_performance_percentage(), 102.78)
        self.assertTrue(kpi.is_meeting_target())

    def test_strategic_metric_creation(self):
        """Test creation of StrategicMetric objects."""
        metric = StrategicMetric(
            name="Market Share",
            current_value=15.5,
            previous_value=14.2,
            target_value=16.0,
            unit="%",
            period="Q4 2023",
        )

        self.assertEqual(metric.name, "Market Share")
        self.assertEqual(metric.current_value, 15.5)
        self.assertEqual(metric.previous_value, 14.2)
        self.assertEqual(metric.get_change(), 1.3)
        self.assertEqual(metric.get_change_percentage(), 9.15)
        self.assertFalse(metric.is_meeting_target())
        self.assertEqual(metric.get_target_gap(), -0.5)

    def test_executive_template_kpi_generation(self):
        """Test generation of executive KPIs from data."""
        kpis = self.template.generate_executive_kpis(self.sample_data)

        self.assertIsInstance(kpis, list)
        self.assertTrue(len(kpis) > 0)

        # Check for required KPI categories
        categories = {kpi.category for kpi in kpis}
        required_categories = {"Financial", "Operational", "Safety", "Environmental"}
        self.assertTrue(required_categories.issubset(categories))

        # Verify specific KPIs
        revenue_kpi = next((k for k in kpis if k.name == "Revenue"), None)
        self.assertIsNotNone(revenue_kpi)
        self.assertEqual(revenue_kpi.value, 125000000)

        uptime_kpi = next((k for k in kpis if k.name == "Uptime"), None)
        self.assertIsNotNone(uptime_kpi)
        self.assertEqual(uptime_kpi.value, 94.5)

    def test_kpi_status_determination(self):
        """Test determination of KPI status (green/yellow/red)."""
        test_cases = [
            (95, 90, "green"),  # Above target
            (88, 90, "yellow"),  # Slightly below target (within 5%)
            (80, 90, "red"),  # Significantly below target
        ]

        for value, target, expected_status in test_cases:
            status = self.template.determine_kpi_status(value, target)
            self.assertEqual(
                status, expected_status, f"Failed for value={value}, target={target}"
            )

    def test_kpi_trend_analysis(self):
        """Test KPI trend analysis over time."""
        historical_data = {
            "monthly_production": [100000, 105000, 102000, 108000, 110000],
            "months": ["Jan", "Feb", "Mar", "Apr", "May"],
        }

        trend = self.template.analyze_kpi_trend(historical_data["monthly_production"])

        self.assertIn(trend, ["up", "down", "stable"])
        self.assertEqual(trend, "up")  # Overall upward trend

    def test_performance_score_calculation(self):
        """Test calculation of overall performance score."""
        kpis = self.template.generate_executive_kpis(self.sample_data)
        score = self.template.calculate_performance_score(kpis)

        self.assertIsInstance(score, PerformanceScore)
        self.assertGreaterEqual(score.overall, 0)
        self.assertLessEqual(score.overall, 100)

        # Check category scores
        self.assertIn("Financial", score.category_scores)
        self.assertIn("Operational", score.category_scores)
        self.assertIn("Safety", score.category_scores)
        self.assertIn("Environmental", score.category_scores)

        # Verify score calculation logic
        for category, cat_score in score.category_scores.items():
            self.assertGreaterEqual(cat_score, 0)
            self.assertLessEqual(cat_score, 100)

    def test_executive_kpi_with_missing_data(self):
        """Test KPI generation with missing data fields."""
        incomplete_data = {
            "production": {"oil_bbls": 100000},
            "financial": {"revenue": Decimal("1000000")},
        }

        kpis = self.template.generate_executive_kpis(incomplete_data)

        # Should still generate KPIs for available data
        self.assertTrue(len(kpis) > 0)

        # Check that missing data is handled gracefully
        for kpi in kpis:
            self.assertIsNotNone(kpi.value)
            self.assertIn(kpi.status, ["green", "yellow", "red", "gray"])

    def test_kpi_comparison_with_benchmarks(self):
        """Test KPI comparison with industry benchmarks."""
        benchmarks = {
            "uptime": 92.0,
            "efficiency": 85.0,
            "trir": 0.50,
            "emissions_intensity": 15.0,
        }

        comparisons = self.template.compare_with_benchmarks(
            self.sample_data, benchmarks
        )

        self.assertIn("uptime", comparisons)
        self.assertIn("performance", comparisons["uptime"])
        self.assertIn("vs_benchmark", comparisons["uptime"])

        # Uptime should be above benchmark
        self.assertGreater(comparisons["uptime"]["vs_benchmark"], 0)

    def test_kpi_priority_ranking(self):
        """Test ranking of KPIs by priority."""
        kpis = self.template.generate_executive_kpis(self.sample_data)
        ranked_kpis = self.template.rank_kpis_by_priority(kpis)

        self.assertEqual(len(ranked_kpis), len(kpis))

        # Check that critical KPIs are ranked higher
        critical_kpis = ["Revenue", "Safety Score", "Production Volume"]
        top_kpi_names = [kpi.name for kpi in ranked_kpis[:5]]

        # At least one critical KPI should be in top 5
        self.assertTrue(any(kpi in top_kpi_names for kpi in critical_kpis))


class TestExecutiveTemplateStrategicMetrics(unittest.TestCase):
    """Tests for strategic metrics calculations."""

    def setUp(self):
        """Set up test fixtures."""
        self.template = ExecutiveTemplate()
        self.strategic_data = self._create_strategic_data()

    def _create_strategic_data(self):
        """Create strategic data for testing."""
        return {
            "current_period": {
                "revenue": Decimal("125000000"),
                "market_share": 15.5,
                "roi": 22.5,
                "production_growth": 8.2,
                "cost_reduction": 5.5,
            },
            "previous_period": {
                "revenue": Decimal("115000000"),
                "market_share": 14.8,
                "roi": 20.1,
                "production_growth": 6.5,
                "cost_reduction": 3.2,
            },
            "targets": {
                "revenue": Decimal("130000000"),
                "market_share": 16.0,
                "roi": 25.0,
                "production_growth": 10.0,
                "cost_reduction": 6.0,
            },
        }

    def test_strategic_metric_calculation(self):
        """Test calculation of strategic metrics."""
        metrics = self.template.calculate_strategic_metrics(self.strategic_data)

        self.assertIsInstance(metrics, list)
        self.assertTrue(all(isinstance(m, StrategicMetric) for m in metrics))

        # Verify revenue metric
        revenue_metric = next((m for m in metrics if m.name == "Revenue"), None)
        self.assertIsNotNone(revenue_metric)
        self.assertEqual(revenue_metric.current_value, 125000000)
        self.assertEqual(revenue_metric.get_change_percentage(), 8.70)

    def test_year_over_year_comparison(self):
        """Test year-over-year metric comparisons."""
        yoy_data = {
            "2024": self.strategic_data["current_period"],
            "2023": self.strategic_data["previous_period"],
            "2022": {
                "revenue": Decimal("105000000"),
                "market_share": 13.5,
                "roi": 18.5,
            },
        }

        yoy_analysis = self.template.analyze_year_over_year(yoy_data)

        self.assertIn("cagr", yoy_analysis)  # Compound Annual Growth Rate
        self.assertIn("trend_direction", yoy_analysis)
        self.assertIn("volatility", yoy_analysis)

        # CAGR should be positive for growing revenue
        self.assertGreater(yoy_analysis["cagr"], 0)

    def test_strategic_forecast(self):
        """Test strategic metric forecasting."""
        historical_data = pd.DataFrame(
            {
                "period": pd.date_range("2023-01-01", periods=12, freq="M"),
                "revenue": np.random.randint(100, 130, 12) * 1000000,
                "production": np.random.randint(90000, 110000, 12),
            }
        )

        forecast = self.template.generate_strategic_forecast(historical_data, periods=3)

        self.assertIn("revenue_forecast", forecast)
        self.assertIn("production_forecast", forecast)
        self.assertIn("confidence_interval", forecast)

        # Forecast should have correct number of periods
        self.assertEqual(len(forecast["revenue_forecast"]), 3)

    def test_strategic_goal_tracking(self):
        """Test tracking of strategic goals."""
        goals = [
            {
                "name": "Increase Production",
                "target": 2000000,
                "current": 1641667,
                "deadline": "2024-12-31",
            },
            {
                "name": "Reduce Operating Costs",
                "target": 40000000,
                "current": 45000000,
                "deadline": "2024-06-30",
            },
        ]

        tracking = self.template.track_strategic_goals(goals)

        self.assertEqual(len(tracking), 2)

        # Check production goal
        prod_goal = next(
            (g for g in tracking if g["name"] == "Increase Production"), None
        )
        self.assertIsNotNone(prod_goal)
        self.assertIn("progress_percentage", prod_goal)
        self.assertIn("on_track", prod_goal)
        self.assertIn("days_remaining", prod_goal)


if __name__ == "__main__":
    unittest.main()
