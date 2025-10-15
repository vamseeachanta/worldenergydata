# PHMSA Pipeline Safety Flagged Incidents

**Downloaded:** 2025-10-08
**Source:** Pipeline and Hazardous Materials Safety Administration (PHMSA)
**Data Type:** Pipeline Safety Incident Reports (1986-Present)
**Total Size:** 24 MB (compressed)

---

## Overview

This archive contains **pipeline safety incident data**, NOT water transport hazmat incidents. This is flagged incident data from PHMSA's pipeline safety programs covering:

- Gas Distribution (GD)
- Gas Transmission/Gathering (GTGG)
- Hazardous Liquid (HL)
- Liquefied Natural Gas (LNG)

**Note:** This is NOT marine/maritime incident data. These are onshore and offshore pipeline incidents.

## File Structure

### Data Files by Pipeline Type

**Gas Distribution (gd):**
- `gd1986tofeb2004.xlsx` (1.3 MB) - 1986 to February 2004
- `gdmar2004to2009.xlsx` (739 KB) - March 2004 to 2009
- `gd2010toPresent.xlsx` (2.0 MB) - 2010 to present
- Form field documentation PDFs

**Gas Transmission/Gathering/Unregulated Systems (gtgg/ungs):**
- `gtgg1986to2001.xlsx` (761 KB) - 1986 to 2001
- `gtgg2002to2009.xlsx` (877 KB) - 2002 to 2009
- `gtggungs2010toPresent.xlsx` (2.9 MB) - 2010 to present
- Form field documentation PDFs

**Hazardous Liquid (hl):**
- `hl1986to2001.xlsx` (1.9 MB) - 1986 to 2001
- `hl2002to2009.xlsx` (2.4 MB) - 2002 to 2009
- `hl2010toPresent.xlsx` (7.3 MB) - 2010 to present ⬅️ **Largest file**
- Form field documentation PDFs

**Liquefied Natural Gas (lng):**
- `lng2011toPresent.xlsx` (86 KB) - 2011 to present
- Form field documentation PDF

### Supporting Documentation

- `Index Data Sources.txt` - Data source metadata
- `EightCauseMappingMethods.xlsx` (28 KB) - Cause classification mapping
- `SevenCauseMappingMethods.xlsx` (28 KB) - Alternative cause classification

## Data Coverage

### Time Range
- **Earliest:** 1986
- **Latest:** 2025 (present)
- **Total:** 39 years of pipeline incident data

### Pipeline Types Covered

**1. Gas Distribution (GD)**
- Local distribution pipelines
- Customer service lines
- City gate to end user

**2. Gas Transmission (GTGG)**
- Interstate/intrastate transmission
- Gathering systems
- High-pressure long-distance transport

**3. Hazardous Liquid (HL)**
- Crude oil pipelines
- Refined petroleum products
- Chemical pipelines
- **NOTE:** Includes offshore pipelines

**4. LNG Facilities**
- Liquefied natural gas facilities
- Import/export terminals
- **NOTE:** May include marine terminals

## Marine/Maritime Relevance

### Offshore Pipeline Incidents

**Potentially relevant to marine safety database:**

1. **Hazardous Liquid offshore segments** (hl files)
   - Gulf of Mexico crude oil pipelines
   - Offshore platform connections
   - Subsea pipeline infrastructure

2. **LNG marine terminals** (lng files)
   - Import/export terminal incidents
   - Marine loading/unloading operations
   - Vessel connection incidents

### Geographic Scope

For marine-relevant data, focus on:
- **Gulf of Mexico** offshore pipelines
- **Alaska** offshore pipelines
- **California** offshore pipelines
- **East Coast** offshore connections

## Data Structure

### Incident Fields (typical)

Based on form field documentation:

**Identifiers:**
- Report number
- Operator name
- System type
- Location (state, county, city, ZIP)

**Incident Details:**
- Incident date/time
- Discovery date/time
- Incident type/cause
- Part involved
- Material released
- Commodity released

**Consequences:**
- Fatalities
- Injuries
- Property damage ($)
- Environmental damage
- Barrels released
- Gas released (MCF)
- Estimated cost

**Response:**
- Shutdown/restart details
- Emergency response
- Notifications made
- Investigation findings

## Relevance to Marine Safety Database

### HIGH RELEVANCE (Include)

**Offshore Pipeline Incidents:**
- Located in offshore waters (Gulf of Mexico, Alaska, California)
- Platform-to-platform pipelines
- Platform-to-shore pipelines
- Subsea pipeline failures
- Marine terminal connections

**Criteria for inclusion:**
- Location indicates offshore/marine environment
- Incident affects vessel traffic/navigation
- Marine casualties resulted (vessel strikes pipeline)
- Environmental impact in marine waters

### LOW RELEVANCE (Exclude)

**Onshore Pipeline Incidents:**
- Land-based distribution pipelines
- City gas distribution
- Interstate transmission (non-marine)
- Storage facility incidents

