# Export Formats

> **Applies To**: All BSEE Online Query Interfaces
> **Base URL**: https://www.data.bsee.gov/{Category}/{Dataset}/Default.aspx
> **Available Formats**: PDF, XLS, XLSX, RTF, CSV

---

## Overview

All BSEE online query interfaces support five export formats. Each format has specific characteristics, limitations, and recommended use cases. This document covers format specifications, best practices, and troubleshooting guidance.

---

## Format Comparison

| Format | Extension | Max Rows | Best For | File Size |
|--------|-----------|----------|----------|-----------|
| PDF | .pdf | ~10,000 | Reports, sharing | Large |
| XLS | .xls | ~65,536 | Legacy Excel | Medium |
| XLSX | .xlsx | ~50,000 | Modern Excel | Medium |
| RTF | .rtf | ~10,000 | Word processing | Large |
| CSV | .csv | ~50,000+ | Data processing | Small |

---

## Format Details

### PDF (Portable Document Format)

| Attribute | Value |
|-----------|-------|
| Extension | .pdf |
| MIME Type | application/pdf |
| Max Rows | ~10,000 (varies) |
| Formatting | Preserved |
| Images | Included |

**Characteristics:**
- Formatted report layout
- Includes headers and footers
- Page numbers and dates
- BSEE branding/logos
- Suitable for printing

**Limitations:**
- Not suitable for data analysis
- Row limit more restrictive
- Large file sizes
- Cannot be directly imported to databases

**Use Cases:**
- Official reports
- Documentation
- Email attachments
- Print distribution

---

### XLS (Excel 2003 Binary)

| Attribute | Value |
|-----------|-------|
| Extension | .xls |
| MIME Type | application/vnd.ms-excel |
| Max Rows | 65,536 (Excel limit) |
| Formatting | Basic |
| Compatibility | Excel 97-2003 |

**Characteristics:**
- Binary Excel format
- Column headers included
- Basic number formatting
- Wide compatibility

**Limitations:**
- 65,536 row limit (Excel 2003 limit)
- 256 column limit
- Larger file size than XLSX
- Older format

**Use Cases:**
- Legacy system compatibility
- Small to medium datasets
- Quick Excel analysis
- Systems requiring .xls format

---

### XLSX (Excel 2007+ XML)

| Attribute | Value |
|-----------|-------|
| Extension | .xlsx |
| MIME Type | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |
| Max Rows | ~50,000 (server limit) |
| Formatting | Enhanced |
| Compatibility | Excel 2007+ |

**Characteristics:**
- Modern XML-based format
- Column headers included
- Better compression
- Wider column support (16,384)

**Limitations:**
- Server-side row limit (~50,000)
- Requires Excel 2007 or later
- Some legacy systems incompatible

**Use Cases:**
- Excel analysis and visualization
- Pivot tables
- Charts and graphs
- Sharing with non-technical users

---

### RTF (Rich Text Format)

| Attribute | Value |
|-----------|-------|
| Extension | .rtf |
| MIME Type | application/rtf |
| Max Rows | ~10,000 |
| Formatting | Tables |
| Compatibility | Universal |

**Characteristics:**
- Word processor compatible
- Table formatting preserved
- Headers and footers
- Editable format

**Limitations:**
- Not suitable for data analysis
- Large file sizes
- Restrictive row limit
- Slow export for large datasets

**Use Cases:**
- Word processing integration
- Report editing
- Document templates
- Text extraction

---

### CSV (Comma-Separated Values)

| Attribute | Value |
|-----------|-------|
| Extension | .csv |
| MIME Type | text/csv |
| Max Rows | ~50,000+ |
| Formatting | None |
| Encoding | UTF-8 |

**Characteristics:**
- Plain text format
- Smallest file size
- Universal compatibility
- Fast export
- Highest row limit

**Limitations:**
- No formatting
- No multiple sheets
- Special character handling required
- Date format may vary

**Use Cases:**
- Data analysis
- Database import
- Programming/scripting
- GIS import
- Large datasets

---

## Recommendations by Use Case

### Data Analysis & Processing

| Priority | Format | Reason |
|----------|--------|--------|
| 1 | CSV | Highest row limit, smallest size, universal |
| 2 | XLSX | If Excel analysis needed |
| 3 | XLS | Legacy system requirement only |

### Reporting & Documentation

| Priority | Format | Reason |
|----------|--------|--------|
| 1 | PDF | Best formatting, print-ready |
| 2 | RTF | If editing needed |
| 3 | XLSX | If data tables required |

### Database Import

| Priority | Format | Reason |
|----------|--------|--------|
| 1 | CSV | Standard import format |
| 2 | XLSX | If CSV parsing issues |

### GIS Integration

| Priority | Format | Reason |
|----------|--------|--------|
| 1 | CSV | Direct import to GIS tools |
| 2 | XLSX | Alternative for QGIS/ArcGIS |

---

## Export Limitations

### Row Limits by Query Type

| Query Type | Typical Max Rows | Notes |
|------------|------------------|-------|
| Borehole | ~57,000 | Full dataset |
| Production | ~50,000 | Monthly data |
| Platform | ~15,000 | All structures |
| Pipeline | ~50,000 | Per segment query |
| Lease | ~30,000 | All leases |

### Handling Large Datasets

**When export limit exceeded:**
1. Add filters to reduce result count
2. Split query by date range
3. Split query by area/region
4. Use raw data downloads instead

