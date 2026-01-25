"""
Tests for ReportController
Following TDD approach - tests written before implementation
"""

import pytest
from datetime import datetime, date
from pathlib import Path
import json
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from worldenergydata.modules.bsee.reports.comprehensive.controller import (
    ReportController,
    ReportConfiguration,
    ReportParameters,
    ReportType
)


class TestReportConfiguration:
    """Test ReportConfiguration class"""
    
    def test_report_configuration_initialization(self):
        """Test basic ReportConfiguration initialization"""
        config = ReportConfiguration(
            report_type=ReportType.FIELD,
            entity_name="Jack",
            date_range=(date(2020, 1, 1), date(2024, 12, 31)),
            output_formats=["excel", "pdf", "html"]
        )
        
        assert config.report_type == ReportType.FIELD
        assert config.entity_name == "Jack"
        assert config.date_range[0] == date(2020, 1, 1)
        assert config.date_range[1] == date(2024, 12, 31)
        assert "excel" in config.output_formats
        assert "pdf" in config.output_formats
        assert "html" in config.output_formats
    
    def test_report_configuration_validation(self):
        """Test configuration validation"""
        # Invalid date range (end before start)
        with pytest.raises(ValueError, match="Invalid date range"):
            ReportConfiguration(
                report_type=ReportType.WELL,
                entity_name="PS001",
                date_range=(date(2024, 1, 1), date(2020, 1, 1))
            )
        
        # Invalid output format
        with pytest.raises(ValueError, match="Invalid output format"):
            ReportConfiguration(
                report_type=ReportType.LEASE,
                entity_name="OCS-G-12345",
                output_formats=["invalid_format"]
            )
    
    def test_report_configuration_from_dict(self):
        """Test creating configuration from dictionary"""
        config_dict = {
            "report_type": "field",
            "entity_name": "Julia",
            "date_range": ["2020-01-01", "2024-12-31"],
            "output_formats": ["excel"],
            "include_economics": True,
            "include_visualizations": True
        }
        
        config = ReportConfiguration.from_dict(config_dict)
        
        assert config.report_type == ReportType.FIELD
        assert config.entity_name == "Julia"
        assert config.include_economics is True
        assert config.include_visualizations is True


class TestReportParameters:
    """Test ReportParameters class"""
    
    def test_report_parameters_defaults(self):
        """Test default report parameters"""
        params = ReportParameters()
        
        assert params.price_deck is not None
        assert params.discount_rate == 0.10
        assert params.royalty_rate == 0.1875
        assert params.operating_cost_per_bbl > 0
        assert params.aggregation_level == "default"
    
    def test_report_parameters_custom(self):
        """Test custom report parameters"""
        custom_price_deck = {
            "oil": {"2024": 80.00, "2025": 82.00},
            "gas": {"2024": 4.00, "2025": 4.25}
        }
        
        params = ReportParameters(
            price_deck=custom_price_deck,
            discount_rate=0.12,
            royalty_rate=0.20,
            operating_cost_per_bbl=15.00
        )
        
        assert params.price_deck["oil"]["2024"] == 80.00
        assert params.discount_rate == 0.12
        assert params.royalty_rate == 0.20
        assert params.operating_cost_per_bbl == 15.00
    
    def test_report_parameters_validation(self):
        """Test parameter validation"""
        # Invalid discount rate
        with pytest.raises(ValueError, match="Invalid discount rate"):
            ReportParameters(discount_rate=1.5)
        
        # Invalid royalty rate
        with pytest.raises(ValueError, match="Invalid royalty rate"):
            ReportParameters(royalty_rate=-0.1)


class TestReportController:
    """Test ReportController class"""
    
    def test_report_controller_initialization(self):
        """Test ReportController initialization"""
        controller = ReportController()
        
        assert controller is not None
        assert controller.data_source is not None
        assert controller.template_engine is not None
        assert controller.export_manager is not None
        assert controller.cache is not None
    
    def test_report_controller_with_config_file(self):
        """Test loading controller with configuration file"""
        # Create test config file
        config_path = Path("test_config.json")
        config_data = {
            "data_source": {
                "type": "bsee",
                "connection": "test_connection"
            },
            "templates": {
                "path": "templates/",
                "default": "field_summary.jinja2"
            },
            "cache": {
                "enabled": True,
                "ttl": 3600
            }
        }
        
        with open(config_path, "w") as f:
            json.dump(config_data, f)
        
        try:
            controller = ReportController(config_file=config_path)
            assert controller.config["cache"]["enabled"] is True
            assert controller.config["cache"]["ttl"] == 3600
        finally:
            config_path.unlink()  # Clean up
    
    def test_generate_single_report(self):
        """Test generating a single report"""
        controller = ReportController()
        
        config = ReportConfiguration(
            report_type=ReportType.WELL,
            entity_name="PS001",
            date_range=(date(2020, 1, 1), date(2024, 12, 31)),
            output_formats=["excel"]
        )
        
        params = ReportParameters()
        
        # This will fail until implementation is complete
        with pytest.raises(NotImplementedError):
            report = controller.generate_report(config, params)
    
    def test_batch_report_generation(self):
        """Test batch report generation"""
        controller = ReportController()
        
        entities = ["Jack", "Julia", "St. Malo", "Stones"]
        
        configs = [
            ReportConfiguration(
                report_type=ReportType.FIELD,
                entity_name=entity,
                date_range=(date(2020, 1, 1), date(2024, 12, 31)),
                output_formats=["excel", "pdf"]
            )
            for entity in entities
        ]
        
        params = ReportParameters()
        
        # This will fail until implementation is complete
        with pytest.raises(NotImplementedError):
            reports = controller.batch_generate(configs, params, parallel=True)
    
    def test_report_validation(self):
        """Test report validation"""
        controller = ReportController()
        
        # Test validation method
        config = ReportConfiguration(
            report_type=ReportType.FIELD,
            entity_name="Jack"
        )
        
        # Validate entity exists
        with pytest.raises(ValueError, match="Entity not found"):
            controller.validate_entity(config.entity_name, config.report_type)
    
    def test_report_caching(self):
        """Test report caching functionality"""
        controller = ReportController()
        
        config = ReportConfiguration(
            report_type=ReportType.FIELD,
            entity_name="Jack",
            date_range=(date(2024, 1, 1), date(2024, 1, 31))
        )
        
        cache_key = controller.generate_cache_key(config)
        assert cache_key is not None
        assert isinstance(cache_key, str)
        
        # Test cache operations
        test_data = {"test": "data"}
        controller.cache_set(cache_key, test_data)
        cached_data = controller.cache_get(cache_key)
        assert cached_data == test_data
    
    def test_report_metadata_generation(self):
        """Test report metadata generation"""
        controller = ReportController()
        
        config = ReportConfiguration(
            report_type=ReportType.BLOCK,
            entity_name="Walker Ridge 759"
        )
        
        metadata = controller.generate_metadata(config)
        
        assert metadata["report_type"] == "block"
        assert metadata["entity_name"] == "Walker Ridge 759"
        assert "generated_at" in metadata
        assert "version" in metadata
        assert metadata["data_source"] == "BSEE"


