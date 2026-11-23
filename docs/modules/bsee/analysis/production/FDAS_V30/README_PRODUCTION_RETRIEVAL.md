# FDAS V30 Production Data Retrieval

## Overview

This guide explains how to retrieve production data for all leases in the FDAS V30 project and generate four types of output:

- **a. Wells by Lease** - List of all API12 wells organized by lease
- **b. Production by Lease** - Monthly production aggregated by lease
- **c. Production by API** - Individual well production with rates and cumulatives  
- **d. Production by Field** - Field-level production aggregation

## Quick Start

### Using the Python Script (Recommended)

```bash
# From project root
cd /mnt/github/workspace-hub/worldenergydata

# Run the production retrieval script
python3 scripts/get_production_by_fdas_leases.py
```

**Prerequisites:**
- Production data must be downloaded and converted to binary format
- Binary files should be in `/data/bsee/production/bin/`

### Output Files

The script generates:

```
results/fdas_production/
├── a_wells_by_lease_YYYYMMDD_HHMMSS.csv
├── b_production_by_lease_YYYYMMDD_HHMMSS.csv
├── c_production_by_api_YYYYMMDD_HHMMSS.csv
├── d_production_by_field_YYYYMMDD_HHMMSS.csv
├── summary_statistics_YYYYMMDD_HHMMSS.csv
├── fdas_production_complete_YYYYMMDD_HHMMSS.xlsx (all sheets)
└── PRODUCTION_SUMMARY_YYYYMMDD_HHMMSS.md
```

## Leases Included

The script processes all 20 leases from `leases.xlsx`:

| Lease | Name | Development | System | Water Depth |
|-------|------|-------------|--------|-------------|
| G17001 | Jack | Jack/StMalo | subsea15 | 9525 ft |
| G16965 | St Malo | Jack/StMalo | subsea15 | 8200 ft |
| G16997 | Julia | Julia | subsea15 | 8900 ft |
| G20351 | Stones | Stones | tieback15 | 7335 ft |
| G31752 | Anchor | Anchor | subsea20 | 5080 ft |
| ... | ... | ... | ... | ... |

*(See `leases.xlsx` for complete list)*

## Output Descriptions

### a. Wells by Lease

**File:** `a_wells_by_lease_*.csv`

Lists all API12 wells associated with each lease.

**Columns:**
- `LEASE_NUMBER` - Lease number (e.g., G17001)
- `LEASE_NAME` - Lease name (e.g., Jack)
- `DEV_NAME` - Development name (e.g., Jack/StMalo)
- `DEV_SYSTEM` - Development system type (e.g., subsea15)
- `API_WELL_NUMBER` - 12-digit well identifier
- `WELL_COUNT` - Total wells on this lease

**Example:**
```csv
LEASE_NUMBER,LEASE_NAME,DEV_NAME,DEV_SYSTEM,API_WELL_NUMBER,WELL_COUNT
G17001,Jack,Jack/StMalo,subsea15,608124011800,7
G17001,Jack,Jack/StMalo,subsea15,608124011400,7
G17001,Jack,Jack/StMalo,subsea15,608124013400,7
```

**Use Cases:**
- Identify all wells drilled on a lease
- Well inventory by development
- Mapping API12 to lease/field hierarchy

---

### b. Production by Lease

**File:** `b_production_by_lease_*.csv`

Monthly production aggregated to lease level.

**Columns:**
- `LEASE_NUMBER` - Lease number
- `LEASE_NAME` - Lease name
- `DEV_NAME` - Development name
- `DEV_SYSTEM` - Development system
- `PRODUCTION_DATE` - Production month (YYYYMM)
- `OIL_BBLS` - Monthly oil production (barrels)
- `GAS_MCF` - Monthly gas production (MCF)
- `WATER_BBLS` - Monthly water production (barrels)
- `OIL_RATE_BOPD` - Average oil rate (BOPD)
- `GAS_RATE_MCFD` - Average gas rate (MCFD)
- `CUMULATIVE_OIL_MMBBL` - Cumulative oil (MMBBL)
- `CUMULATIVE_GAS_BCF` - Cumulative gas (BCF)
- `ACTIVE_WELL_COUNT` - Number of wells producing
- `TOTAL_DAYS_ON_PROD` - Total production days

**Example:**
```csv
LEASE_NUMBER,LEASE_NAME,DEV_NAME,PRODUCTION_DATE,OIL_BBLS,GAS_MCF,CUMULATIVE_OIL_MMBBL
G17001,Jack,Jack/StMalo,202301,1250000,6500000,125.5
G17001,Jack,Jack/StMalo,202302,1180000,6200000,126.7
```

**Use Cases:**
- Track lease-level production over time
- Calculate lease economics (NPV, IRR)
- Regulatory reporting by lease
- Royalty calculations

---

### c. Production by API

**File:** `c_production_by_api_*.csv`

Detailed monthly production for each individual well.

