# Platform Structures Query Interface

> **URL**: https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
> **Category**: Platforms
> **Total Filters**: 13
> **Result Columns**: 28
> **Export Formats**: PDF, XLS, XLSX, RTF, CSV

---

## Overview

The Platform Structures query interface provides access to offshore platform and structure data for the Outer Continental Shelf (OCS). This dataset includes fixed platforms, caissons, floating production systems, subsea installations, and other offshore infrastructure. It tracks installation dates, removal status, site clearance, and operational details.

---

## Filter Options (13 Total)

| # | Filter | Type | Description | Values/Format |
|---|--------|------|-------------|---------------|
| 1 | Area | Dropdown | Geographic area/protraction code | AC, AT, GC, MC, etc. (200+ codes) |
| 2 | Block Number | Text | Block identifier | 001-999 |
| 3 | Lease Number | Text | Associated lease | G00123 |
| 4 | Field | Dropdown | Oil/gas field name | Type-ahead search |
| 5 | Complex ID Number | Text | Complex identifier | Numeric ID |
| 6 | Structure Name | Text | Platform designation | A, B, C, or full name |
| 7 | Company Name | Dropdown | Operating company | Type-ahead search |
| 8 | Water Depth (feet) | Range Slider | Depth range | 0-10,000 ft |
| 9 | Structure Installation Date | Date Range | Installation date | MM/DD/YYYY |
| 10 | Structure Removal Date | Date Range | Removal date | MM/DD/YYYY |
| 11 | Site Clearance Date | Date Range | Site clearance date | MM/DD/YYYY |
| 12 | List Non-Removed Structures | Checkbox | Active structures only | Checked/Unchecked |
| 13 | List Non-Site Clearance | Checkbox | Not yet cleared | Checked/Unchecked |

---

## Filter Descriptions

### Area
Two-character protraction/area code. Common codes:

| Code | Area Name | Typical Depth | Structure Types |
|------|-----------|---------------|-----------------|
| AC | Alaminos Canyon | Deep | Subsea, SPAR |
| AT | Atwater Valley | Deep | Subsea, TLP |
| EI | Eugene Island | Shallow | Fixed, Caisson |
| GC | Garden Banks | Deep | TLP, SPAR, Subsea |
| GB | Green Canyon | Deep | TLP, SPAR, FPSO |
| HI | High Island | Shallow | Fixed, Caisson |
| MC | Mississippi Canyon | Mixed | All types |
| MP | Main Pass | Shallow | Fixed, Caisson |
| SM | South Marsh Island | Shallow | Fixed |
| SS | Ship Shoal | Shallow | Fixed, Caisson |
| SP | South Pelto | Shallow | Fixed |
| ST | South Timbalier | Shallow | Fixed |
| VK | Viosca Knoll | Mixed | Fixed, Subsea |
| WC | West Cameron | Shallow | Fixed |
| WD | West Delta | Shallow | Fixed |
| WR | Walker Ridge | Ultra-deep | Subsea, SPAR |

### Block Number
- Numeric block within the selected area
- Range depends on area (typically 001-999)
- Some areas have alphanumeric blocks (e.g., 123A)

### Field
- Oil/gas field name
- Dropdown with type-ahead search
- Examples: THUNDER HORSE, MARS, URSA, NA KIKA

### Complex ID Number
- Unique identifier for related structure groups
- Multiple platforms may share one Complex ID
- Links structures to common production facilities

### Structure Name
- Platform designation (often single letter: A, B, C)
- May include full names for major structures
- Case insensitive search

### Checkbox Filters

| Filter | When Checked | When Unchecked |
|--------|--------------|----------------|
| List Non-Removed Structures | Shows only active structures | Shows all (including removed) |
| List Non-Site Clearance | Shows structures not yet cleared | Shows all clearance statuses |

**Typical combinations:**
- Both checked: Active platforms only
- Unchecked + Unchecked: All structures including removed
- Removal Date filter: Historical decommissioning analysis

---

## Result Columns (28 Total)

