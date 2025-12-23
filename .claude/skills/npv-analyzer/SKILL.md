---
name: npv-analyzer
description: Perform NPV analysis and economic evaluation for oil & gas assets. Use for cash flow modeling, price scenario analysis, working interest calculations, and financial metrics (IRR, payback, NPV) for field development projects.
---

# NPV Analyzer

Perform comprehensive Net Present Value (NPV) analysis and economic evaluation for oil & gas development projects, including cash flow modeling, price scenarios, and financial metrics.

## When to Use

- Calculating NPV for field development projects
- Modeling cash flows with production forecasts
- Running oil/gas price scenario analysis (low/mid/high)
- Applying working interest and royalty calculations
- Evaluating different development types (subsea, platform, FPSO)
- Computing IRR, payback period, and profitability index
- Comparing economic outcomes across multiple scenarios

## Core Pattern

```
Production Forecast → Price Assumptions → Cash Flow Model → Discount → Metrics
```

## Implementation

### Data Models

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Dict, Tuple
from enum import Enum
import numpy as np
import pandas as pd

class DevelopmentType(Enum):
    """Field development concepts."""
    SUBSEA_TIEBACK = "subsea_tieback"
    FIXED_PLATFORM = "fixed_platform"
    FPSO = "fpso"
    SPAR = "spar"
    TLP = "tlp"
    SEMI = "semi_submersible"

class PriceScenario(Enum):
    """Oil/gas price scenarios."""
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    STRIP = "strip"  # Forward curve prices
    CUSTOM = "custom"

@dataclass
class PriceAssumptions:
    """Oil and gas price assumptions."""
    scenario: PriceScenario = PriceScenario.MID
    oil_price_usd_bbl: float = 70.0
    gas_price_usd_mmbtu: float = 3.50
    ngl_price_usd_bbl: float = 35.0

    # Price escalation
    annual_escalation_pct: float = 2.0

    # Price deck for forward curve
    price_deck: Optional[Dict[int, Tuple[float, float]]] = None  # year: (oil, gas)

    def get_prices(self, year: int, base_year: int = None) -> Tuple[float, float]:
        """Get escalated prices for a specific year."""
        if self.price_deck and year in self.price_deck:
            return self.price_deck[year]

        base_year = base_year or date.today().year
        years_forward = year - base_year

        escalation = (1 + self.annual_escalation_pct / 100) ** years_forward
        oil_price = self.oil_price_usd_bbl * escalation
        gas_price = self.gas_price_usd_mmbtu * escalation

        return oil_price, gas_price

@dataclass
class FiscalTerms:
    """Fiscal and ownership terms."""
    working_interest: float = 1.0  # Fraction (0-1)
    net_revenue_interest: float = 0.875  # After royalty
    royalty_rate: float = 0.125  # 12.5% federal royalty
    state_severance_tax: float = 0.0  # Varies by state
    federal_income_tax: float = 0.21  # Corporate rate
    ad_valorem_tax: float = 0.0

    # Cost recovery (for PSC contracts)
    cost_recovery_limit: float = 1.0  # 100% for typical US
    profit_oil_share: float = 1.0  # 100% for typical US

    def net_revenue_factor(self) -> float:
        """Calculate combined net revenue factor."""
        return self.working_interest * self.net_revenue_interest

@dataclass
class CapexSchedule:
    """Capital expenditure schedule."""
    drilling_per_well: float = 0.0  # USD millions
    completion_per_well: float = 0.0
    facilities: float = 0.0
    subsea_equipment: float = 0.0
    pipeline: float = 0.0
    other_capex: float = 0.0

    # Timing (years from sanction)
    schedule: Dict[int, float] = field(default_factory=dict)  # year: capex

    @property
    def total_capex(self) -> float:
        """Total capital expenditure."""
        return (self.drilling_per_well + self.completion_per_well +
                self.facilities + self.subsea_equipment +
                self.pipeline + self.other_capex)

