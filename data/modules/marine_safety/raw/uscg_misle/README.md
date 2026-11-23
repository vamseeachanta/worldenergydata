# USCG MISLE Database (2002-2015)

**Status:** ⚠️ BLOCKED - Manual Download Required
**Expected Coverage:** 2002-2015
**Expected Records:** 100,000+

---

## Overview

The U.S. Coast Guard Marine Information for Safety and Law Enforcement (MISLE) database contains comprehensive marine casualty and pollution data for commercial vessels operating in U.S. waters.

## Source Information

- **Provider:** U.S. Coast Guard Office of Investigations and Casualty Analysis
- **URL:** https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/Marine-Casualty-and-Pollution-Data-for-Researchers/
- **Expected File:** MISLE_DATA.zip (or similar)
- **Format:** Database files or CSV exports
- **Coverage:** 2002-2015 (approximately)

## Download Status

**❌ Automated Download Failed**
- HTTP 403 Forbidden error when attempting automated download
- USCG website blocks bot/script access
- Requires manual browser-based download or data request

## Alternative Data Sources

### ✅ Historical Data Available (1995-2012)
We have comprehensive USCG data for 1995-2012 in the adjacent directory:
- **Location:** `/dlp_historical/`
- **Records:** 264,196 across 4 files
- **Source:** Data Liberation Project extraction
- **Files:**
  - Accidents_1995-2012.csv (93,237 records)
  - Vessels_1995-2012.csv (110,493 records)
  - Injuries_1995-2012.csv (50,790 records)
  - Deaths_1995-2012.csv (9,676 records)

### Gap Analysis
- **Covered:** 1995-2012 ✅
- **Gap:** 2013-2015 ⚠️ (requires manual download)
- **Recent:** 2016+ (check for updated releases)

## Manual Download Instructions

### Option 1: Direct Website Request

1. Visit USCG data page in browser:
   ```
   https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/Marine-Casualty-and-Pollution-Data-for-Researchers/
   ```

2. Look for data request form or download link
3. Complete any required researcher information forms
4. Download MISLE_DATA.zip or equivalent file
5. Extract to this directory

### Option 2: FOIA Request

If website access restricted, submit Freedom of Information Act request:

**Contact:**
- U.S. Coast Guard FOIA Office
- Email: cgfoia@uscg.mil
- Request: "MISLE database records for marine casualties 2013-2015"

**Estimated Response Time:** 20-60 days

### Option 3: Data.gov Portal

Check federal open data portal for USCG datasets:
- https://catalog.data.gov/dataset?q=coast+guard+marine+casualty
- https://catalog.data.gov/dataset?q=MISLE

## Expected Data Schema

Based on historical USCG data (1995-2012), expect tables for:

### Accidents Table
- Accident ID, date, time
- Location (lat/lon, waterway)
- Vessel information
- Accident type and cause
- Weather conditions
- Damage estimates

### Vessels Table
- Vessel ID
- Name, registration, call sign
- Type, length, tonnage
- Build year, material
- Propulsion type
- Owner/operator information

### Casualties Table (Injuries/Deaths)
- Casualty ID
- Person demographics
- Injury/death classification
- Cause of casualty
- Activity at time of incident
- Protective equipment usage

## Data Quality Considerations

- **Reporting Completeness:** Commercial vessels required to report; recreational often voluntary
- **Investigation Depth:** Varies by severity and vessel type
- **Geographic Coverage:** U.S. waters and EEZ
- **Temporal Lag:** Investigations can take months; data may lag incident dates
- **Coding Standards:** USCG classification codes evolved over time

## Known Relationships

MISLE data connects to:
- **NOAA Oil Spills:** Pollution incidents cross-reference
- **NTSB:** Major casualties investigated by both agencies
- **State Authorities:** Some incidents jointly investigated
- **Insurance Records:** Lloyd's, insurance claims data

## Processing Notes

### When Data Acquired:

1. **Validate File Format**
   - Check if ZIP contains database files or CSVs
   - Document schema and relationships

2. **Extract and Organize**
   - Unzip to this directory
   - Maintain original file names
   - Document extraction date

3. **Data Quality Checks**
   - Record counts by year
   - Check for duplicates
   - Validate date ranges
   - Identify missing values

4. **Schema Documentation**
   - Create data dictionary
   - Map field codes to descriptions
   - Document relationships between tables

## Citation

```
U.S. Coast Guard Office of Investigations and Casualty Analysis. (Year).
Marine Information for Safety and Law Enforcement (MISLE) Database.
Retrieved from [URL] on [Download Date].
```

## Contact

**U.S. Coast Guard:**
- Office of Investigations and Casualty Analysis
- Phone: Check USCG website for current contact
- FOIA: cgfoia@uscg.mil

**Alternative Contact:**
- Data Liberation Project: May have updated extracts
- Email: data-liberation-project@proton.me

---

## Status Updates

### 2025-10-05
- **Status:** Download blocked (403 Forbidden)
- **Action:** Manual download required
- **Alternative:** Historical data 1995-2012 available in `/dlp_historical/`

---

**README Generated:** 2025-10-05
**Data Steward:** Research Agent
