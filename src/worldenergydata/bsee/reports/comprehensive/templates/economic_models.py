"""
Economic data models for comprehensive financial analysis
Contains dataclasses for revenue, cost, profitability, NPV, ROI, and forecasting
"""

from dataclasses import dataclass, field
from datetime import date

# Import dependencies - will be resolved at runtime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy_financial as npf

if TYPE_CHECKING:
    from ..hierarchical_aggregator import CostStructure, PriceDeck
    from ..models import ProductionMetrics


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
        return (
            self.oil_revenue
            + self.gas_revenue
            + self.ngl_revenue
            + self.water_revenue
            + self.other_revenue
        )

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
        return getattr(self, "_revenue_per_boe", 0.0)

    def set_production_volumes(
        self, oil_bbls: float, gas_mcf: float, ngl_bbls: float = 0.0
    ):
        """Set production volumes to calculate per-BOE metrics"""
        total_boe = oil_bbls + (gas_mcf / 6) + ngl_bbls
        if total_boe > 0:
            self._revenue_per_boe = self.total_revenue / total_boe
        else:
            self._revenue_per_boe = 0.0

    @classmethod
    def from_production(
        cls, production_data: Dict[str, float], price_deck: "PriceDeck"
    ) -> "RevenueBreakdown":
        """Create revenue breakdown from production data and price deck"""
        oil_revenue = production_data.get("oil_bbls", 0) * price_deck.oil_price
        gas_revenue = production_data.get("gas_mcf", 0) * price_deck.gas_price
        ngl_revenue = production_data.get("ngl_bbls", 0) * price_deck.ngl_price

        breakdown = cls(
            oil_revenue=oil_revenue, gas_revenue=gas_revenue, ngl_revenue=ngl_revenue
        )

        # Set production volumes for per-BOE calculations
        breakdown.set_production_volumes(
            production_data.get("oil_bbls", 0),
            production_data.get("gas_mcf", 0),
            production_data.get("ngl_bbls", 0),
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
        return (
            self.operating_costs
            + self.capital_costs
            + self.royalties
            + self.severance_tax
            + self.production_tax
            + self.transportation_costs
            + self.processing_costs
            + self.other_costs
        )

    @property
    def variable_costs(self) -> float:
        """Calculate variable costs (exclude CAPEX)"""
        return (
            self.operating_costs
            + self.royalties
            + self.severance_tax
            + self.production_tax
            + self.transportation_costs
            + self.processing_costs
        )

    @property
    def cost_per_boe(self) -> float:
        """Calculate cost per BOE (requires BOE to be set externally)"""
        return getattr(self, "_cost_per_boe", 0.0)

    def set_production_volumes(
        self, oil_bbls: float, gas_mcf: float, ngl_bbls: float = 0.0
    ):
        """Set production volumes to calculate per-BOE metrics"""
        total_boe = oil_bbls + (gas_mcf / 6) + ngl_bbls
        if total_boe > 0:
            self._cost_per_boe = self.total_costs / total_boe
        else:
            self._cost_per_boe = 0.0

    @classmethod
    def from_production(
        cls,
        production_data: Dict[str, float],
        revenue_data: Dict[str, float],
        cost_structure: "CostStructure",
    ) -> "CostAnalysis":
        """Create cost analysis from production data"""
        # Calculate BOE for operating costs
        oil_bbls = production_data.get("oil_bbls", 0)
        gas_mcf = production_data.get("gas_mcf", 0)
        ngl_bbls = production_data.get("ngl_bbls", 0)
        total_boe = oil_bbls + (gas_mcf / 6) + ngl_bbls

        # Calculate costs
        operating_costs = total_boe * cost_structure.operating_cost_per_bbl
        total_revenue = revenue_data.get("total_revenue", 0)
        royalties = total_revenue * cost_structure.royalty_rate
        severance_tax = total_revenue * cost_structure.severance_tax_rate

        analysis = cls(
            operating_costs=operating_costs,
            royalties=royalties,
            severance_tax=severance_tax,
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
    def from_components(
        cls, revenue_breakdown: RevenueBreakdown, cost_analysis: CostAnalysis
    ) -> "ProfitabilityMetrics":
        """Create profitability metrics from revenue and cost components"""
        gross_revenue = revenue_breakdown.total_revenue
        net_income = gross_revenue - cost_analysis.total_costs

        # Calculate margins
        profit_margin = (net_income / gross_revenue * 100) if gross_revenue > 0 else 0
        operating_margin = (
            ((gross_revenue - cost_analysis.variable_costs) / gross_revenue * 100)
            if gross_revenue > 0
            else 0
        )

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
            ebitda=ebitda,
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
        except Exception:
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
            return float("inf")
        return self.initial_investment / self.annual_net_income


@dataclass
class EconomicForecast:
    """Economic forecasting and projections"""

    def forecast_production(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_years: int = 5,
        decline_rate: float = 0.05,
    ) -> List[Dict[str, Any]]:
        """Forecast future production based on historical trends"""
        if not historical_data:
            return []

        # Get latest year data
        latest = historical_data[-1]
        forecasts = []

        for year in range(1, forecast_years + 1):
            forecast_year = latest["year"] + year

            # Apply decline rate
            oil_forecast = latest["oil_bbls"] * ((1 - decline_rate) ** year)
            gas_forecast = latest["gas_mcf"] * ((1 - decline_rate) ** year)

            forecasts.append(
                {
                    "year": forecast_year,
                    "oil_bbls": max(0, oil_forecast),
                    "gas_mcf": max(0, gas_forecast),
                }
            )

        return forecasts

    def forecast_revenue(
        self,
        production_forecast: List[Dict[str, Any]],
        price_deck: "PriceDeck",
        forecast_years: int = 5,
        price_escalation: float = 0.02,
    ) -> List[Dict[str, Any]]:
        """Forecast revenue with price escalation"""
        revenue_forecasts = []

        for i, prod_forecast in enumerate(production_forecast):
            # Apply price escalation
            escalated_oil_price = price_deck.oil_price * ((1 + price_escalation) ** i)
            escalated_gas_price = price_deck.gas_price * ((1 + price_escalation) ** i)

            oil_revenue = prod_forecast["oil_bbls"] * escalated_oil_price
            gas_revenue = prod_forecast["gas_mcf"] * escalated_gas_price
            total_revenue = oil_revenue + gas_revenue

            revenue_forecasts.append(
                {
                    "year": prod_forecast["year"],
                    "oil_revenue": oil_revenue,
                    "gas_revenue": gas_revenue,
                    "total_revenue": total_revenue,
                    "oil_price": escalated_oil_price,
                    "gas_price": escalated_gas_price,
                }
            )

        return revenue_forecasts


@dataclass
class SensitivityAnalysis:
    """Sensitivity analysis for key economic variables"""

    def analyze_oil_price_sensitivity(
        self, base_metrics: "ProductionMetrics", price_range: List[float]
    ) -> List[Dict[str, Any]]:
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
            npv_estimate = (
                net_income * 8
            )  # Simple 8x multiplier for 10-year NPV estimate

            sensitivity_results.append(
                {
                    "price_change_pct": price_change_pct,
                    "new_oil_price": new_oil_price,
                    "total_revenue": total_revenue,
                    "net_income": net_income,
                    "npv": npv_estimate,
                }
            )

        return sensitivity_results

    def analyze_production_sensitivity(
        self, base_metrics: "ProductionMetrics", volume_range: List[float]
    ) -> List[Dict[str, Any]]:
        """Analyze sensitivity to production volume changes"""
        sensitivity_results = []

        for volume_change_pct in volume_range:
            new_oil_production = base_metrics.oil_production_bbls * (
                1 + volume_change_pct / 100
            )
            new_gas_production = base_metrics.gas_production_mcf * (
                1 + volume_change_pct / 100
            )

            # Calculate new revenue and costs
            oil_revenue = new_oil_production * base_metrics.oil_price_usd
            gas_revenue = new_gas_production * base_metrics.gas_price_usd
            total_revenue = oil_revenue + gas_revenue

            # Costs scale with production
            variable_costs = base_metrics.operating_cost_usd * (
                1 + volume_change_pct / 100
            )
            net_income = total_revenue - variable_costs
            npv_estimate = net_income * 8

            sensitivity_results.append(
                {
                    "volume_change_pct": volume_change_pct,
                    "new_oil_production": new_oil_production,
                    "new_gas_production": new_gas_production,
                    "total_revenue": total_revenue,
                    "net_income": net_income,
                    "npv": npv_estimate,
                }
            )

        return sensitivity_results

    def analyze_cost_sensitivity(
        self, base_metrics: "ProductionMetrics", cost_range: List[float]
    ) -> List[Dict[str, Any]]:
        """Analyze sensitivity to operating cost changes"""
        sensitivity_results = []
        base_revenue = base_metrics.total_revenue()

        for cost_change_pct in cost_range:
            new_operating_cost = base_metrics.operating_cost_usd * (
                1 + cost_change_pct / 100
            )
            net_income = base_revenue - new_operating_cost
            npv_estimate = net_income * 8

            sensitivity_results.append(
                {
                    "cost_change_pct": cost_change_pct,
                    "new_operating_cost": new_operating_cost,
                    "net_income": net_income,
                    "npv": npv_estimate,
                }
            )

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
    def from_production_metrics(
        cls,
        production_metrics: "ProductionMetrics",
        price_deck: "PriceDeck",
        cost_structure: "CostStructure",
        entity_id: str = None,
        entity_type: str = "field",
    ) -> "EconomicAnalysis":
        """Create comprehensive economic analysis from production metrics"""

        # Extract production data
        production_data = {
            "oil_bbls": production_metrics.oil_production_bbls,
            "gas_mcf": production_metrics.gas_production_mcf,
            "ngl_bbls": 0.0,  # Would need to be added to ProductionMetrics
        }

        # Create revenue breakdown
        revenue_breakdown = RevenueBreakdown.from_production(
            production_data, price_deck
        )

        # Create cost analysis
        revenue_data = {"total_revenue": revenue_breakdown.total_revenue}
        cost_analysis = CostAnalysis.from_production(
            production_data, revenue_data, cost_structure
        )

        # Create profitability metrics
        profitability_metrics = ProfitabilityMetrics.from_components(
            revenue_breakdown, cost_analysis
        )

        return cls(
            entity_id=entity_id or production_metrics.entity_id or "unknown",
            entity_type=entity_type,
            analysis_date=date.today(),
            revenue_breakdown=revenue_breakdown,
            cost_analysis=cost_analysis,
            profitability_metrics=profitability_metrics,
        )
