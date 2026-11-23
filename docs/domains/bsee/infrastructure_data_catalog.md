# BSEE Offshore Infrastructure Data Catalog

> Reference catalog for BSEE infrastructure datasets available through the worldenergydata platform.

## Overview

This catalog documents 4 infrastructure datasets from data.bsee.gov that supplement the existing well, production, and WAR data in the BSEE module.

## Data Sources

| Dataset | Key | ZIP File | URL | Update Frequency | Approx Size |
|---------|-----|----------|-----|-----------------|-------------|
| Platform Structures | `platform` | PlatStrucRawData.zip | data.bsee.gov/Platform/Files/PlatStrucRawData.zip | Daily | ~2 MB |
| Pipeline Permits | `pipeline_permit` | PipePermRawData.zip | data.bsee.gov/Pipeline/Files/PipePermRawData.zip | Daily | ~5 MB |
| Deepwater Structures | `deepwater_structure` | PermStrucRawData.zip | data.bsee.gov/Other/Files/PermStrucRawData.zip | Daily | ~1 MB |
| Pipeline Locations | `pipeline_location` | PipeLocRawData.zip | data.bsee.gov/Pipeline/Files/PipeLocRawData.zip | Daily | ~15 MB |

---

## 1. Platform Structures (PlatStrucRawData)

All platform structures installed on the Outer Continental Shelf (OCS).

### Fields

| Column | Type | Description |
|--------|------|-------------|
| AREA_CODE | str | OCS planning area code (e.g., GC, MC, VK, EW) |
| BLOCK_NUMBER | str | OCS block number |
| COMPLEX_ID_NUM | str | Complex identifier linking multiple structures |
| STRUCTURE_NUMBER | str | Unique structure identifier within block |
| STRUCTURE_NAME | str | Structure name (operator assigned) |
| STRUC_TYPE_CODE | str | Structure type (see reference below) |
| MAJ_STRUC_FLAG | str | Major structure flag (Y/N) |
| FIELD_NAME_CODE | str | BSEE field name code |
| WATER_DEPTH | float | Water depth in feet |
| INSTALL_DATE | date | Installation date |
| REMOVAL_DATE | date | Removal date (null if active) |
| DECK_COUNT | int | Number of decks |
| SLOT_COUNT | int | Total number of well slots |
| SLANT_SLOT_COUNT | int | Number of slant well slots |
| SLOT_DRILL_COUNT | int | Number of slots drilled |
| SATELLITE_COMPLETION_COUNT | int | Satellite completion count |
| UNDERWATER_COMPLETION_COUNT | int | Underwater completion count |
| HELIPORT_FLAG | str | Has heliport (Y/N) |
| ATTENDED_8_HR_FL | str | Attended 8 hours (Y/N) |
| MANNED_24_HR_FL | str | Manned 24 hours (Y/N) |
| LATITUDE | float | Latitude (decimal degrees) |
| LONGITUDE | float | Longitude (decimal degrees) |
| LEASE_NUMBER | str | OCS lease number |
| DISTRICT_CODE | str | BSEE district code |
| AUTHORITY_TYPE | str | Authorization type |
| AUTHORITY_NUMBER | str | Authorization number |
| AUTHORITY_STATUS | str | Authorization status |
| STE_CLRNCE_DATE | date | Site clearance date |
| INCS | str | Incident tracking code |

### Structure Type Codes

| Code | Description |
|------|-------------|
| FP | Fixed Platform |
| CT | Caisson / Caisson-type |
| WP | Well Protector |
| SP | Single Pile |
| TLP | Tension Leg Platform |
| SPAR | Spar Platform |
| FPS | Floating Production System |
| FPSO | Floating Production, Storage, Offloading |
| SS | Subsea Structure |
| MOPU | Mobile Offshore Production Unit |
| MIN | Minimal Structure |

---

## 2. Pipeline Permits (PipePermRawData)

All pipeline permits issued for OCS pipelines.

### Fields