**Raw Data Alternative:**
```
https://www.data.bsee.gov/{Category}/Files/{Dataset}RawData.zip
```

### Server Timeout Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Export fails | Too many rows | Add filters |
| Partial data | Timeout | Reduce date range |
| Empty file | Query error | Check parameters |
| Corrupted file | Connection issue | Retry export |

---

## CSV Best Practices

### Import Settings

| Setting | Recommended Value |
|---------|-------------------|
| Delimiter | Comma (,) |
| Text Qualifier | Double quote (") |
| Encoding | UTF-8 |
| Header Row | Yes (first row) |

### Date Handling

| Field Type | Export Format | Import Format |
|------------|---------------|---------------|
| Date | MM/DD/YYYY | Parse as date |
| DateTime | YYYY-MM-DD HH:MM:SS | Parse as datetime |
| Month/Year | MM/YYYY | Parse as string |

### Numeric Fields

| Issue | Solution |
|-------|----------|
| Leading zeros lost | Import as text |
| Scientific notation | Format column |
| Decimal precision | Set column type |

### Special Characters

| Character | Handling |
|-----------|----------|
| Comma | Enclosed in quotes |
| Quote | Escaped as "" |
| Newline | Enclosed in quotes |
| Non-ASCII | UTF-8 encoded |

---

## Excel Best Practices

### XLSX Import Tips

1. **Open directly** - Double-click to open in Excel
2. **Data connections** - May prompt for refresh
3. **Column formatting** - Apply after import
4. **Save as** - Convert to native format for features

### Common Issues

| Issue | Solution |
|-------|----------|
| API numbers as scientific | Format column as Text |
| Dates as numbers | Format as Date |
| Truncated text | Widen column |
| Missing columns | Check export settings |

### Preserving Data Types

```
API Number: Format as Text (prevents scientific notation)
Dates: Format as Date
Coordinates: Format as Number (6 decimal places)
Lease Numbers: Format as Text
```

---

## Data Processing Pipeline

### Recommended Workflow

```
1. Query Interface
   ↓
2. CSV Export
   ↓
3. Data Validation
   ↓
4. Database Import
   ↓
5. Analysis/Reporting
```

### Python Example

```python
import pandas as pd

# Read CSV export
df = pd.read_csv(
    'borehole_export.csv',
    dtype={
        'API Well Number': str,  # Preserve leading zeros
        'Bottom Lease Number': str,
        'Surface Lease Number': str
    },
    parse_dates=['Spud Date', 'Total Depth Date', 'Status Date']
)

# Verify data types
print(df.dtypes)
print(f"Records: {len(df)}")
```

### SQL Import Example

```sql
-- Create staging table
CREATE TABLE borehole_staging (
    api_well_number VARCHAR(12),
    well_name VARCHAR(50),
    spud_date DATE,
    water_depth DECIMAL(10,2),
    ...
);

-- Import CSV
COPY borehole_staging FROM '/path/to/export.csv'
WITH (FORMAT CSV, HEADER TRUE);
```

---

## Export URL Parameters

### Triggering Export

While most exports are triggered through the UI, understanding the export mechanism helps with automation:

| Action | Method |
|--------|--------|
| View Results | Default query page |
| Export PDF | Export button > PDF |
| Export XLS | Export button > XLS |
| Export XLSX | Export button > XLSX |
| Export RTF | Export button > RTF |
| Export CSV | Export button > CSV |

### Automation Considerations

- BSEE does not provide direct export URLs
- Session-based authentication required
- Use raw data downloads for bulk access
- Consider API alternatives where available

---

## Troubleshooting

### Export Failures

| Error | Cause | Solution |
|-------|-------|----------|
| "Too many records" | Row limit exceeded | Add filters |
| "Session expired" | Timeout | Refresh page, re-query |
| "File not found" | Export failed | Retry with smaller dataset |
| "Cannot open file" | Corrupt download | Re-download |

### Data Quality Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Missing columns | Export truncation | Use CSV format |
| Garbled text | Encoding mismatch | Specify UTF-8 |
| Wrong dates | Format mismatch | Parse explicitly |
| Duplicate rows | Query overlap | Deduplicate |

### Format-Specific Issues

| Format | Issue | Solution |
|--------|-------|----------|
| PDF | Pages cut off | Reduce columns |
| XLS | Row limit hit | Use XLSX or CSV |
| XLSX | Cannot open | Update Excel version |
| RTF | Formatting lost | Use PDF instead |
| CSV | Commas in data | Check quoting |

---

## Raw Data Downloads

For large datasets, consider raw data downloads instead of query exports:

| Dataset | URL | Size |
|---------|-----|------|
| Borehole | /Well/Files/BoreholeRawData.zip | ~15 MB |
| Production | /Production/Files/ProductionRawData.zip | ~500 MB |
| Platform | /Platform/Files/PlatStrucRawData.zip | ~5 MB |
| Pipeline | /Pipeline/Files/PipeLocRawData.zip | ~50 MB |

**Advantages:**
- No row limits
- Complete dataset
- Faster download
- Offline processing

**See Also:** [Raw Data Downloads](../data-sources/raw-data-downloads.md)

---

## Related Documents

- [Query Interfaces Index](index.md) - All query interfaces
- [Raw Data Downloads](../data-sources/raw-data-downloads.md) - Bulk data access
- [Update Schedule](../data-sources/update-schedule.md) - Data refresh timing
- [Data Dictionaries](../data-dictionaries/index.md) - Field definitions
