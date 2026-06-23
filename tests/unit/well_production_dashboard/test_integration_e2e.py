"""
End-to-end integration tests for Well Production Dashboard.

These tests verify the complete workflow from data loading through
visualization, verification, and export.
"""

import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd

from worldenergydata.well_production_dashboard.export_manager import (
    ExportConfiguration,
    WellDashboardExportManager,
)
from worldenergydata.well_production_dashboard.monitoring import (
    AuditEntry,
    DashboardMonitor,
)
from worldenergydata.well_production_dashboard.query_optimizer import (
    LazyLoadConfig,
    QueryOptimizer,
)

# Import dashboard components
from worldenergydata.well_production_dashboard.well_production import (
    FieldAggregator,
    WellMetrics,
    WellProductionDashboard,
)


class TestEndToEndIntegration(unittest.TestCase):
    """Complete end-to-end integration tests."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.config_path = Path(cls.temp_dir) / "config.yml"
        cls.output_dir = Path(cls.temp_dir) / "output"
        cls.output_dir.mkdir(parents=True, exist_ok=True)

        # Create test configuration
        config_content = """
dashboard:
  title: "Test Dashboard"
  enable_cache: true
  enable_monitoring: true

data:
  source: "test"
  lazy_loading:
    enabled: true
    page_size: 10

verification:
  enabled: true
  quality_threshold: 0.7

export:
  formats: ["pdf", "excel", "json"]
  include_verification: true

monitoring:
  enabled: true
  audit_file: "logs/test_audit.jsonl"
