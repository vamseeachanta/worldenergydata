# Gulf of America (GOA) Data

> **Region Code**: GOA
> **Coordinate System**: NAD27
> **Coverage**: Western, Central, Eastern Gulf
> **Primary Portal**: https://www.data.bsee.gov/ (default)

---

## Overview

The Gulf of America is the primary BSEE data region with:
- **50,000+ wells** drilled
- **3,000+ platforms** installed
- **10,000+ pipeline segments**
- Most comprehensive and current data

---

## Geographic Coverage

### Planning Areas

| Area | Description | Activity Level |
|------|-------------|----------------|
| Western | Texas offshore | High |
| Central | Louisiana offshore | Very High |
| Eastern | Florida/Alabama offshore | Limited |

### BSEE Districts

| Code | Name | State |
|------|------|-------|
| HO | Houma | Louisiana |
| LF | Lafayette | Louisiana |
| LK | Lake Charles | Louisiana |
| NW | New Orleans West | Louisiana |
| SS | Corpus Christi | Texas |

---

## Area/Protraction Codes

### Major Deepwater Areas

| Code | Name | Typical Water Depth |
|------|------|---------------------|
| AC | Alaminos Canyon | 5,000-10,000 ft |
| AT | Atwater Valley | 4,000-8,000 ft |
| DC | De Soto Canyon | 4,000-7,000 ft |
| GC | Green Canyon | 1,500-8,000 ft |
| KC | Keathley Canyon | 6,000-10,000 ft |
| LL | Lloyd Ridge | 7,000-9,000 ft |
| MC | Mississippi Canyon | 1,500-8,000 ft |
| WR | Walker Ridge | 7,000-10,000 ft |

### Shelf Areas

| Code | Name | Typical Water Depth |
|------|------|---------------------|
| EB | East Breaks | 500-3,000 ft |
| EW | Ewing Bank | 500-3,000 ft |
| GB | Garden Banks | 500-5,000 ft |
| HI | High Island | <500 ft |
| MP | Main Pass | <500 ft |
| SL | South Marsh Island | <500 ft |
| SS | Ship Shoal | <500 ft |
| ST | South Timbalier | <500 ft |
| VK | Viosca Knoll | 500-3,000 ft |
| WC | West Cameron | <500 ft |
| WD | West Delta | <500 ft |

### Complete Area Code List (50+)

| Code | Name |
|------|------|
| AC | Alaminos Canyon |
| AM | Amery Terrace |
| AT | Atwater Valley |
| BA | Brazos Area |
| BM | Bryant Canyon |
| BS | Block South |
| BU | Buccanner |
| CA | Chandeleur Area |
| CB | Charlotte Bay |
| CC | Coffin Canyon |
| CG | Clipper Gulch |
| CS | Charlotte Subdivision |
| DC | De Soto Canyon |
| DS | De Soto South |
| EB | East Breaks |
| EC | East Cameron |
| EI | Eugene Island |
| EW | Ewing Bank |
| GA | Galveston Area |
| GB | Garden Banks |
| GC | Green Canyon |
| GI | Grand Isle |
| HE | Henderson |
| HI | High Island |
| KC | Keathley Canyon |
| LL | Lloyd Ridge |
| MC | Mississippi Canyon |
| MI | Matagorda Island |
| MP | Main Pass |
| MT | Mitchell |
| MU | Mustang Island |
| PE | Perdido |
| PI | Port Isabel |
| PL | Pulley Ridge |
| PN | Pensacola |
| PS | Port South |
| SA | Santa Anna |
| SL | South Marsh Island |
| SM | South Pelto |
| SO | Sigsbee Overlay |
| SP | South Pass |
| SS | Ship Shoal |
| ST | South Timbalier |
| TA | Tanner |
| UA | Ussa |
| VK | Viosca Knoll |
| VR | Vermilion |
| WC | West Cameron |
| WD | West Delta |
| WR | Walker Ridge |

---

## Coordinate System

### NAD27 (North American Datum of 1927)
- **EPSG Code**: 4267
- **Ellipsoid**: Clarke 1866
- **Usage**: All GOA geographic coordinates

### Conversion to NAD83
```python
from pyproj import Transformer

# NAD27 to NAD83
transformer = Transformer.from_crs("EPSG:4267", "EPSG:4269")
lat_83, lon_83 = transformer.transform(lat_27, lon_27)

# Approximate shift: ~0.00002 to 0.00005 degrees
```

### UTM Zones
| Zone | Coverage |
|------|----------|
| 14 | Far western Texas |
| 15 | Texas/Louisiana border |
| 16 | Louisiana/Alabama/Florida |

---

## Data Availability

| Dataset | Records | Update Frequency |
|---------|---------|------------------|
| Wells | ~50,000 | Daily |
| Platforms | ~3,000 | Monthly |
| Pipelines | ~10,000 segments | As reported |
| Production | ~300,000 monthly records | Bi-monthly |
| Leases | ~5,000 active | Monthly |

---

## Key Production Statistics

### Historical Production
| Decade | Cumulative Oil (BBL) | Cumulative Gas (MCF) |
|--------|----------------------|----------------------|
| 1950s | 500 million | 2 trillion |
| 1960s | 2.5 billion | 10 trillion |
| 1970s | 5 billion | 25 trillion |
| 1980s | 7 billion | 40 trillion |
| 1990s | 8 billion | 55 trillion |
| 2000s | 10 billion | 65 trillion |
| 2010s | 12 billion | 70 trillion |

### Current Activity
- **Active Platforms**: ~2,000
- **Producing Wells**: ~3,500
- **Monthly Oil**: ~50 million BBL
- **Monthly Gas**: ~200 billion MCF

---

## Deepwater Development

### Water Depth Categories
| Category | Range | Platform Count |
|----------|-------|----------------|
| Shallow | 0-500 ft | ~2,000 |
| Intermediate | 500-1,000 ft | ~400 |
| Deepwater | 1,000-5,000 ft | ~200 |
| Ultra-Deepwater | >5,000 ft | ~50 |

### Notable Deepwater Fields
| Field | Area | Water Depth | Type |
|-------|------|-------------|------|
| Thunder Horse | MC | 6,050 ft | Semi |
| Atlantis | GC | 7,070 ft | Semi |
| Perdido | AC | 8,000 ft | Spar |
| Mad Dog | GC | 4,500 ft | Spar |
| Na Kika | MC | 6,340 ft | Semi |

---

## Sample Queries

### Deepwater Wells in Green Canyon
```
https://www.data.bsee.gov/Well/Borehole/Default.aspx
  ?Region=Gulf%20of%20America
  &BottomArea=GC
  &WaterDepthMin=1000
```

### Production from Central Gulf
```
https://www.data.bsee.gov/Production/ProductionData/Default.aspx
  ?LeaseNumber=G*
  &ProductionMonthYearFrom=01/2024
```

---

## Related Documents

- [Region Index](index.md) - All regions overview
- [Area Codes](../data-dictionaries/leasing/area-codes.md) - Complete area list
- [NAD Projections](../data-dictionaries/common/nad-projections.md) - Coordinate systems
- [Platform Fields](../data-dictionaries/platforms/structure-fields.md) - Platform data
