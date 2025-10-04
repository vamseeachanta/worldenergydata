# USCG Marine Casualty Data - Access Methods

**Date:** 2025-10-03
**Status:** Researched

## Overview

The U.S. Coast Guard maintains the **Marine Information for Safety and Law Enforcement (MISLE)** database, which contains marine casualty and pollution incident data.

## Official Data Sources

### 1. USCG Homeport - Bulk Download (PRIMARY)

**URL:** https://homeport.uscg.mil/missions/investigations/marine-casualty-pollution-investigations

**Description:**
- Official bulk download portal for marine casualty and pollution data
- Data collection period: 1982-present for casualties, 1973-present for pollution
- Dataset updated periodically

**Data Files:**
- `MISLE_DATA.zip` - Historical data (2002-2015 confirmed)
- Additional files may be available for recent years

**Access Method:**
- Direct download from Homeport website
- No API key required
- Files are provided in database format (likely Access .mdb or CSV)

### 2. Data.gov Listing

**URL:** https://data.gov/maritime/safety-at-sea-us-coast-guard-marine-casualty-and-pollution-data-for-researchers/

**Description:**
- Federal open data portal listing
- Links to USCG Homeport for actual downloads
- Provides metadata and documentation

### 3. USCG Marine Casualty Reports (Individual Reports)

**URL:** https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/Marine-Casualty-Reports/

**Description:**
- Individual investigation reports published as PDFs
- More detailed than database records
- Requires web scraping (currently blocked - 403 Forbidden)

**Status:** ⚠️ Currently inaccessible via automated scraping (bot protection)

### 4. CGMIX (Coast Guard Maritime Information Exchange)

**URL:** https://cgmix.uscg.mil/psix/psixsearch.aspx

**Description:**
- Port State Information Exchange (PSIX) search
- May require authentication
- Web interface for querying specific incidents

## Recommended Approach

### Phase 1: Bulk Download (Immediate)
1. Download historical data from USCG Homeport
2. Import into our SQLite/PostgreSQL database
3. Provides 1982-2015+ baseline dataset

### Phase 2: Regular Updates
1. Monitor Homeport for new data releases
2. Download and merge incremental updates
3. Establish quarterly update schedule

### Phase 3: Recent Data (Alternative Methods)
For 2024 current data:
- Contact USCG Office of Investigations directly
- Request access to updated MISLE extracts
- Explore FOIA (Freedom of Information Act) requests if needed

### Phase 4: Supplemental Sources
- NTSB Marine Accident Database (complementary data)
- BTS Maritime Statistics
- International sources (IMO, IMCA)

## Data Format Expectations

Based on research:
- **Format:** Likely Microsoft Access (.mdb) or CSV files
- **Structure:** Multiple tables (incidents, vessels, casualties, investigations)
- **Date Range:** 1982-present (casualties), 1973-present (pollution)
- **Update Frequency:** Periodic (not real-time)

## Implementation Plan

### Immediate Next Steps:
1. ✅ Research complete - data source identified
2. ⏳ Access USCG Homeport and download MISLE_DATA.zip
3. ⏳ Analyze file structure and schema
4. ⏳ Create import script for bulk data
5. ⏳ Map USCG fields to our database schema
6. ⏳ Import historical data

### Alternative if Homeport Access Fails:
- File FOIA request with USCG
- Contact: Office of Investigations and Casualty Analysis
- Email/Phone: Available on USCG website

## Technical Notes

### Current Scraper Status:
- ✅ USCG web scraper implemented (production-ready)
- ❌ Currently blocked by USCG website (403 Forbidden)
- ✅ Retry logic and rate limiting functional
- 💡 **Recommendation:** Use bulk download instead of scraping

### Database Compatibility:
- ✅ Our schema ready to accept USCG data
- ✅ SQLite/PostgreSQL dual support
- ✅ Proper relationships (incidents, vessels, companies, locations)

## References

1. USCG Homeport: https://homeport.uscg.mil/
2. Data.gov: https://data.gov/maritime/
3. USCG Investigations: https://www.dco.uscg.mil/.../Office-of-Investigations-Casualty-Analysis/
4. Wikipedia: https://en.wikipedia.org/wiki/Marine_Investigation_(USCG)

---

**Next Action:** Download MISLE_DATA.zip from USCG Homeport and analyze contents.
