# Atlantic (ATL) Data

> **Region Code**: ATL
> **Coordinate System**: NAD83
> **Coverage**: North, Mid, South Atlantic OCS
> **Primary Portal**: https://www.data.bsee.gov/Main/AtlanticWell.aspx

---

## Overview

The Atlantic OCS is an **exploration-only region** with:
- **~100 wells** drilled historically (1970s-1980s)
- **0 platforms** currently installed
- **0 active production**
- Limited data availability (primarily leasing and historical wells)

**Note**: Current federal moratoriums restrict most Atlantic drilling activity.

---

## Geographic Coverage

### Planning Areas

| Area | Description | Status |
|------|-------------|--------|
| North Atlantic | Maine to New Jersey | Moratorium |
| Mid-Atlantic | Delaware to North Carolina | Moratorium |
| South Atlantic | South Carolina to Florida | Moratorium |
| Straits of Florida | Southern tip of Florida | Moratorium |

### Coastal States (Adjacent)

| State | Adjacent Planning Area |
|-------|----------------------|
| Maine | North Atlantic |
| New Hampshire | North Atlantic |
| Massachusetts | North Atlantic |
| Rhode Island | North Atlantic |
| Connecticut | North Atlantic |
| New York | North Atlantic |
| New Jersey | North Atlantic |
| Delaware | Mid-Atlantic |
| Maryland | Mid-Atlantic |
| Virginia | Mid-Atlantic |
| North Carolina | Mid-Atlantic |
| South Carolina | South Atlantic |
| Georgia | South Atlantic |
| Florida (East) | South Atlantic |

---

## Area/Protraction Codes

### Atlantic Protraction Areas

| Code | Name | Planning Area |
|------|------|---------------|
| NJ18-01 | Hudson Canyon | North Atlantic |
| NJ18-02 | Long Island Sound | North Atlantic |
| NJ18-03 | Georges Bank | North Atlantic |
| VA18-01 | Norfolk Canyon | Mid-Atlantic |
| NC18-01 | Manteo | Mid-Atlantic |
| NC18-02 | Cape Hatteras | Mid-Atlantic |
| SC18-01 | Charleston | South Atlantic |
| GA18-01 | Savannah | South Atlantic |
| FL18-01 | Jacksonville | South Atlantic |
| FL18-02 | Straits of Florida | Straits of Florida |

### Block Numbering

| Format | Example | Notes |
|--------|---------|-------|
| OPD Grid | NJ18-01-3456 | Official Protraction Diagram |
| Block Size | 9 sq mi (3x3 nm) | Standard OCS block |

---

## Coordinate System

### NAD83 (North American Datum of 1983)
- **EPSG Code**: 4269
- **Ellipsoid**: GRS80
- **Usage**: All Atlantic geographic coordinates
- **Compatibility**: Near-identical to WGS84

### No Conversion Needed
```python
# Atlantic uses NAD83, compatible with WGS84
# No conversion typically required for modern GIS
lat_wgs84 = lat_nad83  # Effectively equivalent
lon_wgs84 = lon_nad83  # Differences < 2 meters
```

### UTM Zones

| Zone | Coverage |
|------|----------|
| 17 | Florida/Georgia |
| 18 | South Carolina to New Jersey |
| 19 | New York to Maine |

---

## Data Availability

| Dataset | Records | Status |
|---------|---------|--------|
| Wells | ~100 | Historical only |
| Platforms | 0 | None installed |
| Pipelines | 0 | None installed |
| Production | 0 | No production |
| Leases | Variable | Periodic sales |
| Seismic Permits | Limited | G&G data |

---

## Historical Exploration Activity

### Exploration Summary by Decade

| Period | Wells Drilled | Discoveries | Notes |
|--------|---------------|-------------|-------|
| 1970s | ~30 | 0 | Initial exploration |
| 1980s | ~70 | Minor shows | Peak activity |
| 1990s | 0 | - | Moratorium begins |
| 2000s | 0 | - | Continued moratorium |
| 2010s | 0 | - | Continued moratorium |
| 2020s | 0 | - | Continued moratorium |

### Notable Historical Wells

| Well | Year | Area | Result |
|------|------|------|--------|
| COST B-2 | 1976 | Baltimore Canyon | Dry hole (research) |
| COST B-3 | 1979 | Baltimore Canyon | Dry hole (research) |
| COST G-1 | 1976 | Georges Bank | Dry hole (research) |
| COST G-2 | 1977 | Georges Bank | Dry hole (research) |
| Shell Manteo | 1982 | Mid-Atlantic | Gas shows |

**Note**: COST = Continental Offshore Stratigraphic Test (research wells)

### Geological Basins

| Basin | Location | Potential |
|-------|----------|-----------|
| Baltimore Canyon Trough | Mid-Atlantic | Gas-prone |
| Georges Bank Basin | North Atlantic | Limited testing |
| Southeast Georgia Embayment | South Atlantic | Minimal data |
| Blake Plateau | South Atlantic | Deep, untested |

---

## Current Status

### Moratorium Areas

| Area | Moratorium Since | Current Status |
|------|------------------|----------------|
| North Atlantic | 1990 | Protected |
| Mid-Atlantic | 1990 | Protected |
| South Atlantic | 1990 | Protected |
| Straits of Florida | 2006 | Protected (GOMESA) |

### Regulatory Notes

- **Congressional Moratoriums**: Various since 1982
- **Presidential Withdrawals**: Multiple administrations
- **GOMESA (2006)**: Gulf of Mexico Energy Security Act protections
- **State Opposition**: Most coastal states oppose drilling

---

## Sample Queries

### Historical Atlantic Wells
```
https://www.data.bsee.gov/Main/AtlanticWell.aspx
  (Limited data - check for availability)
```

### Atlantic Leasing Information
```
https://www.boem.gov/oil-gas-energy/leasing/atlantic-ocs-region
  (BOEM handles Atlantic leasing data)
```

### Seismic Survey Data (G&G)
```
https://www.boem.gov/oil-gas-energy/resource-evaluation/
  atlantic-ocs-geological-and-geophysical-data
```

---

## Data Access Notes

### BSEE vs BOEM Data

| Data Type | Primary Source |
|-----------|----------------|
| Well Data | BSEE (historical) |
| Leasing Data | BOEM |
| G&G Permits | BOEM |
| Environmental | BOEM |

### API Number Format

| Component | Format | Example |
|-----------|--------|---------|
| Pseudo-State | 77 | Atlantic OCS |
| Area Code | 3 digits | 100-999 |
| Block | 5 digits | 00001-99999 |
| Well | 2 digits | 01-99 |
| Sidetrack | 2 digits | 00-99 |

**Example**: 77-100-00123-01-00

---

## Related Documents

- [Region Index](index.md) - All regions overview
- [Gulf of America](gulf-of-america.md) - Primary active region
- [Alaska](alaska.md) - Alaska OCS details
- [Pacific](pacific.md) - Pacific OCS details
- [NAD Projections](../data-dictionaries/common/nad-projections.md) - Coordinate systems
- [BOEM Atlantic Region](https://www.boem.gov/regions/atlantic-ocs-region) - Leasing authority
