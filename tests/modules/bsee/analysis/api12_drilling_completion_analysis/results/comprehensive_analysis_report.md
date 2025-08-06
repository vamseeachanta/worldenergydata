# Root Cause Analysis Report: API12 Drilling Completion Days Comparison

**Analysis Date**: August 06, 2025  
**Purpose**: Comprehensive analysis comparing lease-based and API12-based drilling completion day calculation methodologies  
**Dataset**: 12 wells across 6 fields

## Executive Summary

This comprehensive analysis compares two different approaches to calculating drilling and completion days in BSEE oil and gas well data:

1. **Lease Method**: Timeline-based analysis using raw WAR (Well Activity Reports) data with gap thresholds
2. **API12 Method**: Milestone-based analysis using WellRigDays framework integration

### Key Findings

• Analyzed 12 wells across 6 fields
• Average drilling days difference: 94.3 days
• Average completion days difference: 31.2 days
• Maximum total difference: 509 days (well SN208)
• Minimum total difference: 2 days (well 001)
• 6 wells show differences greater than 100 days

### Statistical Overview

- **Average Drilling Difference**: 94.3 days
- **Average Completion Difference**: 31.2 days  
- **Maximum Total Difference**: 509 days
- **Minimum Total Difference**: 2 days
- **Wells with >100 days difference**: 6

## Methodology Comparison


| Aspect | Lease Method | API12 Method |
|--------|--------------|--------------|
| **Data Sources** | WAR binary files, CSV lease data | Structured well data + WellRigDays framework |
| **Timeline Construction** | Raw start/end dates with gap analysis | Aggregated milestone phases |
| **Drilling Calculation** | Gap-based (300-day threshold) | Milestone-based DRL phases |
| **Completion Calculation** | Post-TD WAR analysis (8-day threshold) | Milestone completion phases |
| **Gap Handling** | Fixed thresholds (300 days, 8 days) | Framework-determined logic |
| **Output Format** | Single Excel file | Multiple CSV files + visualizations |
| **Architecture** | Monolithic class processing | Framework integration components |
| **Data Granularity** | Individual WAR record level | Aggregated phase level |


## Statistical Analysis

### Drilling Days Differences
- **Mean**: 94.33 days
- **Median**: 9.00 days
- **Standard Deviation**: 166.36 days
- **Range**: -63 to 496 days
- **Interquartile Range**: -15.8 to 174.2 days

### Completion Days Differences
- **Mean**: 31.25 days
- **Median**: 21.50 days
- **Standard Deviation**: 42.97 days
- **Range**: -36 to 120 days
- **Interquartile Range**: 9.0 to 53.0 days

### Agreement Metrics
- **Mean Absolute Error**: 157.75 days
- **Root Mean Squared Error**: 209.03 days
- **Correlation Coefficient**: 0.549
- **Drilling Correlation**: 0.052
- **Completion Correlation**: 0.883

## Field-by-Field Analysis

| Field | Wells | Avg Drill Diff | Min Drill | Max Drill | Avg Comp Diff | Min Comp | Max Comp | Avg Total Diff |
|-------|-------|----------------|-----------|-----------|---------------|----------|----------|----------------|
| Anchor | 2 | -6.0 | -27 | 15 | 65.5 | 48 | 83 | 86.5 |
| Cascade | 2 | 50.5 | -63 | 164 | 94.0 | 68 | 120 | 207.5 |
| Chinook | 2 | -4.5 | -12 | 3 | -12.0 | -36 | 12 | 31.5 |
| Jack | 2 | 38.0 | -45 | 121 | 26.0 | 18 | 34 | 109.0 |
| St Malo | 2 | 137.5 | 2 | 273 | 12.5 | 0 | 25 | 150.0 |
| Stones | 2 | 350.5 | 205 | 496 | 1.5 | -10 | 13 | 362.0 |

### Field-Specific Insights


#### Stones
- **Wells Analyzed**: 2
- **Average Drilling Difference**: 350.5 days
- **Average Completion Difference**: 1.5 days
- **Average Total Difference**: 362.0 days
- **Drilling Range**: 205 to 496 days
- **Completion Range**: -10 to 13 days

