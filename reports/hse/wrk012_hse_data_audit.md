# WRK-012: HSE Public Data Coverage Audit

**Date**: 2026-02-01
**Status**: Complete
**Repository**: worldenergydata
**Blocked by**: None
**Blocks**: WRK-013 (HSE mishap analysis), WRK-014 (HSE risk index)

---

## Executive Summary

This audit inventories all HSE data currently held in worldenergydata and maps it against the universe of publicly available HSE data sources relevant to the energy industry. The repository holds **~121,000 deduplicated incident records** across two SQLite databases, with **~950,000 raw CSV data lines** spanning 1957-2025. Coverage is strong for **marine casualties** (USCG, TSB Canada, UK MAIB, IMO GISIS, NOAA spills) but has significant gaps in **BSEE offshore incidents**, **onshore oil & gas**, **pipeline safety**, **industrial/process safety**, and **environmental releases**.

### Coverage Score by Category

| Category | Status | Score |
|----------|--------|-------|
| BSEE Offshore Incidents | Partial | 3/10 |
| Marine Casualties | Good | 7/10 |
| Marine Pipeline Incidents | Minimal | 1/10 |
| Marine Navigation Incidents | Good (via USCG/TSB) | 6/10 |
| Onshore Oil & Gas Incidents | Missing | 0/10 |
| Industrial / Process Safety | Missing | 0/10 |
| Environmental / Spill Data | Partial | 4/10 |
| International Offshore Safety | Minimal | 2/10 |

---

## 1. Current Data Inventory

### 1.1 Databases

| Database | Location | Size | Records | Sources | Date Range |
|----------|----------|------|---------|---------|------------|
| marine_safety.db (primary) | `data/modules/marine_safety/database/` | 60 MB | 68,152 incidents | USCG BARD (63,340), NOAA ORR (4,797), USCG live (15) | 1957-2025 |
| marine_safety.db (secondary) | `data/modules/marine_safety/` | 47 MB | 53,261 incidents | TSB Canada (47,385), UK MAIB (5,876) | 1975-2025 |
| **Combined total** | | **107 MB** | **121,413 incidents** | 5 source agencies | 1957-2025 |

**Empty tables in both databases**: companies, incident_causes, incident_documents, scrape_logs.

### 1.2 Raw CSV Data

| Source | File(s) | Records | Size | Date Range |
|--------|---------|---------|------|------------|
| Canadian TSB | 6 CSVs (occurrence, vessel, injuries, equipment) | 86,289 occurrences + related tables | 194 MB | 1975-2025 |
| USCG BARD (DLP) | 4 CSVs (accidents, vessels, injuries, deaths) | 93,237 accidents | 65 MB | 1995-2012 |
| IMO GISIS | 7 CSVs (by decade + collated) | 13,791 casualties | 2.7 MB | 1900-2025 |
| UK MAIB | 3 CSVs (occurrences, vessels, persons) | 5,877 occurrences | 13 MB | 2018-2024 |
| NOAA ORR | 1 CSV (incidents) | 4,798 spill incidents | 3.0 MB | 1957-2025 |
| OSHA Maritime | 1 CSV (Oregon only) | 37 inspections | 2.1 KB | Limited |
| PHMSA Hazmat | 1 CSV (summary only) | 26 records | 1.3 KB | Summary |
| USCG MISLE | 1 CSV (sample) | 16 records | 2.7 KB | Sample |
| NIOSH CFID | 1 CSV | 0 (empty) | 0 B | -- |

### 1.3 Excel Data

| Source | Files | Size | Date Range | Status |
|--------|-------|------|------------|--------|
| BSEE Offshore Incident Statistics | 17 XLSX (FY2007-CY2023) | ~36 MB total | 2007-2023 | **15 of 17 files are 53KB stubs** -- only CY2019 (326KB) and CY2021 (35MB) contain full data |
| PHMSA Pipeline Incidents | 12 XLSX | 18 MB total | 1986-present | Acquired but not imported |
| OSHA Severe Injury | 1 XLSX | 473 B | Minimal | Stub file |
| DOE Pipeline Incidents | 1 XLSX | 0 B | -- | Empty file |

### 1.4 Other Data

