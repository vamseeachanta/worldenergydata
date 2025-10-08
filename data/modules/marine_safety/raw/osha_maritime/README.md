# OSHA Maritime Worker Safety Data

**Downloaded:** 2025-10-06
**Source:** U.S. Department of Labor - OSHA & State Agencies

## Files

### oregon_osha_inspections.csv (2.1 KB)
- **Source:** https://data.oregon.gov/api/views/xc4e-hg3n/rows.csv
- **Coverage:** Oregon OSHA consultations, inspections, citations, violations (1988-2024)
- **Records:** 37 years of annual summary data
- **Status:** ✅ Downloaded successfully
- **Fields:**
  - Year
  - Consultations opened
  - Employees affected
  - SHARP/VPP participation
  - Inspections conducted
  - Workers covered
  - Compliance percentage
  - Citations issued
  - Violations found
  - Penalties ($ millions)

### OSHA_Maritime_Inspections.json (4.2 KB)
- **Source:** https://enforcedata.dol.gov/views/data_summary.php
- **Status:** ⚠️ Contains HTML portal page, not raw data
- **Note:** Requires database query access

### osha_severe_injury_reports.xlsx (473 bytes)
- **Source:** https://www.osha.gov/sites/default/files/Establishment_Specific_Injury_and_Illness_Data.xlsx
- **Status:** ⚠️ File too small, likely error/redirect page

### osha_fatalities.html (0 bytes)
- **Source:** https://www.osha.gov/fatalities
- **Status:** ❌ Download failed (403 Forbidden)
- **Issue:** OSHA website access restricted during government operations suspension

## Data Quality Notes

- ✅ **Oregon State Data:** Complete and usable
- ⚠️ **Federal OSHA Data:** Direct downloads blocked
- 📊 **Oregon Coverage:** State-level only, not national
- 🚧 **Access Issues:** Federal OSHA website experiencing access restrictions

## Alternative Data Sources

Since direct OSHA downloads failed, consider these alternatives:

1. **BLS SOII Database**
   - URL: https://www.bls.gov/iif/soii-data.htm
   - Contains national occupational injury/illness statistics
   - Filter by NAICS codes: 336611 (shipbuilding), 483000 (water transport)

2. **State OSHA Portals**
   - Oregon (downloaded)
   - California, Washington, New York have independent OSHA programs
   - More accessible than federal portal

3. **NIOSH CFID**
   - Already have in `/niosh_cfid/`
   - Commercial fishing fatalities (maritime worker deaths)

4. **NTSB Marine Investigations**
   - Already have in `/ntsb_marine/`
   - Includes worker fatality investigations

## Maritime NAICS Codes to Filter

When accessing OSHA data, filter by these codes:
- **336611:** Ship Building and Repairing
- **483000:** Water Transportation
- **488300:** Support Activities for Water Transportation
- **237990:** Other Heavy Construction (includes marine terminals)

## Next Steps

1. Use Oregon data as pilot for state-level OSHA analysis
2. Attempt BLS SOII database query for national maritime injury statistics
3. Check other state OSHA portals (CA, WA, NY)
4. Cross-reference with NIOSH commercial fishing fatality data
5. Monitor OSHA website for restored access to federal fatality database

## Expected Coverage (When Accessible)

- **OSHA Fatality Database:** ~1,000+ maritime worker deaths (2015-present)
- **SOII Data:** Annual injury/illness rates by industry
- **Focus:** Shipyard workers, port workers, vessel crew (non-fishing)
