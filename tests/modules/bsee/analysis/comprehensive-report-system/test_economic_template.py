"""
Tests for Economic Template financial metrics and NPV calculations
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import (
    CostStructure,
    PriceDeck,
)
from worldenergydata.bsee.reports.comprehensive.models import (
    EconomicMetrics,
    ProductionMetrics,
)
from worldenergydata.bsee.reports.comprehensive.templates.economic_template import (
    CostAnalysis,
    EconomicAnalysis,
    EconomicForecast,
    EconomicTemplate,
    NPVAnalysis,
    ProfitabilityMetrics,
    RevenueBreakdown,
    ROIMetrics,
    SensitivityAnalysis,
    WaterfallComponent,
)


class TestEconomicTemplate:
    """Test EconomicTemplate initialization and basic functionality"""

    @pytest.fixture
    def economic_template(self):
        """Create EconomicTemplate instance for testing"""
        return EconomicTemplate(template_name="economic_report_test", version="1.0.0")

    @pytest.fixture
    def sample_production_metrics(self):
        """Create sample production metrics for testing"""
        return ProductionMetrics(
            entity_id="TEST_FIELD_001",
            entity_type="field",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            oil_production_bbls=1000000.0,
            gas_production_mcf=6000000.0,
            water_production_bbls=500000.0,
            oil_price_usd=75.0,
            gas_price_usd=3.50,
            operating_cost_usd=12000000.0,
            days_in_period=365,
            active_well_count=25,
        )

    @pytest.fixture
    def sample_economic_metrics(self):
        """Create sample economic metrics for testing"""
        return EconomicMetrics(
            entity_id="TEST_FIELD_001",
            entity_type="field",
            revenue=96000000.0,  # Oil: 75M + Gas: 21M
            operating_costs=12000000.0,
            capital_costs=8000000.0,
            royalties=18000000.0,  # 18.75% of revenue
            production_bbls=1000000.0,
            discount_rate=0.10,
            years_from_start=10,
        )

    def test_economic_template_initialization(self, economic_template):
        """Test EconomicTemplate initialization"""
        assert economic_template.template_name == "economic_report_test"
        assert economic_template.template_type == "economic"
        assert economic_template.version == "1.0.0"
        assert hasattr(economic_template, "economic_sections")
        assert hasattr(economic_template, "price_deck")
        assert hasattr(economic_template, "cost_structure")

    def test_economic_template_context_requirements(self, economic_template):
        """Test economic template context requirements"""
        required_fields = economic_template.context.required_fields

        # Base requirements
        assert "report_date" in required_fields
        assert "entity_id" in required_fields

        # Economic-specific requirements
        assert "production_metrics" in required_fields
        assert "financial_summary" in required_fields
        assert "economic_analysis" in required_fields
        assert "revenue_breakdown" in required_fields
        assert "cost_analysis" in required_fields
        assert "profitability_metrics" in required_fields

    def test_build_economic_context_from_production(
        self, economic_template, sample_production_metrics
    ):
        """Test building economic context from production metrics"""
        context = economic_template.build_economic_context_from_production(
            sample_production_metrics
        )

        assert "production_metrics" in context
        assert "revenue_breakdown" in context
        assert "financial_summary" in context

        # Check production metrics
        prod_metrics = context["production_metrics"]
        assert prod_metrics["oil_bbls"] == 1000000.0
        assert prod_metrics["gas_mcf"] == 6000000.0
        assert prod_metrics["entity_id"] == "TEST_FIELD_001"

        # Check revenue breakdown
        revenue = context["revenue_breakdown"]
        assert revenue["oil_revenue"] == 75000000.0  # 1M bbls * $75
        assert revenue["gas_revenue"] == 21000000.0  # 6M mcf * $3.50
        assert revenue["total_revenue"] == 96000000.0

    def test_build_economic_context_from_economics(
        self, economic_template, sample_economic_metrics
    ):
        """Test building economic context from economic metrics"""
        context = economic_template.build_economic_context_from_economics(
            sample_economic_metrics
        )

        assert "economic_analysis" in context
        assert "cost_analysis" in context
        assert "profitability_metrics" in context

        # Check economic analysis
        econ_analysis = context["economic_analysis"]
        assert econ_analysis["revenue"] == 96000000.0
        assert econ_analysis["operating_costs"] == 12000000.0
        assert econ_analysis["capital_costs"] == 8000000.0
        assert econ_analysis["royalties"] == 18000000.0

        # Check profitability metrics
        profitability = context["profitability_metrics"]
        assert "operating_cost_per_bbl" in profitability
        assert "revenue_per_bbl" in profitability
        assert "netback_per_bbl" in profitability
        assert "profit_margin" in profitability


class TestRevenueBreakdown:
    """Test RevenueBreakdown calculations"""

    @pytest.fixture
    def price_deck(self):
        """Create price deck for testing"""
        return PriceDeck(oil_price=75.0, gas_price=3.50, ngl_price=35.0)

    @pytest.fixture
    def production_data(self):
        """Create production data for testing"""
        return {
            "oil_bbls": 1000000,
            "gas_mcf": 6000000,
            "ngl_bbls": 150000,
            "water_bbls": 500000,
        }

    def test_revenue_breakdown_initialization(self, price_deck, production_data):
        """Test RevenueBreakdown initialization and calculation"""
        breakdown = RevenueBreakdown.from_production(production_data, price_deck)

        assert breakdown.oil_revenue == 75000000.0  # 1M * $75
        assert breakdown.gas_revenue == 21000000.0  # 6M * $3.50
        assert breakdown.ngl_revenue == 5250000.0  # 150k * $35
        assert breakdown.total_revenue == 101250000.0

    def test_revenue_breakdown_percentages(self, price_deck, production_data):
        """Test revenue breakdown percentage calculations"""
        breakdown = RevenueBreakdown.from_production(production_data, price_deck)

        assert breakdown.oil_percentage == pytest.approx(74.07, rel=1e-2)
        assert breakdown.gas_percentage == pytest.approx(20.74, rel=1e-2)
        assert breakdown.ngl_percentage == pytest.approx(5.19, rel=1e-2)

    def test_revenue_breakdown_per_bbl_metrics(self, price_deck, production_data):
        """Test per-barrel revenue metrics"""
        breakdown = RevenueBreakdown.from_production(production_data, price_deck)

        total_boe = (
            production_data["oil_bbls"]
            + (production_data["gas_mcf"] / 6)
            + production_data["ngl_bbls"]
        )
        expected_revenue_per_boe = breakdown.total_revenue / total_boe

        assert breakdown.revenue_per_boe == pytest.approx(
            expected_revenue_per_boe, rel=1e-2
        )


class TestCostAnalysis:
    """Test CostAnalysis calculations"""

    @pytest.fixture
    def cost_structure(self):
        """Create cost structure for testing"""
        return CostStructure(
            operating_cost_per_bbl=12.50, royalty_rate=0.1875, severance_tax_rate=0.05
        )

    @pytest.fixture
    def production_data(self):
        """Create production data for testing"""
        return {"oil_bbls": 1000000, "gas_mcf": 6000000, "ngl_bbls": 150000}

    @pytest.fixture
    def revenue_data(self):
        """Create revenue data for testing"""
        return {"total_revenue": 101250000.0}

    def test_cost_analysis_initialization(
        self, cost_structure, production_data, revenue_data
    ):
        """Test CostAnalysis initialization and calculation"""
        analysis = CostAnalysis.from_production(
            production_data, revenue_data, cost_structure
        )

        # BOE calculation: 1M oil + 1M gas BOE + 150k NGL = 2.15M BOE
        expected_boe = 1000000 + (6000000 / 6) + 150000
        expected_opex = expected_boe * 12.50
        expected_royalties = 101250000.0 * 0.1875
        expected_severance = 101250000.0 * 0.05

        assert analysis.operating_costs == pytest.approx(expected_opex, rel=1e-2)
        assert analysis.royalties == pytest.approx(expected_royalties, rel=1e-2)
        assert analysis.severance_tax == pytest.approx(expected_severance, rel=1e-2)
        assert analysis.total_costs == pytest.approx(
            expected_opex + expected_royalties + expected_severance, rel=1e-2
        )

    def test_cost_analysis_per_boe_metrics(
        self, cost_structure, production_data, revenue_data
    ):
        """Test per-BOE cost metrics"""
        analysis = CostAnalysis.from_production(
            production_data, revenue_data, cost_structure
        )

        total_boe = 1000000 + (6000000 / 6) + 150000
        expected_cost_per_boe = analysis.total_costs / total_boe

        assert analysis.cost_per_boe == pytest.approx(expected_cost_per_boe, rel=1e-2)


class TestProfitabilityMetrics:
    """Test ProfitabilityMetrics calculations"""

    @pytest.fixture
    def revenue_breakdown(self):
        """Create revenue breakdown for testing"""
        return RevenueBreakdown(
            oil_revenue=75000000.0, gas_revenue=21000000.0, ngl_revenue=5250000.0
        )

    @pytest.fixture
    def cost_analysis(self):
        """Create cost analysis for testing"""
        return CostAnalysis(
            operating_costs=26875000.0,  # 2.15M BOE * $12.50
            capital_costs=8000000.0,
            royalties=18984375.0,  # 18.75% of revenue
            severance_tax=5062500.0,  # 5% of revenue
        )

    def test_profitability_metrics_calculation(self, revenue_breakdown, cost_analysis):
        """Test profitability metrics calculation"""
        metrics = ProfitabilityMetrics.from_components(revenue_breakdown, cost_analysis)

        # Net income = Revenue - All costs
        expected_net_income = 101250000.0 - 58921875.0  # Total costs
        expected_profit_margin = expected_net_income / 101250000.0

        assert metrics.net_income == pytest.approx(expected_net_income, rel=1e-2)
        assert metrics.profit_margin == pytest.approx(expected_profit_margin, rel=1e-2)

    def test_profitability_netback_calculation(self, revenue_breakdown, cost_analysis):
        """Test netback per barrel calculation"""
        metrics = ProfitabilityMetrics.from_components(revenue_breakdown, cost_analysis)

        # Assuming 2.15M BOE total
        total_boe = 2150000  # 1M oil + 1M gas BOE + 150k NGL
        expected_netback = metrics.net_income / total_boe

        assert metrics.netback_per_boe == pytest.approx(expected_netback, rel=1e-2)


class TestNPVAnalysis:
    """Test NPV Analysis calculations"""

    @pytest.fixture
    def cash_flows(self):
        """Create sample cash flows for NPV testing"""
        # Year 0: Initial investment, Years 1-10: Operating cash flows
        return [-50000000] + [15000000] * 10

    def test_npv_calculation(self, cash_flows):
        """Test NPV calculation with standard discount rate"""
        npv_analysis = NPVAnalysis(
            cash_flows=cash_flows, discount_rate=0.10, project_years=10
        )

        # NPV should be positive for this profitable project
        assert npv_analysis.npv > 0
        assert npv_analysis.discount_rate == 0.10
        assert npv_analysis.project_years == 10

    def test_npv_sensitivity_analysis(self, cash_flows):
        """Test NPV sensitivity to different discount rates"""
        base_npv = NPVAnalysis(cash_flows, 0.10, 10)
        high_discount_npv = NPVAnalysis(cash_flows, 0.15, 10)
        low_discount_npv = NPVAnalysis(cash_flows, 0.05, 10)

        # NPV should decrease as discount rate increases
        assert low_discount_npv.npv > base_npv.npv > high_discount_npv.npv

    def test_irr_calculation(self, cash_flows):
        """Test Internal Rate of Return calculation"""
        npv_analysis = NPVAnalysis(cash_flows, 0.10, 10)
        irr = npv_analysis.calculate_irr()

        # IRR should be reasonable for profitable project
        assert irr > 0.10  # Should be higher than discount rate for positive NPV
        assert irr < 1.0  # Should be less than 100%


class TestROIMetrics:
    """Test ROI Metrics calculations"""

    def test_roi_calculation(self):
        """Test basic ROI calculation"""
        roi_metrics = ROIMetrics(
            initial_investment=50000000.0,
            annual_net_income=15000000.0,
            project_years=10,
        )

        total_returns = 15000000.0 * 10
        expected_roi = (total_returns - 50000000.0) / 50000000.0

        assert roi_metrics.total_roi == pytest.approx(expected_roi, rel=1e-2)
        assert roi_metrics.annual_roi == pytest.approx(expected_roi / 10, rel=1e-2)

    def test_payback_period_calculation(self):
        """Test payback period calculation"""
        roi_metrics = ROIMetrics(
            initial_investment=45000000.0,
            annual_net_income=15000000.0,
            project_years=10,
        )

        expected_payback = 45000000.0 / 15000000.0  # 3 years
        assert roi_metrics.payback_period_years == pytest.approx(
            expected_payback, rel=1e-2
        )


class TestSensitivityAnalysis:
    """Test Sensitivity Analysis calculations"""

    @pytest.fixture
    def base_case_metrics(self):
        """Create base case production metrics"""
        return ProductionMetrics(
            oil_production_bbls=1000000.0,
            gas_production_mcf=6000000.0,
            oil_price_usd=75.0,
            gas_price_usd=3.50,
            operating_cost_usd=26875000.0,
        )

    def test_price_sensitivity_analysis(self, base_case_metrics):
        """Test oil and gas price sensitivity analysis"""
        sensitivity = SensitivityAnalysis()

        # Test oil price sensitivity
        oil_sensitivity = sensitivity.analyze_oil_price_sensitivity(
            base_case_metrics, price_range=[-20, -10, 0, 10, 20]  # Percentage changes
        )

        assert len(oil_sensitivity) == 5
        assert oil_sensitivity[2]["price_change_pct"] == 0  # Base case
        assert (
            oil_sensitivity[0]["npv"] < oil_sensitivity[4]["npv"]
        )  # Lower price < Higher price

    def test_production_sensitivity_analysis(self, base_case_metrics):
        """Test production volume sensitivity analysis"""
        sensitivity = SensitivityAnalysis()

        # Test production sensitivity
        prod_sensitivity = sensitivity.analyze_production_sensitivity(
            base_case_metrics, volume_range=[-30, -15, 0, 15, 30]  # Percentage changes
        )

        assert len(prod_sensitivity) == 5
        assert prod_sensitivity[2]["volume_change_pct"] == 0  # Base case
        assert (
            prod_sensitivity[0]["npv"] < prod_sensitivity[4]["npv"]
        )  # Lower volume < Higher volume

    def test_cost_sensitivity_analysis(self, base_case_metrics):
        """Test operating cost sensitivity analysis"""
        sensitivity = SensitivityAnalysis()

        # Test cost sensitivity
        cost_sensitivity = sensitivity.analyze_cost_sensitivity(
            base_case_metrics, cost_range=[-25, -10, 0, 10, 25]  # Percentage changes
        )

        assert len(cost_sensitivity) == 5
        assert cost_sensitivity[2]["cost_change_pct"] == 0  # Base case
        # Higher costs should result in lower NPV
        assert cost_sensitivity[0]["npv"] > cost_sensitivity[4]["npv"]


class TestEconomicForecast:
    """Test Economic Forecast calculations"""

    @pytest.fixture
    def historical_production(self):
        """Create historical production data"""
        return [
            {"year": 2020, "oil_bbls": 800000, "gas_mcf": 4800000},
            {"year": 2021, "oil_bbls": 900000, "gas_mcf": 5400000},
            {"year": 2022, "oil_bbls": 1000000, "gas_mcf": 6000000},
            {"year": 2023, "oil_bbls": 1100000, "gas_mcf": 6600000},
        ]

    def test_production_forecast(self, historical_production):
        """Test production forecasting based on historical data"""
        forecast = EconomicForecast()

        future_production = forecast.forecast_production(
            historical_production, forecast_years=5
        )

        assert len(future_production) == 5
        # Production should show reasonable growth or decline trends
        for year_forecast in future_production:
            assert "year" in year_forecast
            assert "oil_bbls" in year_forecast
            assert "gas_mcf" in year_forecast
            assert year_forecast["oil_bbls"] > 0
            assert year_forecast["gas_mcf"] > 0

    def test_revenue_forecast(self, historical_production):
        """Test revenue forecasting with price escalation"""
        forecast = EconomicForecast()
        price_deck = PriceDeck(oil_price=75.0, gas_price=3.50)

        revenue_forecast = forecast.forecast_revenue(
            historical_production,
            price_deck,
            forecast_years=3,
            price_escalation=0.03,  # 3% annual increase
        )

        assert len(revenue_forecast) == 3
        # Revenue should increase with price escalation
        for i in range(1, len(revenue_forecast)):
            assert (
                revenue_forecast[i]["total_revenue"]
                >= revenue_forecast[i - 1]["total_revenue"]
            )


class TestWaterfallComponent:
    """Test Waterfall Chart Component calculations"""

    def test_waterfall_component_creation(self):
        """Test creating waterfall components"""
        component = WaterfallComponent(
            name="Oil Revenue",
            value=75000000.0,
            component_type="revenue",
            category="hydrocarbon",
        )

        assert component.name == "Oil Revenue"
        assert component.value == 75000000.0
        assert component.component_type == "revenue"
        assert component.category == "hydrocarbon"
        assert component.is_positive() == True

        # Test negative component
        cost_component = WaterfallComponent(
            name="Operating Costs",
            value=-26875000.0,
            component_type="cost",
            category="operational",
        )

        assert cost_component.is_positive() == False

    def test_waterfall_chart_data_creation(self):
        """Test creating waterfall chart data structure"""
        components = [
            WaterfallComponent("Oil Revenue", 75000000.0, "revenue", "hydrocarbon"),
            WaterfallComponent("Gas Revenue", 21000000.0, "revenue", "hydrocarbon"),
            WaterfallComponent("Operating Costs", -26875000.0, "cost", "operational"),
            WaterfallComponent("Royalties", -18984375.0, "cost", "government"),
            WaterfallComponent("Net Income", 50140625.0, "profit", "final"),
        ]

        # Verify component structure
        assert len(components) == 5

        # Verify revenue components are positive
        revenue_components = [c for c in components if c.component_type == "revenue"]
        assert all(c.is_positive() for c in revenue_components)

        # Verify cost components are negative
        cost_components = [c for c in components if c.component_type == "cost"]
        assert all(not c.is_positive() for c in cost_components)


class TestProductionEconomicsAnalysis:
    """Test production economics analysis integration"""

    @pytest.fixture
    def economic_template_with_production(self):
        """Create EconomicTemplate with production metrics"""
        template = EconomicTemplate()
        production = ProductionMetrics(
            entity_id="TEST_FIELD_001",
            entity_type="field",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            oil_production_bbls=1200000.0,
            gas_production_mcf=7200000.0,
            water_production_bbls=600000.0,
            oil_price_usd=80.0,
            gas_price_usd=4.00,
            operating_cost_usd=15000000.0,
            days_in_period=365,
            active_well_count=30,
        )

        # Build economic context
        context = template.build_economic_context_from_production(production)
        template.set_context(context)

        return template, production

    def test_production_economics_context_creation(
        self, economic_template_with_production
    ):
        """Test production economics context creation"""
        template, production = economic_template_with_production

        # Verify context has all required sections
        context = template.get_context()

        assert "production_metrics" in context
        assert "revenue_breakdown" in context
        assert "cost_analysis" in context
        assert "profitability_metrics" in context
        assert "goby_revenue_calculations" in context
        assert "goby_14_row_metrics" in context

        # Test production metrics
        prod_metrics = context["production_metrics"]
        assert prod_metrics["oil_bbls"] == 1200000.0
        assert prod_metrics["gas_mcf"] == 7200000.0
        assert prod_metrics["entity_id"] == "TEST_FIELD_001"

    def test_goby_revenue_calculations_integration(
        self, economic_template_with_production
    ):
        """Test integration of go-by report revenue calculations"""
        template, production = economic_template_with_production
        context = template.get_context()

        # Verify go-by calculations are present
        goby_revenue = context["goby_revenue_calculations"]
        goby_costs = context["goby_cost_calculations"]

        assert "oil_revenue" in goby_revenue
        assert "gas_revenue" in goby_revenue
        assert "gross_revenue" in goby_revenue

        assert "operating_cost" in goby_costs
        assert "royalties" in goby_costs
        assert "net_income" in goby_costs

    def test_goby_14_row_structure(self, economic_template_with_production):
        """Test go-by 14-row structure calculation"""
        template, production = economic_template_with_production
        context = template.get_context()

        goby_14_rows = context["goby_14_row_metrics"]

        # Test structure rows
        assert "row_1_oil_production_bbls" in goby_14_rows
        assert "row_2_gas_production_mcf" in goby_14_rows
        assert "row_8_gross_revenue_usd" in goby_14_rows
        assert "row_13_net_income_usd" in goby_14_rows
        assert "row_14_profit_margin_pct" in goby_14_rows

        # Test production values
        assert goby_14_rows["row_1_oil_production_bbls"] == 1200000.0
        assert goby_14_rows["row_2_gas_production_mcf"] == 7200000.0
        assert goby_14_rows["row_4_total_boe"] == 2400000.0  # 1.2M oil + 1.2M gas BOE

        # Test per-BOE calculations
        assert "revenue_per_boe" in goby_14_rows
        assert "netback_per_boe" in goby_14_rows
        assert goby_14_rows["revenue_per_boe"] > 0

    def test_production_economics_kpis(self, economic_template_with_production):
        """Test production economics KPI calculations"""
        template, production = economic_template_with_production

        kpis = template.get_economic_kpis()

        # Test primary KPIs
        primary = kpis["primary_kpis"]
        assert "net_income" in primary
        assert "profit_margin" in primary
        assert "netback_per_boe" in primary

        # Test secondary KPIs
        secondary = kpis["secondary_kpis"]
        assert "operating_margin" in secondary
        assert "ebitda" in secondary

        # Test financial ratios
        ratios = kpis["financial_ratios"]
        assert "revenue_per_boe" in ratios
        assert "cost_per_boe" in ratios

    def test_boe_calculations(self, economic_template_with_production):
        """Test BOE (Barrel of Oil Equivalent) calculations"""
        template, production = economic_template_with_production
        context = template.get_context()

        goby_summary = context["goby_economic_summary"]

        # BOE = Oil + Gas/6
        expected_boe = 1200000 + (7200000 / 6)
        assert goby_summary["boe_production"] == expected_boe

        # Test per-BOE metrics
        assert goby_summary["revenue_per_boe"] > 0
        assert goby_summary["cost_per_boe"] > 0
        assert goby_summary["netback_per_boe"] > 0

    def test_productivity_metrics(self, economic_template_with_production):
        """Test productivity and efficiency metrics"""
        template, production = economic_template_with_production
        context = template.get_context()

        goby_14_rows = context["goby_14_row_metrics"]

        # Test gas-oil ratio
        expected_gor = 7200000 / 1200000  # 6.0
        assert goby_14_rows["gas_oil_ratio"] == expected_gor

        # Test water cut percentage
        expected_water_cut = (600000 / (1200000 + 600000)) * 100  # 33.33%
        assert goby_14_rows["water_cut_pct"] == pytest.approx(33.33, rel=1e-2)


class TestWellLevelEconomicAnalysis:
    """Test individual well-level economic analysis"""

    @pytest.fixture
    def well_production_data(self):
        """Create well-level production data"""
        return {
            "well_001": ProductionMetrics(
                entity_id="WELL_001",
                entity_type="well",
                oil_production_bbls=50000.0,
                gas_production_mcf=300000.0,
                water_production_bbls=25000.0,
                oil_price_usd=75.0,
                gas_price_usd=3.50,
                operating_cost_usd=750000.0,
                active_well_count=1,
            ),
            "well_002": ProductionMetrics(
                entity_id="WELL_002",
                entity_type="well",
                oil_production_bbls=35000.0,
                gas_production_mcf=210000.0,
                water_production_bbls=18000.0,
                oil_price_usd=75.0,
                gas_price_usd=3.50,
                operating_cost_usd=525000.0,
                active_well_count=1,
            ),
        }

    def test_individual_well_analysis(self, well_production_data):
        """Test individual well economic analysis"""
        template = EconomicTemplate()

        for well_id, well_production in well_production_data.items():
            # Build well-specific context
            well_context = template.build_economic_context_from_production(
                well_production
            )

            # Test well metrics
            prod_metrics = well_context["production_metrics"]
            assert prod_metrics["entity_id"] == well_id
            assert prod_metrics["entity_type"] == "well"
            assert prod_metrics["active_well_count"] == 1

            # Test well-level calculations
            goby_metrics = well_context["goby_14_row_metrics"]
            assert (
                goby_metrics["row_1_oil_production_bbls"]
                == well_production.oil_production_bbls
            )
            assert (
                goby_metrics["row_2_gas_production_mcf"]
                == well_production.gas_production_mcf
            )

    def test_well_comparison_analysis(self, well_production_data):
        """Test comparison between wells"""
        template = EconomicTemplate()
        well_analyses = {}

        # Analyze each well
        for well_id, well_production in well_production_data.items():
            context = template.build_economic_context_from_production(well_production)
            well_analyses[well_id] = context

        # Compare well performance
        well1_goby = well_analyses["well_001"]["goby_economic_summary"]
        well2_goby = well_analyses["well_002"]["goby_economic_summary"]

        # Well 001 should have higher absolute revenue (more production)
        assert well1_goby["gross_revenue"] > well2_goby["gross_revenue"]

        # Test per-BOE metrics for comparison
        assert well1_goby["revenue_per_boe"] > 0
        assert well2_goby["revenue_per_boe"] > 0
        assert well1_goby["netback_per_boe"] > 0 or well2_goby["netback_per_boe"] > 0

    def test_well_npv_calculation(self, well_production_data):
        """Test NPV calculation for individual wells"""
        template = EconomicTemplate()

        for well_id, well_production in well_production_data.items():
            # Build context
            context = template.build_economic_context_from_production(well_production)
            template.set_context(context)

            # Add NPV analysis
            annual_net_income = context["goby_economic_summary"]["net_income"]

            # Simulate 10-year cash flows
            cash_flows = [-5000000] + [
                annual_net_income
            ] * 10  # Initial investment + 10 years
            template.add_npv_analysis(cash_flows, discount_rate=0.12, project_years=10)

            # Test NPV results
            npv_analysis = template.context["npv_analysis"]
            assert "npv" in npv_analysis
            assert "irr" in npv_analysis
            assert npv_analysis["project_years"] == 10

    def test_well_roi_metrics(self, well_production_data):
        """Test ROI metrics for individual wells"""
        template = EconomicTemplate()

        for well_id, well_production in well_production_data.items():
            # Build context
            context = template.build_economic_context_from_production(well_production)
            template.set_context(context)

            # Add ROI analysis
            annual_net_income = context["goby_economic_summary"]["net_income"]
            initial_investment = 8000000  # $8M well cost

            template.add_roi_metrics(
                initial_investment, annual_net_income, project_years=15
            )

            # Test ROI results
            roi_metrics = template.context["roi_metrics"]
            assert "total_roi" in roi_metrics
            assert "annual_roi" in roi_metrics
            assert "payback_period_years" in roi_metrics

            # Payback should be reasonable
            if annual_net_income > 0:
                expected_payback = initial_investment / annual_net_income
                assert roi_metrics["payback_period_years"] == pytest.approx(
                    expected_payback, rel=1e-2
                )


class TestFieldLevelEconomicIntegration:
    """Test field-level economic integration with go-by patterns"""

    @pytest.fixture
    def field_metrics_data(self):
        """Create field-level aggregated metrics"""
        return {
            "field_id": "FIELD_JACK_001",
            "field_name": "Jack Field",
            "total_wells": 45,
            "active_wells": 42,
            "total_leases": 8,
            "oil_production_bbls": 2500000,
            "gas_production_mcf": 15000000,
            "water_production_bbls": 1200000,
            "total_boe": 5000000,  # 2.5M oil + 2.5M gas BOE
            "gross_revenue": 225000000,
            "operating_cost": 62500000,
            "royalties": 42187500,
            "severance_tax": 11250000,
            "total_costs": 115937500,
            "net_income": 109062500,
            "avg_oil_per_well": 55555,
            "avg_gas_per_well": 333333,
            "avg_wells_per_lease": 5.625,
        }

    def test_field_economics_integration(self, field_metrics_data):
        """Test integration of field-level economics"""
        template = EconomicTemplate()

        # Integrate field economics
        field_economics = template.integrate_goby_field_economics(field_metrics_data)

        # Test field summary
        field_summary = field_economics["field_summary"]
        assert field_summary["total_wells"] == 45
        assert field_summary["active_wells"] == 42
        assert field_summary["oil_production_bbls"] == 2500000
        assert field_summary["total_boe"] == 5000000

        # Test field economics
        field_econ = field_economics["field_economics"]
        assert field_econ["gross_revenue"] == 225000000
        assert field_econ["net_income"] == 109062500

        # Test field performance metrics
        field_perf = field_economics["field_performance"]
        assert field_perf["avg_oil_per_well"] == 55555
        assert field_perf["avg_revenue_per_well"] == 225000000 / 45

    def test_field_context_integration(self, field_metrics_data):
        """Test field economics context integration"""
        template = EconomicTemplate()

        # Integrate field economics
        template.integrate_goby_field_economics(field_metrics_data)

        # Check context
        assert "field_economics" in template.context
        field_context = template.context["field_economics"]

        # Verify structure
        assert "field_summary" in field_context
        assert "field_economics" in field_context
        assert "field_performance" in field_context

    def test_field_per_well_metrics(self, field_metrics_data):
        """Test field-level per-well metrics"""
        template = EconomicTemplate()
        field_economics = template.integrate_goby_field_economics(field_metrics_data)

        # Test average calculations
        field_perf = field_economics["field_performance"]
        expected_avg_revenue_per_well = (
            field_metrics_data["gross_revenue"] / field_metrics_data["total_wells"]
        )

        assert field_perf["avg_revenue_per_well"] == pytest.approx(
            expected_avg_revenue_per_well, rel=1e-2
        )
        assert field_perf["avg_wells_per_lease"] == pytest.approx(5.625, rel=1e-2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
