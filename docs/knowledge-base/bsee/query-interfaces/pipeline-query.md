# Pipeline Location Query Interface

> **URL**: https://www.data.bsee.gov/Pipeline/PipelineLocation/Default.aspx
> **Category**: Pipelines
> **Total Filters**: 3
> **Result Columns**: 13
> **Export Formats**: PDF, XLS, XLSX, RTF, CSV

---

## Overview

The Pipeline Location query interface provides access to pipeline segment location data for the Outer Continental Shelf (OCS). Each pipeline segment is stored as a series of coordinate points defining the route from origin to terminus. This dataset is essential for GIS mapping, route analysis, and infrastructure planning.

**Important**: Segment Number is required to return results due to the large dataset size.

---

## Filter Options (3 Total)

| # | Filter | Type | Required | Description | Format |
|---|--------|------|----------|-------------|--------|
| 1 | Segment Number | Text | **Yes** | Pipeline segment identifier | 1-7 digits |
| 2 | Last Revised Date | Date Range | No | Last modification date range | MM/DD/YYYY |
| 3 | Version Date | Date Range | No | Record version timestamp | MM/DD/YYYY |

---

## Filter Descriptions

### Segment Number (Required)

The Segment Number is the primary identifier for pipeline segments. This filter is **required** to return results.

| Attribute | Description |
|-----------|-------------|
| Format | 1-7 digit numeric string |
| Leading Zeros | Preserved (e.g., "0012345") |
| Multiple Values | Not supported (single segment only) |
| Wildcards | Not supported |

