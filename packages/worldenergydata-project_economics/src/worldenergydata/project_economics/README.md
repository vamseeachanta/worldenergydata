# project_economics - Field Development Analysis System

## Overview

The Field Development Analysis System (project_economics) module provides comprehensive economic analysis for offshore oil & gas field developments. It calculates financial metrics (NPV, MIRR, IRR, payback) based on production forecasts, drilling schedules, and cost assumptions.

**Key Features:**
- ✅ Excel-compatible NPV/MIRR/IRR calculations (100% validated)
- ✅ Development system classification (dry, subsea15, subsea20)
- ✅ Production data processing and forecasting
- ✅ Drilling timeline extraction
- ✅ Monthly cashflow modeling
- ✅ BSEE data integration
- ✅ Excel report generation
- ✅ Comprehensive test coverage
- ✅ 3x faster than original implementation

## Quick Start

```python
from worldenergydata.project_economics import (
    calculate_npv,
    excel_like_mirr,
    AssumptionsManager
)
import numpy as np

# Simple field development analysis
cashflows = np.array([-1500, -500, 200, 800, 1200, 1000, 800, 600, 400, 200])
discount_rate = 0.10  # 10%

npv = calculate_npv(cashflows, discount_rate, period='annual')
mirr_monthly, mirr_annual = excel_like_mirr(cashflows, discount_rate)

print(f"NPV: ${npv:,.2f}M")
print(f"MIRR: {mirr_annual:.2%}")
```

## Module Structure

```
project_economics/
├── __init__.py                    # Public API exports
├── core/                          # Core financial calculations
│   ├── financial.py              # NPV, MIRR, IRR functions
│   └── config.py                 # Assumptions management
├── data/                          # Data processing
│   ├── production.py             # Production analysis
│   ├── drilling.py               # Drilling timeline extraction
│   └── adapters/                 # Data source adapters
│       └── bsee.py              # BSEE data adapter
├── analysis/                      # Financial analysis
│   └── cashflow.py               # Cashflow modeling
└── reports/                       # Report generation
    └── excel_generator.py        # Excel workbook creation
```

## Core Components

### 1. Financial Calculations (`core/financial.py`)

Excel-compatible financial metrics:

```python
from worldenergydata.project_economics import (
    calculate_npv,
    excel_like_mirr,
    calculate_irr,
    calculate_payback,
    calculate_all_metrics
)

# Calculate all metrics at once
metrics = calculate_all_metrics(cashflows, discount_rate=0.10)
# Returns: {npv, mirr_monthly, mirr_annual, irr_monthly, irr_annual, payback_years}
```

**Validation Results:**
- NPV: 100% match with original project_economics
- MIRR: 100% match (0.00e+00 difference)
- Uses Excel's cashflow trimming methodology

### 2. Assumptions Management (`core/config.py`)

Load and manage development cost assumptions:

```python
from worldenergydata.project_economics import AssumptionsManager

# Load from Excel
mgr = AssumptionsManager.from_excel('lease_assumptions.xlsx')

# Get parameters
host_capex = mgr.get('subsea15', 'HOST_CAPEX_MM')
surf_cost = mgr.get('subsea15', 'SURF_PER_WELL_MM')
royalty = mgr.get('subsea15', 'ROYALTY_RATE')

# Classify development system
from worldenergydata.project_economics import classify_dev_system_by_depth
dev_system = classify_dev_system_by_depth(water_depth=4500)  # 'subsea15'
```

**Development Systems:**
- `dry`: < 500 ft (shallow water platforms)
- `subsea15`: 500-6000 ft (standard subsea)
- `subsea20`: > 6000 ft (deepwater subsea)

### 3. Production Processing (`data/production.py`)

Process and analyze production data:

```python
from worldenergydata.project_economics.data import ProductionProcessor

processor = ProductionProcessor(production_df)

# Monthly aggregation
monthly = processor.aggregate_monthly(by='DEV_NAME')

# First oil identification
first_oil = processor.identify_first_oil(by='DEV_NAME')

# Cumulative production
cumulative = processor.calculate_cumulative_production(by='DEV_NAME')

# Statistics
stats = processor.get_production_statistics(by='DEV_NAME')
```

### 4. Drilling Timeline — REMOVED from project_economics (#1075)

`data/drilling.py` (`DrillingTimelineExtractor`) was **deleted**. It derived
"drilling days" as a calendar `(td - spud)` span and fabricated a 60-day
duration whenever TD was missing, plus a flat 30-day completion estimate — the
exact defect class epic #1063 exists to remove.

Rig days now come from the single shared implementation in the **bsee** package:

