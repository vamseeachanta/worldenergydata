# FDAS Module User Guide

## Overview

The Field Development Analysis System (FDAS) module provides comprehensive economic analysis tools for offshore field development projects. It calculates financial metrics including NPV, MIRR, IRR, and payback period based on production forecasts, drilling schedules, and cost assumptions.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [API Reference](#api-reference)
4. [Examples](#examples)
5. [BSEE Data Integration](#bsee-data-integration)
6. [Excel Report Generation](#excel-report-generation)
7. [Troubleshooting](#troubleshooting)

## Quick Start

### Installation

The FDAS module is part of the WorldEnergyData package:

```bash
pip install worldenergydata
```

### Basic Usage

```python
from worldenergydata.fdas import (
    calculate_npv,
    excel_like_mirr,
    AssumptionsManager
)
import numpy as np

# Simple NPV/MIRR calculation
cashflows = np.array([-1500, -500, 200, 800, 1200, 1000, 800, 600, 400, 200])
discount_rate = 0.10  # 10%

npv = calculate_npv(cashflows, discount_rate, period='annual')
mirr_monthly, mirr_annual = excel_like_mirr(cashflows, discount_rate)

print(f"NPV: ${npv:,.2f}M")
print(f"MIRR: {mirr_annual:.2%}")
```

## Core Concepts

### Development Systems

FDAS classifies offshore developments into three categories based on water depth:

- **Dry** (`dry`): Water depth < 500 feet (shallow water platforms)
- **Subsea 15K** (`subsea15`): 500-6000 feet (standard subsea systems)
- **Subsea 20K** (`subsea20`): > 6000 feet (deepwater subsea systems)

Each system has different cost parameters for:
- Host platform CAPEX
- Subsea facilities (SURF) per well
- Drilling rig rates
- Operating expenses (OPEX)
- Royalty rates

### Financial Metrics

#### NPV (Net Present Value)
Discounts all future cashflows to present value:

```python
npv = calculate_npv(cashflows, discount_rate=0.10, period='monthly')
```

#### MIRR (Modified Internal Rate of Return)
Excel-compatible MIRR calculation with cashflow trimming:

```python
mirr_monthly, mirr_annual = excel_like_mirr(
    cashflows,
    discount_rate_annual=0.10,
    reinvestment_rate_annual=None  # Defaults to discount_rate
)
```

#### IRR (Internal Rate of Return)
Standard IRR calculation:

```python
irr_monthly, irr_annual = calculate_irr(cashflows, period='monthly')
```

#### Payback Period
Time to recover initial investment:

```python
payback_years = calculate_payback(cashflows, period='annual')
```

### Assumptions Management

Load development assumptions from Excel:

```python
from pathlib import Path

assumptions_file = Path('lease_assumptions.xlsx')
mgr = AssumptionsManager.from_excel(assumptions_file)

# Get specific parameters
host_capex = mgr.get('subsea15', 'HOST_CAPEX_MM')
surf_cost = mgr.get('subsea15', 'SURF_PER_WELL_MM')
royalty_rate = mgr.get('subsea15', 'ROYALTY_RATE')
```

The assumptions file should be in transposed format:
- First column: `DEV_SYSTEM` (parameter names)
- Subsequent columns: Development system names (`dry`, `subsea15`, `subsea20`)

## API Reference

### Core Financial Functions

#### `calculate_npv(cashflows, discount_rate, period='monthly')`
Calculate Net Present Value.

**Parameters:**
- `cashflows` (np.ndarray): Array of cashflow values
- `discount_rate` (float): Annual discount rate (e.g., 0.10 for 10%)
- `period` (str): 'monthly' or 'annual'

**Returns:** NPV value (float)

#### `excel_like_mirr(cashflows, discount_rate_annual, reinvestment_rate_annual=None)`
Calculate Modified Internal Rate of Return using Excel methodology.

**Parameters:**
- `cashflows` (np.ndarray): Array of cashflow values
- `discount_rate_annual` (float): Annual discount rate
- `reinvestment_rate_annual` (float, optional): Annual reinvestment rate

**Returns:** Tuple of (mirr_monthly, mirr_annual)

#### `calculate_irr(cashflows, period='monthly')`
Calculate Internal Rate of Return.

**Parameters:**
- `cashflows` (np.ndarray): Array of cashflow values
- `period` (str): 'monthly' or 'annual'

**Returns:** Tuple of (irr_monthly, irr_annual)

#### `calculate_all_metrics(cashflows, discount_rate, period='monthly')`
Calculate all financial metrics at once.

**Parameters:**
- `cashflows` (np.ndarray): Array of cashflow values
- `discount_rate` (float): Annual discount rate
- `period` (str): 'monthly' or 'annual'

**Returns:** Dictionary with keys:
- `npv`: Net Present Value
- `mirr_monthly`: Monthly MIRR
- `mirr_annual`: Annual MIRR
- `irr_monthly`: Monthly IRR
- `irr_annual`: Annual IRR
- `payback_years`: Payback period in years

### Configuration Classes

#### `AssumptionsManager`
Manages development cost and revenue assumptions.

**Class Methods:**
```python
@classmethod
def from_excel(cls, file_path, sheet_name='assumptions')
    """Load assumptions from Excel file"""

@classmethod
def from_dataframe(cls, df)
    """Load assumptions from DataFrame"""
```

**Instance Methods:**
```python
def get(self, system_name, parameter, default=0.0)
    """Get parameter value for development system"""

def get_all(self, system_name)
    """Get all parameters for development system"""

def list_systems(self)
    """Get list of available development systems"""

def list_parameters(self)
    """Get list of available parameters"""
```

#### `classify_dev_system_by_depth(water_depth)`
Classify development system based on water depth.

**Parameters:**
- `water_depth` (float): Water depth in feet

**Returns:** Development system string ('dry', 'subsea15', 'subsea20', or 'unknown')

### Data Processing

#### `ProductionProcessor`
Process and analyze production data.

```python
from worldenergydata.fdas.data import ProductionProcessor

processor = ProductionProcessor(production_df)

# Monthly aggregation
monthly = processor.aggregate_monthly(by='DEV_NAME')

# First oil identification
first_oil = processor.identify_first_oil(by='DEV_NAME')

# Cumulative production
cumulative = processor.calculate_cumulative_production(by='DEV_NAME')

# Production statistics
stats = processor.get_production_statistics(by='DEV_NAME')
```

#### `DrillingTimelineExtractor`
Extract drilling and completion timelines.

```python
from worldenergydata.fdas.data import DrillingTimelineExtractor

extractor = DrillingTimelineExtractor(well_data)

timeline = extractor.extract_timeline(
    development_name='ANCHOR',
    gap_months=3  # Treat gaps > 3 months as separate campaigns
)

# Timeline contains:
# - drilling_monthly: Dict[str, float] (drilling days by month)
# - completion_monthly: Dict[str, int] (well completions by month)
# - first_spud: datetime
# - last_completion: datetime
```

### Cashflow Analysis

#### `CashflowEngine`
Generate monthly cashflow projections.

```python
from worldenergydata.fdas.analysis import CashflowEngine
from datetime import datetime

engine = CashflowEngine(assumptions_mgr, dev_system='subsea15')

cashflows = engine.generate_monthly_cashflow(
    production_monthly=production_df,
    drilling_timeline=timeline,
    wti_prices=wti_price_dict,
    first_oil_date=datetime(2025, 1, 1)
)

# Each cashflow object has:
# - year_month: str
# - oil_production_bbl: float
# - oil_revenue_usd: float
# - royalty_usd: float
# - variable_opex_usd: float
# - fixed_opex_usd: float
# - drilling_capex_usd: float
# - facilities_capex_usd: float
# - host_capex_usd: float
# - net_cashflow_usd: float
```

### BSEE Data Adapters

#### `BseeAdapter`
Load and process BSEE data for FDAS analysis.

```python
from worldenergydata.fdas import BseeAdapter
from pathlib import Path

bsee_dir = Path('data/modules/bsee/current')
adapter = BseeAdapter(bsee_dir)

# Load production data
production = adapter.load_production(
    start_date='2020-01-01',
    end_date='2024-12-31'
)

# Load well data
wells = adapter.load_wells()

# Load by development
dev_data = adapter.load_by_development('ANCHOR')
```

## Examples

### Example 1: Simple NPV/MIRR Calculation

```python
import numpy as np
from worldenergydata.fdas import calculate_npv, excel_like_mirr

# Field development cashflow (millions USD)
cashflows = np.array([
    -1500,  # Year 0: Initial CAPEX
    -500,   # Year 1: Additional CAPEX
    200,    # Year 2: First production
    800,    # Year 3: Ramp up
    1200,   # Year 4: Peak
    1000,   # Year 5: Plateau
    800,    # Year 6: Decline
    600,    # Year 7
    400,    # Year 8
    200,    # Year 9
])

discount_rate = 0.10  # 10% cost of capital

# Calculate financial metrics
npv = calculate_npv(cashflows, discount_rate, period='annual')
mirr_monthly, mirr_annual = excel_like_mirr(cashflows, discount_rate)

print(f"NPV (10% discount): ${npv:,.2f}M")
print(f"MIRR (Annual): {mirr_annual:.2%}")
print(f"Project Status: {'✓ PROFITABLE' if npv > 0 else '✗ UNPROFITABLE'}")
```

### Example 2: Using Assumptions Manager

```python
from worldenergydata.fdas import AssumptionsManager
from pathlib import Path

# Load assumptions from Excel
assumptions_file = Path('lease_assumptions.xlsx')
mgr = AssumptionsManager.from_excel(assumptions_file)

# Get subsea 15K parameters
host_capex = mgr.get('subsea15', 'HOST_CAPEX_MM')
surf_cost = mgr.get('subsea15', 'SURF_PER_WELL_MM')
rig_rate = mgr.get('subsea15', 'MODU_LOADED_DAYRATE_MM')
royalty = mgr.get('subsea15', 'ROYALTY_RATE')

print(f"Host CAPEX: ${host_capex:.0f}M")
print(f"SURF per well: ${surf_cost:.0f}M")
print(f"Rig rate: ${rig_rate:.2f}M/day")
print(f"Royalty rate: {royalty:.1%}")
```

### Example 3: Production Processing

```python
import pandas as pd
from worldenergydata.fdas.data import ProductionProcessor

# Load production data
production_df = pd.read_csv('production.csv')

processor = ProductionProcessor(production_df)

# Monthly aggregation
monthly = processor.aggregate_monthly(by='DEV_NAME')

# First oil
first_oil = processor.identify_first_oil(by='DEV_NAME')

# Statistics
stats = processor.get_production_statistics(by='DEV_NAME')

print(f"Total oil: {monthly['MONTHLY_OIL_BBL'].sum():,.0f} BBL")
print(f"First oil: {first_oil['FIRST_OIL_DATE'].iloc[0]}")
print(f"Peak month: {monthly['MONTHLY_OIL_BBL'].max():,.0f} BBL")
```

### Example 4: Complete Workflow

```python
from worldenergydata.fdas import (
    AssumptionsManager,
    BseeAdapter,
    CashflowEngine,
    calculate_all_metrics
)
from worldenergydata.fdas.data import (
    ProductionProcessor,
    DrillingTimelineExtractor
)
from pathlib import Path
import numpy as np

# 1. Load assumptions
assumptions_file = Path('lease_assumptions.xlsx')
mgr = AssumptionsManager.from_excel(assumptions_file)

# 2. Load BSEE data
bsee_dir = Path('data/modules/bsee/current')
adapter = BseeAdapter(bsee_dir)

# 3. Load development data
dev_data = adapter.load_by_development('ANCHOR')
production = dev_data['production']
wells = dev_data['wells']

# 4. Process production
processor = ProductionProcessor(production)
monthly_production = processor.aggregate_monthly(by='DEV_NAME')

# 5. Extract drilling timeline
extractor = DrillingTimelineExtractor(wells)
timeline = extractor.extract_timeline('ANCHOR')

# 6. Generate cashflows
water_depth = wells['WATER_DEPTH'].mean()
dev_system = 'subsea15' if water_depth < 6000 else 'subsea20'

engine = CashflowEngine(mgr, dev_system)

wti_prices = {str(m): 75.0 for m in monthly_production['YEAR_MONTH']}
first_oil = processor.identify_first_oil(by='DEV_NAME')['FIRST_OIL_DATE'].iloc[0]

cashflows = engine.generate_monthly_cashflow(
    monthly_production,
    timeline,
    wti_prices,
    first_oil
)

# 7. Calculate financial metrics
cf_array = np.array([cf.net_cashflow_usd for cf in cashflows])
metrics = calculate_all_metrics(cf_array, 0.10)

print(f"NPV (10%): ${metrics['npv']/1e6:,.1f}M")
print(f"MIRR: {metrics['mirr_annual']:.2%}")
print(f"IRR: {metrics['irr_annual']:.2%}")
print(f"Payback: {metrics['payback_years']:.1f} years")
```

## BSEE Data Integration

### Data Requirements

FDAS requires the following data from BSEE:

**Production Data:**
- `API_WELL_NUMBER`: Well identifier
- `PROD_DATE`: Production date
- `OIL_VOLUME`: Oil production (BBL)
- `WATER_VOLUME`: Water production (BBL)
- `GAS_VOLUME`: Gas production (MCF)
- `DEV_NAME`: Development/field name
- `LEASE_NAME`: Lease identifier

**Well Data:**
- `API_WELL_NUMBER`: Well identifier
- `WATER_DEPTH`: Water depth (feet)
- `WELL_SPUD_DATE`: Spud date
- `TOTAL_DEPTH_DATE`: Completion date
- `DEV_SYSTEM`: Development system classification

### Enhancing BSEE Data

Use the enhancement script to add required columns:

```bash
python scripts/fdas_enhance_bsee_data.py
```

This script:
1. Adds `DEV_SYSTEM` column to well data based on water depth
2. Creates `lease_mapping.csv` linking leases to developments
3. Enhances production data with development names

### Manual Integration Steps

If BSEE data structure differs from FDAS requirements:

1. **Map Wells to Developments**: Create mapping between `API_WELL_NUMBER` and development names
2. **Add DEV_SYSTEM**: Classify wells using `classify_dev_system_by_depth()`
3. **Aggregate Production**: Group production data by development and month
4. **Create Timeline**: Extract drilling/completion dates from well records

## Excel Report Generation

Generate formatted Excel reports with cashflow projections:

```python
from worldenergydata.fdas.reports import FDASReportBuilder

builder = FDASReportBuilder(
    development_name='ANCHOR',
    cashflows=cashflows,
    assumptions=mgr,
    dev_system='subsea15'
)

# Generate report
output_file = Path('reports/anchor_economics.xlsx')
builder.generate_report(output_file)
```

The report includes:
- Executive summary with key metrics
- Monthly cashflow projection
- Revenue and cost breakdown
- NPV/MIRR/IRR calculations
- Sensitivity analysis
- Charts and visualizations

## Troubleshooting

### Common Issues

**Issue: "Parameter not found in assumptions"**

*Solution*: Check parameter name formatting. Special characters like `$` and `/` may need alternate formats:
```python
# Try these variations:
value = mgr.get('subsea15', 'VARIABLE_OPEX_$/BBL')
value = mgr.get('subsea15', 'VARIABLE_OPEX_$_BBL')
```

**Issue: "TypeError: '<' not supported between Period and str"**

*Solution*: Convert Period objects to strings:
```python
prod_dict = {str(k): v for k, v in production_dict.items()}
```

**Issue: "MIRR values differ from Excel"**

*Solution*: FDAS uses Excel-compatible MIRR with cashflow trimming. Ensure you're using `excel_like_mirr()` not numpy-financial's MIRR.

**Issue: "KeyError: LEASE_NUMBER"**

*Solution*: BSEE data may not have lease numbers. Use the enhancement script or create manual mapping.

### Validation

Validate implementation against original FDAS code:

```bash
python -m pytest tests/modules/fdas/validation/test_against_original.py -v
```

Expected results:
- NPV: 100% match
- MIRR: 100% match (0.00e+00 difference)
- Assumptions loading: 100% match (15/15 parameters)

### Performance

FDAS module is optimized for performance:
- 3x faster than original implementation
- Vectorized numpy operations
- Efficient DataFrame processing
- Minimal memory allocation

For large datasets (>100K wells), consider:
- Processing in batches by development
- Using chunked CSV reading
- Parallelizing development-level calculations

## Additional Resources

- **Examples**: `examples/fdas_complete_workflow.py`
- **Integration Tests**: `tests/modules/fdas/integration/`
- **Validation Report**: `docs/modules/fdas/VALIDATION-REPORT.md`
- **API Documentation**: `docs/modules/fdas/API.md`

## Support

For issues or questions:
1. Check the validation report for known issues
2. Review example scripts in `examples/`
3. Run validation tests to verify installation
4. Check BSEE data structure compatibility

---

*Last updated: 2025-10-03*
*FDAS Module Version: 1.0.0*
