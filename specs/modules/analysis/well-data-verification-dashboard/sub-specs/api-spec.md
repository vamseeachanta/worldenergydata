# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-01-13-well-data-verification-dashboard/spec.md

> Created: 2025-01-13
> Version: 1.0.0

## API Overview

RESTful API endpoints for data retrieval, validation, and dashboard operations.

## Base URL
```
http://localhost:8050/api/v1
```

## Authentication
Basic authentication for initial version, Bearer token for production.

## Endpoints

### Well Data Endpoints

#### GET /wells
**Purpose:** Retrieve list of all available wells
**Parameters:** 
- `field` (optional): Filter by field name
- `status` (optional): Filter by production status (active/inactive)
**Response:**
```json
{
  "wells": [
    {
      "api12": "608174046300",
      "well_name": "JACK A-1",
      "field": "Jack",
      "status": "active",
      "last_production_date": "2024-12-31"
    }
  ],
  "total": 150
}
```
**Errors:** 404 (No wells found), 500 (Server error)

#### GET /wells/{api12}
**Purpose:** Get detailed information for a specific well
**Parameters:** None
**Response:**
```json
{
  "api12": "608174046300",
  "well_name": "JACK A-1",
  "field": "Jack",
  "completion_date": "2019-01-15",
  "total_production": 7800613,
  "last_production": {
    "date": "2024-12-31",
    "volume": 45000,
    "rate": 1500
  },
  "economics": {
    "total_revenue": 870823453.46,
    "total_opex": 117009195.00,
    "npv": -1206976526.76
  }
}
```
**Errors:** 404 (Well not found), 500 (Server error)

### Production Data Endpoints

#### GET /production/{api12}
**Purpose:** Retrieve production history for a well
**Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)
- `interval` (optional): daily/monthly/yearly
**Response:**
```json
{
  "api12": "608174046300",
  "production": [
    {
      "date": "2024-12-01",
      "oil_volume": 45000,
      "gas_volume": 12000,
      "water_volume": 3000,
      "days_on_production": 30
    }
  ]
}
```
**Errors:** 404 (No production data), 400 (Invalid date range)

### Validation Endpoints

#### POST /validate/well
**Purpose:** Trigger validation workflow for a well
**Parameters:**
```json
{
  "api12": "608174046300",
  "validation_rules": ["completeness", "outliers", "economics"],
  "reference_file": "path/to/excel/benchmark.xlsx"
}
```
**Response:**
```json
{
  "validation_id": "val_123456",
  "status": "in_progress",
  "initiated_at": "2025-01-13T10:00:00Z"
}
```
**Errors:** 400 (Invalid parameters), 404 (Well not found)

#### GET /validate/status/{validation_id}
**Purpose:** Check validation workflow status
**Parameters:** None
**Response:**
```json
{
  "validation_id": "val_123456",
  "status": "completed",
  "results": {
    "completeness": "passed",
    "outliers": "warning",
    "economics": "failed",
    "issues": [
      {
        "type": "outlier",
        "description": "Production spike in 2024-03",
        "severity": "warning"
      }
    ]
  }
}
```
**Errors:** 404 (Validation not found)

### Dashboard Data Endpoints

#### GET /dashboard/overview
**Purpose:** Get aggregated data for dashboard overview
**Parameters:**
- `fields` (optional): Comma-separated field names
**Response:**
```json
{
  "total_wells": 150,
  "active_wells": 120,
  "total_production_ytd": 45000000,
  "total_revenue_ytd": 2850000000,
  "fields": [
    {
      "name": "Jack",
      "wells": 45,
      "production_ytd": 15000000
    }
  ]
}
```
**Errors:** 500 (Server error)

#### GET /dashboard/metrics/{api12}
**Purpose:** Get dashboard metrics for specific well
**Parameters:**
- `period` (optional): ytd/last_year/all_time
**Response:**
```json
{
  "api12": "608174046300",
  "metrics": {
    "production": {
      "total": 7800613,
      "average_daily": 1500,
      "trend": "declining"
    },
    "economics": {
      "revenue": 870823453,
      "opex": 117009195,
      "npv": -1206976526
    },
    "efficiency": {
      "uptime": 0.95,
      "decline_rate": 0.15
    }
  }
}
```
**Errors:** 404 (Well not found)

### Export Endpoints

#### POST /export/report
**Purpose:** Generate export report
**Parameters:**
```json
{
  "type": "pdf",
  "wells": ["608174046300"],
  "sections": ["production", "economics", "validation"],
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  }
}
```
**Response:**
```json
{
  "export_id": "exp_789012",
  "status": "generating",
  "estimated_time": 30
}
```
**Errors:** 400 (Invalid parameters)

#### GET /export/download/{export_id}
**Purpose:** Download generated report
**Parameters:** None
**Response:** Binary file stream
**Errors:** 404 (Export not found), 410 (Export expired)

## Error Response Format
```json
{
  "error": {
    "code": "WELL_NOT_FOUND",
    "message": "Well with API12 608174046300 not found",
    "details": {},
    "timestamp": "2025-01-13T10:00:00Z"
  }
}
```

## Rate Limiting
- 100 requests per minute per IP
- 1000 requests per hour per user

## Versioning
API version included in URL path (/api/v1/)
Deprecation notices provided in headers for older versions