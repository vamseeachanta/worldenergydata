"""
Tests for template variable substitution
Testing Jinja2 template rendering with various data types and filters
"""

import pytest
import sys
from pathlib import Path
from datetime import date, datetime
import importlib.util
from decimal import Decimal

# Direct import to avoid dependency issues
def import_template_module():
    """Import BaseReportTemplate directly"""
    base_path = Path(__file__).parent.parent.parent.parent.parent / "src" / "worldenergydata" / "modules" / "bsee" / "reports" / "comprehensive" / "templates" / "base.py"
    spec = importlib.util.spec_from_file_location("base", base_path)
    base_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base_module)
    return base_module.BaseReportTemplate, base_module.TemplateContext

BaseReportTemplate, TemplateContext = import_template_module()


class TestTemplateVariableSubstitution:
    """Test template variable substitution and rendering"""
    
    def test_basic_variable_substitution(self):
        """Test basic variable substitution in templates"""
        template = BaseReportTemplate(
            template_name="variable_test",
            template_type="economic"
        )
        
        # Create a simple template string
        template_string = "Report: {{ report_title }} - Generated: {{ generation_date | date_format }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {
            "report_title": "Economic Analysis Report",
            "generation_date": date(2024, 1, 15)
        }
        
        rendered = jinja_template.render(**context)
        
        assert "Economic Analysis Report" in rendered
        assert "2024-01-15" in rendered
    
    def test_currency_filter(self):
        """Test currency formatting filter"""
        template = BaseReportTemplate(
            template_name="currency_test",
            template_type="economic"
        )
        
        template_string = "Revenue: {{ revenue | currency }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"revenue": 1234567.89}
        rendered = jinja_template.render(**context)
        
        assert "$1,234,567.89" in rendered
    
    def test_currency_filter_with_custom_symbol(self):
        """Test currency filter with custom symbol"""
        template = BaseReportTemplate(
            template_name="currency_custom_test",
            template_type="economic"
        )
        
        template_string = "Revenue: {{ revenue | currency('€') }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"revenue": 500000.00}
        rendered = jinja_template.render(**context)
        
        assert "€500,000.00" in rendered
    
    def test_percentage_filter(self):
        """Test percentage formatting filter"""
        template = BaseReportTemplate(
            template_name="percentage_test",
            template_type="economic"
        )
        
        template_string = "Operating Margin: {{ margin | percentage }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"margin": 23.456}
        rendered = jinja_template.render(**context)
        
        assert "23.5%" in rendered
    
    def test_percentage_filter_with_decimals(self):
        """Test percentage filter with custom decimal places"""
        template = BaseReportTemplate(
            template_name="percentage_decimals_test",
            template_type="economic"
        )
        
        template_string = "Precision Margin: {{ margin | percentage(3) }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"margin": 23.45678}
        rendered = jinja_template.render(**context)
        
        assert "23.457%" in rendered
    
    def test_number_format_filter(self):
        """Test number formatting filter"""
        template = BaseReportTemplate(
            template_name="number_test",
            template_type="economic"
        )
        
        template_string = "Production: {{ production | number_format }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"production": 1234567}
        rendered = jinja_template.render(**context)
        
        assert "1,234,567" in rendered
    
    def test_number_format_filter_with_decimals(self):
        """Test number format filter with decimals"""
        template = BaseReportTemplate(
            template_name="number_decimals_test",
            template_type="economic"
        )
        
        template_string = "Rate: {{ rate | number_format(2) }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"rate": 1234.5678}
        rendered = jinja_template.render(**context)
        
        assert "1,234.57" in rendered
    
    def test_date_format_filter(self):
        """Test date formatting filter"""
        template = BaseReportTemplate(
            template_name="date_test",
            template_type="economic"
        )
        
        template_string = "Report Date: {{ report_date | date_format }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"report_date": date(2024, 3, 15)}
        rendered = jinja_template.render(**context)
        
        assert "2024-03-15" in rendered
    
    def test_date_format_filter_custom_format(self):
        """Test date format filter with custom format"""
        template = BaseReportTemplate(
            template_name="date_custom_test",
            template_type="economic"
        )
        
        template_string = "Report Date: {{ report_date | date_format('%B %d, %Y') }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"report_date": date(2024, 3, 15)}
        rendered = jinja_template.render(**context)
        
        assert "March 15, 2024" in rendered
    
    def test_bbl_format_filter(self):
        """Test barrel formatting filter"""
        template = BaseReportTemplate(
            template_name="bbl_test",
            template_type="economic"
        )
        
        template_string = "Oil Production: {{ oil_volume | bbl_format }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"oil_volume": 50000}
        rendered = jinja_template.render(**context)
        
        assert "50,000 bbl" in rendered
    
    def test_mcf_format_filter(self):
        """Test gas formatting filter"""
        template = BaseReportTemplate(
            template_name="mcf_test",
            template_type="economic"
        )
        
        template_string = "Gas Production: {{ gas_volume | mcf_format }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"gas_volume": 75000}
        rendered = jinja_template.render(**context)
        
        assert "75,000 Mcf" in rendered
    
    def test_days_format_filter(self):
        """Test days formatting filter"""
        template = BaseReportTemplate(
            template_name="days_test",
            template_type="operational"
        )
        
        template_string = "Production Days: {{ production_days | days_format }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"production_days": 365}
        rendered = jinja_template.render(**context)
        
        assert "365 days" in rendered
    
    def test_none_value_handling(self):
        """Test handling of None values in filters"""
        template = BaseReportTemplate(
            template_name="none_test",
            template_type="economic"
        )
        
        template_string = """
        Revenue: {{ revenue | currency }}
        Margin: {{ margin | percentage }}
        Production: {{ production | bbl_format }}
        Date: {{ report_date | date_format }}
        """
        
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {
            "revenue": None,
            "margin": None,
            "production": None,
            "report_date": None
        }
        
        rendered = jinja_template.render(**context)
        
        # Should contain N/A for all None values
        assert rendered.count("N/A") == 4
    
    def test_complex_nested_context(self):
        """Test variable substitution with nested context objects"""
        template = BaseReportTemplate(
            template_name="nested_test",
            template_type="economic"
        )
        
        template_string = """
        Field: {{ field.name }}
        Oil: {{ field.production.oil_bbls | bbl_format }}
        Gas: {{ field.production.gas_mcf | mcf_format }}
        Revenue: {{ field.economics.total_revenue | currency }}
        Margin: {{ field.economics.profit_margin | percentage(2) }}
        """
        
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {
            "field": {
                "name": "Jack Field",
                "production": {
                    "oil_bbls": 125000,
                    "gas_mcf": 200000
                },
                "economics": {
                    "total_revenue": 10500000.50,
                    "profit_margin": 34.567
                }
            }
        }
        
        rendered = jinja_template.render(**context)
        
        assert "Jack Field" in rendered
        assert "125,000 bbl" in rendered
        assert "200,000 Mcf" in rendered
        assert "$10,500,000.50" in rendered
        assert "34.57%" in rendered
    
    def test_custom_jinja_functions(self):
        """Test custom Jinja2 functions"""
        template = BaseReportTemplate(
            template_name="functions_test",
            template_type="economic"
        )
        
        template_string = """
        Today: {{ today() }}
        Now: {{ now().year }}
        Sum: {{ sum_list(values) }}
        Average: {{ avg_list(values) }}
        """
        
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"values": [100, 200, 300, 400, 500]}
        rendered = jinja_template.render(**context)
        
        assert str(date.today()) in rendered
        assert str(datetime.now().year) in rendered
        assert "1500" in rendered  # Sum
        assert "300.0" in rendered  # Average
    
    def test_conditional_rendering(self):
        """Test conditional rendering with Jinja2"""
        template = BaseReportTemplate(
            template_name="conditional_test",
            template_type="economic"
        )
        
        template_string = """
        {% if field.active %}
        Status: Active Field
        Production: {{ field.production | bbl_format }}
        {% else %}
        Status: Inactive Field
        {% endif %}
        
        {% if field.profit_margin > 20 %}
        Performance: Excellent
        {% elif field.profit_margin > 10 %}
        Performance: Good
        {% else %}
        Performance: Poor
        {% endif %}
        """
        
        jinja_template = template.jinja_env.from_string(template_string)
        
        # Test active field with excellent performance
        context = {
            "field": {
                "active": True,
                "production": 50000,
                "profit_margin": 25.5
            }
        }
        
        rendered = jinja_template.render(**context)
        
        assert "Active Field" in rendered
        assert "50,000 bbl" in rendered
        assert "Excellent" in rendered
        assert "Inactive Field" not in rendered
    
    def test_loop_rendering(self):
        """Test loop rendering with Jinja2"""
        template = BaseReportTemplate(
            template_name="loop_test",
            template_type="economic"
        )
        
        template_string = """
        Wells Summary:
        {% for well in wells %}
        - {{ well.name }}: {{ well.production | bbl_format }}
        {% endfor %}
        
        Total Wells: {{ wells|length }}
        """
        
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {
            "wells": [
                {"name": "Well A", "production": 1000},
                {"name": "Well B", "production": 2000},
                {"name": "Well C", "production": 1500}
            ]
        }
        
        rendered = jinja_template.render(**context)
        
        assert "Well A: 1,000 bbl" in rendered
        assert "Well B: 2,000 bbl" in rendered
        assert "Well C: 1,500 bbl" in rendered
        assert "Total Wells: 3" in rendered
    
    def test_template_error_handling(self):
        """Test template error handling for invalid syntax"""
        template = BaseReportTemplate(
            template_name="error_test",
            template_type="economic"
        )
        
        # Invalid Jinja2 syntax
        template_string = "{{ invalid.nonexistent.deeply.nested.field }}"
        jinja_template = template.jinja_env.from_string(template_string)
        
        context = {"valid_field": "value"}
        
        # This should raise an error during rendering
        with pytest.raises(Exception):
            jinja_template.render(**context)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])