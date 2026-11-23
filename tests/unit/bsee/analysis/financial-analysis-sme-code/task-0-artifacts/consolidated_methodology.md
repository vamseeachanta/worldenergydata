# Consolidated Financial Analysis Methodology

> Document: SME Roy's Financial Analysis Methodology Consolidation
> Created: 2025-08-21
> Based on: Analysis of 2025-07-29, 2025-07-30, 2025-08-15, and 2025-08-20 implementations

## Executive Summary

This document consolidates the financial analysis methodology developed by SME Roy across four implementation versions, culminating in the V20 comprehensive financial analysis system for BSEE oil and gas lease data.

## Evolution of Approach

### Version Timeline

1. **2025-07-29 (Initial)**: Basic drilling and completion days extraction
   - Focus: Extract drilling/completion days from WAR data
   - Key Innovation: Spud date adjustment logic with gap threshold

2. **2025-07-30 (Enhanced)**: Improved data handling
   - Added: Better Excel output formatting
   - Enhanced: Error handling and data validation

3. **2025-08-15 (V18)**: Full financial analysis
   - Added: NPV calculations and cash flow analysis
   - Introduced: Lease grouping system
   - Implemented: Tax calculations and revenue modeling

4. **2025-08-20 (V20)**: Production-ready system
   - Refined: Formatting and user experience
   - Added: Comprehensive drilling/completion cost modeling
   - Enhanced: Multi-sheet Excel output with README

## Core Components

### 1. Data Sources

#### Primary Inputs
- **leases.xlsx**: Lease configurations and groupings
- **leases_assumptions.xlsx**: Economic assumptions per lease
- **multi_year_lease_matrix_with_charts.xlsx**: Production data
- **drilling_and_completion_days_by_api.xlsx**: D&C timing data
- **wti_full_monthly.xlsx**: Oil price data
- **WAR data files**: mv_war_main.txt, mv_war_boreholes_view.txt, etc.

#### Data Structure
```python
# Lease grouping mapping (consistent across versions)
group_as_map = {
    'Stones': 'Stones',
    'Cascade': 'Cascade Chinook',
    'Chinook': 'Cascade Chinook',
    'Julia': 'Julia',
    'Anchor': 'Anchor',
    'Jack': 'Jack',
    'St Malo': 'St Malo',
    # ... additional mappings
}
```

### 2. Processing Pipeline

#### Phase 1: Data Ingestion
1. Load lease configurations
2. Parse production data (matrix or timeseries format)
3. Extract drilling/completion timing
4. Load economic assumptions and oil prices

#### Phase 2: Drilling & Completion Analysis
```python
# Key algorithm: Spud date adjustment
GAP_THRESHOLD = 300  # days

def adjust_spud(api, td_date):
    # Logic to determine actual spud date
    # Handles gaps in WAR reporting
    # Returns adjusted spud and early days
```

#### Phase 3: Financial Calculations
1. **Monthly Production**: Convert daily rates to monthly volumes
2. **Revenue Calculation**: Production × Oil Price × (1 - Royalty)
3. **CAPEX Allocation**: 
   - Drilling costs spread over drilling period
   - Completion costs at completion date
4. **OPEX Calculation**: Based on production volumes
5. **Tax Application**: State and federal taxes on net revenue
6. **NPV Calculation**: Discounted cash flow at specified rate

### 3. Key Algorithms

#### Production Aggregation
```python
# Convert matrix format to timeseries
def matrix_to_timeseries(df):
    # Melt wide format to long
    # Calculate monthly volumes from daily rates
    # Aggregate by well/lease
```

#### Cash Flow Calculation
```python
def calculate_monthly_cashflow(prod, price, costs, tax_rate):
    revenue = prod * price * (1 - royalty_rate)
    opex = prod * opex_per_bbl
    ebitda = revenue - opex - costs
    tax = max(0, ebitda * tax_rate)
    net_cf = ebitda - tax
    return net_cf
```

#### NPV Calculation
```python
def calculate_npv(cashflows, discount_rate, n_months):
    factors = (1 + discount_rate) ** (np.arange(n_months) / 12)
    return np.sum(cashflows / factors)
```

### 4. Output Generation

#### Excel Structure
1. **README Tab**: Documentation and metadata
2. **Executive Summary**: Key metrics by lease
3. **CF_Debug**: Detailed monthly cash flows
4. **Lease Group Tabs**: Monthly data per grouped lease

#### Formatting Standards
- Column A (dates): Width 12, format mm/dd/yyyy
- Columns B-G (values): Width 15, format #,##0
- All monetary values: No decimals, comma separators

## Best Practices Identified

### Data Validation
1. Always normalize lease numbers (G-prefix handling)
2. Validate date ranges and handle missing data
3. Check for negative cash flows and flag anomalies

### Performance Optimization
1. Use vectorized operations for large datasets
2. Cache intermediate calculations
3. Process leases in batches for memory efficiency

### Error Handling
1. Graceful fallback for missing data
2. Clear error messages with context
3. Log processing steps for debugging

## Implementation Strategy

### Module Structure
```
worldenergydata.bsee.analysis.sme_financial/
├── __init__.py
├── config.py              # Lease mappings and constants
├── data_loader.py         # Input file parsing
├── lease_processor.py     # Lease grouping and aggregation
├── drilling_completion.py # D&C analysis
├── cash_flow_calculator.py # Financial calculations
├── report_generator.py    # Excel output generation
└── financial_analyzer.py  # Main orchestrator
```

### Integration Points
1. **With BSEE Data Module**: Use existing data loaders where possible
2. **With Engine Framework**: Leverage YAML configuration system
3. **With Testing Framework**: Comprehensive unit and integration tests

## Validation Criteria

### Accuracy Requirements
- NPV calculations must match V20 output within 0.01%
- Monthly cash flows must reconcile with source data
- Tax calculations must follow specified rates exactly

### Performance Targets
- Process 100+ leases in < 60 seconds
- Generate Excel with 50+ sheets efficiently
- Memory usage < 2GB for typical runs

## Migration Path

### From Existing Scripts
1. Preserve all calculation logic from V20
2. Refactor into modular components
3. Add comprehensive error handling
4. Implement full test coverage

### Data Compatibility
- Maintain backward compatibility with V18/V20 formats
- Support both matrix and timeseries production data
- Handle various date formats gracefully

## Appendix: Key Formulas

### Drilling Days Calculation
```
drilling_days = (TD_date - adjusted_spud_date).days + early_days
```

### Monthly Revenue
```
revenue = production_bbls × oil_price_$/bbl × (1 - royalty_rate)
```

### Net Cash Flow
```
net_cf = revenue - opex - capex - taxes
```

### NPV Formula
```
NPV = Σ(CF_t / (1 + r)^(t/12))
where t = month index, r = annual discount rate
```

## Notes

- The V20 implementation represents the most mature and tested version
- All financial calculations have been validated against actual field data
- The modular approach in V20 provides the best foundation for integration
- Real data from BSEE should be used for testing - no mock data needed