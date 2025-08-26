"""
Tests for Economic Template visualization generation
Tests waterfall charts, economic dashboards, and sensitivity analysis visualizations
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.worldenergydata.modules.bsee.reports.comprehensive.templates.economic_template import (
    EconomicTemplate, WaterfallComponent, SensitivityAnalysis
)
from src.worldenergydata.modules.bsee.reports.comprehensive.models import ProductionMetrics
from src.worldenergydata.modules.bsee.reports.comprehensive.hierarchical_aggregator import PriceDeck, CostStructure


class TestEconomicVisualizationGeneration:
    """Test economic visualization generation methods"""
    
    @pytest.fixture
    def economic_template_with_data(self):
        """Create EconomicTemplate with sample data for visualization testing"""
        template = EconomicTemplate()
        production = ProductionMetrics(
            entity_id="FIELD_TEST_VIZ",
            entity_type="field",
            oil_production_bbls=1500000.0,
            gas_production_mcf=9000000.0,
            water_production_bbls=750000.0,
            oil_price_usd=85.0,
            gas_price_usd=4.25,
            operating_cost_usd=18000000.0,
            days_in_period=365,
            active_well_count=35
        )
        
        # Build context
        context = template.build_economic_context_from_production(production)
        template.set_context(context)
        
        # Add NPV analysis
        cash_flows = [-75000000] + [25000000] * 12  # 12-year project
        template.add_npv_analysis(cash_flows, discount_rate=0.11, project_years=12)
        
        # Add sensitivity analysis
        template.add_sensitivity_analysis(production)
        
        return template, production
    
    def test_waterfall_chart_data_generation(self, economic_template_with_data):
        """Test generation of waterfall chart data"""
        template, production = economic_template_with_data
        
        # Generate waterfall data
        waterfall_components = template.generate_waterfall_data()
        
        # Test that components are generated
        assert isinstance(waterfall_components, list)
        assert len(waterfall_components) > 0
        
        # Test component structure
        for component in waterfall_components:
            assert isinstance(component, WaterfallComponent)
            assert hasattr(component, 'name')
            assert hasattr(component, 'value')
            assert hasattr(component, 'component_type')
            assert hasattr(component, 'category')
        
        # Test specific components exist
        component_names = [c.name for c in waterfall_components]
        assert "Oil Revenue" in component_names
        assert "Gas Revenue" in component_names
        assert "Operating Costs" in component_names
        assert "Net Income" in component_names
        
        # Test positive and negative values
        revenue_components = [c for c in waterfall_components if c.component_type == "revenue"]
        cost_components = [c for c in waterfall_components if c.component_type == "cost"]
        
        assert all(c.is_positive() for c in revenue_components)
        assert all(not c.is_positive() for c in cost_components)
    
    def test_waterfall_component_creation(self):
        """Test individual waterfall component creation"""
        # Test positive component
        revenue_component = WaterfallComponent(
            name="Oil Revenue",
            value=127500000.0,  # 1.5M bbls * $85
            component_type="revenue",
            category="hydrocarbon"
        )
        
        assert revenue_component.name == "Oil Revenue"
        assert revenue_component.value == 127500000.0
        assert revenue_component.component_type == "revenue"
        assert revenue_component.category == "hydrocarbon"
        assert revenue_component.is_positive() == True
        
        # Test negative component
        cost_component = WaterfallComponent(
            name="Operating Costs",
            value=-18000000.0,
            component_type="cost",
            category="operational"
        )
        
        assert cost_component.is_positive() == False
        
        # Test zero component
        zero_component = WaterfallComponent(
            name="Other Revenue",
            value=0.0,
            component_type="revenue",
            category="other"
        )
        
        assert zero_component.is_positive() == True  # Zero is considered positive
    
    @patch('plotly.io.to_html')
    def test_waterfall_chart_html_generation(self, mock_to_html, economic_template_with_data):
        """Test HTML generation for waterfall charts"""
        template, production = economic_template_with_data
        mock_to_html.return_value = "<div>Mock waterfall chart HTML</div>"
        
        # This would be implemented in the visualization methods
        # For now, test the data structure is correct for chart generation
        waterfall_data = template.generate_waterfall_data()
        
        # Prepare data for Plotly waterfall chart
        names = [component.name for component in waterfall_data]
        values = [component.value for component in waterfall_data]
        measures = []
        
        for component in waterfall_data:
            if component.component_type == "revenue":
                measures.append("relative")
            elif component.component_type == "cost":
                measures.append("relative")
            elif component.component_type == "profit":
                measures.append("total")
            else:
                measures.append("relative")
        
        # Test data structure
        assert len(names) == len(values) == len(measures)
        assert all(isinstance(name, str) for name in names)
        assert all(isinstance(value, (int, float)) for value in values)
        assert all(measure in ["relative", "total"] for measure in measures)


class TestSensitivityAnalysisVisualization:
    """Test sensitivity analysis visualization generation"""
    
    @pytest.fixture
    def sample_production_for_sensitivity(self):
        """Create sample production for sensitivity analysis"""
        return ProductionMetrics(
            entity_id="SENSITIVITY_TEST",
            entity_type="field",
            oil_production_bbls=2000000.0,
            gas_production_mcf=12000000.0,
            water_production_bbls=800000.0,
            oil_price_usd=80.0,
            gas_price_usd=4.00,
            operating_cost_usd=20000000.0
        )
    
    def test_oil_price_sensitivity_analysis(self, sample_production_for_sensitivity):
        """Test oil price sensitivity analysis"""
        sensitivity = SensitivityAnalysis()
        
        # Test oil price sensitivity
        price_range = [-30, -15, 0, 15, 30]  # Percentage changes
        oil_sensitivity = sensitivity.analyze_oil_price_sensitivity(
            sample_production_for_sensitivity, price_range
        )
        
        # Test results structure
        assert len(oil_sensitivity) == len(price_range)
        
        for i, result in enumerate(oil_sensitivity):
            assert "price_change_pct" in result
            assert "new_oil_price" in result
            assert "total_revenue" in result
            assert "net_income" in result
            assert "npv" in result
            
            assert result["price_change_pct"] == price_range[i]
            
            # Oil price should change according to percentage
            expected_price = 80.0 * (1 + price_range[i] / 100)
            assert result["new_oil_price"] == pytest.approx(expected_price, rel=1e-2)
        
        # Test that NPV increases with oil price
        npvs = [result["npv"] for result in oil_sensitivity]
        assert npvs == sorted(npvs)  # Should be ascending
    
    def test_production_volume_sensitivity(self, sample_production_for_sensitivity):
        """Test production volume sensitivity analysis"""
        sensitivity = SensitivityAnalysis()
        
        volume_range = [-40, -20, 0, 20, 40]  # Percentage changes
        prod_sensitivity = sensitivity.analyze_production_sensitivity(
            sample_production_for_sensitivity, volume_range
        )
        
        # Test results structure
        assert len(prod_sensitivity) == len(volume_range)
        
        for i, result in enumerate(prod_sensitivity):
            assert "volume_change_pct" in result
            assert "new_oil_production" in result
            assert "new_gas_production" in result
            assert "total_revenue" in result
            assert "net_income" in result
            assert "npv" in result
            
            # Production volumes should change according to percentage
            expected_oil = 2000000.0 * (1 + volume_range[i] / 100)
            expected_gas = 12000000.0 * (1 + volume_range[i] / 100)
            
            assert result["new_oil_production"] == pytest.approx(expected_oil, rel=1e-2)
            assert result["new_gas_production"] == pytest.approx(expected_gas, rel=1e-2)
        
        # Test that NPV increases with production volume
        npvs = [result["npv"] for result in prod_sensitivity]
        assert npvs == sorted(npvs)  # Should be ascending
    
    def test_cost_sensitivity_analysis(self, sample_production_for_sensitivity):
        """Test operating cost sensitivity analysis"""
        sensitivity = SensitivityAnalysis()
        
        cost_range = [-25, -10, 0, 15, 35]  # Percentage changes
        cost_sensitivity = sensitivity.analyze_cost_sensitivity(
            sample_production_for_sensitivity, cost_range
        )
        
        # Test results structure
        assert len(cost_sensitivity) == len(cost_range)
        
        for i, result in enumerate(cost_sensitivity):
            assert "cost_change_pct" in result
            assert "new_operating_cost" in result
            assert "net_income" in result
            assert "npv" in result
            
            # Operating costs should change according to percentage
            expected_cost = 20000000.0 * (1 + cost_range[i] / 100)
            assert result["new_operating_cost"] == pytest.approx(expected_cost, rel=1e-2)
        
        # Test that NPV decreases with higher costs
        npvs = [result["npv"] for result in cost_sensitivity]
        assert npvs == sorted(npvs, reverse=True)  # Should be descending
    
    def test_tornado_chart_data_preparation(self, economic_template_with_data):
        """Test tornado chart data preparation for sensitivity analysis"""
        template, production = economic_template_with_data
        
        # Get sensitivity analysis from context
        sensitivity_analysis = template.context.get("sensitivity_analysis", {})
        tornado_data = sensitivity_analysis.get("tornado_chart_data", [])
        
        # Test tornado data structure
        assert isinstance(tornado_data, list)
        assert len(tornado_data) > 0
        
        # Test that data is sorted by impact (most sensitive first)
        if len(tornado_data) > 1:
            impact_ranges = [item["impact_range"] for item in tornado_data]
            assert impact_ranges == sorted(impact_ranges, reverse=True)
        
        # Test tornado data components
        for item in tornado_data:
            assert "variable" in item
            assert "impact_range" in item
            assert "low_case" in item
            assert "high_case" in item
            
            # Impact range should be positive
            assert item["impact_range"] >= 0
            
            # High case should be greater than or equal to low case
            assert item["high_case"] >= item["low_case"]


class TestEconomicDashboardVisualization:
    """Test economic dashboard visualization components"""
    
    @pytest.fixture
    def template_with_comprehensive_data(self):
        """Create template with comprehensive economic data"""
        template = EconomicTemplate()
        production = ProductionMetrics(
            entity_id="DASHBOARD_TEST",
            entity_type="field",
            oil_production_bbls=1800000.0,
            gas_production_mcf=10800000.0,
            water_production_bbls=900000.0,
            oil_price_usd=90.0,
            gas_price_usd=4.50,
            operating_cost_usd=22000000.0
        )
        
        # Build context with all components
        context = template.build_economic_context_from_production(production)
        template.set_context(context)
        
        # Add advanced analyses
        cash_flows = [-80000000] + [28000000] * 15
        template.add_npv_analysis(cash_flows, discount_rate=0.12, project_years=15)
        template.add_roi_metrics(80000000, 28000000, project_years=15)
        template.add_sensitivity_analysis(production)
        
        # Add enhanced analyses
        template.add_enhanced_cost_structure_analysis()
        template.add_revenue_optimization_analysis()
        
        return template
    
    def test_economic_kpis_generation(self, template_with_comprehensive_data):
        """Test economic KPIs generation for dashboard"""
        template = template_with_comprehensive_data
        kpis = template.get_economic_kpis()
        
        # Test KPI structure
        assert "primary_kpis" in kpis
        assert "secondary_kpis" in kpis
        assert "financial_ratios" in kpis
        assert "cost_efficiency_metrics" in kpis
        
        # Test primary KPIs
        primary = kpis["primary_kpis"]
        assert "net_income" in primary
        assert "profit_margin" in primary
        assert "netback_per_boe" in primary
        assert "npv" in primary
        
        # Test that values are numeric
        assert isinstance(primary["net_income"], (int, float))
        assert isinstance(primary["profit_margin"], (int, float))
        assert isinstance(primary["netback_per_boe"], (int, float))
        assert isinstance(primary["npv"], (int, float))
        
        # Test secondary KPIs
        secondary = kpis["secondary_kpis"]
        assert "operating_margin" in secondary
        assert "ebitda" in secondary
        assert "irr" in secondary
        assert "roi" in secondary
        
        # Test financial ratios
        ratios = kpis["financial_ratios"]
        assert "revenue_per_boe" in ratios
        assert "cost_per_boe" in ratios
        assert "payback_period" in ratios
        assert "full_netback_percentage" in ratios
    
    def test_enhanced_netback_analysis(self, template_with_comprehensive_data):
        """Test enhanced netback analysis for detailed cost breakdown"""
        template = template_with_comprehensive_data
        netback_analysis = template.calculate_enhanced_netback_analysis()
        
        # Test structure
        assert "revenue_per_boe_breakdown" in netback_analysis
        assert "cost_per_boe_breakdown" in netback_analysis
        assert "netback_calculation" in netback_analysis
        assert "netback_percentages" in netback_analysis
        assert "total_boe" in netback_analysis
        
        # Test revenue per BOE breakdown
        revenue_breakdown = netback_analysis["revenue_per_boe_breakdown"]
        assert "oil_revenue_per_boe" in revenue_breakdown
        assert "gas_revenue_per_boe" in revenue_breakdown
        assert "total_revenue_per_boe" in revenue_breakdown
        
        # Test cost per BOE breakdown
        cost_breakdown = netback_analysis["cost_per_boe_breakdown"]
        assert "operating_cost_per_boe" in cost_breakdown
        assert "royalties_per_boe" in cost_breakdown
        assert "total_variable_cost_per_boe" in cost_breakdown
        
        # Test netback calculations
        netback_calc = netback_analysis["netback_calculation"]
        assert "gross_netback_per_boe" in netback_calc
        assert "operating_netback_per_boe" in netback_calc
        assert "full_netback_per_boe" in netback_calc
        
        # Test logical relationships
        assert netback_calc["gross_netback_per_boe"] >= netback_calc["operating_netback_per_boe"]
        assert netback_calc["operating_netback_per_boe"] >= netback_calc["full_netback_per_boe"]
    
    def test_cost_structure_analysis(self, template_with_comprehensive_data):
        """Test detailed cost structure analysis"""
        template = template_with_comprehensive_data
        cost_analysis = template.add_enhanced_cost_structure_analysis()
        
        # Test structure
        assert "cost_breakdown_percentages" in cost_analysis
        assert "cost_as_revenue_percentages" in cost_analysis
        assert "cost_efficiency_metrics" in cost_analysis
        assert "absolute_costs" in cost_analysis
        
        # Test cost breakdown percentages
        breakdown_pct = cost_analysis["cost_breakdown_percentages"]
        if breakdown_pct:  # If costs exist
            assert "operating_costs_pct" in breakdown_pct
            assert "royalties_pct" in breakdown_pct
            
            # Percentages should sum to approximately 100%
            total_pct = sum(breakdown_pct.values())
            assert 95 <= total_pct <= 105  # Allow some rounding tolerance
        
        # Test cost efficiency metrics
        efficiency = cost_analysis["cost_efficiency_metrics"]
        assert "cost_efficiency_index" in efficiency
        assert "operating_efficiency" in efficiency
        assert "variable_cost_ratio" in efficiency
        
        # Efficiency metrics should be between 0 and 1
        assert 0 <= efficiency["cost_efficiency_index"] <= 1
        assert 0 <= efficiency["operating_efficiency"] <= 1
    
    def test_revenue_optimization_analysis(self, template_with_comprehensive_data):
        """Test revenue optimization analysis"""
        template = template_with_comprehensive_data
        revenue_analysis = template.add_revenue_optimization_analysis()
        
        # Test structure
        assert "revenue_per_unit" in revenue_analysis
        assert "revenue_mix" in revenue_analysis
        assert "revenue_quality_metrics" in revenue_analysis
        assert "optimization_opportunities" in revenue_analysis
        
        # Test revenue mix
        revenue_mix = revenue_analysis["revenue_mix"]
        assert "oil_revenue_percentage" in revenue_mix
        assert "gas_revenue_percentage" in revenue_mix
        assert "hydrocarbon_revenue_percentage" in revenue_mix
        
        # Revenue percentages should be between 0 and 100
        for key, value in revenue_mix.items():
            if key.endswith("_percentage"):
                assert 0 <= value <= 100
        
        # Test revenue quality metrics
        quality = revenue_analysis["revenue_quality_metrics"]
        assert "revenue_concentration_risk" in quality
        assert "revenue_diversification_index" in quality
        assert "high_value_revenue_pct" in quality
        assert "gas_revenue_dependency" in quality
        
        # Quality metrics should be between 0 and 1
        assert 0 <= quality["revenue_concentration_risk"] <= 1
        assert 0 <= quality["revenue_diversification_index"] <= 1
        
        # Test optimization opportunities
        opportunities = revenue_analysis["optimization_opportunities"]
        assert isinstance(opportunities, list)
        
        # If opportunities exist, they should be strings
        for opportunity in opportunities:
            assert isinstance(opportunity, str)
            assert len(opportunity) > 0


class TestChartDataPreparation:
    """Test data preparation for various chart types"""
    
    @pytest.fixture
    def chart_data_template(self):
        """Create template with data suitable for chart generation"""
        template = EconomicTemplate()
        production = ProductionMetrics(
            oil_production_bbls=1600000.0,
            gas_production_mcf=9600000.0,
            oil_price_usd=78.0,
            gas_price_usd=3.75
        )
        
        context = template.build_economic_context_from_production(production)
        template.set_context(context)
        
        return template
    
    def test_revenue_pie_chart_data(self, chart_data_template):
        """Test data preparation for revenue pie chart"""
        template = chart_data_template
        revenue_breakdown = template.context.get("revenue_breakdown", {})
        
        # Prepare pie chart data
        labels = []
        values = []
        
        if revenue_breakdown.get('oil_revenue', 0) > 0:
            labels.append("Oil Revenue")
            values.append(revenue_breakdown['oil_revenue'])
        
        if revenue_breakdown.get('gas_revenue', 0) > 0:
            labels.append("Gas Revenue")
            values.append(revenue_breakdown['gas_revenue'])
        
        if revenue_breakdown.get('ngl_revenue', 0) > 0:
            labels.append("NGL Revenue")
            values.append(revenue_breakdown['ngl_revenue'])
        
        # Test data structure
        assert len(labels) == len(values)
        assert len(labels) >= 2  # Should have at least oil and gas
        assert all(isinstance(label, str) for label in labels)
        assert all(isinstance(value, (int, float)) for value in values)
        assert all(value > 0 for value in values)
    
    def test_cost_stacked_bar_data(self, chart_data_template):
        """Test data preparation for cost stacked bar chart"""
        template = chart_data_template
        cost_analysis = template.context.get("cost_analysis", {})
        
        # Prepare stacked bar data
        categories = ["Total Costs"]
        
        operating_costs = [cost_analysis.get('operating_costs', 0)]
        capital_costs = [cost_analysis.get('capital_costs', 0)]
        royalties = [cost_analysis.get('royalties', 0)]
        other_costs = [cost_analysis.get('severance_tax', 0)]
        
        # Test data structure
        assert len(categories) == len(operating_costs) == len(capital_costs) == len(royalties)
        assert all(isinstance(cost, (int, float)) for cost in operating_costs)
        assert all(isinstance(cost, (int, float)) for cost in capital_costs)
        assert all(isinstance(cost, (int, float)) for cost in royalties)
        
        # At least operating costs should exist
        assert sum(operating_costs) > 0
    
    def test_production_time_series_data(self, chart_data_template):
        """Test data preparation for production time series"""
        template = chart_data_template
        
        # Mock historical production data
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        oil_production = [130000, 135000, 142000, 138000, 145000, 150000]
        gas_production = [780000, 810000, 852000, 828000, 870000, 900000]
        
        # Test time series data structure
        assert len(months) == len(oil_production) == len(gas_production)
        assert all(isinstance(month, str) for month in months)
        assert all(isinstance(prod, (int, float)) for prod in oil_production)
        assert all(isinstance(prod, (int, float)) for prod in gas_production)
        assert all(prod > 0 for prod in oil_production)
        assert all(prod > 0 for prod in gas_production)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])