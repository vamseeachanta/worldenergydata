# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-07-29-drilling-days-comparison/spec.md

> Created: 2025-07-29
> Version: 1.0.0

## Technical Requirements

- **Method Execution Framework:** Automated execution of both drilling days calculation methods using existing test infrastructure
- **Data Format Handling:** Support for both Excel (.xlsx) and CSV output formats from the two methods
- **API Number Matching:** Robust matching logic to handle API10 vs API12 formats and ensure proper well alignment
- **Statistical Analysis:** Comprehensive comparison metrics including mean differences, standard deviations, and correlation analysis
- **Report Generation:** Export comparison results to Excel with multiple worksheets for different analysis views
- **Visualization Support:** Integration with matplotlib/plotly for generating comparison charts and scatter plots

## Approach Options

**Option A:** Sequential Test Execution
- Pros: Simple implementation, uses existing test framework, clear separation of methods
- Cons: Longer execution time, requires manual coordination of outputs

**Option B:** Parallel Test Execution with Shared Configuration (Selected)
- Pros: Faster execution, unified configuration management, better resource utilization
- Cons: More complex implementation, potential resource conflicts

**Option C:** Integrated Single Test Method
- Pros: Unified execution, simplified testing
- Cons: Requires significant refactoring of existing methods, breaks current test structure

**Rationale:** Option B provides the best balance of performance and maintainability while leveraging the existing test infrastructure. The parallel execution will significantly reduce total test time while maintaining clear separation between the two calculation methods.

## External Dependencies

- **openpyxl** - Excel file reading and writing for comparison reports
- **Justification:** Required to handle the Excel output format from the lease method and generate comprehensive comparison reports

- **matplotlib** - Chart generation for comparison visualizations
- **Justification:** Already in tech stack, provides robust plotting capabilities for drilling days comparison charts and statistical analysis

- **pandas** - Data manipulation and analysis for comparison logic
- **Justification:** Already in tech stack, essential for dataframe operations and statistical calculations

## Implementation Architecture

### Data Flow Architecture

```
Input YAML Configs
       ↓
Test Execution Framework
       ↓
┌─────────────────────┬─────────────────────┐
│   Lease Method      │    API12 Method     │
│   (Excel Output)    │    (CSV Output)     │
└─────────────────────┴─────────────────────┘
       ↓                         ↓
Data Alignment and Matching Engine
       ↓
Statistical Comparison Analysis
       ↓
Report Generation and Visualization
       ↓
Comparison Results (Excel + Charts)
```

### Core Components

1. **ComparisonTestFramework:** Main orchestrator class that manages test execution
2. **DataAlignmentEngine:** Handles API number matching and data normalization
3. **StatisticalAnalyzer:** Performs comparison calculations and statistical analysis
4. **ReportGenerator:** Creates Excel reports and visualizations
5. **MethodOutputHandler:** Abstracts different output formats (Excel vs CSV)

### File Structure

```
tests/modules/bsee/analysis/
├── drilling_days_comparison_test.py     # Main comparison test
├── comparison_framework/
│   ├── __init__.py
│   ├── data_alignment.py               # API matching logic
│   ├── statistical_analysis.py         # Comparison calculations
│   ├── report_generator.py             # Excel report creation
│   └── visualization.py                # Chart generation
└── fixtures/
    ├── comparison_config.yml            # Test configuration
    └── expected_comparison_schema.yml   # Output validation schema
```

### Configuration Management

The comparison test will use a unified YAML configuration that references both method configurations:

```yaml
meta:
  label: "drilling_days_comparison"
  description: "Comparison of lease vs API12 drilling days methods"

methods:
  lease_method:
    config_file: "drilling_n_completion_days.yml"
    output_file: "drilling_and_completion_days_by_api.xlsx"
    key_columns:
      api: "API_WELL_NUMBER"
      drilling_days: "DRILLING_DAYS" 
      completion_days: "COMPLETION_DAYS"
      spud_date: "WELL_SPUD_DATE"
      td_date: "TOTAL_DEPTH_DATE"
  
  api12_method:
    config_file: "query_api_01_wells_api12_rig_days.yml"
    output_pattern: "block_api12_*.csv"
    key_columns:
      api: "API12"
      drilling_days: "Drilling Days"
      completion_days: "Completion Days" 
      spud_date: "WELL_SPUD_DATE"
      td_date: "TOTAL_DEPTH_DATE"

comparison:
  tolerance:
    drilling_days: 5  # days
    completion_days: 3  # days
    dates: 1  # days
  
  output:
    report_file: "drilling_days_comparison_report.xlsx"
    charts_enabled: true
    statistical_summary: true
```

### Error Handling Strategy

- **Missing Output Files:** Graceful handling with detailed error messages
- **API Number Mismatches:** Comprehensive logging of unmatched wells
- **Data Type Inconsistencies:** Automatic type conversion with validation
- **Statistical Edge Cases:** Proper handling of zero values and missing data