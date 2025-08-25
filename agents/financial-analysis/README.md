# Financial Analysis Agent

## Overview

The Financial Analysis Agent is a specialized AI module designed for comprehensive financial analysis, energy economics, and market intelligence within the world energy data ecosystem.

## Core Capabilities

### Financial Analysis
- **Investment Evaluation**: NPV, IRR, LCOE calculations for energy projects
- **Risk Assessment**: Monte Carlo simulations, sensitivity analysis, scenario planning
- **Cost-Benefit Analysis**: Comprehensive evaluation of energy investments
- **Portfolio Optimization**: Multi-asset energy portfolio management

### Market Intelligence
- **Price Forecasting**: Oil, natural gas, and electricity price predictions
- **Market Trends**: Real-time analysis of energy commodity markets
- **Supply-Demand Modeling**: Energy market equilibrium analysis
- **Derivatives Analysis**: Energy futures, options, and swaps evaluation

### Economic Analysis
- **Energy Economics**: Sector-specific economic modeling
- **Regulatory Impact**: Financial implications of energy policies
- **Carbon Economics**: Carbon pricing and trading analysis
- **Renewable Energy Economics**: LCOE comparisons and grid parity analysis

## Usage

```python
# Example: Analyze an energy project investment
from agents.financial_analysis import FinancialAnalysisAgent

agent = FinancialAnalysisAgent()

project_data = {
    'capex': 100_000_000,  # $100M
    'opex_annual': 5_000_000,  # $5M/year
    'revenue_annual': 20_000_000,  # $20M/year
    'project_life': 25,  # years
    'discount_rate': 0.08  # 8%
}

analysis = agent.analyze_investment(project_data)
print(f"NPV: ${analysis['npv']:,.2f}")
print(f"IRR: {analysis['irr']:.2%}")
```

## Integration

The agent integrates with:
- **Internal Data**: Historical energy production, cost databases, project metrics
- **External APIs**: EIA, IEA, OPEC, financial market feeds
- **Workflows**: Automated reporting, forecasting, and analysis pipelines

## Configuration

Configure the agent through environment variables or the `agent.yaml` file.

---

*Version: 1.0.0 | Last Updated: 2025-08-25*
