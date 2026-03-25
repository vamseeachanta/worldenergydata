# NAD Projections & Coordinate Systems

> **Usage**: Geographic coordinate handling for BSEE data
> **Primary Systems**: NAD27, NAD83, WGS84
> **Critical**: GOA uses NAD27; all other regions use NAD83

---

## Quick Reference

| Region | Datum | EPSG | Ellipsoid | Transform to WGS84 |
|--------|-------|------|-----------|-------------------|
| Gulf of America | NAD27 | 4267 | Clarke 1866 | Required (~10-50m shift) |
| Alaska | NAD83 | 4269 | GRS80 | Minimal (<1m) |
| Pacific | NAD83 | 4269 | GRS80 | Minimal (<1m) |
| Atlantic | NAD83 | 4269 | GRS80 | Minimal (<1m) |

---

## NAD27 (Gulf of America)

### Specification

| Property | Value |
|----------|-------|
| EPSG Code | 4267 |
| Ellipsoid | Clarke 1866 |
| Semi-major axis | 6,378,206.4 m |
| Flattening | 1/294.9786982 |
| Origin | Meades Ranch, Kansas |
| Usage | GOA wells, platforms, pipelines |

### UTM Zones for GOA

| Zone | Coverage | Central Meridian |
|------|----------|------------------|
| 14N | Western GOA (Texas) | -99° |
| 15N | Central-West GOA | -93° |
| 16N | Central GOA (Louisiana) | -87° |
| 17N | Eastern GOA (Alabama, Florida) | -81° |

### EPSG Codes (NAD27 UTM)

| Zone | EPSG |
|------|------|
| UTM 14N | 26714 |
| UTM 15N | 26715 |
| UTM 16N | 26716 |
| UTM 17N | 26717 |

---

## NAD83 (Alaska, Pacific, Atlantic)

### Specification

| Property | Value |
|----------|-------|
| EPSG Code | 4269 |
| Ellipsoid | GRS80 |
| Semi-major axis | 6,378,137.0 m |
| Flattening | 1/298.257222101 |
| Origin | Earth center of mass |
| Usage | AK, PAC, ATL regions |

### UTM Zones by Region

| Region | Zones | Coverage |
|--------|-------|----------|
| Alaska | 1N-9N | Aleutians to Beaufort |
| Pacific | 10N-11N | California offshore |
| Atlantic | 17N-19N | East Coast |

### EPSG Codes (NAD83 UTM)

| Zone | EPSG | Region |
|------|------|--------|
| UTM 5N | 26905 | Alaska (Chukchi) |
| UTM 6N | 26906 | Alaska (Beaufort) |
| UTM 10N | 26910 | Pacific |
| UTM 11N | 26911 | Pacific |
| UTM 17N | 26917 | Atlantic |
| UTM 18N | 26918 | Atlantic |

---

## NAD27 to NAD83 Conversion

### Shift Magnitude

| Area | Latitude Shift | Longitude Shift | Total |
|------|---------------|-----------------|-------|
| Western GOA | ~25m N | ~15m E | ~30m |
| Central GOA | ~30m N | ~20m E | ~36m |
| Eastern GOA | ~35m N | ~25m E | ~43m |

### Transformation Methods

| Method | Accuracy | Use Case |
|--------|----------|----------|
| NADCON | Sub-meter | US Continental Shelf |
| Molodensky | 5-10m | Quick approximation |
| 7-parameter | 1-2m | Regional accuracy |

### NADCON Grid Files

| File | Coverage |
|------|----------|
| conus.las/los | Continental US + GOA |
| alaska.las/los | Alaska region |
| hawaii.las/los | Hawaii (not OCS) |

---

## Python Code Examples

### Using pyproj

```python
from pyproj import CRS, Transformer

# Define coordinate systems
nad27 = CRS.from_epsg(4267)  # NAD27 (GOA)
nad83 = CRS.from_epsg(4269)  # NAD83
wgs84 = CRS.from_epsg(4326)  # WGS84

# NAD27 to WGS84 (GOA data)
transformer_27_84 = Transformer.from_crs(
    nad27, wgs84, always_xy=True
)

# NAD83 to WGS84 (Alaska, Pacific, Atlantic)
transformer_83_84 = Transformer.from_crs(
    nad83, wgs84, always_xy=True
)

def convert_coordinates(lon, lat, source_datum='NAD27'):
    """Convert BSEE coordinates to WGS84."""
    if source_datum == 'NAD27':
        return transformer_27_84.transform(lon, lat)
    else:  # NAD83
        return transformer_83_84.transform(lon, lat)

# Example: GOA well location
lon_nad27, lat_nad27 = -90.5, 28.5
lon_wgs84, lat_wgs84 = convert_coordinates(lon_nad27, lat_nad27, 'NAD27')
# Shift: approximately 30m northeast
```

### Batch Conversion

```python
import pandas as pd
from pyproj import Transformer

def convert_bsee_coordinates(df, lon_col, lat_col, region_col):
    """Convert BSEE data coordinates based on region."""
    transformer_27 = Transformer.from_crs(4267, 4326, always_xy=True)
    transformer_83 = Transformer.from_crs(4269, 4326, always_xy=True)

    def convert_row(row):
        if row[region_col] == 'GOA':
            return transformer_27.transform(row[lon_col], row[lat_col])
        else:
            return transformer_83.transform(row[lon_col], row[lat_col])

    results = df.apply(convert_row, axis=1)
    df['lon_wgs84'] = [r[0] for r in results]
    df['lat_wgs84'] = [r[1] for r in results]
    return df
```

---

## Accuracy Considerations

| Issue | Impact | Mitigation |
|-------|--------|------------|
| Wrong datum assumption | 10-50m error | Check region, apply correct transform |
| Missing NADCON grids | 5-10m error | Install proj-data package |
| UTM zone boundaries | Edge distortion | Use lat/lon for cross-zone analysis |
| Vertical datum mixing | Variable | Separate horizontal/vertical transforms |

### Common Errors

1. **Assuming all BSEE data is NAD27**
   - Only GOA uses NAD27
   - Alaska, Pacific, Atlantic use NAD83

2. **Treating NAD83 as WGS84**
   - Difference is sub-meter but exists
   - For high-precision work, transform explicitly

3. **Ignoring coordinate order**
   - BSEE: typically (longitude, latitude)
   - Some GIS: (latitude, longitude)
   - Always verify with pyproj `always_xy=True`

---

## Verification

### Test Points

| Location | NAD27 (lon, lat) | WGS84 (lon, lat) | Shift |
|----------|------------------|------------------|-------|
| GOA Central | -90.000, 28.000 | -89.9997, 28.0003 | ~35m |
| GOA Western | -95.000, 27.500 | -94.9998, 27.5003 | ~30m |

### Validation Query

```sql
-- Check for coordinate outliers (likely datum issues)
SELECT api_number, surface_longitude, surface_latitude
FROM wells
WHERE surface_latitude NOT BETWEEN 25 AND 32  -- GOA bounds
   OR surface_longitude NOT BETWEEN -98 AND -80;
```

---

## Related Documents

- [Region Codes](region-codes.md) - Regional datum assignments
- [Borehole Fields](../wells/borehole-fields.md) - Coordinate fields
- [Structure Fields](../platforms/structure-fields.md) - Platform coordinates
