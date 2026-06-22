# Offshore Assets — Global O&G Fields, Facilities & Rigs Reference

Normalized, worldenergydata-native reference tables covering global oil & gas
**fields**, **production facilities**, **host vessels**, **drilling rigs** and
**jackups**. Re-expressed in clean relational tables from a legacy reference
extraction; the valuable attributes (water depth, operator, block, status,
vessel specifications, discovery date) were parsed out of semi-structured
`"Key : Value"` JSON cells into proper typed columns.

Corpus epic llm-wiki#767; worldenergydata issue #543.

## Scope & relationship to BSEE

This is **global** coverage (US, UK, Norway, Australia, Brazil, Angola,
Malaysia, Indonesia, Nigeria, …). It **complements** the US-Gulf-of-Mexico BSEE
module (`data/modules/bsee`), which is the authoritative, regulator-sourced US
dataset. Rows whose country is the United States are flagged `US_GOM_FLAG = Y`
in `fields.csv` and `production_facilities.csv` to support a later **name-based
cross-reference** against BSEE field/facility names (no automatic join is
performed here — names differ in formatting between the two sources).

## Facts-only policy

These are factual reference attributes only. Source-link / URL columns from the
legacy extraction were **dropped entirely**; no free-text narrative or
description prose is carried over (only discrete factual attributes); no
third-party site names or attribution appear anywhere. No personal data.
Operator names (e.g. Shell, Statoil, ONGC, Petrobras) are retained as factual
asset attributes.

## Tables

All CSVs are UTF-8, comma-delimited, header row, under `curated/`.

### `fields.csv` — 2,149 rows
Global oil & gas field catalog. One row per field.

| Column | Type | Notes |
|---|---|---|
| FIELD_ID | string | stable identifier from the legacy catalog |
| FIELD_NAME | string | field name |
| COUNTRY | string | country |
| BLOCK | string | licence block / concession |
| RESERVE_TYPE | string | Oil / Gas / Oil/Gas |
| CURRENT_STATUS | string | e.g. Producing, Under Development, Discovery |
| DISCOVERY_DATE | string | month-year text as recorded (e.g. `Jul 1997`) |
| PRODUCTION_START | string | month-year text where known |
| WATER_DEPTH_M | integer | water depth, metres (parsed from `"… m / … ft"`) |
| WATER_DEPTH_FT | integer | water depth, feet |
| US_GOM_FLAG | string | `Y` if United States (for BSEE cross-reference) |

### `production_facilities.csv` — 836 rows
Production facility catalog (FPSOs, spars, platforms, FLNG, subsea tiebacks…).

| Column | Type | Notes |
|---|---|---|
| FACILITY_ID | string | identifier |
| FACILITY_NAME | string | facility name |
| DUTY | string | Oil / Gas / n/a |
| OPERATOR | string | operating company |
| HOST_TYPE | string | FPSO, Fixed Platform, SPAR, TLP, FLNG, Semisub, Subsea Tieback, … |
| CURRENT_STATUS | string | status with the "since YEAR" suffix stripped |
| STATUS_SINCE_YEAR | integer | year parsed out of the status text where present |
| WATER_DEPTH_M | integer | metres |
| WATER_DEPTH_FT | integer | feet |
| COUNTRY | string | country |
| LOCATION | string | block / concession / location label |
| US_GOM_FLAG | string | `Y` if United States |

### `host_facilities.csv` — 245 rows
Host vessel / facility particulars (predominantly FPSO vessels). Parsed from a
deep `"Key : Value"` vessel-data array; numeric specs are unit-suffixed in the
column name.

Columns: FACILITY_TYPE, VESSEL_NAME, CLASSIFICATION, LENGTH_M, WIDTH_M, DEPTH_M,
MAX_OPERATING_DRAFT_M, HULL_CONSTRUCTION, DEADWEIGHT_DWT_TONNES,
CONSTRUCTION_TYPE, HULL_FAB_YEAR, LATEST_UPGRADE_YEAR, MAX_OIL_PROD_MBOPD,
GAS_PROCESSING_MMSCFD, TOTAL_THROUGHPUT_MBOED, STORAGE_CAPACITY_MBBLS,
TOTAL_RISERS, UMBILICALS, QUARTERS_CAPACITY, MOORING_SYSTEM_TYPE,
PERMANENT_OR_DISCONNECTABLE, NUMBER_OF_ANCHOR_LEGS.

### `drilling_rigs.csv` — 163 rows
Floating drilling rigs (semisubmersibles / drillships).

Columns: RIG_NAME, VESSEL_TYPE, VESSEL_DESIGN, CONSTRUCTION_YEAR, UPGRADE_YEAR,
CLASSIFICATION_SOCIETY, MAX_WATER_DEPTH_RATING_FT, MAX_DRILLING_DEPTH_FT,
TOTAL_VESSEL_POWER_HP, QUARTERS_CAPACITY, LENGTH_FT, WIDTH_FT, OPERATING_DRAFT_FT,
MAX_VARIABLE_LOAD_ST, DERRICK_RATING_KIPS, DRAWWORKS_HP, BOP_OPERATING_PRESSURE_KSI.

### `jackups.csv` — 134 rows
Jackup drilling rigs.

Columns: RIG_NAME, RIG_DESIGN_MODEL, YEAR_DELIVERED, COUNTRY_BUILT,
CLASSIFICATION_SOCIETY, MAX_WATER_DEPTH_RATING_FT, MIN_WATER_DEPTH_FT,
OVERALL_LEG_LENGTH_FT, SPUD_CAN_DIAMETER_FT, MAX_DRILLING_DEPTH_FT,
QUARTERS_CAPACITY, OVERALL_HULL_LENGTH_FT, DERRICK_RATING_KIPS, DRAWWORKS_HP,
BOP_OPERATING_PRESSURE_KSI.

### `country_centroids.csv` — 205 rows
Country → centroid latitude/longitude lookup (COUNTRY, LATITUDE, LONGITUDE) for
mapping fields/facilities by country.

## Parsing notes

- Source attributes lived as JSON arrays of `"Key : Value"` strings inside a
  single `Details` / `data` cell. These were split on `" : "`, empty values and
  section-header rows dropped, and mapped to the typed columns above.
- `WATER_DEPTH_*` parsed from the dual `"1,300 m / 4,290 ft"` form into separate
  metre and feet integer columns.
- `STATUS_SINCE_YEAR` parsed out of strings like `"Producing since 2003"`.
- Numeric columns had thousands separators and unit suffixes stripped.
- Blank cells indicate the attribute was absent in the source record.

## Coverage summary

**Fields (2,149)** top countries: US 333, UK 308, Norway 302, Australia 192,
Brazil 98, Angola 75, Malaysia 65, Indonesia 62, Ireland 39, Denmark 33.
US-flagged (BSEE cross-ref candidates): 333.

**Production facilities (836)** top countries: UK 124, US 88, Norway 82, Brazil
58, Australia 50, Malaysia 48, China 32, Indonesia 30. US-flagged: 88.
By host type: Fixed Platform 465, FPSO 152, Subsea Tieback 54, FSO/FSU 42,
FPU/FPS 32, Semisub 20, TLP 20, SPAR 19, FLNG 8, MOPU 8, others 16.

**Rigs:** drilling rigs 163, jackups 134, host vessels 245.
