# OSHA Enforcement & Fatality Data for Oil & Gas

> WRK-067: Acquire OSHA enforcement and fatality data for oil & gas.

## Data Sources

### 1. DOL OSHA Enforcement Data (enforcedata.dol.gov)

| Dataset | Description | Target File |
|---------|-------------|-------------|
| `osha_inspection` | All OSHA inspections with establishment info, NAICS codes, dates | `osha_inspection.csv` |
| `osha_violation` | Violations cited during inspections, penalty amounts | `osha_violation.csv` |
| `osha_accident` | Accident/incident reports | `osha_accident.csv` |
| `osha_accident_injury` | Injury details linked to accidents | `osha_accident_injury.csv` |

**Download URL (original):**
```
https://enforcedata.dol.gov/views/data_catalogs/zip/osha_inspection.csv.zip
https://enforcedata.dol.gov/views/data_catalogs/zip/osha_violation.csv.zip
https://enforcedata.dol.gov/views/data_catalogs/zip/osha_accident.csv.zip
https://enforcedata.dol.gov/views/data_catalogs/zip/osha_accident_injury.csv.zip
```

**Status (2026-02-01):** UNAVAILABLE via CLI. The enforcedata.dol.gov site has been
migrated to a React SPA that requires JavaScript execution. All URL patterns return
HTML pages instead of data files. The bulk CSV/ZIP download mechanism is no longer
accessible via direct HTTP requests (curl/wget).

**Manual Download Instructions:**
1. Open https://enforcedata.dol.gov in a browser
2. Navigate to Data Catalogs > OSHA
3. Download each dataset as CSV/ZIP
4. Place extracted CSV files in this directory

### 2. OSHA Severe Injury Reports (osha.gov)

**Download URL (original):**
```
https://www.osha.gov/severeinjury/xml/severeinjury.csv
```

**Status (2026-02-01):** Returns HTTP 404. The URL structure has changed.

**Manual Download Instructions:**
1. Open https://www.osha.gov/severeinjury in a browser
2. Look for data download or export option
3. Save as `osha_severe_injury_reports.csv` in `../../../marine_safety/raw/osha_maritime/`

### 3. OSHA Fatality Reports (osha.gov)

**Download URL (original):**
```
https://www.osha.gov/fatalities/reports/csv
```

**Status (2026-02-01):** Returns HTTP 404. The URL structure has changed.

**Manual Download Instructions:**
1. Open https://www.osha.gov/fatalities in a browser
2. Look for data download or CSV export option
3. Save as `osha_fatalities.csv` in this directory

## Oil & Gas NAICS Codes for Filtering

Once data is downloaded, filter using these NAICS codes:

| NAICS Code | Description |
|------------|-------------|
| `211110` | Crude Petroleum and Natural Gas Extraction |
| `211120` | Natural Gas Liquid Extraction |
| `211130` | Natural Gas Extraction |
| `213111` | Drilling Oil and Gas Wells |
| `213112` | Support Activities for Oil and Gas Operations |

**Broader prefixes:**
- `211` - Oil and Gas Extraction
- `213111` - Drilling Oil and Gas Wells
- `213112` - Support Activities for Oil and Gas Operations
- `48611` - Pipeline Transportation of Crude Oil
- `48621` - Pipeline Transportation of Natural Gas

### Filtering Example (Python/Polars)

```python
import polars as pl

OIL_GAS_NAICS = ["211110", "211120", "211130", "213111", "213112"]

df = pl.read_csv("osha_inspection.csv")

# NAICS column is typically "naics_code" in the inspection dataset
oil_gas = df.filter(
    pl.col("naics_code").cast(pl.Utf8).str.starts_with("211")
    | pl.col("naics_code").cast(pl.Utf8).str.starts_with("213111")
    | pl.col("naics_code").cast(pl.Utf8).str.starts_with("213112")
)
```

## Alternative Data Sources

If DOL enforcement data remains unavailable via CLI:

1. **BLS Census of Fatal Occupational Injuries (CFOI):**
   https://www.bls.gov/iif/oshcfoi1.htm
   Annual fatality counts by industry, available as pre-built tables.

2. **NIOSH Worker Health Charts:**
   https://wwwn.cdc.gov/Niosh-whc/
   Occupational injury/illness data with industry breakdowns.

3. **data.gov OSHA datasets:**
   Search https://catalog.data.gov for "OSHA enforcement"
   May have mirrored copies of the DOL datasets.

## Attempted URLs (All Failed - 2026-02-01)

```
# DOL enforcedata - all return HTML (React SPA, requires JS)
https://enforcedata.dol.gov/views/data_catalogs/zip/osha_inspection.csv.zip
https://enforcedata.dol.gov/views/data_summary/osha_inspection.csv.zip
https://enforcedata.dol.gov/api/osha_inspection
https://enforcedata.dol.gov/api/datadownload?dataset=osha_inspection&format=csv

# DOL data portal - returns HTML (Drupal CMS page)
https://data.dol.gov/get/osha_inspection/csv

# OSHA.gov - 404
https://www.osha.gov/severeinjury/xml/severeinjury.csv
https://www.osha.gov/fatalities/reports/csv
https://www.osha.gov/opengov/data

# BLS - 403 (blocked)
https://www.bls.gov/iif/oshcfoi1.htm
```
