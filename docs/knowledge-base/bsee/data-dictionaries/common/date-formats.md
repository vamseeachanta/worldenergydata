# Date Formats & Conventions

> **Usage**: Date handling across BSEE datasets
> **Formats**: Multiple formats depending on data source
> **Critical**: Production uses YYYYMM; permits use MM/DD/YYYY

---

## Quick Reference

| Dataset | Format | Example | Field Names |
|---------|--------|---------|-------------|
| Production | YYYYMM | 202401 | PROD_DATE, PRODUCTION_DATE |
| Wells/Boreholes | MM/DD/YYYY | 01/15/2024 | SPUD_DATE, COMPLETION_DATE |
| Permits (APD) | MM/DD/YYYY | 01/15/2024 | RECEIVED_DATE, APPROVED_DATE |
| Leases | MM/DD/YYYY | 01/15/2024 | EFFECTIVE_DATE, EXPIRATION_DATE |
| Incidents | MM/DD/YYYY | 01/15/2024 | INCIDENT_DATE, REPORT_DATE |

---

## Production Date Format

### YYYYMM Format

| Component | Position | Example |
|-----------|----------|---------|
| Year | 1-4 | 2024 |
| Month | 5-6 | 01 |

### Parsing Examples

```python
from datetime import datetime

# Parse production date
prod_date = "202401"
dt = datetime.strptime(prod_date, "%Y%m")
# Result: datetime(2024, 1, 1)

# Convert to first/last of month
first_day = dt.replace(day=1)
last_day = (dt.replace(month=dt.month % 12 + 1, day=1)
            - timedelta(days=1))
```

### Production Month Convention

| Convention | Description |
|------------|-------------|
| Report Month | Month production occurred |
| Lag | Data typically 2-3 months behind |
| Amendments | Prior months may be amended |

---

## Standard Date Format (MM/DD/YYYY)

### Used In

| Dataset | Date Fields |
|---------|-------------|
| Wells | SPUD_DATE, TD_DATE, COMPLETION_DATE, STATUS_DATE |
| APD | RECEIVED_DATE, APPROVED_DATE, EXPIRE_DATE |
| WAR | START_DATE, END_DATE, REPORT_DATE |
| Platforms | INSTALL_DATE, REMOVAL_DATE |
| Pipelines | IN_SERVICE_DATE, OUT_SERVICE_DATE |

### Parsing Examples

```python
from datetime import datetime

# Parse MM/DD/YYYY
date_str = "01/15/2024"
dt = datetime.strptime(date_str, "%m/%d/%Y")

# Handle potential formats
def parse_bsee_date(date_str):
    """Parse BSEE dates with format detection."""
    if not date_str or date_str in ('', 'NULL', 'None'):
        return None

    formats = [
        "%m/%d/%Y",   # 01/15/2024
        "%Y-%m-%d",   # 2024-01-15 (ISO)
        "%m-%d-%Y",   # 01-15-2024
        "%Y%m%d",     # 20240115
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None
```

---

## Date Range Queries

### BSEE Query Interface

| Parameter | Format | Example |
|-----------|--------|---------|
| Start Date | MM/DD/YYYY | 01/01/2020 |
| End Date | MM/DD/YYYY | 12/31/2024 |
| Production Month | YYYYMM | 202401 |

### API Query Examples

```
# Wells by spud date range
?SpudDateStart=01/01/2020&SpudDateEnd=12/31/2024

# Production by month range
?ProductionDateStart=202001&ProductionDateEnd=202412

# APD by approval date
?ApprovalDateStart=01/01/2023&ApprovalDateEnd=12/31/2023
```

### SQL Examples

```sql
-- Production date range (YYYYMM format)
SELECT * FROM production
WHERE prod_date BETWEEN '202001' AND '202412';

-- Well date range (convert string to date)
SELECT * FROM wells
WHERE STR_TO_DATE(spud_date, '%m/%d/%Y')
      BETWEEN '2020-01-01' AND '2024-12-31';
```

---

## Fiscal Year Conventions

### Federal Fiscal Year

| FY | Start | End |
|----|-------|-----|
| FY2024 | Oct 1, 2023 | Sep 30, 2024 |
| FY2025 | Oct 1, 2024 | Sep 30, 2025 |

### Quarterly Reporting

| Quarter | Months | FY Quarter |
|---------|--------|------------|
| Q1 | Jan-Mar | FY Q2 |
| Q2 | Apr-Jun | FY Q3 |
| Q3 | Jul-Sep | FY Q4 |
| Q4 | Oct-Dec | FY Q1 (next) |

### Calendar vs Fiscal Year

```python
def get_fiscal_year(date):
    """Return federal fiscal year for a date."""
    if date.month >= 10:  # Oct-Dec
        return date.year + 1
    return date.year

def get_fiscal_quarter(date):
    """Return federal fiscal quarter (1-4)."""
    month_to_fq = {
        10: 1, 11: 1, 12: 1,  # Q1: Oct-Dec
        1: 2, 2: 2, 3: 2,     # Q2: Jan-Mar
        4: 3, 5: 3, 6: 3,     # Q3: Apr-Jun
        7: 4, 8: 4, 9: 4      # Q4: Jul-Sep
    }
    return month_to_fq[date.month]
```

---

## Historical Date Handling

### Date Ranges in BSEE Data

| Era | Date Range | Notes |
|-----|------------|-------|
| Modern | 2000-present | Complete digital records |
| Transition | 1985-1999 | Most data digitized |
| Historical | 1947-1984 | Partial records, possible gaps |
| Pre-OCS | Before 1947 | Limited federal data |

### Null/Missing Dates

| Value | Meaning |
|-------|---------|
| NULL | Not recorded |
| 01/01/1900 | Placeholder for unknown |
| 12/31/9999 | No expiration / ongoing |
| Empty string | Not applicable |

### Handling Missing Dates

```python
def clean_bsee_date(date_str):
    """Clean BSEE date handling special values."""
    if not date_str:
        return None

    # Known placeholder dates
    placeholders = ['01/01/1900', '12/31/9999', '00/00/0000']
    if date_str in placeholders:
        return None

    return parse_bsee_date(date_str)
```

---

## Time Zone Considerations

| Context | Time Zone |
|---------|-----------|
| BSEE Data Portal | Central Time (CT) |
| Production Reports | No time component |
| Incident Reports | Local time (varies) |
| API Timestamps | UTC recommended |

---

## Date Field Reference by Dataset

### Wells

| Field | Format | Description |
|-------|--------|-------------|
| SPUD_DATE | MM/DD/YYYY | Drilling start |
| TD_DATE | MM/DD/YYYY | Total depth reached |
| COMPLETION_DATE | MM/DD/YYYY | Well completed |
| STATUS_DATE | MM/DD/YYYY | Last status change |
| PLUG_DATE | MM/DD/YYYY | Plugged/abandoned |

### Production

| Field | Format | Description |
|-------|--------|-------------|
| PROD_DATE | YYYYMM | Production month |
| FIRST_PROD_DATE | YYYYMM | First production |
| LAST_PROD_DATE | YYYYMM | Most recent production |

### Permits (APD)

| Field | Format | Description |
|-------|--------|-------------|
| RECEIVED_DATE | MM/DD/YYYY | Application received |
| APPROVED_DATE | MM/DD/YYYY | Permit approved |
| EXPIRE_DATE | MM/DD/YYYY | Permit expiration |

---

## Related Documents

- [Production Fields](../production/production-fields.md) - Production date usage
- [Borehole Fields](../wells/borehole-fields.md) - Well date fields
- [API Number Format](api-number-format.md) - Well identification