@dataclass
class OpexAssumptions:
    """Operating expenditure assumptions."""
    fixed_opex_usd_year: float = 0.0  # Annual fixed costs
    variable_opex_usd_boe: float = 0.0  # Per BOE
    workover_budget: float = 0.0  # Annual workover allowance
    insurance: float = 0.0
    g_and_a: float = 0.0  # General & administrative

    # Abandonment
    abandonment_cost: float = 0.0
    abandonment_year: Optional[int] = None

@dataclass
class ProductionForecast:
    """Production forecast by year."""
    year: int
    oil_mbbls: float = 0.0  # Thousand barrels
    gas_mmcf: float = 0.0  # Million cubic feet
    ngl_mbbls: float = 0.0
    water_mbbls: float = 0.0

    @property
    def boe(self) -> float:
        """Barrels of oil equivalent (6:1 gas)."""
        return self.oil_mbbls + self.ngl_mbbls + (self.gas_mmcf / 6.0)

    @property
    def gas_mmbtu(self) -> float:
        """Gas in MMBTU (assuming 1 MCF = 1 MMBTU)."""
        return self.gas_mmcf * 1000  # Convert MMCF to MMBTU

@dataclass
class CashFlowYear:
    """Annual cash flow calculation."""
    year: int

    # Revenue
    gross_oil_revenue: float = 0.0
    gross_gas_revenue: float = 0.0
    gross_ngl_revenue: float = 0.0
    total_gross_revenue: float = 0.0
    net_revenue: float = 0.0

    # Costs
    capex: float = 0.0
    opex: float = 0.0
    severance_tax: float = 0.0
    ad_valorem_tax: float = 0.0
    abandonment: float = 0.0

    # Taxes
    taxable_income: float = 0.0
    income_tax: float = 0.0

    # Cash flows
    before_tax_cash_flow: float = 0.0
    after_tax_cash_flow: float = 0.0
    cumulative_cash_flow: float = 0.0
    discounted_cash_flow: float = 0.0
```

### NPV Calculator

```python
from typing import List, Dict, Optional
import numpy as np
import numpy_financial as npf

