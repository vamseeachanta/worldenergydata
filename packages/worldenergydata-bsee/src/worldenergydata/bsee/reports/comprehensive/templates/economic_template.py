"""
Economic Template for comprehensive financial analysis and reporting
Implements NPV calculations, ROI metrics, and revenue/cost analysis

This module has been refactored from a 2,000+ line file into focused modules:
- economic_models.py: Data models (RevenueBreakdown, CostAnalysis, NPVAnalysis, etc.)
- economic_calculations.py: Calculation utilities (netback, cost structure, well economics)
- economic_charts.py: Plotly chart generation (waterfall, dashboard, tornado, time series)
- economic_tables.py: HTML table generation for sensitivity analysis
- economic_goby.py: Go-by report calculations matching Excel formats
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy_financial as npf

from ..hierarchical_aggregator import CostStructure, PriceDeck
from ..models import EconomicMetrics, ProductionMetrics
from .base import BaseReportTemplate
from .economic_calculations import (
    analyze_individual_well_economics,
    calculate_cost_structure_analysis,
    calculate_enhanced_netback_analysis,
    calculate_revenue_optimization_analysis,
    compare_wells_economic_performance,
    get_economic_kpis,
    prepare_tornado_chart_data,
)
from .economic_charts import (
    create_empty_chart,
    generate_economic_dashboard,
    generate_production_economics_time_series,
    generate_sensitivity_tornado_chart,
    generate_waterfall_chart,
)
from .economic_goby import (
    apply_goby_revenue_calculations,
    build_production_context,
    integrate_goby_field_economics,
)

# Import from refactored modules
from .economic_models import (
    CostAnalysis,
    EconomicAnalysis,
    EconomicForecast,
    NPVAnalysis,
    ProfitabilityMetrics,
    RevenueBreakdown,
    ROIMetrics,
    SensitivityAnalysis,
    WaterfallComponent,
)
from .economic_tables import generate_sensitivity_analysis_tables

# Re-export models for backward compatibility
__all__ = [
    "RevenueBreakdown",
    "CostAnalysis",
    "ProfitabilityMetrics",
    "NPVAnalysis",
    "ROIMetrics",
    "EconomicForecast",
    "SensitivityAnalysis",
    "WaterfallComponent",
    "EconomicAnalysis",
    "EconomicTemplate",
]


class EconomicTemplate(BaseReportTemplate):
    """
    Economic Template for comprehensive financial analysis
    Implements NPV calculations, ROI metrics, revenue/cost breakdown, and profitability analysis
    """

    def __init__(
        self,
        template_name: str = "economic_report",
        version: str = "1.0.0",
        template_path: Optional[Path] = None,
        **kwargs,
    ):
        """Initialize EconomicTemplate"""
        super().__init__(
            template_name=template_name,
            template_type="economic",
            version=version,
            template_path=template_path,
            **kwargs,
        )
        self.price_deck = kwargs.get("price_deck", PriceDeck())
        self.cost_structure = kwargs.get("cost_structure", CostStructure())
        self._setup_economic_context_requirements()
        self.economic_sections = {
            "revenue_analysis": True,
            "cost_analysis": True,
            "profitability_metrics": True,
            "npv_analysis": True,
            "roi_metrics": True,
            "sensitivity_analysis": True,
            "economic_forecasts": True,
        }
        self.economic_context = {}

    def _setup_economic_context_requirements(self):
        """Set up economic-specific context requirements"""
        self.context.require_fields(
            [
                "economic_analysis",
                "revenue_breakdown",
                "cost_analysis",
                "profitability_metrics",
                "npv_analysis",
                "roi_metrics",
            ]
        )

    def build_economic_context_from_production(
        self, production: ProductionMetrics
    ) -> Dict[str, Any]:
        """Build economic context from production metrics with go-by report calculations"""
        economic_analysis = EconomicAnalysis.from_production_metrics(
            production,
            self.price_deck,
            self.cost_structure,
            entity_id=production.entity_id,
            entity_type=production.entity_type,
        )
        goby_calcs = apply_goby_revenue_calculations(
            production, self.price_deck, self.cost_structure
        )
        context = {
            "production_metrics": build_production_context(production),
            "revenue_breakdown": {
                "oil_revenue": economic_analysis.revenue_breakdown.oil_revenue,
                "gas_revenue": economic_analysis.revenue_breakdown.gas_revenue,
                "ngl_revenue": economic_analysis.revenue_breakdown.ngl_revenue,
                "total_revenue": economic_analysis.revenue_breakdown.total_revenue,
                "oil_percentage": economic_analysis.revenue_breakdown.oil_percentage,
                "gas_percentage": economic_analysis.revenue_breakdown.gas_percentage,
                "revenue_per_boe": economic_analysis.revenue_breakdown.revenue_per_boe,
            },
            "cost_analysis": {
                "operating_costs": economic_analysis.cost_analysis.operating_costs,
                "capital_costs": economic_analysis.cost_analysis.capital_costs,
                "royalties": economic_analysis.cost_analysis.royalties,
                "severance_tax": economic_analysis.cost_analysis.severance_tax,
                "total_costs": economic_analysis.cost_analysis.total_costs,
                "cost_per_boe": economic_analysis.cost_analysis.cost_per_boe,
            },
            "profitability_metrics": {
                "gross_revenue": economic_analysis.profitability_metrics.gross_revenue,
                "net_income": economic_analysis.profitability_metrics.net_income,
                "profit_margin": economic_analysis.profitability_metrics.profit_margin,
                "operating_margin": economic_analysis.profitability_metrics.operating_margin,
                "netback_per_boe": economic_analysis.profitability_metrics.netback_per_boe,
                "ebitda": economic_analysis.profitability_metrics.ebitda,
            },
            "financial_summary": {
                "total_revenue": economic_analysis.revenue_breakdown.total_revenue,
                "net_revenue": economic_analysis.profitability_metrics.net_revenue,
                "operating_margin": economic_analysis.profitability_metrics.operating_margin,
                "profit_margin": economic_analysis.profitability_metrics.profit_margin,
            },
            "economic_analysis": economic_analysis,
        }
        context.update(goby_calcs)
        return context

    def integrate_goby_field_economics(
        self, field_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Integrate field-level economics following go-by report patterns"""
        field_economics = integrate_goby_field_economics(field_metrics)
        self.context["field_economics"] = field_economics
        return field_economics

    def build_economic_context_from_economics(
        self, economics: EconomicMetrics
    ) -> Dict[str, Any]:
        """Build economic context from EconomicMetrics model"""
        net_income = economics.calculate_net_income()
        return {
            "economic_analysis": {
                "revenue": economics.revenue,
                "operating_costs": economics.operating_costs,
                "capital_costs": economics.capital_costs,
                "royalties": economics.royalties,
                "net_income": net_income,
                "production_bbls": economics.production_bbls,
                "entity_id": economics.entity_id,
                "entity_type": economics.entity_type,
            },
            "cost_analysis": {
                "operating_costs": economics.operating_costs,
                "capital_costs": economics.capital_costs,
                "royalties": economics.royalties,
                "total_costs": economics.operating_costs
                + economics.capital_costs
                + economics.royalties,
                "operating_cost_per_bbl": economics.operating_cost_per_bbl,
            },
            "profitability_metrics": {
                "operating_cost_per_bbl": economics.operating_cost_per_bbl,
                "revenue_per_bbl": economics.revenue_per_bbl,
                "netback_per_bbl": economics.netback_per_bbl,
                "profit_margin": economics.profit_margin,
                "net_income": net_income,
            },
            "npv_analysis": {
                "npv": economics.calculate_npv(),
                "discount_rate": economics.discount_rate,
                "years_projection": economics.years_from_start,
            },
            "financial_summary": {
                "total_revenue": economics.revenue,
                "net_income": net_income,
                "profit_margin": economics.profit_margin,
                "npv": economics.calculate_npv(),
            },
        }

    def add_npv_analysis(
        self,
        cash_flows: List[float],
        discount_rate: float = 0.10,
        project_years: int = 10,
    ):
        """Add NPV analysis to economic template"""
        npv_analysis = NPVAnalysis(
            cash_flows=cash_flows,
            discount_rate=discount_rate,
            project_years=project_years,
        )
        sensitivity_rates = [0.05, 0.08, 0.10, 0.12, 0.15]
        self.context["npv_analysis"] = {
            "npv": npv_analysis.npv,
            "irr": npv_analysis.calculate_irr(),
            "present_value_inflows": npv_analysis.present_value_inflows,
            "present_value_outflows": npv_analysis.present_value_outflows,
            "discount_rate": discount_rate,
            "project_years": project_years,
            "sensitivity_analysis": npv_analysis.sensitivity_analysis(
                sensitivity_rates
            ),
            "cash_flows": cash_flows,
        }

    def add_roi_metrics(
        self,
        initial_investment: float,
        annual_net_income: float,
        project_years: int = 10,
    ):
        """Add ROI metrics to economic template"""
        roi = ROIMetrics(
            initial_investment=initial_investment,
            annual_net_income=annual_net_income,
            project_years=project_years,
        )
        self.context["roi_metrics"] = {
            "total_roi": roi.total_roi,
            "annual_roi": roi.annual_roi,
            "payback_period_years": roi.payback_period_years,
            "initial_investment": initial_investment,
            "annual_net_income": annual_net_income,
            "project_years": project_years,
        }

    def add_sensitivity_analysis(self, production_metrics: ProductionMetrics):
        """Add comprehensive sensitivity analysis"""
        sensitivity = SensitivityAnalysis()
        oil_sens = sensitivity.analyze_oil_price_sensitivity(
            production_metrics, [-30, -20, -10, 0, 10, 20, 30]
        )
        prod_sens = sensitivity.analyze_production_sensitivity(
            production_metrics, [-50, -30, -15, 0, 15, 30, 50]
        )
        cost_sens = sensitivity.analyze_cost_sensitivity(
            production_metrics, [-25, -15, -5, 0, 10, 25, 50]
        )
        self.context["sensitivity_analysis"] = {
            "oil_price_sensitivity": oil_sens,
            "production_sensitivity": prod_sens,
            "cost_sensitivity": cost_sens,
            "tornado_chart_data": prepare_tornado_chart_data(
                oil_sens, prod_sens, cost_sens
            ),
        }

    def add_economic_forecast(
        self,
        historical_production: List[Dict[str, Any]],
        forecast_years: int = 5,
        decline_rate: float = 0.05,
        price_escalation: float = 0.02,
    ):
        """Add economic forecasting to template"""
        forecast = EconomicForecast()
        prod_forecast = forecast.forecast_production(
            historical_production, forecast_years, decline_rate
        )
        rev_forecast = forecast.forecast_revenue(
            prod_forecast, self.price_deck, forecast_years, price_escalation
        )
        cash_flows = [yf["total_revenue"] * 0.6 for yf in rev_forecast]  # 60% margin
        forecast_npv = npf.npv(0.10, [0] + cash_flows)
        self.context["economic_forecast"] = {
            "production_forecast": prod_forecast,
            "revenue_forecast": rev_forecast,
            "forecast_years": forecast_years,
            "decline_rate": decline_rate,
            "price_escalation": price_escalation,
            "forecast_npv": forecast_npv,
            "cash_flows": cash_flows,
        }

    def generate_waterfall_data(self) -> List[WaterfallComponent]:
        """Generate waterfall chart data from economic context"""
        components = []
        revenue = self.context.get("revenue_breakdown", {})
        if revenue:
            components.extend(
                [
                    WaterfallComponent(
                        "Oil Revenue",
                        revenue.get("oil_revenue", 0),
                        "revenue",
                        "hydrocarbon",
                    ),
                    WaterfallComponent(
                        "Gas Revenue",
                        revenue.get("gas_revenue", 0),
                        "revenue",
                        "hydrocarbon",
                    ),
                    WaterfallComponent(
                        "NGL Revenue",
                        revenue.get("ngl_revenue", 0),
                        "revenue",
                        "hydrocarbon",
                    ),
                ]
            )
        costs = self.context.get("cost_analysis", {})
        if costs:
            components.extend(
                [
                    WaterfallComponent(
                        "Operating Costs",
                        -costs.get("operating_costs", 0),
                        "cost",
                        "operational",
                    ),
                    WaterfallComponent(
                        "Royalties", -costs.get("royalties", 0), "cost", "government"
                    ),
                    WaterfallComponent(
                        "Severance Tax",
                        -costs.get("severance_tax", 0),
                        "cost",
                        "government",
                    ),
                    WaterfallComponent(
                        "Capital Costs",
                        -costs.get("capital_costs", 0),
                        "cost",
                        "capital",
                    ),
                ]
            )
        profitability = self.context.get("profitability_metrics", {})
        if profitability:
            components.append(
                WaterfallComponent(
                    "Net Income", profitability.get("net_income", 0), "profit", "final"
                )
            )
        return components

    def calculate_enhanced_netback_analysis(self) -> Dict[str, Any]:
        """Calculate enhanced netback analysis with detailed cost breakdown"""
        return calculate_enhanced_netback_analysis(self.context)

    def add_enhanced_cost_structure_analysis(self) -> Dict[str, Any]:
        """Add detailed cost structure analysis"""
        analysis = calculate_cost_structure_analysis(self.context)
        self.context["cost_structure_analysis"] = analysis
        return analysis

    def add_revenue_optimization_analysis(self) -> Dict[str, Any]:
        """Add revenue optimization analysis"""
        analysis = calculate_revenue_optimization_analysis(self.context)
        self.context["revenue_optimization_analysis"] = analysis
        return analysis

    def get_economic_kpis(self) -> Dict[str, Any]:
        """Get key economic performance indicators"""
        return get_economic_kpis(
            self.context, self.calculate_enhanced_netback_analysis()
        )

    def analyze_individual_well_economics(
        self,
        well_id: str,
        well_production: ProductionMetrics,
        initial_well_cost: float = 8000000.0,
        well_life_years: int = 20,
        decline_rate: float = 0.08,
    ) -> Dict[str, Any]:
        """Analyze individual well economics with NPV and ROI metrics"""
        well_context = self.build_economic_context_from_production(well_production)
        return analyze_individual_well_economics(
            well_id=well_id,
            well_context=well_context,
            initial_well_cost=initial_well_cost,
            well_life_years=well_life_years,
            decline_rate=decline_rate,
        )

    def compare_wells_economic_performance(
        self, wells_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare economic performance across multiple wells"""
        return compare_wells_economic_performance(wells_data)

    def generate_waterfall_chart(
        self, title: str = "Economic Waterfall Analysis"
    ) -> str:
        """Generate waterfall chart showing revenue to net income flow"""
        return generate_waterfall_chart(self.generate_waterfall_data(), title)

    def generate_economic_dashboard(
        self, title: str = "Economic Performance Dashboard"
    ) -> str:
        """Generate comprehensive economic dashboard with multiple charts"""
        return generate_economic_dashboard(
            self.context, self.calculate_enhanced_netback_analysis(), title
        )

    def generate_sensitivity_tornado_chart(
        self, title: str = "NPV Sensitivity Analysis"
    ) -> str:
        """Generate tornado chart for sensitivity analysis"""
        tornado_data = self.context.get("sensitivity_analysis", {}).get(
            "tornado_chart_data", []
        )
        return generate_sensitivity_tornado_chart(tornado_data, title)

    def generate_production_economics_time_series(
        self, title: str = "Production Economics Over Time"
    ) -> str:
        """Generate time series chart showing production and economics trends"""
        return generate_production_economics_time_series(
            self.context, self.calculate_enhanced_netback_analysis(), title
        )

    def _create_empty_chart(self, message: str = "No data available") -> str:
        """Create empty chart with message"""
        return create_empty_chart(message)

    def generate_sensitivity_analysis_tables(self) -> Dict[str, str]:
        """Generate HTML tables for sensitivity analysis showing NPV and IRR variations"""
        return generate_sensitivity_analysis_tables(self.economic_context)
