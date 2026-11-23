# PHMSA Hazardous Materials Incident Data

**Downloaded:** 2025-10-06
**Source:** Pipeline and Hazardous Materials Safety Administration (PHMSA)
**Website:** https://www.phmsa.dot.gov/

## Files

### phmsa_hazmat_main.html (0 bytes)
- **Source:** https://www.phmsa.dot.gov/data-and-statistics/hazmat
- **Status:** ⚠️ Download timeout (empty file)

### hazmat_incidents_10_years.csv (1.2 KB)
- **Source:** https://portal.phmsa.dot.gov/analytics/saw.dll?Download
- **Status:** ⚠️ Oracle Analytics login page, not actual data
- **Issue:** Requires portal authentication

## Data Access Methods

### PHMSA Hazmat Portal
- **URL:** https://portal.phmsa.dot.gov/analytics/saw.dll?Dashboard
- **Access:** Free but requires browser-based query
- **Content:** Hazardous materials incident database (1990-present)

### Data Coverage

**PHMSA Hazmat Database includes:**

1. **Transportation Modes:**
   - **Rail**
   - **Highway**
   - **Water** ⬅️ Our focus for maritime incidents
   - **Air**
   - **Pipeline** (separate database)

2. **Incident Types:**
   - Releases/spills during transport
   - Package failures
   - Transportation accidents
   - Loading/unloading incidents

3. **Maritime-Specific:**
   - Cargo vessel hazmat releases
   - Barge incidents
   - Port/terminal loading operations
   - Marine pipeline connections

### Required Query Parameters

To get maritime-focused data from PHMSA portal:

**Filter by:**
- **Transportation Mode:** Water, Marine
- **Incident Type:** All
- **Date Range:** 2000-2024
- **Hazard Class:** All (or specific: flammable liquids, corrosives, explosives)

## Data Quality Notes

- ❌ **Direct Download:** Failed (requires portal access)
- 🔐 **Portal Access:** Free but interactive query required
- 📊 **Maritime Coverage:** Subset of larger hazmat database
- ⏳ **Manual Process:** Cannot be automated

## Expected Coverage (When Accessed)

**Maritime Hazmat Incidents:**
- **Time Period:** 1990-present (35 years)
- **Estimated Records:** 1,000-3,000 water transport incidents
- **Incident Types:**
  - Vessel cargo releases
  - Barge spills
  - Port/terminal incidents
  - Marine loading operations

**Data Fields:**
- Report number and date
- Transportation mode
- Incident location (state, city, waterway)
- Hazardous material details (UN number, hazard class, quantity)
- Incident type (spill, fire, explosion)
- Injuries/fatalities
- Property damage
- Environmental impact

## Alternative Data Sources

Since direct download failed, consider:

1. **NOAA INC Database (Already Have):**
   - `/noaa_spills/incidents.csv` (3 MB, 700,000+ records)
   - Includes hazmat spills in marine environments
   - Overlaps with PHMSA water transport incidents

2. **USCG National Response Center:**
   - Marine pollution/hazmat incident reports
   - Overlap with PHMSA maritime data
   - Already captured in NOAA INC database

3. **DOT Hazmat Portal Query:**
   - Manual download from PHMSA portal
   - Export to Excel/CSV
   - Filter for water transportation mode

4. **MISLE Database (Already Have):**
   - `/uscg_misle/` directory
   - Includes vessel incidents involving dangerous cargo
   - Complements PHMSA hazmat data

## Next Steps

### Manual Portal Access

1. **Visit PHMSA Portal:**
   - URL: https://portal.phmsa.dot.gov/
   - Navigate to Incident Reports Search
   - Apply filters for water transportation mode

2. **Query Parameters:**
   ```
   Incident Date: 01/01/2000 to 12/31/2024
   Mode of Transportation: Water, Marine
   Include: All hazard classes
   Include: All incident types
   Include: Fatalities/injuries
   ```

3. **Export Data:**
   - Download to Excel/CSV
   - Save to this directory as `phmsa_hazmat_water_incidents.xlsx`

4. **Expected Output:**
   - 1,000-3,000 records
   - 30-40 data fields per record
   - File size: ~2-5 MB

### Data Integration

Once downloaded:
- Cross-reference with NOAA INC spill data
- Identify unique PHMSA incidents not in NOAA database
- Merge datasets on date/location/commodity
- Supplement with USCG MISLE dangerous cargo incidents

## Maritime Hazmat Commodities to Track

Key hazardous materials in maritime transport:

- **Class 3:** Flammable liquids (crude oil, gasoline, chemicals)
- **Class 2:** Gases (LNG, LPG, ammonia)
- **Class 8:** Corrosives (sulfuric acid, caustic soda)
- **Class 6:** Toxic substances (pesticides, industrial chemicals)
- **Class 9:** Miscellaneous dangerous goods

## Related Datasets

- See `/noaa_spills/` for marine pollution incidents (already have)
- See `/uscg_misle/` for vessel dangerous cargo casualties
- See `/bsee_offshore/` for offshore platform chemical releases
- See `/doe_pipelines/` for offshore pipeline incidents

## PHMSA Database Relationships

```
PHMSA Data Systems:
├── Pipeline Incidents (see /doe_pipelines/)
│   └── Offshore pipelines
├── Hazmat Incidents (this directory)
│   ├── Rail transport
│   ├── Highway transport
│   ├── Water transport ⬅️ Maritime focus
│   └── Air transport
└── Carrier Safety (not applicable)
```

## Contact for Bulk Data

If portal access is problematic:

**PHMSA Data Support:**
- Email: PHMSAHazmatInformationCenter@dot.gov
- Phone: 1-800-467-4922
- Request: Bulk download of water transportation hazmat incidents (2000-2024)
