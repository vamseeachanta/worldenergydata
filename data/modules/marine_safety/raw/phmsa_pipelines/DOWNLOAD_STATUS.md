# PHMSA Pipeline Data - Download Status Report

**Date:** 2025-10-08
**Status:** ⚠️ MANUAL DOWNLOAD REQUIRED
**Reason:** Website connectivity issues preventing automated downloads

---

## Summary

**PHMSA (Pipeline and Hazardous Materials Safety Administration)** maintains comprehensive pipeline safety data covering:
- Gas Distribution
- Gas Gathering
- Gas Transmission
- Hazardous Liquids (crude oil, petroleum products, chemicals)
- LNG Facilities
- Underground Natural Gas Storage

**Coverage:** 1970-present (varies by dataset)
**Update Frequency:** Incidents (monthly), Annual Reports (yearly)

---

## Download Attempt Results

### Automated Download Status: ❌ FAILED

**Issues Encountered:**
1. **Website Timeout:** PHMSA website (phmsa.dot.gov) consistently timed out
2. **HTTP/2 Stream Errors:** Direct file downloads returned connection errors
3. **Portal Access:** Interactive data portal requires browser session (not scriptable)

**Error Messages:**
```
curl: (92) HTTP/2 stream 1 was not closed cleanly: INTERNAL_ERROR (err 2)
read ECONNRESET
```

---

## Available Data Sources

### 1. PHMSA Interactive Data Portal

**URL:** https://portal.phmsa.dot.gov/analytics

**Datasets Available:**
- Pipeline Incident 20 Year Trend
- All Reported Incidents (comprehensive)
- Annual Report Data
- Operator Information
- State-level summaries

**Access Method:**
- Requires manual browser access
- Custom query builder
- Export to Excel/CSV
- No bulk download API

**Advantages:**
✅ Most up-to-date data
✅ Custom filtering and querying
✅ Data dictionary included
✅ Quality assured

**Disadvantages:**
❌ No automation possible
❌ Manual downloads required
❌ Session timeouts on large queries
❌ Export size limits

---

### 2. PHMSA Source Data Page

**URL:** https://www.phmsa.dot.gov/data-and-statistics/pipeline/source-data

**Expected Files:**
- `gas_distribution_incidents_YYYY.zip`
- `gas_transmission_incidents_YYYY.zip`
- `hazardous_liquids_incidents_YYYY.zip`
- `lng_incidents_YYYY.zip`
- `annual_reports_gas_distribution_YYYY.zip`
- `annual_reports_gas_transmission_YYYY.zip`
- `annual_reports_hazardous_liquids_YYYY.zip`

**Status:** Page accessible but download links timing out

---

### 3. Alternative Sources

#### A. Data.gov Mirror
**URL:** https://catalog.data.gov/dataset?q=PHMSA+pipeline
**Status:** May have outdated snapshots
**Action:** Search for "PHMSA pipeline incidents" and "PHMSA annual reports"

#### B. NPMS (National Pipeline Mapping System)
**URL:** https://www.npms.phmsa.dot.gov
**Data Type:** Geographic pipeline locations, system attributes
**Access:** Interactive map, bulk download requests require account

#### C. Direct Email Request
**Contact:** phmsa.dataaccess@dot.gov
**Request:** "Bulk download of incident and annual report data, all system types, 2010-2024"
**Response Time:** Typically 5-10 business days
**Format:** Usually ZIP files via secure link

---

## Recommended Next Steps

### Option 1: Manual Portal Download (Immediate)

1. Access: https://portal.phmsa.dot.gov/analytics
2. Navigate: Public → Pipeline Incident 20 Year Trend
3. Query Parameters:
   - Date Range: 2010-01-01 to 2024-12-31
   - System Type: All
   - Export Format: CSV
4. Repeat for each system type:
   - Gas Distribution
   - Gas Transmission & Gathering
   - Hazardous Liquids
   - LNG

**Estimated Time:** 2-3 hours
**Data Quality:** ⭐⭐⭐⭐⭐

---

### Option 2: Email Request (3-5 days)