class NPVCalculator:
    """
    Calculate NPV and related economic metrics for oil & gas projects.
    """

    def __init__(self,
                 production: List[ProductionForecast],
                 prices: PriceAssumptions,
                 fiscal: FiscalTerms,
                 capex: CapexSchedule,
                 opex: OpexAssumptions,
                 discount_rate: float = 0.10):
        """
        Initialize NPV calculator.

        Args:
            production: List of annual production forecasts
            prices: Price assumptions
            fiscal: Fiscal and ownership terms
            capex: Capital expenditure schedule
            opex: Operating expenditure assumptions
            discount_rate: Annual discount rate (default 10%)
        """
        self.production = sorted(production, key=lambda x: x.year)
        self.prices = prices
        self.fiscal = fiscal
        self.capex = capex
        self.opex = opex
        self.discount_rate = discount_rate

        self._cash_flows: Optional[List[CashFlowYear]] = None
        self._base_year: Optional[int] = None

    @property
    def base_year(self) -> int:
        """Get or set base year for discounting."""
        if self._base_year is None:
            self._base_year = min(p.year for p in self.production)
        return self._base_year

    @base_year.setter
    def base_year(self, value: int):
        self._base_year = value
        self._cash_flows = None  # Reset calculations

    def calculate_cash_flows(self) -> List[CashFlowYear]:
        """Calculate annual cash flows."""
        if self._cash_flows is not None:
            return self._cash_flows

        cash_flows = []
        cumulative = 0.0

        for prod in self.production:
            cf = CashFlowYear(year=prod.year)

            # Get prices for year
            oil_price, gas_price = self.prices.get_prices(prod.year, self.base_year)
            ngl_price = self.prices.ngl_price_usd_bbl * (
                (1 + self.prices.annual_escalation_pct / 100) **
                (prod.year - self.base_year)
            )

            # Gross revenue (in thousands USD, since production in Mbbls/MMCF)
            cf.gross_oil_revenue = prod.oil_mbbls * oil_price * 1000
            cf.gross_gas_revenue = prod.gas_mmbtu * gas_price / 1000  # MMBTU to $ thousands
            cf.gross_ngl_revenue = prod.ngl_mbbls * ngl_price * 1000
            cf.total_gross_revenue = (cf.gross_oil_revenue +
                                     cf.gross_gas_revenue +
                                     cf.gross_ngl_revenue)

            # Net revenue (apply WI and NRI)
            cf.net_revenue = cf.total_gross_revenue * self.fiscal.net_revenue_factor()

            # Capital expenditure
            cf.capex = self.capex.schedule.get(prod.year, 0.0) * 1e6  # Convert to $

            # Operating expenditure
            cf.opex = (
                self.opex.fixed_opex_usd_year +
                self.opex.variable_opex_usd_boe * prod.boe * 1000 +
                self.opex.workover_budget +
                self.opex.insurance +
                self.opex.g_and_a
            )

            # Abandonment
            if (self.opex.abandonment_year and
                prod.year == self.opex.abandonment_year):
                cf.abandonment = self.opex.abandonment_cost

            # Severance tax (on gross revenue before NRI)
            cf.severance_tax = (cf.total_gross_revenue *
                               self.fiscal.working_interest *
                               self.fiscal.state_severance_tax)

            # Ad valorem tax
            cf.ad_valorem_tax = (cf.total_gross_revenue *
                                self.fiscal.working_interest *
                                self.fiscal.ad_valorem_tax)

            # Before tax cash flow
            cf.before_tax_cash_flow = (cf.net_revenue -
                                       cf.capex -
                                       cf.opex -
                                       cf.severance_tax -
                                       cf.ad_valorem_tax -
                                       cf.abandonment)

            # Taxable income (simplified - no DD&A or intangible drilling)
            cf.taxable_income = max(0, cf.before_tax_cash_flow)
            cf.income_tax = cf.taxable_income * self.fiscal.federal_income_tax

            # After tax cash flow
            cf.after_tax_cash_flow = cf.before_tax_cash_flow - cf.income_tax

            # Cumulative cash flow
            cumulative += cf.after_tax_cash_flow
            cf.cumulative_cash_flow = cumulative

            # Discounted cash flow
            years_from_base = prod.year - self.base_year
            discount_factor = 1 / (1 + self.discount_rate) ** years_from_base
            cf.discounted_cash_flow = cf.after_tax_cash_flow * discount_factor

            cash_flows.append(cf)

        self._cash_flows = cash_flows
        return cash_flows

    def npv(self) -> float:
        """Calculate Net Present Value."""
        cash_flows = self.calculate_cash_flows()
        return sum(cf.discounted_cash_flow for cf in cash_flows)

    def irr(self) -> Optional[float]:
        """Calculate Internal Rate of Return."""
        cash_flows = self.calculate_cash_flows()
        cf_values = [cf.after_tax_cash_flow for cf in cash_flows]

        try:
            return npf.irr(cf_values)
        except:
            return None

    def payback_period(self) -> Optional[float]:
        """Calculate payback period in years."""
        cash_flows = self.calculate_cash_flows()

        for i, cf in enumerate(cash_flows):
            if cf.cumulative_cash_flow >= 0:
                if i == 0:
                    return 0.0

                # Interpolate
                prev_cf = cash_flows[i - 1]
                fraction = (-prev_cf.cumulative_cash_flow /
                           (cf.cumulative_cash_flow - prev_cf.cumulative_cash_flow))
                return (cf.year - cash_flows[0].year - 1) + fraction

        return None  # Never pays back

    def discounted_payback(self) -> Optional[float]:
        """Calculate discounted payback period."""
        cash_flows = self.calculate_cash_flows()
        cumulative_dcf = 0.0

        for i, cf in enumerate(cash_flows):
            cumulative_dcf += cf.discounted_cash_flow

            if cumulative_dcf >= 0:
                if i == 0:
                    return 0.0

                prev_cumulative = cumulative_dcf - cf.discounted_cash_flow
                fraction = (-prev_cumulative / cf.discounted_cash_flow)
                return (cf.year - cash_flows[0].year - 1) + fraction

        return None

    def profitability_index(self) -> float:
        """Calculate profitability index (PI = NPV / Investment + 1)."""
        cash_flows = self.calculate_cash_flows()
        total_investment = sum(cf.capex for cf in cash_flows)

        if total_investment == 0:
            return float('inf')

        return (self.npv() / total_investment) + 1

    def investment_efficiency(self) -> float:
        """Calculate investment efficiency (NPV per $ invested)."""
        cash_flows = self.calculate_cash_flows()
        total_investment = sum(cf.capex for cf in cash_flows)

        if total_investment == 0:
            return float('inf')

        return self.npv() / total_investment

    def breakeven_price(self, commodity: str = 'oil',
                        tolerance: float = 0.01) -> Optional[float]:
        """
        Calculate breakeven price for NPV = 0.

        Args:
            commodity: 'oil' or 'gas'
            tolerance: NPV tolerance for convergence
        """
        from scipy.optimize import brentq

        original_prices = self.prices

        def npv_at_price(price):
            if commodity == 'oil':
                self.prices = PriceAssumptions(
                    oil_price_usd_bbl=price,
                    gas_price_usd_mmbtu=original_prices.gas_price_usd_mmbtu
                )
            else:
                self.prices = PriceAssumptions(
                    oil_price_usd_bbl=original_prices.oil_price_usd_bbl,
                    gas_price_usd_mmbtu=price
                )
            self._cash_flows = None
            return self.npv()

        try:
            # Search between $10 and $200 for oil, $1 and $20 for gas
            if commodity == 'oil':
                breakeven = brentq(npv_at_price, 10, 200)
            else:
                breakeven = brentq(npv_at_price, 1, 20)
        except:
            breakeven = None
        finally:
            self.prices = original_prices
            self._cash_flows = None

        return breakeven

    def to_dataframe(self) -> pd.DataFrame:
        """Export cash flows to DataFrame."""
        cash_flows = self.calculate_cash_flows()

        data = []
        for cf in cash_flows:
            data.append({
                'year': cf.year,
                'gross_revenue': cf.total_gross_revenue,
                'net_revenue': cf.net_revenue,
                'capex': cf.capex,
                'opex': cf.opex,
                'taxes': cf.severance_tax + cf.ad_valorem_tax + cf.income_tax,
                'btcf': cf.before_tax_cash_flow,
                'atcf': cf.after_tax_cash_flow,
                'cumulative': cf.cumulative_cash_flow,
                'dcf': cf.discounted_cash_flow
            })

        return pd.DataFrame(data)

    def summary(self) -> Dict:
        """Generate summary of economic metrics."""
        cash_flows = self.calculate_cash_flows()

        return {
            'npv_mm': self.npv() / 1e6,
            'irr_pct': (self.irr() or 0) * 100,
            'payback_years': self.payback_period(),
            'discounted_payback_years': self.discounted_payback(),
            'profitability_index': self.profitability_index(),
            'investment_efficiency': self.investment_efficiency(),
            'total_capex_mm': sum(cf.capex for cf in cash_flows) / 1e6,
            'total_opex_mm': sum(cf.opex for cf in cash_flows) / 1e6,
            'total_revenue_mm': sum(cf.net_revenue for cf in cash_flows) / 1e6,
            'cumulative_production_mmboe': sum(p.boe for p in self.production) / 1000,
            'discount_rate_pct': self.discount_rate * 100
        }