| Type | Files | Size | Notes |
|------|-------|------|-------|
| BSEE Historical PDFs | 9 | 36 MB | 1956-2000, not machine-readable |
| PHMSA Form Field PDFs | 7 | 4.5 MB | Reference documentation |
| EMSA Annual Overview PDFs | 4 | 5.8 MB | 2020-2023 reports |
| PHMSA Pipeline ZIP | 2 | 48 MB | Pipeline safety flagged incidents |
| DOE Pipeline GeoPackage | 1 | 30 MB | Geographic/spatial data |
| HTML scraped pages | 31 | ~1 MB | Source pages cached |
| data.gov search results | 3 JSON | 585 KB | API search metadata |

### 1.5 Empty/Scaffold Directories (Planned but No Data)

- `data/modules/pipeline_safety/raw/phmsa/` -- 4 subdirs, all empty
- `data/modules/marine_safety/raw/bts/` -- empty
- `data/modules/marine_safety/raw/epa_nrc/` -- empty
- `data/modules/marine_safety/raw/ntsb/` -- empty
- `data/modules/marine_safety/raw/uscg_boating/` -- empty
- `data/modules/marine_safety/raw/lloyds_historical/` -- empty
- `data/modules/marine_safety/raw/imca/` -- empty
- `data/modules/marine_safety/raw/iii/` -- empty
- `data/modules/marine_safety/raw/dlp_boating/` -- empty
- `data/modules/marine_safety/archive/` -- 7 empty subdirs
- `data/modules/marine_safety/exports/` -- 7 empty subdirs
- `data/modules/marine_safety/processed/` -- 7 empty subdirs

---

## 2. Source-by-Source Gap Analysis

### 2.1 BSEE Offshore Incidents

| Source | Available | Our Status | Gap |
|--------|-----------|------------|-----|
| BSEE Incident Investigations (data.bsee.gov) | CSV/ZIP, 2005+ | **Not acquired** -- Excel stubs only | HIGH |
| BSEE INCs (Incidents of Non-Compliance) | ZIP (INCSRawData.zip), monthly updates | **Not acquired** | HIGH |
| BSEE Spills Archive | HTML/PDF, 1964-2013 (>=50 bbl) | **Not acquired** (have NOAA spills instead) | MEDIUM |
| BSEE Panel Investigation Reports | PDF, historical-present | **Not acquired** | MEDIUM |
| BSEE District Investigation Reports | PDF, 2005+ | **Not acquired** | MEDIUM |
| BSEE Offshore Incident Statistics Tables | HTML, annual | Excel stubs exist (15/17 are empty) | HIGH |
| BSEE Civil Penalties | HTML, annual | **Importer exists but no data acquired** | HIGH |
| SafeOCS (BSEE + BTS) | Dashboard (aggregated, confidential underlying data) | Not applicable (confidential) | N/A |

**Assessment**: The HSE module has 6 importers for BSEE data, but they target well/production data (APD, WAR, Production) rather than the actual incident investigation datasets. The incident Excel files are mostly 53KB stubs. **No actual BSEE incident investigation records have been acquired.**

### 2.2 Marine Casualties

| Source | Available | Our Status | Gap |
|--------|-----------|------------|-----|
| USCG MISLE (bulk, 2002-2015) | ZIP from Homeport | **Sample only (16 records)** -- bulk file not downloaded | HIGH |
| USCG BARD (1995-2012) | 4 CSVs from DLP | **Acquired: 93,237 accidents** | None (historical complete) |
| USCG Live Casualty Reports | Web scraping | **15 records scraped** -- scraper exists but minimal data | MEDIUM |
| NTSB CAROL Marine | CSV/JSON query export | **Importer built, no data acquired** -- raw/ntsb/ is empty | HIGH |
| IMO GISIS | CSV export (registration required) | **Acquired: 13,791 records (1900-2025)** | None |
| UK MAIB | CSV + Power BI | **Acquired: 5,877 records (2018-2024)** | None |
| TSB Canada MARSIS | 6 CSV tables, monthly updates | **Acquired: 86,289 records (1975-2025)** | None |
| EMSA EMCIP (EU) | Web portal (restricted bulk) | **Importer is a stub** -- not implemented | HIGH |
| ATSB Marine (Australia) | PDF reports, scraper available | **Scraper built, data not in DB** | MEDIUM |
| JTSB Marine (Japan) | PDF reports, J-MARISIS tool | **Not researched** | LOW |
| AMSA (Australia) | PDF annual reports | **Not researched** | LOW |

**Assessment**: Strong coverage from TSB Canada, USCG BARD, UK MAIB, and IMO GISIS. Key gaps are the USCG MISLE bulk dataset (only a sample acquired), NTSB marine investigations (importer ready but no data), and EMSA (stub code only).

