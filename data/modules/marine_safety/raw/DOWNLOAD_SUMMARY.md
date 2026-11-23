# Marine Safety Data Download Summary

**Download Date:** October 5, 2025
**Operator:** Data Acquisition Agent
**Target:** Tier 1 and Tier 2 marine safety datasets

---

## ✅ SUCCESSFULLY DOWNLOADED DATASETS

### 1. NOAA Oil Spill Database (Tier 1)
**Status:** ✅ COMPLETE
**Location:** `/noaa_spills/incidents.csv`
**File Size:** 3.0 MB
**Record Count:** 4,797 incidents
**Coverage:** 1957-present (updated September 2025)
**Source URL:** https://incidentnews.noaa.gov/raw/incidents.csv
**Description:** Comprehensive database of oil and chemical spill incidents in U.S. waters, maintained by NOAA Office of Response and Restoration.

**Fields Include:**
- Incident ID, date, name, location
- Lat/lon coordinates
- Threat level, commodity type
- Response measures (skim, shore cleanup, dispersants, burning)
- Maximum potential release volumes
- Detailed descriptions

---

### 2. USCG Historical Data (1995-2012) - Already Downloaded
**Status:** ✅ AVAILABLE
**Location:** `/dlp_historical/`
**Total Records:** 264,196 records across 4 files
**Coverage:** 1995-2012
**Source:** Data Liberation Project / USCG

**Files:**
- `Accidents_1995-2012.csv` - 93,237 records (32 MB)
- `Vessels_1995-2012.csv` - 110,493 records (28 MB)
- `Injuries_1995-2012.csv` - 50,790 records (4.7 MB)
- `Deaths_1995-2012.csv` - 9,676 records (680 KB)

**Description:** Historical U.S. Coast Guard marine casualty and pollution data from MISLE database covering commercial vessel incidents, recreational boating accidents, and associated casualties.

---

## ⚠️ PARTIAL / BLOCKED DOWNLOADS

### 3. USCG MISLE Database (2002-2015) (Tier 1)
**Status:** ⚠️ BLOCKED - Access Denied
**Target:** `uscg_misle/`
**Expected:** 100,000+ records
**Issue:** USCG website blocking automated access (403 Forbidden)
**URL Attempted:** https://www.dco.uscg.mil/Our-Organization/...

**Alternative Approaches:**
1. **Manual Download:** Visit URL in browser, request data via form
2. **FOIA Request:** Submit Freedom of Information Act request to USCG
3. **Historical Data:** We already have 1995-2012 coverage in `/dlp_historical/`
4. **Alternative Source:** Check data.gov or NOAA for USCG data exports

**Recommendation:** The historical data we have (1995-2012) provides substantial coverage. For 2013-2015, consider manual download or FOIA request.

---

### 4. Canadian TSB Marine Database (Tier 1)
**Status:** ⚠️ DOWNLOAD LINKS NOT FOUND
**Target:** `canadian_tsb/`
**Expected:** 30,000+ occurrences (1995-present)
**Issue:** CSV download links not accessible via automated methods
**URL:** https://www.tsb.gc.ca/eng/stats/marine/index.html

**Files Attempted:**
- Monthly CSV tables (6 tables documented in research)
- Occurrences, vessels, consequences tables

**Alternative Approaches:**
1. **Manual Download:** Visit TSB statistics portal directly
2. **Data Request:** Contact TSB for bulk data export
3. **Open Data Portal:** Check Canada's Open Data portal: https://open.canada.ca/
4. **Quarterly Reports:** TSB publishes quarterly statistical reports with data

**Recommendation:** Visit TSB statistics page manually to locate actual CSV download links or use Canada's Open Data portal.

---

### 5. UK MAIB Database (Tier 1)
**Status:** ⚠️ DOWNLOAD LINKS NOT FOUND
**Target:** `uk_maib/`
**Expected:** 5,000+ UK investigations
**Issue:** Data.gov.uk page doesn't expose direct CSV downloads
**URL:** https://www.data.gov.uk/dataset/86352ec7-9dba-404d-b8ec-33ad10b87f1b/

**Alternative Approaches:**
1. **MAIB Portal:** Try https://maps.dft.gov.uk/maib-data-portal/
2. **API Access:** Check if data.gov.uk provides API access
3. **Manual Export:** Use MAIB web portal query tool
4. **Annual Reports:** MAIB publishes annual data summaries

**Recommendation:** Access MAIB data portal directly to export database queries.

---

## ❌ FAILED DOWNLOADS (Require Manual Intervention)

### 6. NIOSH Commercial Fishing Incident Database (Tier 2)
**Status:** ❌ FAILED - Repository Not Found
**Target:** `niosh_cfid/`
**Expected:** 3,559 person-level records (2000-2022)
**Issue:** GitHub repository URLs incorrect or moved
**Attempted URLs:**
- data.world (requires login)
- GitHub data-liberation-project repositories (404 errors)

**Alternative Approaches:**
1. **NIOSH Direct:** https://www.cdc.gov/niosh/topics/fishing/default.html
2. **CDC Wonder:** Check CDC data portal
3. **Data Liberation Project:** Contact project directly for current URLs
4. **Research Journals:** May be published in academic datasets

**Recommendation:** Contact Data Liberation Project directly or access NIOSH website.

---

### 7. NTSB CAROL Marine Database (Tier 2)
**Status:** ❌ FAILED - API Endpoint Not Found
**Target:** `ntsb_marine/`
**Expected:** 1,000+ major investigations (2010-present)
**Issue:** API endpoints return 404 errors
**Attempted URLs:**
- https://data.ntsb.gov/carol-main-public/api/Query
- https://data.ntsb.gov/carol-repgen/api/...

