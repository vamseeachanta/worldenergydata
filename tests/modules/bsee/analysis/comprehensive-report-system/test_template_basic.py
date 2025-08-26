"""
Basic tests for template system
Testing without external dependencies
"""

import pytest
import sys
from pathlib import Path
from datetime import date, datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from worldenergydata.modules.bsee.reports.comprehensive.templates.base import BaseReportTemplate, TemplateContext


class TestBaseReportTemplateBasic:
    """Basic tests for BaseReportTemplate without external dependencies"""
    
    def test_template_initialization(self):
        """Test basic template initialization"""
        template = BaseReportTemplate(
            template_name="test_template",
            template_type="economic",
            version="1.0.0"
        )
        
        assert template.template_name == "test_template"
        assert template.template_type == "economic"
        assert template.version == "1.0.0"
        assert template.jinja_env is not None
        assert isinstance(template.context, dict)
    
    def test_invalid_template_type(self):
        """Test template with invalid type raises error"""
        with pytest.raises(ValueError, match="Invalid template type"):
            BaseReportTemplate(
                template_name="test",
                template_type="invalid_type"
            )
    
    def test_supported_template_types(self):
        """Test all supported template types"""
        supported_types = ["economic", "operational", "compliance", "executive"]
        
        for template_type in supported_types:
            template = BaseReportTemplate(
                template_name=f"{template_type}_test",
                template_type=template_type
            )
            assert template.template_type == template_type
    
    def test_context_setting(self):
        """Test setting and getting template context"""
        template = BaseReportTemplate(
            template_name="context_test",
            template_type="economic"
        )
        
        test_context = {
            "report_date": date(2024, 1, 1),
            "entity_id": "FIELD-001",
            "data": {"production": 1000}
        }
        
        template.set_context(test_context)
        retrieved_context = template.get_context()
        
        assert retrieved_context["report_date"] == test_context["report_date"]
        assert retrieved_context["entity_id"] == test_context["entity_id"]
        assert retrieved_context["data"] == test_context["data"]
    
    def test_default_context(self):
        """Test default context variables"""
        template = BaseReportTemplate(
            template_name="defaults_test",
            template_type="economic"
        )
        
        default_context = template.get_default_context()
        
        assert "report_title" in default_context
        assert "generation_date" in default_context
        assert "template_version" in default_context
        assert "organization_hierarchy" in default_context
        assert default_context["template_version"] == template.version
    
    def test_metadata_handling(self):
        """Test template metadata storage and retrieval"""
        template = BaseReportTemplate(
            template_name="metadata_test",
            template_type="economic"
        )
        
        template.set_metadata("author", "Test Author")
        template.set_metadata("description", "Test Description")
        template.set_metadata("created_date", date(2024, 1, 1))
        
        assert template.get_metadata("author") == "Test Author"
        assert template.get_metadata("description") == "Test Description"
        assert template.get_metadata("created_date") == date(2024, 1, 1)
        assert template.get_metadata("non_existent", "default") == "default"
    
    def test_jinja_filters_registration(self):
        """Test that custom Jinja filters are registered"""
        template = BaseReportTemplate(
            template_name="filter_test",
            template_type="economic"
        )
        
        # Test custom filters are registered
        assert 'currency' in template.jinja_env.filters
        assert 'percentage' in template.jinja_env.filters
        assert 'number_format' in template.jinja_env.filters
        assert 'date_format' in template.jinja_env.filters
        assert 'bbl_format' in template.jinja_env.filters
        assert 'mcf_format' in template.jinja_env.filters
    
    def test_template_rendering_basic(self):
        """Test basic template rendering"""
        template = BaseReportTemplate(
            template_name="render_test",
            template_type="economic"
        )
        
        # Set required context
        template.set_context({
            "report_date": date(2024, 1, 1),
            "entity_id": "TEST-001",
            "production_metrics": {"oil_bbls": 1000},
            "financial_summary": {"revenue": 50000}
        })
        
        # This should not raise an error
        rendered = template.render()
        assert isinstance(rendered, str)
        assert len(rendered) > 0
        assert "Economic Report" in rendered  # Default title
    
    def test_string_representation(self):
        """Test template string representation"""
        template = BaseReportTemplate(
            template_name="repr_test",
            template_type="economic",
            version="1.2.3"
        )
        
        repr_str = repr(template)
        assert "BaseReportTemplate" in repr_str
        assert "repr_test" in repr_str
        assert "economic" in repr_str
        assert "1.2.3" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])