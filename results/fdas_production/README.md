# FDAS V30 Production Data - Complete Package

**Generated:** October 15, 2025  
**Portfolio:** 19 Leases, 158 Wells, 9 Developments  
**Total Production:** 685.0 MMBBL Oil, 144.1 BCF Gas

---

## 📊 Quick Summary

This directory contains **comprehensive production data** for all FDAS V30 leases at **five aggregation levels**:

1. ✅ **Wells by Lease** (158 wells)
2. ✅ **Production by Lease** (2,824 lease-months)
3. ✅ **Production by API/Wells** (8,446 well-months)
4. ✅ **Production by Field** (1,579 field-months)
5. ✅ **Production by Development** (9 developments) ← NEW

---

## 📁 Data Files (CSV)

### Core Production Data

| File | Records | Description | Size |
|------|---------|-------------|------|
| **a_wells_by_lease_*.csv** | 158 | Well inventory by lease with development metadata | 7.8 KB |
| **b_production_by_lease_*.csv** | 2,824 | Monthly production aggregated by lease | 239 KB |
| **c_production_by_api_*.csv** | 8,446 | Individual well production with rates and metrics | 1.3 MB |
| **d_production_by_field_*.csv** | 1,579 | Field-level production aggregation | 130 KB |
| **e_production_by_development_*.csv** | 9 | Development-level summary with system types | 1.5 KB |

### Summary Files

| File | Description |
|------|-------------|
| **lease_summary_*.csv** | Statistical summary for each lease |
| **development_summary_*.csv** | Summary statistics by development |
| **fdas_production_complete_*.xlsx** | All data in Excel workbook (multiple sheets) |

---

## 📄 Report Files (Markdown)

### Integrated Reports

| Report | Description | Sections |
|--------|-------------|----------|
| **COMPREHENSIVE_PRODUCTION_REPORT_*.md** | Master integrated report | Executive Summary, Lease, API, Field, Development, Files |
| **PRODUCTION_BY_DEVELOPMENT_REPORT_*.md** | Development-level detailed analysis | 9 development profiles, system analysis, timeline |
| **PRODUCTION_BY_LEASE_REPORT_*.md** | Lease-level detailed analysis | Top leases, trends, usage examples |
| **EXECUTION_SUMMARY.md** | Data retrieval execution details | Processing statistics, timeline, validation |

---

## 🎯 What's Included

### 1. Wells by Lease (a_wells_by_lease)

**Columns:**
- LEASE_NUMBER, LEASE_NAME, DEV_NAME, DEV_SYSTEM
- API_WELL_NUMBER
- WELL_COUNT (total wells on lease)

**Use Cases:**
- Well inventory management
- Mapping wells to leases/fields
- Development planning

---

### 2. Production by Lease (b_production_by_lease)

**Columns:**
- LEASE_NUMBER, LEASE_NAME, DEV_NAME, DEV_SYSTEM
- PRODUCTION_DATE (YYYYMM)
- OIL_BBLS, GAS_MCF, WATER_BBLS
- OIL_RATE_BOPD, GAS_RATE_MCFD
- CUMULATIVE_OIL_MMBBL, CUMULATIVE_GAS_BCF
- ACTIVE_WELL_COUNT

**Use Cases:**
- Lease-level economics (NPV, IRR)
- Royalty calculations
- Regulatory reporting
- Lease performance tracking

---

### 3. Production by API (c_production_by_api)

**Columns:**
- API_WELL_NUMBER, LEASE_NUMBER, LEASE_NAME, DEV_NAME
- COMPLETION_NAME, PRODUCTION_DATE, DAYS_ON_PROD
- MON_O_PROD_VOL, MON_G_PROD_VOL, MON_WTR_PROD_VOL
- OIL_RATE_BOPD, GAS_RATE_MCFD
- GOR_MCF_BBL, WATER_CUT_PCT
- CUMULATIVE_OIL_MMBBL, CUMULATIVE_GAS_BCF
- BOEM_FIELD, OPERATOR_NUM, SORT_NAME

**Use Cases:**
- Well performance analysis
- Decline curve analysis (DCA)
- Production forecasting
- Well-by-well economics
- Identify high/low performers

---

### 4. Production by Field (d_production_by_field)

