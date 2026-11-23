# Borehole Query Interface

> **URL**: https://www.data.bsee.gov/Well/Borehole/Default.aspx
> **Category**: Wells
> **Total Filters**: 10
> **Result Columns**: 27
> **Export Formats**: PDF, XLS, XLSX, RTF, CSV

---

## Overview

The Borehole query interface provides access to well and borehole data for the Outer Continental Shelf (OCS). This dataset contains information about all wells drilled on federal offshore leases, including location coordinates, depths, status, and operator information.

---

## Filter Options (10 Total)

| # | Filter | Type | Description | Values/Format |
|---|--------|------|-------------|---------------|
| 1 | Region | Dropdown | Geographic OCS region | Gulf of America, Alaska, Pacific, Atlantic |
| 2 | Bottom Area | Dropdown | Area/protraction code at bottomhole | AC, AT, DC, EB, EI, etc. (200+ codes) |
| 3 | Bottom Block | Dropdown | Block number at bottomhole | 001-999 (depends on area) |
| 4 | Bottom Lease Number | Text | Lease identifier at well TD | G00123 (1-10 chars) |
| 5 | API Number | Text | API well number | 10-digit or comma-separated list |
| 6 | Company Name | Dropdown | Current operator name | Type-ahead search enabled |
| 7 | Status Code | Dropdown | Current well status | APD, COM, PA, TA, DRL, etc. |
| 8 | Type Code | Dropdown | Well type classification | D, E, C, N, O, R, S |
| 9 | Water Depth | Range Slider | Water depth in feet | 0-12,000 ft (min/max) |
| 10 | Spud Date | Date Range | Date drilling commenced | MM/DD/YYYY format |

---

## Filter Descriptions

### Region
Select the OCS planning area:
- **Gulf of America** - Primary region (largest dataset)
- **Alaska** - Alaska OCS
- **Pacific** - Pacific coast
- **Atlantic** - Atlantic coast

### Bottom Area
Two-character area code where the well reaches total depth. Common codes:

| Code | Area Name | Water Depth |
|------|-----------|-------------|
| AC | Alaminos Canyon | Deep |
| AT | Atwater Valley | Deep |
| DC | DeSoto Canyon | Deep |
| EB | East Breaks | Deep |
| EI | Eugene Island | Shallow |
| GC | Garden Banks | Deep |
| GB | Green Canyon | Deep |
| MC | Mississippi Canyon | Deep/Ultra-deep |
| SS | Ship Shoal | Shallow |
| SP | South Pelto | Shallow |
| ST | South Timbalier | Shallow |
| VK | Viosca Knoll | Mixed |
| WC | West Cameron | Shallow |
| WR | Walker Ridge | Ultra-deep |

### Status Code
Current regulatory status of the well:

| Code | Status | Description |
|------|--------|-------------|
| APD | Application for Permit | Permit submitted, awaiting approval |
| AST | Approved Sidetrack | Sidetrack permit approved |
| CNL | Cancelled | Well permit cancelled |
| COM | Completed | Well completed (may be producing) |
| CT | Core Test | Core test well |
| DRL | Drilling | Currently drilling |
| DSI | Drilling Suspended | Rig on location, operations paused |
| PA | Permanently Abandoned | Well plugged and abandoned |
| ST | Sidetrack | Sidetrack operation |
| TA | Temporarily Abandoned | Temporarily plugged |
| VCW | Verified Complete | Work verified complete |

### Type Code
Well classification:

| Code | Type | Description |
|------|------|-------------|
| C | Core Test | Core sampling well |
| D | Development | Well in proven area |
| E | Exploratory | Wildcat/exploration well |
| N | New Well | Initial wellbore |
| O | Original Completion | First completion |
| R | Recompletion | Recompletion of existing well |
| S | Sidetrack | Sidetrack from existing bore |

---

## Result Columns (27 Total)

| # | Column | Type | Description | Example |
|---|--------|------|-------------|---------|
| 1 | API Well Number | VARCHAR(12) | Unique well ID (API12) | 177093400100 |
| 2 | Well Name | VARCHAR(50) | Operator-assigned name | THUNDER HAWK |
| 3 | Well Name Suffix | VARCHAR(10) | Additional identifier | A-1 |
| 4 | Bottom Lease Number | VARCHAR(10) | Lease at bottomhole | G00123 |
| 5 | Bottom Area | CHAR(2) | Area code at TD | AC |
| 6 | Bottom Block | VARCHAR(10) | Block at TD | 857 |
| 7 | Region | VARCHAR(20) | Geographic region | Gulf of America |
| 8 | Company Name | VARCHAR(100) | Current operator | Shell Offshore Inc. |
| 9 | Spud Date | DATE | Drilling start date | 01/15/2024 |
| 10 | BH Total MD (feet) | DECIMAL | Measured depth at TD | 25000.00 |
| 11 | True Vertical Depth (feet) | DECIMAL | TVD at TD | 18500.00 |
| 12 | TVD Subsea (feet) | DECIMAL | TVD below sea level | 18450.00 |
| 13 | RKB | DECIMAL | Rotary Kelly Bushing elev. | 85.00 |
| 14 | KOP | DECIMAL | Kick-off point depth | 5000.00 |
| 15 | Total Depth Date | DATE | Date TD reached | 03/20/2024 |
| 16 | Status Date | DATE | Date of current status | 04/15/2024 |
| 17 | Type Code | CHAR(1) | Well type | D |
| 18 | Status Code | CHAR(3) | Current status | COM |
| 19 | Casing Cut Code | CHAR(1) | Casing cut indicator | Y |
| 20 | Water Depth (feet) | DECIMAL | Water depth at location | 4500.00 |
| 21 | Underwater Comp Stub | CHAR(1) | Subsea completion flag | N |
| 22 | Surface Lease Number | VARCHAR(10) | Lease at surface | G00123 |
| 23 | Surface Latitude | DECIMAL | Surface latitude | 27.123456 |
| 24 | Surface Longitude | DECIMAL | Surface longitude | -89.654321 |
| 25 | Bottom Latitude | DECIMAL | Bottomhole latitude | 27.125000 |
| 26 | Bottom Longitude | DECIMAL | Bottomhole longitude | -89.650000 |
| 27 | (Additional fields vary) | - | Export may include more | - |

