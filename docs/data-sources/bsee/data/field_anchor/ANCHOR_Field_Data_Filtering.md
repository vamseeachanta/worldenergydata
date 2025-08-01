# ANCHOR Field Data Filtering Solution

## Overview

This document outlines the solution for filtering ANCHOR field production data based on Chuck's feedback regarding incorrect well allocation in the original dataset.

## Problem Statement

### Issue Identified by Chuck

- **Timeline Mismatch**: CHEVRON announced ANCHOR production started on **August 12, 2024**
- **Data Contamination**: Original spreadsheet included wells producing before August 31, 2024
- **Incorrect Attribution**: Non-ANCHOR wells were incorrectly included in ANCHOR field analysis

### Chuck's Key Points

1. API# `608114075000` is ANCHOR's first well

2. API# `608114075100` is likely ANCHOR's second well with impressive production rates

3. Any wells showing production before August 31, 2024 must be excluded
4. Data filtering was inadequate in original analysis

## Data Analysis

### Original Dataset Issues

The original `prod_rate_bopd_goa_anchor.csv` contained 11 wells with production data spanning from 2014 to 2025:

| API Number | Well Name | Production Period | Status |
|------------|-----------|-------------------|---------|
| 608114062100 | 001 ST00BP00 | 2014-2015 | ❌ Non-ANCHOR |
| 608114062101 | 001 ST00BP01 | 2014-2015 | ❌ Non-ANCHOR |
| 608114063500 | 002 ST00BP00 | 2014-2015 | ❌ Non-ANCHOR |
| 608114063501 | 002 ST00BP01 | 2015 | ❌ Non-ANCHOR |
| 608114067300 | 003 ST00BP00 | 2016-2017 | ❌ Non-ANCHOR |
| 608114067301 | 003 ST00BP01 | 2016-2017 | ❌ Non-ANCHOR |
| 608114072800 | SB001 ST00BP00 | 2019 | ❌ Non-ANCHOR |
| 608114075000 | AP001 ST00BP00 | Aug 2024+ | ✅ ANCHOR Well #1 |
| 608114075100 | AP002 ST00BP00 | Nov 2024+ | ✅ ANCHOR Well #2 |
| 608114076100 | AP004 ST00BP00 | Future | ✅ ANCHOR Well #3 |
| 608114076900 | AP005 ST00BP00 | Future | ✅ ANCHOR Well #4 |

## Solution Implementation

### Filtering Criteria

- **Date Cutoff**: Remove all production data before August 31, 2024
- **Well Selection**: Keep only wells with "AP" (ANCHOR Producer) designation
- **Data Integrity**: Ensure timeline aligns with official ANCHOR production start

### Wells Excluded (7 wells)

```
608114062100, 608114062101, 608114063500, 608114063501,
608114067300, 608114067301, 608114072800
```

### Wells Retained (4 wells)

```
608114075000 (AP001), 608114075100 (AP002),
608114076100 (AP004), 608114076900 (AP005)
```

## Filtered Dataset Results

### ANCHOR Production Timeline

```csv
PRODUCTION_DATETIME,608114075000,608114075100,608114076100,608114076900
2024-08-31,5217.4,0.0,0.0,0.0
2024-09-30,11853.0,0.0,0.0,0.0
2024-10-31,15565.6,0.0,0.0,0.0
2024-11-30,14526.5,7498.7,0.0,0.0
2024-12-31,14070.7,16177.8,0.0,0.0
2025-01-31,13897.6,18325.7,0.0,0.0
2025-02-28,14037.3,18402.1,0.0,0.0
```

### Key Production Insights

#### Well 608114075000 (AP001) - First ANCHOR Producer

- **First Production**: August 2024 (5,217 BOPD)
- **Peak Rate**: October 2024 (15,566 BOPD)
- **Current Rate**: February 2025 (14,037 BOPD)
- **Status**: Stable production profile

#### Well 608114075100 (AP002) - Second ANCHOR Producer

- **First Production**: November 2024 (7,499 BOPD)
- **Rapid Ramp-up**: December 2024 (16,178 BOPD)
- **Peak Rate**: February 2025 (18,402 BOPD)
- **Status**: Excellent performance, exceeding first well

#### Wells 608114076100 & 608114076900 (AP004 & AP005)

- **Status**: Future producers, no production to date
- **Expected**: Additional ANCHOR wells in development

## Benefits of Filtered Dataset

### Data Quality Improvements

1. **Temporal Accuracy**: Aligns with official ANCHOR production timeline
2. **Field-Specific Analysis**: Pure ANCHOR field performance data
3. **Reliable Metrics**: Accurate production rates and trends
4. **Cleaner Visualization**: Focused on actual ANCHOR wells

### Business Impact

- **Accurate Reporting**: True ANCHOR field performance metrics
- **Better Forecasting**: Based on actual ANCHOR well behavior
- **Investor Confidence**: Data integrity for stakeholder presentations
- **Operational Insights**: Clear understanding of ANCHOR well productivity

## Implementation Notes

### Files Created

- `prod_rate_bopd_goa_anchor_filtered.csv` - Clean filtered dataset
- Original file preserved with backup

### Data Validation

- ✅ No production before August 31, 2024
- ✅ Only ANCHOR-designated wells (AP###)
- ✅ Timeline consistency with field announcement
- ✅ Production data integrity maintained

## Recommendations

### Future Data Management

1. **Automated Filtering**: Implement date-based filters in data pipeline
2. **Well Classification**: Use consistent naming conventions (AP### for ANCHOR)

3. **Data Validation**: Regular checks against field development timelines
4. **Version Control**: Maintain filtered datasets separately from raw data

### Analysis Guidelines

- Always verify well attribution before field-level analysis
- Cross-reference production start dates with official announcements
- Use field-specific identifiers (AP### for ANCHOR) as primary filters

- Document data filtering decisions for transparency

## Conclusion

The filtered ANCHOR dataset now provides an accurate representation of the field's performance, removing historical wells that were incorrectly attributed to ANCHOR. This solution addresses Chuck's concerns and ensures data integrity for future analysis and reporting.

---
*Generated: July 9, 2025*
*Author: Data Analysis Team*
*Based on feedback from Chuck regarding ANCHOR field data accuracy*

---

*Last updated: 2025-07-24*