### 2.3 Marine Pipeline Incidents

| Source | Available | Our Status | Gap |
|--------|-----------|------------|-----|
| PHMSA Pipeline Incident Data (source data) | TXT/ZIP, 1970+, nightly updates | **Excel files acquired (18MB) but not imported**; pipeline_safety module is empty scaffold | HIGH |
| PHMSA Pipeline Flagged Files | ZIP/TXT, 20-year trends | **ZIP acquired (24MB) but not extracted/imported** | HIGH |
| BSEE Pipeline Data (data.bsee.gov) | ZIP, historical-present | **Not acquired** | HIGH |
| BOEM Pipeline Arc GIS Data | Shapefiles | **Not acquired** | MEDIUM |
| NTSB Pipeline Investigations | PDF + CAROL query | **Not acquired** | MEDIUM |

**Assessment**: PHMSA data has been downloaded but sits unprocessed. The pipeline_safety module is an empty scaffold with no importers or database schema. This is a significant gap for offshore pipeline incident analysis.

### 2.4 Marine Navigation Incidents

Navigation incidents (collisions, groundings, allisions) are captured within broader marine casualty datasets:

| Source | Coverage of Navigation Events | Our Status |
|--------|------------------------------|------------|
| USCG BARD | Accident types include collision, grounding, allision | **Acquired (93K records)** |
| TSB Canada | Occurrence types include collision, grounding, capsizing | **Acquired (86K records)** |
| IMO GISIS | Casualty types include navigation events | **Acquired (14K records)** |
| UK MAIB | Event types include collision, grounding | **Acquired (5.9K records)** |
| Equasis PSC Data | Port state control inspections, deficiencies | **Not acquired** |
| Paris MoU Inspections | PSC database (no bulk download) | **Not acquired** |
| Tokyo MoU APCIS | PSC database (no bulk download) | **Not acquired** |

**Assessment**: Navigation incidents are reasonably well-covered within the marine casualty datasets already acquired. Port state control data (Equasis, Paris/Tokyo MoU) would add inspection/deficiency context but is not bulk-downloadable.

### 2.5 Onshore Oil & Gas Incidents

| Source | Available | Our Status | Gap |
|--------|-----------|------------|-----|
| OSHA Severe Injury Reports | CSV, 2015+, semi-annual | **1 stub file (473 bytes)** | CRITICAL |
| OSHA Fatality Data | CSV, 2011+, daily updates | **Not acquired** | CRITICAL |
| DOL Enforcement Data (OSHA inspections/violations) | CSV, 1973+, daily updates | **Not acquired** | CRITICAL |
| EPA RMP Accident History | Spreadsheets via DLP FOIA | **Not acquired** | HIGH |
| Texas RRC Incidents | Data files + online query | **Not acquired** | HIGH |
| CalGEM (California) | SQL backups, WellSTAR, GIS | **Not acquired** | MEDIUM |
| NIOSH FOG Database | Interactive charts (no bulk) | **1 empty CSV** | MEDIUM |
| BLS CFOI (fatal injuries) | HTML tables, data files | **Not acquired** | MEDIUM |

**Assessment**: **Zero onshore oil & gas incident data has been acquired.** This is the largest categorical gap. OSHA enforcement data alone covers 1973-present with daily updates and is freely downloadable as CSV.

### 2.6 Industrial / Process Safety Incidents

| Source | Available | Our Status | Gap |
|--------|-----------|------------|-----|
| CSB Investigations | PDF reports (no bulk DB) | **Not acquired** | HIGH |
| EPA TRI (Toxic Release Inventory) | CSV, 1987+, annual | **Not acquired** | HIGH |
| NRC Event Reports (Nuclear) | Pipe-delimited TXT, 1999+, monthly | **Not acquired** | MEDIUM |

**Assessment**: **No industrial/process safety data has been acquired.** EPA TRI provides the most accessible bulk dataset (CSV, 1987-present).

### 2.7 Environmental / Spill Data

| Source | Available | Our Status | Gap |
|--------|-----------|------------|-----|
| NOAA IncidentNews | CSV, 1957+, ongoing | **Acquired: 4,798 records** | None |
| NRC (National Response Center) | Excel/query, 1990+ | **raw/epa_nrc/ directory exists but is empty** | HIGH |
| NOAA ERMA | GIS web layers | Not applicable (web tool) | N/A |
| ITOPF Tanker Spill Stats | PDF (Our World in Data CSV proxy) | **Not acquired** | LOW |
| California OSPR | CSV via data.ca.gov | **Not acquired** | LOW |
| IOPC Fund | PDF publications | **Not acquired** | LOW |