#### St Malo
- **Wells Analyzed**: 2
- **Average Drilling Difference**: 137.5 days
- **Average Completion Difference**: 12.5 days
- **Average Total Difference**: 150.0 days
- **Drilling Range**: 2 to 273 days
- **Completion Range**: 0 to 25 days

#### Jack
- **Wells Analyzed**: 2
- **Average Drilling Difference**: 38.0 days
- **Average Completion Difference**: 26.0 days
- **Average Total Difference**: 109.0 days
- **Drilling Range**: -45 to 121 days
- **Completion Range**: 18 to 34 days

#### Cascade
- **Wells Analyzed**: 2
- **Average Drilling Difference**: 50.5 days
- **Average Completion Difference**: 94.0 days
- **Average Total Difference**: 207.5 days
- **Drilling Range**: -63 to 164 days
- **Completion Range**: 68 to 120 days

#### Anchor
- **Wells Analyzed**: 2
- **Average Drilling Difference**: -6.0 days
- **Average Completion Difference**: 65.5 days
- **Average Total Difference**: 86.5 days
- **Drilling Range**: -27 to 15 days
- **Completion Range**: 48 to 83 days

#### Chinook
- **Wells Analyzed**: 2
- **Average Drilling Difference**: -4.5 days
- **Average Completion Difference**: -12.0 days
- **Average Total Difference**: 31.5 days
- **Drilling Range**: -12 to 3 days
- **Completion Range**: -36 to 12 days

## Extreme Cases Analysis


| Case | API12 | Field | Well | Lease Drill | API12 Drill | Drill Diff | Lease Comp | API12 Comp | Comp Diff | Total Diff |
|------|-------|-------|------|-------------|-------------|------------|------------|------------|-----------|------------|
| Highest Total Diff | 608124010400 | Stones | SN208 | 565 | 69 | 496 | 93 | 80 | 13 | 509 |
| Lowest Total Diff | 608124004400 | St Malo | 001 | 2 | 0 | 2 | 0 | 0 | 0 | 2 |
| Highest Drill Diff | 608124010400 | Stones | SN208 | 565 | 69 | 496 | 93 | 80 | 13 | 509 |
| Lowest Drill Diff | 608124001600 | Cascade | 002 | 74 | 137 | -63 | 120 | 0 | 120 | 183 |


### Case Studies

#### Highest Total Difference: API12 608124010400
- **Well**: SN208 in Stones field
- **Drilling Difference**: 496 days
- **Potential Cause**: Likely due to drilling interruptions captured by lease method but aggregated by API12 method

#### Lowest Total Difference: API12 608124001600
- **Well**: 002 in Cascade field
- **Drilling Difference**: -63 days
- **Potential Cause**: Simple drilling timeline with minimal interruptions

## Root Cause Analysis

### Primary Factors Contributing to Differences

1. Timeline Reconstruction Methods: Lease method uses raw WAR start/end dates vs API12 method uses milestone phase durations
2. Gap Handling Philosophy: Lease method applies fixed thresholds (300 days drilling, 8 days completion) vs API12 method uses framework-determined logic
3. Data Source Granularity: Lease method processes individual WAR records vs API12 method uses aggregated milestone data
4. Drilling Interruption Treatment: Lease method explicitly handles gaps and restarts timeline vs API12 method may aggregate interrupted periods

### Methodology-Specific Impacts

• Gap-based vs Milestone-based: 6 wells show drilling differences >50 days, likely due to different gap handling
• Timeline Reconstruction: Wells with complex drilling histories show larger differences due to timeline calculation methods
• Data Processing: Framework integration in API12 method may smooth out drilling interruptions captured in lease method
• Completion Calculation: 6 wells show completion differences >30 days due to different post-TD analysis methods

### Data Quality Considerations

• WAR Data Completeness: Missing or incomplete WAR records affect lease method calculations
• Milestone Accuracy: WellRigDays framework accuracy depends on milestone calculation quality
• Date Precision: Different date handling between methods may introduce systematic differences
• Activity Classification: Different categorization of drilling vs completion activities

### Fields Most Affected

