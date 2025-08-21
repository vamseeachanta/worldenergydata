# Spec Tasks

These are the tasks to be completed for the spec detailed in @specs/modules/analysis/2025-08-21-enhanced-bsee-testing/spec.md

> Module: bsee/analysis
> Created: 2025-08-21
> Status: Ready for Implementation
> Type: Enhanced

## Module Tasks

### Module Setup
- [ ] **MS-1**: Create august directory structure `[30min]`
  - [ ] MS-1.1: Create src/worldenergydata/modules/bsee/analysis/custom_scripts/Roy/august/
  - [ ] MS-1.2: Add __init__.py with module exports
  - [ ] MS-1.3: Create test directory structure
  - [ ] MS-1.4: Verify module imports work correctly

### Task Group 1: Enhanced Drilling & Completion Days Implementation

- [ ] **DC-1**: Prepare test data and configuration `[1hr]`
  - [ ] DC-1.1: Write unit tests for binary file loading
  - [ ] DC-1.2: Copy docs/.../leases.xlsx to tests/.../leases_enhanced.xlsx
  - [ ] DC-1.3: Create drilling_completion_days_config_enhanced.yml
  - [ ] DC-1.4: Verify binary WAR files exist in data/modules/bsee/bin/war/
  - [ ] DC-1.5: Set up test fixtures for validation

- [ ] **DC-2**: Convert script to enhanced class format `[2hr]`
  - [ ] DC-2.1: Create ExtractDrillingCompletionEnhanced class structure
  - [ ] DC-2.2: Implement __init__ and router methods
  - [ ] DC-2.3: Convert procedural code to class methods
  - [ ] DC-2.4: Add comprehensive logging
  - [ ] DC-2.5: Implement error handling

- [ ] **DC-3**: Implement binary file support `[1.5hr]`
  - [ ] DC-3.1: Replace CSV reading with pickle.load()
  - [ ] DC-3.2: Update file paths to binary locations
  - [ ] DC-3.3: Maintain data transformation logic
  - [ ] DC-3.4: Add binary file validation
  - [ ] DC-3.5: Test binary loading performance

- [ ] **DC-4**: Integrate with custom router `[45min]`
  - [ ] DC-4.1: Import enhanced class in custom_router.py
  - [ ] DC-4.2: Add drilling_completion_enhanced flag condition
  - [ ] DC-4.3: Initialize class instance
  - [ ] DC-4.4: Test routing logic
  - [ ] DC-4.5: Verify configuration passing

- [ ] **DC-5**: Validate output against reference `[1hr]`
  - [ ] DC-5.1: Run enhanced analysis
  - [ ] DC-5.2: Load reference output file
  - [ ] DC-5.3: Compare row counts
  - [ ] DC-5.4: Validate first 5 rows of data
  - [ ] DC-5.5: Document any acceptable variations
  - [ ] DC-5.6: Ensure all tests pass

### Task Group 2: Month Matrix Builder Implementation

- [ ] **MM-1**: Prepare matrix generation environment `[45min]`
  - [ ] MM-1.1: Write unit tests for OGORA processing
  - [ ] MM-1.2: Verify OGORA zip files in historical_production_yearly/
  - [ ] MM-1.3: Create month_matrix_config_enhanced.yml if needed
  - [ ] MM-1.4: Set up test data for matrix validation

- [ ] **MM-2**: Convert to enhanced class structure `[2hr]`
  - [ ] MM-2.1: Create BuildMonthMatrixEnhanced class
  - [ ] MM-2.2: Implement router interface
  - [ ] MM-2.3: Convert main logic to class methods
  - [ ] MM-2.4: Add lease grouping logic
  - [ ] MM-2.5: Implement sheet generation

- [ ] **MM-3**: Implement OGORA file processing `[1.5hr]`
  - [ ] MM-3.1: Direct zip file reading without extraction
  - [ ] MM-3.2: Process multiple year patterns
  - [ ] MM-3.3: Handle encoding variations
  - [ ] MM-3.4: Aggregate production data
  - [ ] MM-3.5: Calculate BBL/day metrics

- [ ] **MM-4**: Add router integration `[30min]`
  - [ ] MM-4.1: Import matrix class in custom_router.py
  - [ ] MM-4.2: Add month_matrix_enhanced flag condition
  - [ ] MM-4.3: Test routing execution
  - [ ] MM-4.4: Verify output generation

- [ ] **MM-5**: Validate matrix output `[45min]`
  - [ ] MM-5.1: Execute matrix generation
  - [ ] MM-5.2: Compare sheet count with reference
  - [ ] MM-5.3: Validate column headers (YYYY-MM)
  - [ ] MM-5.4: Check production values
  - [ ] MM-5.5: Ensure all tests pass

### Task Group 3: Development Financials Implementation

- [ ] **FN-1**: Prepare financial analysis setup `[1hr]`
  - [ ] FN-1.1: Write unit tests for NPV/MIRR calculations
  - [ ] FN-1.2: Verify all input files available
  - [ ] FN-1.3: Create financials_config_enhanced.yml
  - [ ] FN-1.4: Set up assumptions file
  - [ ] FN-1.5: Prepare WTI data if needed

