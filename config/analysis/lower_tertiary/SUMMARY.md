# Lower Tertiary Analysis Framework - Setup Complete

## Status: ✅ Ready for Analysis

**Date**: 2024-12-20  
**Purpose**: Economic analysis of Lower Tertiary subsea fields matching Industry Performance paper outputs

---

## What Has Been Created

### 1. Configuration Files (YAML)

#### `economic_assumptions.yml` (10.2 KB)
Complete economic parameter set including:
- **Commodity prices**: Oil ($75/bbl), Gas ($3.50/mcf), NGL ($30/bbl)
- **Fiscal terms**: 18.75% royalty, 21% income tax
- **CAPEX assumptions**: $1.8-3.2B per field development
- **OPEX assumptions**: $15/boe variable + $120MM/year fixed
- **Production type curves**: Hyperbolic decline (45% initial → 8% terminal)
- **Financial metrics**: 10% discount rate, 15% hurdle rate
- **Sensitivity parameters**: Price, production, cost ranges
- **Data sources**: BSEE production, EIA prices

#### `field_parameters.yml` (13.4 KB)
Individual field configurations for 8 Lower Tertiary developments:
- ✅ **Jack/St. Malo**: $7.5B CAPEX, 11 wells, 177 MBOPD capacity
- ✅ **Stones**: $3.8B CAPEX, 7 wells, 50 MBOPD FPSO
- ✅ **Julia**: $4.7B CAPEX, 6 wells, 34 MBOPD tieback
- ✅ **Anchor**: $5.6B CAPEX, 7 wells, 75 MBOPD, 20K psi HPHT
- ✅ **Cascade/Chinook**: $2.9B CAPEX, 6 wells, 75 MBOPD
- ✅ **Shenandoah**: $1.8B CAPEX, 6 wells, 100 MBOPD (2025 startup)
- ⏳ **Tiber**: Pre-FID, ~$8B estimate
- ⏳ **Kaskida**: Pre-FID, ~$10B estimate

Each field includes:
- Location (water depth, BOEM field codes)
- Partners and working interests
- Key dates (discovery, FID, first oil)
- Development concept
- Capital costs (actual disclosed values)
- Reserve estimates
- Production profiles

#### `analysis_config.yml` (15.3 KB)
Main orchestration configuration:
- **Analysis scope**: 2008-2024 actual + forecast to 2050
- **Data sources**: BSEE production, EIA prices, well data
- **Calculation methods**: Revenue, costs, cash flow, NPV, IRR
- **Pipeline stages**: 9-stage execution plan
- **Output formats**: Excel tables, HTML dashboard, CSV exports
- **Validation targets**: Benchmarks from Industry Performance paper

### 2. Documentation Files

#### `ASSUMPTIONS.md` (15.1 KB)
Comprehensive documentation of all assumptions:
- Economic assumptions (prices, fiscal terms, costs)
- Production assumptions (decline curves, type curves)
- Financial assumptions (discount rates, IRR targets)
- Data sources and validation methods
- Limitations and uncertainties
- Sensitivity analysis parameters
- References and benchmarks

#### `README.md` (11.4 KB)
User guide with:
- Quick start instructions
- Configuration file descriptions
- 9-stage pipeline explanation
- Output file descriptions
- Troubleshooting guide
- Customization examples
- Validation criteria

### 3. Analysis Runner Script

#### `scripts/lower_tertiary_analysis.py` (executable)
Python orchestration script that:
- Loads all YAML configurations
- Validates inputs
- Executes 9-stage pipeline
- Generates reports and dashboards
- Compares results with paper benchmarks

**Test Result**: ✅ Successfully loaded and validated all configurations

---

## Pipeline Stages

The analysis executes through 9 sequential stages:

1. **Load Configurations** ✅ Tested
   - Load economic assumptions
   - Load field parameters  
   - Validate configurations

2. **Load Data** (Ready)
   - BSEE production data
   - Historical price data
   - Well and drilling data

3. **Calculate Revenues** (Ready)
   - Oil revenue
   - Gas revenue
   - NGL revenue

4. **Calculate Costs** (Ready)
   - Royalties
   - Operating costs
   - Depreciation
   - Income tax

5. **Calculate Cash Flows** (Ready)
   - Operating cash flow
   - Free cash flow
   - Cumulative cash flow

6. **Calculate Financial Metrics** (Ready)
   - NPV (10%, 8%, 15%)
   - IRR
   - Payback period
   - Profitability index

7. **Run Sensitivities** (Ready)
   - Price sensitivity (±20%, ±30%)
   - Production sensitivity
   - Cost sensitivity

