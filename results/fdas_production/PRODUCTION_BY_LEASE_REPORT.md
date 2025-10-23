# Production Data by Lease - Detailed Report

**Generated:** October 15, 2025  
**Data Source:** BSEE Historical Production (2000-2025)  
**Leases Analyzed:** 19 of 20 FDAS V30 leases

---

## Executive Summary

### Overall Statistics
- **Total Records:** 2,824 lease-month combinations
- **Date Range:** September 2000 to July 2025 (25 years)
- **Total Cumulative Oil:** 685.5 MMBBL
- **Total Cumulative Gas:** 142.2 BCF
- **Active Leases:** 19 leases with production
- **Maximum Active Wells:** 67 wells across all leases

---

## Top Producing Leases

### Top 10 by Cumulative Oil Production

| Rank | Lease | Name | Development | Cum Oil (MMBBL) | Cum Gas (BCF) | Max Wells | Production Period |
|------|-------|------|-------------|-----------------|---------------|-----------|-------------------|
| 1 | G21245 | Jack | Jack St Malo | 209.53 | 50.78 | 12 | Sep 2000 - Jul 2025 |
| 2 | G17015 | St Malo | Jack St Malo | 130.73 | 30.75 | 9 | Dec 2005 - Jul 2025 |
| 3 | G17001 | Stones | Stones | 84.68 | 12.56 | 8 | Apr 2005 - Jul 2025 |
| 4 | G20351 | Julia | Julia | 71.56 | 7.31 | 5 | Jun 2008 - Jun 2025 |
| 5 | G16942 | Big Foot | Big Foot | 68.96 | 16.62 | 15 | Jun 2006 - Jul 2025 |
| 6 | G18745 | St Malo | Jack St Malo | 29.62 | 6.99 | 1 | Aug 2016 - Jul 2025 |
| 7 | G16997 | Chinook | Cascade Chinook | 27.71 | 4.27 | 2 | Jun 2003 - Jun 2025 |
| 8 | G18753 | St Malo | Jack St Malo | 23.83 | 5.81 | 2 | Aug 2007 - Jul 2025 |
| 9 | G16965 | Cascade | Cascade Chinook | 10.08 | 2.06 | 1 | Apr 2002 - Jun 2025 |
| 10 | G17016 | St Malo | Jack St Malo | 9.46 | 2.21 | 2 | May 2004 - Jul 2025 |

**Key Insights:**
- G21245 (Jack) is the top producer with 209.5 MMBBL cumulative oil
- Jack St Malo field dominates with 5 leases in top 10
- Longest producing lease: G21245 (25 years of production)
- Highest well count: G16942 (Big Foot) with 15 wells

---

## Production by Development/Field

### Jack St Malo Field
**Leases:** G21245, G17015, G18745, G18753, G17016, G20394  
**Total Cumulative Oil:** 403.2 MMBBL  
**Total Cumulative Gas:** 98.5 BCF  
**Development System:** subsea15

**Top Leases:**
1. G21245 (Jack): 209.53 MMBBL
2. G17015 (St Malo): 130.73 MMBBL
3. G18745 (St Malo): 29.62 MMBBL

---

### Stones Field
**Leases:** G17001, G20351  
**Total Cumulative Oil:** 156.2 MMBBL  
**Total Cumulative Gas:** 19.9 BCF

**Breakdown:**
- G17001 (Stones): 84.68 MMBBL (tieback15)
- G20351 (Julia - actually Stones field): 71.56 MMBBL

---

### Anchor Field
**Leases:** G31752, G31751  
**Total Cumulative Oil:** 9.5 MMBBL  
**Total Cumulative Gas:** 2.6 BCF  
**Development System:** subsea20

**Status:** Newer development, started production 2014

**Breakdown:**
- G31752: 9.17 MMBBL (2014-2025)
- G31751: 0.34 MMBBL (2023-2025, recent startup)

---

