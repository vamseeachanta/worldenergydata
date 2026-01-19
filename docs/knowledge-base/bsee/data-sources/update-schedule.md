# BSEE Data Update Schedule

> **Source**: BSEE Data Center
> **Note**: Schedules are approximate and may vary
> **Last Verified**: 2026-01-18

---

## Update Frequency Summary

| Frequency | Dataset Types | Count |
|-----------|---------------|-------|
| Daily | Well APD, WAR, Borehole, eWell | 10 |
| Bi-monthly | Production (15th) | 8 |
| Monthly | Platforms, Leasing, Company | 12 |
| As Reported | Pipelines, Plans | 8 |
| Annual | Decom Costs, Royalty Relief | 2 |

---

## Daily Updates

| Dataset | Update Time | Notes |
|---------|-------------|-------|
| APDRawData.zip | ~6:00 AM CST | Application permits |
| BoreholeRawData.zip | ~6:00 AM CST | Borehole data |
| eWellAPDRawData.zip | ~6:00 AM CST | eWell APD submissions |
| eWellAPMRawData.zip | ~6:00 AM CST | eWell APM submissions |
| eWellEORRawData.zip | ~6:00 AM CST | eWell EOR submissions |
| eWellWARRawData.zip | ~6:00 AM CST | Well Activity Reports |
| APIRawData.zip | ~6:00 AM CST | API lookups |

---

## Bi-Monthly Updates

| Dataset | Update Day | Notes |
|---------|------------|-------|
| ProductionRawData.zip | 15th | Previous month's data |
| ogoradelimit.zip | 15th | OGOR-A historical |
| OGORRawDataSet.zip | 15th | Complete OGOR |

### Production Data Timing
- **Report Date**: 15th of each month
- **Coverage**: Previous month's production
- **Lag**: ~45 days from production date

Example:
- January production → Reported March 15
- February production → Reported April 15

---

## Monthly Updates

| Dataset | Approximate Day | Notes |
|---------|-----------------|-------|
| PlatStrucRawData.zip | 1st week | Platform structures |
| FMPRawData.zip | 1st week | Facility measurement points |
| FMPMetersRawData.zip | 1st week | Meters/tanks |
| OffshoreStatsRawData.zip | 1st week | Statistics by depth |
| LABRawData.zip | 1st week | Lease area block |
| LeaseOwnerRawData.zip | 1st week | Lease ownership |
| CompanyRawData.zip | 1st week | Company data |
| INCSRawData.zip | 1st week | Non-compliance |
| IncInvRawData.zip | 1st week | Incident investigations |

---

## GIS Data Updates

| Dataset | Approximate Frequency | Last Update |
|---------|----------------------|-------------|
| Platforms | Monthly | 01/02/2026 |
| Pipelines | Monthly | 01/02/2026 |
| Active Leases | Monthly | 01/02/2026 |
| Blocks | Quarterly | 02/11/2025 |
| Protractions | Quarterly | 02/11/2025 |
| Fed/State Boundary | As needed | 02/11/2025 |

---

## As-Reported Updates

These datasets update when changes are reported:

| Dataset | Trigger | Typical Frequency |
|---------|---------|-------------------|
| PipeLocRawData.zip | Pipeline changes | Weekly-Monthly |
| PipePermRawData.zip | New permits | Weekly |
| RowDescRawData.zip | ROW changes | Monthly |
| AssignmentsRawData.zip | Ownership transfers | Weekly |
| PlansRawData.zip | Plan submissions | Weekly |
| APIChangesRawData.zip | API number changes | As needed |

---

## Annual Updates

| Dataset | Update Month | Notes |
|---------|--------------|-------|
| DecomCostEstRawData.zip | Q1 | Decommissioning estimates |
| RoyaltyRefRawData.zip | Q1 | Royalty relief |
| DeepQualRawData.zip | Q1 | Deepwater qualified fields |

---

## Update Monitoring

### Check Last Modified Header
```python
import requests

url = "https://www.data.bsee.gov/Well/Files/APDRawData.zip"
response = requests.head(url)
last_modified = response.headers.get('Last-Modified')
print(f"Last updated: {last_modified}")
```

### Compare File Sizes
```python
# Compare current size to cached size
current_size = response.headers.get('Content-Length')
if current_size != cached_size:
    print("Dataset has been updated")
```

---

## Scheduled Download Script

```python
from datetime import datetime, timedelta

SCHEDULE = {
    "daily": ["APDRawData.zip", "BoreholeRawData.zip", "eWellWARRawData.zip"],
    "bi_monthly": ["ProductionRawData.zip"],  # 15th
    "monthly": ["PlatStrucRawData.zip", "LABRawData.zip"],  # 1st week
}

def should_download(dataset: str) -> bool:
    today = datetime.now()

    if dataset in SCHEDULE["daily"]:
        return True
    elif dataset in SCHEDULE["bi_monthly"]:
        return today.day == 15
    elif dataset in SCHEDULE["monthly"]:
        return today.day <= 7
    return False
```

---

## Data Freshness Notes

1. **Well Data**: Most current, updated daily
2. **Production Data**: ~45 day lag from actual production
3. **Platforms**: Monthly snapshot, may lag changes
4. **Leasing**: Generally current within 1 week
5. **GIS Data**: Updated first week of month

---

## Notification

BSEE does not provide update notifications. Monitor:
- Last-Modified HTTP headers
- File sizes
- "Data Last Updated" timestamps on web pages

---

## Related Documents

- [Raw Data Downloads](raw-data-downloads.md) - Complete download list
- [Data Sources Index](index.md) - All URLs
- [Codebase Mapping](../integration/codebase-mapping.md) - Scraper integration