## Estimated Marine-Relevant Records

**From Hazardous Liquid files (offshore oil/gas):**
- Gulf of Mexico: ~1,000-2,000 incidents
- Alaska offshore: ~100-200 incidents
- California offshore: ~50-100 incidents
- **Total offshore HL:** ~1,500-2,500 incidents

**From LNG files (marine terminals):**
- Marine terminal incidents: ~50-100 incidents

**Grand Total Marine-Relevant:** ~1,500-2,600 incidents (estimated)

## Integration Strategy

### Phase 1: Identify Marine Incidents

1. **Filter Hazardous Liquid data by location:**
   - State = "OFFSHORE" or "OCS" (Outer Continental Shelf)
   - Location contains "Gulf of Mexico", "Alaska", "Pacific"
   - County/City indicates offshore jurisdiction

2. **Filter LNG data by facility type:**
   - Facility type = "Marine terminal"
   - Location = coastal areas with vessel access

### Phase 2: Cross-Reference

**Compare with existing data:**
- BSEE offshore incidents (already have)
- NOAA oil spills (already have)
- USCG marine casualties (already have)

**Goal:** Identify unique pipeline incidents not captured elsewhere

### Phase 3: Import

**Create new importer:**
- `phmsa_pipeline_importer.py`
- Focus on offshore/marine incidents only
- Map to marine_safety_incidents schema
- Store pipeline-specific data in metadata_json

## Data Quality Notes

### Strengths
- Comprehensive coverage (39 years)
- Detailed incident information
- Regulatory-quality data (mandatory reporting)
- Consistent schema (PHMSA forms)

### Limitations
- Primarily onshore pipeline focus
- Offshore incidents are subset
- May overlap with BSEE data (offshore platforms)
- LNG terminal data limited

## Next Steps

### Immediate Actions

1. **Examine offshore incidents:**
   ```python
   # Read HL 2010-present (largest offshore coverage)
   df = pd.read_excel('hl2010toPresent.xlsx', header=1)

   # Filter for offshore
   offshore = df[df['STATE'].isin(['OFFSHORE', 'OCS', 'GULF OF MEXICO'])]
   print(f"Offshore incidents: {len(offshore)}")
   ```

2. **Assess marine relevance:**
   - Count offshore incidents
   - Review incident descriptions
   - Identify overlaps with BSEE/NOAA data

3. **Decision point:**
   - If >500 unique marine incidents: Create importer
   - If <500: Manual review and selective import
   - If mostly duplicates: Document overlap, skip import

### Manual Work Required

**For water transport hazmat data (still needed):**
- Visit PHMSA Hazmat Portal: https://hazmatonline.phmsa.dot.gov/
- Filter by Transportation Mode: "Water"
- Export incidents (separate from pipeline data)
- Expected: 500-1,500 maritime hazmat incidents

## File Locations

```
phmsa_hazmat/
├── PHMSA_Pipeline_Safety_Flagged_Incidents.zip (24 MB)
├── PHMSA_PIPELINE_DATA_README.md (this file)
├── README.md (hazmat portal notes)
├── Gas Distribution (1986-present)
│   ├── gd1986tofeb2004.xlsx
│   ├── gdmar2004to2009.xlsx
│   └── gd2010toPresent.xlsx
├── Gas Transmission (1986-present)
│   ├── gtgg1986to2001.xlsx
│   ├── gtgg2002to2009.xlsx
│   └── gtggungs2010toPresent.xlsx
├── Hazardous Liquid (1986-present) ⬅️ OFFSHORE DATA
│   ├── hl1986to2001.xlsx
│   ├── hl2002to2009.xlsx
│   └── hl2010toPresent.xlsx (7.3 MB)
└── LNG (2011-present) ⬅️ MARINE TERMINALS
    └── lng2011toPresent.xlsx
```

## Related Datasets

**Offshore incidents already in database:**
- BSEE offshore platform incidents (`/bsee_offshore/`) - 67 years, 50K+ records
- NOAA oil spills (`/noaa_spills/`) - 4,797 incidents including offshore
- Marine pipeline areas (`/doe_pipelines/`) - GeoPackage spatial data

**Complementary data not yet imported:**
- PHMSA offshore pipeline incidents (this directory)
- PHMSA water transport hazmat (still need to download)

## Contact

**PHMSA Pipeline Safety:**
- Website: https://www.phmsa.dot.gov/data-and-statistics/pipeline
- Data Portal: https://portal.phmsa.dot.gov/analytics/
- Email: phmsa.pipelinedata@dot.gov

**For marine/maritime questions:**
- BSEE (offshore platforms): https://www.bsee.gov/
- USCG (vessel incidents): https://www.dco.uscg.mil/

---

**README Created:** 2025-10-08
**Data Status:** Downloaded, ready for offshore incident analysis
**Marine Relevance:** Moderate (offshore pipeline subset)
**Priority:** Medium (after BSEE offshore import)