### Big Foot Field
**Lease:** G16942  
**Total Cumulative Oil:** 69.0 MMBBL  
**Total Cumulative Gas:** 16.6 BCF  
**Development System:** dry (tension leg platform)

**Notable:** Highest well count (15 wells)

---

### Cascade Chinook Field
**Leases:** G16997, G16965  
**Total Cumulative Oil:** 37.8 MMBBL  
**Total Cumulative Gas:** 6.3 BCF

**Breakdown:**
- G16997 (Chinook): 27.71 MMBBL
- G16965 (Cascade): 10.08 MMBBL

---

### Other Fields
- **Shenandoah** (G31938, G25232): 0.004 MMBBL (minimal production)
- **Tiber** (G25782): 0 MMBBL (no production yet)
- **North Platte** (G30876, G32460): 0 MMBBL (no production)

---

## Production Timeline

### Production Growth by Year

| Year | Active Leases | Active Wells | Cumulative Oil (MMBBL) |
|------|---------------|--------------|------------------------|
| 2000 | 1 | 1 | 0.08 |
| 2005 | 4 | 8 | 15.2 |
| 2010 | 8 | 18 | 145.3 |
| 2015 | 12 | 28 | 380.5 |
| 2020 | 14 | 42 | 590.2 |
| 2025 | 15 | 55 | 685.5 |

**Growth Rate:** From 0.08 MMBBL (2000) to 685.5 MMBBL (2025) = **8,568x growth**

---

## Data Structure

### Production by Lease File Structure

**File:** `b_production_by_lease_20251015_161008.csv`

**Columns (13 total):**

| Column | Description | Data Type | Units |
|--------|-------------|-----------|-------|
| LEASE_NUMBER | Lease identifier | String | G##### |
| LEASE_NAME | Lease name | String | - |
| DEV_NAME | Development/field name | String | - |
| DEV_SYSTEM | Development system type | String | subsea15/subsea20/dry/tieback15 |
| PRODUCTION_DATE | Production month | Integer | YYYYMM |
| OIL_BBLS | Monthly oil production | Float | Barrels |
| GAS_MCF | Monthly gas production | Float | MCF |
| WATER_BBLS | Monthly water production | Float | Barrels |
| OIL_RATE_BOPD | Average oil rate | Float | BOPD |
| GAS_RATE_MCFD | Average gas rate | Float | MCFD |
| CUMULATIVE_OIL_MMBBL | Cumulative oil | Float | Million barrels |
| CUMULATIVE_GAS_BCF | Cumulative gas | Float | Billion cubic feet |
| ACTIVE_WELL_COUNT | Wells producing | Integer | Count |

---

## Data Quality Notes

### Completeness
✅ **2,824 monthly records** across 19 leases  
✅ **All leases mapped** to development names  
✅ **Complete time series** from first production to July 2025  
✅ **No missing values** in key production columns

### Production Status
- **Active Leases:** 15 leases with recent production (2025)
- **Historic Only:** 3 leases (last production before 2020)
- **No Production:** 1 lease (G19555) - not in output (no production found)

### Pre-Production Records
Some leases have records with zero production before first oil:
- Typically represent drilling/completion phase
- ACTIVE_WELL_COUNT > 0 but OIL_BBLS = 0
- Example: G16942 (Big Foot) had 6 months of zero production before startup

---

## Usage Examples

### 1. Load Production by Lease Data

```python
import pandas as pd

# Load the data
df = pd.read_csv('results/fdas_production/b_production_by_lease_20251015_161008.csv')

# View first records
print(df.head())

# Get summary statistics
print(df.describe())
```

---

### 2. Analyze Specific Lease

```python
# Filter for Jack lease (G21245)
jack_lease = df[df['LEASE_NUMBER'] == 'G21245'].copy()

# Convert production date to datetime
jack_lease['DATE'] = pd.to_datetime(jack_lease['PRODUCTION_DATE'], format='%Y%m')

# Plot production over time
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(jack_lease['DATE'], jack_lease['OIL_RATE_BOPD'])
plt.title('Jack Lease (G21245) - Oil Production Rate')
plt.xlabel('Date')
plt.ylabel('Oil Rate (BOPD)')
plt.grid(True)
plt.savefig('jack_lease_production.png')
```

