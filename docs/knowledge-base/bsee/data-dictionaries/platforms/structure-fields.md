# Platform Structure Fields

> **Dataset**: Platform Structures
> **Source**: https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
> **Raw Data**: https://www.data.bsee.gov/Platform/Files/PlatStrucRawData.zip
> **Update Frequency**: As reported

---

## Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| Area | Dropdown | Geographic area code | AC (Alaminos Canyon) |
| Block Number | Text | Block identifier | 857 |
| Lease Number | Text | Lease identifier | G00123 |
| Field | Dropdown | Oil/gas field name | THUNDER HAWK |
| Complex ID Number | Text | Complex identifier | 12345 |
| Structure Name | Text | Platform/structure name | A |
| Company Name | Dropdown | Operating company | Shell Offshore |
| Water Depth (feet) | Range | Depth range (0-10,000) | 1000-5000 |
| Structure Installation Date | Date Range | Installation date range | 01/01/2000 - 12/31/2025 |
| Structure Removal Date | Date Range | Removal date range | (empty = not removed) |
| Site Clearance Date | Date Range | Site clearance date range | (empty = not cleared) |
| List Non-Removed Structures | Checkbox | Filter active only | Checked |
| List Non-Site Clearance | Checkbox | Filter not cleared | Checked |

---

## Result Fields (28 Columns)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Area Code | CHAR(2) | Area/protraction code | AC |
| Block Number | VARCHAR(10) | Block identifier | 857 |
| Field | VARCHAR(50) | Oil/gas field name | THUNDER HAWK |
| Structure Name | VARCHAR(20) | Platform designation | A |
| Structure Number | VARCHAR(10) | Structure sequence number | 001 |
| Structure Type Code | VARCHAR(5) | Type of structure | FIXED |
| Authority Type | VARCHAR(10) | Regulatory authority | MMS |
| Authority Number | VARCHAR(20) | Authority permit number | G12345 |
| Authority Status | VARCHAR(20) | Current authority status | APPROVED |
| Business Name | VARCHAR(100) | Current operator | Shell Offshore Inc. |
| Complex ID Number | INT | Complex identifier | 12345 |
| Major Structure Flag | CHAR(1) | Major structure indicator | Y |
| Installation Date | DATE | Structure installation date | 05/15/2010 |
| Removal Date | DATE | Structure removal date | (null if active) |
| Site Clearance Date | DATE | Site clearance date | (null if not cleared) |
| District Code | CHAR(2) | BSEE district | HO |
| Heliport Flag | CHAR(1) | Has heliport | Y |
| Lease Number | VARCHAR(10) | Associated lease | G00123 |
| Water Depth | DECIMAL(8,2) | Water depth in feet | 4500.00 |
| Incidents of Non-Compliance | INT | INC count | 0 |
| Latitude | DECIMAL(10,6) | Platform latitude | 27.123456 |
| Longitude | DECIMAL(11,6) | Platform longitude | -89.654321 |
| NAD Year Code | CHAR(2) | Datum year (27/83) | 27 |
| Projection Code | VARCHAR(10) | Map projection | UTM15 |
| Platform X Location | DECIMAL(15,6) | Projected X coordinate | 615000.000 |
| Platform Y Location | DECIMAL(15,6) | Projected Y coordinate | 3010000.000 |
| Surface N-S Distance | DECIMAL(10,2) | N-S offset from block center | 1500.00 |
| Surface N-S Code | CHAR(1) | N or S direction | N |
| Surface E-W Distance | DECIMAL(10,2) | E-W offset from block center | 2000.00 |
| Surface E-W Code | CHAR(1) | E or W direction | W |
| Attended 8-Hour Staffing | CHAR(1) | 8-hour staffing | Y |
| Manned 24-Hour Staffing | CHAR(1) | 24-hour staffing | Y |

---

## Structure Type Codes

| Code | Description | Notes |
|------|-------------|-------|
| FIXED | Fixed Platform | Traditional jacket structure |
| CAIS | Caisson | Single-pile caisson |
| WP | Well Protector | Minimal structure for well protection |
| SPAR | SPAR Platform | Deepwater floating |
| TLP | Tension Leg Platform | Deepwater floating |
| SEMI | Semi-Submersible | Deepwater floating |
| FPSO | Floating Production Storage | Deepwater floating |
| SS | Subsea System | Subsea infrastructure |
| MOPU | Mobile Offshore Production Unit | Mobile unit |
| CT | Compliant Tower | Deepwater fixed |

---

## Authority Types

| Code | Description |
|------|-------------|
| APD | Application for Permit to Drill |
| APM | Application for Permit to Modify |
| DPP | Development and Production Plan |
| DOCD | Development Operations Coordination Document |
| EP | Exploration Plan |
| ROW | Right of Way |
| RUE | Right of Use and Easement |

---

## District Codes

| Code | District | Location |
|------|----------|----------|
| HO | Houma | Louisiana |
| LF | Lafayette | Louisiana |
| LK | Lake Charles | Louisiana |
| NW | New Orleans West | Louisiana |
| SS | Corpus Christi | Texas |

---

## Water Depth Categories

| Category | Depth Range | Notes |
|----------|-------------|-------|
| Shallow | 0-500 ft | Most structures |
| Intermediate | 500-1,000 ft | Transitional |
| Deepwater | 1,000-5,000 ft | Deepwater threshold |
| Ultra-Deepwater | >5,000 ft | Extreme depth |

---

## Complex ID

- Unique identifier for a group of related structures
- Multiple platforms may share one Complex ID
- Used to associate production with infrastructure

---

## Location Reference

| Field | Reference | Notes |
|-------|-----------|-------|
| Latitude/Longitude | Geodetic | NAD27 or NAD83 depending on region |
| X/Y Coordinates | Projected | UTM zone coordinates |
| N-S/E-W Distance | Block Center | Offset from block center |

---

## Sample Query

```
https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
  ?Area=AC
  &WaterDepthMin=1000
  &WaterDepthMax=5000
  &ListNonRemovedStructures=true
```

---

## Export Formats

Available export options:
- PDF
- XLS (Excel 2003)
- XLSX (Excel 2007+)
- RTF (Rich Text)
- CSV (Comma-separated)

---

## Related Documents

- [Deepwater Structures](deepwater-structures.md) - Deepwater (>1000ft)
- [Authority Codes](authority-codes.md) - Complete authority reference
- [Structure Types](structure-types.md) - Complete type reference
- [Offshore Stats](offshore-stats.md) - Statistics by water depth