- [ ] **FN-2**: Convert to enhanced class format `[2.5hr]`
  - [ ] FN-2.1: Create BuildDevelopmentFinancialsEnhanced class
  - [ ] FN-2.2: Implement complex initialization
  - [ ] FN-2.3: Convert financial logic to methods
  - [ ] FN-2.4: Maintain calculation accuracy
  - [ ] FN-2.5: Add comprehensive error handling

- [ ] **FN-3**: Implement financial calculations `[2hr]`
  - [ ] FN-3.1: NPV calculation with monthly discounting
  - [ ] FN-3.2: MIRR with finance/reinvestment rates
  - [ ] FN-3.3: CAPEX allocation logic
  - [ ] FN-3.4: Tax calculations
  - [ ] FN-3.5: Cash flow generation

- [ ] **FN-4**: Integrate with router `[30min]`
  - [ ] FN-4.1: Import financial class in custom_router.py
  - [ ] FN-4.2: Add financials_enhanced flag condition
  - [ ] FN-4.3: Test complete execution
  - [ ] FN-4.4: Verify all sheets generated

- [ ] **FN-5**: Validate financial outputs `[1.5hr]`
  - [ ] FN-5.1: Run financial analysis
  - [ ] FN-5.2: Compare NPV with reference (tolerance: $1000)
  - [ ] FN-5.3: Compare MIRR with reference (tolerance: 0.001)
  - [ ] FN-5.4: Validate all summary sheets
  - [ ] FN-5.5: Check QC reconciliation tabs
  - [ ] FN-5.6: Ensure all tests pass

### Task Group 4: Integration and End-to-End Testing

- [ ] **IT-1**: Module integration testing `[1.5hr]`
  - [ ] IT-1.1: Write integration test suite
  - [ ] IT-1.2: Test drilling to matrix data flow
  - [ ] IT-1.3: Test matrix to financials data flow
  - [ ] IT-1.4: Verify router handles all flags correctly
  - [ ] IT-1.5: Test error propagation

- [ ] **IT-2**: End-to-end workflow execution `[2hr]`
  - [ ] IT-2.1: Execute complete three-stage workflow
  - [ ] IT-2.2: Verify data dependencies satisfied
  - [ ] IT-2.3: Check intermediate file generation
  - [ ] IT-2.4: Validate final outputs
  - [ ] IT-2.5: Performance benchmarking

- [ ] **IT-3**: Reference validation suite `[1.5hr]`
  - [ ] IT-3.1: Load all reference files
  - [ ] IT-3.2: Compare all enhanced outputs
  - [ ] IT-3.3: Generate validation report
  - [ ] IT-3.4: Document any variations
  - [ ] IT-3.5: Create summary metrics

- [ ] **IT-4**: Performance optimization `[1hr]`
  - [ ] IT-4.1: Profile code execution
  - [ ] IT-4.2: Identify bottlenecks
  - [ ] IT-4.3: Optimize critical paths
  - [ ] IT-4.4: Verify memory usage < 2GB
  - [ ] IT-4.5: Ensure total runtime < 5 minutes

### Task Group 5: Documentation and Finalization

- [ ] **DF-1**: Code documentation `[1hr]`
  - [ ] DF-1.1: Add comprehensive docstrings
  - [ ] DF-1.2: Include usage examples
  - [ ] DF-1.3: Document configuration parameters
  - [ ] DF-1.4: Add inline comments for complex logic
  - [ ] DF-1.5: Create module README

- [ ] **DF-2**: Test documentation `[45min]`
  - [ ] DF-2.1: Document test coverage
  - [ ] DF-2.2: Create test execution guide
  - [ ] DF-2.3: Document validation criteria
  - [ ] DF-2.4: Add performance benchmarks
  - [ ] DF-2.5: Create troubleshooting guide

- [ ] **DF-3**: Final validation `[1hr]`
  - [ ] DF-3.1: Run complete test suite
  - [ ] DF-3.2: Verify all deliverables present
  - [ ] DF-3.3: Check code quality metrics
  - [ ] DF-3.4: Validate against spec requirements
  - [ ] DF-3.5: Generate final summary report

## Task Summary

### Time Estimates
- Module Setup: 30 minutes
- Drilling & Completion: 6.25 hours
- Month Matrix: 5 hours
- Financials: 7.5 hours
- Integration Testing: 6 hours
- Documentation: 2.75 hours
- **Total Estimated Time: ~28 hours (3.5-4 days)**

### Dependencies
- MM tasks depend on DC completion for testing
- FN tasks depend on MM completion for input data
- IT tasks depend on all implementation tasks
- DF tasks can partially overlap with implementation

### Critical Path
1. MS-1 → DC-1 → DC-2 → DC-3 → DC-4 → DC-5
2. MM-1 → MM-2 → MM-3 → MM-4 → MM-5
3. FN-1 → FN-2 → FN-3 → FN-4 → FN-5
4. IT-1 → IT-2 → IT-3 → IT-4
5. DF-1 → DF-2 → DF-3

### Risk Mitigation
- Early validation of binary file availability
- Incremental testing at each stage
- Reference data validation throughout
- Performance monitoring from start