| Column | Type | Description |
|--------|------|-------------|
| SEGMENT_NUM | str | Pipeline segment number |
| PPL_SIZE_CODE | str | Outside diameter code (see OD reference) |
| MAOP_PRSS | float | Maximum Allowable Operating Pressure (psig) |
| RECV_MAOP_PRSS | float | Received MAOP pressure (psig) |
| SEG_LENGTH | float | Segment length (miles) |
| MAX_WTR_DPTH | float | Maximum water depth (feet) |
| MIN_WTR_DPTH | float | Minimum water depth (feet) |
| PROD_CODE | str | Product code (see reference) |
| CATHODIC_CODE | str | Cathodic protection code |
| CAT_LIFE_TM | float | Cathodic protection design life (years) |
| BUR_DSGN_FL | str | Burial design flag |
| LK_DETEC_FL | str | Leak detection flag |
| BD_PPL_SDV_FL | str | Bidirectional pipeline SDV flag |
| BD_PPL_FSV_FL | str | Bidirectional pipeline FSV flag |
| BIDIR_FLAG | str | Bidirectional flow flag |
| DEP_FLAG | str | Departure flag |
| STATUS_CODE | str | Pipeline status code |
| PPL_CONST_DATE | date | Pipeline construction date |
| INIT_HS_DT | date | Initial hydrocarbon service date |
| APPROVED_DATE | date | Permit approval date |
| ABAN_DATE | date | Abandonment date |
| ABAN_APRV_DT | date | Abandonment approval date |
| ABAN_TYPE | str | Abandonment type |
| AREA_CODE | str | OCS area code |
| BLOCK_NUMBER | str | OCS block number |
| LEASE_NUMBER | str | OCS lease number |

### Pipeline OD Standard Sizes

| Code | OD (inches) |
|------|-------------|
| 005 | 0.5 |
| 010 | 1.0 |
| 015 | 1.5 |
| 020 | 2.0 |
| 025 | 2.5 |
| 030 | 3.0 |
| 035 | 3.5 |
| 040 | 4.0 |
| 045 | 4.5 |
| 060 | 6.0 |
| 065 | 6.625 |
| 080 | 8.0 |
| 085 | 8.625 |
| 100 | 10.0 |
| 105 | 10.75 |
| 120 | 12.0 |
| 125 | 12.75 |
| 140 | 14.0 |
| 160 | 16.0 |
| 180 | 18.0 |
| 200 | 20.0 |
| 220 | 22.0 |
| 240 | 24.0 |
| 260 | 26.0 |
| 280 | 28.0 |
| 300 | 30.0 |
| 320 | 32.0 |
| 340 | 34.0 |
| 360 | 36.0 |
| 380 | 38.0 |
| 400 | 40.0 |
| 420 | 42.0 |
| 440 | 44.0 |
| 480 | 48.0 |
| 540 | 54.0 |

### Pipeline Product Codes (Common)

| Code | Product |
|------|---------|
| OIL | Crude Oil |
| GAS | Natural Gas |
| CON | Condensate |
| WTR | Produced Water |
| GLC | Gas Lift, Continuous |
| GLI | Gas Lift, Intermittent |
| INJ | Injection |
| SRV | Service |
| TST | Test |

---

## 3. Deepwater Structures (PermStrucRawData)

Permitted structures, including deepwater and subsea installations.

### Fields

Similar to Platform Structures with additional fields:

| Column | Type | Description |
|--------|------|-------------|
| PERMIT_NUMBER | str | Structure permit number |
| BUS_ASC_NAME | str | Business associate (operator) name |
| (All Platform Structure fields) | | See Platform Structures section |

---

## 4. Pipeline Locations (PipeLocRawData)

Geographic coordinate points for all OCS pipeline segments.

### Fields

| Column | Type | Description |
|--------|------|-------------|
| SEGMENT_NUM | str | Pipeline segment number |
| POINT_NUM | int | Sequential point number along segment |
| LATITUDE | float | Latitude (decimal degrees) |
| LONGITUDE | float | Longitude (decimal degrees) |
| WATER_DEPTH | float | Water depth at point (feet) |
| AREA_CODE | str | OCS area code |
| BLOCK_NUMBER | str | OCS block number |