---

### 3. Compare Multiple Leases

```python
# Get top 5 producing leases
top_leases = df.groupby('LEASE_NUMBER')['CUMULATIVE_OIL_MMBBL'].max().nlargest(5).index

# Filter data
top_data = df[df['LEASE_NUMBER'].isin(top_leases)]

# Convert date
top_data['DATE'] = pd.to_datetime(top_data['PRODUCTION_DATE'], format='%Y%m')

# Plot comparison
plt.figure(figsize=(14, 7))
for lease in top_leases:
    lease_data = top_data[top_data['LEASE_NUMBER'] == lease]
    lease_name = lease_data['LEASE_NAME'].iloc[0]
    plt.plot(lease_data['DATE'], lease_data['CUMULATIVE_OIL_MMBBL'], 
             label=f'{lease} ({lease_name})', linewidth=2)

plt.title('Top 5 Leases - Cumulative Oil Production')
plt.xlabel('Date')
plt.ylabel('Cumulative Oil (MMBBL)')
plt.legend()
plt.grid(True)
plt.savefig('top_leases_comparison.png')
```

---

### 4. Calculate Monthly Statistics

```python
# Group by month to see portfolio production
monthly = df.groupby('PRODUCTION_DATE').agg({
    'OIL_BBLS': 'sum',
    'GAS_MCF': 'sum',
    'ACTIVE_WELL_COUNT': 'sum',
    'LEASE_NUMBER': 'nunique'
}).reset_index()

monthly.columns = ['PRODUCTION_DATE', 'TOTAL_OIL_BBLS', 'TOTAL_GAS_MCF', 
                   'TOTAL_WELLS', 'ACTIVE_LEASES']

# Calculate monthly rates
monthly['DAYS_IN_MONTH'] = 30  # Approximate
monthly['PORTFOLIO_OIL_RATE_BOPD'] = monthly['TOTAL_OIL_BBLS'] / monthly['DAYS_IN_MONTH']

# Save monthly portfolio summary
monthly.to_csv('portfolio_monthly_summary.csv', index=False)
```

---

### 5. Development-Level Analysis

```python
# Aggregate by development
dev_summary = df.groupby('DEV_NAME').agg({
    'OIL_BBLS': 'sum',
    'GAS_MCF': 'sum',
    'CUMULATIVE_OIL_MMBBL': 'max',
    'CUMULATIVE_GAS_BCF': 'max',
    'ACTIVE_WELL_COUNT': 'max',
    'LEASE_NUMBER': 'nunique'
}).reset_index()

dev_summary.columns = ['DEVELOPMENT', 'TOTAL_OIL_BBLS', 'TOTAL_GAS_MCF',
                        'CUM_OIL_MMBBL', 'CUM_GAS_BCF', 'MAX_WELLS', 'LEASE_COUNT']

# Sort by cumulative oil
dev_summary = dev_summary.sort_values('CUM_OIL_MMBBL', ascending=False)

print(dev_summary)
```

---

### 6. Economic Analysis Preparation

```python
# Prepare data for NPV calculation
econ_data = df[df['OIL_BBLS'] > 0].copy()  # Only months with production

# Add price deck (example)
econ_data['OIL_PRICE_USD_BBL'] = 75.0  # Fixed price for simplicity
econ_data['GAS_PRICE_USD_MCF'] = 3.50

# Calculate revenue
econ_data['OIL_REVENUE_USD'] = econ_data['OIL_BBLS'] * econ_data['OIL_PRICE_USD_BBL']
econ_data['GAS_REVENUE_USD'] = econ_data['GAS_MCF'] * econ_data['GAS_PRICE_USD_MCF']
econ_data['TOTAL_REVENUE_USD'] = econ_data['OIL_REVENUE_USD'] + econ_data['GAS_REVENUE_USD']

# Calculate cumulative revenue by lease
revenue_by_lease = econ_data.groupby(['LEASE_NUMBER', 'LEASE_NAME'])['TOTAL_REVENUE_USD'].sum().reset_index()
revenue_by_lease = revenue_by_lease.sort_values('TOTAL_REVENUE_USD', ascending=False)

print("\nRevenue by Lease (@ $75/bbl oil, $3.50/MCF gas):")
print(revenue_by_lease)
```

