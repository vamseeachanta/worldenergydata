# Lower Tertiary Economic Analysis

## Overview

This analysis framework calculates production revenues, NPV, IRR, and other economic metrics for Lower Tertiary subsea field developments in the Gulf of Mexico. The analysis is designed to reproduce and match the outputs from the "Industry Performance in Lower Tertiary" paper (October 2020).

## Quick Start

### Prerequisites
- Python 3.11+
- Required packages installed (`uv sync` or `pip install -r requirements.txt`)
- BSEE production data downloaded
- Price data (WTI, Henry Hub) available

### Run the Analysis

```bash
# Full analysis (all stages)
python scripts/lower_tertiary_analysis.py

# Run specific stage
python scripts/lower_tertiary_analysis.py --stage 3

# Verbose output
python scripts/lower_tertiary_analysis.py --verbose
```

## Configuration Files

### 1. `economic_assumptions.yml`
**Purpose**: Core economic parameters used across all fields

**Key sections**:
- Commodity prices (oil, gas, NGL)
- Fiscal terms (royalties, taxes)
- Capital expenditure assumptions
- Operating expenditure assumptions
- Production assumptions (decline curves)
- Financial metrics (discount rates, IRR targets)

**Usage**: Rarely needs modification unless changing base economic assumptions

### 2. `field_parameters.yml`
**Purpose**: Field-specific data for each Lower Tertiary development

**Contains**:
- Location and operator information
- Partnership structure
- Key dates (discovery, FID, first oil)
- Development concept and capacity
- Actual capital costs (from disclosures)
- Reserve estimates
- Production profiles

**Fields included**:
- Jack/St. Malo
- Stones
- Julia
- Anchor
- Cascade/Chinook
- Shenandoah
- Tiber (pre-FID)
- Kaskida (pre-FID)

**Usage**: Update when new field data is disclosed or for adding new fields

### 3. `analysis_config.yml`
**Purpose**: Main orchestration configuration

**Defines**:
- Analysis scope (time periods, fields to analyze)
- Data sources and paths
- Calculation methods
- Output specifications
- Pipeline execution stages
- Validation criteria

**Usage**: Configure what gets analyzed and how results are presented

## Analysis Pipeline

The analysis runs through 9 stages:

### Stage 1: Load Configurations
- Load economic assumptions
- Load field parameters
- Validate configuration files

### Stage 2: Load Data
- BSEE production data (monthly by lease)
- Historical price data (WTI, Henry Hub)
- Well and drilling data
- Data quality validation

### Stage 3: Calculate Revenues
- Oil revenue = Production × WTI price
- Gas revenue = Production × Henry Hub price (with basis differential)
- NGL revenue = Gas production × yield × NGL price
- Total revenue aggregation

### Stage 4: Calculate Costs
- Royalties (18.75% of gross revenue)
- Operating costs (fixed + variable)
- Depreciation (straight-line over 10 years)
- Income tax (21% of net income)

### Stage 5: Calculate Cash Flows
- Operating cash flow = Revenue - Royalty - Opex - Tax
- Free cash flow = Operating cash flow - Capex
- Cumulative cash flow (running sum from FID)

### Stage 6: Calculate Financial Metrics
- NPV at 10%, 8%, and 15% discount rates
- Internal rate of return (IRR)
- Payback period (discounted and undiscounted)
- Profitability index (NPV/CAPEX)

### Stage 7: Run Sensitivities
- Oil price sensitivity (±20%, ±30%)
- Gas price sensitivity (±20%, ±30%)
- Production/EUR sensitivity (±20%)
- Operating cost sensitivity (±20%)
- Capital cost sensitivity (±20%)

### Stage 8: Generate Reports
- Excel reports (tables and summaries)
- HTML interactive dashboard (Plotly charts)
- Validation report (vs. paper benchmarks)
- Export intermediate data (CSV, JSON)

### Stage 9: Validate Results
- Compare with paper benchmarks
- Document all assumptions
- Generate final summary

## Output Files

### Primary Reports (Excel)
Located in `results/lower_tertiary/`:

1. **`production_revenue_summary.xlsx`**
   - Annual production and revenue by field
   - Oil, gas, NGL breakdown
   - Subtotals and grand totals

2. **`npv_analysis_by_field.xlsx`**
   - NPV at multiple discount rates
   - IRR and payback period
   - Profitability index
   - Ranked by NPV10

3. **`monthly_cash_flow.xlsx`**
   - Monthly time series for each field
   - Production, revenue, costs, cash flow
   - Cumulative metrics

4. **`capital_deployment.xlsx`**
   - Annual capital expenditure schedule
   - By category: exploration, development, abandonment

### Interactive Dashboard (HTML)
- **`dashboard.html`**: Plotly-based interactive dashboard
  - Executive summary metrics
  - Production charts (area, bar, line)
  - Financial performance (waterfall, scatter, tornado)
  - Unit economics comparisons
  - Sensitivity analysis

### Validation Report
- **`paper_comparison.html`**: 
  - Side-by-side comparison with paper results
  - Variance analysis
  - Assumptions reconciliation

### Intermediate Data
Located in `results/lower_tertiary/intermediate/`:
- `monthly_production.csv`
- `monthly_prices.csv`
- `monthly_revenue.csv`
- `monthly_costs.csv`
- `monthly_cash_flow.csv`
- `npv_calculations.csv`

## Key Assumptions

### Economic Assumptions
- **Oil Price**: $75/bbl (2024 base case)
- **Gas Price**: $3.50/mcf (2024 base case)
- **Royalty Rate**: 18.75% (federal OCS standard)
- **Income Tax**: 21% (federal corporate rate)
- **Discount Rate**: 10% (primary)
- **Opex**: ~$15/boe (subsea development)

### Production Assumptions
- **Decline Curve**: Hyperbolic (45% initial, 8% terminal)
- **Type Curve**: Based on actual field performance where available
- **EUR per Well**: 8-18 MMBOE (P10-P90)
- **GOR**: 800-1,500 scf/bbl (increasing over time)

### Capital Assumptions
- **Development CAPEX**: $1,800-3,200 million per field (actual disclosed values used)
- **Well Cost**: $200-350 million per well
- **FID to First Oil**: 5 years typical
- **Abandonment**: 10% of development CAPEX

See [`ASSUMPTIONS.md`](ASSUMPTIONS.md) for complete documentation.

## Data Sources

### Production Data
- **Source**: Bureau of Safety and Environmental Enforcement (BSEE)
- **Dataset**: Monthly production reports (OGOR-A)
- **Path**: `data/modules/bsee/zip/historical_production_yearly/`
- **Coverage**: Through December 2024

### Price Data
- **Oil**: EIA WTI Cushing monthly spot prices
- **Gas**: EIA Henry Hub monthly spot prices
- **Path**: `data/prices/`
- **Coverage**: 1990-2024

### Cost and Field Data
- **Source**: Public disclosures (SEC filings, press releases, investor presentations)
- **Reliability**: High for producing fields; estimates for pre-FID fields
- **Documented in**: `field_parameters.yml`

## Validation

### Benchmark Comparison
Results are validated against expected values from the Industry Performance paper:

| Field | Cumulative Production | Cumulative Revenue | NPV10 |
|-------|----------------------|-------------------|-------|
| Jack/St. Malo | ~150 MMBOE | ~$8,000 MM | ~$3,500 MM |
| Stones | ~80 MMBOE | ~$4,500 MM | ~$2,000 MM |
| Julia | ~50 MMBOE | ~$2,800 MM | ~$1,200 MM |

**Tolerance**: ±10% on production, ±15% on revenue, ±20% on NPV

### Quality Checks
- Production data: No negative values, no impossible spikes
- Price data: Within historical bounds ($20-150/bbl)
- Cost data: Within industry benchmarks (±30%)
- Decline curves: Physically reasonable (DI < 95%/year)
- NPV/CAPEX: Should be >0.3 for commercial projects
- IRR: Should be >15% for sanctioned projects

## Customization

### Adding a New Field

1. **Update `field_parameters.yml`**:
```yaml
fields:
  my_new_field:
    field_names:
      - "My New Field"
    operator: "Operator Name"
    location:
      boem_field_codes:
        - "XXnnn"
      # ... other parameters
```

