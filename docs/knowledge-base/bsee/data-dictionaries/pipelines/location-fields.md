# Pipeline Location Fields

> **Dataset**: Pipeline Location
> **Source**: https://www.data.bsee.gov/Pipeline/PipelineLocation/Default.aspx
> **Raw Data**: https://www.data.bsee.gov/Pipeline/Files/PipeLocRawData.zip
> **Update Frequency**: As reported

---

## Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| Segment Number | Text | Pipeline segment ID (1-7 digits) | 1234567 |
| Last Revised Date | Date Range | Last modification date | 01/01/2024 - 12/31/2024 |
| Version Date | Date Range | Version timestamp | 01/01/2024 - 12/31/2024 |

**Note**: Segment Number is required to limit results due to dataset size.

---

## Result Fields (13 Columns)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Segment Number | VARCHAR(7) | Pipeline segment identifier | 1234567 |
| Point Sequence Number | INT | Sequential point in segment | 1 |
| Latitude | DECIMAL(10,6) | Geographic latitude | 27.123456 |
| Longitude | DECIMAL(11,6) | Geographic longitude | -89.654321 |
| NAD Year Code | CHAR(2) | Datum year (27 or 83) | 27 |
| Projection Code | VARCHAR(10) | Map projection system | UTM15 |
| X Coordinate Location | DECIMAL(15,6) | Projected X coordinate | 615000.000 |
| Y Coordinate Location | DECIMAL(15,6) | Projected Y coordinate | 3010000.000 |
| Last Revised Date | DATE | Most recent modification | 05/15/2024 |
| Version Date | DATETIME | Record version timestamp | 2024-05-15 14:30:00 |
| Asbuilt Flag | CHAR(1) | As-built status | Y |
| PPL Apurt Type | VARCHAR(10) | Pipeline appurtenance type | RISER |
| Bidirectional | CHAR(1) | Bi-directional flow | N |

---

## Field Definitions

### Segment Number
- Unique 7-digit identifier for each pipeline segment
- Format: Numeric string (leading zeros preserved)
- Example: "0012345"

### Point Sequence Number
- Sequential point within a segment
- Starts at 1 for first point
- Defines pipeline path from origin to terminus

### Coordinates
| Field | Description | Notes |
|-------|-------------|-------|
| Latitude | Geographic latitude | Decimal degrees, positive N |
| Longitude | Geographic longitude | Decimal degrees, negative W |
| X Coordinate | Projected easting | UTM zone dependent |
| Y Coordinate | Projected northing | UTM zone dependent |

### NAD Year Code
| Code | Description | Regions |
|------|-------------|---------|
| 27 | NAD27 datum | Gulf of America (primary) |
| 83 | NAD83 datum | Alaska, Pacific, Atlantic |

### PPL Appurtenance Types
| Code | Description |
|------|-------------|
| RISER | Riser connection |
| PLEM | Pipeline End Manifold |
| SDV | Shut-Down Valve |
| TEE | Pipeline tee connection |
| VALVE | Valve location |
| METER | Metering station |
| PIG | Pig launcher/receiver |

---

## Data Structure

Pipeline location data is stored as a series of coordinate points:

```
Segment 1234567:
  Point 1: (27.100, -89.500) - Origin
  Point 2: (27.150, -89.450)
  Point 3: (27.200, -89.400)
  ...
  Point N: (27.500, -89.100) - Terminus
```

Each segment represents one continuous pipeline from origin to terminus.

---

## Coordinate Systems

| Region | Datum | Projection | Zone |
|--------|-------|------------|------|
| Gulf of America | NAD27 | UTM | 14, 15, 16 |
| Alaska | NAD83 | UTM | Varies |
| Pacific | NAD83 | UTM | 10, 11 |
| Atlantic | NAD83 | UTM | 17, 18, 19 |

---

## Bidirectional Flag

| Value | Description |
|-------|-------------|
| Y | Pipeline can flow in both directions |
| N | Pipeline flows in one direction only |

---

## Asbuilt Flag

| Value | Description |
|-------|-------------|
| Y | Survey represents as-built condition |
| N | Survey represents permitted/planned route |

---

## Sample Query

```
https://www.data.bsee.gov/Pipeline/PipelineLocation/Default.aspx
  ?SegmentNumber=1234567
```

---

## GIS Integration

Pipeline location data can be converted to GIS formats:

1. **Point data**: Each record is a point feature
2. **Line data**: Connect points by Segment + Point Sequence
3. **Route data**: Order by Point Sequence within Segment

### Python Example
```python
import pandas as pd
from shapely.geometry import LineString

# Group points by segment, order by sequence
segments = df.groupby('Segment Number').apply(
    lambda x: LineString(
        x.sort_values('Point Sequence Number')[['Longitude', 'Latitude']].values
    )
)
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

- [Permit Fields](permit-fields.md) - Pipeline permit data
- [ROW Descriptions](row-descriptions.md) - Right-of-Way data
- [Product Codes](product-codes.md) - Pipeline product types
- [GIS Catalog](../../gis-catalog/index.md) - Pre-built pipeline shapefiles