```

### Scenario Analyzer

```python
from typing import List, Dict
from dataclasses import replace
import pandas as pd

class ScenarioAnalyzer:
    """
    Run multiple NPV scenarios with different price assumptions.
    """

    # Standard price scenarios
    PRICE_SCENARIOS = {
        PriceScenario.LOW: PriceAssumptions(
            scenario=PriceScenario.LOW,
            oil_price_usd_bbl=50.0,
            gas_price_usd_mmbtu=2.50
        ),
        PriceScenario.MID: PriceAssumptions(
            scenario=PriceScenario.MID,
            oil_price_usd_bbl=70.0,
            gas_price_usd_mmbtu=3.50
        ),
        PriceScenario.HIGH: PriceAssumptions(
            scenario=PriceScenario.HIGH,
            oil_price_usd_bbl=90.0,
            gas_price_usd_mmbtu=5.00
        )
    }

    def __init__(self,
                 production: List[ProductionForecast],
                 fiscal: FiscalTerms,
                 capex: CapexSchedule,
                 opex: OpexAssumptions,
                 discount_rate: float = 0.10):
        """Initialize scenario analyzer."""
        self.production = production
        self.fiscal = fiscal
        self.capex = capex
        self.opex = opex
        self.discount_rate = discount_rate

    def run_price_scenarios(self) -> pd.DataFrame:
        """Run standard price scenarios and compare results."""
        results = []

        for scenario, prices in self.PRICE_SCENARIOS.items():
            calc = NPVCalculator(
                production=self.production,
                prices=prices,
                fiscal=self.fiscal,
                capex=self.capex,
                opex=self.opex,
                discount_rate=self.discount_rate
            )

            summary = calc.summary()
            summary['scenario'] = scenario.value
            summary['oil_price'] = prices.oil_price_usd_bbl
            summary['gas_price'] = prices.gas_price_usd_mmbtu
            results.append(summary)

        return pd.DataFrame(results)

    def sensitivity_analysis(self,
                            base_prices: PriceAssumptions,
                            variable: str,
                            range_pct: float = 0.30,
                            steps: int = 11) -> pd.DataFrame:
        """
        Run sensitivity analysis on a single variable.

        Args:
            base_prices: Base case prices
            variable: Variable to vary ('oil_price', 'gas_price', 'capex', 'opex', 'discount_rate')
            range_pct: Range as percentage of base value
            steps: Number of steps
        """
        results = []

        # Get base value
        if variable == 'oil_price':
            base_value = base_prices.oil_price_usd_bbl
        elif variable == 'gas_price':
            base_value = base_prices.gas_price_usd_mmbtu
        elif variable == 'capex':
            base_value = 1.0  # Multiplier
        elif variable == 'opex':
            base_value = 1.0  # Multiplier
        elif variable == 'discount_rate':
            base_value = self.discount_rate
        else:
            raise ValueError(f"Unknown variable: {variable}")

        # Generate range
        min_val = base_value * (1 - range_pct)
        max_val = base_value * (1 + range_pct)
        values = np.linspace(min_val, max_val, steps)

        for val in values:
            # Modify parameter
            if variable == 'oil_price':
                prices = replace(base_prices, oil_price_usd_bbl=val)
                capex = self.capex
                opex = self.opex
                discount = self.discount_rate
            elif variable == 'gas_price':
                prices = replace(base_prices, gas_price_usd_mmbtu=val)
                capex = self.capex
                opex = self.opex
                discount = self.discount_rate
            elif variable == 'capex':
                prices = base_prices
                # Scale capex schedule
                capex = replace(self.capex,
                               schedule={y: c * val for y, c in self.capex.schedule.items()})
                opex = self.opex
                discount = self.discount_rate
            elif variable == 'opex':
                prices = base_prices
                capex = self.capex
                opex = replace(self.opex,
                              fixed_opex_usd_year=self.opex.fixed_opex_usd_year * val,
                              variable_opex_usd_boe=self.opex.variable_opex_usd_boe * val)
                discount = self.discount_rate
            elif variable == 'discount_rate':
                prices = base_prices
                capex = self.capex
                opex = self.opex
                discount = val

            # Calculate NPV
            calc = NPVCalculator(
                production=self.production,
                prices=prices,
                fiscal=self.fiscal,
                capex=capex,
                opex=opex,
                discount_rate=discount
            )

            results.append({
                'variable': variable,
                'value': val,
                'pct_change': (val - base_value) / base_value * 100,
                'npv_mm': calc.npv() / 1e6,
                'irr_pct': (calc.irr() or 0) * 100
            })

        return pd.DataFrame(results)

    def tornado_chart_data(self, base_prices: PriceAssumptions,
                          range_pct: float = 0.20) -> pd.DataFrame:
        """Generate data for tornado sensitivity chart."""
        variables = ['oil_price', 'gas_price', 'capex', 'opex', 'discount_rate']
        results = []

        # Calculate base case
        base_calc = NPVCalculator(
            production=self.production,
            prices=base_prices,
            fiscal=self.fiscal,
            capex=self.capex,
            opex=self.opex,
            discount_rate=self.discount_rate
        )
        base_npv = base_calc.npv() / 1e6

        for var in variables:
            sensitivity = self.sensitivity_analysis(base_prices, var, range_pct, steps=3)
            low = sensitivity.iloc[0]['npv_mm']
            high = sensitivity.iloc[-1]['npv_mm']

            results.append({
                'variable': var,
                'low_npv': low,
                'high_npv': high,
                'base_npv': base_npv,
                'range': abs(high - low)
            })

        return pd.DataFrame(results).sort_values('range', ascending=False)
