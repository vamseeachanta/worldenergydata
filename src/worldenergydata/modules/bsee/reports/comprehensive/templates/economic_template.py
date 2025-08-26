"""
Economic Template for comprehensive financial analysis and reporting
Implements NPV calculations, ROI metrics, and revenue/cost analysis
"""

import numpy as np
import numpy_financial as npf
from datetime import date, datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from decimal import Decimal
import pandas as pd

from .base import BaseReportTemplate, TemplateContext
from ..models import ProductionMetrics, EconomicMetrics
from ..hierarchical_aggregator import PriceDeck, CostStructure


@dataclass
class RevenueBreakdown:
    """Revenue breakdown analysis for oil, gas, and NGL"""
    oil_revenue: float = 0.0
    gas_revenue: float = 0.0
    ngl_revenue: float = 0.0
    water_revenue: float = 0.0  # Sometimes water has value for disposal
    other_revenue: float = 0.0
    
    @property
    def total_revenue(self) -> float:
        """Calculate total revenue"""
        return (self.oil_revenue + self.gas_revenue + self.ngl_revenue + 
                self.water_revenue + self.other_revenue)
    
    @property
    def oil_percentage(self) -> float:
        """Calculate oil revenue percentage"""
        if self.total_revenue > 0:
            return (self.oil_revenue / self.total_revenue) * 100
        return 0.0
    
    @property
    def gas_percentage(self) -> float:
        """Calculate gas revenue percentage"""
        if self.total_revenue > 0:
            return (self.gas_revenue / self.total_revenue) * 100
        return 0.0
    
    @property
    def ngl_percentage(self) -> float:
        """Calculate NGL revenue percentage"""
        if self.total_revenue > 0:
            return (self.ngl_revenue / self.total_revenue) * 100
        return 0.0
    
    @property
    def revenue_per_boe(self) -> float:
        """Calculate revenue per BOE (requires BOE to be set externally)"""
        # This will be calculated when we have production volumes
        return getattr(self, '_revenue_per_boe', 0.0)
    
    def set_production_volumes(self, oil_bbls: float, gas_mcf: float, ngl_bbls: float = 0.0):
        """Set production volumes to calculate per-BOE metrics"""
        total_boe = oil_bbls + (gas_mcf / 6) + ngl_bbls
        if total_boe > 0:
            self._revenue_per_boe = self.total_revenue / total_boe
        else:
            self._revenue_per_boe = 0.0
    
    @classmethod
    def from_production(cls, production_data: Dict[str, float], 
                       price_deck: PriceDeck) -> 'RevenueBreakdown':
        """Create revenue breakdown from production data and price deck"""
        oil_revenue = production_data.get('oil_bbls', 0) * price_deck.oil_price
        gas_revenue = production_data.get('gas_mcf', 0) * price_deck.gas_price
        ngl_revenue = production_data.get('ngl_bbls', 0) * price_deck.ngl_price
        
        breakdown = cls(
            oil_revenue=oil_revenue,
            gas_revenue=gas_revenue,
            ngl_revenue=ngl_revenue
        )
        
        # Set production volumes for per-BOE calculations
        breakdown.set_production_volumes(
            production_data.get('oil_bbls', 0),
            production_data.get('gas_mcf', 0),
            production_data.get('ngl_bbls', 0)
        )
        
        return breakdown


@dataclass
class CostAnalysis:
    """Cost analysis including OPEX, CAPEX, and taxes"""
    operating_costs: float = 0.0
    capital_costs: float = 0.0
    royalties: float = 0.0
    severance_tax: float = 0.0
    production_tax: float = 0.0
    transportation_costs: float = 0.0
    processing_costs: float = 0.0
    other_costs: float = 0.0
    
    @property
    def total_costs(self) -> float:
        """Calculate total costs"""
        return (self.operating_costs + self.capital_costs + self.royalties + 
                self.severance_tax + self.production_tax + self.transportation_costs +
                self.processing_costs + self.other_costs)
    
    @property
    def variable_costs(self) -> float:
        """Calculate variable costs (exclude CAPEX)"""
        return (self.operating_costs + self.royalties + self.severance_tax +
                self.production_tax + self.transportation_costs + self.processing_costs)
    
    @property
    def cost_per_boe(self) -> float:
        """Calculate cost per BOE (requires BOE to be set externally)"""
        return getattr(self, '_cost_per_boe', 0.0)
    
    def set_production_volumes(self, oil_bbls: float, gas_mcf: float, ngl_bbls: float = 0.0):
        """Set production volumes to calculate per-BOE metrics"""
        total_boe = oil_bbls + (gas_mcf / 6) + ngl_bbls
        if total_boe > 0:
            self._cost_per_boe = self.total_costs / total_boe
        else:
            self._cost_per_boe = 0.0
    
    @classmethod
    def from_production(cls, production_data: Dict[str, float], 
                       revenue_data: Dict[str, float],
                       cost_structure: CostStructure) -> 'CostAnalysis':
        """Create cost analysis from production data"""
        # Calculate BOE for operating costs
        oil_bbls = production_data.get('oil_bbls', 0)
        gas_mcf = production_data.get('gas_mcf', 0)
        ngl_bbls = production_data.get('ngl_bbls', 0)
        total_boe = oil_bbls + (gas_mcf / 6) + ngl_bbls
        
        # Calculate costs
        operating_costs = total_boe * cost_structure.operating_cost_per_bbl
        total_revenue = revenue_data.get('total_revenue', 0)
        royalties = total_revenue * cost_structure.royalty_rate
        severance_tax = total_revenue * cost_structure.severance_tax_rate
        
        analysis = cls(
            operating_costs=operating_costs,
            royalties=royalties,
            severance_tax=severance_tax
        )
        
        # Set production volumes for per-BOE calculations
        analysis.set_production_volumes(oil_bbls, gas_mcf, ngl_bbls)
        
        return analysis


@dataclass
class ProfitabilityMetrics:
    """Profitability metrics and ratios"""
    gross_revenue: float = 0.0
    net_revenue: float = 0.0
    net_income: float = 0.0
    operating_margin: float = 0.0
    profit_margin: float = 0.0
    netback_per_boe: float = 0.0
    ebitda: float = 0.0
    
    @classmethod
    def from_components(cls, revenue_breakdown: RevenueBreakdown,
                       cost_analysis: CostAnalysis) -> 'ProfitabilityMetrics':
        """Create profitability metrics from revenue and cost components"""
        gross_revenue = revenue_breakdown.total_revenue
        net_income = gross_revenue - cost_analysis.total_costs
        
        # Calculate margins
        profit_margin = (net_income / gross_revenue * 100) if gross_revenue > 0 else 0
        operating_margin = ((gross_revenue - cost_analysis.variable_costs) / gross_revenue * 100) if gross_revenue > 0 else 0
        
        # Calculate netback per BOE
        netback_per_boe = revenue_breakdown.revenue_per_boe - cost_analysis.cost_per_boe
        
        # EBITDA (earnings before interest, taxes, depreciation, amortization)
        ebitda = gross_revenue - cost_analysis.operating_costs
        
        return cls(
            gross_revenue=gross_revenue,
            net_revenue=gross_revenue - cost_analysis.variable_costs,
            net_income=net_income,
            operating_margin=operating_margin,
            profit_margin=profit_margin,
            netback_per_boe=netback_per_boe,
            ebitda=ebitda
        )


@dataclass
class NPVAnalysis:
    """NPV analysis for project economics"""
    cash_flows: List[float] = field(default_factory=list)
    discount_rate: float = 0.10
    project_years: int = 10
    
    @property
    def npv(self) -> float:
        """Calculate Net Present Value"""
        if not self.cash_flows:
            return 0.0
        return npf.npv(self.discount_rate, self.cash_flows)
    
    @property
    def present_value_inflows(self) -> float:
        """Calculate present value of positive cash flows"""
        if not self.cash_flows:
            return 0.0
        positive_flows = [max(0, cf) for cf in self.cash_flows]
        return npf.npv(self.discount_rate, positive_flows)
    
    @property
    def present_value_outflows(self) -> float:
        """Calculate present value of negative cash flows"""
        if not self.cash_flows:
            return 0.0
        negative_flows = [min(0, cf) for cf in self.cash_flows]
        return abs(npf.npv(self.discount_rate, negative_flows))
    
    def calculate_irr(self) -> float:
        """Calculate Internal Rate of Return"""
        if not self.cash_flows or len(self.cash_flows) < 2:
            return 0.0
        try:
            return npf.irr(self.cash_flows)
        except:
            return 0.0  # IRR calculation failed
    
    def sensitivity_analysis(self, discount_rates: List[float]) -> Dict[float, float]:
        """Perform NPV sensitivity analysis across different discount rates"""
        sensitivity = {}
        for rate in discount_rates:
            if self.cash_flows:
                sensitivity[rate] = npf.npv(rate, self.cash_flows)
            else:
                sensitivity[rate] = 0.0
        return sensitivity


@dataclass
class ROIMetrics:
    """Return on Investment metrics"""
    initial_investment: float = 0.0
    annual_net_income: float = 0.0
    project_years: int = 10
    
    @property
    def total_roi(self) -> float:
        """Calculate total ROI over project life"""
        if self.initial_investment <= 0:
            return 0.0
        total_returns = self.annual_net_income * self.project_years
        return (total_returns - self.initial_investment) / self.initial_investment
    
    @property
    def annual_roi(self) -> float:
        """Calculate annualized ROI"""
        return self.total_roi / self.project_years if self.project_years > 0 else 0.0
    
    @property
    def payback_period_years(self) -> float:
        """Calculate simple payback period in years"""
        if self.annual_net_income <= 0:
            return float('inf')
        return self.initial_investment / self.annual_net_income


