# Financial Analysis Domain Expertise

## Core Competencies

### 1. Financial Markets & Instruments
- **Equity Markets**: Stock valuation, market analysis, sector rotation
- **Fixed Income**: Bond pricing, yield curves, duration, credit analysis
- **Derivatives**: Options, futures, swaps, structured products
- **Commodities**: Energy markets, precious metals, agricultural products
- **Foreign Exchange**: Currency pairs, carry trades, hedging strategies
- **Alternative Investments**: Private equity, hedge funds, real assets

### 2. Investment Analysis
- **Fundamental Analysis**: Financial statement analysis, ratio analysis, DCF modeling
- **Technical Analysis**: Chart patterns, indicators, momentum strategies
- **Quantitative Analysis**: Factor models, statistical arbitrage, algorithmic trading
- **Portfolio Management**: Asset allocation, risk management, performance attribution
- **Risk Assessment**: VaR, CVaR, stress testing, scenario analysis
- **ESG Investing**: Sustainable finance, impact investing, green bonds

### 3. Corporate Finance
- **Capital Structure**: Optimal leverage, cost of capital, capital budgeting
- **Valuation Methods**: DCF, comparables, precedent transactions, LBO analysis
- **M&A Analysis**: Synergies, accretion/dilution, deal structuring
- **Financial Planning**: Budgeting, forecasting, variance analysis
- **Working Capital**: Cash management, receivables, inventory optimization
- **Dividend Policy**: Payout ratios, share buybacks, capital allocation

### 4. Risk Management
- **Market Risk**: Beta, volatility, correlation, hedging strategies
- **Credit Risk**: Default probability, credit spreads, rating models
- **Operational Risk**: Process risks, fraud detection, internal controls
- **Liquidity Risk**: Funding risk, market liquidity, cash flow management
- **Regulatory Risk**: Compliance, capital requirements, stress testing
- **Systemic Risk**: Contagion effects, macroeconomic factors

### 5. Energy Finance
- **Oil & Gas Economics**: Price forecasting, project finance, reserve valuation
- **Power Markets**: Electricity pricing, renewable energy finance, PPAs
- **Carbon Markets**: Emissions trading, carbon credits, offset projects
- **Energy Derivatives**: Commodity futures, options, basis swaps
- **Project Finance**: Infrastructure funding, risk allocation, cash flow modeling
- **Energy Transition**: Clean energy investments, stranded assets, transition risks

### 6. Financial Modeling
- **DCF Models**: Free cash flow, WACC, terminal value calculations
- **LBO Models**: Debt schedules, returns analysis, exit strategies
- **Merger Models**: Pro forma statements, synergy modeling, integration costs
- **Project Finance Models**: Construction phase, operations, debt service
- **Monte Carlo Simulation**: Probabilistic modeling, sensitivity analysis
- **Option Pricing Models**: Black-Scholes, binomial trees, real options

## Industry Standards & Regulations

### Accounting Standards
- **US GAAP**: Generally Accepted Accounting Principles
- **IFRS**: International Financial Reporting Standards
- **FASB**: Financial Accounting Standards Board guidelines
- **SEC Reporting**: 10-K, 10-Q, 8-K requirements
- **Audit Standards**: PCAOB, internal controls, SOX compliance

### Financial Regulations
- **Basel III/IV**: Capital requirements, liquidity ratios
- **Dodd-Frank**: Volcker rule, stress testing, derivatives regulation
- **MiFID II**: Market structure, transparency, investor protection
- **Solvency II**: Insurance capital requirements
- **GDPR**: Data protection in financial services

### Market Standards
- **GIPS**: Global Investment Performance Standards
- **CFA Standards**: Code of Ethics and Standards of Professional Conduct
- **ISDA**: Derivatives documentation and standards
- **FIX Protocol**: Electronic trading communications
- **XBRL**: Financial reporting taxonomy

## Key Analysis Methods

### Valuation Techniques
- **Discounted Cash Flow (DCF)**
  - FCFF: Free Cash Flow to Firm
  - FCFE: Free Cash Flow to Equity
  - DDM: Dividend Discount Model
  - APV: Adjusted Present Value

- **Relative Valuation**
  - P/E, EV/EBITDA, P/B ratios
  - PEG ratio, EV/Sales
  - Industry-specific multiples

- **Asset-Based Valuation**
  - Book value, liquidation value
  - Replacement cost, sum-of-parts

### Risk Metrics
- **Portfolio Risk**
  - Standard deviation, Sharpe ratio
  - Information ratio, Sortino ratio
  - Maximum drawdown, Calmar ratio

- **Value at Risk (VaR)**
  - Historical simulation
  - Variance-covariance method
  - Monte Carlo simulation

- **Credit Metrics**
  - Probability of default (PD)
  - Loss given default (LGD)
  - Expected loss (EL)
  - Credit value adjustment (CVA)

### Performance Analysis
- **Return Metrics**
  - TWR: Time-weighted return
  - MWR: Money-weighted return
  - IRR: Internal rate of return
  - XIRR: Extended IRR

- **Risk-Adjusted Returns**
  - Sharpe ratio, Treynor ratio
  - Jensen's alpha, Information ratio
  - M-squared, Omega ratio

## Software Tools & APIs