---

## Depth Reference Points

| Field | Reference | Notes |
|-------|-----------|-------|
| BH Total MD | RKB (Rotary Kelly Bushing) | Measured along wellbore path |
| True Vertical Depth | RKB | Vertical projection |
| TVD Subsea | Mean Sea Level | TVD minus RKB elevation |
| Water Depth | Sea Floor | Water column depth |

---

## Example Queries

### Query 1: Deepwater Completed Wells in Gulf of America
```
https://www.data.bsee.gov/Well/Borehole/Default.aspx
  ?Region=Gulf%20of%20America
  &WaterDepthMin=1000
  &WaterDepthMax=5000
  &StatusCode=COM
```
Returns all completed wells in 1,000-5,000 ft water depth.

### Query 2: Recent Exploratory Wells
```
https://www.data.bsee.gov/Well/Borehole/Default.aspx
  ?Region=Gulf%20of%20America
  &TypeCode=E
  &SpudDateFrom=01/01/2024
  &SpudDateTo=12/31/2024
```
Returns exploratory wells spud in 2024.

### Query 3: Specific API Number Lookup
```
https://www.data.bsee.gov/Well/Borehole/Default.aspx
  ?APINumber=1770934001
```
Returns single well by API number.

### Query 4: Multiple API Numbers
```
https://www.data.bsee.gov/Well/Borehole/Default.aspx
  ?APINumber=1770934001,1770934002,1770934003
```
Returns multiple wells (comma-separated).

### Query 5: Operator-Specific Query
```
https://www.data.bsee.gov/Well/Borehole/Default.aspx
  ?CompanyName=Shell%20Offshore%20Inc
  &StatusCode=PA
```
Returns all permanently abandoned Shell wells.

### Query 6: Area and Block Specific
```
https://www.data.bsee.gov/Well/Borehole/Default.aspx
  ?BottomArea=MC
  &BottomBlock=252
```
Returns all wells in Mississippi Canyon Block 252.

---

## URL Parameter Reference

| Parameter | URL Key | Format | Example |
|-----------|---------|--------|---------|
| Region | Region | URL-encoded | Gulf%20of%20America |
| Bottom Area | BottomArea | 2-char code | AC |
| Bottom Block | BottomBlock | Block number | 857 |
| Bottom Lease | BottomLeaseNumber | Lease ID | G00123 |
| API Number | APINumber | 10-digit or CSV | 1770934001 |
| Company Name | CompanyName | URL-encoded | Shell%20Offshore |
| Status Code | StatusCode | 2-3 char | COM |
| Type Code | TypeCode | 1 char | D |
| Water Depth Min | WaterDepthMin | Integer | 1000 |
| Water Depth Max | WaterDepthMax | Integer | 5000 |
| Spud Date From | SpudDateFrom | MM/DD/YYYY | 01/01/2024 |
| Spud Date To | SpudDateTo | MM/DD/YYYY | 12/31/2024 |

---

## Tips for Effective Searches

### Performance Tips
1. **Use at least one filter** - Unfiltered queries may timeout
2. **Limit date ranges** - Narrow to specific periods when possible
3. **Filter by area first** - Area selection significantly reduces results
4. **Use API numbers for specific wells** - Most efficient lookup method

### Data Quality Tips
1. **Check coordinate datums** - Gulf uses NAD27, other regions use NAD83
2. **Verify depth references** - MD and TVD have different reference points
3. **Note status dates** - Historical status changes not shown
4. **Cross-reference lease numbers** - Surface and bottom leases may differ

### Export Tips
1. **Use CSV for data processing** - Most compatible format
2. **Check row limits** - Large results may be truncated (~50,000 rows)
3. **Export incrementally** - Split large queries by date or area
4. **Verify column headers** - Export column order may vary

---

## Common Use Cases

| Use Case | Recommended Filters |
|----------|---------------------|
| Find wells in specific block | Area + Block |
| Operator activity analysis | Company Name + Date Range |
| Deepwater well inventory | Water Depth range + Status |
| Recent drilling activity | Spud Date range + Status=DRL |
| Abandoned well locations | Status=PA + Area |
| Specific well lookup | API Number |

---

## Related Documents

- [Borehole Fields](../data-dictionaries/wells/borehole-fields.md) - Field definitions
- [Status Codes](../data-dictionaries/wells/status-codes.md) - Complete status reference
- [Type Codes](../data-dictionaries/wells/type-codes.md) - Complete type reference
- [API Number Format](../data-dictionaries/common/api-number-format.md) - API numbering system
- [Export Formats](export-formats.md) - Export options and best practices