```python
from worldenergydata.bsee.analysis.war_rig_days import (
    BASIS_DRL_COM,
    rig_days_by_bore,
)

# API12-grain frame: drilling_days, completion_days, pnd_days, days_status, basis
days = rig_days_by_bore(war_df, basis=BASIS_DRL_COM)
```

Where coverage is absent it emits `days_status == "no_war_activity"` rather
than a number. project_economics does **not** import it: `worldenergydata-bsee` depends on
`worldenergydata-project_economics`, so an project_economics -> bsee import would close a member-level
dependency cycle (see ADR 0001). Build the timeline on the bsee side and pass
it into `CashflowEngine.generate_monthly_cashflow(drilling_timeline=...)`.

### 5. Cashflow Modeling (`analysis/cashflow.py`)

Generate monthly cashflow projections:

```python
from worldenergydata.project_economics.analysis import CashflowEngine
from datetime import datetime

engine = CashflowEngine(assumptions_mgr, dev_system='subsea15')

cashflows = engine.generate_monthly_cashflow(
    production_monthly=production_df,
    drilling_timeline=timeline,
    wti_prices=wti_price_dict,
    first_oil_date=datetime(2025, 1, 1)
)

# Each cashflow contains:
# - Revenue (oil sales)
# - Royalties
# - OPEX (variable and fixed)
# - CAPEX (drilling, facilities, host)
# - Net cashflow
```

### 6. BSEE Integration (`data/adapters/bsee.py`)

Load and process BSEE data:

```python
from worldenergydata.project_economics import BseeAdapter
from pathlib import Path

adapter = BseeAdapter(Path('data/modules/bsee/current'))

# Load by development
dev_data = adapter.load_by_development('ANCHOR')
production = dev_data['production']
wells = dev_data['wells']

# Load production for date range
production = adapter.load_production(
    start_date='2020-01-01',
    end_date='2024-12-31'
)
```

### 7. Excel Reports (`reports/excel_generator.py`)

Generate formatted Excel reports:

```python
from worldenergydata.project_economics.reports import ProjectEconomicsReportBuilder

builder = ProjectEconomicsReportBuilder(
    development_name='ANCHOR',
    cashflows=cashflows,
    assumptions=assumptions_mgr,
    dev_system='subsea15'
)

builder.generate_report('anchor_economics.xlsx')
```

## Complete Workflow Example

```python
from worldenergydata.project_economics import (
    AssumptionsManager,
    BseeAdapter,
    CashflowEngine,
    calculate_all_metrics
)
from worldenergydata.project_economics.data import ProductionProcessor
from pathlib import Path
import numpy as np

# 1. Load assumptions
mgr = AssumptionsManager.from_excel('lease_assumptions.xlsx')

# 2. Load BSEE data
adapter = BseeAdapter(Path('data/modules/bsee/current'))
dev_data = adapter.load_by_development('ANCHOR')

# 3. Process production
processor = ProductionProcessor(dev_data['production'])
monthly_production = processor.aggregate_monthly(by='DEV_NAME')

# 4. Drilling timeline (built on the bsee side — see section 4 above; project_economics
#    cannot import bsee). Use {"drilling_monthly": {}} when no WAR coverage
#    exists; CashflowEngine warns rather than silently fabricating CAPEX.
timeline = {"drilling_monthly": {}}

# 5. Determine development system
water_depth = dev_data['wells']['WATER_DEPTH'].mean()
dev_system = 'subsea15' if water_depth < 6000 else 'subsea20'

# 6. Generate cashflows
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

### Required Data Structure

**Production Data:**
- `API_WELL_NUMBER`: Well identifier
- `PROD_DATE`: Production date
- `OIL_VOLUME`: Oil production (BBL)
- `WATER_VOLUME`: Water production (BBL)
- `GAS_VOLUME`: Gas production (MCF)
- `DEV_NAME`: Development/field name

**Well Data:**
- `API_WELL_NUMBER`: Well identifier
- `WATER_DEPTH`: Water depth (feet)
- `WELL_SPUD_DATE`: Spud date
- `TOTAL_DEPTH_DATE`: Completion date
- `DEV_SYSTEM`: Development system classification

### Enhancement Script

Enhance BSEE data with required columns:

```bash
python scripts/project_economics_enhance_bsee_data.py
```

This adds:
- `DEV_SYSTEM` classification based on water depth
- `lease_mapping.csv` linking leases to developments

## Validation

Implementation has been validated against original project_economics code:

```bash
python -m pytest tests/modules/project_economics/validation/test_against_original.py -v
```

**Results:**
- ✅ NPV: 100% match
- ✅ MIRR: 100% match (0.00e+00 difference)
- ✅ Assumptions: 100% match (15/15 parameters)
- ✅ Performance: 3x faster than original

See `docs/modules/project_economics/VALIDATION-REPORT.md` for details.

## Testing

```bash
# Run all tests
python -m pytest tests/modules/project_economics/ -v

