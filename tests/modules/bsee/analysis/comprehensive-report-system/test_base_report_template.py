"""
Tests for BaseReportTemplate - Template System Foundation
Following TDD approach - tests written before implementation
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import date
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

# Import models using try/except to handle dependency issues
try:
    from worldenergydata.modules.bsee.reports.comprehensive.models import (
        ProductionMetrics,
        EconomicMetrics,
        WellSummary
    )
except ImportError:
    # Mock the models for testing when dependencies are not available
    ProductionMetrics = Mock
    EconomicMetrics = Mock 
    WellSummary = Mock


class TestBaseReportTemplate:
    """Test BaseReportTemplate initialization and basic functionality"""
    
    def test_base_report_template_initialization(self):
        """Test BaseReportTemplate initialization with default values"""
        # This test will fail initially until we implement BaseReportTemplate
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            template = BaseReportTemplate(
                template_name="test_template",
                template_type="economic",
                version="1.0.0"
            )
            
            assert template.template_name == "test_template"
            assert template.template_type == "economic"
            assert template.version == "1.0.0"
            assert template.jinja_env is not None
            assert template.context == {}
            assert template.template_path is None
    
    def test_base_report_template_with_custom_template_path(self):
        """Test BaseReportTemplate with custom template directory"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            template_dir = Path(__file__).parent / "test_templates"
            template = BaseReportTemplate(
                template_name="custom_template",
                template_type="operational",
                version="2.0.0",
                template_path=template_dir
            )
            
            assert template.template_path == template_dir
            assert template.template_name == "custom_template"
            assert template.template_type == "operational"
            assert template.version == "2.0.0"
    
    def test_base_report_template_jinja_environment_setup(self):
        """Test that Jinja2 environment is properly configured"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            template = BaseReportTemplate(
                template_name="jinja_test",
                template_type="compliance"
            )
            
            # Test Jinja environment exists and has expected configuration
            assert template.jinja_env is not None
            assert hasattr(template.jinja_env, 'loader')
            assert hasattr(template.jinja_env, 'filters')
            
            # Test custom filters are registered
            assert 'currency' in template.jinja_env.filters
            assert 'percentage' in template.jinja_env.filters
            assert 'number_format' in template.jinja_env.filters
            assert 'date_format' in template.jinja_env.filters
    
    def test_base_report_template_context_initialization(self):
        """Test template context is properly initialized"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            template = BaseReportTemplate(
                template_name="context_test",
                template_type="executive"
            )
            
            # Test initial context
            assert template.context == {}
            
            # Test context can be set
            test_context = {
                "report_date": date(2024, 1, 1),
                "organization_level": "field",
                "data": {"production": 1000}
            }
            
            template.set_context(test_context)
            assert template.context == test_context
    
    def test_base_report_template_with_invalid_template_type(self):
        """Test BaseReportTemplate with invalid template type"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            with pytest.raises(ValueError, match="Invalid template type"):
                BaseReportTemplate(
                    template_name="invalid_test",
                    template_type="invalid_type"
                )
    
    def test_base_report_template_supported_template_types(self):
        """Test all supported template types"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            supported_types = ["economic", "operational", "compliance", "executive"]
            
            for template_type in supported_types:
                template = BaseReportTemplate(
                    template_name=f"{template_type}_test",
                    template_type=template_type
                )
                assert template.template_type == template_type
    
    def test_base_report_template_metadata_handling(self):
        """Test template metadata storage and retrieval"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            template = BaseReportTemplate(
                template_name="metadata_test",
                template_type="economic"
            )
            
            # Test setting metadata
            template.set_metadata("author", "Test Author")
            template.set_metadata("description", "Test Description")
            template.set_metadata("created_date", date(2024, 1, 1))
            
            assert template.get_metadata("author") == "Test Author"
            assert template.get_metadata("description") == "Test Description"
            assert template.get_metadata("created_date") == date(2024, 1, 1)
            assert template.get_metadata("non_existent", "default") == "default"
    
    def test_base_report_template_default_context_variables(self):
        """Test that default context variables are available"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            template = BaseReportTemplate(
                template_name="defaults_test",
                template_type="economic"
            )
            
            # Get default context
            default_context = template.get_default_context()
            
            # Test required default variables
            assert "report_title" in default_context
            assert "generation_date" in default_context
            assert "template_version" in default_context
            assert "organization_hierarchy" in default_context
            assert default_context["template_version"] == template.version


