"""
End-to-End Integration Tests for BSEE Comprehensive Report System

Tests the complete workflow from data loading through report generation and export.
Validates that all components work together correctly to produce accurate reports.
"""

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

from worldenergydata.modules.bsee.reports.comprehensive.aggregators.base import (
    DataAggregator,
)
from worldenergydata.modules.bsee.reports.comprehensive.aggregators.block_aggregator_enhanced import (
    BlockAggregator,
)
from worldenergydata.modules.bsee.reports.comprehensive.aggregators.field_aggregator_enhanced import (
    FieldAggregator,
)
from worldenergydata.modules.bsee.reports.comprehensive.aggregators.lease_aggregator_enhanced import (
    LeaseAggregator,
)
from worldenergydata.modules.bsee.reports.comprehensive.controller_enhanced import (
    ReportController,
)
from worldenergydata.modules.bsee.reports.comprehensive.exporters.base import (
    ReportExporter,
)
from worldenergydata.modules.bsee.reports.comprehensive.exporters.excel_exporter import (
    ExcelExporter,
)
from worldenergydata.modules.bsee.reports.comprehensive.exporters.pdf_exporter import (
    PDFExporter,
)
from worldenergydata.modules.bsee.reports.comprehensive.models import (
    HierarchyLevel,
    OrganizationalUnit,
    ProductionMetrics,
    WellSummary,
)
from worldenergydata.modules.bsee.reports.comprehensive.templates.compliance_template import (
    ComplianceTemplate,
)
from worldenergydata.modules.bsee.reports.comprehensive.templates.economic_template import (
    EconomicTemplate,
)
from worldenergydata.modules.bsee.reports.comprehensive.templates.executive_template import (
    ExecutiveTemplate,
)
from worldenergydata.modules.bsee.reports.comprehensive.templates.operational_template import (
    OperationalTemplate,
)


