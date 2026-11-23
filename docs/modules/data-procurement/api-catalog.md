# Energy Data API Catalog

> Created: 2025-01-06
> Status: Active
> Purpose: Comprehensive catalog of available energy data APIs for the WorldEnergyData project

## Table of Contents
- [BSEE APIs](#bsee-apis)
- [EIA APIs](#eia-apis) 
- [NOAA APIs](#noaa-apis)
- [Wind Energy APIs](#wind-energy-apis)
- [Summary and Recommendations](#summary-and-recommendations)

---

## BSEE APIs

### Overview
The Bureau of Safety and Environmental Enforcement (BSEE) provides comprehensive offshore oil and gas data through their Data Center and ArcGIS REST services.

### Base URLs
- **Data Center**: https://www.data.bsee.gov/
- **ArcGIS REST Services**: https://gis.boem.gov/arcgis/rest/services/BOEM_BSEE/

### Available Endpoints

#### 1. ArcGIS MapServer REST API
**URL**: `https://gis.boem.gov/arcgis/rest/services/BOEM_BSEE/MMC_Layers/MapServer`

**Available Layers**:
- OCS Drilling Platforms
- OCS Oil and Natural Gas Wells  
- OCS Oil and Gas Pipelines
- BOEM OCS Administrative Boundaries
- BOEM OCS Lease Blocks
- BOEM Block Aliquots
- BOEM Oil and Gas Leases

**Data Format**: JSON, GeoJSON, ESRI Shape files
**Authentication**: None required for public data
**Rate Limits**: Standard ArcGIS server limits apply

#### 2. BSEE Data Center Query Interfaces

**Production Data**:
- URL: https://www.data.bsee.gov/Production/
- Query by: Lease, Well (API No.), Lease Operator
- Format: CSV, ASCII, PDF

**Well Data**:
- URL: https://www.data.bsee.gov/Well/
- Includes: API lists, directional surveys, completion data
- Format: CSV, ASCII, PDF

**Platform Data**:
- URL: https://www.data.bsee.gov/Platform/PlatformStructures/Default.aspx
- Query: Platform structures and installations
- Format: Online query, CSV export

### Data Update Frequency
- Production data: Monthly
- Well data: As reported
- Platform data: Real-time updates

---

## EIA APIs

### Overview
The U.S. Energy Information Administration provides a comprehensive RESTful API (v2) for accessing energy statistics and data.

### Base URL
`https://api.eia.gov/v2/`

### Authentication
- **Required**: Yes - API key
- **Registration**: https://www.eia.gov/opendata/register.php
- **Key Usage**: Pass as query parameter `?api_key=YOUR_KEY`
- **Rate Limits**: 
  - Default: 10,000 requests per day
  - No specified per-second limit

### Major Endpoints

#### 1. Petroleum Data
```
GET /v2/petroleum/data
```
- Weekly, monthly, and annual data
- Imports/exports, stocks, supply and disposition
- Response format: JSON

#### 2. Natural Gas Data
```
GET /v2/natural-gas/data
```
- Production, consumption, prices
- Monthly and annual data
- Underground storage data

#### 3. Electricity Data
```
GET /v2/electricity/data
```
- Retail sales (customers, price, revenue, MWh)
- Electric power operations
- RTO data (daily and hourly)
- State electricity profiles

#### 4. Crude Oil Imports
```
GET /v2/crude-oil-imports/data
```
- By country and destination
- Type, grade, quantity data
- Monthly updates

#### 5. International Energy Data
```
GET /v2/international/data
```
- Country-level production and consumption
- Multiple fuel types
- Annual data

### Query Parameters
- `frequency`: annual, monthly, weekly, daily, hourly
- `data[]`: Specify data columns to return
- `facets[]`: Filter by specific attributes
- `start` & `end`: Date range filtering
- `sort[]`: Sorting options
- `offset` & `length`: Pagination

### Response Format
```json
{
  "response": {
    "total": 1234,
    "dateFormat": "YYYY-MM-DD",
    "frequency": "monthly",
    "data": [
      {
        "period": "2024-01",
        "value": "123.45",
        "units": "thousand barrels"
      }
    ]
  }
}
```

---

## NOAA APIs

### Overview
National Oceanic and Atmospheric Administration provides weather, climate, and ocean data through multiple API services.

### 1. NCEI Access Data Service API (Current)

**Base URL**: `https://www.ncei.noaa.gov/access/services/data/v1`

**Authentication**: None required
**Protocol**: HTTPS only (HSTS enforced)
**Methods**: GET requests only

**Available Formats**:
- CSV, SSV, JSON, PDF, NetCDF (dataset dependent)

**Key Datasets**:
- `global-summary-of-the-month`
- `daily-summaries`
- `global-hourly`

**Query Parameters**:
- `dataset`: Dataset identifier
- `stations`: Station IDs (comma-separated)
- `startDate` & `endDate`: Date range (YYYY-MM-DD)
- `dataTypes`: Data types (TMIN, TMAX, PRCP, etc.)
- `format`: Output format

### 2. NOAA Weather Service API

**Base URL**: `https://api.weather.gov/`

**Authentication**: None required
**Rate Limits**: Reasonable use expected
**Default Format**: GeoJSON

**Key Endpoints**:
```
GET /points/{latitude},{longitude}
GET /gridpoints/{office}/{gridX},{gridY}/forecast
GET /gridpoints/{office}/{gridX},{gridY}/forecast/hourly
GET /stations/{stationId}/observations
GET /alerts/active
```

### 3. CO-OPS Tides and Currents API

**Base URL**: `https://api.tidesandcurrents.noaa.gov/api/prod/`

**Key Parameters**:
- `station`: Station ID
- `product`: water_level, predictions, currents, etc.
- `datum`: MSL, MLLW, etc.
- `units`: metric, english
- `time_zone`: gmt, lst, lst_ldt
- `format`: json, xml, csv

### 4. Climate Data Online (CDO) API (Legacy - Limited to 2022)

**Base URL**: `https://www.ncei.noaa.gov/cdo-web/api/v2/`

**Authentication**: Token required
**Registration**: https://www.ncdc.noaa.gov/cdo-web/token
**Rate Limits**: 
- 5 requests per second
- 10,000 requests per day

**Endpoints**:
- `/data`: Fetch actual data
- `/stations`: Station metadata
- `/locationcategories`: Location categories
- `/datacategories`: Data categories
- `/datatypes`: Data type descriptions

---

## Wind Energy APIs

### 1. USWTDB (U.S. Wind Turbine Database) API

**Base URL**: `https://energy.usgs.gov/api/uswtdb/v1/`

**Authentication**: None (read-only public access)
**Protocol**: REST/HTTPS
**Format**: JSON

**Key Endpoints**:
```
GET /turbines
GET /projects
GET /manufacturers
```

**Features**:
- Land-based and offshore wind turbine locations
- Project information and technical specifications
- No authentication required for read access

### 2. NREL Wind Toolkit API

**Base URL**: `https://developer.nrel.gov/api/`

**Authentication**: API key required
**Registration**: https://developer.nrel.gov/signup/

**Offshore Wind Endpoints**:
```
GET /wind-toolkit/v2/wind/offshore-ca-download.{format}
```

**Parameters**:
- `api_key`: Your API key
- `lat` & `lon`: Coordinates
- `year`: Data year
- `interval`: Time interval (5-min, hourly)
- `format`: json, csv

**Available Data**:
- Wind speed and direction at multiple heights
- Temperature and pressure
- Wave height and period (offshore)

### 3. BOEM Renewable Energy GIS Services

**Base URL**: Via ArcGIS REST services

**Available Layers**:
- Wind Planning Areas
- Wind Lease Areas
- Met ocean buoys
- Environmental data layers

**Access**: Through standard WMS/WFS protocols or ArcGIS REST API

---

## Summary and Recommendations

### Priority APIs for Implementation

1. **BSEE ArcGIS REST API** - Critical for offshore oil & gas data
   - No authentication required
   - Well-documented REST interface
   - Spatial query capabilities

2. **EIA API v2** - Essential for energy statistics
   - Comprehensive energy data coverage
   - Well-structured RESTful design
   - Requires API key (free)

3. **NOAA NCEI Access Data Service** - Important for weather/ocean conditions
   - Multiple format support
   - No authentication needed
   - Relevant for offshore operations

### Authentication Strategy

| API | Auth Type | Storage Method |
|-----|-----------|----------------|
| BSEE | None | N/A |
| EIA | API Key | Environment variable |
| NOAA Weather | None | N/A |
| NOAA CDO | Token | Environment variable |
| NREL | API Key | Environment variable |
| USWTDB | None | N/A |

### Rate Limiting Considerations

| API | Rate Limit | Strategy |
|-----|------------|----------|
| EIA | 10k/day | Cache aggressively |
| NOAA CDO | 5/sec, 10k/day | Queue requests |
| NREL | Varies by tier | Monitor usage |
| Others | Unspecified | Implement backoff |

### Implementation Priority

**Phase 1 (Week 1)**:
- BSEE ArcGIS REST API integration
- EIA API v2 core endpoints

**Phase 2 (Week 2)**:
- NOAA weather/climate data
- Basic caching layer

**Phase 3 (Week 3)**:
- Wind energy APIs
- Advanced features

### Next Steps

1. Register for required API keys
2. Create environment configuration
3. Build base HTTP client with retry logic
4. Implement API-specific adapters
5. Add response transformation layer
6. Develop caching strategy
7. Create comprehensive test suite