# Block Numbering System

> **Usage**: OCS official leasing and mapping grid system
> **Authority**: Bureau of Ocean Energy Management (BOEM)
> **Basis**: UTM Protraction Diagram system

---

## Standard Block Dimensions

| Attribute | Value | Notes |
|-----------|-------|-------|
| Width | 3 statute miles | East-West |
| Height | 3 statute miles | North-South |
| Area | 5,760 acres | 9 square miles |
| Grid | UTM-based | Varies by region |

**Note**: Blocks at protraction boundaries may be irregular (partial blocks).

---

## Block Numbering by Region

### Gulf of America

| Pattern | Description | Example |
|---------|-------------|---------|
| 1-999 | Standard block numbers | MC 252 |
| A001-A999 | Supplemental blocks | GC A100 |
| Direction | South to North, West to East | — |
| Origin | Southwest corner of area | Block 1 |

**Gulf Numbering Grid**:
```
        West ←→ East

   North  | 7  8  9 |
    ↑     | 4  5  6 |
    ↓     | 1  2  3 |
   South  └─────────┘
          (Example 3x3)
```

### Alaska

| Pattern | Description | Example |
|---------|-------------|---------|
| 1-9999 | Standard block numbers | BF 0001 |
| Direction | Varies by planning area | — |
| Grid | NAD83 UTM zones | Zones 1-6 |

### Pacific

| Pattern | Description | Example |
|---------|-------------|---------|
| 1-999 | Standard block numbers | SM 500 |
| Direction | South to North, West to East | — |
| Grid | NAD83 UTM zones | Zones 10-11 |

---

## Sub-Block Designations

### Quarter Blocks (1,440 acres each)

| Code | Position | Description |
|------|----------|-------------|
| NE/4 | Northeast | Upper right quarter |
| NW/4 | Northwest | Upper left quarter |
| SE/4 | Southeast | Lower right quarter |
| SW/4 | Southwest | Lower left quarter |

### Half Blocks (2,880 acres each)

| Code | Position | Description |
|------|----------|-------------|
| N/2 | North | Top half |
| S/2 | South | Bottom half |
| E/2 | East | Right half |
| W/2 | West | Left half |

### Visual Reference

```
┌─────────┬─────────┐
│   NW/4  │   NE/4  │
│ (1,440) │ (1,440) │
├─────────┼─────────┤
│   SW/4  │   SE/4  │
│ (1,440) │ (1,440) │
└─────────┴─────────┘
   Full Block = 5,760 acres
```

---

## Aliquot Descriptions

### Common Patterns

| Description | Acreage | Meaning |
|-------------|---------|---------|
| All | 5,760 | Entire block |
| N/2 | 2,880 | North half |
| NE/4 | 1,440 | Northeast quarter |
| NW/4 NE/4 | 720 | Northwest quarter of NE quarter |
| N/2 NW/4 | 720 | North half of NW quarter |
| S/2 S/2 | 1,440 | South half of south half |

### Sixteenth Blocks (360 acres each)

| Example | Description |
|---------|-------------|
| NE/4 NE/4 | Northeast quarter of northeast quarter |
| SW/4 NW/4 | Southwest quarter of northwest quarter |
| SE/4 SE/4 | Southeast quarter of southeast quarter |

---

## Block Reference Format

### Standard Format
```
[Area Code] [Block Number]
Example: MC 252
```

### With Aliquot
```
[Area Code] [Block Number] [Aliquot]
Example: GC 640 NE/4
```

### Full Lease Reference
```
[Lease Number] / [Area] / [Block] / [Region]
Example: G33203 / MC / 252 / Gulf of America
```

---

## Protraction Diagrams

### Structure
Each protraction area contains:

| Component | Count | Notes |
|-----------|-------|-------|
| Official Map | 1 | BOEM published |
| Blocks | 50-500+ | Varies by area size |
| Boundaries | Defined | Lat/Long coordinates |

### Naming Convention
```
OPD (Official Protraction Diagram)
Example: Mississippi Canyon OPD
```

---

## Block Corner Coordinates

### Data Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| NW Corner Lat | DECIMAL(10,6) | Northwest latitude | 28.123456 |
| NW Corner Lon | DECIMAL(11,6) | Northwest longitude | -89.654321 |
| NE Corner Lat | DECIMAL(10,6) | Northeast latitude | 28.123456 |
| NE Corner Lon | DECIMAL(11,6) | Northeast longitude | -89.610987 |
| SE Corner Lat | DECIMAL(10,6) | Southeast latitude | 28.080123 |
| SE Corner Lon | DECIMAL(11,6) | Southeast longitude | -89.610987 |
| SW Corner Lat | DECIMAL(10,6) | Southwest latitude | 28.080123 |
| SW Corner Lon | DECIMAL(11,6) | Southwest longitude | -89.654321 |

### Centroid
```
Block Center = Average of 4 corners
Used for distance calculations
```

---

## Special Block Types

| Type | Description | Example |
|------|-------------|---------|
| Partial Block | <5,760 acres at boundary | Edge of protraction |
| Irregular Block | Non-rectangular | Coastal areas |
| Excluded Block | Within area but not leased | Environmental exclusion |
| Split Block | Divided by state/federal line | 3-mile boundary |

---

## Block Queries

### By Block Number
```
?Block=252
?BlockMin=200&BlockMax=300
```

### By Area and Block
```
?Area=Mississippi%20Canyon&Block=252
?BottomArea=MC&BottomBlock=252
```

### Block Range Search
```
?BlockStart=200&BlockEnd=299  (Blocks 200-299)
```

---

## GIS Block Data

### Available Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| Shapefile | .shp | Standard GIS |
| Geodatabase | .gdb | ESRI format |
| GeoJSON | .json | Web mapping |
| KML | .kml | Google Earth |

### Download Source
```
https://www.boem.gov/oil-gas-energy/mapping-and-data
```

---

## Examples

### Famous Block References

| Location | Description |
|----------|-------------|
| MC 252 | Macondo well / Deepwater Horizon |
| GC 640 | Perdido development hub |
| WR 718 | Jack/St. Malo development |
| GB 426 | Auger TLP platform |
| VK 826 | Mars platform |
| MC 807 | Thunder Horse platform |

### Block Calculations

| Calculation | Formula | Example |
|-------------|---------|---------|
| Full blocks | Count × 5,760 | 4 blocks = 23,040 acres |
| Half blocks | Count × 2,880 | 2 halves = 5,760 acres |
| Quarters | Count × 1,440 | 3 quarters = 4,320 acres |

---

## Related Documents

- [Lease Fields](lease-fields.md) - Lease data dictionary
- [Area Codes](area-codes.md) - Protraction area codes
- [Region Codes](../common/region-codes.md) - Region definitions
- [GIS Catalog](../../gis-catalog/index.md) - Block shapefiles
