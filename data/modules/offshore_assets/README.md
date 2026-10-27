# Offshore Assets — Global O&G Fields, Facilities & Rigs Reference

## Angola evidence extension

Issue [1144](https://github.com/vamseeachanta/worldenergydata/issues/1144) adds an
optional evidence extension reader without changing `curated/fields.csv` or
the legacy facility joins. The importer preserves namespaced research IDs,
typed development/phase/block/well scopes, source vintages, depth envelopes,
milestone date bounds and cost bases. Shared legacy IDs remain informational.
Exact names and compatible blocks produce pending candidates; equivalence
requires an owner decision pinned to the candidate digest.

Run `scripts/field_development/integrate_angola_catalog.py --snapshot <snapshot>
--output <local-preview>` to generate a local draft and publication decision
matrix. Output must be outside the original snapshot. Original input bytes
are verified against their manifest; generated outputs receive deterministic
hashes. `catalog_integration.read_bundle(path)` verifies output hashes and
reads registry, crosswalk, legacy ledger, relationships and scoped evidence.
The writer validates serialized readback before creating a new destination and
rejects existing destinations. The manifest is written last. Gate-file JSON
rejects duplicate keys and non-finite numbers; optional raw gate-file digests
remain separate from normalized decision digests. Accepted crosswalk rows retain
their candidate-bound decision records on export and readback. Recorded signoff
is evidence metadata, not authenticated publication authority.

The reader contract is described in `catalog_integration_schema.json`.
Preview outputs are local drafts and must not be staged as public data.
`--public-export --eligibility <owner-reviewed-matrix>` filters the complete
dependency closure. Missing or stale eligibility decisions defer records;
an empty entity export fails. Public readers use `public_only=True`.
Inherited costs reference their existing parent rows rather than add new
cost observations. The extension does not establish national completeness,
verified current configuration, engineering suitability or field allocation.

Normalized, worldenergydata-native reference tables covering global oil & gas
**fields**, **production facilities**, **host vessels**, **drilling rigs** and
**jackups**. Except for jackups, re-expressed in clean relational tables from a legacy reference
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

These are factual reference attributes only. Jackups retain public contractor
source URLs as described below. For the other tables, source-link / URL columns from the
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

### `jackups.csv` — 163 rows

Jackup drilling rigs rebuilt solely from public contractor specification pages
and contractor overview pages, retrieved **27 Oct 2026**. The previous table was replaced
because source redistribution was not cleared. No previous row values were used.

Columns: RIG_NAME, RIG_DESIGN_MODEL, YEAR_DELIVERED, COUNTRY_BUILT,
CLASSIFICATION_SOCIETY, MAX_WATER_DEPTH_RATING_FT, MIN_WATER_DEPTH_FT,
OVERALL_LEG_LENGTH_FT, SPUD_CAN_DIAMETER_FT, MAX_DRILLING_DEPTH_FT,
QUARTERS_CAPACITY, OVERALL_HULL_LENGTH_FT, DERRICK_RATING_KIPS, DRAWWORKS_HP,
BOP_OPERATING_PRESSURE_KSI, source_url.

The following mapping is the complete input basis; additional contractor fields
are not imported. The collection digest, output digest and row count are recorded
in the `jackups.csv` entry of `_metadata.json`.

| Output column | Contractor collection field | Transformation |
|---|---|---|
| RIG_NAME | rig | unchanged |
| RIG_DESIGN_MODEL | design | unchanged |
| YEAR_DELIVERED | year | unchanged; mixed year basis described below |
| MAX_WATER_DEPTH_RATING_FT | max_water_depth_m | metres to feet |
| OVERALL_LEG_LENGTH_FT | leg_length_m | metres to feet |
| SPUD_CAN_DIAMETER_FT | spudcan_diameter_m | metres to feet |
| MAX_DRILLING_DEPTH_FT | drilling_depth_m | metres to feet |
| OVERALL_HULL_LENGTH_FT | hull_length_m | metres to feet |
| source_url | source_url | unchanged; multiple URLs separated by semicolons |

Lengths are divided by exactly 0.3048 and rounded to one decimal foot. Decimal
places describe conversion, not measurement accuracy. A blank source value
stays blank. COUNTRY_BUILT, CLASSIFICATION_SOCIETY, MIN_WATER_DEPTH_FT,
QUARTERS_CAPACITY, DERRICK_RATING_KIPS, DRAWWORKS_HP and
BOP_OPERATING_PRESSURE_KSI are entirely blank because the collection has no
corresponding fields. Consumers must accept empty cells as unknown, never zero.

`YEAR_DELIVERED` retains its column name for compatibility but the collection
mixes build, delivery and entered-service years; it is not a uniform delivery
date. Water-depth limits may describe design or operating conditions, and source
vintages vary. Spudcan diameter is populated only when explicitly labelled as
a diameter. Total leg length excludes explicitly below-hull or deployable
lengths; some source totals include spudcans. Hull lengths may use the source's
overall dimensions. No suitability or current configuration is established.

The collection covers 13 contractor groups and is a sample, not a global census.
Fourteen rows depend partly or wholly on indexed official specifications whose
direct sheets could not be read: nine from ARO Drilling, four from
Northern Offshore, and one from COSL. Their URLs identify the reported public
sources; direct-source readback is not established. Missing or conflicting
particulars remain empty. Source links may redirect or become unavailable.

To rebuild from the supplied collection, take its SHA-256 from `_metadata.json`
and run:

```sh
python scripts/field_development/build_contractor_jackups.py \
  <contractor-collection.csv> <replacement.csv> --source-sha256 <digest>
```

The importer validates the input digest before writing and never reads an
existing output. The source collection is retained separately; URLs and a digest
do not constitute an archived copy of the source pages. This replacement does
not rewrite the old file in git history.

### `country_centroids.csv` — 205 rows
Country → centroid latitude/longitude lookup (COUNTRY, LATITUDE, LONGITUDE) for
mapping fields/facilities by country.

### `coverage_summary.csv` — 135 rows  (derived roll-up)
Analytical roll-ups computed **from `fields.csv` and `production_facilities.csv`**
(counts by country, reserve type / duty, status, host type, water-depth band, and
US-GoM vs rest of world). Long-form: CATEGORY, DIMENSION, FIELDS_COUNT,
FACILITIES_COUNT. See `COVERAGE_SUMMARY.md` for the narrative breakdown. This is a
new derived artifact, not a copy of any source.

## Parsing notes

These legacy parsing notes apply to the tables other than `jackups.csv`.

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

**Rigs:** drilling rigs 163, jackups 163, host vessels 245.
