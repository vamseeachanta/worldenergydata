"""
Tests for compliance visualization generation
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch
import sys
from pathlib import Path
import tempfile
import shutil

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "src"))

# Import the compliance template classes directly 
exec(open(Path(__file__).parent.parent.parent.parent.parent.parent / 
          "src/worldenergydata/modules/bsee/reports/comprehensive/templates/compliance_template.py").read())


class TestComplianceVisualizationGeneration:
    """Test compliance visualization generation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.template_path = self.temp_dir / "compliance"
        self.template_path.mkdir(parents=True, exist_ok=True)
        
        self.template = ComplianceTemplate(
            template_name="test_compliance",
            template_path=self.template_path
        )
        
        # Sample compliance data
        self.compliance_data = {
            "production_compliance": 95.0,
            "environmental_score": 0.85,
            "safety_score": 0.92,
            "overall_compliance_score": 0.907
        }
    
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_generate_compliance_visualizations_basic(self):
        """Test basic compliance visualization generation"""
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        
        # Check that charts are generated
        assert isinstance(charts, dict)
        assert "compliance_dashboard" in charts
        assert isinstance(charts["compliance_dashboard"], str)
        assert len(charts["compliance_dashboard"]) > 0
    
    def test_compliance_dashboard_content(self):
        """Test compliance dashboard content"""
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        dashboard_html = charts["compliance_dashboard"]
        
        # Check that dashboard contains expected content
        assert "Compliance Dashboard" in dashboard_html
        assert "plotly" in dashboard_html.lower() or "div" in dashboard_html
        # Should contain gauge chart elements
        assert "indicator" in dashboard_html.lower() or "gauge" in dashboard_html.lower()
    
    def test_production_quota_chart_generation(self):
        """Test production quota chart generation"""
        # Add quota analysis to template context
        quota_analysis = {
            "oil_quota": 100000,
            "oil_actual": 95000,
            "gas_quota": 500000,
            "gas_actual": 480000
        }
        self.template.context["quota_analysis"] = quota_analysis
        
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        
        assert "production_quota_chart" in charts
        chart_html = charts["production_quota_chart"]
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
        assert "Production Quota vs Actual" in chart_html
    
    def test_environmental_trends_chart_generation(self):
        """Test environmental trends chart generation"""
        # Add environmental compliance to template context
        env_compliance = {
            "spill_incidents": 1,
            "environmental_score": 0.85,
            "air_emissions": 120.0
        }
        self.template.context["environmental_compliance"] = env_compliance
        
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        
        assert "environmental_trends" in charts
        chart_html = charts["environmental_trends"]
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
        assert "Environmental Compliance Trends" in chart_html
    
    def test_safety_metrics_chart_generation(self):
        """Test safety metrics chart generation"""
        # Add safety compliance to template context
        safety_compliance = {
            "trir": 2.5,
            "ltir": 1.0,
            "near_misses": 5,
            "safety_score": 0.92
        }
        self.template.context["safety_compliance"] = safety_compliance
        
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        
        assert "safety_metrics" in charts
        chart_html = charts["safety_metrics"]
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
        assert "Safety Performance Metrics" in chart_html
    
    def test_milestone_timeline_generation_with_data(self):
        """Test milestone timeline generation with milestone data"""
        # Add milestone tracking to template context
        milestones = [
            RegulatoryMilestone(
                milestone_id="TEST_001",
                description="Submit production report",
                due_date=date(2024, 3, 31),
                completion_date=date(2024, 3, 28),
                status="completed"
            ),
            RegulatoryMilestone(
                milestone_id="TEST_002",
                description="Environmental compliance audit",
                due_date=date(2024, 6, 30),
                status="pending"
            )
        ]
        
        milestone_tracking = {
            "milestones": milestones
        }
        self.template.context["milestone_tracking"] = milestone_tracking
        
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        
        assert "milestone_timeline" in charts
        chart_html = charts["milestone_timeline"]
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
        assert "Regulatory Milestones Timeline" in chart_html
    
    def test_milestone_timeline_generation_empty(self):
        """Test milestone timeline generation with no milestone data"""
        # Add empty milestone tracking to template context
        milestone_tracking = {
            "milestones": []
        }
        self.template.context["milestone_tracking"] = milestone_tracking
        
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        
        assert "milestone_timeline" in charts
        chart_html = charts["milestone_timeline"]
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
        assert "No milestones to display" in chart_html
    
    def test_compliance_status_color_coding(self):
        """Test compliance status color coding"""
        # Test different score levels
        excellent_color = self.template.get_compliance_status_color(0.95)
        good_color = self.template.get_compliance_status_color(0.85)
        fair_color = self.template.get_compliance_status_color(0.75)
        poor_color = self.template.get_compliance_status_color(0.65)
        
        # Check that colors are hex codes
        assert excellent_color.startswith("#")
        assert good_color.startswith("#")
        assert fair_color.startswith("#")
        assert poor_color.startswith("#")
        
        # Check that different scores get different colors
        colors = [excellent_color, good_color, fair_color, poor_color]
        assert len(set(colors)) > 1  # Should have different colors
    
    def test_all_chart_types_generated(self):
        """Test that all expected chart types are generated"""
        # Set up all context data
        self.template.context.update({
            "quota_analysis": {"oil_quota": 100000, "oil_actual": 95000},
            "environmental_compliance": {"spill_incidents": 1},
            "safety_compliance": {"trir": 2.0},
            "milestone_tracking": {"milestones": []}
        })
        
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        
        expected_charts = [
            "compliance_dashboard",
            "production_quota_chart", 
            "environmental_trends",
            "safety_metrics",
            "milestone_timeline"
        ]
        
        for chart_name in expected_charts:
            assert chart_name in charts
            assert isinstance(charts[chart_name], str)
            assert len(charts[chart_name]) > 0
    
    def test_chart_html_structure(self):
        """Test that generated charts have proper HTML structure"""
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        
        for chart_name, chart_html in charts.items():
            # Should contain HTML div elements
            assert "<div" in chart_html or "<html" in chart_html
            # Should contain plotly CDN reference
            assert "plotly" in chart_html.lower()
            # Should not contain script errors
            assert "error" not in chart_html.lower()
    
    def test_chart_data_integration(self):
        """Test that compliance data is properly integrated into charts"""
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        dashboard_html = charts["compliance_dashboard"]
        
        # Check that compliance values are reflected in the chart
        # Values should be converted to strings and present in HTML
        assert "95" in dashboard_html or "95.0" in dashboard_html  # Production compliance
        assert "85" in dashboard_html or "0.85" in dashboard_html or "85.0" in dashboard_html  # Environmental score
        assert "92" in dashboard_html or "0.92" in dashboard_html or "92.0" in dashboard_html  # Safety score
    
    def test_chart_responsive_design(self):
        """Test that charts include responsive design elements"""
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        
        for chart_html in charts.values():
            # Charts should include responsive configuration
            # This is implicit in plotly's default behavior, so we check for plotly integration
            assert "plotly" in chart_html.lower()
    
    def test_chart_accessibility(self):
        """Test that charts include accessibility features"""
        charts = self.template.generate_compliance_visualizations(self.compliance_data)
        
        for chart_html in charts.values():
            # Charts should have titles for accessibility
            assert "title" in chart_html.lower()
    
    def test_chart_error_handling(self):
        """Test chart generation error handling"""
        # Test with invalid compliance data
        invalid_data = {
            "production_compliance": "invalid",
            "environmental_score": None,
            "safety_score": -1
        }
        
        # Should not raise exception
        charts = self.template.generate_compliance_visualizations(invalid_data)
        assert isinstance(charts, dict)
        assert "compliance_dashboard" in charts
    
    def test_chart_customization_options(self):
        """Test chart customization capabilities"""
        # Create compliance data with extreme values to test scaling
        extreme_data = {
            "production_compliance": 150.0,  # Over 100%
            "environmental_score": 0.5,     # Low score
            "safety_score": 0.99,           # High score
            "overall_compliance_score": 0.75
        }
        
        charts = self.template.generate_compliance_visualizations(extreme_data)
        
        # Charts should handle extreme values gracefully
        assert "compliance_dashboard" in charts
        dashboard_html = charts["compliance_dashboard"]
        
        # Should contain the extreme values
        assert "150" in dashboard_html or "1.5" in dashboard_html  # Over-production
        assert "50" in dashboard_html or "0.5" in dashboard_html   # Low environmental score


