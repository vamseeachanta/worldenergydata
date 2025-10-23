# FDAS V30 Comprehensive Production Data Report

**Generated:** October 15, 2025 at 09:57 PM  
**Report Type:** Integrated Analysis (Lease, API, Field)

---

## Executive Summary

### Portfolio Overview

| Metric | Value | Description |
|--------|-------|-------------|
| **Total Leases** | 19 | Producing leases |
| **Total Wells** | 158 | Unique API12 wells |
| **Total Fields** | 9 | Development fields |
| **Cumulative Oil** | 685.0 MMBBL | Total portfolio oil production |
| **Cumulative Gas** | 144.1 BCF | Total portfolio gas production |
| **Production Period** | 2000-2025 | 25 years of production data |
| **Total Records** | 12,849 | All aggregation levels |

### Top Performers

- **Top Lease:** G21245 (Jack) - 209.53 MMBBL
- **Top Well:** 608124005800 - 37.570 MMBBL
- **Top Field:** Jack St Malo - 412.46 MMBBL

---

## 1. Production by Lease

### Overview

Lease-level production aggregation showing **19 producing leases** across the FDAS V30 portfolio. Data represents monthly production aggregated to the lease level.

**Key Statistics:**
- Total lease-month records: **2,824**
- Date range: 200009 to 202507
- Average wells per lease: **8.8**

### Top 10 Producing Leases

| Rank | Lease | Name | Development | Cum Oil (MMBBL) | Cum Gas (BCF) | Max Wells | % of Total |
|------|-------|------|-------------|-----------------|---------------|-----------|------------|
| 11 | G21245 | Jack | Jack St Malo | 209.53 | 50.78 | 12 | 30.6% |
| 5 | G17015 | St Malo | Jack St Malo | 130.73 | 30.75 | 9 | 19.1% |
| 4 | G17001 | Stones | Stones | 84.68 | 12.56 | 8 | 12.4% |
| 9 | G20351 | Julia | Julia | 71.56 | 7.31 | 5 | 10.4% |
| 1 | G16942 | Big Foot | Big Foot | 68.96 | 16.62 | 15 | 10.1% |
| 7 | G18745 | St Malo | Jack St Malo | 29.62 | 6.99 | 1 | 4.3% |
| 3 | G16997 | Chinook | Cascade Chinook | 27.71 | 4.27 | 2 | 4.0% |
| 8 | G18753 | St Malo | Jack St Malo | 23.83 | 5.81 | 2 | 3.5% |
| 2 | G16965 | Cascade | Cascade Chinook | 10.08 | 2.06 | 1 | 1.5% |
| 6 | G17016 | St Malo | Jack St Malo | 9.46 | 2.21 | 2 | 1.4% |

### Key Insights - Lease Level

- ✅ Top 3 leases account for **62.0%** of total production
- ✅ 9 leases have cumulative production > 10 MMBBL
- ✅ Average of **8.8 wells** per lease
- ✅ Longest producing lease: **25+ years** of continuous production

**File:** `b_production_by_lease_*.csv` (2,824 records)

---

## 2. Production by API (Individual Wells)

### Overview

Well-level production showing **158 individual API12 wells**. This data includes production rates, cumulative volumes, GOR, and water cut for each well.

**Key Statistics:**
- Total API-month records: **8,446**
- Wells per lease: **1 to 23** wells
- Average well production: **4.228 MMBBL**

### Top 10 Producing Wells