2. **Add to analysis scope in `analysis_config.yml`**:
```yaml
analysis_scope:
  fields_to_analyze:
    producing:
      - my_new_field
```

3. **Run analysis**:
```bash
python scripts/lower_tertiary_analysis.py --field my_new_field
```

### Changing Economic Assumptions

Edit `economic_assumptions.yml`:
```yaml
commodity_prices:
  oil:
    base_case:
      wti_usd_per_bbl: 80.00  # Change from 75.00
```

Re-run analysis to see updated results.

### Running Sensitivity Cases

Sensitivity parameters are defined in `analysis_config.yml`:
```yaml
calculations:
  metrics:
    sensitivity:
      enabled: true
      parameters:
        - oil_price: [-30, -20, -10, 0, 10, 20, 30]
```

Results appear in the interactive dashboard's "Sensitivity Analysis" section.

## Troubleshooting

### Common Issues

**1. Missing production data**
```
Error: Production data not found for lease G24030
```
**Solution**: Verify BSEE data is downloaded to `data/modules/bsee/zip/historical_production_yearly/`

**2. Price data errors**
```
Error: WTI prices missing for date 2024-01-01
```
**Solution**: Check `data/prices/wti_full_monthly.xlsx` has complete data through Dec 2024

**3. Configuration validation errors**
```
Error: Missing required section: data_sources
```
**Solution**: Ensure all three YAML files (`economic_assumptions.yml`, `field_parameters.yml`, `analysis_config.yml`) are present and valid

**4. Memory issues with large datasets**
```
MemoryError: Unable to allocate array
```
**Solution**: Enable chunking in `analysis_config.yml`:
```yaml
processing:
  performance:
    chunk_size: 10000
    use_parallel: true
```

### Debug Mode

Enable verbose logging:
```bash
python scripts/lower_tertiary_analysis.py --verbose
```

Check log file:
```bash
tail -f logs/lower_tertiary_analysis.log
```

## Advanced Usage

### Running Individual Stages

For development or debugging, run individual stages:
```bash
# Load and validate data only
python scripts/lower_tertiary_analysis.py --stage 2

# Calculate revenues only
python scripts/lower_tertiary_analysis.py --stage 3

# Generate reports only (assumes prior stages completed)
python scripts/lower_tertiary_analysis.py --stage 8
```

### Using Checkpoints

The pipeline saves checkpoints after each stage:
```
checkpoints/lower_tertiary/stage_1.pkl
checkpoints/lower_tertiary/stage_2.pkl
...
```

To resume from a checkpoint, modify the execution plan in `analysis_config.yml`.

### Parallel Processing

For large datasets, enable parallel processing:
```yaml
processing:
  performance:
    use_parallel: true
    max_workers: 4  # Adjust based on CPU cores
```

## Support and Contributing

### Getting Help
- Check [`ASSUMPTIONS.md`](ASSUMPTIONS.md) for detailed assumption documentation
- Review example outputs in `results/lower_tertiary/`
- Enable verbose logging for debugging

### Contributing
To add new features or fix issues:
1. Create a feature branch
2. Update relevant YAML configuration
3. Test with existing fields
4. Document changes in `ASSUMPTIONS.md`
5. Submit pull request

## References

1. **Industry Paper**: "Industry Performance in Lower Tertiary" (October 2020)
2. **BSEE Data**: https://www.data.bsee.gov/
3. **EIA Petroleum Data**: https://www.eia.gov/petroleum/
4. **Field Disclosures**: SEC EDGAR filings, operator websites

---

## Version History

- **v1.0.0** (2024-12-20): Initial configuration framework
  - 8 fields configured (Jack/St. Malo, Stones, Julia, Anchor, Cascade/Chinook, Shenandoah, Tiber, Kaskida)
  - Complete economic assumptions
  - 9-stage analysis pipeline
  - Excel and HTML reporting
  - Benchmark validation

---

**Last Updated**: 2024-12-20  
**Configuration Version**: 1.0.0  
**Compatible with**: worldenergydata module v3.0+