Send email to: phmsa.dataaccess@dot.gov

**Subject:** Bulk Download Request - Pipeline Incident and Annual Report Data

**Body:**
```
Dear PHMSA Data Team,

I am requesting bulk download access to the following datasets for research purposes:

1. Incident Reports (1970-2024):
   - Gas Distribution
   - Gas Transmission
   - Gas Gathering
   - Hazardous Liquids
   - LNG Facilities

2. Annual Reports (2010-2024):
   - Gas Distribution (49 CFR 191)
   - Gas Transmission (49 CFR 191)
   - Hazardous Liquids (49 CFR 195)

Preferred Format: CSV files with data dictionaries
Purpose: Marine safety correlation analysis and statistical research

Thank you for your assistance.
```

**Expected Response:** Secure download link or FTP credentials
**Data Quality:** ⭐⭐⭐⭐⭐

---

### Option 3: Data.gov Mirror (Variable)

1. Search: https://catalog.data.gov/dataset?q=PHMSA
2. Look for:
   - "Pipeline and Hazardous Materials Safety Administration Incident Data"
   - "PHMSA Annual Report Data"
3. Check last updated date
4. Download available files

**Data Quality:** ⭐⭐⭐ (may be outdated)

---

## Expected Data Schema

### Incident Reports (Key Fields)

| Field | Type | Description |
|-------|------|-------------|
| REPORT_NUMBER | String | Unique incident identifier |
| OPERATOR_ID | String | OPID operator code |
| OPERATOR_NAME | String | Company name |
| ACCIDENT_YEAR | Integer | Calendar year |
| ACCIDENT_DATE | Date | MM/DD/YYYY |
| STATE_ABBREVIATION | String | Two-letter state code |
| CITY_NAME | String | Municipality |
| COUNTY_NAME | String | County name |
| LOCATION_LATITUDE | Decimal | Latitude (NAD83) |
| LOCATION_LONGITUDE | Decimal | Longitude (NAD83) |
| SYSTEM_TYPE | String | Distribution, Transmission, Gathering |
| COMMODITY | String | Natural Gas, Crude Oil, HVL, etc. |
| CAUSE_CATEGORY | String | Corrosion, Equipment Failure, External Force, etc. |
| CAUSE_SUBCATEGORY | String | Detailed cause classification |
| TOTAL_COST_CURRENT | Decimal | Property damage ($ current) |
| TOTAL_COST_IN_1984_DOLLARS | Decimal | Inflation-adjusted cost |
| FATAL | Integer | Fatality count |
| INJURE | Integer | Injury count (hospitalized) |
| IGNITE_IND | Boolean | Fire or explosion occurred |
| EXPLODE_IND | Boolean | Explosion occurred |
| LIQUID_RELEASE_BBLS | Decimal | Volume released (hazardous liquids) |
| LIQUID_RECOVERY_BBLS | Decimal | Volume recovered |
| GAS_RELEASED_MCF | Decimal | Gas volume released (thousand cubic feet) |

**Total Fields:** 100+ (varies by system type and report year)

---

### Annual Reports (Key Fields)

| Field | Type | Description |
|-------|------|-------------|
| OPERATOR_ID | String | OPID operator code |
| REPORT_YEAR | Integer | Calendar year |
| STATE | String | State abbreviation |
| TOTAL_MILES | Decimal | Total system miles |
| MILES_STEEL | Decimal | Steel pipe miles |
| MILES_PLASTIC | Decimal | Plastic pipe miles |
| MILES_CAST_IRON | Decimal | Cast iron miles (distribution) |
| MILES_HCA | Decimal | High Consequence Area miles |
| LEAK_DETECTED | Integer | Leaks found |
| LEAK_REPAIRED | Integer | Leaks repaired |
| SERVICES | Integer | Service lines count |
| CUSTOMERS | Integer | Customer count |
| MAOP_AVG | Decimal | Average maximum operating pressure (psig) |

**Total Fields:** 200+ (varies by system type)

---

## Data Coverage Summary