**Columns:**
- `API_WELL_NUMBER` - Well identifier
- `LEASE_NUMBER` - Lease number
- `LEASE_NAME` - Lease name
- `DEV_NAME` - Development name
- `DEV_SYSTEM` - Development system
- `COMPLETION_NAME` - Completion identifier
- `PRODUCTION_DATE` - Production month (YYYYMM)
- `DAYS_ON_PROD` - Days on production
- `MON_O_PROD_VOL` - Monthly oil volume (bbls)
- `MON_G_PROD_VOL` - Monthly gas volume (MCF)
- `MON_WTR_PROD_VOL` - Monthly water volume (bbls)
- `OIL_RATE_BOPD` - Oil rate (barrels/day)
- `GAS_RATE_MCFD` - Gas rate (MCF/day)
- `WATER_RATE_BWD` - Water rate (barrels/day)
- `GOR_MCF_BBL` - Gas-oil ratio
- `WATER_CUT_PCT` - Water cut percentage
- `CUMULATIVE_OIL_MMBBL` - Well cumulative oil (MMBBL)
- `CUMULATIVE_GAS_BCF` - Well cumulative gas (BCF)
- `BOEM_FIELD` - BOEM field name
- `AREA_CODE_BLOCK_NUM` - Block location
- `OPERATOR_NUM` - Operator number
- `SORT_NAME` - Operator name

**Example:**
```csv
API_WELL_NUMBER,LEASE_NUMBER,DEV_NAME,PRODUCTION_DATE,OIL_RATE_BOPD,GAS_RATE_MCFD,CUMULATIVE_OIL_MMBBL
608124011800,G17001,Jack/StMalo,202301,42500,225000,18.5
608124011800,G17001,Jack/StMalo,202302,40200,215000,19.7
```

**Use Cases:**
- Well performance analysis
- Decline curve analysis (DCA)
- Production forecasting
- Well-by-well economics
- Identify high/low performers
- Water cut trends
- GOR analysis

---

### d. Production by Field

**File:** `d_production_by_field_*.csv`

Monthly production aggregated to field/development level.

**Columns:**
- `FIELD_NAME` - Development/field name
- `DEV_SYSTEM` - Development system type
- `PRODUCTION_DATE` - Production month (YYYYMM)
- `OIL_BBLS` - Monthly oil production (barrels)
- `GAS_MCF` - Monthly gas production (MCF)
- `WATER_BBLS` - Monthly water production (barrels)
- `OIL_RATE_BOPD` - Average oil rate (BOPD)
- `GAS_RATE_MCFD` - Average gas rate (MCFD)
- `GOR_MCF_BBL` - Field-level GOR
- `CUMULATIVE_OIL_MMBBL` - Field cumulative oil (MMBBL)
- `CUMULATIVE_GAS_BCF` - Field cumulative gas (BCF)
- `ACTIVE_WELL_COUNT` - Number of producing wells
- `ACTIVE_LEASE_COUNT` - Number of active leases
- `TOTAL_DAYS_ON_PROD` - Total production days

**Example:**
```csv
FIELD_NAME,DEV_SYSTEM,PRODUCTION_DATE,OIL_BBLS,CUMULATIVE_OIL_MMBBL,ACTIVE_WELL_COUNT
Jack/StMalo,subsea15,202301,2500000,245.8,14
Julia,subsea15,202301,1800000,185.2,11
Stones,tieback15,202301,950000,32.5,4
```

**Use Cases:**
- Field-level performance tracking
- Portfolio analysis
- Development comparison
- Corporate reporting
- Investment decisions
- Production forecasting at field level

---

## Data Processing Details

### Production Metrics Calculated

The script automatically calculates:

1. **Production Rates**
   - Oil Rate (BOPD) = Monthly Oil Volume / Days on Production
   - Gas Rate (MCFD) = Monthly Gas Volume / Days on Production
   - Water Rate (BWD) = Monthly Water Volume / Days on Production

2. **Cumulative Production**
   - Cumulative Oil (MMBBL) = Sum of monthly oil / 1,000,000
   - Cumulative Gas (BCF) = Sum of monthly gas / 1,000,000

3. **Performance Indicators**
   - GOR = Monthly Gas Volume / Monthly Oil Volume
   - Water Cut % = (Water Volume / (Oil + Water Volume)) × 100

4. **Activity Metrics**
   - Active well count per month
   - Active lease count per month
   - Total days on production

### Aggregation Hierarchy

```
API12 (Individual Wells)
    ↓
Lease (Multiple wells on one lease)
    ↓
Field/Development (Multiple leases in one development)
```

### Data Sources

The script loads production data from binary files which are preprocessed from BSEE ZIP archives:

```
/data/bsee/production/bin/
├── prod_2020_01.bin
├── prod_2020_02.bin
├── ...
└── prod_2024_12.bin
```

Each binary file contains one month of Gulf of Mexico production data for all operators.

---

## Advanced Usage

### Custom Output Directory

