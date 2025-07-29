# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/2025-07-29-drilling-days-comparison/spec.md

> Created: 2025-07-29
> Version: 1.0.0

## Test Coverage

### Unit Tests

**DataAlignmentEngine**
- Test API10 to API12 conversion logic
- Test well matching with exact API matches
- Test well matching with fuzzy API matching for data quality issues
- Test handling of duplicate API numbers
- Test data normalization for different date formats

**StatisticalAnalyzer**
- Test drilling days difference calculations
- Test completion days difference calculations
- Test correlation analysis between methods
- Test statistical summary generation (mean, median, std dev)
- Test percentage difference calculations
- Test tolerance-based matching logic

**ReportGenerator**
- Test Excel workbook creation with multiple sheets
- Test chart generation for drilling days comparisons
- Test statistical summary report formatting
- Test handling of large datasets in Excel output

**MethodOutputHandler**
- Test Excel file reading from lease method
- Test CSV file reading from API12 method (multiple files)
- Test data type conversion and validation
- Test handling of missing or corrupted output files

### Integration Tests

**End-to-End Comparison Workflow**
- Test complete comparison workflow from method execution to report generation
- Test parallel execution of both drilling days methods
- Test data alignment between different output formats
- Test generation of comprehensive comparison report

**Configuration Management**
- Test YAML configuration parsing for comparison parameters
- Test method-specific configuration handling
- Test tolerance settings application in comparisons
- Test output file path resolution

**Data Processing Pipeline**
- Test extraction of drilling days data from both methods
- Test date parsing and normalization across different formats
- Test API number standardization and matching
- Test statistical analysis pipeline from raw data to summary metrics

### Feature Tests

**Method Execution and Output Collection**
- Execute lease method test and verify drilling_and_completion_days_by_api.xlsx is generated
- Execute API12 method test and verify block_api12_*.csv files are generated
- Verify output files contain expected columns and data types
- Test handling of method execution failures

**Data Comparison and Analysis**
- Compare drilling days values between methods for common wells
- Compare completion days values between methods for common wells
- Identify wells with significant discrepancies (beyond tolerance)
- Generate statistical summaries of differences

**Report Generation and Visualization**
- Create Excel comparison report with side-by-side well data
- Generate scatter plots showing drilling days correlation between methods
- Create histogram of drilling days differences
- Generate summary statistics worksheet

### Mocking Requirements

**File System Operations**
- **Mock file reading operations:** Use pytest fixtures to provide sample Excel and CSV data
- **Mock file writing operations:** Capture and validate output file generation

**External Method Execution**
- **Mock engine() calls:** Simulate both drilling days methods without full execution
- **Mock test execution:** Provide controlled test environments with known data

**Date and Time Operations**
- **Mock datetime functions:** Ensure consistent test execution timing
- **Mock file timestamps:** Control file modification times for comparison logic

### Test Data Strategy

**Sample Data Sets**
- Create representative BSEE well data covering various scenarios
- Include wells with complete drilling and completion data
- Include wells with missing or partial data
- Include wells with edge cases (zero drilling days, very long completion periods)

**Expected Results Validation**
- Define expected comparison results for sample data sets
- Create validation schemas for comparison report structure
- Establish baseline statistical metrics for regression testing

### Performance Testing

**Large Dataset Handling**
- Test comparison framework with datasets containing 100+ wells
- Validate memory usage during large Excel file processing
- Test report generation time with extensive comparison data

**Concurrent Execution**
- Test parallel method execution under various system loads
- Validate data integrity when methods run simultaneously
- Test resource cleanup after comparison completion

### Error Handling Tests

**Missing or Corrupted Input Files**
- Test behavior when lease method Excel file is missing
- Test behavior when API12 method CSV files are corrupted
- Test graceful degradation when partial data is available

**Data Quality Issues**
- Test handling of invalid API numbers
- Test processing of malformed date fields
- Test behavior with negative drilling days values
- Test handling of wells present in only one method's output

**Configuration Errors**
- Test invalid tolerance settings in configuration
- Test missing required configuration parameters
- Test malformed YAML configuration files