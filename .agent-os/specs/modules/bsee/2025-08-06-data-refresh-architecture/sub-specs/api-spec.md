# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/modules/bsee/2025-08-06-data-refresh-architecture/spec.md

> Created: 2025-08-06
> Version: 1.0.0

## Overview

While BSEE doesn't provide a formal REST API, this specification documents the web scraping endpoints and future API integration points for the data refresh system.

## Web Scraping Endpoints

### Production Data Query

**URL:** https://www.data.bsee.gov/Production/OCSProduction/Default.aspx

**Purpose:** Retrieve oil and gas production data by date range, lease, or operator

**Method:** GET (with form submission via POST)

**Parameters:**
- `startDate` - Beginning of date range (MM/DD/YYYY)
- `endDate` - End of date range (MM/DD/YYYY)
- `leaseNumber` - Optional lease filter
- `operatorNumber` - Optional operator filter
- `productType` - O (oil), G (gas), or both

**Response:** HTML table with production records

**Scraping Strategy:**
```python
# Use selectolax for fast parsing
# Extract table data with CSS selectors
# Handle pagination if results > 1000 rows
```

### Well/API Data Query

**URL:** https://www.data.bsee.gov/Well/API/Default.aspx

**Purpose:** Access well information including API numbers and drilling data

**Method:** GET/POST

**Parameters:**
- `apiNumber` - Specific API well number
- `blockNumber` - Block area filter
- `leaseNumber` - Lease filter
- `wellStatus` - Active/Inactive/All

**Response:** HTML table with well details

**Error Handling:**
- 404: Invalid parameters or no data
- 500: Server error, implement retry
- Rate limiting: 429 responses require backoff

### WAR (Well Activity Report) Data

**URL:** https://www.data.bsee.gov/Other/FileRequestSystem/Default.aspx

**Purpose:** Request well activity reports and documentation

**Method:** Multi-step form submission

**Process:**
1. GET initial form page
2. POST search criteria
3. Parse results page
4. Submit file request
5. Poll for download readiness

**Parameters:**
- `reportType` - WAR
- `dateRange` - Activity date filter
- `api` - Well API number(s)

## File Download Endpoints

### Production Raw Data

**URL:** https://www.data.bsee.gov/Main/RawData.aspx

**File:** ProductionRawData.zip

**Purpose:** Bulk download of all production data

**Method:** Direct file download

**Update Frequency:** Weekly (Thursdays)

**File Structure:**
```
ProductionRawData.zip
├── opcprod2024.txt  # Current year data
├── opcprod2023.txt  # Previous years
└── layout.txt       # Field definitions
```

### Platform/Rig Data

**URL:** https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx

**Purpose:** Platform and rig information including coordinates

**Download Options:**
- Full dataset (ZIP)
- Query results (CSV export)

## Internal API Design (CLI Interface)

### Refresh Command

**Endpoint:** `python -m worldenergydata.bsee refresh`

**Parameters:**
```bash
--data-type [war|production|well|all]    # Data to refresh
--date-range START:END                    # Date filter
--source [auto|web|file]                  # Data source
--config PATH                             # Config file
--output PATH                             # Output directory
--verbose                                 # Detailed logging
--dry-run                                # Preview without download
--force                                  # Ignore cache
```

**Response Format:**
```json
{
  "status": "success",
  "data_types": ["production", "well"],
  "records_processed": 15234,
  "new_records": 127,
  "updated_records": 43,
  "duration_seconds": 45.2,
  "files_created": [
    "data/bsee/binary/production_2024.bin",
    "data/bsee/binary/well_2024.bin"
  ]
}
```

### Status Command

**Endpoint:** `python -m worldenergydata.bsee status`

**Purpose:** Check last refresh status and data availability

**Response:**
```json
{
  "last_refresh": {
    "production": "2024-03-15T14:30:00Z",
    "well": "2024-03-15T14:35:00Z",
    "war": "2024-03-10T09:00:00Z"
  },
  "data_coverage": {
    "production": "2020-01-01 to 2024-03-15",
    "well": "2015-01-01 to 2024-03-15",
    "war": "2018-01-01 to 2024-03-10"
  },
  "storage_used": "1.2 GB",
  "binary_files": 15
}
```

## Future API Integration

### BSEE REST API (Hypothetical)

When/if BSEE provides a REST API, integrate using this structure:

**Base URL:** `https://api.bsee.gov/v1`

**Authentication:** API key in header

**Endpoints:**
- `GET /production` - Production data with pagination
- `GET /wells` - Well information
- `GET /platforms` - Platform data
- `GET /activity-reports` - WAR data

**Rate Limiting:** 
- 1000 requests/hour per API key
- Implement token bucket algorithm

**Response Format:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 100,
    "total": 15234
  },
  "metadata": {
    "last_updated": "2024-03-15T14:30:00Z",
    "version": "1.0"
  }
}
```

## Error Handling

### HTTP Status Codes
- **200:** Success
- **400:** Invalid parameters
- **401:** Authentication required (future)
- **429:** Rate limit exceeded
- **500:** Server error
- **503:** Service unavailable

### Retry Strategy
```python
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(requests.RequestException)
)
def fetch_data(url, params):
    # Implementation
```

### Error Response Format
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please retry after 60 seconds.",
    "retry_after": 60,
    "documentation": "https://docs.worldenergydata.com/errors/rate-limit"
  }
}
```

## Monitoring and Logging

- Log all API/scraping requests with timestamps
- Track response times and success rates
- Monitor data quality metrics
- Alert on repeated failures