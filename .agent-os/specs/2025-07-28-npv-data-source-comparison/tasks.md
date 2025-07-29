# Spec Tasks

These are the tasks to be completed for the spec detailed in @.agent-os/specs/2025-07-28-npv-data-source-comparison/spec.md

> Created: 2025-07-28
> Status: Ready for Implementation

## Tasks

- [x] 1. Create Excel Data Extraction Utilities
  - [x] 1.1 Write tests for Excel data extraction functions
  - [x] 1.2 Implement production data extraction from Row 22 (JSM Total AVGMoly)
  - [x] 1.3 Implement oil price extraction from Row 4 (BRENT prices - corrected from Row 2)
  - [x] 1.4 Add data validation and error handling
  - [x] 1.5 Verify all extraction tests pass (14/14 tests passing)

- [x] 2. Analyze Excel Data Characteristics
  - [x] 2.1 Extract and validate Excel benchmark data (55 periods)
  - [x] 2.2 Calculate average production (33,938 BBL/period)
  - [x] 2.3 Calculate average oil price ($56.60/BBL)
  - [x] 2.4 Identify data represents DAILY production, not monthly
  - [x] 2.5 Document total revenue potential ($106M)

- [x] 3. Build NPV Comparison Framework
  - [x] 3.1 Create NPV calculation using Excel data
  - [x] 3.2 Calculate NPV with same parameters as manual analysis
  - [x] 3.3 Identify 44.2% variance from Excel benchmark
  - [x] 3.4 Test sensitivity to daily vs monthly interpretation
  - [x] 3.5 Generate comprehensive comparison reports
  - [x] 3.6 Save visualizations and CSV breakdowns

- [x] 4. Identify Root Causes of NPV Variance
  - [x] 4.1 Production scale mismatch: Excel data is daily (33,938 BBL/day)
  - [x] 4.2 Period count difference: 55 periods vs expected 60 months
  - [x] 4.3 Revenue scale issue: $106M seems low for deepwater field
  - [x] 4.4 Confirm OPEX calculation uses same $15/BBL rate
  - [x] 4.5 Document cash flow component breakdown
  - [x] 4.6 Create detailed recommendations for alignment

- [x] 5. Create Comprehensive Production and Prices Differences Report
  - [x] 5.1 Document production data scale differences (daily vs monthly)
  - [x] 5.2 Analyze oil price data source alignment and variations
  - [x] 5.3 Quantify revenue impact of production scale mismatch (33.1x factor)
  - [x] 5.4 Create detailed comparison tables and visualizations
  - [x] 5.5 Generate executive summary of key differences
  - [x] 5.6 Provide specific recommendations for data alignment

- [ ] 6. Implement Data Alignment Solution
  - [ ] 6.1 Update manual analysis to use daily production data
  - [ ] 6.2 Ensure consistent time period aggregation
  - [ ] 6.3 Extend data to full 60-month period if possible
  - [ ] 6.4 Re-run NPV calculations with aligned data
  - [ ] 6.5 Update NPV accuracy spec (2025-07-25) with findings
  - [ ] 6.6 Verify NPV variance reduced to <20% target

- [x] 7. Create Comparison Table for Field Analysis Methods
  - [x] 7.1 Write tests for comparison table generation
  - [x] 7.2 Extract field data for both Excel and WorldEnergyData methods
  - [x] 7.3 Calculate required parameters for comparison table
  - [x] 7.4 Generate markdown comparison table with the following parameters:
    - Number of months of production
    - Production Start Month
    - Production End Month
    - Total production in BBL
    - Average oil price in USD
    - Total revenue in USD
    - Number of Wells - total
    - Number of Wells - producing
    - Total average daily Production by month
  - [x] 7.5 Verify comparison accuracy and save results

- [x] 8. Generate Monthly Field Economics DataFrame
  - [x] 8.1 Write tests for monthly dataframe generation
  - [x] 8.2 Create monthly production and economic data extraction
  - [x] 8.3 Calculate monthly economic metrics (CAPEX, OPEX, Oil sales, Revenue, NPV)
  - [x] 8.4 Generate dataframe with following columns by month:
    - Month-Year (production period)
    - Monthly production in BBL
    - Oil price in USD
    - CAPEX (monthly allocation)
    - OPEX (monthly calculation)  
    - Oil sales (monthly revenue)
    - Net revenue (after OPEX)
    - Cumulative revenue
    - Cumulative OPEX
    - Cumulative CAPEX
    - Cumulative cash flow
    - Cumulative cash flow after OPEX
    - Cumulative NPV
    - Wells total (monthly count)
    - Wells producing (monthly count)
    - Daily production rate (BBL/day for that month)
  - [x] 8.5 Save dataframe as CSV in results folder
  - [x] 8.6 Verify data accuracy and completeness

- [ ] 9. SME Manual Verification and Review #TODO
  - [ ] 9.1 Review Excel data extraction methodology and accuracy
  - [ ] 9.2 Validate production data alignment with field knowledge
  - [ ] 9.3 Verify oil price sources and historical accuracy
  - [ ] 9.4 Review CAPEX allocation schedule ($2.6B over 60 months)
  - [ ] 9.5 Validate OPEX calculation ($15/BBL operational costs)
  - [ ] 9.6 Check NPV calculation methodology and discount rate (10%)
  - [ ] 9.7 Verify well count progression (20→28 wells) matches field development
  - [ ] 9.8 Review monthly economics DataFrame for field-specific accuracy
  - [ ] 9.9 Validate cumulative cash flow and NPV calculations
  - [ ] 9.10 Cross-check results against known Jack St. Malo field benchmarks
  - [ ] 9.11 Provide recommendations for data source improvements
  - [ ] 9.12 Sign off on program accuracy for production use

## Key Findings Summary

1. **Excel Data Characteristics:**
   - 55 periods of DAILY production data
   - Average: 33,938 BBL/day
   - Oil prices: $56.60/BBL average
   - Total revenue: $106M

2. **NPV Calculation Results:**
   - Using Excel data: -$1.45B
   - Excel benchmark: ~-$2.6B
   - Variance: 44.2%

3. **Root Cause Analysis:**
   - Production data is DAILY, not MONTHLY
   - Only 55 days of data vs expected 60 months
   - Manual analysis likely using monthly aggregation
   - This explains the significant NPV variance