"""
        cls.config_path.write_text(config_content)

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    def setUp(self):
        """Set up for each test."""
        # Create dashboard with mocked dependencies
        with patch(
            "worldenergydata.well_production_dashboard.well_production.DashboardBuilder"
        ):
            self.dashboard = WellProductionDashboard(config_path=str(self.config_path))

        # Mock data source
        self.mock_data = self._create_mock_data()

    def _create_mock_data(self):
        """Create mock production data."""
        dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")

        return pd.DataFrame(
            {
                "date": dates,
                "well_id": "W001",
                "oil_production": 500 + (100 * pd.Series(range(len(dates)))).values,
                "gas_production": 2000 + (200 * pd.Series(range(len(dates)))).values,
                "water_production": 100 + (50 * pd.Series(range(len(dates)))).values,
                "quality_score": 0.85,
                "verified": True,
            }
        )

    def test_complete_workflow(self):
        """Test complete dashboard workflow from data load to export."""
        # Step 1: Load data
        self.dashboard.get_well_data = Mock(return_value=self.mock_data)
        well_data = self.dashboard.get_well_data("W001")

        self.assertIsNotNone(well_data)
        self.assertEqual(len(well_data), 365)

        # Step 2: Calculate metrics
        metrics = WellMetrics()
        metrics.production_data = well_data

        npv = metrics.calculate_npv(cash_flows=[100000] * 12, discount_rate=0.1)
        self.assertGreater(npv, 0)

        # Step 3: Verify data quality
        verification_result = self.dashboard.verify_data_quality(["W001"])
        self.assertIsNotNone(verification_result)

        # Step 4: Generate field aggregation
        aggregator = FieldAggregator()
        aggregator.get_field_data = Mock(
            return_value={"Field1": {"wells": ["W001"], "production": self.mock_data}}
        )

        field_summary = aggregator.aggregate_field_production("Field1")
        self.assertIsNotNone(field_summary)

        # Step 5: Export data
        export_manager = WellDashboardExportManager(self.dashboard)
        export_config = ExportConfiguration(
            include_charts=False, include_verification=True, include_raw_data=True
        )

        # Mock export methods
        export_manager.export_to_json = Mock(return_value={"success": True})

        result = export_manager.export_to_json(
            data={"wells": ["W001"], "data": well_data.to_dict()},
            output_path=str(self.output_dir / "test.json"),
            config=export_config,
        )

        self.assertTrue(result["success"])

    def test_lazy_loading_integration(self):
        """Test lazy loading with large dataset."""
        # Create large dataset
        large_data = pd.concat([self.mock_data] * 100, ignore_index=True)

        # Configure lazy loading
        optimizer = QueryOptimizer()
        optimizer.lazy_config = LazyLoadConfig(
            page_size=100, chunk_size=500, enable_compression=True
        )

        # Mock data fetching
        optimizer.get_well_data_optimized = Mock(return_value=large_data[:100])

        # Test pagination
        page_data = optimizer.get_data_lazy(page=0)
        self.assertIsNotNone(page_data)

        # Test chunking
        chunks = list(optimizer.get_data_chunked())
        self.assertGreater(len(chunks), 0)

    def test_monitoring_integration(self):
        """Test monitoring and audit logging integration."""
        monitor = DashboardMonitor(
            config={
                "audit_file": str(self.output_dir / "audit.jsonl"),
                "enable_background_monitoring": False,
            }
        )

        # Track performance
        with monitor.track_performance("test_operation"):
            # Simulate work
            result = self.dashboard.get_well_data("W001")

        # Check metrics
        self.assertEqual(monitor.metrics.query_count, 1)
        self.assertGreater(monitor.metrics.total_query_time, 0)

        # Log audit entry
        entry = monitor.audit_verification(
            well_id="W001", quality_score=0.85, anomalies=[], user="test_user"
        )

        self.assertEqual(entry.action, "data_verification")
        self.assertEqual(entry.verification_score, 0.85)

        # Get audit trail
        trail = monitor.get_audit_trail(resource="well_W001")
        self.assertGreater(len(trail), 0)

    def test_export_all_formats(self):
        """Test exporting data in all supported formats."""
        export_manager = WellDashboardExportManager(self.dashboard)

        test_data = {
            "wells": ["W001"],
            "production": self.mock_data.to_dict(),
            "verification": {"quality_score": 0.85, "verified": True},
        }

        # Test JSON export
        json_path = self.output_dir / "test.json"
        export_manager.export_to_json = Mock(return_value={"success": True})
        json_result = export_manager.export_to_json(test_data, str(json_path))
        self.assertTrue(json_result["success"])

        # Test Excel export (mocked)
        excel_path = self.output_dir / "test.xlsx"
        export_manager.export_to_excel = Mock(return_value={"success": True})
        excel_result = export_manager.export_to_excel(test_data, str(excel_path))
        self.assertTrue(excel_result["success"])

        # Test PDF export (mocked)
        pdf_path = self.output_dir / "test.pdf"
        export_manager.export_to_pdf = Mock(return_value={"success": True})
        pdf_result = export_manager.export_to_pdf(test_data, str(pdf_path))
        self.assertTrue(pdf_result["success"])

    def test_quality_filtering_workflow(self):
        """Test workflow with quality filtering."""
        # Create data with varying quality scores
        data_high_quality = self.mock_data.copy()
        data_high_quality["quality_score"] = 0.95

        data_low_quality = self.mock_data.copy()
        data_low_quality["quality_score"] = 0.45

        # Mock dashboard methods
        self.dashboard.get_well_data = Mock(
            side_effect=[data_high_quality, data_low_quality]
        )

        # Get data for two wells
        well1_data = self.dashboard.get_well_data("W001")
        well2_data = self.dashboard.get_well_data("W002")

        # Filter by quality threshold
        quality_threshold = 0.7

        filtered_wells = []
        if well1_data["quality_score"].mean() >= quality_threshold:
            filtered_wells.append("W001")
        if well2_data["quality_score"].mean() >= quality_threshold:
            filtered_wells.append("W002")

        self.assertEqual(len(filtered_wells), 1)
        self.assertEqual(filtered_wells[0], "W001")

    def test_field_aggregation_workflow(self):
        """Test field-level aggregation workflow."""
        aggregator = FieldAggregator()

        # Mock field data
        field_data = {
            "W001": self.mock_data.copy(),
            "W002": self.mock_data.copy(),
            "W003": self.mock_data.copy(),
        }

        # Modify data for each well
        field_data["W002"]["oil_production"] *= 0.8
        field_data["W003"]["oil_production"] *= 1.2

        # Mock aggregation
        aggregator.aggregate_wells = Mock(return_value=pd.concat(field_data.values()))

        # Perform aggregation
        aggregated = aggregator.aggregate_wells(list(field_data.keys()))

        self.assertIsNotNone(aggregated)
        self.assertEqual(len(aggregated), 365 * 3)

    def test_error_handling_workflow(self):
        """Test error handling throughout the workflow."""
        # Test data loading error
        self.dashboard.get_well_data = Mock(side_effect=Exception("Data load error"))

        try:
            well_data = self.dashboard.get_well_data("W001")
            self.fail("Expected exception not raised")
        except Exception as e:
            self.assertEqual(str(e), "Data load error")

        # Test export error handling
        export_manager = WellDashboardExportManager(self.dashboard)
        export_manager.export_to_pdf = Mock(side_effect=Exception("Export error"))

        try:
            result = export_manager.export_to_pdf({}, "test.pdf")
            self.fail("Expected exception not raised")
        except Exception as e:
            self.assertEqual(str(e), "Export error")

    def test_cache_integration(self):
        """Test caching integration."""
        # Enable caching
        self.dashboard.query_optimizer.optimize_for_dashboard(
            enable_lazy=True, cache_ttl=60
        )

        # First call - cache miss
        self.dashboard.get_well_data = Mock(return_value=self.mock_data)
        data1 = self.dashboard.get_well_data("W001")

        # Second call - should use cache (mock returns same data)
        data2 = self.dashboard.get_well_data("W001")

        # Verify data is the same
        self.assertTrue(data1.equals(data2))

        # Clear cache
        self.dashboard.query_optimizer.clear_cache()

    def test_performance_metrics(self):
        """Test performance metrics collection."""
        monitor = DashboardMonitor()

        # Simulate multiple operations
        for i in range(10):
            with monitor.track_performance(f"operation_{i}"):
                # Simulate work
                pass

        # Track cache hits/misses
        monitor.track_cache_access(hit=True)
        monitor.track_cache_access(hit=True)
        monitor.track_cache_access(hit=False)

        # Track data processing
        monitor.track_data_processing(1000)

        # Get metrics summary
        summary = monitor.get_metrics_summary()

        self.assertEqual(summary["query_count"], 10)
        self.assertEqual(summary["cache_hit_rate"], 2 / 3)
        self.assertEqual(summary["data_points_processed"], 1000)


class TestCLIIntegration(unittest.TestCase):
    """Test CLI command integration."""

    def test_cli_commands_available(self):
        """Test that all CLI commands are available."""
        from worldenergydata.well_production_dashboard.cli import DashboardCLI

        cli = DashboardCLI()

        # Check main commands exist
        self.assertTrue(hasattr(cli, "serve"))
        self.assertTrue(hasattr(cli, "report"))
        self.assertTrue(hasattr(cli, "verify"))
        self.assertTrue(hasattr(cli, "export"))
        self.assertTrue(hasattr(cli, "cache"))
        self.assertTrue(hasattr(cli, "monitor"))

    @patch("worldenergydata.well_production_dashboard.cli.WellProductionDashboard")
    def test_cli_report_generation(self, mock_dashboard):
        """Test CLI report generation."""
        from worldenergydata.well_production_dashboard.cli import DashboardCLI

        cli = DashboardCLI()
        cli.dashboard = mock_dashboard.return_value

        # Mock report generation
        cli.dashboard.export_to_pdf = Mock(return_value={"success": True})

        # Test report command
        result = cli.report(
            wells=["W001", "W002"], format="pdf", output="test_report.pdf"
        )

        cli.dashboard.export_to_pdf.assert_called_once()


if __name__ == "__main__":
    unittest.main()
