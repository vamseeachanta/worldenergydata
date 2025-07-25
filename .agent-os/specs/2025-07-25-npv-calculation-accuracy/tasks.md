# Spec Tasks

These are the tasks to be completed for the spec detailed in @.agent-os/specs/2025-07-25-npv-calculation-accuracy/spec.md

> Created: 2025-07-25
> Status: In Progress (Task 3)
> Last Updated: 2025-07-25

## Relevant Files

- NPV Implementation: `src/worldenergydata/modules/bsee/analysis/production_api12.py`
- Test File: `tests/modules/bsee/analysis/query_field_jack_stmalo_npv_test.py`
- Excel Reference: `docs/modules/bsee/data/NPV_JStM-WELL-Production-Data-thru-2019.xlsx`

## Tasks

- [x] 1. Analyze and Document Current NPV Discrepancy Sources
  - [x] 1.1 Write comprehensive tests for current NPV implementation to isolate discrepancy sources
  - [x] 1.2 Create detailed comparison between current implementation and Excel NPV methodology
  - [x] 1.3 Document specific calculation differences (period timing, discount rate application, cash flow construction)
  - [x] 1.4 Verify all tests pass for current implementation baseline

- [x] 2. Implement Excel-Aligned NPV Calculation Engine
  - [x] 2.1 Write tests for new Excel-aligned NPV function with known benchmark results
  - [x] 2.2 Create custom NPV function that exactly mirrors Excel's NPV formula
  - [x] 2.3 Implement proper period timing (Period 0 for CAPEX, Period 1+ for operations)
  - [x] 2.4 Add comprehensive logging for cash flow components and discount rate application
  - [x] 2.5 Verify all tests pass for new NPV implementation

- [ ] 3. Fix Cash Flow Construction and Data Alignment  
  - [ ] 3.1 Write tests for cash flow component calculation (revenue, OPEX, net cash flow)
    - [ ] Test revenue calculation: production volume * oil price
    - [ ] Test OPEX calculation: production volume * OPEX per barrel
    - [ ] Test net cash flow: revenue - OPEX
    - [ ] Test edge cases: zero production, negative prices, missing data
  - [ ] 3.2 Ensure oil price data exactly matches Excel analysis source
    - [ ] Extract BRENT prices from Excel Row 2 (NPV sheet)
    - [ ] Validate price extraction range and values
    - [ ] Implement fallback to external oil price file
    - [ ] Create price data verification utility
  - [ ] 3.3 Verify production data alignment with Excel analysis periods
    - [ ] Extract production data from Excel Row 12
    - [ ] Implement calibration factor for scale matching
    - [ ] Ensure monthly/annual period alignment
    - [ ] Handle data length mismatches gracefully
  - [ ] 3.4 Implement cash flow validation and comparison utilities
    - [ ] Create Excel vs Python calculation comparison function
    - [ ] Add detailed logging for each component
    - [ ] Build variance analysis reporting
    - [ ] Generate visual comparison charts
  - [ ] 3.5 Verify all tests pass for cash flow construction
    - [ ] Run full test suite with new implementation
    - [ ] Ensure <20% variance from Excel benchmarks
    - [ ] Document any remaining discrepancies
    - [ ] Create regression test suite

- [ ] 4. Create NPV Accuracy Validation Framework
  - [ ] 4.1 Write automated tests comparing NPV results against Excel benchmarks
  - [ ] 4.2 Implement benchmark validation for multiple discount rates (8%, 10%, 12%)
  - [ ] 4.3 Create test scenarios for different CAPEX and oil price configurations
  - [ ] 4.4 Add performance benchmarking vs previous implementation
  - [ ] 4.5 Verify all validation tests achieve <20% variance from Excel results

- [ ] 5. Integration and Documentation
  - [ ] 5.1 Write integration tests for complete NPV analysis workflow
  - [ ] 5.2 Update existing NPV calculation method in ProductionAPI12Analysis class
  - [ ] 5.3 Ensure backward compatibility with existing configuration files
  - [ ] 5.4 Create documentation explaining NPV alignment methodology and remaining variance sources
  - [ ] 5.5 Verify all integration tests pass and NPV accuracy requirements are met

## Progress Summary

### Completed
- ✅ Task 1: NPV discrepancy analysis and documentation
- ✅ Task 2: Excel-aligned NPV calculation engine implementation

### In Progress
- 🔄 Task 3: Cash flow construction and data alignment fixes

### Next Steps
1. Begin with Task 3.1 - Write comprehensive tests for cash flow components
2. Focus on accurate data extraction from Excel source (3.2 & 3.3)
3. Build validation utilities to verify improvements (3.4)
4. Complete test validation (3.5)

### Key Success Metrics
- NPV variance from Excel: Target <20% (currently ~50%)
- All tests passing with new implementation
- Comprehensive documentation of methodology