**Columns:**
- FIELD_NAME, DEV_SYSTEM, PRODUCTION_DATE
- OIL_BBLS, GAS_MCF, WATER_BBLS
- OIL_RATE_BOPD, GAS_RATE_MCFD, GOR_MCF_BBL
- CUMULATIVE_OIL_MMBBL, CUMULATIVE_GAS_BCF
- ACTIVE_WELL_COUNT, ACTIVE_LEASE_COUNT
- TOTAL_DAYS_ON_PROD

**Use Cases:**
- Portfolio analysis
- Field-level benchmarking
- Corporate reporting
- Investment decisions

---

### 5. Production by Development (e_production_by_development) ← NEW

**Columns:**
- DEVELOPMENT, SYSTEM
- TOTAL_OIL_BBLS, TOTAL_GAS_MCF
- CUM_OIL_MMBBL, CUM_GAS_BCF
- MAX_WELLS, MAX_LEASES
- FIRST_PROD, LAST_PROD, MONTHS
- AVG_GOR, PROD_YEARS, PCT_OF_TOTAL

**Use Cases:**
- Development system comparison
- Portfolio optimization
- System type analysis
- Long-term planning

---

## 📈 Top Performers

### By Lease (Top 3)
1. **G21245 (Jack)** - 209.53 MMBBL (30.6%)
2. **G17015 (St Malo)** - 130.73 MMBBL (19.1%)
3. **G17001 (Stones)** - 84.68 MMBBL (12.4%)

### By Well (Top 3)
1. **608124005800** - 37.570 MMBBL
2. **608124005103** - 37.480 MMBBL
3. **608124011400** - 35.231 MMBBL

### By Development (Top 3)
1. **Jack St Malo** - 412.46 MMBBL (60.2%)
2. **Stones** - 84.68 MMBBL (12.4%)
3. **Julia** - 71.56 MMBBL (10.4%)

---

## 🔍 Data Hierarchy

```
API12 Wells (158 wells)
    ↓
Leases (19 leases)
    ↓
Fields (9 fields)
    ↓
Developments (9 developments)
    ↓
Portfolio (685 MMBBL)
```

---

## 💡 Quick Usage Examples

### Load Production Data

```python
import pandas as pd

# Load by lease
df_lease = pd.read_csv('b_production_by_lease_20251015_161008.csv')

# Load by API/wells
df_api = pd.read_csv('c_production_by_api_20251015_161008.csv')

# Load by field
df_field = pd.read_csv('d_production_by_field_20251015_161008.csv')

# Load by development
df_dev = pd.read_csv('e_production_by_development_20251015_225323.csv')
```

### Analyze Top Producers

```python
# Top leases
top_leases = df_lease.groupby('LEASE_NUMBER')['CUMULATIVE_OIL_MMBBL'].max().sort_values(ascending=False).head(10)

# Top wells
top_wells = df_api.groupby('API_WELL_NUMBER')['CUMULATIVE_OIL_MMBBL'].max().sort_values(ascending=False).head(10)

# Top developments
top_devs = df_dev.sort_values('CUM_OIL_MMBBL', ascending=False)
```

### Calculate Economics

```python
# Apply price deck
oil_price = 75.0  # $/bbl
gas_price = 3.50  # $/MCF

# Revenue by lease
df_lease['OIL_REVENUE'] = df_lease['OIL_BBLS'] * oil_price
df_lease['GAS_REVENUE'] = df_lease['GAS_MCF'] * gas_price
df_lease['TOTAL_REVENUE'] = df_lease['OIL_REVENUE'] + df_lease['GAS_REVENUE']

# NPV calculation by lease
revenue_by_lease = df_lease.groupby('LEASE_NUMBER')['TOTAL_REVENUE'].sum()
```

---

## 🎨 Visualization Ideas

### Time Series Plots

```python
import matplotlib.pyplot as plt

# Production rate over time for top lease
lease_data = df_lease[df_lease['LEASE_NUMBER'] == 'G21245']
lease_data['DATE'] = pd.to_datetime(lease_data['PRODUCTION_DATE'], format='%Y%m')

plt.figure(figsize=(12, 6))
plt.plot(lease_data['DATE'], lease_data['OIL_RATE_BOPD'])
plt.title('Jack Lease (G21245) - Oil Production Rate')
plt.xlabel('Date')
plt.ylabel('Oil Rate (BOPD)')
plt.grid(True)
plt.savefig('jack_production_rate.png')
```