| Dataset | Start Year | End Year | Records | Update Frequency |
|---------|------------|----------|---------|------------------|
| Gas Distribution Incidents | 1970 | 2024 | ~25,000 | Monthly |
| Gas Transmission Incidents | 1970 | 2024 | ~10,000 | Monthly |
| Hazardous Liquids Incidents | 1970 | 2024 | ~15,000 | Monthly |
| LNG Incidents | 1970 | 2024 | ~500 | Monthly |
| Gas Distribution Annual | 2010 | 2023 | ~2,000/year | Annual (Mar 15) |
| Gas Transmission Annual | 2010 | 2023 | ~1,500/year | Annual (Mar 15) |
| Hazardous Liquids Annual | 2010 | 2023 | ~800/year | Annual (Mar 15) |

**Total Estimated Records:** 50,000+ incidents, 60,000+ annual reports

---

## Use Cases for Marine Safety Analysis

### 1. Offshore Platform Connections
- Pipelines connecting to offshore platforms
- Beach approach incidents
- Subsea pipeline failures
- Platform supply incidents

### 2. Marine Terminal Operations
- LNG import/export terminals
- Crude oil loading facilities
- Product terminals on waterfront
- Ship-to-shore incidents

### 3. Cross-Jurisdictional Events
- Incidents affecting both PHMSA (pipeline) and USCG (marine) jurisdictions
- Correlation with vessel casualties
- Environmental impacts shared with NOAA data

### 4. Comparative Safety Analysis
- Pipeline incident rates vs. marine incident rates
- Common causes (corrosion, equipment failure)
- Economic impact comparison
- Regulatory effectiveness

---

## Related Marine Safety Datasets

**Already Downloaded:**
- ✅ BSEE Offshore Incidents (1956-2023) - 25 files, 71 MB
- ✅ USCG MISLE (pending import)
- ✅ NTSB Marine (pending import)
- ✅ NOAA Spills (downloaded)

**Pending:**
- ⏳ PHMSA Pipeline Incidents (this dataset)
- ⏳ PHMSA Hazmat Incidents
- ⏳ EPA NRC Oil Spills
- ⏳ State Pipeline Agencies

---

## Priority & Timeline

**Priority:** MEDIUM-HIGH

**Rationale:**
- Important for comprehensive energy infrastructure safety analysis
- Overlaps with offshore/marine operations
- Needed for correlation studies
- Not immediately critical (can proceed with other datasets first)

**Recommended Timeline:**
1. **Immediate:** Continue with other marine safety downloads
2. **Within 1 week:** Manual portal download or email request
3. **Within 2 weeks:** Import and validate data
4. **Within 1 month:** Integration with marine safety database

---

## Technical Notes

### File Size Expectations
- **Incidents (all types, 1970-2024):** ~200-300 MB (CSV)
- **Annual Reports (2010-2024):** ~500-800 MB (CSV)
- **Total with data dictionaries:** ~1-2 GB

### Processing Requirements
- CSV parsing with mixed data types
- Date standardization (various formats over years)
- Geographic coordinate validation
- Operator name normalization (mergers, acquisitions)
- Cause code mapping (changed over time)

### Database Integration
**Target Tables:**
- `pipeline_incidents` - Core incident records
- `pipeline_operators` - Operator information
- `pipeline_causes` - Standardized cause classifications
- `pipeline_annual_reports` - System characteristics
- `pipeline_geographic` - Location and routing data

---

## Contact Information

**PHMSA Data Access:**
- Email: phmsa.dataaccess@dot.gov
- Phone: 202-366-4595
- Portal Support: https://portal.phmsa.dot.gov/support

**Alternative Contacts:**
- Information Resources Manager: information@phmsa.dot.gov
- Public Affairs: PublicAffairs@dot.gov

---

## Status Log

### 2025-10-08 - Initial Download Attempt
- **Status:** ❌ Failed
- **Reason:** Website connectivity issues
- **Action:** Created comprehensive documentation
- **Next Steps:** Manual download or email request required

---

**Report Created:** 2025-10-08
**Last Updated:** 2025-10-08
**Status:** Awaiting manual intervention
**Prepared by:** Research Agent