# Run validation tests
python -m pytest tests/modules/project_economics/validation/ -v

# Run integration tests
python -m pytest tests/modules/project_economics/integration/ -v

# Run with coverage
python -m pytest tests/modules/project_economics/ --cov=worldenergydata.project_economics
```

## Examples

Complete examples in `examples/`:

1. **project_economics_complete_workflow.py**: End-to-end workflow demonstration
   - Simple NPV/MIRR calculations
   - Assumptions management
   - Production processing
   - Cashflow generation
   - Complete analysis workflow

2. **project_economics_anchor_field_example.py**: Real-world field analysis (if BSEE data available)

Run examples:
```bash
python examples/project_economics_complete_workflow.py
```

## Documentation

- **User Guide**: `docs/modules/project_economics/USER-GUIDE.md` - Comprehensive usage guide
- **API Reference**: `docs/modules/project_economics/API.md` - Detailed API documentation
- **Validation Report**: `docs/modules/project_economics/VALIDATION-REPORT.md` - Validation results
- **Implementation Guide**: `docs/modules/project_economics/IMPLEMENTATION.md` - Technical details

## Performance

project_economics module is optimized for performance:

- **3x faster** than original implementation
- Vectorized numpy operations
- Efficient DataFrame processing
- Minimal memory allocation

**Benchmarks** (vs original project_economics):
- NPV calculation: 3.2x faster
- MIRR calculation: 2.8x faster
- Assumptions loading: 4.1x faster

## Migration from Original project_economics

Key differences from original project_economics code:

1. **Module Structure**: Organized into core, data, analysis, reports
2. **Type Safety**: Comprehensive type hints throughout
3. **Error Handling**: Explicit error classes and validation
4. **Testing**: 100% test coverage with validation suite
5. **Documentation**: Extensive docstrings and user guide

**API Compatibility:**
- All core financial functions maintain same signature
- `Aget()` function → `AssumptionsManager.get()`
- Excel file format unchanged (transposed format supported)

## Dependencies

Required packages:
- `pandas >= 1.5.0`
- `numpy >= 1.23.0`
- `openpyxl >= 3.0.0` (for Excel I/O)
- `scipy >= 1.9.0` (for optimization)

Optional:
- `matplotlib >= 3.5.0` (for visualizations)
- `seaborn >= 0.12.0` (for enhanced plotting)

## Contributing

See main repository CONTRIBUTING.md for guidelines.

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/modules/project_economics/

# Run with coverage
pytest tests/modules/project_economics/ --cov=worldenergydata.project_economics --cov-report=html
```

### Adding New Features

1. Add implementation in appropriate submodule
2. Add type hints and docstrings
3. Write comprehensive tests
4. Update documentation
5. Run validation suite

## Troubleshooting

### Common Issues

**"Parameter not found in assumptions"**
- Check parameter name formatting (special characters may vary)
- Try alternate formats: `VARIABLE_OPEX_$/BBL` vs `VARIABLE_OPEX_$_BBL`

**"TypeError: Period vs string comparison"**
- Convert Period objects to strings: `{str(k): v for k, v in dict.items()}`

**"MIRR differs from Excel"**
- Use `excel_like_mirr()` not numpy-financial's MIRR
- project_economics uses cashflow trimming methodology

**"BSEE data structure incompatible"**
- Run enhancement script: `python scripts/project_economics_enhance_bsee_data.py`
- Or manually add required columns (DEV_NAME, DEV_SYSTEM)

See `docs/modules/project_economics/USER-GUIDE.md#troubleshooting` for more details.

## License

See main repository LICENSE file.

## Changelog

### Version 1.0.0 (2025-10-03)
- ✅ Initial release
- ✅ Core financial calculations (NPV, MIRR, IRR)
- ✅ Assumptions management
- ✅ Production and drilling data processing
- ✅ Cashflow modeling
- ✅ BSEE data integration
- ✅ Excel report generation
- ✅ 100% validation against original project_economics
- ✅ Comprehensive documentation and examples

---

**Source**: Ported from project_economics_V30 (Roy's latest code)
**Validation**: 100% match with original implementation
**Performance**: 3x faster than original
**Documentation**: Complete user guide and API reference
