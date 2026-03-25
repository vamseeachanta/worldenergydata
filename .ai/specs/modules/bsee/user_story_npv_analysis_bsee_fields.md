# User Story: NPV Analysis for BSEE Fields

## Issue Reference
- **GitHub Issue**: #46
- **Module**: BSEE
- **Priority**: High
- **Type**: Enhancement/Extension
- **Implementation Status**: 85% Complete

## User Story
As a **petroleum economist/analyst**, I want to **implement NPV analysis for BSEE fields** so that **I can generate comprehensive NPV reports for any BSEE field and save results for further analysis**.

## Description
Implement NPV analysis for BSEE fields with comprehensive results output, multi-field support, and advanced reporting capabilities. The system should be flexible enough to handle any BSEE field configuration.

## Current Implementation Status

### ✅ Base Framework Available
- [x] NPV calculation function framework (`perform_npv_calculation()` in `production_api12.py`)
- [x] Economic parameter configuration structure (OPEX, CAPEX, discount rates)
- [x] Revenue calculation from production data and oil prices
- [x] Monthly cash flow generation and NPV computation
- [x] Test framework foundation
- [x] Basic documentation and methodology structure

## Acceptance Criteria (Remaining Work)

### 1. NPV Results Output Enhancement
- [ ] Save NPV results to CSV files in analysis output directory
- [ ] Generate NPV summary reports with key metrics
- [ ] Create monthly cash flow export functionality
- [ ] Add NPV values to existing well timeline CSV files
- [ ] Integrate NPV metrics into field summary reports

### 2. Multi-Field NPV Analysis
- [ ] Enable NPV calculation for multiple BSEE fields (configurable)
- [ ] Implement field-agnostic NPV configuration system
- [ ] Add support for custom economic parameters per field
- [ ] Create field comparison NPV analysis capability

### 3. Advanced NPV Analysis Features
- [ ] Implement discount rate sensitivity analysis (5%, 10%, 15%)
- [ ] Add CAPEX scenario analysis (base, optimistic, pessimistic)
- [ ] Create NPV visualization charts and sensitivity plots
- [ ] Generate executive summary dashboards

### 4. System Integration
- [ ] Integrate NPV results into existing analysis workflows
- [ ] Add NPV calculation flags to field configuration files
- [ ] Update test suite for new NPV output features
- [ ] Create NPV results validation against external benchmarks

## Technical Requirements

### Implementation Framework
- NPV calculation: `src/worldenergydata/modules/bsee/analysis/production_api12.py`
- Configuration templates: `tests/modules/bsee/analysis/query_field_*_npv.yml`
- Test framework: `tests/modules/bsee/analysis/query_field_*_npv_test.py`
- Documentation: `docs/modules/bsee/analysis/economics/NPV/`

### Enhancement Requirements
- File I/O: CSV/Excel export for NPV results
- Visualization: matplotlib/plotly for NPV charts
- Multi-field: Configuration templates for different fields
- Analysis: Scenario and sensitivity analysis frameworks

### Current Data Sources (Already Integrated)
- Production data: `data/modules/bsee/analysis_data/production.csv`
- Well data: `data/modules/bsee/analysis_data/well_data.csv`
- Oil price data: `data/modules/oil_price/F000000__3m.xls`
- Economic parameters: Configured in YAML files

### New Output Requirements
- NPV results: `tests/modules/bsee/analysis/results/npv_summary.csv`
- Cash flows: `tests/modules/bsee/analysis/results/monthly_cashflows.csv`
- Charts: `tests/modules/bsee/analysis/results/npv_analysis_plots.png`
- Reports: Enhanced summary reports with NPV integration

## Definition of Done
- [ ] NPV results output functionality implemented and tested
- [ ] Multi-field NPV analysis enabled for at least 2 fields
- [ ] Visualization and reporting enhancements completed
- [ ] Integration with existing analysis workflows verified
- [ ] Performance testing with multiple field scenarios
- [ ] Updated documentation reflecting new capabilities
- [ ] All new features covered by automated tests

## Dependencies
- NPV calculation framework (✅ Available)
- Test framework foundation (✅ Available)
- BSEE production and well data (✅ Available)
- Oil price data integration (✅ Available)
- Result file storage permissions
- Visualization library dependencies (matplotlib/plotly)

## Assumptions
- NPV calculation logic framework is sound
- Default economic parameters (OPEX $15/BBL, 10% discount) are reasonable starting points
- Field-agnostic design will support multiple BSEE fields
- Monthly cash flow granularity is sufficient for analysis
- Standard file output formats (CSV, Excel) meet reporting requirements

## Risk Factors
- Performance impact of generating multiple NPV scenarios
- File I/O failures when saving large result datasets
- Visualization rendering issues with complex multi-field plots
- Configuration complexity when adding new fields
- Backward compatibility with existing analysis workflows

## Success Metrics
- NPV calculation completed within specified timeframe
- Results validated with <2% variance between methods
- Complete documentation delivered
- Stakeholder approval of analysis methodology and results

## Related Files
- `docs/modules/bsee/analysis/`
- `tests/modules/bsee/analysis/query_field_{field_name}_npv.yml`
- `tests/modules/bsee/analysis/query_field_{field_name}_npv_test.py`