```

### Report Generator

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

class NPVReportGenerator:
    """Generate interactive HTML reports for NPV analysis."""

    def __init__(self, calculator: NPVCalculator,
                 scenario_analyzer: ScenarioAnalyzer = None):
        """Initialize report generator."""
        self.calculator = calculator
        self.analyzer = scenario_analyzer

    def generate_report(self, output_path: Path, project_name: str = "Project"):
        """Generate comprehensive NPV analysis report."""
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Annual Cash Flows',
                'Cumulative Cash Flow',
                'Price Scenario NPV',
                'Sensitivity Analysis',
                'Production Profile',
                'Revenue Breakdown'
            ),
            vertical_spacing=0.10
        )

        cf_df = self.calculator.to_dataframe()

        # Annual cash flows
        fig.add_trace(
            go.Bar(x=cf_df['year'], y=cf_df['atcf']/1e6,
                   name='After-Tax CF ($MM)', marker_color='green'),
            row=1, col=1
        )
        fig.add_trace(
            go.Bar(x=cf_df['year'], y=-cf_df['capex']/1e6,
                   name='CAPEX ($MM)', marker_color='red'),
            row=1, col=1
        )

        # Cumulative cash flow
        fig.add_trace(
            go.Scatter(x=cf_df['year'], y=cf_df['cumulative']/1e6,
                      name='Cumulative CF', fill='tozeroy',
                      line=dict(color='blue')),
            row=1, col=2
        )
        fig.add_hline(y=0, line_dash='dash', line_color='gray', row=1, col=2)

        # Price scenarios
        if self.analyzer:
            scenarios = self.analyzer.run_price_scenarios()
            fig.add_trace(
                go.Bar(x=scenarios['scenario'], y=scenarios['npv_mm'],
                       name='NPV by Scenario',
                       marker_color=['#d62728', '#2ca02c', '#1f77b4']),
                row=2, col=1
            )

            # Tornado chart
            tornado = self.analyzer.tornado_chart_data(self.calculator.prices)
            for _, row_data in tornado.iterrows():
                fig.add_trace(
                    go.Bar(
                        y=[row_data['variable']],
                        x=[row_data['high_npv'] - row_data['base_npv']],
                        orientation='h',
                        name=f"{row_data['variable']} High",
                        marker_color='green',
                        showlegend=False
                    ),
                    row=2, col=2
                )
                fig.add_trace(
                    go.Bar(
                        y=[row_data['variable']],
                        x=[row_data['low_npv'] - row_data['base_npv']],
                        orientation='h',
                        name=f"{row_data['variable']} Low",
                        marker_color='red',
                        showlegend=False
                    ),
                    row=2, col=2
                )

        # Production profile
        prod_df = pd.DataFrame([
            {'year': p.year, 'oil': p.oil_mbbls, 'gas': p.gas_mmcf/6, 'ngl': p.ngl_mbbls}
            for p in self.calculator.production
        ])

        fig.add_trace(
            go.Bar(x=prod_df['year'], y=prod_df['oil'],
                   name='Oil (Mbbls)', marker_color='green'),
            row=3, col=1
        )
        fig.add_trace(
            go.Bar(x=prod_df['year'], y=prod_df['gas'],
                   name='Gas (BOE Mbbls)', marker_color='red'),
            row=3, col=1
        )

        # Revenue breakdown
        cash_flows = self.calculator.calculate_cash_flows()
        total_oil_rev = sum(cf.gross_oil_revenue for cf in cash_flows)
        total_gas_rev = sum(cf.gross_gas_revenue for cf in cash_flows)
        total_ngl_rev = sum(cf.gross_ngl_revenue for cf in cash_flows)

        fig.add_trace(
            go.Pie(
                labels=['Oil', 'Gas', 'NGL'],
                values=[total_oil_rev, total_gas_rev, total_ngl_rev],
                marker_colors=['green', 'red', 'orange']
            ),
            row=3, col=2
        )

        # Summary metrics annotation
        summary = self.calculator.summary()
        summary_text = (
            f"<b>Economic Summary</b><br>"
            f"NPV (10%): ${summary['npv_mm']:.1f}MM<br>"
            f"IRR: {summary['irr_pct']:.1f}%<br>"
            f"Payback: {summary['payback_years']:.1f} years<br>"
            f"PI: {summary['profitability_index']:.2f}"
        )

        fig.add_annotation(
            text=summary_text,
            xref='paper', yref='paper',
            x=1.02, y=0.98,
            showarrow=False,
            font=dict(size=12),
            align='left',
            bgcolor='white',
            bordercolor='gray'
        )

        fig.update_layout(
            height=1100,
            title_text=f"{project_name} - NPV Analysis",
            showlegend=True,
            barmode='relative'
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_path))

        return output_path
```

