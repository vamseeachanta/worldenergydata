# Spec Tasks

These are the tasks to be completed for the spec detailed in @.agent-os/specs/2025-07-29-drilling-days-comparison/spec.md

> Created: 2025-07-29
> Status: Ready for Implementation

## Tasks

- [x] 1. Create Comparison Test Framework
  - [x] 1.1 Write tests for DrillingDaysComparisonTest class
  - [x] 1.2 Implement test configuration YAML file
  - [x] 1.3 Create base comparison test structure with pytest integration
  - [x] 1.4 Implement test discovery and execution logic
  - [x] 1.5 Verify all tests pass

- [ ] 2. Implement Data Loading Components
  - [ ] 2.1 Write tests for ComparisonDataLoader class
  - [ ] 2.2 Implement Excel file loader for Method 1 outputs
  - [ ] 2.3 Implement CSV file loader for Method 2 outputs
  - [ ] 2.4 Add data validation and error handling
  - [ ] 2.5 Implement column name standardization logic
  - [ ] 2.6 Verify all tests pass

- [ ] 3. Build Comparison Analysis Engine
  - [ ] 3.1 Write tests for ComparisonAnalyzer class
  - [ ] 3.2 Implement API12 matching logic between datasets
  - [ ] 3.3 Create drilling days and completion days difference calculations
  - [ ] 3.4 Implement discrepancy detection and flagging logic
  - [ ] 3.5 Add percentage difference calculations
  - [ ] 3.6 Verify all tests pass

- [ ] 4. Develop Markdown Report Generator
  - [ ] 4.1 Write tests for MarkdownReportGenerator class
  - [ ] 4.2 Implement markdown table formatting logic
  - [ ] 4.3 Create column alignment and spacing functionality
  - [ ] 4.4 Add status flag generation (OK/REVIEW/ERROR)
  - [ ] 4.5 Implement file output handling
  - [ ] 4.6 Verify all tests pass

- [ ] 5. Integration Testing and Validation
  - [ ] 5.1 Write integration tests for complete workflow
  - [ ] 5.2 Test with actual Tiber field data (API12: 608084001500)
  - [ ] 5.3 Validate comparison accuracy against known reference data
  - [ ] 5.4 Test edge cases and error conditions
  - [ ] 5.5 Verify generated markdown reports are properly formatted
  - [ ] 5.6 Verify all tests pass

- [ ] 6. CSV Output Generation for Future Use
  - [ ] 6.1 Write tests for CSV export functionality
  - [ ] 6.2 Implement CSV export for comparison results with all drilling/completion days data
  - [ ] 6.3 Create standardized CSV format with columns:
    - API12_number, Well_name, Method_1_drilling_days, Method_2_drilling_days
    - Method_1_completion_days, Method_2_completion_days
    - Drilling_days_difference, Completion_days_difference
    - Drilling_days_percent_diff, Completion_days_percent_diff
    - Status_flag, Notes
  - [ ] 6.4 Save individual method outputs as separate CSV files:
    - drilling_days_lease_method_YYYYMMDD.csv
    - drilling_days_api12_method_YYYYMMDD.csv
    - drilling_days_comparison_YYYYMMDD.csv
  - [ ] 6.5 Implement CSV file naming with timestamps for version control
  - [ ] 6.6 Add CSV metadata headers with processing date and method details
  - [ ] 6.7 Create CSV files in results directory for easy access and future analysis
  - [ ] 6.8 Verify CSV output accuracy and data integrity
  - [ ] 6.9 Test CSV import/export compatibility with Excel and pandas
  - [ ] 6.10 Verify all CSV generation tests pass