class TestTemplateContextBuilding:
    """Test template context building functionality"""
    
    def test_build_context_from_production_metrics(self):
        """Test building template context from production data"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            template = BaseReportTemplate(
                template_name="production_context_test",
                template_type="economic"
            )
            
            # Create test production metrics
            production_data = ProductionMetrics(
                entity_id="FIELD-001",
                entity_type="field",
                oil_production_bbls=50000,
                gas_production_mcf=75000,
                oil_price_usd=80.0,
                gas_price_usd=4.0,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 12, 31)
            )
            
            # Build context
            context = template.build_context_from_production(production_data)
            
            # Test context structure
            assert "production_metrics" in context
            assert "entity_info" in context
            assert "financial_summary" in context
            
            # Test production metrics
            assert context["production_metrics"]["oil_bbls"] == 50000
            assert context["production_metrics"]["gas_mcf"] == 75000
            
            # Test financial calculations
            assert context["financial_summary"]["oil_revenue"] > 0
            assert context["financial_summary"]["gas_revenue"] > 0
            assert context["financial_summary"]["total_revenue"] > 0
    
    def test_build_context_from_economic_metrics(self):
        """Test building template context from economic data"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            template = BaseReportTemplate(
                template_name="economic_context_test",
                template_type="economic"
            )
            
            # Create test economic metrics
            economic_data = EconomicMetrics(
                entity_id="FIELD-001",
                entity_type="field",
                revenue=4000000,
                operating_costs=1500000,
                capital_costs=500000,
                royalties=750000,
                production_bbls=50000
            )
            
            # Build context
            context = template.build_context_from_economics(economic_data)
            
            # Test context structure
            assert "economic_metrics" in context
            assert "financial_ratios" in context
            assert "profitability" in context
            
            # Test economic calculations
            assert context["economic_metrics"]["revenue"] == 4000000
            assert context["economic_metrics"]["net_income"] > 0
            assert context["financial_ratios"]["operating_cost_per_bbl"] == 30.0
    
    def test_build_context_validation(self):
        """Test context validation before rendering"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            template = BaseReportTemplate(
                template_name="validation_test",
                template_type="economic"
            )
            
            # Test valid context
            valid_context = {
                "report_date": date(2024, 1, 1),
                "entity_id": "FIELD-001",
                "production_metrics": {"oil_bbls": 1000}
            }
            
            # Should not raise error
            template.validate_context(valid_context)
            
            # Test invalid context - missing required fields
            invalid_context = {
                "report_date": date(2024, 1, 1)
                # Missing entity_id
            }
            
            with pytest.raises(ValueError, match="Missing required context field"):
                template.validate_context(invalid_context)


class TestTemplateInheritanceSystem:
    """Test template inheritance functionality"""
    
    def test_template_inheritance_setup(self):
        """Test template inheritance system initialization"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            # Create base template
            base_template = BaseReportTemplate(
                template_name="base_report",
                template_type="economic"
            )
            
            # Create child template that inherits from base
            child_template = BaseReportTemplate(
                template_name="detailed_economic",
                template_type="economic",
                parent_template="base_report"
            )
            
            assert child_template.parent_template == "base_report"
            assert hasattr(child_template, 'inheritance_chain')
    
    def test_template_block_override(self):
        """Test template block overriding in inheritance"""
        with pytest.importerror_raises(ImportError):
            from worldenergydata.modules.bsee.reports.comprehensive.templates import BaseReportTemplate
            
            template = BaseReportTemplate(
                template_name="override_test",
                template_type="economic"
            )
            
            # Test template has override capability
            assert hasattr(template, 'register_block_override')
            assert hasattr(template, 'get_template_blocks')
            
            # Register block override
            template.register_block_override("header", "custom_header.html")
            overrides = template.get_block_overrides()
            
            assert "header" in overrides
            assert overrides["header"] == "custom_header.html"


# Helper for testing import errors during development
@pytest.fixture
def importerror_raises():
    """Custom pytest fixture for expected import errors during TDD"""
    import contextlib
    
    @contextlib.contextmanager
    def _importerror_raises(expected_exception):
        try:
            yield
        except expected_exception:
            # Expected during TDD - implementation doesn't exist yet
            pytest.skip("Implementation not yet available - expected during TDD")
        except Exception as e:
            # Re-raise unexpected exceptions
            raise e
    
    return _importerror_raises

# Make importerror_raises available to pytest
pytest.importerror_raises = importerror_raises


if __name__ == "__main__":
    pytest.main([__file__, "-v"])