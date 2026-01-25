# Codebase Integration Mapping

> **Purpose**: Map BSEE knowledge base to existing codebase locations
> **Codebase Root**: `src/worldenergydata/modules/bsee/`
> **Last Updated**: 2026-01-18

---

## Quick Reference

| Knowledge Base Section | Primary Codebase Location |
|------------------------|---------------------------|
| Well URLs | `data/scrapers/bsee_web.py` |
| Production URLs | `data/refresh/data_refresh_enhanced.py` |
| Configuration | `data/config/config_router.py` |
| Data Processing | `data/enhanced/` |
| Analysis Tools | `analysis/` |
| Paleowells | `paleowells/` |

---

## URL Definitions

### Primary URL Locations

| File | URLs Defined | Purpose |
|------|--------------|---------|
| `data/scrapers/bsee_web.py` | 4 primary URLs | Main scraper definitions |
| `paleowells/data_downloader.py` | 6 URLs | Well/BOEM data downloads |
| `data/config/config_router.py` | 5+ URLs | Configuration-based routing |
| `data/refresh/data_refresh_enhanced.py` | 3 URLs | Enhanced data refresh |
| `data/enhanced/data_refresh_chunked.py` | 4 URLs | Chunked download handling |

### bsee_web.py (Primary Scraper)
```python
# Lines 26-29
BSEE_URLS = {
    "apd": "https://www.data.bsee.gov/Well/Files/APDRawData.zip",
    "war": "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip",
    "production": "https://www.data.bsee.gov/Production/Files/ProductionRawData.zip",
    "borehole": "https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip",
}
```

### paleowells/data_downloader.py
```python
# Lines 23-46
BSEE_SOURCES = {
    "apd": "https://www.data.bsee.gov/Well/Files/APDRawData.zip",
    "war": "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip",
    "borehole": "https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip",
}
BOEM_SOURCES = {
    "borehole": "https://www.data.boem.gov/Well/Borehole/Default.aspx",
}
```

---

## Data Dictionary Mappings

| Knowledge Base Dictionary | Codebase Usage |
|---------------------------|----------------|
| Well Status Codes | `analysis/well_api12.py`, docs in `well_activity_cd_description.md` |
| Production Fields | `data/_legacy/production_data_from_website.py` |
| Platform Fields | (To be implemented) |
| Pipeline Fields | (To be implemented) |

### Existing Code Lookups

| Lookup | Location | Notes |
|--------|----------|-------|
| Status Codes | `docs/data-sources/bsee/data/clean_up/well_activity_cd_description.md` | Partial |
| Area Codes | `data/config/` | Configuration files |
| Company Codes | (Derived from data) | No static lookup |

---

## Configuration Files

### config_router.py
```python
# Line 115-123
DATA_SOURCES = {
    "wells": {
        "apd": ConfiguredSource(...),
        "borehole": ConfiguredSource(...),
    },
    "production": {
        "monthly": ConfiguredSource(...),
    },
}
```

---

## Data Flow

```
BSEE Data Center
       │
       ▼
┌─────────────────────────────────┐
│  data/scrapers/bsee_web.py      │ ◄── Downloads raw ZIP files
└─────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  data/refresh/                   │ ◄── Orchestrates refresh cycles
│    data_refresh_enhanced.py      │
└─────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  data/enhanced/                  │ ◄── Chunked processing
│    data_refresh_chunked.py       │
└─────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  analysis/                       │ ◄── Analysis modules
│    well_api12.py                 │
│    decline_curve.py              │
└─────────────────────────────────┘
```

---

## Module Structure

```
src/worldenergydata/modules/bsee/
├── data/
│   ├── scrapers/
│   │   └── bsee_web.py          # Main scraper
│   ├── config/
│   │   └── config_router.py     # URL routing config
│   ├── refresh/
│   │   └── data_refresh_enhanced.py  # Refresh orchestration
│   ├── enhanced/
│   │   └── data_refresh_chunked.py   # Chunked downloads
│   └── _legacy/
│       ├── production_data_from_website.py
│       ├── get_zip_well_production_data.py
│       ├── scrapy_well_data.py
│       └── scrapy_production_data.py
├── analysis/
│   ├── well_api12.py           # API well analysis
│   └── decline_curve.py        # Production decline
├── paleowells/
│   └── data_downloader.py      # Historical well data
└── reports/
    └── comprehensive/
        └── templates/
            └── compliance_template.py
```

---

## HSE Integration

| Module | BSEE Usage |
|--------|------------|
| `modules/hse/importers/bsee_incidents_importer_url.py` | Incident data |
| `modules/hse/importers/bsee_penalties_importer_url.py` | Penalty data |
| `modules/hse/importers/bsee_statistics_importer_url.py` | Statistics |

---

## Documentation Locations

| Doc Type | Location |
|----------|----------|
| Data Exploration | `docs/raw_data/bsee/data_exploration.md` |
| Data Explanation | `docs/data-sources/bsee/data/clean_up/data_explaination.md` |
| Production Notes | `docs/data-sources/bsee/data/production/notes.md` |
| APM Data | `docs/data-sources/bsee/data/apm_data_rev1.md` |
| URL Integration | `docs/hse/URL_REFRESH_INTEGRATION.md` |

---

## Skills Integration

| Skill | Location | BSEE Usage |
|-------|----------|------------|
| BSEE Data Extractor | `.claude/skills/bsee-data-extractor/` | Data extraction |
| Web Scraper Energy | `.claude/skills/web-scraper-energy/` | General scraping |

---

## Test Coverage

| Test Location | Coverage |
|---------------|----------|
| `tests/modules/bsee/analysis/` | Analysis modules |
| `tests/modules/data-procurement/` | API discovery |
| `tests/_archived_tests/modules/bsee/` | Archived tests |

---

## Recommended Updates

Based on knowledge base creation, these codebase updates are recommended:

1. **Centralize URL Definitions**
   - Create `data/config/urls.py` with all BSEE URLs
   - Reference from all scrapers

2. **Add Code Lookups**
   - Create `data/lookups/` with status codes, type codes
   - Reference from knowledge base

3. **Update Documentation**
   - Link existing docs to knowledge base
   - Add cross-references

4. **Standardize Field Names**
   - Align DataFrame columns with BSEE field names
   - Document any transformations

---

## Related Documents

- [Scraper URLs](scraper-urls.md) - Complete URL inventory
- [Data Sources Index](../data-sources/index.md) - Master URL registry
- [Borehole Fields](../data-dictionaries/wells/borehole-fields.md) - Field definitions
