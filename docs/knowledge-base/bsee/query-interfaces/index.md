# BSEE Online Query Interfaces

> **Base URL**: https://www.data.bsee.gov/{Category}/{Dataset}/Default.aspx
> **Export Formats**: PDF, XLS, XLSX, RTF, CSV
> **Total Interfaces**: 22+ query pages

---

## Quick Reference

| Category | Query Interfaces | Primary Use |
|----------|------------------|-------------|
| Wells | 5 | Well/borehole lookup |
| Production | 4 | Production data search |
| Platforms | 2 | Structure queries |
| Pipelines | 3 | Pipeline location/permits |
| Leasing | 4 | Lease information |
| Company | 2 | Operator data |
| Other | 2 | Miscellaneous |

---

## Wells

| Query | URL | Filters | Columns |
|-------|-----|---------|---------|
| Borehole | [Link](https://www.data.bsee.gov/Well/Borehole/Default.aspx) | 10 | 27 |
| APD | [Link](https://www.data.bsee.gov/Well/APD/Default.aspx) | 8 | 20+ |
| API Lookup | [Link](https://www.data.bsee.gov/Well/API/Default.aspx) | 5 | 15 |
| BHPS | [Link](https://www.data.bsee.gov/Well/BHPS/Default.aspx) | 6 | 18 |
| Directional Survey | [Link](https://www.data.bsee.gov/Well/DirSurvey/Default.aspx) | 4 | 12 |

### Borehole Query Filters
- Region, Bottom Area, Bottom Block
- Bottom Lease Number, API Number
- Company Name, Status Code, Type Code
- Water Depth (range), Spud Date (range)

---

## Production

| Query | URL | Filters | Columns |
|-------|-----|---------|---------|
| Production Data | [Link](https://www.data.bsee.gov/Production/ProductionData/Default.aspx) | 9 | 11 |
| OGOR-A | [Link](https://www.data.bsee.gov/Main/OGOR-A.aspx) | 6 | 15 |
| FMP | [Link](https://www.data.bsee.gov/Production/FMP/Default.aspx) | 5 | 12 |
| Production Overview | [Link](https://www.data.bsee.gov/Main/Production.aspx) | - | - |

### Production Data Query Filters
- Lease Number
- Production Month/Year (from/to)
- Oil, Condensate, Gas, Water production (ranges)
- Producing Completions (range)
- Max Water Depth (range)

---

## Platforms

| Query | URL | Filters | Columns |
|-------|-----|---------|---------|
| Platform Structures | [Link](https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx) | 13 | 28 |
| Deepwater Structures | [Link](https://www.data.bsee.gov/Other/DataTables/PermDeepStruc.aspx) | 5 | 20 |

### Platform Structures Query Filters
- Area, Block Number, Lease Number
- Field, Complex ID, Structure Name
- Company Name, Water Depth (range)
- Installation/Removal/Clearance Date (ranges)
- Non-Removed Structures (checkbox)
- Non-Site Clearance (checkbox)

---

## Pipelines

| Query | URL | Filters | Columns |
|-------|-----|---------|---------|
| Pipeline Location | [Link](https://www.data.bsee.gov/Pipeline/PipelineLocation/Default.aspx) | 3 | 13 |
| Pipeline Permits | [Link](https://www.data.bsee.gov/Pipeline/PipelinePermits/Default.aspx) | 5 | 18 |
| ROW Descriptions | [Link](https://www.data.bsee.gov/Pipeline/ROW/Default.aspx) | 4 | 10 |

### Pipeline Location Query Filters
- Segment Number (required)
- Last Revised Date (range)
- Version Date (range)

**Note**: Segment Number is required to limit results.

---

## Leasing

| Query | URL | Filters | Columns |
|-------|-----|---------|---------|
| Lease Area Block | [Link](https://www.data.bsee.gov/Leasing/LeaseAreaBlock/Default.aspx) | 8 | 15 |
| Lease Owner | [Link](https://www.data.bsee.gov/Leasing/LeaseOwner/Default.aspx) | 5 | 12 |
| Assignments | [Link](https://www.data.bsee.gov/Leasing/Assignments/Default.aspx) | 4 | 10 |
| Decom Cost Estimates | [Link](https://www.data.bsee.gov/Leasing/DecomCostEst/Default.aspx) | 3 | 8 |

---

## Company

| Query | URL | Filters | Columns |
|-------|-----|---------|---------|
| Company Detail | [Link](https://www.data.bsee.gov/Company/CompanyDetail/Default.aspx) | 3 | 10 |
| INCs | [Link](https://www.data.bsee.gov/Company/INCs/Default.aspx) | 5 | 15 |

---

## Export Options

All query interfaces support these export formats:

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | .pdf | Formatted report |
| XLS | .xls | Excel 2003 |
| XLSX | .xlsx | Excel 2007+ |
| RTF | .rtf | Rich Text Format |
| CSV | .csv | Comma-separated |

### Export Limitations
- Maximum rows per export: ~50,000 (varies by query)
- Large datasets may require filtering
- CSV recommended for data processing

---

## Common Query Parameters

### Date Ranges
- Format: MM/DD/YYYY
- Use "From" and "To" fields
- Empty "To" = current date

### Numeric Ranges
- Slider controls (min/max)
- Direct input also accepted

### Dropdown Filters
- Single-select or multi-select
- Type-ahead search available

### Checkboxes
- Toggle boolean filters
- Example: "List Non-Removed Structures"

---

## URL Query String Examples

### Borehole Query
```
https://www.data.bsee.gov/Well/Borehole/Default.aspx
  ?Region=Gulf%20of%20America
  &WaterDepthMin=1000
  &WaterDepthMax=5000
  &StatusCode=COM
```

### Production Query
```
https://www.data.bsee.gov/Production/ProductionData/Default.aspx
  ?LeaseNumber=G00123
  &ProductionMonthYearFrom=01/2024
  &ProductionMonthYearTo=12/2024
```

### Platform Query
```
https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
  ?Area=AC
  &ListNonRemovedStructures=true
```

---

## Query Interface Documentation

Each query interface has detailed documentation:

- [Borehole Query](borehole-query.md)
- [Production Query](production-query.md)
- [Platform Query](platform-query.md)
- [Pipeline Query](pipeline-query.md)
- [Lease Query](lease-query.md)
- [Export Formats](export-formats.md)

---

## Tips for Effective Queries

1. **Use specific filters** to reduce result size
2. **Export as CSV** for data processing
3. **Check record counts** before export
4. **Use date ranges** to limit results
5. **Combine filters** for targeted searches

---

## Related Documents

- [Data Sources Index](../data-sources/index.md) - URL registry
- [Borehole Fields](../data-dictionaries/wells/borehole-fields.md) - Field definitions
- [Production Fields](../data-dictionaries/production/production-fields.md) - Production fields
- [Platform Fields](../data-dictionaries/platforms/structure-fields.md) - Platform fields