class TestReportType:
    """Test ReportType enum"""
    
    def test_report_type_values(self):
        """Test ReportType enum values"""
        assert ReportType.WELL.value == "well"
        assert ReportType.LEASE.value == "lease"
        assert ReportType.FIELD.value == "field"
        assert ReportType.BLOCK.value == "block"
    
    def test_report_type_hierarchy(self):
        """Test report type hierarchy levels"""
        assert ReportType.get_hierarchy_level(ReportType.WELL) == 1
        assert ReportType.get_hierarchy_level(ReportType.LEASE) == 2
        assert ReportType.get_hierarchy_level(ReportType.FIELD) == 3
        assert ReportType.get_hierarchy_level(ReportType.BLOCK) == 4
    
    def test_report_type_from_string(self):
        """Test creating ReportType from string"""
        assert ReportType.from_string("well") == ReportType.WELL
        assert ReportType.from_string("FIELD") == ReportType.FIELD
        assert ReportType.from_string("Block") == ReportType.BLOCK
        
        with pytest.raises(ValueError):
            ReportType.from_string("invalid")


class TestHierarchyRelationships:
    """Test hierarchy relationship building utilities"""
    
    def test_build_hierarchy_from_data(self):
        """Test building hierarchy from raw data"""
        controller = ReportController()
        
        # Sample data structure
        raw_data = {
            "wells": [
                {"id": "W1", "name": "PS001", "lease_id": "L1"},
                {"id": "W2", "name": "PS002", "lease_id": "L1"},
                {"id": "W3", "name": "PS003", "lease_id": "L2"}
            ],
            "leases": [
                {"id": "L1", "number": "OCS-G-12345", "field_id": "F1"},
                {"id": "L2", "number": "OCS-G-12346", "field_id": "F1"}
            ],
            "fields": [
                {"id": "F1", "name": "Jack", "block_id": "B1"}
            ],
            "blocks": [
                {"id": "B1", "number": "759", "area": "Walker Ridge"}
            ]
        }
        
        hierarchy = controller.build_hierarchy(raw_data)
        
        assert hierarchy is not None
        assert hierarchy.root.id == "B1"
        assert len(hierarchy.get_fields()) == 1
        assert len(hierarchy.get_leases()) == 2
        assert len(hierarchy.get_wells()) == 3
    
    def test_hierarchy_traversal(self):
        """Test traversing hierarchy relationships"""
        controller = ReportController()
        
        # Build test hierarchy
        hierarchy = controller.create_test_hierarchy()
        
        # Test upward traversal (well to block)
        well = hierarchy.get_well_by_id("W1")
        lease = hierarchy.get_parent(well)
        field = hierarchy.get_parent(lease)
        block = hierarchy.get_parent(field)
        
        assert lease is not None
        assert field is not None
        assert block is not None
        assert block.level == "block"
        
        # Test downward traversal (block to wells)
        block_wells = hierarchy.get_all_wells_in_block(block.id)
        assert len(block_wells) > 0
    
    def test_hierarchy_aggregation(self):
        """Test aggregating metrics through hierarchy"""
        controller = ReportController()
        
        hierarchy = controller.create_test_hierarchy()
        
        # Set well-level production
        wells = hierarchy.get_wells()
        for i, well in enumerate(wells):
            well.set_metric("daily_production", 1000 * (i + 1))
        
        # Test aggregation up the hierarchy
        lease_production = hierarchy.aggregate_to_lease("daily_production")
        field_production = hierarchy.aggregate_to_field("daily_production")
        block_production = hierarchy.aggregate_to_block("daily_production")
        
        assert lease_production > 0
        assert field_production >= lease_production
        assert block_production >= field_production


if __name__ == "__main__":
    pytest.main([__file__, "-v"])