```python
from scripts.get_production_by_fdas_leases import FDASProductionRetriever

retriever = FDASProductionRetriever(
    leases_file='docs/modules/bsee/analysis/production/FDAS_V30/leases.xlsx',
    output_dir='./my_custom_results'
)

retriever.run()
```

### Filter by Date Range

After generating the outputs, you can filter by date:

```python
import pandas as pd

# Load production by API
df = pd.read_csv('results/fdas_production/c_production_by_api_*.csv')

# Filter for 2023 only
df['PRODUCTION_DATE'] = pd.to_datetime(df['PRODUCTION_DATE'], format='%Y%m')
df_2023 = df[(df['PRODUCTION_DATE'] >= '2023-01-01') & 
             (df['PRODUCTION_DATE'] <= '2023-12-31')]

# Save filtered data
df_2023.to_csv('production_api_2023.csv', index=False)
```

### Analyze Specific Wells

```python
# Load API production
df = pd.read_csv('results/fdas_production/c_production_by_api_*.csv')

# Get all production for a specific well
well_data = df[df['API_WELL_NUMBER'] == 608124011800]

# Plot production profile
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(well_data['PRODUCTION_DATE'], well_data['OIL_RATE_BOPD'])
plt.title('Well 608124011800 Production Profile')
plt.xlabel('Date')
plt.ylabel('Oil Rate (BOPD)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('well_production.png')
```

### Compare Field Performance

```python
# Load field production
df = pd.read_csv('results/fdas_production/d_production_by_field_*.csv')

# Get peak production by field
peak_production = df.groupby('FIELD_NAME')['OIL_RATE_BOPD'].max().sort_values(ascending=False)

print("Peak Oil Production by Field:")
print(peak_production)
```

---

## Troubleshooting

### Issue: "Binary folder not found"

**Solution:** Download and convert production data to binary format:

```python
from worldenergydata.bsee.data._from_zip.production_data import GetProdDataFromZip

prod_loader = GetProdDataFromZip()
prod_loader.save_zip_data_to_binary(cfg)
```

### Issue: "No production data found for FDAS leases"

**Possible causes:**
1. Lease numbers don't match (check G-prefix)
2. Binary files don't contain these leases
3. Date range issue

**Solution:** Check lease numbers in the binary files:

```python
import pickle
import pandas as pd

# Load one binary file
with open('data/bsee/production/bin/prod_2023_01.bin', 'rb') as f:
    df = pickle.load(f)
    
# Check unique leases
print(df['LEASE_NUMBER'].unique())
```

### Issue: Script runs out of memory

**Solution:** Process in chunks or use a machine with more RAM. The script loads all production data into memory for faster processing.

---

## Performance Notes

**Processing Time:** Depends on data size
- 20 leases, 5 years of data: ~2-5 minutes
- 20 leases, full history: ~10-20 minutes

**Memory Usage:** ~2-8 GB RAM depending on data volume

**Optimization Tips:**
1. Use binary files instead of ZIP (10-100x faster)
2. Filter date range if only recent data needed
3. Process leases in batches if memory constrained

---

## Output File Sizes

Typical output sizes (20 leases, 5 years):

- Wells by Lease: < 1 MB
- Production by Lease: 5-20 MB
- Production by API: 50-200 MB (largest)
- Production by Field: 1-5 MB
- Excel workbook: 50-200 MB (compressed)

---

## Integration with Other Tools

### Use with Financial Analysis

```python
from worldenergydata.bsee.analysis.financial.analyzer import FinancialAnalyzer

# Load production by lease
production_df = pd.read_csv('b_production_by_lease_*.csv')

# Run NPV analysis
analyzer = FinancialAnalyzer(config)
results = analyzer.run_analysis(production_df)
```

### Export to Excel for Reporting

```python
import pandas as pd

# Load all outputs
wells = pd.read_csv('a_wells_by_lease_*.csv')
lease_prod = pd.read_csv('b_production_by_lease_*.csv')
api_prod = pd.read_csv('c_production_by_api_*.csv')
field_prod = pd.read_csv('d_production_by_field_*.csv')

# Create custom Excel report
with pd.ExcelWriter('custom_report.xlsx') as writer:
    wells.to_excel(writer, sheet_name='Wells', index=False)
    lease_prod.to_excel(writer, sheet_name='Lease_Production', index=False)
    api_prod.to_excel(writer, sheet_name='Well_Production', index=False)
    field_prod.to_excel(writer, sheet_name='Field_Production', index=False)
```

---

## Summary

This production retrieval system provides **comprehensive production data** at multiple aggregation levels:

✅ **Wells by Lease** - Well inventory and mapping  
✅ **Production by Lease** - Lease-level economics and reporting  
✅ **Production by API** - Well performance and forecasting  
✅ **Production by Field** - Portfolio analysis and benchmarking

All outputs include calculated metrics (rates, cumulatives, GOR, water cut) and can be used for:
- Economic analysis (NPV, IRR, payout)
- Production forecasting
- Regulatory reporting
- Performance monitoring
- Investment decisions
