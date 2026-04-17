"""
Tests for Well Detail View Components.

Tests production charts, economic metrics, decline curves, and verification integration.
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import yaml

# Import components to test
from worldenergydata.well_production_dashboard.well_detail_views import (
    AuditTrailLink,
    ChartQualityIndicator,
    DeclineCurveAnalyzer,
    EconomicMetricsCalculator,
    ProductionChartBuilder,
    VerificationStatusBadge,
    WellDetailConfig,
    WellDetailView,
)


class TestWellDetailConfig(unittest.TestCase):
    """Test well detail view configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WellDetailConfig()
        self.assertTrue(config.show_quality_indicators)
        self.assertTrue(config.enable_audit_links)
        self.assertEqual(config.chart_refresh_rate, 500)
        self.assertEqual(config.quality_threshold, 0.8)

    def test_custom_config(self):
        """Test custom configuration."""
        config = WellDetailConfig(
            show_quality_indicators=False,
            chart_refresh_rate=1000,
            quality_threshold=0.9,
        )
        self.assertFalse(config.show_quality_indicators)
        self.assertEqual(config.chart_refresh_rate, 1000)
        self.assertEqual(config.quality_threshold, 0.9)

    def test_load_from_yaml(self):
        """Test loading configuration from YAML."""
        yaml_content = """
        show_quality_indicators: true
        enable_audit_links: true
        chart_refresh_rate: 750
        quality_threshold: 0.85
        chart_types:
          - production_time_series
          - decline_curve
          - economic_waterfall
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = WellDetailConfig.from_yaml(temp_path)
            self.assertEqual(config.chart_refresh_rate, 750)
            self.assertEqual(config.quality_threshold, 0.85)
            self.assertIn("decline_curve", config.chart_types)
        finally:
            Path(temp_path).unlink()


class TestProductionChartBuilder(unittest.TestCase):
    """Test production chart builder component."""

    def setUp(self):
        """Set up test data."""
        # Create sample production data
        dates = pd.date_range("2020-01-01", periods=36, freq="ME")
        self.production_data = pd.DataFrame(
            {
                "date": dates,
                "oil_production": np.random.uniform(1000, 5000, 36),
                "gas_production": np.random.uniform(10000, 50000, 36),
                "water_production": np.random.uniform(100, 1000, 36),
                "quality_score": np.random.uniform(0.7, 1.0, 36),
                "verification_status": np.random.choice(
                    ["verified", "pending", "failed"], 36
                ),
            }
        )

        self.builder = ProductionChartBuilder()

    def test_create_time_series_chart(self):
        """Test creating time series production chart."""
        chart = self.builder.create_time_series_chart(
            self.production_data, well_name="Test Well 001"
        )

        self.assertIsNotNone(chart)
        self.assertEqual(chart["type"], "time_series")
        self.assertIn("data", chart)
        self.assertIn("layout", chart)
        self.assertEqual(len(chart["data"]), 3)  # Oil, gas, water

    def test_add_quality_indicators(self):
        """Test adding quality indicators to chart."""
        chart = self.builder.create_time_series_chart(
            self.production_data, well_name="Test Well 001"
        )

        chart_with_quality = self.builder.add_quality_indicators(
            chart,
            self.production_data["quality_score"],
            self.production_data["verification_status"],
        )

        # Check that quality indicators were added
        self.assertIn("quality_overlay", chart_with_quality)
        self.assertIn("verification_markers", chart_with_quality)

    def test_create_decline_curve_chart(self):
        """Test creating decline curve chart."""
        chart = self.builder.create_decline_curve_chart(
            self.production_data["oil_production"].values,
            self.production_data["date"].values,
            well_name="Test Well 001",
        )

        self.assertIsNotNone(chart)
        self.assertEqual(chart["type"], "decline_curve")
        self.assertIn("actual_production", chart["data"])
        self.assertIn("fitted_curve", chart["data"])
        self.assertIn("forecast", chart["data"])

    def test_create_stacked_production_chart(self):
        """Test creating stacked production chart."""
        chart = self.builder.create_stacked_production_chart(
            self.production_data, well_name="Test Well 001"
        )

        self.assertIsNotNone(chart)
        self.assertEqual(chart["type"], "stacked_area")
        self.assertIn("data", chart)
        self.assertEqual(len(chart["data"]), 3)  # Oil, gas, water stacked

    def test_chart_with_annotations(self):
        """Test adding annotations for data quality issues."""
        chart = self.builder.create_time_series_chart(
            self.production_data, well_name="Test Well 001"
        )

        # Check if there are any existing annotations
        initial_annotations = 0
        if "layout" in chart and hasattr(chart["layout"], "annotations"):
            initial_annotations = (
                len(chart["layout"].annotations) if chart["layout"].annotations else 0
            )

        annotations = [
            {"date": "2020-06-01", "text": "Data quality issue"},
            {"date": "2021-01-01", "text": "Verification pending"},
        ]

        annotated_chart = self.builder.add_annotations(chart, annotations)
        self.assertIn("annotations", annotated_chart)
        self.assertIn("layout", annotated_chart)
        # Should have initial annotations plus 2 new ones
        if hasattr(annotated_chart["layout"], "annotations"):
            self.assertEqual(
                len(annotated_chart["layout"].annotations), initial_annotations + 2
            )
        else:
            # If annotations are stored differently, check the stored annotations
            self.assertEqual(len(annotated_chart["annotations"]), 2)


class TestEconomicMetricsCalculator(unittest.TestCase):
    """Test economic metrics calculator."""

    def setUp(self):
        """Set up test data."""
        self.calculator = EconomicMetricsCalculator()

        # Sample production and price data
        self.production_data = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=36, freq="ME"),
                "oil_production": np.random.uniform(1000, 5000, 36),
                "gas_production": np.random.uniform(10000, 50000, 36),
                "oil_price": np.random.uniform(40, 80, 36),
                "gas_price": np.random.uniform(2, 5, 36),
                "opex": np.random.uniform(10000, 30000, 36),
                "capex": [100000 if i == 0 else 0 for i in range(36)],
            }
        )

    def test_calculate_revenue(self):
        """Test revenue calculation."""
        revenue = self.calculator.calculate_revenue(
            self.production_data["oil_production"].values,
            self.production_data["oil_price"].values,
            self.production_data["gas_production"].values,
            self.production_data["gas_price"].values,
        )

        self.assertIsNotNone(revenue)
        self.assertEqual(len(revenue), 36)
        self.assertTrue(all(r >= 0 for r in revenue))

    def test_calculate_npv(self):
        """Test NPV calculation."""
        cash_flows = (
            self.calculator.calculate_revenue(
                self.production_data["oil_production"].values,
                self.production_data["oil_price"].values,
                self.production_data["gas_production"].values,
                self.production_data["gas_price"].values,
            )
            - self.production_data["opex"].values
            - self.production_data["capex"].values
        )

        npv = self.calculator.calculate_npv(cash_flows, discount_rate=0.1)
        self.assertIsInstance(npv, float)

    def test_calculate_irr(self):
        """Test IRR calculation."""
        cash_flows = (
            self.calculator.calculate_revenue(
                self.production_data["oil_production"].values,
                self.production_data["oil_price"].values,
                self.production_data["gas_production"].values,
                self.production_data["gas_price"].values,
            )
            - self.production_data["opex"].values
            - self.production_data["capex"].values
        )

        irr = self.calculator.calculate_irr(cash_flows)
        self.assertIsInstance(irr, float)
        self.assertTrue(-1 <= irr <= 10)  # Reasonable IRR range

    def test_calculate_payback_period(self):
        """Test payback period calculation."""
        cash_flows = (
            self.calculator.calculate_revenue(
                self.production_data["oil_production"].values,
                self.production_data["oil_price"].values,
                self.production_data["gas_production"].values,
                self.production_data["gas_price"].values,
            )
            - self.production_data["opex"].values
            - self.production_data["capex"].values
        )

        payback = self.calculator.calculate_payback_period(cash_flows)
        self.assertIsInstance(payback, (int, float))
        self.assertTrue(0 <= payback <= 36)

    def test_create_waterfall_chart(self):
        """Test creating economic waterfall chart."""
        chart = self.calculator.create_waterfall_chart(
            revenue=1000000,
            opex=300000,
            capex=100000,
            taxes=150000,
            well_name="Test Well 001",
        )

        self.assertIsNotNone(chart)
        self.assertEqual(chart["type"], "waterfall")
        self.assertIn("data", chart)
        self.assertIn("categories", chart["data"])


class TestDeclineCurveAnalyzer(unittest.TestCase):
    """Test decline curve analyzer."""

    def setUp(self):
        """Set up test data."""
        self.analyzer = DeclineCurveAnalyzer()

        # Create declining production data
        time = np.arange(0, 36)
        self.production = 5000 * np.exp(-0.02 * time) + np.random.normal(0, 100, 36)
        self.dates = pd.date_range("2020-01-01", periods=36, freq="ME")

    def test_fit_exponential_decline(self):
        """Test fitting exponential decline curve."""
        params = self.analyzer.fit_exponential_decline(self.production, self.dates)

        self.assertIn("initial_production", params)
        self.assertIn("decline_rate", params)
        self.assertIn("r_squared", params)
        self.assertTrue(0 <= params["r_squared"] <= 1)

    def test_fit_hyperbolic_decline(self):
        """Test fitting hyperbolic decline curve."""
        params = self.analyzer.fit_hyperbolic_decline(self.production, self.dates)

        self.assertIn("initial_production", params)
        self.assertIn("decline_rate", params)
        self.assertIn("b_factor", params)
        self.assertIn("r_squared", params)

    def test_forecast_production(self):
        """Test production forecasting."""
        params = self.analyzer.fit_exponential_decline(self.production, self.dates)

        forecast = self.analyzer.forecast_production(
            params, periods=12, decline_type="exponential"
        )

        self.assertEqual(len(forecast), 12)
        self.assertTrue(all(f > 0 for f in forecast))

    def test_calculate_eur(self):
        """Test Estimated Ultimate Recovery calculation."""
        params = self.analyzer.fit_exponential_decline(self.production, self.dates)

        eur = self.analyzer.calculate_eur(
            params, economic_limit=100, decline_type="exponential"
        )

        self.assertIsInstance(eur, float)
        self.assertTrue(eur > sum(self.production))

    def test_create_type_curve(self):
        """Test creating type curve visualization."""
        chart = self.analyzer.create_type_curve(
            self.production, self.dates, well_name="Test Well 001"
        )

        self.assertIsNotNone(chart)
        self.assertEqual(chart["type"], "type_curve")
        self.assertIn("actual_data", chart["data"])
        self.assertIn("fitted_curve", chart["data"])


class TestVerificationStatusBadge(unittest.TestCase):
    """Test verification status badge component."""

    def setUp(self):
        """Set up test instance."""
        self.badge = VerificationStatusBadge()

    def test_create_verified_badge(self):
        """Test creating verified status badge."""
        badge = self.badge.create(
            status="verified", quality_score=0.95, timestamp=datetime.now()
        )

        self.assertEqual(badge["status"], "verified")
        self.assertEqual(badge["color"], "green")
        self.assertEqual(badge["icon"], "✓")
        self.assertIn("tooltip", badge)

    def test_create_pending_badge(self):
        """Test creating pending status badge."""
        badge = self.badge.create(
            status="pending", quality_score=0.75, timestamp=datetime.now()
        )

        self.assertEqual(badge["status"], "pending")
        self.assertEqual(badge["color"], "yellow")
        self.assertEqual(badge["icon"], "⚠")

    def test_create_failed_badge(self):
        """Test creating failed status badge."""
        badge = self.badge.create(
            status="failed", quality_score=0.45, timestamp=datetime.now()
        )

        self.assertEqual(badge["status"], "failed")
        self.assertEqual(badge["color"], "red")
        self.assertEqual(badge["icon"], "✗")

    def test_badge_with_details(self):
        """Test badge with detailed information."""
        badge = self.badge.create(
            status="verified",
            quality_score=0.92,
            timestamp=datetime.now(),
            details={"completeness": 0.95, "accuracy": 0.90, "consistency": 0.92},
        )

        self.assertIn("details", badge)
        self.assertEqual(len(badge["details"]), 3)


class TestAuditTrailLink(unittest.TestCase):
    """Test audit trail link component."""

    def setUp(self):
        """Set up test instance."""
        self.audit_link = AuditTrailLink()

    def test_create_audit_link(self):
        """Test creating audit trail link."""
        link = self.audit_link.create(
            well_id="WELL-001", verification_id="VER-12345", timestamp=datetime.now()
        )

        self.assertIn("url", link)
        self.assertIn("text", link)
        self.assertIn("icon", link)
        self.assertIn("VER-12345", link["url"])

    def test_create_batch_audit_links(self):
        """Test creating multiple audit links."""
        verification_ids = ["VER-001", "VER-002", "VER-003"]
        links = self.audit_link.create_batch(
            well_id="WELL-001", verification_ids=verification_ids
        )

        self.assertEqual(len(links), 3)
        for link, ver_id in zip(links, verification_ids):
            self.assertIn(ver_id, link["url"])

    def test_format_audit_summary(self):
        """Test formatting audit trail summary."""
        summary = self.audit_link.format_summary(
            total_verifications=10, passed=8, failed=1, pending=1
        )

        self.assertIn("total", summary)
        self.assertIn("passed", summary)
        self.assertIn("success_rate", summary)
        self.assertEqual(summary["success_rate"], 0.8)


class TestWellDetailView(unittest.TestCase):
    """Test main well detail view component."""

    def setUp(self):
        """Set up test data and mocks."""
        self.config = WellDetailConfig()
        self.view = WellDetailView(self.config)

        # Create comprehensive test data
        dates = pd.date_range("2020-01-01", periods=36, freq="ME")
        self.well_data = {
            "well_id": "WELL-001",
            "well_name": "Test Well 001",
            "field": "Test Field",
            "production": pd.DataFrame(
                {
                    "date": dates,
                    "oil": np.random.uniform(1000, 5000, 36),
                    "gas": np.random.uniform(10000, 50000, 36),
                    "water": np.random.uniform(100, 1000, 36),
                }
            ),
            "economics": pd.DataFrame(
                {
                    "date": dates,
                    "revenue": np.random.uniform(50000, 200000, 36),
                    "opex": np.random.uniform(10000, 30000, 36),
                    "capex": [100000 if i == 0 else 0 for i in range(36)],
                }
            ),
            "verification": pd.DataFrame(
                {
                    "date": dates,
                    "quality_score": np.random.uniform(0.7, 1.0, 36),
                    "status": np.random.choice(["verified", "pending", "failed"], 36),
                    "verification_id": [f"VER-{i:05d}" for i in range(36)],
                }
            ),
        }

    @patch("worldenergydata.analysis.dashboard.well_detail_views.VerificationWorkflow")
    def test_render_well_detail_page(self, mock_verification):
        """Test rendering complete well detail page."""
        mock_verification.return_value.get_verification_status.return_value = {
            "status": "verified",
            "quality_score": 0.92,
        }

        page = self.view.render(self.well_data)

        self.assertIsNotNone(page)
        self.assertIn("header", page)
        self.assertIn("charts", page)
        self.assertIn("metrics", page)
        self.assertIn("verification_status", page)

    def test_create_production_section(self):
        """Test creating production charts section."""
        section = self.view.create_production_section(
            self.well_data["production"], self.well_data["verification"]
        )

        self.assertIn("time_series_chart", section)
        self.assertIn("decline_curve", section)
        self.assertIn("quality_indicators", section)

    def test_create_economic_section(self):
        """Test creating economic metrics section."""
        section = self.view.create_economic_section(
            self.well_data["economics"], self.well_data["production"]
        )

        self.assertIn("npv", section)
        self.assertIn("irr", section)
        self.assertIn("payback_period", section)
        self.assertIn("waterfall_chart", section)

    def test_create_verification_section(self):
        """Test creating verification status section."""
        section = self.view.create_verification_section(self.well_data["verification"])

        self.assertIn("current_status", section)
        self.assertIn("quality_timeline", section)
        self.assertIn("audit_links", section)

    def test_export_functionality(self):
        """Test export to PDF/Excel functionality."""
        # Test PDF export
        pdf_data = self.view.export_to_pdf(self.well_data)
        self.assertIsNotNone(pdf_data)
        self.assertIsInstance(pdf_data, bytes)

        # Test Excel export
        excel_data = self.view.export_to_excel(self.well_data)
        self.assertIsNotNone(excel_data)
        self.assertIsInstance(excel_data, bytes)

    def test_real_time_update(self):
        """Test real-time data update functionality."""
        # Create a simpler initial page without decline curves
        simple_config = WellDetailConfig(chart_types=["production_time_series"])
        simple_view = WellDetailView(simple_config)

        # Initial render with simple config
        initial_page = simple_view.render(self.well_data)

        # Update data
        new_production = pd.DataFrame(
            {
                "date": [pd.Timestamp("2023-01-01")],
                "oil": [4500],
                "gas": [45000],
                "water": [900],
            }
        )

        updated_page = simple_view.update_real_time(initial_page, new_production)

        self.assertIsNotNone(updated_page)
        # Check that the page was marked as updated
        self.assertTrue(updated_page.get("real_time_update", False))

    def test_drill_down_functionality(self):
        """Test drill-down to verification details."""
        verification_id = "VER-00001"
        details = self.view.get_verification_details(
            self.well_data["well_id"], verification_id
        )

        self.assertIsNotNone(details)
        self.assertIn("audit_trail", details)
        self.assertIn("quality_checks", details)
        self.assertIn("validation_rules", details)

    def test_performance_metrics(self):
        """Test performance with large dataset."""
        # Create large dataset
        large_dates = pd.date_range("2010-01-01", periods=120, freq="ME")
        large_data = {
            "well_id": "WELL-001",
            "production": pd.DataFrame(
                {
                    "date": large_dates,
                    "oil": np.random.uniform(1000, 5000, 120),
                    "gas": np.random.uniform(10000, 50000, 120),
                    "water": np.random.uniform(100, 1000, 120),
                }
            ),
        }

        import time

        start_time = time.time()
        page = self.view.render(large_data)
        render_time = time.time() - start_time

        self.assertIsNotNone(page)
        self.assertLess(render_time, 3.0)  # Should render in less than 3 seconds


if __name__ == "__main__":
    unittest.main()