| # | Column | Type | Description | Example |
|---|--------|------|-------------|---------|
| 1 | Area Code | CHAR(2) | Area/protraction code | MC |
| 2 | Block Number | VARCHAR(10) | Block identifier | 252 |
| 3 | Field | VARCHAR(50) | Oil/gas field name | THUNDER HORSE |
| 4 | Structure Name | VARCHAR(20) | Platform designation | A |
| 5 | Structure Number | VARCHAR(10) | Sequence number | 001 |
| 6 | Structure Type Code | VARCHAR(5) | Type of structure | FIXED |
| 7 | Authority Type | VARCHAR(10) | Regulatory authority | DPP |
| 8 | Authority Number | VARCHAR(20) | Permit number | G12345 |
| 9 | Authority Status | VARCHAR(20) | Current status | APPROVED |
| 10 | Business Name | VARCHAR(100) | Current operator | Shell Offshore Inc. |
| 11 | Complex ID Number | INT | Complex identifier | 12345 |
| 12 | Major Structure Flag | CHAR(1) | Major structure (Y/N) | Y |
| 13 | Installation Date | DATE | Structure installed | 05/15/2010 |
| 14 | Removal Date | DATE | Structure removed | (null if active) |
| 15 | Site Clearance Date | DATE | Site cleared | (null if not) |
| 16 | District Code | CHAR(2) | BSEE district | HO |
| 17 | Heliport Flag | CHAR(1) | Has heliport (Y/N) | Y |
| 18 | Lease Number | VARCHAR(10) | Associated lease | G00123 |
| 19 | Water Depth | DECIMAL | Depth in feet | 4500.00 |
| 20 | Incidents of Non-Compliance | INT | INC count | 0 |
| 21 | Latitude | DECIMAL | Platform latitude | 27.123456 |
| 22 | Longitude | DECIMAL | Platform longitude | -89.654321 |
| 23 | NAD Year Code | CHAR(2) | Datum year | 27 |
| 24 | Projection Code | VARCHAR(10) | Map projection | UTM15 |
| 25 | Platform X Location | DECIMAL | Projected X | 615000.000 |
| 26 | Platform Y Location | DECIMAL | Projected Y | 3010000.000 |
| 27 | Surface N-S Distance | DECIMAL | N-S offset | 1500.00 |
| 28 | Surface N-S Code | CHAR(1) | N or S | N |
| 29 | Surface E-W Distance | DECIMAL | E-W offset | 2000.00 |
| 30 | Surface E-W Code | CHAR(1) | E or W | W |
| 31 | Attended 8-Hour Staffing | CHAR(1) | 8-hr staffing | Y |
| 32 | Manned 24-Hour Staffing | CHAR(1) | 24-hr staffing | Y |

---

## Structure Type Codes

| Code | Description | Water Depth | Notes |
|------|-------------|-------------|-------|
| FIXED | Fixed Platform | 0-1,500 ft | Traditional jacket structure |
| CAIS | Caisson | 0-500 ft | Single-pile caisson |
| WP | Well Protector | 0-500 ft | Minimal protection structure |
| SPAR | SPAR Platform | 2,000-10,000 ft | Deepwater floating |
| TLP | Tension Leg Platform | 1,500-5,000 ft | Deepwater floating |
| SEMI | Semi-Submersible | 3,000-10,000 ft | Deepwater floating |
| FPSO | Floating Production | 2,000-10,000 ft | Production/storage |
| SS | Subsea System | All depths | Subsea infrastructure |
| MOPU | Mobile Production | Varies | Mobile unit |
| CT | Compliant Tower | 1,000-3,000 ft | Deepwater fixed |
| MINSTRUC | Minor Structure | All | Small structures |

---

## District Codes

| Code | District | State | Coverage |
|------|----------|-------|----------|
| HO | Houma | Louisiana | Central GoM |
| LF | Lafayette | Louisiana | Western Louisiana |
| LK | Lake Charles | Louisiana | Western GoM |
| NW | New Orleans West | Louisiana | Eastern Louisiana |
| SS | Corpus Christi | Texas | Texas coast |

---

## Example Queries

### Query 1: Active Deepwater Platforms
```
https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
  ?WaterDepthMin=1000
  &WaterDepthMax=10000
  &ListNonRemovedStructures=true
```
Returns all active structures in >1,000 ft water depth.

### Query 2: Specific Area and Block
```
https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
  ?Area=MC
  &BlockNumber=252
  &ListNonRemovedStructures=true
```
Returns active platforms in Mississippi Canyon Block 252.

### Query 3: Structures Installed in Date Range
```
https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
  ?InstallationDateFrom=01/01/2020
  &InstallationDateTo=12/31/2024
```
Returns all structures installed 2020-2024.

### Query 4: Recently Removed Structures
```
https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
  ?RemovalDateFrom=01/01/2023
  &RemovalDateTo=12/31/2024
```
Returns structures removed in 2023-2024.

### Query 5: Operator-Specific Inventory
```
https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
  ?CompanyName=Shell%20Offshore%20Inc
  &ListNonRemovedStructures=true
```
Returns all active Shell structures.