The following fields show the highest average total differences:
• Stones
• Cascade
• St Malo

## Well Details

| API12 | Field | Well | Lease Drill | API12 Drill | Drill Diff | Lease Comp | API12 Comp | Comp Diff | Total Diff |
|-------|-------|------|-------------|-------------|------------|------------|------------|-----------|------------|
| 608124010400 | Stones | SN208 | 565 | 69 | 496 | 93 | 80 | 13 | 509 |
| 608124011200 | Stones | SN206 | 259 | 54 | 205 | 51 | 61 | -10 | 215 |
| 608124004400 | St Malo | 001 | 2 | 0 | 2 | 0 | 0 | 0 | 2 |
| 608124005300 | St Malo | PN001 | 331 | 58 | 273 | 94 | 69 | 25 | 298 |
| 608124003100 | Jack | 003 | 230 | 109 | 121 | 18 | 0 | 18 | 139 |
| 608124000400 | Jack | 001 | 66 | 111 | -45 | 34 | 0 | 34 | 79 |
| 608124003800 | Cascade | CA003 | 210 | 46 | 164 | 204 | 136 | 68 | 232 |
| 608124001600 | Cascade | 002 | 74 | 137 | -63 | 120 | 0 | 120 | 183 |
| 608114075000 | Anchor | AP001 | 105 | 90 | 15 | 216 | 133 | 83 | 98 |
| 608114062101 | Anchor | 001 | 19 | 46 | -27 | 48 | 0 | 48 | 75 |
| 608124009700 | Chinook | CH004 | 94 | 91 | 3 | 261 | 297 | -36 | 39 |
| 608124004600 | Chinook | 002 | 29 | 41 | -12 | 12 | 0 | 12 | 24 |

## Recommendations

### Immediate Actions
1. Investigate the 6 wells with differences >100 days to understand specific causes
2. Focus on Stones field wells (showing highest differences) for detailed timeline analysis
3. Validate milestone calculation logic in WellRigDays framework against known drilling histories
4. Compare gap threshold appropriateness (300 days drilling, 8 days completion) against actual field data

### Methodology Improvements
1. Develop hybrid approach combining WAR data granularity with milestone framework benefits
2. Implement configurable gap thresholds based on field-specific or well-specific characteristics
3. Add data quality indicators to identify wells where method differences may be due to data issues
4. Create validation framework to cross-check both methods against external drilling timeline data

### Validation Steps
1. Select 10-15 wells across different fields for detailed manual timeline validation
2. Compare both methods against operator-reported drilling and completion timelines
3. Analyze correlation between data completeness and calculation accuracy
4. Validate WellRigDays milestone logic against raw WAR data for representative wells

### Future Research Directions
1. Investigate machine learning approaches for improved timeline reconstruction
2. Study field-specific patterns in methodology differences
3. Develop uncertainty quantification for both calculation methods
4. Research optimal gap thresholds based on drilling technology and field characteristics

## Conclusion

This analysis reveals significant methodological differences between the lease-based and API12-based approaches to calculating drilling and completion days. The key findings indicate that:

1. **Timeline Reconstruction Methods** are the primary source of differences, with the lease method using raw WAR timeline analysis while the API12 method uses milestone-based phase calculations.

2. **Gap Handling Philosophy** differs significantly, with fixed thresholds in the lease method versus framework-determined logic in the API12 method.

3. **Data Source Granularity** impacts accuracy, with the lease method processing individual WAR records while the API12 method uses aggregated milestone data.

4. **Extreme Differences** (>100 days) occur in 6 wells, primarily due to different treatment of drilling interruptions and timeline reconstruction methods.

### Recommended Next Steps

1. **Immediate**: Focus validation efforts on the 6 wells showing extreme differences
2. **Short-term**: Implement hybrid approach combining WAR granularity with milestone framework benefits  
3. **Long-term**: Develop adaptive gap thresholds and uncertainty quantification for both methods

This analysis provides the foundation for improving drilling and completion day calculations and ensuring consistency across different analytical approaches in the energy industry.

---

*Report generated on August 06, 2025 at 10:13 AM as part of the API12 drilling completion days methodology comparison study.*
