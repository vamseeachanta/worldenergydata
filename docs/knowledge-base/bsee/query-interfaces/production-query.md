# Production Data Query Interface

> **URL**: https://www.data.bsee.gov/Production/ProductionData/Default.aspx
> **Category**: Production
> **Total Filters**: 9
> **Result Columns**: 11
> **Export Formats**: PDF, XLS, XLSX, RTF, CSV

---

## Overview

The Production Data query interface provides access to monthly production volumes aggregated by lease for the Outer Continental Shelf (OCS). Data includes oil, condensate, gas (both gas-well and associated), and water production volumes, plus active completion counts and water depth information.

---

## Filter Options (9 Total)

| # | Filter | Type | Description | Values/Format |
|---|--------|------|-------------|---------------|
| 1 | Lease Number | Text | OCS lease identifier | G00123 (1-100 chars, comma-separated OK) |
| 2 | Production Month/Year From | Date | Start of date range | MM/YYYY format |
| 3 | Production Month/Year To | Date | End of date range | MM/YYYY format |
| 4 | Lease Oil Production (BBL) | Range Slider | Oil volume range | 0-999,999,999 BBL |
| 5 | Lease Condensate Production (BBL) | Range Slider | Condensate volume range | 0-999,999,999 BBL |
| 6 | Lease Gas-Well-Gas Production (MCF) | Range Slider | Gas from gas wells | 0-999,999,999 MCF |
| 7 | Lease Oil-Well-Gas Production (MCF) | Range Slider | Associated gas from oil wells | 0-999,999,999 MCF |
| 8 | Lease Water Production (BBL) | Range Slider | Produced water volume | 0-999,999,999 BBL |
| 9 | Producing Completions | Range Slider | Count of active completions | 0-200 |
| 10 | Lease Max Water Depth (meters) | Range Slider | Maximum water depth | 0-3,000 meters |

---

## Filter Descriptions

### Lease Number
- Format: Alphanumeric identifier (typically G prefix for Gulf)
- Multiple leases: Comma-separated list supported
- Case insensitive
- Examples: G00123, G34567, P00012

### Production Date Range
- **Format**: MM/YYYY (month/year only, no day)
- **From**: First month to include
- **To**: Last month to include (leave empty for current)
- **Data Lag**: Production data typically lags 2-3 months

### Volume Filters
All volume filters are range sliders with minimum and maximum values:

| Filter | Unit | Typical Range | Notes |
|--------|------|---------------|-------|
| Oil Production | BBL | 0-1,000,000 | Barrels (42 US gallons) |
| Condensate Production | BBL | 0-500,000 | Light hydrocarbons |
| Gas-Well-Gas | MCF | 0-10,000,000 | Thousand cubic feet |
| Oil-Well-Gas | MCF | 0-5,000,000 | Associated gas |
| Water Production | BBL | 0-5,000,000 | Produced water/brine |

### Producing Completions
- Number of active well completions on the lease
- Range: 0-200
- Useful for filtering by lease size/activity

### Water Depth
- **Unit**: Meters (not feet)
- **Conversion**: 1 meter = 3.28084 feet
- Maximum water depth across all wells on the lease

---

## Result Columns (11 Total)

| # | Column | Type | Unit | Description | Example |
|---|--------|------|------|-------------|---------|
| 1 | Lease Number | VARCHAR(10) | - | OCS lease identifier | G00123 |
| 2 | Production Month | INT | - | Month (1-12) | 6 |
| 3 | Production Year | INT | - | Year | 2025 |
| 4 | Lease Oil Production | DECIMAL | BBL | Total oil produced | 125000.00 |
| 5 | Lease Condensate Production | DECIMAL | BBL | Total condensate | 5000.00 |
| 6 | Lease Gas-Well-Gas Production | DECIMAL | MCF | Gas from gas wells | 500000.00 |
| 7 | Lease Oil-Well-Gas Production | DECIMAL | MCF | Associated gas | 75000.00 |
| 8 | Lease Water Production | DECIMAL | BBL | Produced water | 85000.00 |
| 9 | Producing Completions | INT | Count | Active completions | 12 |
| 10 | Lease Max Water Depth | DECIMAL | Meters | Maximum depth | 1250.00 |
| 11 | (Production Date combined) | - | - | May appear as single column | 06/2025 |

---

## Date Range Formatting

### Standard Format
```
MM/YYYY
```

### Examples
| Description | From | To |
|-------------|------|-----|
| Single month | 06/2025 | 06/2025 |
| Calendar year | 01/2024 | 12/2024 |
| Rolling 12 months | 01/2024 | 12/2024 |
| All available | (empty) | (empty) |
| Since specific date | 01/2020 | (empty) |

### Date Handling Notes
- Empty "From" = earliest available data (1966+)
- Empty "To" = most recent available data
- Data typically available through 2-3 months prior to current date

---

## Example Queries

### Query 1: Single Lease Annual Production
```
https://www.data.bsee.gov/Production/ProductionData/Default.aspx
  ?LeaseNumber=G00123
  &ProductionMonthYearFrom=01/2024
  &ProductionMonthYearTo=12/2024
```
Returns monthly production for lease G00123 in 2024.

### Query 2: Multiple Leases
```
https://www.data.bsee.gov/Production/ProductionData/Default.aspx
  ?LeaseNumber=G00123,G00124,G00125
  &ProductionMonthYearFrom=01/2024
  &ProductionMonthYearTo=12/2024
```
Returns production for multiple leases.