## YAML Configuration

### Project Configuration

```yaml
# config/npv_analysis.yaml

metadata:
  project_name: "Lower Tertiary Development"
  analyst: "Engineering Team"
  date: "2024-01-15"
  version: "1.0"

economics:
  discount_rate: 0.10  # 10%
  base_year: 2024
  project_life: 25  # years

prices:
  scenario: mid  # low, mid, high, strip
  oil_price_usd_bbl: 70.0
  gas_price_usd_mmbtu: 3.50
  ngl_price_usd_bbl: 35.0
  annual_escalation_pct: 2.0

fiscal:
  working_interest: 0.50  # 50% WI
  net_revenue_interest: 0.875  # 87.5% NRI (12.5% royalty)
  royalty_rate: 0.125
  state_severance_tax: 0.0  # Federal waters
  federal_income_tax: 0.21
  ad_valorem_tax: 0.0

capex:
  drilling_per_well: 120.0  # $MM per well
  completion_per_well: 40.0
  facilities: 500.0
  subsea_equipment: 300.0
  pipeline: 150.0
  other_capex: 50.0
  schedule:  # year: amount ($MM)
    2024: 200.0
    2025: 600.0
    2026: 360.0

opex:
  fixed_opex_usd_year: 25000000  # $25MM/year
  variable_opex_usd_boe: 8.0  # $8/BOE
  workover_budget: 5000000
  insurance: 3000000
  g_and_a: 2000000
  abandonment_cost: 150000000
  abandonment_year: 2049

production:
  source: "file"  # file, manual, decline_curve
  file_path: "data/production_forecast.csv"

  # Or manual entry:
  # manual:
  #   - year: 2027
  #     oil_mbbls: 5000
  #     gas_mmcf: 3000
  #   - year: 2028
  #     oil_mbbls: 8000
  #     gas_mmcf: 5000

output:
  cash_flow_csv: "data/results/cash_flows.csv"
  summary_json: "data/results/summary.json"
  report_html: "reports/npv_analysis.html"
```

