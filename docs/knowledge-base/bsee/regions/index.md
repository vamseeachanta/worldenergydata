# BSEE Regional Data Overview

> **Coverage**: Gulf of America, Alaska, Pacific, Atlantic
> **Primary Region**: Gulf of America (most comprehensive data)
> **Coordinate Systems**: NAD27 (GOA), NAD83 (Others)

---

## Quick Reference

| Region | Abbreviation | Portal | Coordinate System |
|--------|--------------|--------|-------------------|
| Gulf of America | GOA | [Default Portal](https://www.data.bsee.gov/) | NAD27 |
| Alaska | AK | [Alaska Portal](https://www.data.bsee.gov/Main/AlaskaWell.aspx) | NAD83 |
| Pacific | PAC | [Pacific Portal](https://www.data.bsee.gov/Main/PacificPlatform.aspx) | NAD83 |
| Atlantic | ATL | [Atlantic Portal](https://www.data.bsee.gov/Main/AtlanticWell.aspx) | NAD83 |

---

## Data Availability by Region

| Dataset | GOA | Alaska | Pacific | Atlantic |
|---------|:---:|:------:|:-------:|:--------:|
| Wells/Boreholes | Full | Full | Limited | Limited |
| Production | Full | Full | Limited | None |
| Platforms | Full | Limited | Full | None |
| Pipelines | Full | Limited | Limited | None |
| Leasing | Full | Full | Full | Full |
| GIS Data | Full | Partial | Partial | Partial |

---

## Gulf of America (Primary)

**Portal**: https://www.data.bsee.gov/ (default)

### Coverage
- Western Gulf (Texas)
- Central Gulf (Louisiana)
- Eastern Gulf (Florida/Alabama)

### Key Characteristics
- Most comprehensive data
- Highest well count (~50,000+)
- Most active production
- NAD27 coordinate system

### Area Codes
| Code | Name |
|------|------|
| AC | Alaminos Canyon |
| AT | Atwater Valley |
| DC | De Soto Canyon |
| EB | East Breaks |
| EW | Ewing Bank |
| GB | Garden Banks |
| GC | Green Canyon |
| KC | Keathley Canyon |
| MC | Mississippi Canyon |
| WR | Walker Ridge |
| (50+ more) | ... |

See [Gulf of America](gulf-of-america.md) for complete details.

---

## Alaska

**Portal**: https://www.data.bsee.gov/Main/AlaskaWell.aspx

### Coverage
- Beaufort Sea
- Chukchi Sea
- Cook Inlet

### Key Characteristics
- Arctic operations
- Seasonal drilling
- NAD83 coordinate system
- Fewer active wells

### Specific Data Portals
| Type | URL |
|------|-----|
| Wells | https://www.data.bsee.gov/Main/AlaskaWell.aspx |
| Leasing | https://www.data.bsee.gov/Main/AlaskaLeasing.aspx |
| Production | (Included in main production data) |

See [Alaska](alaska.md) for complete details.

---

## Pacific

**Portal**: https://www.data.bsee.gov/Main/PacificPlatform.aspx

### Coverage
- Southern California
- Central California
- Northern California

### Key Characteristics
- Established platforms
- Limited new development
- NAD83 coordinate system
- Environmental focus

### Specific Data Portals
| Type | URL |
|------|-----|
| Platforms | https://www.data.bsee.gov/Main/PacificPlatform.aspx |
| Pipelines | https://www.data.bsee.gov/Main/PacificPipeline.aspx |
| Production | (Included in main production data) |

See [Pacific](pacific.md) for complete details.

---

## Atlantic

**Portal**: Limited data available

### Coverage
- Atlantic OCS (limited activity)
- No current production

### Key Characteristics
- Exploration focus only
- Leasing data available
- NAD83 coordinate system
- Minimal infrastructure

### Specific Data Portals
| Type | URL |
|------|-----|
| Wells | https://www.data.bsee.gov/Main/AtlanticWell.aspx |
| Leasing | (Included in main leasing data) |

See [Atlantic](atlantic.md) for complete details.

---

## Coordinate System Notes

### NAD27 (Gulf of America)
- North American Datum of 1927
- Clarke 1866 ellipsoid
- Historical standard for GOA
- Must convert for modern GIS

### NAD83 (Alaska, Pacific, Atlantic)
- North American Datum of 1983
- GRS80 ellipsoid
- Current standard
- Compatible with WGS84

### Conversion
```python
# Example using pyproj
from pyproj import Transformer

# NAD27 to NAD83
transformer = Transformer.from_crs("EPSG:4267", "EPSG:4269")
lat_83, lon_83 = transformer.transform(lat_27, lon_27)
```

**Important**: Coordinate conversion is required when combining GOA data with other regions.

---

## API Well Number State Codes

| Region | Pseudo-State Code | Notes |
|--------|-------------------|-------|
| Gulf of America | 17 | Federal OCS |
| Alaska | 55 | Federal OCS |
| Pacific | 66 | Federal OCS |
| Atlantic | 77 | Federal OCS |

These are pseudo-codes, not actual state FIPS codes.

---

## Data Quality Notes

| Region | Data Completeness | Update Frequency | Notes |
|--------|-------------------|------------------|-------|
| GOA | Excellent | Daily | Most comprehensive |
| Alaska | Good | Weekly | Seasonal variations |
| Pacific | Good | Weekly | Stable, less change |
| Atlantic | Limited | As needed | Minimal activity |

---

## Regional Documentation

- [Gulf of America](gulf-of-america.md) - Primary region details
- [Alaska](alaska.md) - Alaska OCS specifics
- [Pacific](pacific.md) - Pacific OCS specifics
- [Atlantic](atlantic.md) - Atlantic OCS specifics

---

## Related Documents

- [Data Sources Index](../data-sources/index.md) - All URLs by region
- [NAD Projections](../data-dictionaries/common/nad-projections.md) - Coordinate details
- [GIS Catalog](../gis-catalog/index.md) - Regional GIS data
