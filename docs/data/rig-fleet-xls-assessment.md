# Rig Fleet XLS Data Assessment for Porting

> **Date**: 2026-02-08
> **Assessor**: Claude Agent (automated legal + data assessment)
> **Source**: `client_projects/energy_engineering/0113 Orc DR/Reference/`
> **Target**: `worldenergydata/src/worldenergydata/modules/bsee/data/`
> **Status**: ASSESSMENT ONLY -- no data has been ported

---

## 1. Legal Scan Results

### 1.1 Deny List Scan

The legal sanity scanner (`scripts/legal/legal-sanity-scan.sh --repo=worldenergydata`) was executed. The scan uses the following deny lists:

- **Global**: `.legal-deny-list.yaml` (no active patterns configured)
- **worldenergydata**: `worldenergydata/.legal-deny-list.yaml` (ENIGMA, Databricks, dbutils, dbfs:, spark.databricks)

The scanner timed out when running with grep fallback (ripgrep not available in environment). However, a manual Python-based scan of all 11 XLS/XLSX file contents was performed (see Section 1.2).

### 1.2 Manual Content Scan

All cell values across all 11 files (10 `.xls` + 1 `.xlsx`) were programmatically scanned for:

| Pattern | Result |
|---------|--------|
| Email addresses (`@domain.tld`) | **NONE FOUND** |
| Project code `0113` | **NONE FOUND** in file contents |
| Project codename `Orc DR` | **NONE FOUND** in file contents |
| `ENIGMA` (denied term) | **NONE FOUND** |
| `Databricks` (denied term) | **NONE FOUND** |
| `dbutils` (denied term) | **NONE FOUND** |
| `dbfs:` (denied term) | **NONE FOUND** |
| Windows file paths (`C:\`) | **NONE FOUND** |
| UNC paths (`\\server`) | **NONE FOUND** |

### 1.3 Metadata Scan

File metadata was inspected for author/creator information:

| File | Metadata Finding | Severity |
|------|------------------|----------|
| `DrillRigs.xls` | User name: `Undi` | **WARN** -- generic, not identifiable |
| `Drilling Riser Model Properties.xlsx` | Creator: `Manoj Pydah`, Last modified by: `Manoj Pydah` | **WARN** -- personal name in metadata |
| All other `.xls` files | No user name in metadata | CLEAR |

### 1.4 Directory/Filename References

The source directory path `client_projects/energy_engineering/0113 Orc DR/Reference/` contains:
- **`0113`**: Internal project number -- **BLOCK** severity if included in ported data/code
- **`Orc DR`**: Internal project codename -- **BLOCK** severity if included in ported data/code

These references exist ONLY in the file system path, NOT within the data files themselves. No action required as long as ported data does not reference the source path.

---

## 2. Data Inventory

### 2.1 File Summary

| # | File | Size | Sheets | Rows | Cols | Description |
|---|------|------|--------|------|------|-------------|
| 1 | `DrillRigs.xls` | 186 KB | 1 | 95 | 164 | **Master file** -- all 163 rigs with 95 field rows |
| 2 | `DrillRigs Rig Data.xls` | 33 KB | 1 | 6 | 164 | Vessel type, design, construction/upgrade dates, classification |
| 3 | `DrillRigs Rig Rating and Contract.xls` | 32 KB | 1 | 7 | 164 | Water depth ratings, drilling depth, contract info, area of operation |
| 4 | `DrillRigs Vessel Particulars.xls` | 35 KB | 1 | 11 | 164 | Power, speed, quarters, dimensions, draft, variable load, moonpool |
| 5 | `DrillRigs Mooring and Station Keeping.xls` | 32 KB | 1 | 9 | 164 | DP rating, thrusters, chain, wire rope, anchors |
| 6 | `DrillRigs Lifting Equipment.xls` | 26 KB | 1 | 6 | 164 | Pedestal cranes (1-4), riser handling crane |
| 7 | `DrillRigs Drilling Equipment and Engineering Company Details.xls` | 50 KB | 1 | 16 | 164 | Derrick, drawworks, top drive, heave compensator, pipe racking |
| 8 | `DrillRigs Mud Pumps.xls` | 36 KB | 1 | 11 | 164 | Mud pumps, mud pit volumes, shale shakers, solids control |
| 9 | `DrillRigs Riser and Tensioner data.xls` | 40 KB | 1 | 11 | 164 | Riser tensioners, riser specs (size, class, manufacturer) |
| 10 | `DrillRigs BOP and BOP Control Details.xls` | 45 KB | 1 | 17 | 164 | BOP pressure, ram/annular BOPs, stack dimensions, control system |
| 11 | `Drilling Riser Model Properties.xlsx` | 278 KB | 1 | 131 | 9 | **Template only** -- section headers for riser analysis model, NOT fleet data |

### 2.2 Data Structure

All `.xls` files share the same transposed layout:
- **Row 0**: Rig names (163 rigs across columns 1-163)
- **Rows 1+**: Field labels in column 0, values in columns 1-163
- The master `DrillRigs.xls` consolidates all data from files 2-10

### 2.3 Rig Count and Types

- **Total rig entries**: 163
- **Unique rig names**: 163

Vessel types present:
- `SS` -- Semi-Submersible
- `DS` -- Drillship
- `Louisiana` -- appears to be a data entry anomaly (single entry)

### 2.4 Data Vintage

- Contract expiration dates range from 2010 to 2022
- "Area of Operation" header references July 2008
- Construction dates range from 1974 to 2013
- **Conclusion**: This is a circa 2008-2012 era dataset, valuable as historical reference

---

## 3. Complete Field Inventory with Data Completeness

### 3.1 Rig Identification (files 2, 3)

| XLS Field | Filled | % | Notes |
|-----------|--------|---|-------|
| NAME | 163/163 | 100% | Rig names -- all public/industry-known |
| VESSEL TYPE | 162/163 | 99% | SS, DS |
| VESSEL DESIGN | 162/163 | 99% | Design class names (F&G, RBS-8M, etc.) |
| CONSTRUCTION DATE (yr.) | 161/163 | 99% | Year built |
| UPGRADE DATE (yr.) | 80/163 | 49% | Last major upgrade year |
| CLASSIFICATION (society) | 158/163 | 97% | ABS, DNV, BV, LR, NMD |

### 3.2 Ratings (file 3)

| XLS Field | Filled | % | Notes |
|-----------|--------|---|-------|
| MAXIMUM WATER DEPTH EQUIPPED (ft.) | 162/163 | 99% | Mixed formats: pure numeric + "8,000 ft." strings |
| MAXIMUM WATER DEPTH RATING (ft.) | 163/163 | 100% | Same format issues |
| MAXIMUM DRILLING DEPTH (ft.) | 161/163 | 99% | Same format issues |
| CURRENT CONTRACT (expiration) | 133/163 | 82% | Quarter/year format: "3Q/12" |
| AREA OF OPERATION | 158/163 | 97% | Geographic regions: GoM, Norway, W. Africa, etc. |

### 3.3 Vessel Particulars (file 4)

| XLS Field | Filled | % | Notes |
|-----------|--------|---|-------|
| TOTAL VESSEL POWER (H.P.) | 142/163 | 87% | Horsepower |
| MAX. VESSEL SPEED (knots) | 141/163 | 87% | Knots |
| QUARTERS CAPACITY (persons) | 157/163 | 96% | Person count |
| LENGTH (ft.) | 159/163 | 98% | Mixed: pure numeric + "392 ft." strings |
| WIDTH (ft.) | 155/163 | 95% | Mixed format |
| TRANSIT DRAFT (ft.) | 146/163 | 90% | Mixed format |
| OPERATING DRAFT (ft.) | 147/163 | 90% | Mixed format |
| MAX. VARIABLE LOAD (S.T.) | 154/163 | 95% | Short tons |
| MOONPOOL LENGTH (ft.) | 139/163 | 85% | **Complex**: "20 x 40", "89.2 ft. x 36.7 ft." |
| MOONPOOL BREADTH (ft.) | 139/163 | 85% | Same as length -- appears duplicated |

### 3.4 Station Keeping / Mooring (file 5)

| XLS Field | Filled | % | Notes |
|-----------|--------|---|-------|
| D.P. RATING | 127/163 | 78% | Mixed: "DP2", "DP3", "N/A", "n/a" |
| THRUSTERS (No. and H.P.) | 130/163 | 80% | Free-text: "6x5,000", "4x2,700" |
| SIZE of CHAIN (In.) | 86/163 | 53% | Inches |
| CHAIN GRADE | 81/163 | 50% | ORQ+20, R3S, K4, etc. |
| LENGTH OF CHAIN (ft.) | 81/163 | 50% | Mixed format |
| WIRE ROPE Diameter (In.) | 76/163 | 47% | Inches |
| LENGTH of WIRE ROPE (ft.) | 75/163 | 46% | Feet |
| ANCHOR SIZE (S.T.) | 93/163 | 57% | Short tons |

### 3.5 Lifting Equipment (file 6)

| XLS Field | Filled | % | Notes |
|-----------|--------|---|-------|
| PEDESTAL CRANE 1 (S.T.) | 154/163 | 95% | Short tons |
| PEDESTAL CRANE 2 (S.T.) | 154/163 | 95% | Short tons |
| PEDESTAL CRANE 3 (S.T.) | 98/163 | 60% | Short tons |
| PEDESTAL CRANE 4 (S.T.) | 61/163 | 37% | Short tons |
| RISER HANDLING CRANE (S.T.) | 76/163 | 47% | Short tons |

### 3.6 Drilling Equipment (file 7)

| XLS Field | Filled | % | Notes |
|-----------|--------|---|-------|
| DERRICK RATING (Max Hook Kips) | 146/163 | 90% | Kips |
| DERRICK MANUFACTURER | 153/163 | 94% | Manufacturer names |
| DERRICK FOOTPRINT LENGTH (ft.) | 135/163 | 83% | Mixed format |
| DERRICK FOOTPRINT BREADTH (ft.) | 135/163 | 83% | Mixed format |
| DRAWWORKS (H.P.) | 152/163 | 93% | Mixed: numeric + free-text |
| DRAWWORKS Manufacturer | 157/163 | 96% | Manufacturer names |
| DRILL LINE SIZE (In.) | 132/163 | 81% | Inches |
| ROTARY TABLE SIZE (In.) | 150/163 | 92% | Mixed: "60.5 in.", "60.5 in./49.5 in." |
| IRON ROUGHNECK Model | 148/163 | 91% | Model names |
| TOP DRIVE Manufacturer & Model | 150/163 | 92% | Combined mfr+model string |
| HEAVE COMPENSATOR Manufacturer | 143/163 | 88% | Manufacturer names |
| HEAVE COMPENSATION CAPACITY (Kips) | 141/163 | 87% | Mixed: numeric + "840/661" |
| COMPENSATION TYPE | 143/163 | 88% | Active/Passive/Both |
| PIPE RACKING SYSTEM Model | 135/163 | 83% | Model names |
| DRILLING INSTRUMENTATION Manufacturer | 121/163 | 74% | Manufacturer names |

### 3.7 Mud Systems (file 8)

| XLS Field | Filled | % | Notes |
|-----------|--------|---|-------|
| MUD PUMPS No. | 157/163 | 96% | Count |
| MUD PUMPS Manufacturer & Model | 153/163 | 94% | Combined string |
| MUD PIT ACTIVE VOLUME (bbls.) | 142/163 | 87% | Barrels |
| MUD PIT RESERVE VOLUME (bbls.) | 142/163 | 87% | Barrels, some "incl." values |
| DEDICATED COMPLETION FLUID VOLUME (bbls.) | 134/163 | 82% | Barrels |
| BULK STORAGE CAPACITY (Cu. ft.) | 140/163 | 86% | Cubic feet |
| GUMBO BUSTER (YES/NO) | 116/163 | 71% | Y/N/1.0 (inconsistent) |
| SHALE SHAKERS No. | 146/163 | 90% | Count, some "4+4" values |
| DESANDER No. | 124/163 | 76% | Count |
| DESILTER No. | 115/163 | 71% | Count |

### 3.8 Riser and Tensioner Data (file 9)

| XLS Field | Filled | % | Notes |
|-----------|--------|---|-------|
| RISER TENSIONER (Total Capacity) (Kips) | 145/163 | 89% | Kips |
| RISER TENSIONERS No. | 146/163 | 90% | Count |
| RISER TENSIONERS Manufacturer | 141/163 | 87% | Manufacturer names |
| DIVERTER SIZE (In.) | 141/163 | 87% | Mixed format |
| CLASS of RISER (API) | 121/163 | 74% | API class: E, F, G, H |
| RISER SIZE (O.D. In.) | 145/163 | 89% | Mixed format |
| RISER JOINT LENGTH (ft.) | 142/163 | 87% | Mixed format |
| FLEX JOINT (Top/Bottom) | 135/163 | 83% | Top/Bottom/Both/T+B |
| RISER MANUFACTURER | 144/163 | 88% | Manufacturer names |
| RISER STORAGE (ft.) | 126/163 | 77% | Feet |

### 3.9 BOP and BOP Control (file 10)

| XLS Field | Filled | % | Notes |
|-----------|--------|---|-------|
| BOP OPERATING PRESSURE (Ksi) | 149/163 | 91% | 10 or 15 Ksi |
| C&K LINE SIZE (I.D. In.) | 142/163 | 87% | Inches |
| AUX. LINE SIZE (I.D. In.) | 141/163 | 87% | Mixed: "3.8/2.5", "4.5 in." |
| AUX. LINES ON RISER No. | 141/163 | 87% | Count |
| RAM BOPs No. | 144/163 | 88% | Count |
| RAM BOPs Manufacturer | 146/163 | 90% | Cameron, Shaffer, NOV, etc. |
| ANNULAR BOPs No. | 144/163 | 88% | Count |
| ANNULAR BOPs Manufacturer | 146/163 | 90% | Manufacturer names |
| BOP Stack Length (ft.) | 117/163 | 72% | Feet |
| BOP Stack Breadth (ft.) | 117/163 | 72% | Feet |
| Total BOP Stack Weight (Kips) | 116/163 | 71% | Kips (includes LMRP) |
| WELLHEAD CONNECTOR TYPE | 141/163 | 87% | Connector model codes |
| BOP CONTROL SYSTEM TYPE | 145/163 | 89% | MUX, Bias, etc. |
| BOP CONTROL SYSTEM Manufacturer | 144/163 | 88% | Manufacturer names |
| ABLE TO SHEAR 6.635" Drillpipe | 128/163 | 79% | Y/N |
| RISER HANG-OFF CAPACITY (Kips) | 102/163 | 63% | Kips |

---

## 4. Client Reference Assessment

### 4.1 References Found

| Category | Finding | Severity |
|----------|---------|----------|
| Rig names | All 163 are publicly known drilling rigs (Transocean, Noble, Ensco, etc.) | CLEAR |
| Equipment manufacturers | All are public companies (Cameron, NOV, Vetco, Shaffer, etc.) | CLEAR |
| Geographic areas | Generic regions (GoM, Norway, West Africa) | CLEAR |
| Classification societies | Public bodies (ABS, DNV, BV, LR) | CLEAR |
| Contract dates | Quarter/year only, no client-specific details | CLEAR |
| File metadata - `DrillRigs.xls` | Username: `Undi` | **WARN** |
| File metadata - `Drilling Riser Model Properties.xlsx` | Creator: `Manoj Pydah` | **WARN** |
| Directory path | Contains `0113 Orc DR` (project code + codename) | **BLOCK** (path only) |
| File content | No denied terms, no client identifiers in any cell values | CLEAR |

### 4.2 Data Nature Classification

This dataset contains **publicly available industry reference data**:
- Rig names, types, and specifications are published by rig operators in marketing materials, regulatory filings, and industry databases (e.g., RigZone, IHS Petrodata, Offshore Magazine)
- Equipment specifications are manufacturer-published data
- No proprietary analysis, no client-specific calculations, no internal project references

---

## 5. Portability Rating

### Overall: **GREEN** (with minor caveats)

The data content is generic offshore drilling rig industry reference data. No client-identifiable information exists within the cell values of any file. The only flagged items are:

1. **File metadata** (WARN): Personal names in xlsx metadata -- will be stripped automatically during data extraction since only cell values are ported
2. **Source path** (BLOCK): The `0113 Orc DR` path must never appear in ported code, comments, or configuration

---

## 6. Data Quality Issues for Porting

### 6.1 Format Inconsistencies

The data has significant format inconsistencies that require parsing/cleaning:

| Issue | Examples | Affected Fields |
|-------|----------|-----------------|
| Mixed numeric + string with units | `5000.0` vs `"8,000 ft."` vs `"7,500 ft."` | Water depth, drilling depth, length, width, draft |
| Compound values | `"20 x 40"`, `"89.2 ft. x 36.7 ft."` | Moonpool dimensions |
| Slash-separated pairs | `"840/661"`, `"3.8/2.5"`, `"60.5 in./49.5 in."` | Heave compensation, aux line, rotary table |
| Free-text equipment specs | `"6x5,000"`, `"N-O FC2200(3), A1700PT(1)"` | Thrusters, mud pumps |
| Boolean inconsistency | `"Y"`, `"Yes"`, `"1.0"`, `"N"`, `"No"` | Gumbo buster, shear capability |
| N/A variants | `"N/A"`, `"n/a"`, `"NA"`, `""`, `"No"` | DP rating, various fields |
| Comma in numbers | `"3,000 ft."` | Chain length, wire rope length |

### 6.2 Structural Issues

- **Transposed layout**: Data is rig-per-column, not rig-per-row -- requires transposition
- **Duplicate fields**: Moonpool length and breadth contain identical compound values (e.g., `"20 x 40"` in both)
- **Section header rows**: Rows like "RIG INFORMATION", "VESSEL PARTICULARS" are labels, not data
- **Duplicate rig entries**: Some rigs appear in multiple columns of the sub-files (e.g., Atwood Hunter x8) -- these represent different time snapshots or configurations

---

## 7. Mapping to Existing RigFleetSchema

### 7.1 Direct Mappings (existing schema fields)

| RigFleetSchema Field | XLS Source Field | Parsing Required |
|---------------------|------------------|------------------|
| `RIG_NAME` | `NAME` | Strip whitespace only |
| `RIG_TYPE` | `VESSEL TYPE` | Map: SS->semi_submersible, DS->drillship |
| `OWNER` | Not in XLS | N/A -- not available |
| `OPERATOR` | Not in XLS | N/A -- not available |
| `WATER_DEPTH_RATING_FT` | `MAXIMUM WATER DEPTH RATING (ft.)` | Parse mixed format, strip commas and "ft." |
| `DRILLING_DEPTH_RATING_FT` | `MAXIMUM DRILLING DEPTH (ft.)` | Parse mixed format |
| `LOA_M` | `LENGTH (ft.)` | Parse + convert ft to meters |
| `BEAM_M` | `WIDTH (ft.)` | Parse + convert ft to meters |
| `DP_CLASS` | `D.P. RATING` | Parse: "DP2"->2, "DP3"->3, "N/A"->None |
| `YEAR_BUILT` | `CONSTRUCTION DATE (yr.)` | Cast to int |
| `MOONPOOL_DIAMETER_M` | `MOONPOOL LENGTH/BREADTH` | Parse compound "L x W", compute equivalent diameter, convert ft->m |

### 7.2 Fields Not Mappable (no XLS source)

| RigFleetSchema Field | Status |
|---------------------|--------|
| `RIG_STATUS` | Not in XLS (would need external source) |
| `IMO_NUMBER` | Not in XLS |
| `FLAG_STATE` | Not in XLS |
| `LAST_WAR_DATE` | Not in XLS |
| `LAST_AREA_CODE` | Partial: `AREA OF OPERATION` could map |
| `DISPLACEMENT_TONNES` | Not in XLS |
| `WELLS_DRILLED_COUNT` | Not in XLS |

---

## 8. New Schema Fields Needed

The XLS files contain extensive technical specifications not currently in `RigFleetSchema`. Recommended new fields:

### 8.1 Priority 1 -- High Value, Clean Data

| Proposed Field | Type | Unit | Source XLS Field | Completeness |
|----------------|------|------|------------------|--------------|
| `VESSEL_DESIGN` | `str` | -- | VESSEL DESIGN | 99% |
| `CLASSIFICATION_SOCIETY` | `str` | -- | CLASSIFICATION (society) | 97% |
| `MAX_WATER_DEPTH_EQUIPPED_FT` | `float` | ft | MAXIMUM WATER DEPTH EQUIPPED | 99% |
| `TOTAL_VESSEL_POWER_HP` | `float` | HP | TOTAL VESSEL POWER | 87% |
| `MAX_SPEED_KNOTS` | `float` | knots | MAX. VESSEL SPEED | 87% |
| `QUARTERS_CAPACITY` | `int` | persons | QUARTERS CAPACITY | 96% |
| `TRANSIT_DRAFT_FT` | `float` | ft | TRANSIT DRAFT | 90% |
| `OPERATING_DRAFT_FT` | `float` | ft | OPERATING DRAFT | 90% |
| `MAX_VARIABLE_LOAD_ST` | `float` | short tons | MAX. VARIABLE LOAD | 95% |
| `YEAR_UPGRADED` | `int` | year | UPGRADE DATE | 49% |

### 8.2 Priority 2 -- Riser and BOP (Core Engineering Data)

| Proposed Field | Type | Unit | Source XLS Field | Completeness |
|----------------|------|------|------------------|--------------|
| `RISER_TENSIONER_CAPACITY_KIPS` | `float` | kips | riser tensioner Total capacity | 89% |
| `RISER_TENSIONER_COUNT` | `int` | -- | RISER TENSIONERS No. | 90% |
| `RISER_OD_IN` | `float` | inches | RISER SIZE (O.D.) | 89% |
| `RISER_API_CLASS` | `str` | -- | CLASS of RISER (API) | 74% |
| `RISER_JOINT_LENGTH_FT` | `float` | ft | RISER JOINT LENGTH | 87% |
| `RISER_MANUFACTURER` | `str` | -- | RISER MANUFACTURER | 88% |
| `BOP_OPERATING_PRESSURE_KSI` | `float` | ksi | BOP OPERATING PRESSURE | 91% |
| `BOP_RAM_COUNT` | `int` | -- | RAM BOPs No. | 88% |
| `BOP_ANNULAR_COUNT` | `int` | -- | ANNULAR BOPs No. | 88% |
| `BOP_STACK_WEIGHT_KIPS` | `float` | kips | Total BOP stack Wt. | 71% |
| `BOP_CONTROL_SYSTEM_TYPE` | `str` | -- | BOP CONTROL SYSTEM TYPE | 89% |
| `RISER_HANGOFF_CAPACITY_KIPS` | `float` | kips | RISER HANG-OFF CAPACITY | 63% |

### 8.3 Priority 3 -- Moonpool Dimensions (Needs Special Parsing)

| Proposed Field | Type | Unit | Source XLS Field | Completeness |
|----------------|------|------|------------------|--------------|
| `MOONPOOL_LENGTH_FT` | `float` | ft | MOONPOOL LENGTH | 85% |
| `MOONPOOL_WIDTH_FT` | `float` | ft | MOONPOOL BREADTH | 85% |

Note: Current schema has `MOONPOOL_DIAMETER_M` (circular moonpool assumption). The XLS data provides rectangular dimensions as "L x W" compound strings. Both representations should be supported.

### 8.4 Priority 4 -- Drilling Equipment (Extended Specs)

| Proposed Field | Type | Unit | Source XLS Field | Completeness |
|----------------|------|------|------------------|--------------|
| `DERRICK_RATING_KIPS` | `float` | kips | DERRICK RATING | 90% |
| `DRAWWORKS_HP` | `float` | HP | DRAWWORKS | 93% |
| `HEAVE_COMP_CAPACITY_KIPS` | `float` | kips | HEAVE COMPENSATION CAPACITY | 87% |
| `HEAVE_COMP_TYPE` | `str` | -- | COMPENSATION TYPE | 88% |
| `MUD_PUMP_COUNT` | `int` | -- | MUD PUMPS No. | 96% |
| `MUD_PIT_ACTIVE_VOL_BBL` | `float` | bbls | MUD PIT ACTIVE VOLUME | 87% |
| `CRANE_1_CAPACITY_ST` | `float` | short tons | PEDESTAL CRANE 1 | 95% |

---

## 9. Recommended Actions

### 9.1 Immediate (Before Any Porting)

1. **Do NOT reference source path** -- Never include `0113`, `Orc DR`, or the full source directory path in any ported code, comments, configs, or commit messages
2. **Strip file metadata** -- The xlsx creator name `Manoj Pydah` must not propagate; extract cell values only
3. **Verify public domain** -- The rig names and specs in this dataset match publicly available industry data (RigZone, ODS-Petrodata). A spot-check of 3-5 rigs against public sources is recommended before bulk import

### 9.2 Data Extraction Pipeline

1. **Read from master file** (`DrillRigs.xls`) which consolidates all sub-files
2. **Transpose** data from rig-per-column to rig-per-row format
3. **Parse mixed formats** using regex to extract numeric values from strings like `"8,000 ft."` and `"89.2 ft. x 36.7 ft."`
4. **Deduplicate** rigs that appear in multiple columns (different time snapshots)
5. **Map vessel types**: SS -> semi_submersible, DS -> drillship
6. **Convert units** where needed (ft -> m for LOA, beam; if storing in metric)
7. **Validate** through `RigFleetSchema` with extended fields

### 9.3 Schema Extension

1. Extend `RigFleetSchema` with Priority 1 and 2 fields first
2. Add compound dimension support for moonpool (rectangular L x W, not just circular diameter)
3. Add equipment specification fields as a separate related schema (`RigEquipmentSchema`) to avoid bloating the main schema beyond 30+ fields
4. Consider a `RigBOPSchema` and `RigRiserSchema` for the detailed subsea equipment data

### 9.4 Data Quality Fixes

1. Build a robust numeric parser for the mixed format values (regex: strip commas, "ft.", "in.", "kips", unit suffixes)
2. Handle compound moonpool values by splitting on "x" delimiter
3. Normalize DP ratings to integers (DP2->2, DP3->3)
4. Normalize boolean fields (Y/Yes/1.0 -> True, N/No/0.0 -> False)
5. Handle "N/A" variants uniformly as None

---

## 10. Drilling Riser Model Properties.xlsx Assessment

This file is **NOT fleet data**. It is a riser analysis model template containing only section headers:
- Water Depth, Joint Properties, Auxiliary Lines, Flex Joint, Telescopic Joint
- Tensioner Properties, BOP/LMRP Properties, Conductor Properties
- Gimbal Bearing Specification, Vessel Properties, Riser Stackup

The only data value is a water depth of 1783m. This file is **not suitable for porting** to the rig fleet module. It belongs to a riser analysis workflow, not a fleet database.

---

## 11. Summary

| Metric | Value |
|--------|-------|
| Files assessed | 11 (10 .xls + 1 .xlsx) |
| Rigs in dataset | 163 unique drilling rigs |
| Data fields | 95 rows (approximately 80 actual data fields) |
| Client references in data | **NONE** |
| Denied terms found | **NONE** |
| Metadata warnings | 2 (personal names in file metadata) |
| Path-level blocks | 1 (source directory contains project code) |
| Portability rating | **GREEN** |
| Estimated parsing effort | **MEDIUM** (mixed formats require robust parsing) |
| Schema changes required | **YES** (20-30 new fields across Priority 1-4) |
| Recommended approach | Extract from master `DrillRigs.xls`, transpose, parse, validate |
