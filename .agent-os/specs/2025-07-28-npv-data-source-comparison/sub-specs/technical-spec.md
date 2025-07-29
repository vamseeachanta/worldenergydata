# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-07-28-npv-data-source-comparison/spec.md

> Created: 2025-07-28
> Version: 1.0.0

## Technical Requirements

### Data Source Identification
- Identify exact data sources used in manual NPV calculations
  - Production data extraction from BSEE database
  - Oil price data sources (internal vs external)
  - Time period coverage and aggregation methods
- Map Excel benchmark data structure
  - Production data location (Row 22 - JSM Total AVGMoly)
  - Oil price data location (Row 2 - BRENT prices)
  - Time period coverage in Excel analysis

### Data Extraction Requirements
- Excel data extraction utilities must:
  - Read specific rows/columns from NPV_JStM-WELL-Production-Data-thru-2019.xlsx
  - Handle different data formats (numbers, currency, percentages)
  - Validate data integrity and completeness
  - Support multiple sheet extraction if needed

### Data Comparison Framework
- Compare production volumes month-by-month
- Compare oil prices period-by-period
- Identify:
  - Missing data points
  - Scale differences (e.g., daily vs monthly production)
  - Time period misalignments
  - Unit differences (BBL vs MMBBL)

### Performance Requirements
- Data extraction should complete within 2 seconds
- Comparison analysis should handle up to 360 months of data
- Memory efficient processing for large datasets

## Approach Options

**Option A:** Direct Excel Integration
- Pros: Exact data match, single source of truth
- Cons: Excel dependency, slower processing

**Option B:** Cached Data Approach (Selected)
- Pros: Fast processing, version control for data, testable
- Cons: Requires synchronization with Excel updates

**Rationale:** Option B selected for better testing capabilities and performance while maintaining data accuracy through validation.

## External Dependencies

- **openpyxl** - Already in use for Excel file reading
- **pandas** - Already in use for data manipulation
- **numpy** - Already in use for numerical operations

No new external dependencies required.