### Comparison Charts

```python
# Development comparison
plt.figure(figsize=(14, 8))
plt.barh(df_dev['DEVELOPMENT'], df_dev['CUM_OIL_MMBBL'])
plt.xlabel('Cumulative Oil (MMBBL)')
plt.title('Production by Development')
plt.tight_layout()
plt.savefig('development_comparison.png')
```

---

## 📊 Key Metrics Calculated

### Production Volumes
- Monthly oil production (barrels)
- Monthly gas production (MCF)
- Monthly water production (barrels)
- Cumulative oil (MMBBL)
- Cumulative gas (BCF)

### Performance Indicators
- Oil rate (BOPD)
- Gas rate (MCFD)
- Gas-Oil Ratio (GOR)
- Water cut percentage
- Active well counts
- Production years

---

## ✅ Data Quality

**Validation:**
- ✅ All leases mapped to developments
- ✅ All wells tracked to leases
- ✅ Cumulative calculations verified
- ✅ Date ranges validated (2000-2025)
- ✅ No missing production data
- ✅ Rate calculations cross-checked

**Coverage:**
- Date Range: September 2000 - July 2025 (25 years)
- Total Records: 12,849 across all levels
- Data Completeness: 100%

---

## 🚀 Next Steps

### Economic Analysis
- Apply price decks to production volumes
- Calculate NPV/IRR by lease
- Perform sensitivity analysis
- Evaluate development economics

### Production Forecasting
- Build decline curve models (exponential, hyperbolic)
- Forecast future production by well/lease/field
- Calculate EUR (Estimated Ultimate Recovery)
- Model field decline rates

### Portfolio Optimization
- Compare lease performance
- Identify underperformers
- Optimize development sequencing
- Evaluate divestment opportunities

### Reporting
- Regulatory submissions (lease-level)
- Investor presentations (portfolio-level)
- Internal dashboards (field-level)
- Partner updates (development-level)

---

## 📞 Scripts & Tools

### Data Retrieval
- **Script:** `/scripts/run_fdas_production_retrieval.py`
- **Function:** Loads production from BSEE ZIP archives
- **Runtime:** ~20 seconds for 30 years of data

### Analysis
- **Script:** `/scripts/analyze_production_by_lease.py`
- **Function:** Generates lease-level statistics and summaries

### Reporting
- **Script:** `/scripts/generate_production_report.py`
- **Function:** Creates comprehensive markdown reports

---

## 📦 Complete File List

### Data Files (CSV)
```
a_wells_by_lease_20251015_161008.csv          (158 rows)
b_production_by_lease_20251015_161008.csv     (2,824 rows)
c_production_by_api_20251015_161008.csv       (8,446 rows)
d_production_by_field_20251015_161008.csv     (1,579 rows)
e_production_by_development_*.csv              (9 rows)
lease_summary_*.csv
development_summary_*.csv
```

### Excel Workbook
```
fdas_production_complete_20251015_161008.xlsx
  ├─ Sheet 1: Wells_by_Lease
  ├─ Sheet 2: Production_by_Lease
  ├─ Sheet 3: Production_by_API
  └─ Sheet 4: Production_by_Field
```

### Reports (Markdown)
```
COMPREHENSIVE_PRODUCTION_REPORT_*.md
PRODUCTION_BY_DEVELOPMENT_REPORT_*.md
PRODUCTION_BY_LEASE_REPORT_*.md
EXECUTION_SUMMARY.md
README.md (this file)
```

---

## 🎯 Summary

**Complete Package:**
- ✅ 5 aggregation levels (Wells, Lease, API, Field, Development)
- ✅ 12,849 total production records
- ✅ 25 years of production history (2000-2025)
- ✅ 685.0 MMBBL cumulative oil production
- ✅ 144.1 BCF cumulative gas production

**Ready For:**
- Economic analysis (NPV, IRR, payout)
- Production forecasting (DCA, EUR)
- Regulatory reporting (lease-level)
- Portfolio optimization (field/development)
- Stakeholder presentations

**All data validated and production-ready!** ✨

---

**Last Updated:** October 15, 2025  
**Data Source:** BSEE Historical Production Archives  
**System:** WorldEnergyData Production Retrieval System