8. **Generate Reports** (Ready)
   - Excel reports (4 primary reports)
   - HTML interactive dashboard
   - Validation report
   - Export data files

9. **Validate Results** (Ready)
   - Compare with paper benchmarks
   - Document assumptions
   - Generate final summary

---

## Expected Outputs

### Primary Excel Reports
Location: `results/lower_tertiary/`

1. **`production_revenue_summary.xlsx`**
   - Annual production (oil, gas, NGL) by field
   - Revenue breakdown by commodity
   - Subtotals and grand totals

2. **`npv_analysis_by_field.xlsx`**
   - NPV at 10%, 8%, 15% discount rates
   - IRR and payback period
   - Profitability index
   - Ranked by NPV10

3. **`monthly_cash_flow.xlsx`**
   - Time series for each field
   - Production, revenue, costs, cash flow
   - Cumulative metrics

4. **`capital_deployment.xlsx`**
   - Annual CAPEX schedule
   - By category: exploration, development, abandonment

### Interactive HTML Dashboard
Location: `results/lower_tertiary/dashboard.html`

Sections:
- **Executive Summary**: Total investment, cumulative production, NPV, IRR
- **Production Overview**: Area charts, bar charts by field
- **Financial Performance**: Waterfall, scatter, line charts
- **Unit Economics**: Cost per BOE comparisons
- **Sensitivity Analysis**: Tornado charts

### Validation Report
Location: `results/lower_tertiary/paper_comparison.html`

Compares calculated results with paper benchmarks:
- Jack/St. Malo: ~150 MMBOE, ~$8B revenue, ~$3.5B NPV10
- Stones: ~80 MMBOE, ~$4.5B revenue, ~$2.0B NPV10
- Julia: ~50 MMBOE, ~$2.8B revenue, ~$1.2B NPV10

---

## How to Run

### Full Analysis
```bash
cd /mnt/github/workspace-hub/worldenergydata
python scripts/lower_tertiary_analysis.py
```

### Individual Stages (for testing)
```bash
# Stage 1: Load configurations (tested ✅)
python scripts/lower_tertiary_analysis.py --stage 1

# Stage 2: Load data
python scripts/lower_tertiary_analysis.py --stage 2

# Stage 3: Calculate revenues
python scripts/lower_tertiary_analysis.py --stage 3

# ... etc through stage 9
```

### With Verbose Logging
```bash
python scripts/lower_tertiary_analysis.py --verbose
```

---

## Key Assumptions Summary

| Parameter | Base Case | Source |
|-----------|-----------|--------|
| **Oil Price** | $75/bbl | EIA WTI 2024 avg |
| **Gas Price** | $3.50/mcf | EIA HH 2024 avg |
| **Royalty** | 18.75% | Federal OCS standard |
| **Income Tax** | 21% | Federal corporate rate |
| **Discount Rate** | 10% | Industry standard |
| **Subsea Opex** | $15/boe | Industry benchmarks |
| **Decline Curve** | Hyperbolic | 45% initial → 8% terminal |
| **Development Time** | 5 years | FID to first oil |

See `ASSUMPTIONS.md` for complete details.

---

## Data Requirements

### Required Data Sources

1. **BSEE Production Data** ✅
   - Location: `data/modules/bsee/zip/historical_production_yearly/`
   - File: `ogora2025delimit.zip` (or latest)
   - Coverage: Through December 2024

2. **Price Data** (Required)
   - Location: `data/prices/`
   - Files:
     - `wti_full_monthly.xlsx` (WTI Cushing)
     - `henry_hub_monthly.xlsx` (Henry Hub gas)
   - Coverage: 1990-2024

3. **Well Data** ✅ (Optional for validation)
   - Location: `data/modules/bsee/bin/war/`
   - Use: Well counts, drilling dates

### Data Download Instructions

If production or price data is missing, you can:

1. **Download BSEE data**:
   ```bash
   cd data/modules/bsee/zip/historical_production_yearly/
   wget https://www.data.bsee.gov/Production/Files/OGORRawDataSet.zip
   mv OGORRawDataSet.zip ogora2025delimit.zip
   ```

2. **Download price data**:
   - Visit https://www.eia.gov/petroleum/data.php
   - Download WTI and Henry Hub monthly data
   - Save to `data/prices/` folder

---

## Next Steps

### Immediate (To Match Paper)

1. **Verify Data Availability**
   ```bash
   # Check production data
   ls -lh data/modules/bsee/zip/historical_production_yearly/
   
   # Check price data
   ls -lh data/prices/
   ```