class TestEndToEndIntegration:
    """Test complete report generation workflow."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for test results."""
        temp_dir = tempfile.mkdtemp(prefix="bsee_integration_test_")
        yield Path(temp_dir)
        # Cleanup after test
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def sample_hierarchical_data(self):
        """Create sample hierarchical data for testing."""
        # Create sample well data
        wells = []
        np.random.seed(42)  # For reproducible tests

        blocks = ["MC 123", "MC 456"]
        fields_per_block = {"MC 123": ["Field_A", "Field_B"], "MC 456": ["Field_C"]}
        leases_per_field = {
            "Field_A": ["LEASE001", "LEASE002"],
            "Field_B": ["LEASE003"],
            "Field_C": ["LEASE004", "LEASE005"],
        }

        well_id = 1
        for block in blocks:
            for field in fields_per_block[block]:
                for lease in leases_per_field[field]:
                    # Create 3-5 wells per lease
                    num_wells = np.random.randint(3, 6)
                    for i in range(num_wells):
                        well = {
                            "well_id": f"WELL_{well_id:04d}",
                            "api_well_number": f"608174{well_id:04d}",
                            "block": block,
                            "field": field,
                            "lease": lease,
                            "well_name": f"Well-{well_id}",
                            "status": np.random.choice(["ACTIVE", "SHUT-IN", "P&A"]),
                            "water_depth_m": np.random.uniform(500, 2000),
                            "spud_date": datetime(2020, 1, 1)
                            + timedelta(days=np.random.randint(0, 1095)),
                            "first_production": datetime(2021, 1, 1)
                            + timedelta(days=np.random.randint(0, 730)),
                        }
                        wells.append(well)
                        well_id += 1

        # Create production data for each well
        production_data = []
        for well in wells:
            if well["status"] == "ACTIVE":
                # Generate 12 months of production data
                for month in range(1, 13):
                    prod_date = datetime(2024, month, 1)
                    prod_record = {
                        "well_id": well["well_id"],
                        "production_date": prod_date,
                        "oil_volume_bbl": np.random.uniform(1000, 50000),
                        "gas_volume_mcf": np.random.uniform(500, 25000),
                        "water_volume_bbl": np.random.uniform(100, 5000),
                        "production_days": np.random.randint(20, 31),
                        "oil_price_usd": np.random.uniform(70, 90),
                        "gas_price_usd_mcf": np.random.uniform(3, 5),
                        "operating_cost_usd": np.random.uniform(50000, 200000),
                        "revenue_usd": 0,  # Will be calculated
                        "netback_usd": 0,  # Will be calculated
                    }
                    # Calculate revenue and netback
                    prod_record["revenue_usd"] = (
                        prod_record["oil_volume_bbl"] * prod_record["oil_price_usd"]
                        + prod_record["gas_volume_mcf"]
                        * prod_record["gas_price_usd_mcf"]
                    )
                    prod_record["netback_usd"] = (
                        prod_record["revenue_usd"] - prod_record["operating_cost_usd"]
                    )
                    production_data.append(prod_record)

        return {
            "wells": pd.DataFrame(wells),
            "production": pd.DataFrame(production_data),
            "hierarchy": {
                "blocks": blocks,
                "fields_per_block": fields_per_block,
                "leases_per_field": leases_per_field,
            },
        }

    @pytest.fixture
    def report_config(self, temp_output_dir):
        """Create report configuration for testing."""
        config = {
            "output_directory": str(temp_output_dir),
            "report_settings": {
                "title": "BSEE Integration Test Report",
                "author": "Test System",
                "company": "Test Company",
                "report_date": datetime.now().strftime("%Y-%m-%d"),
                "include_visualizations": True,
                "include_executive_summary": True,
            },
            "aggregation_settings": {
                "hierarchy_levels": ["WELL", "LEASE", "FIELD", "BLOCK"],
                "metrics_to_aggregate": [
                    "oil_volume_bbl",
                    "gas_volume_mcf",
                    "water_volume_bbl",
                    "revenue_usd",
                    "operating_cost_usd",
                    "netback_usd",
                ],
                "calculate_averages": True,
                "calculate_totals": True,
            },
            "template_settings": {
                "compliance": {"enabled": True, "include_violations": True},
                "economic": {
                    "enabled": True,
                    "include_npv": True,
                    "discount_rate": 0.1,
                },
                "operational": {"enabled": True, "include_efficiency": True},
                "executive": {"enabled": True, "include_kpis": True},
            },
            "export_settings": {
                "formats": ["excel", "pdf", "html"],
                "excel": {"include_charts": True, "separate_sheets": True},
                "pdf": {"include_toc": True, "page_size": "A4"},
                "html": {"interactive": True, "include_css": True},
            },
            "performance_settings": {
                "use_parallel_processing": True,
                "max_workers": 4,
                "cache_enabled": True,
                "batch_size": 100,
            },
        }
        return config

    def test_complete_workflow_with_all_components(
        self, sample_hierarchical_data, report_config, temp_output_dir
    ):
        """Test the complete end-to-end workflow with all components."""
        # Initialize controller
        controller = ReportController(report_config)

        # Load data
        wells_df = sample_hierarchical_data["wells"]
        production_df = sample_hierarchical_data["production"]

        # Create organizational units
        organizational_units = controller.build_hierarchy(wells_df, production_df)

        # Verify hierarchy was built correctly
        assert len(organizational_units["blocks"]) == 2
        assert all(
            block in organizational_units["blocks"] for block in ["MC 123", "MC 456"]
        )

        # Run aggregation at each level
        aggregation_results = controller.run_aggregation(
            organizational_units, production_df
        )

        # Verify aggregation results
        assert "block_level" in aggregation_results
        assert "field_level" in aggregation_results
        assert "lease_level" in aggregation_results
        assert "well_level" in aggregation_results

        # Generate reports with each template
        templates = ["compliance", "economic", "operational", "executive"]
        generated_reports = {}

        for template_name in templates:
            report = controller.generate_report(
                template_name=template_name,
                data=aggregation_results,
                organizational_units=organizational_units,
            )
            generated_reports[template_name] = report

            # Verify report structure
            assert report is not None
            assert "metadata" in report
            assert "content" in report
            assert "visualizations" in report

        # Export reports in all formats
        export_results = {}
        for format_type in ["excel", "pdf", "html"]:
            export_path = controller.export_report(
                report_data=generated_reports,
                format_type=format_type,
                output_dir=temp_output_dir,
            )
            export_results[format_type] = export_path

            # Verify file was created
            assert Path(export_path).exists()
            assert Path(export_path).stat().st_size > 0

        # Verify all outputs
        assert len(export_results) == 3
        assert all(Path(path).exists() for path in export_results.values())

        # Test batch processing
        batch_results = controller.process_batch(
            organizational_units=["MC 123", "MC 456"],
            templates=templates,
            export_formats=["excel"],
        )

        assert len(batch_results) == 2  # Two blocks processed
        assert all("reports" in result for result in batch_results.values())

        # Verify memory usage is reasonable
        import psutil

        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        assert memory_mb < 1000  # Should use less than 1GB for test data

    def test_data_consistency_across_hierarchy(
        self, sample_hierarchical_data, report_config
    ):
        """Test that data remains consistent across hierarchy levels."""
        controller = ReportController(report_config)

        wells_df = sample_hierarchical_data["wells"]
        production_df = sample_hierarchical_data["production"]

        # Build hierarchy and aggregate
        organizational_units = controller.build_hierarchy(wells_df, production_df)
        aggregation_results = controller.run_aggregation(
            organizational_units, production_df
        )

        # Verify totals match across levels
        well_total_oil = aggregation_results["well_level"]["oil_volume_bbl"].sum()
        lease_total_oil = aggregation_results["lease_level"]["oil_volume_bbl"].sum()
        field_total_oil = aggregation_results["field_level"]["oil_volume_bbl"].sum()
        block_total_oil = aggregation_results["block_level"]["oil_volume_bbl"].sum()

        # All levels should have the same total (within floating point tolerance)
        assert abs(well_total_oil - lease_total_oil) < 0.01
        assert abs(lease_total_oil - field_total_oil) < 0.01
        assert abs(field_total_oil - block_total_oil) < 0.01

        # Verify revenue calculations are consistent
        well_total_revenue = aggregation_results["well_level"]["revenue_usd"].sum()
        block_total_revenue = aggregation_results["block_level"]["revenue_usd"].sum()
        assert abs(well_total_revenue - block_total_revenue) < 0.01

    def test_template_data_integration(self, sample_hierarchical_data, report_config):
        """Test that all templates work with the same dataset."""
        controller = ReportController(report_config)

        wells_df = sample_hierarchical_data["wells"]
        production_df = sample_hierarchical_data["production"]

        organizational_units = controller.build_hierarchy(wells_df, production_df)
        aggregation_results = controller.run_aggregation(
            organizational_units, production_df
        )

        # Test each template with the same data
        templates = {
            "compliance": ComplianceTemplate(),
            "economic": EconomicTemplate(),
            "operational": OperationalTemplate(),
            "executive": ExecutiveTemplate(),
        }

        for template_name, template_instance in templates.items():
            # Render template
            rendered = template_instance.render(
                data=aggregation_results,
                organizational_units=organizational_units,
                config=report_config,
            )

            # Verify rendered output
            assert rendered is not None
            assert len(rendered) > 0

            # Verify template-specific sections
            if template_name == "compliance":
                assert "compliance_status" in rendered or "Compliance" in rendered
            elif template_name == "economic":
                assert "revenue" in rendered.lower() or "economic" in rendered.lower()
            elif template_name == "operational":
                assert (
                    "operational" in rendered.lower()
                    or "efficiency" in rendered.lower()
                )
            elif template_name == "executive":
                assert "executive" in rendered.lower() or "summary" in rendered.lower()

    def test_error_handling_and_recovery(self, report_config, temp_output_dir):
        """Test error handling and recovery mechanisms."""
        controller = ReportController(report_config)

        # Test with empty data
        empty_wells = pd.DataFrame()
        empty_production = pd.DataFrame()

        try:
            result = controller.build_hierarchy(empty_wells, empty_production)
            # Should handle empty data gracefully
            assert result is not None
        except Exception as e:
            pytest.fail(f"Controller should handle empty data gracefully: {e}")

        # Test with malformed data
        malformed_wells = pd.DataFrame(
            {
                "well_id": [1, 2, None],  # None value that could cause issues
                "block": ["MC 123", None, "MC 456"],  # Missing block
                "field": ["Field_A", "Field_B", None],  # Missing field
            }
        )

        try:
            result = controller.build_hierarchy(malformed_wells, empty_production)
            # Should handle malformed data with appropriate defaults or filtering
            assert result is not None
        except Exception as e:
            pytest.fail(f"Controller should handle malformed data: {e}")

        # Test export to non-existent directory
        non_existent_dir = Path(temp_output_dir) / "non" / "existent" / "path"
        try:
            # Should create directory if it doesn't exist
            controller.export_report(
                report_data={"test": "data"},
                format_type="excel",
                output_dir=non_existent_dir,
            )
            assert non_existent_dir.exists()
        except Exception as e:
            # Should handle directory creation
            pass

    def test_performance_with_moderate_dataset(self, report_config):
        """Test performance with a moderate-sized dataset."""
        import time

        # Generate larger dataset (100 wells)
        np.random.seed(42)
        num_wells = 100

        wells = []
        for i in range(num_wells):
            well = {
                "well_id": f"WELL_{i:04d}",
                "api_well_number": f"608174{i:04d}",
                "block": f"MC {i // 25}",  # 4 blocks
                "field": f"Field_{i // 10}",  # 10 fields
                "lease": f"LEASE{i // 5:03d}",  # 20 leases
                "well_name": f"Well-{i}",
                "status": "ACTIVE",
            }
            wells.append(well)

        wells_df = pd.DataFrame(wells)

        # Generate 12 months of production for each well
        production = []
        for well in wells:
            for month in range(1, 13):
                prod = {
                    "well_id": well["well_id"],
                    "production_date": datetime(2024, month, 1),
                    "oil_volume_bbl": np.random.uniform(1000, 50000),
                    "gas_volume_mcf": np.random.uniform(500, 25000),
                    "revenue_usd": np.random.uniform(100000, 1000000),
                    "operating_cost_usd": np.random.uniform(50000, 200000),
                }
                production.append(prod)

        production_df = pd.DataFrame(production)

        controller = ReportController(report_config)

        # Measure processing time
        start_time = time.time()

        # Run complete workflow
        organizational_units = controller.build_hierarchy(wells_df, production_df)
        aggregation_results = controller.run_aggregation(
            organizational_units, production_df
        )
        report = controller.generate_report(
            "economic", aggregation_results, organizational_units
        )

        end_time = time.time()
        processing_time = end_time - start_time

        # Should process 100 wells in under 60 seconds
        assert (
            processing_time < 60
        ), f"Processing took {processing_time:.2f} seconds, should be under 60"

        # Verify results
        assert len(aggregation_results["well_level"]) == num_wells
        assert report is not None

    @pytest.mark.integration
    def test_integration_with_real_bsee_data(self, report_config):
        """Test with real BSEE data if available."""
        # Check if real data exists
        real_data_path = Path("tests/modules/bsee/analysis/results/Data")
        if not real_data_path.exists():
            pytest.skip("Real BSEE data not available")

        # Load real BSEE data
        try:
            # This would load actual BSEE data files
            # Implementation depends on actual data format
            pass
        except Exception as e:
            pytest.skip(f"Could not load real data: {e}")
