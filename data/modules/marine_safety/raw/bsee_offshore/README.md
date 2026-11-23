# BSEE Offshore Incident Statistics

**Status:** ✅ SUCCESSFULLY DOWNLOADED
**Coverage:** 1956-2023 (67 years)
**Format:** Excel (2007-2023) + PDF Historical (1956-2000)
**Downloaded:** 2025-10-08

---

## Source Information

- **Provider:** Bureau of Safety and Environmental Enforcement (BSEE)
- **Statistics Page:** https://www.bsee.gov/stats-facts/offshore-incident-statistics
- **Data Format:** Excel spreadsheets and PDF reports

## Download Status

**✅ Successfully Downloaded**
- **17 Excel files** covering 2007-2023 (Calendar Years 2018-2023, Fiscal Years 2007-2017)
- **8 PDF historical reports** covering 1956-2000
- **Total coverage:** 67 years of offshore incident data (1956-2023)

## Directory Structure

```
bsee_offshore/
├── excel/                    # Excel spreadsheets (2007-2023) - 17 files, 36MB
│   ├── cy-2023-excel-spreadsheet.xlsx
│   ├── cy-2022-excel-spreadsheet.xlsx
│   ├── cy-2021-excel-spreadsheet.xlsx (35MB - detailed records)
│   ├── cy-2020-excel-spreadsheet.xlsx
│   ├── cy-2019-excel-spreadsheet.xlsx (326KB)
│   ├── cy-2018-excel-spreadsheet.xlsx
│   ├── fy-2017-excel-spreadsheet.xlsx
│   ├── fy-2016-excel-spreadsheet.xlsx
│   ├── fy-2015-excel-spreadsheet.xlsx
│   ├── fy-2014-excel-spreadsheet.xlsx
│   ├── fy-2013-excel-spreadsheet.xlsx
│   ├── fy-2012-excel-spreadsheet.xlsx
│   ├── fy-2011-excel-spreadsheet.xlsx
│   ├── fy-2010-excel-spreadsheet.xlsx
│   ├── fy-2009-excel-spreadsheet.xlsx
│   ├── fy-2008-excel-spreadsheet.xlsx
│   └── fy-2007-excel-spreadsheet.xlsx
├── pdf/                      # PDF historical reports (1956-2000) - 8 files, 35MB
│   ├── incidents_1956-1990.pdf (5.8MB - 34 years)
│   ├── incidents_1991-1994.pdf (417KB)
│   ├── addendum_1991-1994.pdf (32KB - fatality details)
│   ├── incidents_1995-1996.pdf (24MB - comprehensive)
│   ├── finalocs97.pdf (2.0MB)
│   ├── finalocs98.pdf (763KB)
│   ├── finalocs99.pdf (972KB)
│   └── accidentreport2000.pdf (1.5MB)
└── README.md                 # This file
```

## Incident Categories Tracked

All downloaded files track multiple incident categories:

#### A. Well Control Incidents
- Blowouts, well control events
- Loss of well control
- H2S releases

#### B. Injuries and Fatalities
- Employee injuries
- Contractor injuries
- Fatalities
- Lost time incidents

#### C. Fire and Explosions
- Platform fires
- Explosions
- Flammable gas releases

#### D. Structural Failures
- Platform damage
- Equipment failures
- Crane accidents

#### E. Spills and Pollution
- Oil spills (≥ 1 BBL)
- Chemical releases
- Environmental incidents

#### F. Diving and Marine Operations
- Diving accidents
- Marine vessel incidents
- Personnel transfers

#### G. Other Categories
- Lifting incidents
- Musters (emergency assemblies)
- Gas releases
- Collisions

**Note:** Individual incidents may be counted in multiple categories

## Expected Data Schema

### Common Fields Across Incident Types:
- **Incident Date/Time:** When incident occurred
- **Report Date:** When incident reported to BSEE
- **Operator:** Company operating the facility
- **Facility:** Platform or vessel name
- **Location:**
  - Region (Gulf of Mexico, Pacific, Alaska)
  - Area, Block, Lease number
  - Lat/lon coordinates
  - Water depth
- **Incident Type:** Classification code
- **Severity:** Minor, major, catastrophic
- **Description:** Narrative description
- **Injuries/Fatalities:** Count and severity
- **Property Damage:** Estimated cost
- **Production Impact:** Barrels lost, downtime
- **Pollution:** Volume and type of release
- **Investigation:** Status, findings, enforcement actions
- **Root Cause:** Primary and contributing causes