**Alternative Approaches:**
1. **CAROL Web Interface:** https://data.ntsb.gov/carol-main-public/query-builder
2. **Developer Portal:** Register at https://developer.ntsb.gov/
3. **Download Center:** Check https://www.ntsb.gov/safety/data/Pages/Data_Stats.aspx
4. **Manual Query:** Use web interface to query marine mode, export to CSV

**Recommendation:** Use NTSB CAROL web query builder to manually construct and export marine investigations.

---

### 8. BSEE Offshore Incidents (Tier 2)
**Status:** ❌ FAILED - Data Portal Access Issues
**Target:** `bsee_offshore/`
**Expected:** 50,000+ offshore incidents
**Issue:** Data portal API endpoints return 404 or HTML error pages
**URL:** https://www.data.bsee.gov/

**Alternative Approaches:**
1. **BSEE Stats Page:** https://www.bsee.gov/stats-facts/offshore-incident-statistics
2. **Query Tool:** Access online query and export functionality
3. **Annual Reports:** BSEE publishes annual statistical summaries
4. **Data.gov:** Search for BSEE datasets on federal data portal

**Recommendation:** Use BSEE's online query tool to export incident data by year and incident type.

---

## 📊 ACQUISITION SUMMARY

### Overall Statistics
- **Total Datasets Targeted:** 7 (Tier 1: 4, Tier 2: 4)
- **Successfully Downloaded:** 2 datasets
- **Already Available (Historical):** 1 dataset (4 files)
- **Partial/Blocked:** 3 datasets
- **Failed:** 3 datasets

### Data Successfully Acquired
- **Total File Count:** 6 files
- **Total Size:** ~68 MB
- **Total Records:** ~268,993 records
  - NOAA: 4,797 incidents
  - USCG Historical: 264,196 records

### Coverage Achieved
- ✅ **Oil Spills:** 1957-2025 (NOAA)
- ✅ **U.S. Casualties:** 1995-2012 (USCG Historical)
- ⚠️ **U.S. Casualties:** 2013-present (requires manual download)
- ⚠️ **Canadian Data:** 1995-present (requires manual download)
- ⚠️ **UK Data:** Available but requires manual download
- ❌ **Fishing Incidents:** 2000-2022 (requires alternative source)
- ❌ **NTSB Investigations:** 2010-present (requires web query)
- ❌ **Offshore Incidents:** Full range (requires query tool)

---

## 🔧 NEXT STEPS

### Immediate Actions Required

1. **Manual Downloads (High Priority):**
   - Canadian TSB: Visit statistics portal, download 6 monthly CSV tables
   - UK MAIB: Access data portal, export database tables
   - USCG MISLE 2013-2015: Request via USCG website form

2. **Alternative Data Sources (Medium Priority):**
   - NIOSH CFID: Contact Data Liberation Project or CDC directly
   - NTSB: Use CAROL web query builder, export marine investigations
   - BSEE: Use online query tool to export incident data

3. **Data Validation:**
   - Verify NOAA incidents.csv data quality
   - Check USCG historical data completeness
   - Document data schemas for each source

4. **Import Pipeline:**
   - Create data import scripts for acquired datasets
   - Design unified schema for marine safety incidents
   - Implement data quality checks and validation

5. **Documentation:**
   - Create individual README files for each data source
   - Document data dictionaries and field definitions
   - Track data lineage and update frequencies

---

## 📝 NOTES

### Access Restrictions Encountered
- Government websites increasingly block automated downloads
- Many require interactive web forms or user authentication
- Some datasets moved to new platforms (e.g., data.gov)
- API documentation often outdated or endpoints changed

### Lessons Learned
1. **Manual intervention often required** for government data portals
2. **Historical data readily available** through Data Liberation Project
3. **NOAA provides excellent bulk download access** (model for others)
4. **GitHub/data.world require authentication** for some datasets
5. **API endpoints frequently change** without documentation updates

### Recommendations for Future Downloads
1. Start with manual browser access to identify actual download mechanisms
2. Check data.gov and open data portals before scraping agency sites
3. Register for API access where available (NTSB Developer Portal)
4. Contact data stewards directly for bulk data requests
5. Consider FOIA requests for blocked government datasets
6. Use selenium/browser automation for JavaScript-heavy portals

---

## 📂 DIRECTORY STRUCTURE

```
/mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/
├── DOWNLOAD_SUMMARY.md (this file)
├── download_datasets.py (Python acquisition script)
│
├── noaa_spills/ ✅
│   ├── incidents.csv (4,797 records, 3.0 MB)
│   └── README.md
│
├── dlp_historical/ ✅ (USCG 1995-2012)
│   ├── Accidents_1995-2012.csv (93,237 records, 32 MB)
│   ├── Vessels_1995-2012.csv (110,493 records, 28 MB)
│   ├── Injuries_1995-2012.csv (50,790 records, 4.7 MB)
│   ├── Deaths_1995-2012.csv (9,676 records, 680 KB)
│   └── README.md
│
├── uscg_misle/ ⚠️ (Blocked - requires manual download)
│   └── README.md
│
├── canadian_tsb/ ⚠️ (Requires manual download)
│   └── README.md
│
├── uk_maib/ ⚠️ (Requires manual download)
│   └── README.md
│
├── niosh_cfid/ ❌ (Alternative source needed)
│   └── README.md
│
├── ntsb_marine/ ❌ (Use web query builder)
│   └── README.md
│
└── bsee_offshore/ ❌ (Use online query tool)
    └── README.md
```

---

**End of Download Summary**
**Generated:** 2025-10-05 15:45 UTC
**Agent:** Data Acquisition Agent (Research Specialist)