### Market Data Platforms
- **Bloomberg Terminal**: Real-time data, analytics, trading
- **Refinitiv Eikon**: Market data, news, analytics
- **S&P Capital IQ**: Financial data, research, analytics
- **FactSet**: Portfolio analytics, risk management
- **Morningstar Direct**: Investment research, portfolio analysis

### Financial Modeling Software
- **Excel**: Financial modeling, VBA automation
- **Python**: Quantitative analysis, data science
- **R**: Statistical analysis, econometrics
- **MATLAB**: Numerical computing, optimization
- **Stata**: Econometric analysis

### Trading & Risk Systems
- **RiskMetrics**: Risk management platform
- **Murex**: Trading and risk management
- **Calypso**: Capital markets platform
- **Numerix**: Derivatives pricing
- **QuantLib**: Open-source quantitative finance library

## Python Libraries for Finance

### Core Libraries
```python
# Data Analysis
import pandas as pd
import numpy as np
from scipy import stats, optimize

# Financial Data
import yfinance as yf
import pandas_datareader as pdr
import fredapi  # Federal Reserve data

# Quantitative Finance
import quantlib as ql
import pyfolio  # Portfolio analytics
import zipline  # Backtesting
import empyrical  # Performance metrics

# Machine Learning
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import tensorflow as tf
import xgboost as xgb

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import dash  # Interactive dashboards
```

### Custom Modules
```python
# Portfolio optimization
from worldenergydata.portfolio import markowitz_optimization

# Risk analysis
from worldenergydata.risk import calculate_var, stress_test

# Valuation
from worldenergydata.valuation import dcf_model, relative_valuation

# Energy finance
from worldenergydata.energy_finance import oil_price_forecast
```

## Integration with WorldEnergyData

### Energy Market Analysis
- Oil and gas price forecasting
- Power market modeling
- Renewable energy project finance
- Carbon market analysis
- Energy commodity derivatives

### ESG Analytics
- Climate risk assessment
- Transition risk modeling
- Green bond analysis
- Sustainability metrics
- Impact measurement

### Sector Analysis
- Energy sector valuation
- Utilities financial analysis
- Infrastructure investments
- Clean tech opportunities
- Traditional vs renewable economics

## Best Practices

### Financial Analysis Workflow
1. **Data Collection**: Gather reliable, timely data
2. **Data Validation**: Check for errors, outliers, missing values
3. **Analysis Framework**: Apply appropriate models and methods
4. **Sensitivity Analysis**: Test key assumptions and variables
5. **Documentation**: Clear assumptions, methodology, limitations
6. **Review Process**: Peer review, model validation

### Model Development
1. **Simplicity First**: Start with simple models, add complexity as needed
2. **Transparency**: Clear logic, documented assumptions
3. **Flexibility**: Parameterized inputs, scenario capability
4. **Validation**: Backtesting, out-of-sample testing
5. **Version Control**: Track changes, maintain audit trail

### Risk Management
1. **Diversification**: Across assets, sectors, geographies
2. **Limits**: Position limits, concentration limits, VaR limits
3. **Stress Testing**: Historical scenarios, hypothetical scenarios
4. **Monitoring**: Real-time risk metrics, early warning systems
5. **Governance**: Clear policies, regular reviews

### Reporting Standards
1. **Accuracy**: Verify calculations, cross-check results
2. **Clarity**: Clear presentation, appropriate visualizations
3. **Completeness**: Include assumptions, limitations, risks
4. **Timeliness**: Meet reporting deadlines, update regularly
5. **Compliance**: Follow regulatory and internal requirements

## Common Calculations

### Present Value & NPV
```python
def calculate_npv(cash_flows, discount_rate, initial_investment=0):
    """Calculate Net Present Value"""
    pv = sum([cf / (1 + discount_rate)**i 
              for i, cf in enumerate(cash_flows, 1)])
    return pv - initial_investment
```

### WACC Calculation
```python
def calculate_wacc(equity_weight, debt_weight, cost_of_equity, 
                   cost_of_debt, tax_rate):
    """Calculate Weighted Average Cost of Capital"""
    wacc = (equity_weight * cost_of_equity + 
            debt_weight * cost_of_debt * (1 - tax_rate))
    return wacc
```

### Sharpe Ratio
```python
def sharpe_ratio(returns, risk_free_rate, periods_per_year=252):
    """Calculate Sharpe Ratio"""
    excess_returns = returns - risk_free_rate/periods_per_year
    return np.sqrt(periods_per_year) * (excess_returns.mean() / 
                                        excess_returns.std())
```

### Black-Scholes Option Pricing
```python
from scipy.stats import norm

def black_scholes(S, K, T, r, sigma, option_type='call'):
    """Black-Scholes option pricing"""
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    
    if option_type == 'call':
        price = S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
    else:  # put
        price = K*np.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)
    
    return price
```

## References

1. **CFA Institute Materials** - Comprehensive investment knowledge
2. **Options, Futures, and Other Derivatives** - John Hull
3. **Investment Valuation** - Aswath Damodaran
4. **Risk Management and Financial Institutions** - John Hull
5. **Energy Finance and Economics** - Betty Simkins & Russell Simkins
6. **Python for Finance** - Yves Hilpisch
7. **Quantitative Portfolio Management** - Grinold & Kahn