### Scenario Comparison

```yaml
# config/scenario_comparison.yaml

scenarios:
  - name: "Base Case"
    oil_price: 70
    gas_price: 3.50
    capex_multiplier: 1.0

  - name: "Low Price"
    oil_price: 50
    gas_price: 2.50
    capex_multiplier: 1.0

  - name: "High Price"
    oil_price: 90
    gas_price: 5.00
    capex_multiplier: 1.0

  - name: "Cost Overrun"
    oil_price: 70
    gas_price: 3.50
    capex_multiplier: 1.25

  - name: "Fast Payout"
    oil_price: 80
    gas_price: 4.00
    capex_multiplier: 0.90

analysis:
  run_sensitivity: true
  sensitivity_range_pct: 0.30
  tornado_chart: true

output:
  comparison_csv: "data/results/scenario_comparison.csv"
  report_html: "reports/scenario_comparison.html"
```

## CLI Usage

```bash
# Run NPV analysis
python -m npv_analyzer run --config config/npv_analysis.yaml

# Quick NPV calculation
python -m npv_analyzer calculate \
    --production data/forecast.csv \
    --oil-price 70 \
    --gas-price 3.50 \
    --discount-rate 0.10

# Run scenario comparison
python -m npv_analyzer scenarios --config config/scenario_comparison.yaml

# Calculate breakeven price
python -m npv_analyzer breakeven --config config/npv_analysis.yaml --commodity oil

# Generate sensitivity tornado
python -m npv_analyzer sensitivity --config config/npv_analysis.yaml --range 0.30
```

