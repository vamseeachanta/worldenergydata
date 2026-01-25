# Drilling Days Comparison Test Report

**Generated**: 2025-08-04 11:53:36
**Wells Analyzed**: 1

## Comparison Table

The following table compares drilling and completion days between the lease-based method and API12-based method for 1 well api12:

| API12 Number | Drilling Days (Lease) | Drilling Days (API12) | Completion Days (Lease) | Completion Days (API12) |
| :-------------: | :------------------: | :------------------: | :--------------------: | :--------------------: |
| 608084001500 | 157 | 151 | 10 | 0 |

## Status Summary

- **✅ OK**: 0 wells (0.0%) - Within acceptable thresholds
- **⚠️ REVIEW**: 0 wells (0.0%) - Moderate discrepancies requiring review
- **❌ ERROR**: 1 wells (100.0%) - Significant discrepancies requiring investigation

**Total Wells Compared**: 1

## Analysis Summary

### Drilling Days Differences
- **Mean Difference**: 6.0 days (Lease - API12)
- **Standard Deviation**: nan days
- **Maximum Absolute Difference**: 6.0 days

### Completion Days Differences
- **Mean Difference**: 10.0 days (Lease - API12)
- **Standard Deviation**: nan days
- **Maximum Absolute Difference**: 10.0 days


## Methodology

**Data Sources:**
- **Lease Method**: Based on lease number approach using drilling_and_completion_days analysis
- **API12 Method**: Based on API12 number approach using well_api12 analysis

**Status Flag Criteria:**
- **✅ OK**: Differences within acceptable thresholds (≤5 days drilling, ≤3 days completion, ≤10% percentage)
- **⚠️ REVIEW**: Moderate differences requiring investigation (≤10 days drilling, ≤6 days completion, ≤20% percentage)
- **❌ ERROR**: Significant differences requiring immediate attention (>10 days drilling, >6 days completion, >20% percentage)

**Note**: Differences are calculated as (Lease Method - API12 Method). Positive values indicate lease method reports higher days.