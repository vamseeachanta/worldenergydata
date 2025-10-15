# Canadian Transportation Safety Board (TSB) Marine Database

**Status:** ⚠️ MANUAL DOWNLOAD REQUIRED
**Expected Coverage:** 1995-present
**Expected Records:** 30,000+ occurrences

---

## Overview

The Transportation Safety Board of Canada maintains a comprehensive database of marine occurrences (accidents, incidents, and safety issues) investigated in Canadian waters.

## Source Information

- **Provider:** Transportation Safety Board of Canada (TSB)
- **Statistics Portal:** https://www.tsb.gc.ca/eng/stats/marine/index.html
- **Expected Format:** CSV files (6 monthly tables)
- **Update Frequency:** Monthly
- **Language:** English and French versions available

## Download Status

**❌ Automated Download Failed**
- CSV download links not accessible via direct URLs
- Statistics portal requires interactive navigation
- Manual download from portal required

## Data Tables Expected

The TSB marine database consists of 6 linked tables updated monthly:

### 1. Occurrences
- Occurrence ID (primary key)
- Date and time
- Location details
- Occurrence type
- Investigation level
- TSB report number

### 2. Vessels
- Vessel ID
- Name and registration
- Type and size
- Build year
- Flag state
- Links to occurrence

### 3. Consequences
- Fatalities
- Injuries (serious, minor)
- Missing persons
- Environmental damage
- Property damage estimates

### 4. Causes and Contributing Factors
- Primary causes
- Contributing factors
- Safety deficiencies identified
- Coded classification

### 5. Safety Actions
- Recommendations issued
- Deficiency notices
- Follow-up actions
- Status tracking

### 6. Investigation Status
- Open/closed status
- Investigation milestones
- Report publication dates
- Updates and amendments

## Manual Download Instructions

### Step-by-Step Process

1. **Visit TSB Marine Statistics Portal**
   ```
   https://www.tsb.gc.ca/eng/stats/marine/index.html
   ```

2. **Navigate to Data Downloads**
   - Look for "Monthly data" or "Download data" section
   - May be under "Statistical summaries" or "Data tables"

3. **Download Monthly CSV Files**
   - Download all 6 CSV tables
   - Select most recent monthly update
   - Save files to this directory with original names

4. **Verify Download**
   - Check file sizes (should total ~50-100 MB)
   - Verify CSV format and encoding (UTF-8)
   - Count records in each file

### Alternative: Open Data Portal

**Canada Open Data Portal:**
```
https://open.canada.ca/
```

Search terms:
- "TSB marine occurrences"
- "Transportation Safety Board marine"
- "Marine accidents Canada"

### Alternative: Direct Data Request

**Contact TSB:**
- Email: communications@tsb.gc.ca
- Request: "Bulk download of marine occurrence database"
- Specify: CSV format, all tables, date range needed

## Expected Data Volume

Based on TSB documentation:
- **Total Occurrences:** ~30,000 (1995-2025)
- **Annual Rate:** ~1,000-1,200 occurrences/year
- **Vessels:** ~40,000 (many involved in multiple occurrences)
- **Geographic Coverage:** Canadian waters, Great Lakes, inland waterways

## Data Schema Notes

### Occurrence Types
- **Accidents:** Vessels, cargo operations, personnel casualties
- **Incidents:** Near-misses, equipment failures, safety deficiencies
- **Marine Safety Issues:** Systemic concerns, emerging hazards

### Investigation Levels
- **Class 1:** Comprehensive investigation with public report
- **Class 2:** Limited investigation
- **Class 3:** Safety issue investigation
- **Class 4:** Data collection only

### Geographic Classification
- **Region:** Pacific, Central, Quebec, Atlantic, North
- **Waterway Type:** Coastal, inland, Great Lakes, river
- **Jurisdiction:** Federal, provincial, international waters

## Data Quality Considerations

- **Completeness:** Mandatory reporting for commercial vessels; recreational variable
- **Investigation Depth:** Varies by classification level
- **Temporal Coverage:** Complete from 1995; earlier records partial
- **Bilingual Data:** Some fields in both English and French
- **Updates:** Historical records updated as investigations close

## Known Issues

1. **Encoding:** French accents may require UTF-8 encoding
2. **Date Formats:** May use Canadian format (YYYY-MM-DD)
3. **Missing Values:** Earlier records less complete
4. **Classification Changes:** Coding schemes evolved over time
5. **Vessel Identification:** Multiple identifiers (IMO, official number, name)

## Related Datasets

### Canadian Sources
- **Transport Canada Marine Safety:** Vessel inspections, detentions
- **Canadian Coast Guard:** Search and rescue incidents
- **Fisheries and Oceans Canada:** Fishing vessel safety

### International Linkages
- **U.S. Coast Guard:** Cross-border incidents (Great Lakes, shared waters)
- **IMO Global Integrated Shipping Information System (GISIS)**
- **European Marine Casualty Information Platform (EMCIP)**

## Processing Workflow

### When Data Acquired:

1. **File Organization**
   ```
   canadian_tsb/
   ├── occurrences_YYYYMM.csv
   ├── vessels_YYYYMM.csv
   ├── consequences_YYYYMM.csv
   ├── causes_YYYYMM.csv
   ├── safety_actions_YYYYMM.csv
   ├── investigation_status_YYYYMM.csv
   └── README.md (this file)
   ```

2. **Data Validation**
   - Verify record counts against TSB website statistics
   - Check table relationships (foreign keys)
   - Validate date ranges (1995-present expected)

3. **Schema Documentation**
   - Create data dictionary for each table
   - Document field codes and classifications
   - Map relationships between tables

4. **Quality Checks**
   - Check for duplicates (by occurrence ID)
   - Validate geographic coordinates
   - Ensure referential integrity across tables

## Sample Queries

### High-Priority Analysis Questions

1. **Trend Analysis:** Marine accident rates by year and region
2. **Vessel Types:** Most common vessel types involved
3. **Causes:** Leading causes and contributing factors
4. **Severity:** Fatality and injury trends
5. **Geography:** High-risk waterways and locations
6. **Seasonal:** Patterns by season and weather conditions

## Citation

```
Transportation Safety Board of Canada. (2025). Marine Occurrence Database.
Retrieved October 5, 2025, from https://www.tsb.gc.ca/eng/stats/marine/
```

## Contact

**Transportation Safety Board of Canada:**
- Email: communications@tsb.gc.ca
- Phone: 1-800-387-3557 (toll-free in Canada)
- Address: 200 Promenade du Portage, Gatineau QC K1A 1K8

---

## Status Updates

### 2025-10-05
- **Status:** Automated download failed
- **Issue:** CSV links not found via direct URLs
- **Action Required:** Manual download from TSB portal
- **Priority:** HIGH - Tier 1 data source

### Next Steps
1. Visit TSB statistics portal manually
2. Locate and download 6 monthly CSV tables
3. Verify data completeness
4. Document final schema and update this README

---

**README Generated:** 2025-10-05
**Data Steward:** Research Agent