**Finding Segment Numbers:**
- Use [Pipeline Permits](https://www.data.bsee.gov/Pipeline/PipelinePermits/Default.aspx) query to find segment numbers
- Reference permit documents
- Use raw data download for bulk segment lookup

### Last Revised Date

Filter by the most recent modification date of the segment location data.

| Attribute | Description |
|-----------|-------------|
| Format | MM/DD/YYYY |
| From | Start of date range |
| To | End of date range |
| Empty | Returns all dates |

**Use cases:**
- Find recently modified segments
- Track route changes over time
- Identify updated as-built surveys

### Version Date

Filter by the record version timestamp.

| Attribute | Description |
|-----------|-------------|
| Format | MM/DD/YYYY |
| From | Start of date range |
| To | End of date range |
| Empty | Returns all versions |

**Use cases:**
- Retrieve specific historical versions
- Track data update history
- Audit trail analysis

---

## Result Columns (13 Total)

| # | Column | Type | Description | Example |
|---|--------|------|-------------|---------|
| 1 | Segment Number | VARCHAR(7) | Pipeline segment ID | 1234567 |
| 2 | Point Sequence Number | INT | Sequential point in segment | 1 |
| 3 | Latitude | DECIMAL(10,6) | Geographic latitude | 27.123456 |
| 4 | Longitude | DECIMAL(11,6) | Geographic longitude | -89.654321 |
| 5 | NAD Year Code | CHAR(2) | Datum year (27 or 83) | 27 |
| 6 | Projection Code | VARCHAR(10) | Map projection system | UTM15 |
| 7 | X Coordinate Location | DECIMAL(15,6) | Projected X (easting) | 615000.000 |
| 8 | Y Coordinate Location | DECIMAL(15,6) | Projected Y (northing) | 3010000.000 |
| 9 | Last Revised Date | DATE | Most recent modification | 05/15/2024 |
| 10 | Version Date | DATETIME | Record version timestamp | 2024-05-15 14:30:00 |
| 11 | Asbuilt Flag | CHAR(1) | As-built status (Y/N) | Y |
| 12 | PPL Apurt Type | VARCHAR(10) | Appurtenance type | RISER |
| 13 | Bidirectional | CHAR(1) | Bi-directional flow (Y/N) | N |

---

## Field Definitions

### Point Sequence Number

Points are numbered sequentially along the pipeline route:
- Point 1 = Origin (start of segment)
- Point N = Terminus (end of segment)
- Intermediate points define the route path

```
Segment 1234567:
  Point 1: (27.100, -89.500) - Origin
  Point 2: (27.150, -89.450)
  Point 3: (27.200, -89.400)
  ...
  Point N: (27.500, -89.100) - Terminus
```

### NAD Year Code

| Code | Description | Primary Region |
|------|-------------|----------------|
| 27 | NAD27 datum | Gulf of America |
| 83 | NAD83 datum | Alaska, Pacific, Atlantic |

**Important**: Mixing coordinates from different datums requires transformation.

### Projection Code

| Code | Description | Region |
|------|-------------|--------|
| UTM14 | UTM Zone 14 | Western Gulf |
| UTM15 | UTM Zone 15 | Central Gulf |
| UTM16 | UTM Zone 16 | Eastern Gulf |
| UTM10 | UTM Zone 10 | Pacific |
| UTM11 | UTM Zone 11 | Pacific |

### PPL Appurtenance Types

| Code | Description | Notes |
|------|-------------|-------|
| RISER | Riser connection | Platform connection point |
| PLEM | Pipeline End Manifold | Subsea manifold |
| SDV | Shut-Down Valve | Safety valve location |
| TEE | Pipeline tee | Branch connection |
| VALVE | Valve location | Inline valve |
| METER | Metering station | Measurement point |
| PIG | Pig launcher/receiver | Cleaning/inspection |
| (blank) | Regular point | No appurtenance |

### Asbuilt Flag

| Value | Description |
|-------|-------------|
| Y | Survey represents as-built condition |
| N | Survey represents permitted/planned route |

### Bidirectional Flag

| Value | Description |
|-------|-------------|
| Y | Pipeline can flow in both directions |
| N | Pipeline flows in one direction only |

---

## Example Queries

### Query 1: Single Segment Location
```
https://www.data.bsee.gov/Pipeline/PipelineLocation/Default.aspx
  ?SegmentNumber=1234567
```
Returns all coordinate points for segment 1234567.

### Query 2: Recently Revised Segment
```
https://www.data.bsee.gov/Pipeline/PipelineLocation/Default.aspx
  ?SegmentNumber=1234567
  &LastRevisedDateFrom=01/01/2024
  &LastRevisedDateTo=12/31/2024
```
Returns segment if revised in 2024.

### Query 3: Specific Version
```
https://www.data.bsee.gov/Pipeline/PipelineLocation/Default.aspx
  ?SegmentNumber=1234567
  &VersionDateFrom=01/01/2024
  &VersionDateTo=06/30/2024
```
Returns segment versions from H1 2024.

### Query 4: Leading Zero Segment
```
https://www.data.bsee.gov/Pipeline/PipelineLocation/Default.aspx
  ?SegmentNumber=0012345
```
Leading zeros preserved in search.

---

## URL Parameter Reference

| Parameter | URL Key | Format | Required | Example |
|-----------|---------|--------|----------|---------|
| Segment Number | SegmentNumber | 1-7 digits | **Yes** | 1234567 |
| Revised Date From | LastRevisedDateFrom | MM/DD/YYYY | No | 01/01/2024 |
| Revised Date To | LastRevisedDateTo | MM/DD/YYYY | No | 12/31/2024 |
| Version Date From | VersionDateFrom | MM/DD/YYYY | No | 01/01/2024 |
| Version Date To | VersionDateTo | MM/DD/YYYY | No | 12/31/2024 |

---

## Finding Segment Numbers

Since Segment Number is required, use these methods to discover segment IDs:

### Method 1: Pipeline Permits Query
```
https://www.data.bsee.gov/Pipeline/PipelinePermits/Default.aspx
  ?Area=MC
  &BlockNumber=252
```
Returns permits with associated segment numbers.

### Method 2: Raw Data Download
Download the complete dataset:
```
https://www.data.bsee.gov/Pipeline/Files/PipeLocRawData.zip
```
Contains all segments for bulk lookup.

### Method 3: ROW Descriptions Query
```
https://www.data.bsee.gov/Pipeline/ROW/Default.aspx
```
Returns Right-of-Way information with segment references.

---

## GIS Integration

### Converting to Line Features

Pipeline location data can be converted to GIS line features:

**Process:**
1. Query segment location data
2. Order points by Point Sequence Number
3. Connect points to form LineString geometry
4. Apply appropriate coordinate system

**Python Example:**
```python
import pandas as pd
from shapely.geometry import LineString
import geopandas as gpd

# Load segment data
df = pd.read_csv('segment_data.csv')

# Create LineString for each segment
def create_line(segment_df):
    points = segment_df.sort_values('Point Sequence Number')
    coords = points[['Longitude', 'Latitude']].values
    return LineString(coords)

lines = df.groupby('Segment Number').apply(create_line)

# Create GeoDataFrame
gdf = gpd.GeoDataFrame(
    lines.reset_index(),
    geometry=0,
    crs='EPSG:4267'  # NAD27
)
```

### Coordinate Reference Systems

| Region | EPSG Code | CRS Name |
|--------|-----------|----------|
| Gulf (NAD27) | 4267 | NAD27 Geographic |
| Gulf UTM 15 | 26715 | NAD27 / UTM zone 15N |
| Other (NAD83) | 4269 | NAD83 Geographic |

### Appurtenance Mapping

Create point features for pipeline appurtenances:
```python
# Filter for appurtenance points
appurtenances = df[df['PPL Apurt Type'].notna()]

# Create point features
from shapely.geometry import Point
appurtenances['geometry'] = appurtenances.apply(
    lambda r: Point(r['Longitude'], r['Latitude']),
    axis=1
)
```

---

## Data Structure

### Segment Composition
```
Segment: 1234567
├── Point 1 (Origin)
│   ├── Coordinates: (27.100, -89.500)
│   ├── Appurtenance: RISER
│   └── Asbuilt: Y
├── Point 2
│   ├── Coordinates: (27.150, -89.450)
│   └── Appurtenance: (none)
├── Point 3
│   ├── Coordinates: (27.200, -89.400)
│   ├── Appurtenance: SDV
│   └── Asbuilt: Y
└── Point N (Terminus)
    ├── Coordinates: (27.500, -89.100)
    ├── Appurtenance: PLEM
    └── Asbuilt: Y
```

### Data Relationships
```
Segment Number ─────┬───── Pipeline Permits
                    ├───── ROW Descriptions
                    └───── Location Points (this query)
```

---

## Tips for Effective Searches

### Performance Tips
1. **Always provide segment number** - Required filter
2. **Use date filters sparingly** - Most effective with known segment
3. **Export as CSV** - Most efficient for GIS processing
4. **Batch by segment** - Query one segment at a time

### Data Quality Tips
1. **Check NAD datum** - Verify coordinate system before processing
2. **Verify point order** - Use Point Sequence Number for routing
3. **Review Asbuilt flag** - Distinguish planned vs actual routes
4. **Check appurtenances** - Important features for analysis

### GIS Tips
1. **Transform coordinates** - Match target CRS
2. **Connect points in order** - Use sequence number
3. **Handle datum differences** - NAD27 vs NAD83
4. **Create topology** - Build network from segments

---

## Common Use Cases

| Use Case | Approach |
|----------|----------|
| Map single pipeline | Query segment, export CSV, import to GIS |
| Route analysis | Connect points in sequence order |
| Appurtenance inventory | Filter by PPL Apurt Type |
| As-built verification | Filter Asbuilt Flag = Y |
| Track modifications | Use Last Revised Date range |
| Network mapping | Query multiple segments, build topology |

---

## Related Pipeline Queries

| Query | URL | Description |
|-------|-----|-------------|
| Pipeline Permits | /Pipeline/PipelinePermits/Default.aspx | Permit information |
| ROW Descriptions | /Pipeline/ROW/Default.aspx | Right-of-Way data |
| Pipeline Overview | /Main/Pipeline.aspx | Pipeline statistics |

---

## Related Documents

- [Pipeline Location Fields](../data-dictionaries/pipelines/location-fields.md) - Field definitions
- [Product Codes](../data-dictionaries/pipelines/product-codes.md) - Pipeline product types
- [GIS Catalog](../gis-catalog/index.md) - Pre-built shapefiles
- [Export Formats](export-formats.md) - Export options and best practices
