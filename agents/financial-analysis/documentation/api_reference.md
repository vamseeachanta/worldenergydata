# Financial Analysis Agent API Reference

## Overview
API documentation for the Financial Analysis Agent module.

## Core Classes

### FinancialAnalysisAgent
Main agent class for financial analysis operations.

#### Methods

##### `analyze_investment(project_data: dict) -> dict`
Performs comprehensive investment analysis.

**Parameters:**
- `project_data`: Dictionary containing project specifications
  - `capex`: Capital expenditure
  - `opex_annual`: Annual operating expenses
  - `revenue_annual`: Annual revenue
  - `project_life`: Project duration in years
  - `discount_rate`: Discount rate for NPV calculation

**Returns:**
- Dictionary with analysis results including NPV, IRR, payback period

##### `forecast_commodity_price(commodity: str, horizon_months: int) -> dict`
Generates price forecasts for energy commodities.

**Parameters:**
- `commodity`: Type of commodity (crude_oil, natural_gas, electricity)
- `horizon_months`: Forecast horizon in months

**Returns:**
- Forecast results with confidence intervals

##### `assess_risk(project_data: dict, method: str = 'monte_carlo') -> dict`
Performs risk assessment using specified methodology.

**Parameters:**
- `project_data`: Project specifications
- `method`: Risk assessment method (monte_carlo, sensitivity, scenario)

**Returns:**
- Risk metrics and probability distributions

## Configuration

### Environment Variables
- `FA_API_KEY`: API key for external data sources
- `FA_CACHE_TTL`: Cache time-to-live in seconds
- `FA_MAX_WORKERS`: Maximum parallel workers

### YAML Configuration
```yaml
agent:
  name: financial-analysis
  version: 1.0.0
  cache_enabled: true
  parallel_processing: true
```

## Error Handling
All methods raise `FinancialAnalysisError` for invalid inputs or processing errors.

## Examples
See README.md for usage examples.