### Specific Fields by Category:

**Well Control:**
- Well depth, pressure
- Control event type
- Volume released
- Control method used

**Injuries:**
- Body part injured
- Nature of injury
- Activity being performed
- Safety equipment usage

**Fires/Explosions:**
- Ignition source
- Material ignited
- Suppression method
- Damage extent

**Spills:**
- Volume (barrels)
- Material type (oil, condensate, chemicals)
- Cause of spill
- Recovery amount
- Environmental impact

## Data Quality Notes

- **Completeness:** Mandatory reporting to BSEE; high compliance
- **Timeliness:** Reports due within 24 hours; database updated regularly
- **Accuracy:** Verified through BSEE investigations
- **Coverage:** All OCS (Outer Continental Shelf) operations
- **Resolution:** Incident-level detail with investigation findings

## Historical Context

- **Pre-2010:** BSEE was part of MMS (Minerals Management Service)
- **2011:** BSEE created after Deepwater Horizon disaster
- **Data Continuity:** Historical MMS data integrated into BSEE systems
- **Regulatory Changes:** Reporting requirements enhanced post-2010

## Known Issues

1. **Multiple Databases:** BSEE maintains separate systems for different incident types
2. **Classification Changes:** Incident coding evolved over time
3. **Merger Artifacts:** MMS to BSEE transition may show data inconsistencies
4. **Operator Changes:** Facility ownership changes complicate trend analysis
5. **Hurricane Impacts:** Gulf of Mexico data shows seasonal variability

## Related Datasets

- **USCG Marine Casualties:** Vessel incidents in offshore areas
- **NOAA Oil Spills:** Overlaps with BSEE spill reporting
- **OSHA:** Occupational injuries on offshore facilities
- **EPA:** Environmental compliance and violations
- **State Agencies:** State waters incidents (Louisiana, Texas, California)

## High-Value Analysis Opportunities

1. **Trend Analysis:** Incident rates by year, region, operator
2. **Cause Analysis:** Root cause patterns across incident types
3. **Severity Modeling:** Factors predicting major casualties
4. **Operator Performance:** Comparative safety records
5. **Regional Differences:** Gulf vs. Pacific vs. Alaska patterns
6. **Weather/Environmental:** Seasonal and weather-related risks
7. **Technology Impact:** Safety improvements from new technologies
8. **Regulatory Effectiveness:** Impact of post-Deepwater Horizon rules

## Citation

```
Bureau of Safety and Environmental Enforcement. (2007-2023).
Offshore Incident Statistics - Excel Spreadsheets [Data files].
Retrieved October 8, 2025, from https://www.bsee.gov/stats-facts/offshore-incident-statistics

Bureau of Safety and Environmental Enforcement. (1956-2000).
Historical Offshore Incident Reports [PDF reports].
Retrieved October 8, 2025, from https://www.bsee.gov/stats-facts/offshore-incident-statistics
```

## Contact

**BSEE:**
- Data Center Support: See website for current contact
- FOIA Office: BSEE.FOIA@bsee.gov
- Phone: 703-787-1300

**Regional Offices:**
- Gulf of Mexico: New Orleans
- Pacific: Camarillo, California
- Alaska: Anchorage

---

## Status Updates

### 2025-10-08 - ✅ DOWNLOAD COMPLETE
- **Status:** Successfully downloaded all available files
- **Source:** BSEE Statistics Page (https://www.bsee.gov/stats-facts/offshore-incident-statistics)
- **Files Downloaded:** 25 total (17 Excel + 8 PDF)
- **Coverage:** 67 years (1956-2023)
- **Total Size:** 71 MB

### Download Details
- **Excel Files:** Direct downloads from BSEE statistics page
- **PDF Reports:** Historical incident summaries and annual reports
- **Data Gap:** 2001-2006 not available on statistics page
- **Documentation:** See DOWNLOAD_SUMMARY.md for complete details

### Next Steps
1. ✅ Download complete
2. ⏳ Parse Excel files into database format
3. ⏳ Extract data from PDF reports (OCR if needed)
4. ⏳ Import to marine_safety_incidents table
5. ⏳ Validate data completeness and quality
6. ⏳ Create analysis reports and visualizations

---

**README Updated:** 2025-10-08
**Download Status:** ✅ COMPLETE
**Data Steward:** Research Agent
