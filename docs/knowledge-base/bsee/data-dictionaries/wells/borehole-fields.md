# Borehole Data Fields

> **Dataset**: Borehole
> **Source**: https://www.data.bsee.gov/Well/Borehole/Default.aspx
> **Raw Data**: https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip
> **Total Records**: ~57,334 (as of 2026-01-18)
> **Update Frequency**: Daily

---

## Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| Region | Dropdown | Geographic region | Gulf of America |
| Bottom Area | Dropdown | Area/protraction code | AC (Alaminos Canyon) |
| Bottom Block | Dropdown | Block number | 001-999 |
| Bottom Lease Number | Text | Lease identifier | G00123 |
| API Number | Text | API well number (comma-separated OK) | 1770934001 |
| Company Name | Dropdown | Operator name | Shell Offshore |
| Status Code | Dropdown | Well status | COM, PA, TA |
| Type Code | Dropdown | Well type | D (Development) |
| Water Depth | Range | Depth range (0-12,000 ft) | 1000-5000 |
| Spud Date | Date Range | Start date range | 01/01/2020 - 12/31/2025 |

---

## Result Fields (27 Columns)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| API Well Number | VARCHAR(12) | Unique well identifier (API12 format) | 177093400100 |
| Well Name | VARCHAR(50) | Well name assigned by operator | THUNDER HAWK |
| Well Name Suffix | VARCHAR(10) | Additional well identifier | A-1 |
| Bottom Lease Number | VARCHAR(10) | Lease at well bottomhole | G00123 |
| Bottom Area | CHAR(2) | Area code at bottomhole | AC |
| Bottom Block | VARCHAR(10) | Block at bottomhole | 857 |
| Region | VARCHAR(20) | Geographic region | Gulf of America |
| Company Name | VARCHAR(100) | Current operator name | Shell Offshore Inc. |
| Spud Date | DATE | Date drilling began | 01/15/2024 |
| BH Total MD (feet) | DECIMAL(10,2) | Bottomhole measured depth | 25000.00 |
| True Vertical Depth (feet) | DECIMAL(10,2) | True vertical depth | 18500.00 |
| TVD Subsea (feet) | DECIMAL(10,2) | TVD below sea level | 18450.00 |
| RKB | DECIMAL(8,2) | Rotary Kelly Bushing elevation | 85.00 |
| KOP | DECIMAL(10,2) | Kick-off point depth | 5000.00 |
| Total Depth Date | DATE | Date TD reached | 03/20/2024 |
| Status Date | DATE | Date of current status | 04/15/2024 |
| Type Code | CHAR(1) | Well type classification | D |
| Status Code | CHAR(3) | Current well status | COM |
| Casing Cut Code | CHAR(1) | Casing cut indicator | Y |
| Water Depth (feet) | DECIMAL(8,2) | Water depth at location | 4500.00 |
| Underwater Comp Stub | CHAR(1) | Subsea completion indicator | N |
| Surface Lease Number | VARCHAR(10) | Lease at surface location | G00123 |
| Surface Latitude | DECIMAL(10,6) | Surface location latitude | 27.123456 |
| Surface Longitude | DECIMAL(11,6) | Surface location longitude | -89.654321 |
| Bottom Latitude | DECIMAL(10,6) | Bottomhole latitude | 27.125000 |
| Bottom Longitude | DECIMAL(11,6) | Bottomhole longitude | -89.650000 |

---

## Status Codes

| Code | Description | Notes |
|------|-------------|-------|
| APD | Application for Permit to Drill | Permit submitted, not yet approved |
| AST | Approved Sidetrack | Sidetrack approved |
| CNL | Cancelled | Permit/well cancelled |
| COM | Borehole Completed | Well completed, may be producing |
| CT | Core Test | Core test well |
| DRL | Drilling | Currently drilling |
| DSI | Drilling Suspended - Rig on Location | Rig still on location |
| PA | Permanently Abandoned | Well plugged and abandoned |
| ST | Sidetrack | Sidetrack operation |
| TA | Temporarily Abandoned | Temporarily plugged |
| VCW | Verified Completion of Work | Work verified complete |

---

## Type Codes

| Code | Description | Notes |
|------|-------------|-------|
| C | Core Test | Core sampling well |
| D | Development | Development well in proven area |
| E | Exploratory | Exploratory/wildcat well |
| N | New Well | New well (initial bore) |
| O | Original Completion | Original completion |
| R | Recompletion | Recompletion of existing well |
| S | Sidetrack | Sidetrack from existing wellbore |

---

## Coordinate System Notes

| Region | Datum | Notes |
|--------|-------|-------|
| Gulf of America | NAD27 | Primary region, most wells |
| Alaska | NAD83 | Alaska OCS |
| Pacific | NAD83 | Pacific OCS |
| Atlantic | NAD83 | Atlantic OCS |

**Important**: Coordinates must be converted when combining data from different regions.

---

## Depth Reference

| Field | Reference Point | Notes |
|-------|-----------------|-------|
| BH Total MD | RKB | Measured along wellbore path |
| True Vertical Depth | RKB | Vertical projection |
| TVD Subsea | Mean Sea Level | TVD minus RKB elevation |
| Water Depth | Sea Floor | Water column depth |

---

## Sample Query URL

```
https://www.data.bsee.gov/Well/Borehole/Default.aspx
  ?Region=Gulf%20of%20America
  &WaterDepthMin=1000
  &WaterDepthMax=5000
  &StatusCode=COM
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

- [Status Codes](status-codes.md) - Complete status code reference
- [Type Codes](type-codes.md) - Complete type code reference
- [API Number Format](../common/api-number-format.md) - API numbering system
- [APD Fields](apd-fields.md) - Application for Permit to Drill fields
