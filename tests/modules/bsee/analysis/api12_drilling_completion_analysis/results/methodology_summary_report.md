# Methodology Analysis Report: API12 Drilling Completion Days Comparison

**Analysis Date**: August 6, 2025  
**Purpose**: Compare drilling and completion day calculation methodologies between lease-based and API12-based approaches

## Executive Summary

This analysis compares two different approaches to calculating drilling and completion days in BSEE oil and gas well data:

1. **Lease Method**: Uses raw WAR (Well Activity Reports) timeline analysis with gap-based logic
2. **API12 Method**: Uses milestone-based phase calculations through WellRigDays framework integration

## Key Findings

### Fundamental Methodological Differences

| Aspect | Lease Method | API12 Method |
|--------|--------------|--------------|
| **Data Approach** | Direct WAR timeline analysis | Framework-driven milestone calculation |
| **Timeline Construction** | Raw start/end dates with gap thresholds | Aggregated milestone phases |
| **Drilling Calculation** | Gap-based (300-day threshold) | Milestone-based DRL phases |
| **Completion Calculation** | Post-TD WAR analysis (8-day threshold) | Milestone completion phases |
| **Data Sources** | Binary WAR files, CSV lease data | Structured well data + WellRigDays |
| **Output Format** | Single Excel file | Multiple CSV files + visualizations |

### Data Source Comparison

**Lease Method Data Sources:**
- `mv_war_main.bin` - Primary WAR records with start/end dates
- `mv_war_boreholes_view.bin` - Borehole and depth information  
- `mv_war_main_prop.bin` - Well properties (mud weights, etc.)
- `leases.csv` - Lease metadata for grouping

**API12 Method Data Sources:**
- Input well data structure - Configuration-driven well groups
- WellRigDays class - Milestone-based rig analysis framework
- Directional surveys - Spatial well path data
- Borehole integration - Technical specifications

### Calculation Logic Analysis

#### Drilling Days Calculation

**Lease Method:**
1. Extract Total Depth Date from boreholes
2. Filter WAR records before TD date
3. Apply 300-day gap threshold for drilling interruptions
4. Adjust spud date after major gaps
5. Calculate: `(TD_DATE - ADJUSTED_SPUD_DATE) - early_days`

**API12 Method:**
1. Integrate with WellRigDays for milestone analysis
2. Extract DRL (drilling) phase durations
3. Use milestone-based approach for phase tracking
4. Calculate efficiency metrics (days per 10,000 ft)

#### Completion Days Calculation

**Lease Method:**
1. Find WAR records after Total Depth Date
2. Apply 8-day gap threshold for completion activities
3. Group consecutive activities into segments
4. Sum all segment durations

**API12 Method:**
1. Extract completion phases from milestone data
2. Track completion activities separately from drilling
3. Link to production start dates when available

### Processing Complexity

**Lease Method:**
- **Architecture**: Monolithic class with sequential processing
- **Time Complexity**: O(n*m) where n=wells, m=WAR records per well
- **Bottlenecks**: Gap analysis for wells with many WAR records

**API12 Method:**
- **Architecture**: Framework integration with specialized components
- **Time Complexity**: O(n) for well processing + WellRigDays overhead
- **Bottlenecks**: WellRigDays milestone calculation

### Business Rules Identified

**Lease Method Business Rules:**
- GAP_THRESHOLD = 300 days for drilling interruptions
- COMPLETION_GAP_THRESHOLD = 8 days between completion activities
- If gap > 300 days, restart drilling timeline from after gap
- Early drilling days before major gaps are subtracted from total
- Only use WAR records that start before Total Depth Date

**API12 Method Business Rules:**
- Uses WellRigDays class for standardized rig analysis
- Milestone approach tracks DRL (drilling) activities
- Incorporates sidetrack and bypass information
- Links completion activities to production timeline

## Root Cause Analysis for Calculation Differences

### Primary Factors Contributing to Differences:

1. **Timeline Reconstruction Methods**
   - Lease method: Direct date arithmetic with gap handling
   - API12 method: Milestone-based phase aggregation

2. **Data Granularity**
   - Lease method: Individual WAR record start/end dates
   - API12 method: Aggregated milestone phase durations

3. **Gap Handling Philosophy**
   - Lease method: Fixed thresholds (300 days drilling, 8 days completion)
   - API12 method: Framework-determined milestone logic

4. **Data Source Completeness**
   - Lease method: May miss activities not in WAR records
   - API12 method: Dependent on milestone calculation accuracy

### Validation Requirements

To validate which method is more accurate, the following analysis is recommended:

1. **Compare gap threshold impacts** on specific wells with known drilling interruptions
2. **Validate milestone calculation logic** in WellRigDays framework
3. **Analyze data source completeness** for both WAR records and milestone data
4. **Review timeline reconstruction accuracy** against known well histories

## Implementation Strengths and Limitations

### Lease Method
**Strengths:**
- Comprehensive gap analysis for drilling interruptions
- Uses multiple data sources for complete picture
- Handles complex drilling timelines with restarts
- Provides detailed well metadata

**Limitations:**
- Relies on WAR data quality and completeness
- Fixed gap thresholds may not suit all scenarios
- Complex logic may be hard to troubleshoot

### API12 Method
**Strengths:**
- Integrates with specialized rig days analysis framework
- Supports complex multi-well field analysis
- Milestone-based approach provides detailed activity tracking
- Comprehensive output including visualization support

**Limitations:**
- Dependent on WellRigDays class implementation
- More complex data flow and dependencies
- Milestone data quality affects accuracy

## Recommendations

1. **For Accuracy**: Validate both methods against known well timelines to determine which provides more accurate results
2. **For Standardization**: Consider developing hybrid approach that combines WAR data granularity with milestone framework benefits
3. **For Analysis**: Focus on wells with extreme differences (e.g., 509 days vs 2 days) to understand root causes
4. **For Future Development**: Implement configurable gap thresholds and milestone validation in both approaches

---

*This analysis was generated as part of the API12 drilling completion days comparison study to identify methodological differences and recommend validation approaches.*