**Assessment**: NOAA spill data is acquired. The National Response Center (NRC) spill data is a significant gap -- it covers all oil, chemical, radiological, and biological discharges reported in the US since 1990.

### 2.8 International Offshore Safety

| Source | Available | Our Status | Gap |
|--------|-----------|------------|-----|
| UK HSE Offshore Statistics | PDF annual reports | **Not acquired** | MEDIUM |
| IOGP Safety Performance Data | PDF + online portal | **Not acquired** | MEDIUM |
| Norway Havtil RNNP | PDF reports | **Not acquired** | MEDIUM |
| NOPSEMA (Australia) | PDF annual reports | **Not acquired** | LOW |
| OEUK HSE Report | PDF (may require membership) | **Not acquired** | LOW |

**Assessment**: No international offshore-specific safety data beyond what's captured in IMO GISIS. These sources are mostly PDF reports without bulk data downloads.

---

## 3. Code Quality Issues

### 3.1 HSE Module -- Data Loss Bugs

| Issue | Severity | Description |
|-------|----------|-------------|
| **Violation fields silently dropped** | HIGH | `BSEEPenaltiesImporter.normalize_data()` captures 7 violation-specific fields (inc_number, violation_type, regulation_cited, penalty_amount, penalty_status, compliance_deadline, compliance_achieved) but `BaseImporter.import_record()` only creates `HSEIncident` objects. The `ViolationIncident` child table is never populated. |
| **Statistics fields silently dropped** | HIGH | `BSEEStatisticsImporter` captures 7 aggregate count fields that have no columns in `HSEIncident`. The `DataQualityValidator` acknowledges these as "placeholders". |
| **Source URL mismatch** | MEDIUM | URL importers target well/production datasets (APDRawData.zip, eWellWARRawData.zip, ProductionRawData.zip) rather than actual incident/penalty/statistics datasets from BSEE. |
| **BSEE Excel stubs** | MEDIUM | 15 of 17 BSEE incident Excel files are 53KB, likely empty or minimal. Only CY2019 and CY2021 contain substantial data. |

### 3.2 Marine Safety Module -- Config Gap

The `marine_safety.yaml` config defines only 4 sources (uscg_misle, noaa, maib, tsb), but importers exist for 8 sources (also NTSB, ATSB, IMO, EMSA, Boating). The NTSB, ATSB, IMO, and BARD importers are not referenced in the config.

### 3.3 EMSA Importer is a Stub

The EMSA EMCIP importer has 98 field mappings defined but all methods raise `NotImplementedError`. Access requires a formal request process (4-8 weeks) through EU Member State authorities.

---

## 4. Priority Gap Recommendations

### Tier 1 -- High Impact, Easy Acquisition (CSV/ZIP downloads)

| # | Source | Action | Est. Records | Format |
|---|--------|--------|-------------|--------|
| 1 | **OSHA Enforcement Data** (DOL) | Download from enforcedata.dol.gov; filter NAICS 211/213 for oil & gas | 100K+ | CSV |
| 2 | **OSHA Severe Injury Reports** | Download full dataset from osha.gov/severe-injury-reports | 50K+ | CSV |
| 3 | **OSHA Fatality Data** | Download from osha.gov/fatalities | 10K+ | CSV |
| 4 | **BSEE Incident Investigations** | Download from data.bsee.gov (actual incident dataset, not APD/WAR) | 10K+ | ZIP/CSV |
| 5 | **BSEE INCs** | Download INCSRawData.zip from data.bsee.gov | 50K+ | ZIP |
| 6 | **EPA TRI** | Download basic data files 1987-present from EPA | 1M+ | CSV |
| 7 | **PHMSA Pipeline Data** | Extract & import existing ZIPs; download latest source data | 20K+ | TXT/ZIP |
| 8 | **USCG MISLE Bulk** | Download MISLE_DATA.zip from USCG Homeport | 200K+ | ZIP |
| 9 | **NTSB CAROL Marine** | Query CAROL for mode=marine, export CSV | 2K+ | CSV/JSON |

### Tier 2 -- High Impact, Moderate Effort

