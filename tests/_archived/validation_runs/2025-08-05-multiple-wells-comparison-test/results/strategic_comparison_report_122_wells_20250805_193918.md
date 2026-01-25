# Multiple Wells Drilling and Completion Days Comparison Report

**Generated:** 2025-08-05 19:39:18  
**Total Wells Analyzed:** 122  
**Report Version:** 2.0.0 (Corrected for 122 Wells)

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Key Findings](#key-findings)
- [Statistical Analysis](#statistical-analysis)
- [Summary Tables](#summary-tables)
- [Detailed Analysis](#detailed-analysis)

---

## Executive Summary

### Overview
This report presents a comprehensive comparison analysis of drilling and completion days between lease-based and API12-based calculation methods across **122 wells**. The analysis was conducted using advanced statistical methods and automated outlier detection to ensure data quality and reliability.

### Key Performance Indicators

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Total Wells Analyzed** | 122 | Complete dataset coverage (corrected count) |
| **Successful Matches** | 122 (100.0%) | High data alignment |
| **Wells with OK Status** | 13 (10.7%) | Acceptable agreement |
| **Wells Requiring Review** | 49 (40.2%) | Minor discrepancies detected |
| **Wells with Errors** | 60 (49.2%) | Significant discrepancies |

### Executive Recommendations

⚠️ **Investigation Required**: Significant discrepancies detected. Review methodology and data sources.

---

## Key Findings

### Method Agreement Analysis

**Drilling Days Comparison:**
- Average difference: **+2.61 days** (API12 vs Lease method)
- Correlation coefficient: **-0.088** (Weak correlation)
- Wells within 5-day agreement: **31 wells** (25.4%)

**Completion Days Comparison:**
- Average difference: **+0.68 days** (API12 vs Lease method)
- Correlation coefficient: **0.056** (Weak correlation)
- Wells within 2-day agreement: **39 wells** (32.0%)

### Outlier Detection Results

- **Total outliers identified:** 95 wells (77.9% of dataset)
- **Data quality assessment:** Requires Review

---

## Statistical Analysis

This section provides detailed statistical analysis of the comparison results with corrected 122 wells dataset.

### Distribution Analysis

**Drilling Days Statistics:**
- Mean difference: 2.61 days
- Standard deviation: 16.07 days
- Correlation: -0.088

**Completion Days Statistics:**
- Mean difference: 0.68 days
- Standard deviation: 6.58 days
- Correlation: 0.056

---

## Summary Tables

### Top 15 Drilling Days Discrepancies

| API12 | Well_Name | Lease_Drilling_Days | API12_Drilling_Days | Drilling_Diff | Status |
| --- | --- | --- | --- | --- | --- |
| 608124000075 | Lease Well 75 | 13 | 61 | 48 | ERROR |
| 608124000050 | Lease Well 50 | 23 | 67 | 44 | ERROR |
| 608124000080 | Lease Well 80 | 21 | 54 | 33 | ERROR |
| 608124000045 | Lease Well 45 | 27 | 57 | 30 | ERROR |
| 608124000029 | Lease Well 29 | 37 | 66 | 29 | ERROR |
| 608124000031 | Lease Well 31 | 37 | 65 | 28 | ERROR |
| 608124000093 | Lease Well 93 | 36 | 64 | 28 | ERROR |
| 608124000078 | Lease Well 78 | 41 | 68 | 27 | ERROR |
| 608124000014 | Lease Well 14 | 22 | 47 | 25 | ERROR |
| 608124000015 | Lease Well 15 | 24 | 49 | 25 | ERROR |
| 608124000096 | Lease Well 96 | 27 | 52 | 25 | ERROR |
| 608124000117 | Lease Well 117 | 44 | 68 | 24 | ERROR |
| 608124000118 | Lease Well 118 | 30 | 54 | 24 | ERROR |
| 608124000077 | Lease Well 77 | 46 | 69 | 23 | ERROR |
| 608124000024 | Lease Well 24 | 27 | 49 | 22 | ERROR |

### Top 15 Completion Days Discrepancies

| API12 | Well_Name | Lease_Completion_Days | API12_Completion_Days | Completion_Diff | Status |
| --- | --- | --- | --- | --- | --- |
| 608124000018 | Lease Well 18 | 8 | 24 | 16 | ERROR |
| 608124000067 | Lease Well 67 | 10 | 24 | 14 | ERROR |
| 608124000037 | Lease Well 37 | 9 | 22 | 13 | ERROR |
| 608124000083 | Lease Well 83 | 8 | 21 | 13 | ERROR |
| 608124000025 | Lease Well 25 | 8 | 19 | 11 | ERROR |
| 608124000063 | Lease Well 63 | 13 | 24 | 11 | ERROR |
| 608124000102 | Lease Well 102 | 6 | 16 | 10 | ERROR |
| 608124000027 | Lease Well 27 | 17 | 26 | 9 | ERROR |
| 608124000060 | Lease Well 60 | 10 | 19 | 9 | ERROR |
| 608124000015 | Lease Well 15 | 11 | 19 | 8 | ERROR |
| 608124000016 | Lease Well 16 | 13 | 21 | 8 | REVIEW |
| 608124000068 | Lease Well 68 | 7 | 15 | 8 | ERROR |
| 608124000078 | Lease Well 78 | 9 | 17 | 8 | ERROR |
| 608124000115 | Lease Well 115 | 4 | 12 | 8 | REVIEW |
| 608124000120 | Lease Well 120 | 14 | 22 | 8 | REVIEW |

### Method Comparison Statistics

| Metric | Lease Method | API12 Method | Difference |
|--------|--------------|--------------|------------|
| **Avg Drilling Days** | 43.6 | 46.2 | +2.6 |
| **Avg Completion Days** | 14.9 | 15.6 | +0.7 |
| **Drilling Days Std Dev** | 11.1 | 10.7 | -0.3 |
| **Completion Days Std Dev** | 5.0 | 4.5 | -0.5 |

---

## Detailed Analysis

This section focuses on the **109 wells** that require attention, avoiding information overload from the full dataset.

### Wells Requiring Review (49 wells)

Wells with minor discrepancies that should be reviewed:

| API12 | Well_Name | Drilling_Diff | Completion_Diff | Outlier_Flags |
| --- | --- | --- | --- | --- |
| 608124000001 | Lease Well 1 | -6 | -3 | none |
| 608124000002 | Lease Well 2 | 8 | 5 | completion_percentage_outlier |
| 608124000005 | Lease Well 5 | -4 | 7 | completion_absolute_outlier,completion_percentage_outlier |
| 608124000006 | Lease Well 6 | -5 | 7 | completion_absolute_outlier,completion_percentage_outlier |
| 608124000008 | Lease Well 8 | 11 | 2 | drilling_absolute_outlier |
| 608124000010 | Lease Well 10 | -7 | -4 | none |
| 608124000011 | Lease Well 11 | 9 | 5 | completion_percentage_outlier |
| 608124000013 | Lease Well 13 | 9 | 6 | completion_absolute_outlier,completion_percentage_outlier |
| 608124000016 | Lease Well 16 | -3 | 8 | completion_absolute_outlier,completion_percentage_outlier |
| 608124000017 | Lease Well 17 | 15 | -2 | drilling_absolute_outlier,drilling_percentage_outlier |
| 608124000019 | Lease Well 19 | 9 | -5 | drilling_percentage_outlier,completion_percentage_outlier |
| 608124000021 | Lease Well 21 | -11 | 3 | drilling_absolute_outlier,completion_percentage_outlier |
| 608124000022 | Lease Well 22 | -3 | 5 | completion_percentage_outlier |
| 608124000023 | Lease Well 23 | 9 | 3 | none |
| 608124000026 | Lease Well 26 | -3 | 4 | completion_percentage_outlier |
| 608124000033 | Lease Well 33 | 9 | -5 | completion_percentage_outlier |
| 608124000036 | Lease Well 36 | 14 | 2 | drilling_absolute_outlier,drilling_percentage_outlier |
| 608124000039 | Lease Well 39 | -6 | 0 | none |
| 608124000040 | Lease Well 40 | -7 | -6 | completion_absolute_outlier,completion_percentage_outlier |
| 608124000042 | Lease Well 42 | -2 | 7 | completion_absolute_outlier,completion_percentage_outlier |

*Note: Showing top 20 wells requiring review. Total wells needing review: 49.*

### Wells with Errors (60 wells)

Wells with significant discrepancies requiring immediate investigation:

| API12 | Well_Name | Drilling_Diff | Completion_Diff | Outlier_Flags |
| --- | --- | --- | --- | --- |
| 608124000003 | Lease Well 3 | -22 | -2 | drilling_absolute_outlier,drilling_percentage_outlier |
| 608124000004 | Lease Well 4 | -32 | -11 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000007 | Lease Well 7 | -18 | 5 | drilling_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000009 | Lease Well 9 | 21 | 7 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000014 | Lease Well 14 | 25 | -9 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000015 | Lease Well 15 | 25 | 8 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000018 | Lease Well 18 | 14 | 16 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000020 | Lease Well 20 | 18 | -12 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000024 | Lease Well 24 | 22 | -6 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000025 | Lease Well 25 | 9 | 11 | completion_absolute_outlier,completion_percentage_outlier |
| 608124000027 | Lease Well 27 | 16 | 9 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000029 | Lease Well 29 | 29 | 3 | drilling_absolute_outlier,drilling_percentage_outlier |
| 608124000030 | Lease Well 30 | 17 | 4 | drilling_absolute_outlier,drilling_percentage_outlier |
| 608124000031 | Lease Well 31 | 28 | 3 | drilling_absolute_outlier,drilling_percentage_outlier |
| 608124000032 | Lease Well 32 | -29 | -2 | drilling_absolute_outlier,drilling_percentage_outlier |
| 608124000034 | Lease Well 34 | 12 | 6 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000035 | Lease Well 35 | 17 | 0 | drilling_absolute_outlier,drilling_percentage_outlier |
| 608124000037 | Lease Well 37 | -13 | 13 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000038 | Lease Well 38 | 21 | -6 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier,completion_percentage_outlier |
| 608124000041 | Lease Well 41 | -16 | -6 | drilling_absolute_outlier,completion_absolute_outlier,drilling_percentage_outlier |

*Note: Showing top 20 wells with errors. Total wells with errors: 60.*

---

## Report Generation Details

- **Analysis Engine:** Strategic Markdown Report Generator v2.0.0
- **Generation Time:** 2025-08-05 19:39:18
- **Dataset:** Corrected 122 wells (previously 125)
- **Configuration:** Max detailed wells = 20, Advanced outlier detection enabled
- **Quality Assurance:** Automated statistical validation and systematic discrepancy detection applied

---

*This report was generated automatically by the WorldEnergyData analysis framework with corrected 122 wells dataset.*
