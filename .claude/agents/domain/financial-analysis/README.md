# Financial Analysis Expert Agent v3.0

## Overview

The Financial Analysis Expert Agent is a specialized AI assistant with comprehensive domain knowledge in investment analysis, corporate finance, risk management, and financial markets. This agent implements v3.0 principles while providing expert guidance across traditional finance, energy markets, and sustainable investing.

## Specialization: Financial Markets & Energy Economics
Domain expert in financial analysis, valuation, portfolio management, and energy finance

## Core Capabilities

### Financial Domains
- **Investment Analysis**: Equity research, fixed income, derivatives, portfolio optimization
- **Corporate Finance**: DCF valuation, M&A analysis, capital structure, financial planning
- **Risk Management**: VaR, stress testing, credit risk, operational risk assessment
- **Energy Finance**: Oil & gas economics, power markets, renewable project finance
- **Quantitative Finance**: Financial modeling, algorithmic strategies, statistical analysis
- **ESG Investing**: Climate risk, sustainable finance, green bonds, impact measurement

### Analysis Expertise
- **Valuation Methods**: DCF, comparables, precedent transactions, real options
- **Risk Metrics**: VaR, CVaR, Sharpe ratio, maximum drawdown, beta
- **Performance Analysis**: Attribution, benchmarking, risk-adjusted returns
- **Market Analysis**: Technical indicators, fundamental analysis, macro factors
- **Financial Modeling**: Excel, Python, Monte Carlo simulation, optimization

## Features

### Phased Document Processing (v3.0)
- **Phase 1: Discovery** - Financial document inventory and classification
- **Phase 2: Quality Assessment** - Data quality scoring and validation
- **Phase 3: Extraction** - Financial metrics and insights extraction
- **Phase 4: Synthesis** - Cross-source reconciliation and analysis
- **Phase 5: Validation** - Regulatory compliance and accuracy checks
- **Phase 6: Integration** - Knowledge base integration and updating

### Modular Management (v3.0)
- **Specialization Level**: financial-markets-energy
- **Context Optimization**: 16000 tokens
- **Refresh Priority**: high (market data daily)
- **Auto-Refresh**: Enabled (1-day interval for prices)

### Context Engineering (v2.0)
- **Layered Architecture**: Market data, fundamentals, technicals, regulations
- **Memory Management**: Trade history, portfolio positions, risk limits
- **RAG Optimization**: Financial document chunking, formula preservation
- **Duplicate Detection**: Price data deduplication, report versioning

## Structure
```
financial-analysis/
├── agent.yaml                 # Agent configuration
├── context/                   # Context management
│   ├── domain/               # Financial expertise
│   │   └── financial_expertise.md
│   ├── energy_markets.md     # Energy market knowledge
│   ├── repository/           # Code patterns
│   └── module/              # Module-specific docs
├── prompts/                 # Agent prompts
│   └── system_prompt.md    # Financial expert prompt
├── templates/               # Calculation templates
│   ├── analysis_template.yaml
│   └── financial_calculations.py
├── workflows/               # Analysis workflows
│   └── investment_analysis.yaml
├── documentation/           # API and guides
├── memory/                 # Learning storage
└── README.md               # This file
```

## Usage Examples

### Investment Analysis
```python
# Equity valuation
"Perform DCF valuation for XOM with 5-year projections"
"Compare P/E ratios of energy sector stocks"
"Calculate intrinsic value using dividend discount model"

# Portfolio optimization
"Optimize portfolio of 10 energy stocks for maximum Sharpe ratio"
"Calculate VaR for oil & gas portfolio at 95% confidence"
"Rebalance portfolio with ESG constraints"

# Risk assessment
"Stress test portfolio for $50 oil scenario"
"Calculate portfolio beta against S&P Energy index"
"Analyze correlation matrix for commodity exposures"
```

### Energy Finance
```python
# Project finance
"Model economics for 100MW solar project with PPA"
"Calculate LCOE for offshore wind farm"
"Evaluate IRR for LNG terminal investment"

# Commodity analysis
"Forecast WTI crude prices using futures curve"
"Analyze crack spread profitability"
"Calculate natural gas storage arbitrage opportunity"

# Market analysis
"Analyze impact of OPEC cuts on oil prices"
"Evaluate renewable energy subsidy changes"
"Model carbon credit price scenarios"
```

### Code Generation
```python
# Using the templates
from agents.financial_analysis.templates.financial_calculations import *

# DCF Valuation
fcf = [100, 110, 121, 133, 146]  # Million USD
valuation = dcf_valuation(fcf, 0.03, 0.10)
print(f"Enterprise Value: ${valuation['enterprise_value']:,.2f}M")

# Portfolio Optimization
returns_data = pd.DataFrame({...})  # Your return data
optimal = portfolio_optimization(returns_data)
print(f"Optimal Sharpe: {optimal['sharpe_ratio']:.2f}")

# Option Pricing
option = black_scholes(spot=100, strike=105, time_to_expiry=0.25,
                      risk_free_rate=0.05, volatility=0.2)
print(f"Option Price: ${option['price']:.2f}")
```

## Integration with WorldEnergyData

### Market Data Integration
- Real-time energy commodity prices
- Stock prices for energy companies
- Currency exchange rates
- Interest rate curves
- Credit spreads

### BSEE Data Analysis
- Production economics analysis
- Operating cost benchmarking
- Capital efficiency metrics
- Reserve valuation
- Decommissioning liabilities

### ESG Analytics
- Carbon footprint calculation
- Climate scenario analysis
- Transition risk assessment
- Green bond evaluation
- Sustainability reporting

## Key Files

- **Domain Knowledge**: `context/domain/financial_expertise.md`
- **System Prompt**: `prompts/system_prompt.md`
- **Calculations**: `templates/financial_calculations.py`
- **Agent Config**: `agent.yaml`

## Best Practices

### When Using This Agent

1. **Provide Context**: Include time periods, currencies, market conditions
2. **Specify Requirements**: Valuation methods, risk metrics, compliance standards
3. **Data Quality**: Verify sources, validate assumptions, document limitations
4. **Regulatory Compliance**: Consider GAAP/IFRS, SEC, Basel III, MiFID II

### Quality Standards
- Use current, verified market data
- Apply appropriate methodologies
- Include comprehensive risk assessment
- Follow regulatory standards
- Provide clear documentation

### Risk Warnings
- Past performance ≠ future results
- All investments carry risk
- Projections based on assumptions
- Market conditions change rapidly
- Regulatory changes impact returns

## Metrics
- **Specialization**: financial-markets-energy
- **Context Size**: 16000 tokens
- **Refresh Priority**: high
- **Update Frequency**: Daily (prices), Weekly (regulations)
- **Created**: 2025-08-25

---

*Enhanced Agent v3.0 - Comprehensive financial analysis with energy market specialization*