| # | Source | Action | Notes |
|---|--------|--------|-------|
| 10 | **NRC Spill Reports** | Query nrc.uscg.mil; may need FOIA for bulk | 1990-present |
| 11 | **EPA RMP Accidents** | Download from Data Liberation Project | FOIA-obtained data |
| 12 | **Texas RRC Incidents** | Download from rrc.texas.gov | Texas-specific |
| 13 | **CSB Investigations** | Scrape investigation reports from csb.gov | PDF-based, ~200 investigations |
| 14 | **BSEE Pipeline Data** | Download from data.bsee.gov/Main/Pipeline.aspx | Offshore pipeline segments |

### Tier 3 -- Moderate Impact, Lower Priority

| # | Source | Action | Notes |
|---|--------|--------|-------|
| 15 | **UK HSE Offshore Stats** | Download PDFs from hse.gov.uk | UK-specific, annual reports |
| 16 | **IOGP Safety Data** | Access data.iogp.org | May require membership for detailed data |
| 17 | **Norway Havtil RNNP** | Download English reports | Norwegian offshore, PDF |
| 18 | **California OSPR Spills** | Download CSV from data.ca.gov | California-specific |
| 19 | **ITOPF Stats** (via Our World in Data) | Download proxy CSV | Tanker spill trends |
| 20 | **BLS CFOI** | Download industry fatal injury tables | Aggregated statistics |

### Tier 4 -- Low Priority / Restricted Access

| # | Source | Notes |
|---|--------|-------|
| 21 | EMSA EMCIP | Requires institutional access (4-8 week process) |
| 22 | DNV WOAD | Paid subscription |
| 23 | Lloyd's List Intelligence | Paid subscription |
| 24 | IADC ISP | Membership required for detailed data |
| 25 | API OII Survey | Purchased through IHS Markit |

---

## 5. Fix Recommendations (Code)

| # | Issue | Fix |
|---|-------|-----|
| 1 | HSE Penalties importer drops violation fields | Override `import_record()` in `BSEEPenaltiesImporter` to create `ViolationIncident` child records |
| 2 | HSE Statistics importer schema mismatch | Create a separate `SafetyStatistics` model for aggregated data, or refactor to map aggregated counts to individual synthetic records |
| 3 | URL importers target wrong BSEE datasets | Update URLs to point to actual incident, penalty, and statistics raw data endpoints on data.bsee.gov |
| 4 | BSEE Excel files are stubs | Re-download all 17 Excel files from bsee.gov/stats-facts/offshore-incident-statistics; verify content |
| 5 | marine_safety.yaml missing sources | Add NTSB, ATSB, IMO, and BARD to config |
| 6 | Pipeline safety module is empty | Build importers for PHMSA data (already downloaded) using existing marine_safety importer patterns |

---

## 6. Summary Statistics

| Metric | Value |
|--------|-------|
| **Total incident records (deduplicated, in DBs)** | 121,413 |
| **Total raw data lines (CSV)** | ~950,000 |
| **Data footprint (marine safety)** | 584 MB |
| **Source agencies with data acquired** | 6 (USCG BARD, TSB Canada, UK MAIB, IMO GISIS, NOAA ORR, USCG live) |
| **Source agencies with importers but no data** | 3 (NTSB, ATSB, EMSA) |
| **Source agencies not yet researched/built** | 15+ (see Tier 1-3 above) |
| **Categories with zero coverage** | 2 (Onshore O&G, Industrial/Process Safety) |
| **Categories with minimal coverage** | 2 (BSEE Offshore, Pipeline Safety) |
| **Estimated records available from Tier 1 sources** | 1.4M+ |

---

## 7. Conclusion

The worldenergydata HSE data foundation is **incomplete for comprehensive risk profiling**. The marine casualty dataset is the strongest asset (~121K records from 6 agencies), but BSEE offshore incident data is virtually absent despite having importers (they point to wrong data endpoints), onshore oil & gas data is entirely missing, and pipeline safety data is downloaded but unprocessed.

**Recommended next step**: Execute Tier 1 acquisitions (items 1-9) to close the most critical gaps. This would add an estimated 1.4M+ records across OSHA, BSEE, EPA TRI, PHMSA, USCG MISLE, and NTSB sources, all freely available as CSV/ZIP downloads requiring no authentication or institutional access.

---

*Report generated for WRK-012. Unblocks WRK-013 (HSE mishap analysis by activity) and WRK-014 (HSE risk index).*