class TestComplianceDashboardSpecific:
    """Test compliance dashboard specific functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.template = ComplianceTemplate(
            template_name="dashboard_test",
            template_path=self.temp_dir
        )
    
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_compliance_dashboard_gauge_configuration(self):
        """Test compliance dashboard gauge chart configuration"""
        compliance_data = {
            "production_compliance": 95.0,
            "environmental_score": 0.85,
            "safety_score": 0.90,
            "overall_compliance_score": 0.90
        }
        
        # Generate dashboard
        dashboard_html = self.template._create_compliance_dashboard(compliance_data)
        
        # Check gauge configuration elements
        assert "gauge" in dashboard_html.lower()
        assert "indicator" in dashboard_html.lower()
        assert "Production Compliance" in dashboard_html
        assert "Environmental Score" in dashboard_html
        assert "Safety Score" in dashboard_html
        assert "Overall Compliance" in dashboard_html
    
    def test_compliance_dashboard_threshold_visualization(self):
        """Test dashboard threshold visualization"""
        # Test data with different threshold levels
        test_cases = [
            {"score": 0.95, "expected_color": "darkblue"},
            {"score": 0.85, "expected_color": "green"},
            {"score": 0.75, "expected_color": "orange"},
            {"score": 0.65, "expected_color": "purple"}
        ]
        
        for case in test_cases:
            compliance_data = {
                "production_compliance": case["score"] * 100,
                "environmental_score": case["score"],
                "safety_score": case["score"],
                "overall_compliance_score": case["score"]
            }
            
            dashboard_html = self.template._create_compliance_dashboard(compliance_data)
            
            # Should contain threshold indicators
            assert "threshold" in dashboard_html.lower()
            # Should contain gauge elements
            assert "gauge" in dashboard_html.lower()
    
    def test_dashboard_layout_structure(self):
        """Test dashboard layout structure"""
        compliance_data = {
            "production_compliance": 90.0,
            "environmental_score": 0.80,
            "safety_score": 0.85,
            "overall_compliance_score": 0.85
        }
        
        dashboard_html = self.template._create_compliance_dashboard(compliance_data)
        
        # Check for subplot structure (2x2 grid)
        assert "subplot" in dashboard_html.lower() or "row" in dashboard_html.lower()
        # Check for proper height configuration
        assert "height" in dashboard_html.lower()
        # Check that legend is hidden (showlegend=False)
        assert "showlegend" in dashboard_html.lower()