@dataclass
class EconomicForecast:
    """Economic forecasting and projections"""
    
    def forecast_production(self, historical_data: List[Dict[str, Any]], 
                          forecast_years: int = 5,
                          decline_rate: float = 0.05) -> List[Dict[str, Any]]:
        """Forecast future production based on historical trends"""
        if not historical_data:
            return []
        
        # Get latest year data
        latest = historical_data[-1]
        forecasts = []
        
        for year in range(1, forecast_years + 1):
            forecast_year = latest['year'] + year
            
            # Apply decline rate
            oil_forecast = latest['oil_bbls'] * ((1 - decline_rate) ** year)
            gas_forecast = latest['gas_mcf'] * ((1 - decline_rate) ** year)
            
            forecasts.append({
                'year': forecast_year,
                'oil_bbls': max(0, oil_forecast),
                'gas_mcf': max(0, gas_forecast)
            })
        
        return forecasts
    
    def forecast_revenue(self, production_forecast: List[Dict[str, Any]],
                        price_deck: PriceDeck, forecast_years: int = 5,
                        price_escalation: float = 0.02) -> List[Dict[str, Any]]:
        """Forecast revenue with price escalation"""
        revenue_forecasts = []
        
        for i, prod_forecast in enumerate(production_forecast):
            # Apply price escalation
            escalated_oil_price = price_deck.oil_price * ((1 + price_escalation) ** i)
            escalated_gas_price = price_deck.gas_price * ((1 + price_escalation) ** i)
            
            oil_revenue = prod_forecast['oil_bbls'] * escalated_oil_price
            gas_revenue = prod_forecast['gas_mcf'] * escalated_gas_price
            total_revenue = oil_revenue + gas_revenue
            
            revenue_forecasts.append({
                'year': prod_forecast['year'],
                'oil_revenue': oil_revenue,
                'gas_revenue': gas_revenue,
                'total_revenue': total_revenue,
                'oil_price': escalated_oil_price,
                'gas_price': escalated_gas_price
            })
        
        return revenue_forecasts


@dataclass  
class SensitivityAnalysis:
    """Sensitivity analysis for key economic variables"""
    
    def analyze_oil_price_sensitivity(self, base_metrics: ProductionMetrics,
                                    price_range: List[float]) -> List[Dict[str, Any]]:
        """Analyze sensitivity to oil price changes"""
        sensitivity_results = []
        base_oil_price = base_metrics.oil_price_usd
        
        for price_change_pct in price_range:
            new_oil_price = base_oil_price * (1 + price_change_pct / 100)
            
            # Calculate new revenue
            oil_revenue = base_metrics.oil_production_bbls * new_oil_price
            gas_revenue = base_metrics.gas_production_mcf * base_metrics.gas_price_usd
            total_revenue = oil_revenue + gas_revenue
            
            # Estimate NPV impact (simplified)
            net_income = total_revenue - base_metrics.operating_cost_usd
            npv_estimate = net_income * 8  # Simple 8x multiplier for 10-year NPV estimate
            
            sensitivity_results.append({
                'price_change_pct': price_change_pct,
                'new_oil_price': new_oil_price,
                'total_revenue': total_revenue,
                'net_income': net_income,
                'npv': npv_estimate
            })
        
        return sensitivity_results
    
    def analyze_production_sensitivity(self, base_metrics: ProductionMetrics,
                                     volume_range: List[float]) -> List[Dict[str, Any]]:
        """Analyze sensitivity to production volume changes"""
        sensitivity_results = []
        
        for volume_change_pct in volume_range:
            new_oil_production = base_metrics.oil_production_bbls * (1 + volume_change_pct / 100)
            new_gas_production = base_metrics.gas_production_mcf * (1 + volume_change_pct / 100)
            
            # Calculate new revenue and costs
            oil_revenue = new_oil_production * base_metrics.oil_price_usd
            gas_revenue = new_gas_production * base_metrics.gas_price_usd
            total_revenue = oil_revenue + gas_revenue
            
            # Costs scale with production
            variable_costs = base_metrics.operating_cost_usd * (1 + volume_change_pct / 100)
            net_income = total_revenue - variable_costs
            npv_estimate = net_income * 8
            
            sensitivity_results.append({
                'volume_change_pct': volume_change_pct,
                'new_oil_production': new_oil_production,
                'new_gas_production': new_gas_production,
                'total_revenue': total_revenue,
                'net_income': net_income,
                'npv': npv_estimate
            })
        
        return sensitivity_results
    
    def analyze_cost_sensitivity(self, base_metrics: ProductionMetrics,
                               cost_range: List[float]) -> List[Dict[str, Any]]:
        """Analyze sensitivity to operating cost changes"""
        sensitivity_results = []
        base_revenue = base_metrics.total_revenue()
        
        for cost_change_pct in cost_range:
            new_operating_cost = base_metrics.operating_cost_usd * (1 + cost_change_pct / 100)
            net_income = base_revenue - new_operating_cost
            npv_estimate = net_income * 8
            
            sensitivity_results.append({
                'cost_change_pct': cost_change_pct,
                'new_operating_cost': new_operating_cost,
                'net_income': net_income,
                'npv': npv_estimate
            })
        
        return sensitivity_results


@dataclass
class WaterfallComponent:
    """Component for waterfall chart visualization"""
    name: str
    value: float
    component_type: str  # 'revenue', 'cost', 'profit'
    category: str = "general"  # Additional categorization
    
    def is_positive(self) -> bool:
        """Check if component value is positive"""
        return self.value >= 0


@dataclass
class EconomicAnalysis:
    """Complete economic analysis for an entity"""
    entity_id: str
    entity_type: str
    analysis_date: date
    revenue_breakdown: RevenueBreakdown
    cost_analysis: CostAnalysis
    profitability_metrics: ProfitabilityMetrics
    npv_analysis: Optional[NPVAnalysis] = None
    roi_metrics: Optional[ROIMetrics] = None
    sensitivity_analysis: Optional[Dict[str, Any]] = None
    forecast: Optional[EconomicForecast] = None
    
    @classmethod
    def from_production_metrics(cls, production_metrics: ProductionMetrics,
                               price_deck: PriceDeck, cost_structure: CostStructure,
                               entity_id: str = None, entity_type: str = "field") -> 'EconomicAnalysis':
        """Create comprehensive economic analysis from production metrics"""
        
        # Extract production data
        production_data = {
            'oil_bbls': production_metrics.oil_production_bbls,
            'gas_mcf': production_metrics.gas_production_mcf,
            'ngl_bbls': 0.0  # Would need to be added to ProductionMetrics
        }
        
        # Create revenue breakdown
        revenue_breakdown = RevenueBreakdown.from_production(production_data, price_deck)
        
        # Create cost analysis
        revenue_data = {'total_revenue': revenue_breakdown.total_revenue}
        cost_analysis = CostAnalysis.from_production(production_data, revenue_data, cost_structure)
        
        # Create profitability metrics
        profitability_metrics = ProfitabilityMetrics.from_components(revenue_breakdown, cost_analysis)
        
        return cls(
            entity_id=entity_id or production_metrics.entity_id or "unknown",
            entity_type=entity_type,
            analysis_date=date.today(),
            revenue_breakdown=revenue_breakdown,
            cost_analysis=cost_analysis,
            profitability_metrics=profitability_metrics
        )


