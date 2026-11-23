# Pacific (PAC) Data

> **Region Code**: PAC
> **Coordinate System**: NAD83
> **Coverage**: Southern, Central, Northern California Offshore
> **Primary Portal**: https://www.data.bsee.gov/

---

## Overview

The Pacific OCS Region covers California's offshore waters:
- **~1,000+ wells** drilled (historical)
- **23 platforms** installed (most now decommissioned)
- **Limited active production** (ongoing phase-out)
- **Oldest offshore operations** in the U.S. (since 1896)

---

## Geographic Coverage

### Planning Areas

| Area | Description | Activity Level |
|------|-------------|----------------|
| Southern | Los Angeles Basin offshore | Low (decommissioning) |
| Central | Point Conception to Monterey | Very Low |
| Northern | Monterey to Oregon border | None (no development) |

### BSEE District

| Code | Name | Coverage |
|------|------|----------|
| CAM | Camarillo | All Pacific OCS |

---

## Area/Protraction Codes

### Southern California Areas

| Code | Name | Typical Water Depth |
|------|------|---------------------|
| SB | Santa Barbara Channel | 100-1,500 ft |
| SM | Santa Maria Basin | 200-2,000 ft |
| SN | San Nicolas | 500-3,000 ft |
| SC | Santa Cruz Basin | 300-1,500 ft |
| SR | Santa Rosa-Cortes Ridge | 500-2,500 ft |
| SP | San Pedro Basin | 200-3,000 ft |
| SJ | San Juan Seamount | 2,000-4,000 ft |

### Central California Areas

| Code | Name | Typical Water Depth |
|------|------|---------------------|
| PA | Point Arguello | 200-1,500 ft |
| PC | Point Conception | 200-1,000 ft |
| MB | Monterey Bay | 500-3,000 ft |

### Complete Area Code List

| Code | Name |
|------|------|
| MB | Monterey Bay |
| PA | Point Arguello |
| PC | Point Conception |
| SB | Santa Barbara Channel |
| SC | Santa Cruz Basin |
| SJ | San Juan Seamount |
| SM | Santa Maria Basin |
| SN | San Nicolas |
| SP | San Pedro Basin |
| SR | Santa Rosa-Cortes Ridge |

---

## Coordinate System

### NAD83 (North American Datum of 1983)
- **EPSG Code**: 4269
- **Ellipsoid**: GRS 1980
- **Usage**: All PAC geographic coordinates

### Conversion from NAD27
```python
from pyproj import Transformer

# NAD27 to NAD83 (historical data conversion)
transformer = Transformer.from_crs("EPSG:4267", "EPSG:4269")
lat_83, lon_83 = transformer.transform(lat_27, lon_27)

# Shift varies: ~0.5 to 1.5 meters
```

### UTM Zones
| Zone | Coverage |
|------|----------|
| 10 | Northern California |
| 11 | Southern California |

---

## Data Availability

| Dataset | Records | Update Frequency |
|---------|---------|------------------|
| Wells | ~1,200 | Monthly |
| Platforms | 23 (total) | Monthly |
| Pipelines | ~50 segments | As reported |
| Production | ~500 monthly records | Bi-monthly |
| Leases | ~50 active | Monthly |

---

## Key Production Statistics

### Historical Production
| Decade | Cumulative Oil (BBL) | Cumulative Gas (MCF) |
|--------|----------------------|----------------------|
| 1960s | 50 million | 100 billion |
| 1970s | 200 million | 400 billion |
| 1980s | 500 million | 800 billion |
| 1990s | 800 million | 1 trillion |
| 2000s | 900 million | 1.1 trillion |
| 2010s | 950 million | 1.15 trillion |

### Current Activity
- **Active Platforms**: 3 (as of 2024)
- **Producing Wells**: ~50
- **Monthly Oil**: ~500,000 BBL
- **Monthly Gas**: ~500 million MCF

---

## Notable Platforms

### Historical and Operating Platforms

| Platform | Field | Water Depth | Status | Operator |
|----------|-------|-------------|--------|----------|
| Holly | South Ellwood | 211 ft | Decommissioned (2022) | DCOR |
| A | Dos Cuadras | 188 ft | Active | Sable Offshore |
| B | Dos Cuadras | 190 ft | Active | Sable Offshore |
| C | Dos Cuadras | 192 ft | Active | Sable Offshore |
| Gail | Point Arguello | 739 ft | Decommissioned | Freeport-McMoRan |
| Harvest | Point Arguello | 675 ft | Decommissioned | Freeport-McMoRan |
| Hermosa | Point Arguello | 603 ft | Decommissioned | Freeport-McMoRan |
| Hidalgo | Santa Ynez | 430 ft | Idle | Exxon |
| Heritage | Santa Ynez | 1,075 ft | Idle | Exxon |
| Harmony | Santa Ynez | 1,198 ft | Idle | Exxon |
| Hondo | Santa Ynez | 842 ft | Idle | Exxon |
| Grace | Santa Clara | 318 ft | Decommissioned | Venoco |
| Gilda | Santa Clara | 205 ft | Decommissioned | Venoco |
| Irene | Point Pedernales | 242 ft | Decommissioned | Freeport-McMoRan |

### Platform Categories
| Category | Range | Platform Count |
|----------|-------|----------------|
| Shallow | 0-500 ft | 15 |
| Intermediate | 500-1,000 ft | 6 |
| Deepwater | >1,000 ft | 2 |

---

## Regulatory Context

### Key Events
| Year | Event |
|------|-------|
| 1969 | Santa Barbara oil spill |
| 1981 | Moratorium begins |
| 1990 | OCS Lands Act amendments |
| 2010 | Obama extends moratorium |
| 2019 | California phase-out acceleration |
| 2022 | Platform Holly decommissioned |

### Current Restrictions
- No new leasing since 1984
- Federal moratorium on new drilling
- State waters ban (California Coastal Sanctuary Act)
- Ongoing decommissioning of legacy infrastructure

---

## Sample Queries

### All Pacific Wells
```
https://www.data.bsee.gov/Well/Borehole/Default.aspx
  ?Region=Pacific
```

### Production from Santa Barbara Channel
```
https://www.data.bsee.gov/Production/ProductionData/Default.aspx
  ?Region=Pacific
  &BottomArea=SB
  &ProductionMonthYearFrom=01/2024
```

### Platform Structures
```
https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
  ?Region=Pacific
```

---

## Related Documents

- [Region Index](index.md) - All regions overview
- [Gulf of America](gulf-of-america.md) - Primary BSEE region
- [Area Codes](../data-dictionaries/leasing/area-codes.md) - Complete area list
- [NAD Projections](../data-dictionaries/common/nad-projections.md) - Coordinate systems
- [Platform Fields](../data-dictionaries/platforms/structure-fields.md) - Platform data