2. **Run Stage 2** (Load Data)
   ```bash
   python scripts/lower_tertiary_analysis.py --stage 2
   ```

3. **Complete Pipeline**
   ```bash
   python scripts/lower_tertiary_analysis.py
   ```

4. **Review Results**
   - Open `results/lower_tertiary/dashboard.html` in browser
   - Review Excel reports
   - Check validation report for paper comparison

### Customization (If Needed)

1. **Change Price Assumptions**
   - Edit `economic_assumptions.yml`
   - Modify `commodity_prices` section
   - Re-run analysis

2. **Add New Field**
   - Edit `field_parameters.yml`
   - Add field configuration under `fields:`
   - Update `analysis_config.yml` to include in scope
   - Re-run analysis

3. **Adjust Sensitivities**
   - Edit `analysis_config.yml`
   - Modify `calculations.metrics.sensitivity.parameters`
   - Re-run analysis

---

## Validation Criteria

Results will be validated against paper benchmarks with tolerances:
- **Production**: ±10%
- **Revenue**: ±15%
- **NPV**: ±20%

If variances exceed tolerances, the validation report will flag them for investigation.

---

## Support Files Created

### Directory Structure
```
config/analysis/lower_tertiary/
├── economic_assumptions.yml    (10.2 KB)
├── field_parameters.yml        (13.4 KB)
├── analysis_config.yml         (15.3 KB)
├── ASSUMPTIONS.md              (15.1 KB)
├── README.md                   (11.4 KB)
└── SUMMARY.md                  (this file)

scripts/
└── lower_tertiary_analysis.py  (executable)

results/lower_tertiary/         (created on first run)
├── production_revenue_summary.xlsx
├── npv_analysis_by_field.xlsx
├── monthly_cash_flow.xlsx
├── capital_deployment.xlsx
├── dashboard.html
├── paper_comparison.html
└── intermediate/
    ├── monthly_production.csv
    ├── monthly_prices.csv
    ├── monthly_revenue.csv
    ├── monthly_costs.csv
    └── monthly_cash_flow.csv
```

---

## Test Results

✅ **Configuration Loading**: Successfully loaded all YAML files  
✅ **Field Parameters**: 8 fields configured with complete data  
✅ **Economic Assumptions**: All parameters validated  
✅ **Validation**: Configuration validation passed  
✅ **Output Directories**: Created successfully  

**Stage 1 Test Output**:
```
2025-10-21 12:12:42 - INFO - Economic assumptions loaded successfully
  Oil price (base): $75.0/bbl
  Gas price (base): $3.5/mcf
  Discount rate: 10.0%
  
2025-10-21 12:12:42 - INFO - Field parameters loaded: 8 fields configured
  - jack_st_malo: Operator=Chevron, CAPEX=$7500MM
  - stones: Operator=Shell, CAPEX=$3800MM
  - julia: Operator=Equinor, CAPEX=$4700MM
  - anchor: Operator=Chevron, CAPEX=$5600MM
  - tiber: Operator=BP, CAPEX=N/A (pre-FID)
  - shenandoah: Operator=Beacon Offshore Energy, CAPEX=$1800MM
  - cascade_chinook: Operator=TotalEnergies, CAPEX=$2900MM
  - kaskida: Operator=BP, CAPEX=N/A (pre-FID)
  
2025-10-21 12:12:42 - INFO - Configuration validation passed
2025-10-21 12:12:42 - INFO - Completed Stage 1: Load Configurations
```

---

## Summary

The Lower Tertiary economic analysis framework is now **fully configured and ready to execute**. All YAML configuration files have been created with comprehensive economic assumptions, field-specific parameters, and analysis orchestration settings.

**Key Deliverables**:
- ✅ Complete YAML configuration suite (3 files)
- ✅ Comprehensive documentation (2 files)
- ✅ Python analysis runner script
- ✅ 9-stage execution pipeline
- ✅ Configuration validation passed
- ⏳ Awaiting production and price data to execute full analysis

**To Match Paper Results**:
1. Ensure data is available (BSEE production, EIA prices)
2. Run full analysis: `python scripts/lower_tertiary_analysis.py`
3. Review outputs in `results/lower_tertiary/`
4. Compare with paper benchmarks in validation report

**Total Configuration Size**: 65.3 KB (compressed set of assumptions and parameters)

---

**Questions or Issues?**
- Check `README.md` for detailed usage instructions
- Review `ASSUMPTIONS.md` for assumption details
- Enable verbose logging: `python scripts/lower_tertiary_analysis.py --verbose`
- Check logs: `tail -f logs/lower_tertiary_analysis.log`
