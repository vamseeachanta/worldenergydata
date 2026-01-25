# BSEE Data Center Knowledge Base

> **Data Source**: Bureau of Safety and Environmental Enforcement (BSEE)
> **Portal**: https://www.data.bsee.gov/
> **Last Updated**: 2026-01-18
> **Coverage**: Gulf of America, Alaska, Pacific, Atlantic OCS Regions

---

## Quick Reference

| Category | Datasets | Documentation |
|----------|----------|---------------|
| **Wells** | APD, Borehole, API Lookup, BHPS, eWell | [data-dictionaries/wells/](data-dictionaries/wells/) |
| **Production** | OGOR-A/B/C, FMP, By Platform, By Planning Area | [data-dictionaries/production/](data-dictionaries/production/) |
| **Platforms** | Structures, Deepwater (>1000ft) | [data-dictionaries/platforms/](data-dictionaries/platforms/) |
| **Pipelines** | Location, Permits, ROW Descriptions | [data-dictionaries/pipelines/](data-dictionaries/pipelines/) |
| **Leasing** | Lease Area/Block, Owner, Assignments, Decom Costs | [data-dictionaries/leasing/](data-dictionaries/leasing/) |
| **GIS** | 15+ Shapefiles & Geodatabases | [gis-catalog/](gis-catalog/) |

---

## Data Access Methods

### 1. Raw Data Downloads (ZIP Files)
Direct download of delimited ASCII files. See [data-sources/raw-data-downloads.md](data-sources/raw-data-downloads.md)

```
Base URL: https://www.data.bsee.gov/{Category}/Files/{Dataset}RawData.zip
Example:  https://www.data.bsee.gov/Well/Files/APDRawData.zip
```

### 2. Online Query Interfaces
Web-based search with filters and export options. See [query-interfaces/](query-interfaces/)

```
Base URL: https://www.data.bsee.gov/{Category}/{Dataset}/Default.aspx
Example:  https://www.data.bsee.gov/Well/Borehole/Default.aspx
```

### 3. GIS Data (Shapefiles & Geodatabases)
Geospatial data for mapping. See [gis-catalog/](gis-catalog/)

```
Base URL: https://www.data.bsee.gov/Mapping/Files/{dataset}.zip
Example:  https://www.data.bsee.gov/Mapping/Files/platform.zip
```

---

## Directory Structure

```
docs/knowledge-base/bsee/
├── README.md                    # This file
├── data-sources/                # URL registry and data source catalog
│   ├── index.md                 # Master index of all data sources
│   ├── raw-data-downloads.md    # All ZIP file downloads (38 files)
│   ├── online-queries.md        # Web-based query interfaces
│   └── update-schedule.md       # Data refresh frequencies
├── regions/                     # Regional data organization
│   ├── index.md                 # Region overview
│   ├── gulf-of-america.md       # GOA (primary region)
│   ├── alaska.md                # Alaska OCS
│   ├── pacific.md               # Pacific OCS
│   └── atlantic.md              # Atlantic OCS
├── data-dictionaries/           # Field definitions (reference tables)
│   ├── wells/                   # Well data fields
│   ├── production/              # Production data fields
│   ├── platforms/               # Platform structure fields
│   ├── pipelines/               # Pipeline data fields
│   ├── leasing/                 # Lease data fields
│   ├── company/                 # Company data fields
│   └── common/                  # Shared codes and formats
├── gis-catalog/                 # GIS data documentation
│   ├── index.md                 # GIS overview
│   ├── shapefiles.md            # Shapefile downloads
│   ├── geodatabases.md          # Geodatabase files
│   └── coordinate-systems.md    # NAD27/NAD83 details
├── query-interfaces/            # Online query documentation
│   ├── index.md                 # Query interface overview
│   └── {dataset}-query.md       # Per-dataset query docs
└── integration/                 # Codebase integration
    ├── codebase-mapping.md      # Maps to src/worldenergydata
    └── scraper-urls.md          # URLs used in scrapers
```

---

## Regional Coverage

| Region | Abbreviation | Primary Coordinate System | Notes |
|--------|--------------|---------------------------|-------|
| Gulf of America | GOA | NAD27 | Most comprehensive, primary data |
| Alaska | AK | NAD83 | Alaska OCS-specific datasets |
| Pacific | PAC | NAD83 | Pacific OCS data |
| Atlantic | ATL | NAD83 | Atlantic OCS data |

---

## Update Frequencies

| Dataset Type | Update Frequency | Notes |
|--------------|------------------|-------|
| Well APD | Daily | Application for Permit to Drill |
| Well WAR | Daily | Well Activity Reports |
| Production | Bi-monthly | 15th of each month |
| Platforms | As reported | Structure changes |
| Pipelines | As reported | Location changes |
| GIS Data | Monthly | First week of month |

---

## Key Concepts

### API Well Number
- **API10**: 10-digit format (State + County + Well)
- **API12**: 12-digit format (API10 + Sidetrack + Completion)
- See [data-dictionaries/common/api-number-format.md](data-dictionaries/common/api-number-format.md)

### Status Codes
| Code | Description |
|------|-------------|
| APD | Application for Permit to Drill |
| AST | Approved Sidetrack |
| CNL | Cancelled |
| COM | Borehole Completed |
| CT | Core Test |
| DRL | Drilling |
| DSI | Drilling Suspended - Rig on Location |
| PA | Permanently Abandoned |
| ST | Sidetrack |
| TA | Temporarily Abandoned |
| VCW | Verified Completion of Work |

### Type Codes
| Code | Description |
|------|-------------|
| C | Core Test |
| D | Development |
| E | Exploratory |
| N | New Well |
| O | Original Completion |
| R | Recompletion |
| S | Sidetrack |

---

## Codebase Integration

This knowledge base maps to the following codebase locations:

| Knowledge Base | Codebase Location |
|----------------|-------------------|
| Well URLs | `src/worldenergydata/modules/bsee/data/scrapers/bsee_web.py` |
| Production URLs | `src/worldenergydata/modules/bsee/data/refresh/data_refresh_enhanced.py` |
| Config routing | `src/worldenergydata/modules/bsee/data/config/config_router.py` |
| Analysis tools | `src/worldenergydata/modules/bsee/analysis/` |

See [integration/codebase-mapping.md](integration/codebase-mapping.md) for complete mapping.

---

## External Links

- **BSEE Main Site**: https://www.bsee.gov/
- **BSEE Data Center**: https://www.data.bsee.gov/
- **BOEM Data Center**: https://www.data.boem.gov/
- **BOEM GIS Services**: https://gis.boem.gov/arcgis/rest/services/BOEM_BSEE/

---

## Related Documentation

- [BSEE Data Exploration](../../raw_data/bsee/data_exploration.md)
- [BSEE Analysis Documentation](../../data-sources/bsee/)
- [HSE URL Integration](../../hse/URL_REFRESH_INTEGRATION.md)
