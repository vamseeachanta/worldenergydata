# Alaska (AK) Data

> **Region Code**: AK
> **Coordinate System**: NAD83
> **Coverage**: Beaufort Sea, Chukchi Sea, Cook Inlet
> **Primary Portal**: https://www.data.bsee.gov/Main/AlaskaWell.aspx

---

## Overview

Alaska OCS is a specialized BSEE data region with:
- **500+ wells** drilled (exploration and development)
- **~25 platforms** installed (primarily Cook Inlet)
- **Seasonal drilling operations** (Arctic areas)
- Separate data portal from Gulf of America

---

## Geographic Coverage

### Planning Areas

| Area | Description | Activity Level |
|------|-------------|----------------|
| Beaufort Sea | North Slope offshore | Moderate |
| Chukchi Sea | Northwest Alaska offshore | Limited |
| Cook Inlet | South-central Alaska | Moderate |
| Gulf of Alaska | Southeast offshore | Minimal |
| Norton Basin | Western Alaska | Minimal |

### BSEE Districts

| Code | Name | Coverage |
|------|------|----------|
| AK | Alaska Regional Office | All Alaska OCS |
| - | Anchorage | Primary operations center |

---

## Area/Protraction Codes

### Beaufort Sea Areas

| Code | Name | Typical Water Depth |
|------|------|---------------------|
| BF | Beaufort Sea | 50-200 ft |
| CA | Camden Bay | 50-150 ft |
| FL | Flaxman Island | 30-100 ft |
| HA | Harrison Bay | 20-80 ft |
| LI | Liberty | 20-50 ft |
| NP | Northstar | 30-60 ft |
| SD | Stump Island | 20-50 ft |

### Chukchi Sea Areas

| Code | Name | Typical Water Depth |
|------|------|---------------------|
| CH | Chukchi Sea | 100-200 ft |
| BU | Burger | 130-150 ft |
| KL | Klondike | 100-140 ft |
| PP | Popcorn | 100-130 ft |

### Cook Inlet Areas

| Code | Name | Typical Water Depth |
|------|------|---------------------|
| CI | Cook Inlet | 50-600 ft |
| KB | Kenai Block | 100-300 ft |
| TB | Trading Bay | 50-150 ft |
| GC | Granite Point | 50-100 ft |
| MC | McArthur River | 50-100 ft |

### Complete Area Code List

| Code | Name | Region |
|------|------|--------|
| BF | Beaufort Sea | Beaufort |
| CA | Camden Bay | Beaufort |
| CH | Chukchi Sea | Chukchi |
| CI | Cook Inlet | Cook Inlet |
| FL | Flaxman Island | Beaufort |
| GA | Gulf of Alaska | Gulf |
| HA | Harrison Bay | Beaufort |
| KB | Kenai Block | Cook Inlet |
| KL | Klondike | Chukchi |
| NB | Norton Basin | Norton |
| NP | Northstar | Beaufort |
| PP | Popcorn | Chukchi |
| TB | Trading Bay | Cook Inlet |

---

## Coordinate System

### NAD83 (North American Datum of 1983)
- **EPSG Code**: 4269
- **Ellipsoid**: GRS80
- **Usage**: All Alaska geographic coordinates

### Alaska-Specific Projections

| Projection | EPSG | Coverage |
|------------|------|----------|
| Alaska Albers | 3338 | Statewide |
| UTM Zone 3N | 32603 | Aleutians |
| UTM Zone 4N | 32604 | Western Alaska |
| UTM Zone 5N | 32605 | Cook Inlet |
| UTM Zone 6N | 32606 | Beaufort Sea |
| UTM Zone 7N | 32607 | Eastern Beaufort |

### Coordinate Handling
```python
from pyproj import Transformer

# WGS84 to Alaska Albers
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3338")
x, y = transformer.transform(lat, lon)

# NAD83 is compatible with WGS84 for most purposes
```

---

## Data Availability

| Dataset | Records | Update Frequency |
|---------|---------|------------------|
| Wells | ~500 | Weekly |
| Platforms | ~25 | Monthly |
| Pipelines | ~50 segments | As reported |
| Production | ~2,000 monthly records | Bi-monthly |
| Leases | ~200 active | Monthly |

---

## Key Production Statistics

### Historical Production

| Decade | Cumulative Oil (BBL) | Cumulative Gas (MCF) |
|--------|----------------------|----------------------|
| 1960s | 5 million | 20 billion |
| 1970s | 50 million | 100 billion |
| 1980s | 150 million | 300 billion |
| 1990s | 200 million | 400 billion |
| 2000s | 100 million | 200 billion |
| 2010s | 50 million | 100 billion |

### Current Activity
- **Active Platforms**: ~15 (primarily Cook Inlet)
- **Producing Wells**: ~50
- **Monthly Oil**: ~500,000 BBL
- **Monthly Gas**: ~5 billion MCF

---

## Operational Characteristics

### Seasonal Constraints

| Season | Activity | Notes |
|--------|----------|-------|
| Winter (Oct-May) | Ice operations | Beaufort/Chukchi drilling window |
| Summer (Jun-Sep) | Open water | Logistics, marine operations |
| Year-round | Cook Inlet | Less ice impact |

### Arctic-Specific Considerations
- Ice-resistant platform designs
- Environmental monitoring requirements
- Subsistence hunting coordination
- Limited infrastructure access

---

## Notable Fields/Prospects

| Field | Area | Water Depth | Status | Type |
|-------|------|-------------|--------|------|
| Northstar | BF | 39 ft | Producing | Gravel island |
| Liberty | BF | 22 ft | Development | Drill site |
| Oooguruk | BF | 5-10 ft | Producing | Gravel island |
| Nikaitchuq | BF | 5-10 ft | Producing | Extended reach |
| Granite Point | CI | 100 ft | Producing | Platform |
| Trading Bay | CI | 80 ft | Producing | Platform |

---

## Sample Queries

### Alaska Wells by Area
```
https://www.data.bsee.gov/Main/AlaskaWell.aspx
  ?AreaCode=BF
  &WellStatus=Active
```

### Alaska Leasing Data
```
https://www.data.bsee.gov/Main/AlaskaLeasing.aspx
  ?PlanningArea=Beaufort%20Sea
  &LeaseStatus=Active
```

### Alaska Production (via main portal)
```
https://www.data.bsee.gov/Production/ProductionData/Default.aspx
  ?Region=Alaska
  &ProductionMonthYearFrom=01/2024
```

---

## Specific Data Portals

| Data Type | Portal URL |
|-----------|------------|
| Wells | https://www.data.bsee.gov/Main/AlaskaWell.aspx |
| Leasing | https://www.data.bsee.gov/Main/AlaskaLeasing.aspx |
| Production | https://www.data.bsee.gov/Production/ProductionData/Default.aspx |
| GIS Data | https://www.data.boem.gov/Main/Mapping.aspx |

---

## Related Documents

- [Region Index](index.md) - All regions overview
- [Area Codes](../data-dictionaries/leasing/area-codes.md) - Complete area list
- [NAD Projections](../data-dictionaries/common/nad-projections.md) - Coordinate systems
- [API Well Numbers](../data-dictionaries/wells/api-well-number.md) - Alaska pseudo-state code 55
- [Well Status Codes](../data-dictionaries/wells/well-status-codes.md) - Status definitions