class EconomicTemplate(BaseReportTemplate):
    """
    Economic Template for comprehensive financial analysis
    Implements NPV calculations, ROI metrics, revenue/cost breakdown, and profitability analysis
    """
    
    def __init__(self, template_name: str = "economic_report", version: str = "1.0.0",
                 template_path: Optional[Path] = None, **kwargs):
        """Initialize EconomicTemplate"""
        super().__init__(
            template_name=template_name,
            template_type="economic",
            version=version,
            template_path=template_path,
            **kwargs
        )
        
        # Price deck and cost structure for calculations
        self.price_deck = kwargs.get('price_deck', PriceDeck())
        self.cost_structure = kwargs.get('cost_structure', CostStructure())
        
        # Add economic-specific context requirements
        self._setup_economic_context_requirements()
        
        # Initialize economic sections
        self.economic_sections = {
            "revenue_analysis": True,
            "cost_analysis": True,
            "profitability_metrics": True,
            "npv_analysis": True,
            "roi_metrics": True,
            "sensitivity_analysis": True,
            "economic_forecasts": True
        }
    
    def _setup_economic_context_requirements(self):
        """Set up economic-specific context requirements"""
        economic_requirements = [
            "economic_analysis",
            "revenue_breakdown", 
            "cost_analysis",
            "profitability_metrics",
            "npv_analysis",
            "roi_metrics"
        ]
        
        # Add to existing requirements
        self.context.require_fields(economic_requirements)
    
    def build_economic_context_from_production(self, production: ProductionMetrics) -> Dict[str, Any]:
        """Build economic context from production metrics with go-by report calculations"""
        # Create comprehensive economic analysis following go-by report patterns
        economic_analysis = EconomicAnalysis.from_production_metrics(
            production, self.price_deck, self.cost_structure,
            entity_id=production.entity_id, entity_type=production.entity_type
        )
        
        # Apply go-by report revenue calculation patterns
        goby_revenue_calculations = self._apply_goby_revenue_calculations(production)
        
        context = {
            "production_metrics": {
                "oil_bbls": production.oil_production_bbls,
                "gas_mcf": production.gas_production_mcf,
                "water_bbls": production.water_production_bbls,
                "daily_oil_rate": production.daily_oil_rate,
                "daily_gas_rate": production.daily_gas_rate,
                "period_start": production.period_start,
                "period_end": production.period_end,
                "days_in_period": production.days_in_period,
                "active_well_count": production.active_well_count,
                "entity_id": production.entity_id,
                "entity_type": production.entity_type
            },
            "revenue_breakdown": {
                "oil_revenue": economic_analysis.revenue_breakdown.oil_revenue,
                "gas_revenue": economic_analysis.revenue_breakdown.gas_revenue,
                "ngl_revenue": economic_analysis.revenue_breakdown.ngl_revenue,
                "total_revenue": economic_analysis.revenue_breakdown.total_revenue,
                "oil_percentage": economic_analysis.revenue_breakdown.oil_percentage,
                "gas_percentage": economic_analysis.revenue_breakdown.gas_percentage,
                "revenue_per_boe": economic_analysis.revenue_breakdown.revenue_per_boe
            },
            "cost_analysis": {
                "operating_costs": economic_analysis.cost_analysis.operating_costs,
                "capital_costs": economic_analysis.cost_analysis.capital_costs,
                "royalties": economic_analysis.cost_analysis.royalties,
                "severance_tax": economic_analysis.cost_analysis.severance_tax,
                "total_costs": economic_analysis.cost_analysis.total_costs,
                "cost_per_boe": economic_analysis.cost_analysis.cost_per_boe
            },
            "profitability_metrics": {
                "gross_revenue": economic_analysis.profitability_metrics.gross_revenue,
                "net_income": economic_analysis.profitability_metrics.net_income,
                "profit_margin": economic_analysis.profitability_metrics.profit_margin,
                "operating_margin": economic_analysis.profitability_metrics.operating_margin,
                "netback_per_boe": economic_analysis.profitability_metrics.netback_per_boe,
                "ebitda": economic_analysis.profitability_metrics.ebitda
            },
            "financial_summary": {
                "total_revenue": economic_analysis.revenue_breakdown.total_revenue,
                "net_revenue": economic_analysis.profitability_metrics.net_revenue,
                "operating_margin": economic_analysis.profitability_metrics.operating_margin,
                "profit_margin": economic_analysis.profitability_metrics.profit_margin
            },
            "economic_analysis": economic_analysis
        }
        
        # Merge go-by report calculations into context
        context.update(goby_revenue_calculations)
        
        return context
    
    def _apply_goby_revenue_calculations(self, production: ProductionMetrics) -> Dict[str, Any]:
        """Apply go-by report revenue calculation patterns matching Excel reports"""
        from ..hierarchical_aggregator import HierarchicalAggregator
        
        # Initialize hierarchical aggregator with same price/cost settings
        hierarchical_agg = HierarchicalAggregator(
            price_deck=self.price_deck,
            cost_structure=self.cost_structure
        )
        
        # Convert ProductionMetrics to production dictionary format for aggregator
        production_data = {
            'oil_bbls': production.oil_production_bbls,
            'gas_mcf': production.gas_production_mcf,
            'ngl_bbls': getattr(production, 'ngl_production_bbls', 0.0),  # Add if available
            'water_bbls': production.water_production_bbls
        }
        
        # Apply hierarchical aggregator revenue calculations (matches go-by Excel logic)
        revenue_calculations = hierarchical_agg.well_aggregator.calculate_revenue(production_data)
        cost_calculations = hierarchical_agg.well_aggregator.calculate_costs(production_data, revenue_calculations)
        
        # Calculate 14-row structure metrics matching go-by reports
        goby_metrics = self._calculate_goby_14_row_structure(
            production_data, revenue_calculations, cost_calculations
        )
        
        return {
            "goby_revenue_calculations": revenue_calculations,
            "goby_cost_calculations": cost_calculations,
            "goby_14_row_metrics": goby_metrics,
            "goby_economic_summary": {
                "gross_revenue": revenue_calculations['gross_revenue'],
                "total_costs": cost_calculations['total_costs'],
                "net_income": cost_calculations['net_income'],
                "boe_production": production_data['oil_bbls'] + (production_data['gas_mcf'] / 6),
                "revenue_per_boe": revenue_calculations['gross_revenue'] / (production_data['oil_bbls'] + (production_data['gas_mcf'] / 6)) if (production_data['oil_bbls'] + (production_data['gas_mcf'] / 6)) > 0 else 0,
                "cost_per_boe": cost_calculations['total_costs'] / (production_data['oil_bbls'] + (production_data['gas_mcf'] / 6)) if (production_data['oil_bbls'] + (production_data['gas_mcf'] / 6)) > 0 else 0,
                "netback_per_boe": cost_calculations['net_income'] / (production_data['oil_bbls'] + (production_data['gas_mcf'] / 6)) if (production_data['oil_bbls'] + (production_data['gas_mcf'] / 6)) > 0 else 0
            }
        }
    
    def _calculate_goby_14_row_structure(self, production_data: Dict[str, float], 
                                        revenue_calcs: Dict[str, float], 
                                        cost_calcs: Dict[str, float]) -> Dict[str, Any]:
        """Calculate 14-row structure metrics matching go-by Excel reports"""
        
        # Extract volumes
        oil_bbls = production_data.get('oil_bbls', 0)
        gas_mcf = production_data.get('gas_mcf', 0)
        water_bbls = production_data.get('water_bbls', 0)
        boe_total = oil_bbls + (gas_mcf / 6)  # Convert gas to BOE
        
        # Extract financial values
        gross_revenue = revenue_calcs.get('gross_revenue', 0)
        operating_costs = cost_calcs.get('operating_cost', 0)
        royalties = cost_calcs.get('royalties', 0)
        severance_tax = cost_calcs.get('severance_tax', 0)
        net_income = cost_calcs.get('net_income', 0)
        
        # Calculate 14-row structure (following go-by Excel report format)
        goby_14_rows = {
            "row_1_oil_production_bbls": oil_bbls,
            "row_2_gas_production_mcf": gas_mcf,
            "row_3_water_production_bbls": water_bbls,
            "row_4_total_boe": boe_total,
            "row_5_oil_revenue_usd": revenue_calcs.get('oil_revenue', 0),
            "row_6_gas_revenue_usd": revenue_calcs.get('gas_revenue', 0),
            "row_7_ngl_revenue_usd": revenue_calcs.get('ngl_revenue', 0),
            "row_8_gross_revenue_usd": gross_revenue,
            "row_9_operating_costs_usd": operating_costs,
            "row_10_royalties_usd": royalties,
            "row_11_severance_tax_usd": severance_tax,
            "row_12_total_costs_usd": cost_calcs.get('total_costs', 0),
            "row_13_net_income_usd": net_income,
            "row_14_profit_margin_pct": (net_income / gross_revenue * 100) if gross_revenue > 0 else 0
        }
        
        # Add per-BOE calculations (key metrics from go-by reports)
        if boe_total > 0:
            goby_14_rows.update({
                "revenue_per_boe": gross_revenue / boe_total,
                "operating_cost_per_boe": operating_costs / boe_total,
                "royalties_per_boe": royalties / boe_total,
                "netback_per_boe": net_income / boe_total,
                "total_cost_per_boe": cost_calcs.get('total_costs', 0) / boe_total
            })
        
        # Add productivity metrics (common in go-by reports)
        if oil_bbls > 0:
            goby_14_rows.update({
                "gas_oil_ratio": gas_mcf / oil_bbls,
                "water_cut_pct": (water_bbls / (oil_bbls + water_bbls) * 100) if (oil_bbls + water_bbls) > 0 else 0
            })
        
        return goby_14_rows
    
    def integrate_goby_field_economics(self, field_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate field-level economics following go-by report patterns"""
        
        # Extract field-level aggregated data (from hierarchical aggregator output)
        field_economics = {
            "field_summary": {
                "total_wells": field_metrics.get('total_wells', 0),
                "active_wells": field_metrics.get('active_wells', 0),
                "total_leases": field_metrics.get('total_leases', 0),
                "oil_production_bbls": field_metrics.get('oil_production_bbls', 0),
                "gas_production_mcf": field_metrics.get('gas_production_mcf', 0),
                "water_production_bbls": field_metrics.get('water_production_bbls', 0),
                "total_boe": field_metrics.get('total_boe', 0)
            },
            "field_economics": {
                "gross_revenue": field_metrics.get('gross_revenue', 0),
                "operating_cost": field_metrics.get('operating_cost', 0),
                "royalties": field_metrics.get('royalties', 0),
                "severance_tax": field_metrics.get('severance_tax', 0),
                "total_costs": field_metrics.get('total_costs', 0),
                "net_income": field_metrics.get('net_income', 0)
            },
            "field_performance": {
                "avg_oil_per_well": field_metrics.get('avg_oil_per_well', 0),
                "avg_gas_per_well": field_metrics.get('avg_gas_per_well', 0),
                "avg_revenue_per_well": field_metrics.get('gross_revenue', 0) / field_metrics.get('total_wells', 1),
                "avg_wells_per_lease": field_metrics.get('avg_wells_per_lease', 0)
            }
        }
        
        # Add field economics to template context
        self.context["field_economics"] = field_economics
        
        return field_economics
    
    def build_economic_context_from_economics(self, economics: EconomicMetrics) -> Dict[str, Any]:
        """Build economic context from EconomicMetrics model"""
        # Calculate net income
        net_income = economics.calculate_net_income()
        
        context = {
            "economic_analysis": {
                "revenue": economics.revenue,
                "operating_costs": economics.operating_costs,
                "capital_costs": economics.capital_costs,
                "royalties": economics.royalties,
                "net_income": net_income,
                "production_bbls": economics.production_bbls,
                "entity_id": economics.entity_id,
                "entity_type": economics.entity_type
            },
            "cost_analysis": {
                "operating_costs": economics.operating_costs,
                "capital_costs": economics.capital_costs,
                "royalties": economics.royalties,
                "total_costs": economics.operating_costs + economics.capital_costs + economics.royalties,
                "operating_cost_per_bbl": economics.operating_cost_per_bbl,
            },
            "profitability_metrics": {
                "operating_cost_per_bbl": economics.operating_cost_per_bbl,
                "revenue_per_bbl": economics.revenue_per_bbl,
                "netback_per_bbl": economics.netback_per_bbl,
                "profit_margin": economics.profit_margin,
                "net_income": net_income
            },
            "npv_analysis": {
                "npv": economics.calculate_npv(),
                "discount_rate": economics.discount_rate,
                "years_projection": economics.years_from_start
            },
            "financial_summary": {
                "total_revenue": economics.revenue,
                "net_income": net_income,
                "profit_margin": economics.profit_margin,
                "npv": economics.calculate_npv()
            }
        }
        
        return context
    
    def add_npv_analysis(self, cash_flows: List[float], discount_rate: float = 0.10,
                        project_years: int = 10):
        """Add NPV analysis to economic template"""
        npv_analysis = NPVAnalysis(
            cash_flows=cash_flows,
            discount_rate=discount_rate,
            project_years=project_years
        )
        
        # Calculate sensitivity across different discount rates
        sensitivity_rates = [0.05, 0.08, 0.10, 0.12, 0.15]
        npv_sensitivity = npv_analysis.sensitivity_analysis(sensitivity_rates)
        
        self.context["npv_analysis"] = {
            "npv": npv_analysis.npv,
            "irr": npv_analysis.calculate_irr(),
            "present_value_inflows": npv_analysis.present_value_inflows,
            "present_value_outflows": npv_analysis.present_value_outflows,
            "discount_rate": discount_rate,
            "project_years": project_years,
            "sensitivity_analysis": npv_sensitivity,
            "cash_flows": cash_flows
        }
    
    def add_roi_metrics(self, initial_investment: float, annual_net_income: float,
                       project_years: int = 10):
        """Add ROI metrics to economic template"""
        roi_metrics = ROIMetrics(
            initial_investment=initial_investment,
            annual_net_income=annual_net_income,
            project_years=project_years
        )
        
        self.context["roi_metrics"] = {
            "total_roi": roi_metrics.total_roi,
            "annual_roi": roi_metrics.annual_roi,
            "payback_period_years": roi_metrics.payback_period_years,
            "initial_investment": initial_investment,
            "annual_net_income": annual_net_income,
            "project_years": project_years
        }
    
    def add_sensitivity_analysis(self, production_metrics: ProductionMetrics):
        """Add comprehensive sensitivity analysis"""
        sensitivity = SensitivityAnalysis()
        
        # Oil price sensitivity (-30% to +30%)
        oil_price_sensitivity = sensitivity.analyze_oil_price_sensitivity(
            production_metrics, [-30, -20, -10, 0, 10, 20, 30]
        )
        
        # Production volume sensitivity (-50% to +50%)
        production_sensitivity = sensitivity.analyze_production_sensitivity(
            production_metrics, [-50, -30, -15, 0, 15, 30, 50]
        )
        
        # Operating cost sensitivity (-25% to +50%)
        cost_sensitivity = sensitivity.analyze_cost_sensitivity(
            production_metrics, [-25, -15, -5, 0, 10, 25, 50]
        )
        
        self.context["sensitivity_analysis"] = {
            "oil_price_sensitivity": oil_price_sensitivity,
            "production_sensitivity": production_sensitivity,
            "cost_sensitivity": cost_sensitivity,
            "tornado_chart_data": self._prepare_tornado_chart_data(
                oil_price_sensitivity, production_sensitivity, cost_sensitivity
            )
        }
    
    def _prepare_tornado_chart_data(self, oil_sensitivity: List[Dict], 
                                  production_sensitivity: List[Dict],
                                  cost_sensitivity: List[Dict]) -> List[Dict]:
        """Prepare data for tornado chart showing sensitivity impact"""
        
        def get_sensitivity_range(data, key='npv'):
            values = [item[key] for item in data]
            return max(values) - min(values)
        
        tornado_data = [
            {
                'variable': 'Oil Price',
                'impact_range': get_sensitivity_range(oil_sensitivity),
                'low_case': min(item['npv'] for item in oil_sensitivity),
                'high_case': max(item['npv'] for item in oil_sensitivity)
            },
            {
                'variable': 'Production Volume',
                'impact_range': get_sensitivity_range(production_sensitivity),
                'low_case': min(item['npv'] for item in production_sensitivity),
                'high_case': max(item['npv'] for item in production_sensitivity)
            },
            {
                'variable': 'Operating Costs',
                'impact_range': get_sensitivity_range(cost_sensitivity),
                'low_case': min(item['npv'] for item in cost_sensitivity),
                'high_case': max(item['npv'] for item in cost_sensitivity)
            }
        ]
        
        # Sort by impact range (most sensitive first)
        return sorted(tornado_data, key=lambda x: x['impact_range'], reverse=True)
    
    def add_economic_forecast(self, historical_production: List[Dict[str, Any]],
                            forecast_years: int = 5, decline_rate: float = 0.05,
                            price_escalation: float = 0.02):
        """Add economic forecasting to template"""
        forecast = EconomicForecast()
        
        # Generate production forecast
        production_forecast = forecast.forecast_production(
            historical_production, forecast_years, decline_rate
        )
        
        # Generate revenue forecast
        revenue_forecast = forecast.forecast_revenue(
            production_forecast, self.price_deck, forecast_years, price_escalation
        )
        
        # Calculate NPV of forecasted cash flows (simplified)
        forecasted_cash_flows = []
        for year_forecast in revenue_forecast:
            # Simplified cash flow = revenue - estimated costs
            revenue = year_forecast['total_revenue']
            estimated_costs = revenue * 0.4  # 40% cost assumption
            cash_flow = revenue - estimated_costs
            forecasted_cash_flows.append(cash_flow)
        
        forecast_npv = npf.npv(0.10, [0] + forecasted_cash_flows)  # No initial investment assumed
        
        self.context["economic_forecast"] = {
            "production_forecast": production_forecast,
            "revenue_forecast": revenue_forecast,
            "forecast_years": forecast_years,
            "decline_rate": decline_rate,
            "price_escalation": price_escalation,
            "forecast_npv": forecast_npv,
            "cash_flows": forecasted_cash_flows
        }
    
    def generate_waterfall_data(self) -> List[WaterfallComponent]:
        """Generate waterfall chart data from economic context"""
        components = []
        
        # Get revenue breakdown
        revenue = self.context.get("revenue_breakdown", {})
        if revenue:
            components.extend([
                WaterfallComponent("Oil Revenue", revenue.get('oil_revenue', 0), "revenue", "hydrocarbon"),
                WaterfallComponent("Gas Revenue", revenue.get('gas_revenue', 0), "revenue", "hydrocarbon"),
                WaterfallComponent("NGL Revenue", revenue.get('ngl_revenue', 0), "revenue", "hydrocarbon")
            ])
        
        # Get cost breakdown
        costs = self.context.get("cost_analysis", {})
        if costs:
            components.extend([
                WaterfallComponent("Operating Costs", -costs.get('operating_costs', 0), "cost", "operational"),
                WaterfallComponent("Royalties", -costs.get('royalties', 0), "cost", "government"),
                WaterfallComponent("Severance Tax", -costs.get('severance_tax', 0), "cost", "government"),
                WaterfallComponent("Capital Costs", -costs.get('capital_costs', 0), "cost", "capital")
            ])
        
        # Add net income
        profitability = self.context.get("profitability_metrics", {})
        if profitability:
            components.append(
                WaterfallComponent("Net Income", profitability.get('net_income', 0), "profit", "final")
            )
        
        return components
    
    def calculate_enhanced_netback_analysis(self) -> Dict[str, Any]:
        """Calculate enhanced netback analysis with detailed cost breakdown"""
        revenue_breakdown = self.context.get("revenue_breakdown", {})
        cost_analysis = self.context.get("cost_analysis", {})
        production_metrics = self.context.get("production_metrics", {})
        
        # Calculate BOE for per-unit calculations
        oil_bbls = production_metrics.get("oil_bbls", 0)
        gas_mcf = production_metrics.get("gas_mcf", 0)
        total_boe = oil_bbls + (gas_mcf / 6) if oil_bbls or gas_mcf else 1
        
        # Revenue components per BOE
        revenue_per_boe_breakdown = {
            "oil_revenue_per_boe": revenue_breakdown.get('oil_revenue', 0) / total_boe,
            "gas_revenue_per_boe": revenue_breakdown.get('gas_revenue', 0) / total_boe,
            "ngl_revenue_per_boe": revenue_breakdown.get('ngl_revenue', 0) / total_boe,
            "total_revenue_per_boe": revenue_breakdown.get('total_revenue', 0) / total_boe
        }
        
        # Cost components per BOE
        cost_per_boe_breakdown = {
            "operating_cost_per_boe": cost_analysis.get('operating_costs', 0) / total_boe,
            "royalties_per_boe": cost_analysis.get('royalties', 0) / total_boe,
            "severance_tax_per_boe": cost_analysis.get('severance_tax', 0) / total_boe,
            "transportation_cost_per_boe": cost_analysis.get('transportation_costs', 0) / total_boe,
            "processing_cost_per_boe": cost_analysis.get('processing_costs', 0) / total_boe,
            "total_variable_cost_per_boe": cost_analysis.get('variable_costs', 0) / total_boe
        }
        
        # Netback calculation (revenue minus variable costs per BOE)
        netback_calculation = {
            "gross_netback_per_boe": revenue_per_boe_breakdown['total_revenue_per_boe'],
            "operating_netback_per_boe": (revenue_per_boe_breakdown['total_revenue_per_boe'] - 
                                        cost_per_boe_breakdown['operating_cost_per_boe']),
            "royalty_netback_per_boe": (revenue_per_boe_breakdown['total_revenue_per_boe'] - 
                                      cost_per_boe_breakdown['operating_cost_per_boe'] -
                                      cost_per_boe_breakdown['royalties_per_boe']),
            "full_netback_per_boe": (revenue_per_boe_breakdown['total_revenue_per_boe'] - 
                                   cost_per_boe_breakdown['total_variable_cost_per_boe'])
        }
        
        # Netback percentages
        gross_revenue_per_boe = revenue_per_boe_breakdown['total_revenue_per_boe']
        netback_percentages = {}
        if gross_revenue_per_boe > 0:
            netback_percentages = {
                "operating_netback_pct": (netback_calculation['operating_netback_per_boe'] / gross_revenue_per_boe * 100),
                "royalty_netback_pct": (netback_calculation['royalty_netback_per_boe'] / gross_revenue_per_boe * 100),
                "full_netback_pct": (netback_calculation['full_netback_per_boe'] / gross_revenue_per_boe * 100)
            }
        
        return {
            "revenue_per_boe_breakdown": revenue_per_boe_breakdown,
            "cost_per_boe_breakdown": cost_per_boe_breakdown,
            "netback_calculation": netback_calculation,
            "netback_percentages": netback_percentages,
            "total_boe": total_boe
        }
    
    def add_enhanced_cost_structure_analysis(self) -> Dict[str, Any]:
        """Add detailed cost structure analysis"""
        cost_analysis = self.context.get("cost_analysis", {})
        revenue_breakdown = self.context.get("revenue_breakdown", {})
        
        total_costs = cost_analysis.get('total_costs', 0)
        total_revenue = revenue_breakdown.get('total_revenue', 0)
        
        # Cost breakdown percentages
        cost_breakdown_pct = {}
        if total_costs > 0:
            cost_breakdown_pct = {
                "operating_costs_pct": (cost_analysis.get('operating_costs', 0) / total_costs * 100),
                "capital_costs_pct": (cost_analysis.get('capital_costs', 0) / total_costs * 100),
                "royalties_pct": (cost_analysis.get('royalties', 0) / total_costs * 100),
                "severance_tax_pct": (cost_analysis.get('severance_tax', 0) / total_costs * 100),
                "other_costs_pct": (cost_analysis.get('other_costs', 0) / total_costs * 100)
            }
        
        # Cost as percentage of revenue
        cost_as_revenue_pct = {}
        if total_revenue > 0:
            cost_as_revenue_pct = {
                "total_costs_vs_revenue_pct": (total_costs / total_revenue * 100),
                "operating_costs_vs_revenue_pct": (cost_analysis.get('operating_costs', 0) / total_revenue * 100),
                "royalties_vs_revenue_pct": (cost_analysis.get('royalties', 0) / total_revenue * 100),
                "severance_tax_vs_revenue_pct": (cost_analysis.get('severance_tax', 0) / total_revenue * 100)
            }
        
        # Cost efficiency metrics
        cost_efficiency = {
            "cost_efficiency_index": (1 - (total_costs / total_revenue)) if total_revenue > 0 else 0,
            "operating_efficiency": (1 - (cost_analysis.get('operating_costs', 0) / total_revenue)) if total_revenue > 0 else 0,
            "variable_cost_ratio": (cost_analysis.get('variable_costs', 0) / total_revenue) if total_revenue > 0 else 0
        }
        
        cost_structure_analysis = {
            "cost_breakdown_percentages": cost_breakdown_pct,
            "cost_as_revenue_percentages": cost_as_revenue_pct,
            "cost_efficiency_metrics": cost_efficiency,
            "absolute_costs": {
                "operating_costs": cost_analysis.get('operating_costs', 0),
                "capital_costs": cost_analysis.get('capital_costs', 0),
                "royalties": cost_analysis.get('royalties', 0),
                "severance_tax": cost_analysis.get('severance_tax', 0),
                "total_costs": total_costs
            }
        }
        
        self.context["cost_structure_analysis"] = cost_structure_analysis
        return cost_structure_analysis
    
    def add_revenue_optimization_analysis(self) -> Dict[str, Any]:
        """Add revenue optimization analysis"""
        revenue_breakdown = self.context.get("revenue_breakdown", {})
        production_metrics = self.context.get("production_metrics", {})
        
        oil_bbls = production_metrics.get("oil_bbls", 0)
        gas_mcf = production_metrics.get("gas_mcf", 0)
        
        # Revenue per unit calculations
        revenue_per_unit = {}
        if oil_bbls > 0:
            revenue_per_unit["oil_revenue_per_bbl"] = revenue_breakdown.get('oil_revenue', 0) / oil_bbls
        if gas_mcf > 0:
            revenue_per_unit["gas_revenue_per_mcf"] = revenue_breakdown.get('gas_revenue', 0) / gas_mcf
        
        # Revenue mix analysis
        total_revenue = revenue_breakdown.get('total_revenue', 0)
        revenue_mix = {}
        if total_revenue > 0:
            revenue_mix = {
                "oil_revenue_percentage": revenue_breakdown.get('oil_percentage', 0),
                "gas_revenue_percentage": revenue_breakdown.get('gas_percentage', 0),
                "ngl_revenue_percentage": revenue_breakdown.get('ngl_percentage', 0),
                "hydrocarbon_revenue_percentage": (revenue_breakdown.get('oil_percentage', 0) + 
                                                 revenue_breakdown.get('gas_percentage', 0) + 
                                                 revenue_breakdown.get('ngl_percentage', 0))
            }
        
        # Revenue diversification index (higher = more diversified)
        oil_pct = revenue_mix.get("oil_revenue_percentage", 0) / 100
        gas_pct = revenue_mix.get("gas_revenue_percentage", 0) / 100
        ngl_pct = revenue_mix.get("ngl_revenue_percentage", 0) / 100
        
        diversification_index = 1 - (oil_pct**2 + gas_pct**2 + ngl_pct**2) if oil_pct or gas_pct or ngl_pct else 0
        
        # Revenue quality metrics
        revenue_quality = {
            "revenue_concentration_risk": max(oil_pct, gas_pct, ngl_pct),
            "revenue_diversification_index": diversification_index,
            "high_value_revenue_pct": oil_pct + ngl_pct,  # Oil and NGL typically higher value
            "gas_revenue_dependency": gas_pct
        }
        
        revenue_optimization_analysis = {
            "revenue_per_unit": revenue_per_unit,
            "revenue_mix": revenue_mix,
            "revenue_quality_metrics": revenue_quality,
            "optimization_opportunities": self._identify_revenue_optimization_opportunities(
                revenue_mix, revenue_quality
            )
        }
        
        self.context["revenue_optimization_analysis"] = revenue_optimization_analysis
        return revenue_optimization_analysis
    
    def _identify_revenue_optimization_opportunities(self, revenue_mix: Dict[str, float], 
                                                   revenue_quality: Dict[str, float]) -> List[str]:
        """Identify revenue optimization opportunities"""
        opportunities = []
        
        # Check for over-dependence on gas
        if revenue_quality.get("gas_revenue_dependency", 0) > 0.6:
            opportunities.append("Consider oil development to reduce gas dependence")
        
        # Check for low diversification
        if revenue_quality.get("revenue_diversification_index", 0) < 0.3:
            opportunities.append("Improve revenue diversification across hydrocarbon types")
        
        # Check for NGL capture opportunities
        if revenue_mix.get("ngl_revenue_percentage", 0) < 5:
            opportunities.append("Evaluate NGL capture and processing opportunities")
        
        # Check for high concentration risk
        if revenue_quality.get("revenue_concentration_risk", 0) > 0.8:
            opportunities.append("Mitigate revenue concentration risk through diversification")
        
        return opportunities
    
    def get_economic_kpis(self) -> Dict[str, Any]:
        """Get key economic performance indicators"""
        profitability = self.context.get("profitability_metrics", {})
        npv_analysis = self.context.get("npv_analysis", {})
        roi_metrics = self.context.get("roi_metrics", {})
        netback_analysis = self.calculate_enhanced_netback_analysis()
        
        return {
            "primary_kpis": {
                "net_income": profitability.get('net_income', 0),
                "profit_margin": profitability.get('profit_margin', 0),
                "netback_per_boe": netback_analysis["netback_calculation"].get('full_netback_per_boe', 0),
                "npv": npv_analysis.get('npv', 0)
            },
            "secondary_kpis": {
                "operating_margin": profitability.get('operating_margin', 0),
                "ebitda": profitability.get('ebitda', 0),
                "irr": npv_analysis.get('irr', 0),
                "roi": roi_metrics.get('annual_roi', 0),
                "operating_netback_per_boe": netback_analysis["netback_calculation"].get('operating_netback_per_boe', 0)
            },
            "financial_ratios": {
                "revenue_per_boe": netback_analysis["revenue_per_boe_breakdown"].get('total_revenue_per_boe', 0),
                "cost_per_boe": netback_analysis["cost_per_boe_breakdown"].get('total_variable_cost_per_boe', 0),
                "payback_period": roi_metrics.get('payback_period_years', 0),
                "full_netback_percentage": netback_analysis["netback_percentages"].get('full_netback_pct', 0)
            },
            "cost_efficiency_metrics": {
                "operating_cost_per_boe": netback_analysis["cost_per_boe_breakdown"].get('operating_cost_per_boe', 0),
                "royalties_per_boe": netback_analysis["cost_per_boe_breakdown"].get('royalties_per_boe', 0),
                "total_variable_cost_per_boe": netback_analysis["cost_per_boe_breakdown"].get('total_variable_cost_per_boe', 0)
            }
        }
    
    def analyze_individual_well_economics(self, well_id: str, well_production: ProductionMetrics,
                                        initial_well_cost: float = 8000000.0,
                                        well_life_years: int = 20,
                                        decline_rate: float = 0.08) -> Dict[str, Any]:
        """Analyze individual well economics with NPV and ROI metrics"""
        
        # Build economic context for this well
        well_context = self.build_economic_context_from_production(well_production)
        
        # Get first-year economics
        first_year_net_income = well_context["goby_economic_summary"]["net_income"]
        first_year_revenue = well_context["goby_economic_summary"]["gross_revenue"]
        
        # Generate cash flow projections with decline
        cash_flows = [-initial_well_cost]  # Initial investment
        
        for year in range(1, well_life_years + 1):
            # Apply decline rate to production and revenue
            year_factor = (1 - decline_rate) ** (year - 1)
            year_net_income = first_year_net_income * year_factor
            cash_flows.append(year_net_income)
        
        # Calculate NPV and IRR
        npv_10 = npf.npv(0.10, cash_flows)
        npv_12 = npf.npv(0.12, cash_flows)
        npv_15 = npf.npv(0.15, cash_flows)
        
        try:
            irr = npf.irr(cash_flows)
        except:
            irr = 0.0
        
        # Calculate payback period
        cumulative_cash = -initial_well_cost
        payback_years = well_life_years
        for year, cash_flow in enumerate(cash_flows[1:], 1):
            cumulative_cash += cash_flow
            if cumulative_cash >= 0:
                # Interpolate for partial year
                prev_cumulative = cumulative_cash - cash_flow
                payback_years = year - 1 + abs(prev_cumulative) / cash_flow
                break
        
        # Calculate ROI metrics
        total_cash_flows = sum(cash_flows[1:])  # Exclude initial investment
        total_roi = (total_cash_flows - initial_well_cost) / initial_well_cost
        annual_roi = total_roi / well_life_years
        
        # Calculate EUR (Estimated Ultimate Recovery)
        first_year_oil = well_production.oil_production_bbls
        first_year_gas = well_production.gas_production_mcf
        
        eur_oil = sum([first_year_oil * ((1 - decline_rate) ** (year - 1)) 
                      for year in range(1, well_life_years + 1)])
        eur_gas = sum([first_year_gas * ((1 - decline_rate) ** (year - 1)) 
                      for year in range(1, well_life_years + 1)])
        eur_boe = eur_oil + (eur_gas / 6)
        
        # Well-level efficiency metrics
        finding_cost_per_boe = initial_well_cost / eur_boe if eur_boe > 0 else 0
        revenue_per_investment_dollar = total_cash_flows / initial_well_cost if initial_well_cost > 0 else 0
        
        well_economics = {
            "well_identification": {
                "well_id": well_id,
                "entity_id": well_production.entity_id,
                "analysis_assumptions": {
                    "initial_well_cost": initial_well_cost,
                    "well_life_years": well_life_years,
                    "decline_rate": decline_rate
                }
            },
            "npv_analysis": {
                "npv_10_percent": npv_10,
                "npv_12_percent": npv_12,
                "npv_15_percent": npv_15,
                "irr": irr,
                "cash_flows": cash_flows
            },
            "roi_metrics": {
                "total_roi": total_roi,
                "annual_roi": annual_roi,
                "payback_period_years": payback_years,
                "revenue_per_investment_dollar": revenue_per_investment_dollar
            },
            "production_forecast": {
                "eur_oil_bbls": eur_oil,
                "eur_gas_mcf": eur_gas,
                "eur_boe": eur_boe,
                "first_year_oil": first_year_oil,
                "first_year_gas": first_year_gas
            },
            "cost_efficiency": {
                "finding_cost_per_boe": finding_cost_per_boe,
                "initial_cost_per_daily_boe": initial_well_cost / (well_context["production_metrics"]["oil_bbls"] / 365 + well_context["production_metrics"]["gas_mcf"] / (365 * 6)) if well_context["production_metrics"]["oil_bbls"] > 0 or well_context["production_metrics"]["gas_mcf"] > 0 else 0
            },
            "profitability_assessment": {
                "is_profitable_10_percent": npv_10 > 0,
                "is_profitable_12_percent": npv_12 > 0,
                "is_profitable_15_percent": npv_15 > 0,
                "irr_exceeds_10_percent": irr > 0.10 if irr else False,
                "payback_under_5_years": payback_years < 5,
                "investment_grade": self._determine_well_investment_grade(npv_12, irr, payback_years)
            },
            "first_year_metrics": well_context["goby_economic_summary"]
        }
        
        return well_economics
    
    def _determine_well_investment_grade(self, npv_12: float, irr: float, payback_years: float) -> str:
        """Determine investment grade for individual well"""
        
        # Excellent: High NPV, High IRR, Quick Payback
        if npv_12 > 5000000 and irr > 0.25 and payback_years < 3:
            return "Excellent"
        
        # Good: Positive NPV, Good IRR, Reasonable Payback
        elif npv_12 > 2000000 and irr > 0.15 and payback_years < 5:
            return "Good"
        
        # Acceptable: Positive NPV, Meets hurdle rates
        elif npv_12 > 0 and irr > 0.12 and payback_years < 8:
            return "Acceptable"
        
        # Marginal: Barely profitable
        elif npv_12 > -1000000 and irr > 0.08 and payback_years < 10:
            return "Marginal"
        
        # Poor: Not profitable
        else:
            return "Poor"
    
    def compare_wells_economic_performance(self, wells_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Compare economic performance across multiple wells"""
        
        well_comparisons = []
        
        for well_id, well_economics in wells_data.items():
            well_summary = {
                "well_id": well_id,
                "npv_12_percent": well_economics["npv_analysis"]["npv_12_percent"],
                "irr": well_economics["npv_analysis"]["irr"],
                "payback_years": well_economics["roi_metrics"]["payback_period_years"],
                "eur_boe": well_economics["production_forecast"]["eur_boe"],
                "finding_cost_per_boe": well_economics["cost_efficiency"]["finding_cost_per_boe"],
                "investment_grade": well_economics["profitability_assessment"]["investment_grade"],
                "first_year_netback": well_economics["first_year_metrics"]["netback_per_boe"]
            }
            well_comparisons.append(well_summary)
        
        # Sort by NPV (descending)
        well_comparisons.sort(key=lambda x: x["npv_12_percent"], reverse=True)
        
        # Calculate portfolio statistics
        npvs = [w["npv_12_percent"] for w in well_comparisons]
        irrs = [w["irr"] for w in well_comparisons if w["irr"] > 0]
        paybacks = [w["payback_years"] for w in well_comparisons if w["payback_years"] < 20]
        
        portfolio_stats = {
            "total_wells": len(well_comparisons),
            "average_npv": sum(npvs) / len(npvs) if npvs else 0,
            "median_npv": sorted(npvs)[len(npvs)//2] if npvs else 0,
            "average_irr": sum(irrs) / len(irrs) if irrs else 0,
            "median_payback": sorted(paybacks)[len(paybacks)//2] if paybacks else 0,
            "profitable_wells_12_percent": sum(1 for npv in npvs if npv > 0),
            "excellent_grade_wells": sum(1 for w in well_comparisons if w["investment_grade"] == "Excellent"),
            "poor_grade_wells": sum(1 for w in well_comparisons if w["investment_grade"] == "Poor")
        }
        
        # Identify top and bottom performers
        top_performers = well_comparisons[:3]  # Top 3
        bottom_performers = well_comparisons[-3:] if len(well_comparisons) > 3 else []
        
        return {
            "well_rankings": well_comparisons,
            "portfolio_statistics": portfolio_stats,
            "top_performers": top_performers,
            "bottom_performers": bottom_performers,
            "investment_recommendations": self._generate_well_investment_recommendations(portfolio_stats, well_comparisons)
        }
    
    def _generate_well_investment_recommendations(self, portfolio_stats: Dict[str, Any], 
                                                well_comparisons: List[Dict[str, Any]]) -> List[str]:
        """Generate investment recommendations based on well performance"""
        recommendations = []
        
        # Portfolio-level recommendations
        profitable_rate = portfolio_stats["profitable_wells_12_percent"] / portfolio_stats["total_wells"]
        if profitable_rate < 0.6:
            recommendations.append("Portfolio has low profitability rate - review drilling strategy and target selection")
        
        if portfolio_stats["average_npv"] < 1000000:
            recommendations.append("Average well NPV is below $1M - consider higher-return prospects")
        
        if portfolio_stats["average_irr"] < 0.15:
            recommendations.append("Average IRR below 15% - evaluate cost reduction opportunities")
        
        # Individual well recommendations
        excellent_wells = [w for w in well_comparisons if w["investment_grade"] == "Excellent"]
        if excellent_wells:
            recommendations.append(f"Focus on replicating success patterns from {len(excellent_wells)} excellent-grade wells")
        
        poor_wells = [w for w in well_comparisons if w["investment_grade"] == "Poor"]
        if poor_wells:
            recommendations.append(f"Investigate and address issues with {len(poor_wells)} poor-performing wells")
        
        # High-grading opportunities
        if portfolio_stats["median_npv"] > portfolio_stats["average_npv"]:
            recommendations.append("Consider high-grading portfolio - eliminate bottom performers")
        
        return recommendations
    
    def generate_waterfall_chart(self, title: str = "Economic Waterfall Analysis") -> str:
        """Generate waterfall chart showing revenue to net income flow"""
        waterfall_components = self.generate_waterfall_data()
        
        if not waterfall_components:
            return self._create_empty_chart("No data available for waterfall chart")
        
        # Prepare data for Plotly waterfall chart
        names = [component.name for component in waterfall_components]
        values = [component.value for component in waterfall_components]
        
        # Create measures array - 'relative' for flow items, 'total' for final result
        measures = []
        colors = []
        
        for component in waterfall_components:
            if component.component_type == "profit":
                measures.append("total")
                colors.append("#2E86AB")  # Blue for final result
            elif component.component_type == "revenue":
                measures.append("relative")
                colors.append("#A23B72")  # Purple for revenue
            elif component.component_type == "cost":
                measures.append("relative") 
                colors.append("#F18F01")  # Orange for costs
            else:
                measures.append("relative")
                colors.append("#C73E1D")  # Red for other
        
        # Create waterfall chart
        fig = go.Figure(go.Waterfall(
            name="Economic Flow",
            orientation="v",
            measure=measures,
            x=names,
            textposition="outside",
            text=[f"${val/1000000:.1f}M" if abs(val) >= 1000000 else f"${val/1000:.0f}K" 
                  for val in values],
            y=values,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "#A23B72"}},  # Revenue color
            decreasing={"marker": {"color": "#F18F01"}},  # Cost color
            totals={"marker": {"color": "#2E86AB"}}       # Net income color
        ))
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#2F4F4F'}
            },
            xaxis_title="Economic Components",
            yaxis_title="Value (USD)",
            yaxis_tickformat="$,.0f",
            height=500,
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        # Format y-axis with million/thousand suffixes
        fig.update_yaxes(
            tickformat="$,.0f",
            gridcolor='lightgray',
            gridwidth=0.5
        )
        
        # Rotate x-axis labels if too many components
        if len(names) > 6:
            fig.update_xaxes(tickangle=45)
        
        return pio.to_html(fig, include_plotlyjs='cdn', div_id="waterfall-chart")
    
    def generate_economic_dashboard(self, title: str = "Economic Performance Dashboard") -> str:
        """Generate comprehensive economic dashboard with multiple charts"""
        
        # Create subplot dashboard
        fig = make_subplots(
            rows=3, cols=2,
            specs=[
                [{'type': 'indicator'}, {'type': 'pie'}],
                [{'type': 'bar'}, {'type': 'scatter'}],
                [{'colspan': 2, 'type': 'bar'}, None]
            ],
            subplot_titles=[
                "Key Performance Indicators", "Revenue Mix", 
                "Cost Breakdown", "NPV Sensitivity",
                "Production Economics Comparison"
            ],
            vertical_spacing=0.1,
            horizontal_spacing=0.1
        )
        
        # 1. KPI Indicators (Row 1, Col 1)
        kpis = self.get_economic_kpis()
        primary_kpis = kpis.get("primary_kpis", {})
        
        fig.add_trace(
            go.Indicator(
                mode="number+gauge+delta",
                value=primary_kpis.get("profit_margin", 0),
                domain={'x': [0, 1], 'y': [0.7, 1]},
                title={'text': "Profit Margin (%)"},
                number={'suffix': "%"},
                gauge={
                    'axis': {'range': [None, 50]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 15], 'color': "lightgray"},
                        {'range': [15, 30], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 25
                    }
                }
            ),
            row=1, col=1
        )
        
        # 2. Revenue Mix Pie Chart (Row 1, Col 2)
        revenue_breakdown = self.context.get("revenue_breakdown", {})
        
        pie_labels = []
        pie_values = []
        pie_colors = ['#A23B72', '#F18F01', '#C73E1D', '#2E86AB']
        
        if revenue_breakdown.get('oil_revenue', 0) > 0:
            pie_labels.append('Oil Revenue')
            pie_values.append(revenue_breakdown['oil_revenue'])
            
        if revenue_breakdown.get('gas_revenue', 0) > 0:
            pie_labels.append('Gas Revenue')
            pie_values.append(revenue_breakdown['gas_revenue'])
            
        if revenue_breakdown.get('ngl_revenue', 0) > 0:
            pie_labels.append('NGL Revenue')
            pie_values.append(revenue_breakdown['ngl_revenue'])
        
        if pie_values:
            fig.add_trace(
                go.Pie(
                    labels=pie_labels,
                    values=pie_values,
                    marker=dict(colors=pie_colors[:len(pie_labels)]),
                    textinfo='label+percent',
                    hole=0.3
                ),
                row=1, col=2
            )
        
        # 3. Cost Breakdown Bar Chart (Row 2, Col 1)
        cost_analysis = self.context.get("cost_analysis", {})
        
        cost_categories = ['Operating', 'Royalties', 'Severance Tax', 'Capital']
        cost_values = [
            cost_analysis.get('operating_costs', 0),
            cost_analysis.get('royalties', 0),
            cost_analysis.get('severance_tax', 0),
            cost_analysis.get('capital_costs', 0)
        ]
        
        # Filter out zero values
        filtered_costs = [(cat, val) for cat, val in zip(cost_categories, cost_values) if val > 0]
        if filtered_costs:
            cost_cats, cost_vals = zip(*filtered_costs)
            
            fig.add_trace(
                go.Bar(
                    x=cost_cats,
                    y=cost_vals,
                    marker_color='#F18F01',
                    text=[f"${val/1000000:.1f}M" if val >= 1000000 else f"${val/1000:.0f}K" 
                          for val in cost_vals],
                    textposition='auto'
                ),
                row=2, col=1
            )
        
        # 4. NPV Sensitivity Analysis (Row 2, Col 2)
        sensitivity_data = self.context.get("sensitivity_analysis", {})
        oil_sensitivity = sensitivity_data.get("oil_price_sensitivity", [])
        
        if oil_sensitivity:
            price_changes = [item["price_change_pct"] for item in oil_sensitivity]
            npvs = [item["npv"] / 1000000 for item in oil_sensitivity]  # Convert to millions
            
            fig.add_trace(
                go.Scatter(
                    x=price_changes,
                    y=npvs,
                    mode='lines+markers',
                    line=dict(color='#2E86AB', width=3),
                    marker=dict(size=8, color='#A23B72'),
                    name='NPV vs Oil Price'
                ),
                row=2, col=2
            )
        
        # 5. Production Economics Comparison (Row 3, spanning both columns)
        netback_analysis = self.calculate_enhanced_netback_analysis()
        
        metrics = ['Revenue/BOE', 'Operating Cost/BOE', 'Royalties/BOE', 'Net/BOE']
        values = [
            netback_analysis["revenue_per_boe_breakdown"].get('total_revenue_per_boe', 0),
            netback_analysis["cost_per_boe_breakdown"].get('operating_cost_per_boe', 0),
            netback_analysis["cost_per_boe_breakdown"].get('royalties_per_boe', 0),
            netback_analysis["netback_calculation"].get('full_netback_per_boe', 0)
        ]
        
        colors = ['#A23B72', '#F18F01', '#C73E1D', '#2E86AB']
        
        fig.add_trace(
            go.Bar(
                x=metrics,
                y=values,
                marker_color=colors,
                text=[f"${val:.2f}" for val in values],
                textposition='auto'
            ),
            row=3, col=1
        )
        
        # Update layout
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 22, 'color': '#2F4F4F'}
            },
            height=900,
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        # Update axes
        fig.update_yaxes(tickformat="$,.0f", row=2, col=1)
        fig.update_yaxes(title_text="NPV ($M)", row=2, col=2)
        fig.update_xaxes(title_text="Oil Price Change (%)", row=2, col=2)
        fig.update_yaxes(title_text="Value per BOE ($)", tickformat="$,.2f", row=3, col=1)
        
        return pio.to_html(fig, include_plotlyjs='cdn', div_id="economic-dashboard")
    
    def generate_sensitivity_tornado_chart(self, title: str = "NPV Sensitivity Analysis") -> str:
        """Generate tornado chart for sensitivity analysis"""
        
        sensitivity_data = self.context.get("sensitivity_analysis", {})
        tornado_data = sensitivity_data.get("tornado_chart_data", [])
        
        if not tornado_data:
            return self._create_empty_chart("No sensitivity data available")
        
        # Prepare data for tornado chart
        variables = [item["variable"] for item in tornado_data]
        low_values = [item["low_case"] / 1000000 for item in tornado_data]  # Convert to millions
        high_values = [item["high_case"] / 1000000 for item in tornado_data]
        
        # Calculate ranges for sorting (already sorted in tornado_data)
        ranges = [high - low for high, low in zip(high_values, low_values)]
        
        # Create horizontal bar chart (tornado style)
        fig = go.Figure()
        
        # Add bars for negative impact (low case)
        fig.add_trace(go.Bar(
            y=variables,
            x=[-r/2 for r in ranges],  # Negative half of range
            orientation='h',
            name='Downside Impact',
            marker_color='#F18F01',
            text=[f"${low:.1f}M" for low in low_values],
            textposition='auto',
            width=0.6
        ))
        
        # Add bars for positive impact (high case) 
        fig.add_trace(go.Bar(
            y=variables,
            x=[r/2 for r in ranges],   # Positive half of range
            orientation='h',
            name='Upside Impact',
            marker_color='#A23B72',
            text=[f"${high:.1f}M" for high in high_values],
            textposition='auto',
            width=0.6
        ))
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': '#2F4F4F'}
            },
            xaxis_title="NPV Impact ($M)",
            yaxis_title="Variables",
            barmode='relative',
            height=400,
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Add vertical line at zero
        fig.add_vline(x=0, line_width=2, line_color="black")
        
        return pio.to_html(fig, include_plotlyjs='cdn', div_id="tornado-chart")
    
    def generate_production_economics_time_series(self, title: str = "Production Economics Over Time") -> str:
        """Generate time series chart showing production and economics trends"""
        
        # Mock time series data - in real implementation, this would come from historical data
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Generate sample data based on current production with some variability
        production_metrics = self.context.get("production_metrics", {})
        base_oil = production_metrics.get("oil_bbls", 1000000) / 12  # Monthly
        base_gas = production_metrics.get("gas_mcf", 6000000) / 12  # Monthly
        
        # Add some monthly variation
        oil_production = [base_oil * (0.85 + 0.3 * (i % 4) / 4) for i in range(12)]
        gas_production = [base_gas * (0.9 + 0.2 * (i % 3) / 3) for i in range(12)]
        
        # Calculate monthly netback (simplified)
        netback_analysis = self.calculate_enhanced_netback_analysis()
        base_netback = netback_analysis["netback_calculation"].get('full_netback_per_boe', 30)
        monthly_netback = [base_netback * (0.8 + 0.4 * (i % 5) / 5) for i in range(12)]
        
        # Create subplot with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add oil production
        fig.add_trace(
            go.Scatter(
                x=months, y=oil_production, mode='lines+markers',
                name="Oil Production (bbls/month)",
                line=dict(color='#A23B72', width=3),
                marker=dict(size=8)
            ),
            secondary_y=False,
        )
        
        # Add gas production
        fig.add_trace(
            go.Scatter(
                x=months, y=gas_production, mode='lines+markers',
                name="Gas Production (Mcf/month)",
                line=dict(color='#F18F01', width=3),
                marker=dict(size=8)
            ),
            secondary_y=False,
        )
        
        # Add netback on secondary y-axis
        fig.add_trace(
            go.Scatter(
                x=months, y=monthly_netback, mode='lines+markers',
                name="Netback ($/BOE)",
                line=dict(color='#2E86AB', width=3, dash='dash'),
                marker=dict(size=8, symbol='diamond')
            ),
            secondary_y=True,
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="Month")
        fig.update_yaxes(title_text="Production Volume", secondary_y=False)
        fig.update_yaxes(title_text="Netback ($/BOE)", secondary_y=True)
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': '#2F4F4F'}
            },
            height=500,
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return pio.to_html(fig, include_plotlyjs='cdn', div_id="time-series-chart")
    
    def _create_empty_chart(self, message: str = "No data available") -> str:
        """Create empty chart with message"""
        fig = go.Figure()
        
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            font=dict(size=16, color="gray")
        )
        
        fig.update_layout(
            title="Chart Not Available",
            height=300,
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        
        return pio.to_html(fig, include_plotlyjs='cdn')
    
    def generate_sensitivity_analysis_tables(self) -> Dict[str, str]:
        """
        Generate HTML tables for sensitivity analysis showing NPV and IRR variations
        
        Returns:
            Dictionary containing HTML tables for different sensitivity scenarios
        """
        if not self.economic_context:
            return {"error": "<p>No economic context available for sensitivity analysis tables</p>"}
            
        tables = {}
        
        # Oil price sensitivity table
        oil_price_scenarios = [50, 60, 70, 80, 90, 100]  # $/bbl
        gas_price_base = self.economic_context.get('gas_price', 3.50)
        
        oil_sensitivity_data = []
        for oil_price in oil_price_scenarios:
            # Recalculate economics with new oil price
            temp_context = self.economic_context.copy()
            temp_context['oil_price'] = oil_price
            
            # Simplified NPV calculation for sensitivity
            annual_oil_revenue = temp_context.get('annual_oil_bbl', 100000) * oil_price
            annual_gas_revenue = temp_context.get('annual_gas_mcf', 500000) * gas_price_base
            annual_revenue = annual_oil_revenue + annual_gas_revenue
            annual_costs = temp_context.get('operating_costs', 2500000)
            annual_net_cash = annual_revenue - annual_costs
            
            # 10-year cash flow projection
            cash_flows = [-temp_context.get('initial_capex', 10000000)]  # Initial investment
            for year in range(10):
                decline_factor = (1 - temp_context.get('decline_rate', 0.08)) ** year
                cash_flows.append(annual_net_cash * decline_factor)
            
            # Calculate NPV and IRR
            npv_10 = npf.npv(0.10, cash_flows)
            npv_15 = npf.npv(0.15, cash_flows)
            
            try:
                irr = npf.irr(cash_flows)
                irr_percent = f"{irr:.1%}" if not np.isnan(irr) else "N/A"
            except:
                irr_percent = "N/A"
                
            oil_sensitivity_data.append({
                'oil_price': oil_price,
                'npv_10': npv_10,
                'npv_15': npv_15,
                'irr': irr_percent
            })
        
        # Generate oil price sensitivity HTML table
        oil_table_html = """
        <table class="sensitivity-table" style="border-collapse: collapse; width: 100%; margin: 20px 0;">
            <caption style="font-weight: bold; margin-bottom: 10px;">Oil Price Sensitivity Analysis</caption>
            <thead>
                <tr style="background-color: #f0f0f0;">
                    <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">Oil Price ($/bbl)</th>
                    <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">NPV @ 10%</th>
                    <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">NPV @ 15%</th>
                    <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">IRR</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for row in oil_sensitivity_data:
            npv_10_color = "green" if row['npv_10'] > 0 else "red"
            npv_15_color = "green" if row['npv_15'] > 0 else "red"
            
            oil_table_html += f"""
                <tr>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">${row['oil_price']}</td>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: right; color: {npv_10_color};">${row['npv_10']:,.0f}</td>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: right; color: {npv_15_color};">${row['npv_15']:,.0f}</td>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">{row['irr']}</td>
                </tr>
            """
        
        oil_table_html += """
            </tbody>
        </table>
        """
        
        tables['oil_price_sensitivity'] = oil_table_html
        
        # Gas price sensitivity table
        gas_price_scenarios = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5]  # $/mcf
        oil_price_base = self.economic_context.get('oil_price', 75.0)
        
        gas_sensitivity_data = []
        for gas_price in gas_price_scenarios:
            # Recalculate economics with new gas price
            temp_context = self.economic_context.copy()
            temp_context['gas_price'] = gas_price
            
            # Simplified NPV calculation for sensitivity
            annual_oil_revenue = temp_context.get('annual_oil_bbl', 100000) * oil_price_base
            annual_gas_revenue = temp_context.get('annual_gas_mcf', 500000) * gas_price
            annual_revenue = annual_oil_revenue + annual_gas_revenue
            annual_costs = temp_context.get('operating_costs', 2500000)
            annual_net_cash = annual_revenue - annual_costs
            
            # 10-year cash flow projection
            cash_flows = [-temp_context.get('initial_capex', 10000000)]
            for year in range(10):
                decline_factor = (1 - temp_context.get('decline_rate', 0.08)) ** year
                cash_flows.append(annual_net_cash * decline_factor)
            
            # Calculate NPV
            npv_10 = npf.npv(0.10, cash_flows)
            npv_15 = npf.npv(0.15, cash_flows)
            
            try:
                irr = npf.irr(cash_flows)
                irr_percent = f"{irr:.1%}" if not np.isnan(irr) else "N/A"
            except:
                irr_percent = "N/A"
                
            gas_sensitivity_data.append({
                'gas_price': gas_price,
                'npv_10': npv_10,
                'npv_15': npv_15,
                'irr': irr_percent
            })
        
        # Generate gas price sensitivity HTML table
        gas_table_html = """
        <table class="sensitivity-table" style="border-collapse: collapse; width: 100%; margin: 20px 0;">
            <caption style="font-weight: bold; margin-bottom: 10px;">Gas Price Sensitivity Analysis</caption>
            <thead>
                <tr style="background-color: #f0f0f0;">
                    <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">Gas Price ($/mcf)</th>
                    <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">NPV @ 10%</th>
                    <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">NPV @ 15%</th>
                    <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">IRR</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for row in gas_sensitivity_data:
            npv_10_color = "green" if row['npv_10'] > 0 else "red"
            npv_15_color = "green" if row['npv_15'] > 0 else "red"
            
            gas_table_html += f"""
                <tr>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">${row['gas_price']:.2f}</td>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: right; color: {npv_10_color};">${row['npv_10']:,.0f}</td>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: right; color: {npv_15_color};">${row['npv_15']:,.0f}</td>
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">{row['irr']}</td>
                </tr>
            """
        
        gas_table_html += """
            </tbody>
        </table>
        """
        
        tables['gas_price_sensitivity'] = gas_table_html
        
        # Combined scenario analysis table (oil vs gas price matrix)
        oil_scenarios = [60, 75, 90]
        gas_scenarios = [2.5, 3.5, 4.5]
        
        matrix_table_html = """
        <table class="sensitivity-matrix" style="border-collapse: collapse; width: 100%; margin: 20px 0;">
            <caption style="font-weight: bold; margin-bottom: 10px;">NPV Scenario Matrix (@ 10% Discount Rate)</caption>
            <thead>
                <tr style="background-color: #f0f0f0;">
                    <th style="border: 1px solid #ccc; padding: 10px;">Oil Price / Gas Price</th>
        """
        
        for gas_price in gas_scenarios:
            matrix_table_html += f'<th style="border: 1px solid #ccc; padding: 10px; text-align: center;">${gas_price:.1f}/mcf</th>'
        
        matrix_table_html += """
                </tr>
            </thead>
            <tbody>
        """
        
        for oil_price in oil_scenarios:
            matrix_table_html += f"""
                <tr>
                    <td style="border: 1px solid #ccc; padding: 8px; font-weight: bold; background-color: #f8f8f8;">${oil_price}/bbl</td>
            """
            
            for gas_price in gas_scenarios:
                # Calculate NPV for this combination
                annual_oil_revenue = self.economic_context.get('annual_oil_bbl', 100000) * oil_price
                annual_gas_revenue = self.economic_context.get('annual_gas_mcf', 500000) * gas_price
                annual_revenue = annual_oil_revenue + annual_gas_revenue
                annual_costs = self.economic_context.get('operating_costs', 2500000)
                annual_net_cash = annual_revenue - annual_costs
                
                cash_flows = [-self.economic_context.get('initial_capex', 10000000)]
                for year in range(10):
                    decline_factor = (1 - self.economic_context.get('decline_rate', 0.08)) ** year
                    cash_flows.append(annual_net_cash * decline_factor)
                
                npv = npf.npv(0.10, cash_flows)
                npv_color = "green" if npv > 0 else "red"
                
                matrix_table_html += f"""
                    <td style="border: 1px solid #ccc; padding: 8px; text-align: right; color: {npv_color};">${npv:,.0f}</td>
                """
            
            matrix_table_html += "</tr>"
        
        matrix_table_html += """
            </tbody>
        </table>
        """
        
        tables['scenario_matrix'] = matrix_table_html
        
        return tables