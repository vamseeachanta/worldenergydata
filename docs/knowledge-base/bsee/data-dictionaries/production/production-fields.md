# Production Data Fields

> **Dataset**: Production Data
> **Source**: https://www.data.bsee.gov/Production/ProductionData/Default.aspx
> **Raw Data**: https://www.data.bsee.gov/Production/Files/ProductionRawData.zip
> **Update Frequency**: Bi-monthly (15th of each month)
> **Last Updated**: 2026-01-15

---

## Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| Lease Number | Text | Lease identifier (1-100 chars) | G00123 |
| Production Month/Year From | Date | Start of date range | 01/2020 |
| Production Month/Year To | Date | End of date range | 12/2025 |
| Lease Oil Production (BBL) | Range | Oil volume range | 1000-50000 |
| Lease Condensate Production (BBL) | Range | Condensate volume range | 100-5000 |
| Lease Gas-Well-Gas Production (MCF) | Range | Gas-well gas volume | 10000-500000 |
| Lease Oil-Well-Gas Production (MCF) | Range | Associated gas volume | 5000-100000 |
| Lease Water Production (BBL) | Range | Water volume range | 0-100000 |
| Producing Completions | Range | Number of completions (0-200) | 1-50 |
| Lease Max Water Depth (meters) | Range | Max water depth (0-3000) | 500-1500 |

---

## Result Fields (11 Columns)

| Field | Type | Description | Example | Unit |
|-------|------|-------------|---------|------|
| Lease Number | VARCHAR(10) | OCS lease identifier | G00123 | - |
| Production Month | INT | Month of production (1-12) | 6 | - |
| Production Year | INT | Year of production | 2025 | - |
| Lease Oil Production | DECIMAL(12,2) | Total oil produced | 125000.00 | BBL |
| Lease Condensate Production | DECIMAL(12,2) | Total condensate produced | 5000.00 | BBL |
| Lease Gas-Well-Gas Production | DECIMAL(12,2) | Gas from gas wells | 500000.00 | MCF |
| Lease Oil-Well-Gas Production | DECIMAL(12,2) | Associated gas from oil wells | 75000.00 | MCF |
| Lease Water Production | DECIMAL(12,2) | Total water produced | 85000.00 | BBL |
| Producing Completions | INT | Number of active completions | 12 | Count |
| Lease Max Water Depth | DECIMAL(8,2) | Maximum water depth | 1250.00 | Meters |

---

## Field Definitions

### Lease Number
- Format: Alphanumeric, typically starting with G (Gulf) or other region prefix
- Length: Up to 10 characters
- Examples: G00123, G34567, P00012 (Pacific)

### Production Volumes

| Volume Type | Description | Notes |
|-------------|-------------|-------|
| Oil Production | Crude oil from all wells | BBL (42 US gallons) |
| Condensate Production | Light hydrocarbons from gas | BBL |
| Gas-Well-Gas | Gas from gas wells | MCF (1000 cu ft) |
| Oil-Well-Gas | Associated gas from oil wells | MCF |
| Water Production | Produced water (brine) | BBL |

### Water Depth
- Measured in **meters** (not feet)
- Convert to feet: multiply by 3.28084
- Maximum lease water depth across all wells on lease

---

## Unit Conversions

| From | To | Multiply By |
|------|-----|-------------|
| BBL | Gallons | 42 |
| BBL | Liters | 158.987 |
| MCF | SCF | 1,000 |
| MCF | Cubic Meters | 28.317 |
| Meters | Feet | 3.28084 |

---

## Aggregation Notes

- Data is aggregated **by lease** for each month
- Multiple wells on a lease are summed together
- Producing Completions = count of active completions on the lease

---

## Historical Data

| Period | Data Availability | Notes |
|--------|-------------------|-------|
| 1966-Present | Complete | Via OGOR-A archives |
| Pre-1966 | Limited | Some historical data available |

### OGOR Report Types

| Report | Description | Frequency |
|--------|-------------|-----------|
| OGOR-A | Operator's Oil and Gas Operations Report | Monthly |
| OGOR-B | Well-level production | Monthly |
| OGOR-C | Injection/disposal | Monthly |

---

## Sample Query

```
https://www.data.bsee.gov/Production/ProductionData/Default.aspx
  ?LeaseNumber=G00123
  &ProductionMonthYearFrom=01/2024
  &ProductionMonthYearTo=12/2024
```

---

## Data Quality Notes

1. **Zero Production**: Months with no production may be omitted
2. **Negative Values**: Corrections may appear as negative adjustments
3. **Estimated Values**: Some values may be estimated pending verification
4. **Timing**: Data typically lags 2-3 months behind current date

---

## Export Formats

Available export options:
- PDF
- XLS (Excel 2003)
- XLSX (Excel 2007+)
- RTF (Rich Text)
- CSV (Comma-separated)

---

## Related Documents

- [OGOR Reports](ogor-reports.md) - Detailed OGOR documentation
- [FMP Fields](fmp-fields.md) - Facility Measurement Points
- [Lease Fields](../leasing/lease-fields.md) - Lease information
- [Planning Area](planning-area.md) - Production by planning area