| Rank | API Well Number | Lease | Development | Cum Oil (MMBBL) | Cum Gas (BCF) | Avg GOR |
|------|-----------------|-------|-------------|-----------------|---------------|---------|
| 70 | 608124005800 | G21245 | Jack St Malo | 37.570 | 9.072 | 0 |
| 61 | 608124005103 | G17015 | Jack St Malo | 37.480 | 8.807 | 0 |
| 113 | 608124011400 | G21245 | Jack St Malo | 35.231 | 8.444 | 0 |
| 69 | 608124005700 | G21245 | Jack St Malo | 32.738 | 8.032 | 0 |
| 67 | 608124005400 | G21245 | Jack St Malo | 30.284 | 7.303 | 0 |
| 106 | 608124010701 | G18745 | Jack St Malo | 29.622 | 6.994 | 0 |
| 73 | 608124006001 | G16942 | Big Foot | 28.461 | 7.723 | 0 |
| 107 | 608124010800 | G20351 | Julia | 28.363 | 3.309 | 0 |
| 33 | 608124001701 | G17015 | Jack St Malo | 25.349 | 5.963 | 0 |
| 118 | 608124011504 | G17015 | Jack St Malo | 24.065 | 5.666 | 0 |

### Key Insights - Well Level

- ✅ Top well has produced **37.570 MMBBL** cumulative oil
- ✅ Average well production: **4.228 MMBBL**
- ✅ Well count per lease ranges from **1 to 23** wells
- ✅ Data includes **GOR, water cut, and rate calculations** for each well

**File:** `c_production_by_api_*.csv` (8,446 records)

---

## 3. Production by Field (Development Level)

### Overview

Field-level aggregation showing **9 development fields**. Multiple leases can be aggregated into a single field/development.

**Key Statistics:**
- Total field-month records: **1,579**
- Fields with production: **7**
- Average leases per field: **2.0**

### All Fields Ranked by Production

| Rank | Field Name | System | Cum Oil (MMBBL) | Cum Gas (BCF) | Max Wells | Leases | % of Total |
|------|------------|--------|-----------------|---------------|-----------|--------|------------|
| 4 | Jack St Malo | subsea15 | 412.46 | 98.70 | 26 | 6 | 60.2% |
| 8 | Stones | subsea15 | 84.68 | 12.56 | 8 | 1 | 12.4% |
| 5 | Julia | tieback15 | 71.56 | 7.31 | 5 | 1 | 10.4% |
| 2 | Big Foot | dry | 68.96 | 16.62 | 15 | 1 | 10.1% |
| 3 | Cascade Chinook | subsea15 | 37.79 | 6.33 | 3 | 2 | 5.5% |
| 1 | Anchor | subsea20 | 9.51 | 2.59 | 5 | 2 | 1.4% |
| 7 | Shenandoah | subsea20 | 0.00 | 0.00 | 9 | 2 | 0.0% |
| 6 | North Platte | subsea20 | 0.00 | 0.00 | 2 | 2 | 0.0% |
| 9 | Tiber | subsea20 | 0.00 | 0.00 | 2 | 1 | 0.0% |

### Key Insights - Field Level

- ✅ Top field accounts for **60.2%** of portfolio production
- ✅ **7** fields have production > 0 MMBBL
- ✅ Development systems: **subsea15, subsea20, dry tree, tieback15**
- ✅ Subsea15 systems dominate with **~78%** of production

**File:** `d_production_by_field_*.csv` (1,579 records)

---


## 4. Production by Development

### Overview

Development-level aggregation showing **9 developments** in the FDAS V30 portfolio. Developments represent field-level projects that may span multiple leases.

**Key Statistics:**
- Total developments: **9**
- Development systems: **4 types** (subsea15, subsea20, dry, tieback15)
- Average development size: **76.11 MMBBL**

### All Developments Ranked by Production

| Rank | Development | System | Leases | Wells | Cum Oil (MMBBL) | Cum Gas (BCF) | Years | % of Total |
|------|-------------|--------|--------|-------|-----------------|---------------|-------|------------|
| 1 | Jack St Malo | subsea15 | 6 | 26 | 412.46 | 98.70 | 24.8 | 60.2% |
| 2 | Stones | subsea15 | 1 | 8 | 84.68 | 12.56 | 20.2 | 12.4% |
| 3 | Julia | tieback15 | 1 | 5 | 71.56 | 7.31 | 17.0 | 10.4% |
| 4 | Big Foot | dry | 1 | 15 | 68.96 | 16.62 | 19.1 | 10.1% |
| 5 | Cascade Chinook | subsea15 | 2 | 3 | 37.79 | 6.33 | 23.2 | 5.5% |
| 6 | Anchor | subsea20 | 2 | 5 | 9.51 | 2.59 | 10.6 | 1.4% |
| 7 | Shenandoah | subsea20 | 2 | 9 | 0.00 | 0.00 | 16.6 | 0.0% |
| 8 | North Platte | subsea20 | 2 | 2 | 0.00 | 0.00 | 4.7 | 0.0% |
| 9 | Tiber | subsea20 | 1 | 2 | 0.00 | 0.00 | 7.7 | 0.0% |

