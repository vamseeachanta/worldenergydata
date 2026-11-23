# Region Codes

> **Usage**: Identifies geographic region for OCS data
> **Scope**: Federal Outer Continental Shelf regions

---

## Region Reference

| Code | Region | Abbreviation | Coordinate System |
|------|--------|--------------|-------------------|
| GOA | Gulf of America | Gulf | NAD27 |
| PAC | Pacific | Pac | NAD83 |
| AK | Alaska | AK | NAD83 |
| ATL | Atlantic | Atl | NAD83 |

---

## Detailed Descriptions

### Gulf of America (GOA)
- **Coverage**: Texas to Florida offshore
- **Sub-regions**: Western, Central, Eastern
- **Activity**: Most active, highest production
- **Wells**: ~50,000+
- **Coordinate System**: NAD27
- **API State Code**: 17

### Pacific (PAC)
- **Coverage**: California offshore
- **Sub-regions**: Southern, Central, Northern
- **Activity**: Limited, established operations
- **Wells**: ~1,000+
- **Coordinate System**: NAD83
- **API State Code**: 66

### Alaska (AK)
- **Coverage**: Beaufort Sea, Chukchi Sea, Cook Inlet
- **Sub-regions**: Beaufort, Chukchi, Cook Inlet
- **Activity**: Seasonal, Arctic conditions
- **Wells**: ~500+
- **Coordinate System**: NAD83
- **API State Code**: 55

### Atlantic (ATL)
- **Coverage**: East Coast offshore
- **Sub-regions**: North, Mid, South Atlantic
- **Activity**: Exploration only, no current production
- **Wells**: ~100 (historical)
- **Coordinate System**: NAD83
- **API State Code**: 77

---

## API Well Number State Codes

| Region | Pseudo-State Code | Example API |
|--------|-------------------|-------------|
| Gulf of America | 17 | 177093400100 |
| Alaska | 55 | 557000100100 |
| Pacific | 66 | 667000100100 |
| Atlantic | 77 | 777000100100 |

**Note**: These are pseudo-state codes for federal OCS, not actual state FIPS codes.

---

## Regional Data Portals

| Region | Primary Portal |
|--------|----------------|
| GOA | https://www.data.bsee.gov/ (default) |
| Alaska | https://www.data.bsee.gov/Main/AlaskaWell.aspx |
| Pacific | https://www.data.bsee.gov/Main/PacificPlatform.aspx |
| Atlantic | https://www.data.bsee.gov/Main/AtlanticWell.aspx |

---

## Data Availability by Region

| Dataset | GOA | Alaska | Pacific | Atlantic |
|---------|:---:|:------:|:-------:|:--------:|
| Wells | Full | Full | Limited | Limited |
| Production | Full | Full | Limited | None |
| Platforms | Full | Limited | Full | None |
| Pipelines | Full | Limited | Limited | None |
| Leasing | Full | Full | Full | Full |
| GIS Data | Full | Partial | Partial | Partial |

---

## Region Filter in Queries

Most BSEE query interfaces include a Region filter:

### Dropdown Options
- Gulf of America
- Alaska
- Pacific
- Atlantic

### Query String
```
?Region=Gulf%20of%20America
?Region=Alaska
?Region=Pacific
?Region=Atlantic
```

---

## Coordinate System by Region

| Region | Datum | EPSG | Transform to WGS84 |
|--------|-------|------|-------------------|
| GOA | NAD27 | 4267 | Required |
| Alaska | NAD83 | 4269 | Minimal |
| Pacific | NAD83 | 4269 | Minimal |
| Atlantic | NAD83 | 4269 | Minimal |

### Conversion Notes
- NAD27 → NAD83: Shift of ~10-50 meters
- NAD83 ≈ WGS84: Sub-meter difference
- Always verify coordinate system before analysis

---

## Related Documents

- [Region Index](../../regions/index.md) - Regional overview
- [Gulf of America](../../regions/gulf-of-america.md) - GOA details
- [NAD Projections](nad-projections.md) - Coordinate systems
- [API Number Format](api-number-format.md) - State codes