## Usage Examples

### Example 1: Simple NPV Calculation

```python
from npv_analyzer import (
    NPVCalculator, ProductionForecast, PriceAssumptions,
    FiscalTerms, CapexSchedule, OpexAssumptions
)

# Define production forecast
production = [
    ProductionForecast(year=2027, oil_mbbls=3000, gas_mmcf=2000),
    ProductionForecast(year=2028, oil_mbbls=8000, gas_mmcf=5000),
    ProductionForecast(year=2029, oil_mbbls=10000, gas_mmcf=6500),
    ProductionForecast(year=2030, oil_mbbls=9000, gas_mmcf=6000),
    ProductionForecast(year=2031, oil_mbbls=7500, gas_mmcf=5000),
]

# Define economics
prices = PriceAssumptions(oil_price_usd_bbl=70, gas_price_usd_mmbtu=3.50)
fiscal = FiscalTerms(working_interest=0.50, net_revenue_interest=0.875)
capex = CapexSchedule(schedule={2024: 200, 2025: 600, 2026: 360})
opex = OpexAssumptions(fixed_opex_usd_year=25e6, variable_opex_usd_boe=8.0)

# Calculate NPV
calc = NPVCalculator(production, prices, fiscal, capex, opex, discount_rate=0.10)

print(f"NPV @ 10%: ${calc.npv()/1e6:.1f}MM")
print(f"IRR: {calc.irr()*100:.1f}%")
print(f"Payback: {calc.payback_period():.1f} years")
```

### Example 2: Scenario Analysis

```python
from npv_analyzer import ScenarioAnalyzer, NPVReportGenerator

# Create analyzer
analyzer = ScenarioAnalyzer(production, fiscal, capex, opex)

# Run price scenarios
scenarios = analyzer.run_price_scenarios()
print("\nPrice Scenario Results:")
print(scenarios[['scenario', 'npv_mm', 'irr_pct', 'payback_years']])

# Generate tornado chart data
tornado = analyzer.tornado_chart_data(prices)
print("\nSensitivity Ranking:")
print(tornado[['variable', 'range']])

# Generate report
reporter = NPVReportGenerator(calc, analyzer)
reporter.generate_report(
    Path("reports/npv_report.html"),
    project_name="Lower Tertiary Development"
)
```

## Best Practices

### Model Setup
- Use consistent units throughout (USD, bbls, MCF)
- Validate production forecasts against reservoir studies
- Document all assumptions in YAML configs
- Version control economic parameters

### Sensitivity Analysis
- Always run multiple price scenarios
- Include cost and schedule sensitivities
- Identify breakeven prices for investment decisions
- Document uncertainty ranges

### Reporting
- Include summary metrics prominently
- Show cash flow timing clearly
- Compare against investment criteria (hurdle rate, payback limits)
- Archive analysis with assumptions

## Related Skills

- [bsee-data-extractor](../bsee-data-extractor/SKILL.md) - Production data for forecasts
- [engineering-report-generator](/mnt/github/workspace-hub/.claude/skills/development/engineering-report-generator/SKILL.md) - Report generation
- [data-pipeline-processor](/mnt/github/workspace-hub/.claude/skills/development/data-pipeline-processor/SKILL.md) - Data processing
