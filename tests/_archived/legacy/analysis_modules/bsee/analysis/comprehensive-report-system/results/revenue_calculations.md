# Revenue Calculation Mapping

## Overview
This document maps the revenue calculation methodology for the comprehensive reporting system based on analysis of go-by reports.

## Revenue Components

### Oil Revenue
- **Formula**: `oil_volume × oil_price × (1 - royalty_rate)`
- **Source**: BSEE production data
- **Royalty**: 18.75% federal standard

### Gas Revenue
- **Formula**: `gas_volume × gas_price × (1 - royalty_rate)`
- **Source**: BSEE production data
- **Benchmark**: Henry Hub pricing

### Total Revenue
- **Formula**: `oil_revenue + gas_revenue + ngl_revenue`

## Cost Structure

### Operating Costs
- **Lease Operating Expense**: $5-15/BBL depending on water depth
- **Workover Costs**: $1-5M per workover
- **Transportation**: $2-8/BBL

### Capital Costs
- **Drilling**: $50-150M per deepwater well
- **Completion**: $20-50M per well
- **Facilities**: $500M-2B for deepwater development

## Economic Metrics

### Key Performance Indicators
1. **Net Revenue**: Total revenue - Operating costs
2. **EBITDA**: Net revenue - G&A costs
3. **Free Cash Flow**: EBITDA - Capital costs - Taxes
4. **NPV**: Discounted cash flows at 10%
5. **IRR**: Target > 15%
6. **Payback Period**: Target < 5 years

## Calculation Workflow

### Step-by-Step Process
1. **Production Data**: Load and clean monthly volumes
2. **Price Application**: Apply price deck to production
3. **Gross Revenue**: Calculate product revenues
4. **Royalties/Taxes**: Apply government takes
5. **Operating Costs**: Deduct operating expenses
6. **Capital Treatment**: Apply depreciation/amortization
7. **Cash Flow**: Generate cash flow schedule
8. **NPV/Metrics**: Calculate economic indicators

## Price Assumptions

### Base Case (2024-2028)
- **Oil**: $75-80/BBL (WTI)
- **Gas**: $3.50-4.25/MCF (Henry Hub)
- **NGL**: 45% of oil price
- **Escalation**: 2% annual inflation

## Implementation Notes
- All calculations performed at monthly granularity
- Aggregation to field/block level as needed
- Sensitivity analysis on key variables
- Monte Carlo simulation for uncertainty

---
*Generated for Comprehensive Report System*
