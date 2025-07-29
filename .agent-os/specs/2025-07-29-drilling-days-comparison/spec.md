# Spec Requirements Document

> Spec: Drilling Days Test Comparison
> Created: 2025-07-29
> Status: Planning

## User Prompt

> This spec was initiated based on the following user request:

```
Create a test comparison between two drilling days calculation methods:
- Method 1 (lease): Uses tests\modules\bsee\analysis\drilling_n_completion_days_test.py and implements logic in src\worldenergydata\modules\bsee\analysis\custom_scripts\Roy\july\extract_drilling_and_completion_days.py
- Method 2 (api12): Uses tests\modules\bsee\analysis\query_api_01_wells_api12_rig_days_test.py and implements logic in src\worldenergydata\modules\bsee\analysis\well_api12.py

**Key columns to compare in output files:** API number, drilling days, completion days

**Goal:** Write a test that compares both methods' output files and generates a comparison report

**Technical Context:**
- Lease method outputs: drilling_and_completion_days_by_api.xlsx with columns API_WELL_NUMBER, WELL_NAME, WELL_SPUD_DATE, TOTAL_DEPTH_DATE, DRILLING_DAYS, COMPLETION_DAYS
- API12 method outputs: CSV files with columns API12, WELL_SPUD_DATE, TOTAL_DEPTH_DATE, Drilling Days, Completion Days
- Both methods process BSEE well data but use different approaches (lease-based vs API12-based filtering)
- Need automated comparison framework to validate consistency between methods
```

## Overview

Create an automated testing framework that compares the output of two different drilling days calculation methods to validate data consistency and identify discrepancies between lease-based and API12-based approaches for BSEE well data analysis.

## User Stories

### Drilling Data Quality Assurance

As a data analyst working with BSEE drilling data, I want to compare the outputs of two different drilling days calculation methods, so that I can ensure data consistency and identify potential issues in either approach.

The system will automatically run both methods, compare their outputs on common wells, and generate a detailed comparison report showing matches, discrepancies, and statistical analysis of the differences.

### Method Validation and Benchmarking

As a petroleum engineer validating drilling analysis methods, I want to systematically compare lease-based vs API12-based calculation approaches, so that I can understand which method provides more accurate or consistent results for economic evaluation.

The framework will provide detailed metrics on calculation differences, highlight wells with significant discrepancies, and generate visualizations to help understand patterns in the data differences.

## Spec Scope

1. **Automated Test Execution** - Framework to run both drilling days calculation methods and collect their outputs
2. **Data Alignment and Matching** - Logic to match wells between the two methods' outputs using API numbers
3. **Comprehensive Comparison Analysis** - Statistical comparison of drilling days, completion days, and date fields
4. **Discrepancy Reporting** - Detailed reports highlighting wells with significant differences between methods
5. **Visualization Dashboard** - Charts and graphs showing comparison results and patterns in discrepancies

## Out of Scope

- Modifying the existing calculation logic within either method
- Creating new drilling days calculation approaches
- Real-time monitoring or continuous comparison workflows
- Integration with external data validation systems

## Expected Deliverable

1. **Comparison Test Framework** - Automated test that runs both methods and compares outputs in the browser
2. **Detailed Comparison Report** - Excel/CSV output showing side-by-side comparison of all matched wells
3. **Statistical Summary** - Summary statistics of differences and correlation analysis between methods

## Spec Documentation

- File Locations Guide: @.agent-os/specs/2025-07-29-drilling-days-comparison/spec_file_locations.md
- Tasks: @.agent-os/specs/2025-07-29-drilling-days-comparison/tasks.md
- Technical Specification: @.agent-os/specs/2025-07-29-drilling-days-comparison/sub-specs/technical-spec.md
- Tests Specification: @.agent-os/specs/2025-07-29-drilling-days-comparison/sub-specs/tests.md