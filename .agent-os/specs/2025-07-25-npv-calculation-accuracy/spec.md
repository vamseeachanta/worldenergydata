# Spec Requirements Document

> Spec: NPV Calculation Accuracy Improvement
> Created: 2025-07-25
> Status: Planning

## Overview

Improve NPV calculation accuracy to achieve within 10-20% variance from Excel analysis results, eliminating the current ~50% discrepancy between manual analysis and Excel NPV calculations with the same 10% discount rate.

## User Stories

### Accurate Economic Analysis

As an energy analyst, I want to perform NPV calculations that closely match Excel reference results, so that I can trust the economic evaluation for investment decisions and regulatory reporting.

The current implementation shows significant variance (up to 50%) from Excel NPV analysis using the same input parameters (10% discount rate, same production data, same oil prices). This creates uncertainty in economic evaluation and reduces confidence in automated analysis results.

### Consistent Calculation Methodology

As a data scientist, I want the NPV calculation methodology to exactly mirror Excel's NPV function behavior, so that results are reproducible and can be verified against standard financial analysis tools.

The calculation should handle cash flow timing, discount rate application, and period aggregation in the same manner as Excel's built-in NPV function, ensuring identical results given identical inputs.

## Spec Scope

1. **NPV Calculation Engine Refactoring** - Redesign the NPV calculation to exactly match Excel NPV function behavior
2. **Cash Flow Alignment** - Ensure cash flow construction matches Excel analysis methodology 
3. **Discount Rate Application** - Implement precise discount rate timing and compounding as used in Excel
4. **Data Input Validation** - Verify production data, oil prices, and cost parameters match Excel inputs exactly
5. **Results Validation Framework** - Create automated testing to verify NPV results within 10% of Excel benchmarks

## Out of Scope

- Major changes to production data collection methodology
- Modification of underlying BSEE data processing
- Changes to visualization or reporting components unrelated to NPV accuracy

## Expected Deliverable

1. **NPV calculation accuracy within 10-20% of Excel results** when using identical input parameters
2. **Automated test suite** that validates NPV calculations against Excel benchmarks for multiple scenarios
3. **Documentation** explaining the alignment methodology and any remaining variance sources

## Spec Documentation

- Tasks: @.agent-os/specs/2025-07-25-npv-calculation-accuracy/tasks.md
- Technical Specification: @.agent-os/specs/2025-07-25-npv-calculation-accuracy/sub-specs/technical-spec.md
- Tests Specification: @.agent-os/specs/2025-07-25-npv-calculation-accuracy/sub-specs/tests.md