**Total:** 684.97 MMBBL across 9 developments

### Development System Analysis

**Production by System Type:**

- **subsea15**: 3 developments, 534.93 MMBBL (78.1%)
- **tieback15**: 1 developments, 71.56 MMBBL (10.4%)
- **dry**: 1 developments, 68.96 MMBBL (10.1%)
- **subsea20**: 4 developments, 9.52 MMBBL (1.4%)


### Key Insights - Development Level

- ✅ Top development accounts for **60.2%** of portfolio production
- ✅ **subsea15** systems dominate with **78.1%** of production
- ✅ Average development size: **76.11 MMBBL**
- ✅ **7** developments with active production

**File:** `e_production_by_development_*.csv` (9 records)

---

## Data Files Summary

### Output Files

| File Name | Description | Records | Size | Key Columns |
|-----------|-------------|---------|------|-------------|
| **a_wells_by_lease** | Well inventory | 158 | 7.8 KB | LEASE_NUMBER, API_WELL_NUMBER, DEV_NAME |
| **b_production_by_lease** | Monthly production by lease | 2,824 | 239 KB | OIL_BBLS, GAS_MCF, CUMULATIVE_OIL_MMBBL |
| **c_production_by_api** | Individual well production | 8,446 | 1.3 MB | API_WELL_NUMBER, OIL_RATE_BOPD, GOR, WATER_CUT |
| **d_production_by_field** | Field-level aggregation | 1,579 | 130 KB | FIELD_NAME, CUMULATIVE_OIL_MMBBL, ACTIVE_WELL_COUNT |

### Metrics Calculated

**Production Volumes:**
- Monthly oil production (barrels)
- Monthly gas production (MCF)
- Monthly water production (barrels)
- Cumulative oil (MMBBL)
- Cumulative gas (BCF)

**Performance Metrics:**
- Oil rate (BOPD)
- Gas rate (MCFD)
- Gas-Oil Ratio (GOR)
- Water cut percentage
- Active well counts

---

## Summary Statistics

### Portfolio Totals

- **Total Cumulative Oil:** 685.0 MMBBL
- **Total Cumulative Gas:** 144.1 BCF
- **Total Leases:** 19
- **Total Wells:** 158
- **Total Fields:** 9

### Top 3 Contributions

**By Lease:**
1. G21245 (Jack): 209.53 MMBBL (30.6%)
2. G17015 (St Malo): 130.73 MMBBL (19.1%)
3. G17001 (Stones): 84.68 MMBBL (12.4%)

**By Field:**
1. Jack St Malo: 412.46 MMBBL (60.2%)
2. Stones: 84.68 MMBBL (12.4%)
3. Julia: 71.56 MMBBL (10.4%)

---

## File Locations

All files located in: `/mnt/github/workspace-hub/worldenergydata/results/fdas_production/`

**Data Files:**
- `a_wells_by_lease_20251015_161008.csv`
- `b_production_by_lease_20251015_161008.csv`
- `c_production_by_api_20251015_161008.csv`
- `d_production_by_field_20251015_161008.csv`
- `fdas_production_complete_20251015_161008.xlsx` (All sheets)

**Scripts:**
- `/scripts/run_fdas_production_retrieval.py` - Data retrieval
- `/scripts/analyze_production_by_lease.py` - Lease analysis

---

**Report Generated:** October 15, 2025 at 09:57 PM  
**Data Source:** BSEE Historical Production Archives (2000-2025)  
**System:** WorldEnergyData Production Retrieval System