### Query 6: Specific Field
```
https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
  ?Field=THUNDER%20HORSE
  &ListNonRemovedStructures=true
```
Returns all active Thunder Horse structures.

### Query 7: Pending Site Clearance
```
https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
  ?RemovalDateFrom=01/01/2010
  &RemovalDateTo=12/31/2020
  &ListNonSiteClearance=true
```
Returns removed structures not yet cleared.

---

## URL Parameter Reference

| Parameter | URL Key | Format | Example |
|-----------|---------|--------|---------|
| Area | Area | 2-char code | MC |
| Block Number | BlockNumber | Numeric | 252 |
| Lease Number | LeaseNumber | Lease ID | G00123 |
| Field | Field | URL-encoded | THUNDER%20HORSE |
| Complex ID | ComplexIDNumber | Integer | 12345 |
| Structure Name | StructureName | Text | A |
| Company Name | CompanyName | URL-encoded | Shell%20Offshore |
| Water Depth Min | WaterDepthMin | Integer (ft) | 1000 |
| Water Depth Max | WaterDepthMax | Integer (ft) | 5000 |
| Install Date From | InstallationDateFrom | MM/DD/YYYY | 01/01/2020 |
| Install Date To | InstallationDateTo | MM/DD/YYYY | 12/31/2024 |
| Removal Date From | RemovalDateFrom | MM/DD/YYYY | 01/01/2020 |
| Removal Date To | RemovalDateTo | MM/DD/YYYY | 12/31/2024 |
| Clearance Date From | SiteClearanceDateFrom | MM/DD/YYYY | 01/01/2020 |
| Clearance Date To | SiteClearanceDateTo | MM/DD/YYYY | 12/31/2024 |
| Non-Removed | ListNonRemovedStructures | true/false | true |
| Non-Cleared | ListNonSiteClearance | true/false | true |

---

## Checkbox Filter Logic

### List Non-Removed Structures

| Value | Result |
|-------|--------|
| true (checked) | Only structures with NULL Removal Date |
| false (unchecked) | All structures regardless of removal status |

### List Non-Site Clearance

| Value | Result |
|-------|--------|
| true (checked) | Only structures with NULL Site Clearance Date |
| false (unchecked) | All structures regardless of clearance status |

### Combined Filter Effects

| Non-Removed | Non-Cleared | Result |
|-------------|-------------|--------|
| true | true | Active structures only |
| true | false | Active structures (cleared or not) |
| false | true | All, but not cleared yet |
| false | false | All structures including removed/cleared |

---

## Water Depth Categories

| Category | Depth Range | Typical Structure Types |
|----------|-------------|------------------------|
| Shallow | 0-500 ft | Fixed, Caisson, WP |
| Transitional | 500-1,000 ft | Fixed, Caisson |
| Deepwater | 1,000-5,000 ft | SPAR, TLP, CT, Subsea |
| Ultra-Deepwater | >5,000 ft | SPAR, SEMI, FPSO, Subsea |

---

## Tips for Effective Searches

### Performance Tips
1. **Use checkbox filters** - Significantly reduces result set
2. **Filter by area first** - Most efficient approach
3. **Specify water depth range** - Limits to relevant structure types
4. **Use Complex ID** - For related structure groups

### Data Quality Tips
1. **Check coordinates** - NAD27 datum for Gulf
2. **Verify removal dates** - NULL means still installed
3. **Review structure type** - Affects regulatory requirements
4. **Note INC count** - Historical compliance indicator

### Analysis Tips
1. **Group by Complex ID** - Analyze related structures together
2. **Track installation trends** - Date range queries
3. **Decommissioning analysis** - Removal vs clearance dates
4. **Staffing assessment** - 8-hr vs 24-hr flags

---

## Common Use Cases

| Use Case | Recommended Filters |
|----------|---------------------|
| Active platform inventory | ListNonRemovedStructures=true |
| Decommissioning candidates | Removal Date range + Non-Cleared |
| Deepwater infrastructure | Water Depth >1000 ft |
| Operator portfolio | Company Name + Non-Removed |
| Field development review | Field name + Non-Removed |
| Historical installations | Installation Date range |
| Compliance review | Area + Non-Removed (check INC count) |

---

## Related Documents

- [Platform Structure Fields](../data-dictionaries/platforms/structure-fields.md) - Field definitions
- [Structure Type Codes](../data-dictionaries/platforms/structure-types.md) - Complete type reference
- [Authority Codes](../data-dictionaries/platforms/authority-codes.md) - Regulatory authorities
- [Export Formats](export-formats.md) - Export options and best practices
- [Deepwater Structures](../data-sources/deepwater-structures.md) - Deepwater-specific data