### Notes
- Multiple points per segment define the pipeline route
- Points are ordered sequentially along the pipeline path
- Can be joined to Pipeline Permits via SEGMENT_NUM

---

## Data Relationships

```
Complex (COMPLEX_ID_NUM)
  └── Platform Structure (AREA_CODE + BLOCK_NUMBER + STRUCTURE_NUMBER)
       └── Lease (LEASE_NUMBER)
            └── Wells (from existing well data)

Pipeline Permit (SEGMENT_NUM)
  └── Pipeline Location points (SEGMENT_NUM + POINT_NUM)
  └── Connected to Platform/Structure via AREA_CODE + BLOCK_NUMBER
```

### Join Keys

| From | To | Join Key |
|------|----|----------|
| Platform → Complex | Many-to-one | COMPLEX_ID_NUM |
| Platform → Lease | Many-to-one | LEASE_NUMBER |
| Platform → Wells | One-to-many | AREA_CODE + BLOCK_NUMBER + LEASE_NUMBER |
| Pipeline Permit → Location | One-to-many | SEGMENT_NUM |
| Pipeline → Block | Many-to-one | AREA_CODE + BLOCK_NUMBER |

---

## Available vs. Missing Engineering Data

### Available in BSEE Public Data

| Data Element | Source Dataset | Field |
|-------------|----------------|-------|
| Platform location | Platform Structures | LATITUDE, LONGITUDE |
| Water depth | Platform Structures | WATER_DEPTH |
| Structure type | Platform Structures | STRUC_TYPE_CODE |
| Installation date | Platform Structures | INSTALL_DATE |
| Well slot count | Platform Structures | SLOT_COUNT |
| Pipeline OD | Pipeline Permits | PPL_SIZE_CODE |
| Pipeline length | Pipeline Permits | SEG_LENGTH |
| Operating pressure | Pipeline Permits | MAOP_PRSS |
| Pipeline route | Pipeline Locations | LAT/LON points |
| Product type | Pipeline Permits | PROD_CODE |

### Known Gaps (Not in BSEE Public Data)

| Missing Data | Why It Matters | Potential Source |
|-------------|----------------|-----------------|
| Wall thickness | Pressure rating, corrosion assessment | BSEE scanned pipeline maps, FOIA requests |
| Inside Diameter (ID) | Flow capacity calculations | Calculate from OD + wall thickness |
| Material grade (X52, X65, etc.) | Strength analysis, remaining life | DNV reports, operator filings |
| Riser specifications | Critical path analysis | Not in BSEE public data; operator docs |
| Jumper details (rigid/flexible) | Subsea system design | Not tracked; subsea vendor data |
| Material strength (SMYS) | Pressure containment analysis | Derive from material grade |
| Coating/insulation type | Thermal/corrosion analysis | Not in BSEE; operator engineering docs |
| Platform structural dimensions | Structural integrity assessment | Not public; structural design reports |
| Subsea equipment specs | Manifolds, trees, connectors | BSEE eWell/permit data, operator filings |
| Fatigue life data | Remaining useful life | Operator inspection reports |
| Corrosion rates | Integrity management | Operator ILI/inspection data |

---

## CLI Usage

```bash
# Refresh individual infrastructure types
worldenergydata bsee refresh --type platform
worldenergydata bsee refresh --type pipeline_permit
worldenergydata bsee refresh --type deepwater_structure
worldenergydata bsee refresh --type pipeline_location

# Refresh all 4 infrastructure datasets
worldenergydata bsee refresh --type infrastructure

# Refresh everything (well + production + infrastructure)
worldenergydata bsee refresh --type all

# Force re-download even if data is current
worldenergydata bsee refresh --type platform --force
```

---

## Binary Output Files

After refresh, data is saved as pickle `.bin` files:

| Dataset | Output Path |
|---------|-------------|
| Platform Structures | `data/modules/bsee/bin/platform/` |
| Pipeline Permits | `data/modules/bsee/bin/pipeline_permit/` |
| Deepwater Structures | `data/modules/bsee/bin/deepwater_structure/` |
| Pipeline Locations | `data/modules/bsee/bin/pipeline_location/` |
