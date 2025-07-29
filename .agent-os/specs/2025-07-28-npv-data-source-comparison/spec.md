# Spec Requirements Document

> Spec: NPV Data Source Comparison and Validation
> Created: 2025-07-28
> Status: Planning

## Overview

Identify and resolve differences between manual analysis data sources (oil production and prices) and Excel benchmark data to ensure NPV calculations use identical input data, building upon the completed NPV calculation accuracy improvements from spec 2025-07-25-npv-calculation-accuracy.

## User Stories

### Data Source Alignment

As an energy analyst, I want to ensure that manual NPV calculations use the exact same production data and oil prices as the Excel benchmarks, so that NPV variance is solely due to calculation methodology rather than input data differences.

The completed NPV accuracy spec showed a 44.55% variance even with improved calculation methodology. This spec focuses on identifying and eliminating data source differences to further reduce this variance to the target <20%.

### Production Data Validation

As a data scientist, I want to validate that production volumes extracted from BSEE systems match the production data used in Excel analysis (Row 22 - JSM Total AVGMoly), so that cash flow calculations are based on identical production inputs.

Current implementation may be using different production data sources or time periods, leading to significant NPV differences even with correct calculation methodology.

## Spec Scope

1. **Production Data Source Analysis** - Compare manual system production data extraction with Excel benchmark production volumes
2. **Oil Price Data Validation** - Verify oil price sources match Excel BRENT prices (Row 2) exactly
3. **Time Period Alignment** - Ensure manual and Excel analyses cover identical time periods with same aggregation
4. **Data Extraction Utilities** - Create robust utilities to extract and validate Excel benchmark data
5. **Comprehensive Comparison Tests** - Build test suite that validates data alignment before NPV calculation

## Out of Scope

- Changes to NPV calculation methodology (already addressed in spec 2025-07-25)
- Modifications to underlying BSEE data processing logic
- Changes to production data collection from original sources
- UI or visualization updates

## Expected Deliverable

1. **Data comparison report** showing exact differences between manual and Excel data sources
2. **Automated test suite** that validates production and price data alignment
3. **Data extraction utilities** that reliably extract benchmark data from Excel for comparison

## Spec Documentation

- Tasks: @.agent-os/specs/2025-07-28-npv-data-source-comparison/tasks.md
- Technical Specification: @.agent-os/specs/2025-07-28-npv-data-source-comparison/sub-specs/technical-spec.md
- Tests Specification: @.agent-os/specs/2025-07-28-npv-data-source-comparison/sub-specs/tests.md