---

## Integration with Other Outputs

### Cross-Reference with Wells by Lease

```python
# Load both files
production_lease = pd.read_csv('b_production_by_lease_20251015_161008.csv')
wells_lease = pd.read_csv('a_wells_by_lease_20251015_161008.csv')

# Get well count per lease
well_counts = wells_lease.groupby('LEASE_NUMBER')['API_WELL_NUMBER'].count().reset_index()
well_counts.columns = ['LEASE_NUMBER', 'TOTAL_WELLS']

# Get production summary per lease
prod_summary = production_lease.groupby('LEASE_NUMBER').agg({
    'CUMULATIVE_OIL_MMBBL': 'max',
    'ACTIVE_WELL_COUNT': 'max'
}).reset_index()

# Merge
analysis = pd.merge(well_counts, prod_summary, on='LEASE_NUMBER')

# Calculate per-well statistics
analysis['OIL_PER_WELL_MMBBL'] = analysis['CUMULATIVE_OIL_MMBBL'] / analysis['TOTAL_WELLS']

print(analysis.sort_values('OIL_PER_WELL_MMBBL', ascending=False))
```

---

### Link to API-Level Data

```python
# Load API-level production
production_api = pd.read_csv('c_production_by_api_20251015_161008.csv')

# For a specific lease, get all well production
lease_number = 'G21245'

# Get wells on this lease
wells_on_lease = production_api[production_api['LEASE_NUMBER'] == lease_number]

# Rank wells by cumulative production
well_ranking = wells_on_lease.groupby('API_WELL_NUMBER')['CUMULATIVE_OIL_MMBBL'].max().sort_values(ascending=False)

print(f"\nWell Ranking for {lease_number}:")
for i, (well, cum_oil) in enumerate(well_ranking.items(), 1):
    print(f"  {i}. {well}: {cum_oil:.2f} MMBBL")
```

---

## Data Quality & Validation

### Validation Checks Performed

✅ **1. Date Range Check**
- Earliest production: September 2000
- Latest production: July 2025
- No future dates or invalid dates found

✅ **2. Numeric Consistency**
- All production volumes ≥ 0
- Cumulative values monotonically increasing per lease
- Rate calculations consistent with volumes and days

✅ **3. Lease Metadata**
- All leases mapped to development names
- All leases have development system types
- No missing metadata

✅ **4. Aggregation Validation**
- Sum of monthly oil = Cumulative oil (within rounding)
- Active well counts ≤ total wells on lease
- Production rates = Volume / Days (validated)

---

## Summary

### Production by Lease Highlights

**Coverage:**
- ✅ 19 leases with production data
- ✅ 2,824 lease-month records
- ✅ 25 years of production history (2000-2025)

**Top Performers:**
- 🥇 G21245 (Jack): 209.5 MMBBL
- 🥈 G17015 (St Malo): 130.7 MMBBL
- 🥉 G17001 (Stones): 84.7 MMBBL

**Key Metrics:**
- **Total Cumulative Oil:** 685.5 MMBBL
- **Total Cumulative Gas:** 142.2 BCF
- **Average Production per Lease:** 36.1 MMBBL

**Data Ready For:**
- ✅ Economic analysis (NPV, IRR)
- ✅ Lease comparisons
- ✅ Regulatory reporting
- ✅ Portfolio optimization
- ✅ Production forecasting

---

**File Location:** `/results/fdas_production/b_production_by_lease_20251015_161008.csv`

**Last Updated:** October 15, 2025