### Query 3: High-Volume Oil Producers
```
https://www.data.bsee.gov/Production/ProductionData/Default.aspx
  ?LeaseOilProductionMin=100000
  &ProductionMonthYearFrom=01/2025
  &ProductionMonthYearTo=01/2025
```
Returns leases producing >100,000 BBL oil in January 2025.

### Query 4: Deepwater Production
```
https://www.data.bsee.gov/Production/ProductionData/Default.aspx
  ?LeaseMaxWaterDepthMin=300
  &LeaseMaxWaterDepthMax=1500
  &ProductionMonthYearFrom=01/2024
  &ProductionMonthYearTo=12/2024
```
Returns production from deepwater leases (300-1500m depth).

### Query 5: Gas-Dominant Production
```
https://www.data.bsee.gov/Production/ProductionData/Default.aspx
  ?LeaseGasWellGasProductionMin=1000000
  &LeaseOilProductionMax=1000
  &ProductionMonthYearFrom=01/2024
```
Returns gas-dominant leases (high gas, low oil).

### Query 6: Active Multi-Well Leases
```
https://www.data.bsee.gov/Production/ProductionData/Default.aspx
  ?ProducingCompletionsMin=5
  &ProducingCompletionsMax=50
  &ProductionMonthYearFrom=01/2025
```
Returns leases with 5-50 active completions.

---

## URL Parameter Reference

| Parameter | URL Key | Format | Example |
|-----------|---------|--------|---------|
| Lease Number | LeaseNumber | CSV allowed | G00123,G00124 |
| Date From | ProductionMonthYearFrom | MM/YYYY | 01/2024 |
| Date To | ProductionMonthYearTo | MM/YYYY | 12/2024 |
| Oil Min | LeaseOilProductionMin | Integer | 1000 |
| Oil Max | LeaseOilProductionMax | Integer | 1000000 |
| Condensate Min | LeaseCondensateProductionMin | Integer | 100 |
| Condensate Max | LeaseCondensateProductionMax | Integer | 100000 |
| Gas-Well-Gas Min | LeaseGasWellGasProductionMin | Integer | 10000 |
| Gas-Well-Gas Max | LeaseGasWellGasProductionMax | Integer | 10000000 |
| Oil-Well-Gas Min | LeaseOilWellGasProductionMin | Integer | 5000 |
| Oil-Well-Gas Max | LeaseOilWellGasProductionMax | Integer | 5000000 |
| Water Min | LeaseWaterProductionMin | Integer | 0 |
| Water Max | LeaseWaterProductionMax | Integer | 1000000 |
| Completions Min | ProducingCompletionsMin | Integer | 1 |
| Completions Max | ProducingCompletionsMax | Integer | 50 |
| Depth Min | LeaseMaxWaterDepthMin | Integer (m) | 300 |
| Depth Max | LeaseMaxWaterDepthMax | Integer (m) | 1500 |

---

## Unit Conversions

| From | To | Multiply By |
|------|-----|-------------|
| BBL | US Gallons | 42 |
| BBL | Liters | 158.987 |
| BBL | Cubic Meters | 0.159 |
| MCF | SCF | 1,000 |
| MCF | Cubic Meters | 28.317 |
| MCF | BOE (approx) | 0.167 |
| Meters | Feet | 3.28084 |

---

## Data Aggregation Notes

### Lease-Level Aggregation
- All production volumes are summed across wells on each lease
- Each row represents one lease-month combination
- Producing Completions = count of active completions that month

### Zero Production
- Months with zero production may be omitted from results
- Query may return fewer months than expected for declining leases

### Negative Values
- Corrections may appear as negative adjustments
- Typically indicates prior month over-reporting
- Sum monthly values to get corrected totals

### Data Timing
| Metric | Timing |
|--------|--------|
| Data availability | ~60-90 days after production month |
| Update frequency | Bi-monthly (15th of each month) |
| Historical revisions | May occur for 12+ months |

---

## Tips for Effective Searches

### Performance Tips
1. **Always specify date range** - Open-ended queries return millions of rows
2. **Use lease number when known** - Most efficient filter
3. **Limit volume ranges** - Narrow ranges improve performance
4. **Export in batches** - Split multi-year queries by year

### Data Quality Tips
1. **Account for data lag** - Recent months may be incomplete
2. **Sum for corrections** - Negative values are adjustments
3. **Verify water depth units** - Meters, not feet
4. **Check for missing months** - Zero production months omitted

### Analysis Tips
1. **Calculate GOR** - Gas/Oil Ratio = (GWG + OWG) / Oil
2. **Calculate Water Cut** - Water / (Water + Oil + Condensate)
3. **Aggregate annually** - Sum 12 months for annual totals
4. **Track decline curves** - Monthly data ideal for decline analysis

---

## Common Use Cases

| Use Case | Recommended Approach |
|----------|---------------------|
| Lease production history | Lease Number + full date range |
| Regional production trends | Water Depth range + date range |
| Top producers ranking | Volume minimum + single month |
| Decline curve analysis | Single lease + multi-year range |
| Water cut analysis | Compare water vs oil volumes |
| Field-level rollup | Multiple lease numbers + date range |

---

## Related Production Datasets

| Dataset | URL | Description |
|---------|-----|-------------|
| OGOR-A | /Main/OGOR-A.aspx | Operator production reports |
| FMP | /Production/FMP/Default.aspx | Facility measurement points |
| Planning Area | /Production/PlanningArea/ | Production by planning area |

---

## Related Documents

- [Production Fields](../data-dictionaries/production/production-fields.md) - Field definitions
- [Lease Fields](../data-dictionaries/leasing/lease-fields.md) - Lease information
- [Export Formats](export-formats.md) - Export options and best practices
- [Update Schedule](../data-sources/update-schedule.md) - Data refresh timing
