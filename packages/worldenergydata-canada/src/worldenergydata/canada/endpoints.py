# ABOUTME: Canada API endpoint definitions for AER, BCER, and Petrinex data sources
# ABOUTME: Defines all available REST API endpoints with their IDs and metadata

"""
Canada API endpoint definitions.

Defines all available API endpoints for Canadian oil and gas data sources:
- Alberta Energy Regulator (AER) public data
- BC Energy Regulator (BCER) ArcGIS REST services
- Petrinex production data portal
"""

# =============================================================================
# Alberta Energy Regulator (AER) Endpoints
# =============================================================================

AER_ENDPOINTS = {
    "wells": {
        "id": "aer_wells",
        "endpoint": "/st37/index.html",
        "description": "Alberta well license and drilling information",
        "base_url": "https://www.aer.ca/providing-information/data-and-reports/statistical-reports",
        "fields": [
            "license_number",
            "uwi",
            "well_name",
            "licensee",
            "field_name",
            "pool_name",
            "spud_date",
            "final_drill_date",
            "total_depth",
            "well_status",
            "well_type",
            "substance",
            "latitude",
            "longitude",
        ],
    },
    "production": {
        "id": "aer_production",
        "endpoint": "/st3/index.html",
        "description": "Alberta monthly production data (oil, gas, water)",
        "base_url": "https://www.aer.ca/providing-information/data-and-reports/statistical-reports",
        "fields": [
            "uwi",
            "production_month",
            "oil_volume_m3",
            "gas_volume_e3m3",
            "water_volume_m3",
            "condensate_volume_m3",
            "hours_on_production",
        ],
    },
    "facilities": {
        "id": "aer_facilities",
        "endpoint": "/st102/index.html",
        "description": "Alberta facility information (batteries, pipelines)",
        "base_url": "https://www.aer.ca/providing-information/data-and-reports/statistical-reports",
        "fields": [
            "facility_id",
            "facility_name",
            "facility_type",
            "licensee",
            "status",
            "latitude",
            "longitude",
        ],
    },
    "licenses": {
        "id": "aer_licenses",
        "endpoint": "/st1/index.html",
        "description": "Alberta well license applications and approvals",
        "base_url": "https://www.aer.ca/providing-information/data-and-reports/statistical-reports",
        "fields": [
            "license_number",
            "application_date",
            "approval_date",
            "licensee",
            "well_type",
            "substance",
            "field_name",
        ],
    },
    "operators": {
        "id": "aer_operators",
        "endpoint": "/st50/index.html",
        "description": "Alberta operator/licensee directory",
        "base_url": "https://www.aer.ca/providing-information/data-and-reports/statistical-reports",
        "fields": [
            "ba_code",
            "company_name",
            "address",
            "contact_info",
            "status",
        ],
    },
}

# AER Petrinex endpoints for production data
AER_PETRINEX_ENDPOINTS = {
    "volumetric_data": {
        "id": "petrinex_volumetric",
        "endpoint": "/publicdata/volumetric",
        "description": "Petrinex volumetric production data for Alberta",
        "base_url": "https://www.petrinex.gov.ab.ca",
        "fields": [
            "uwi",
            "facility_id",
            "activity_type",
            "product_type",
            "volume",
            "volume_units",
            "reporting_month",
        ],
    },
}

# =============================================================================
# BC Energy Regulator (BCER) ArcGIS REST Endpoints
# =============================================================================

BCER_ENDPOINTS = {
    "wells": {
        "id": "bcer_wells",
        "endpoint": "/arcgis/rest/services/BCER_WELLS/FeatureServer/0/query",
        "description": "BC well location and drilling information",
        "base_url": "https://maps.bcer.gov.bc.ca",
        "fields": [
            "wa_num",
            "uwi",
            "well_name",
            "operator",
            "field_name",
            "pool_name",
            "spud_date",
            "rig_release_date",
            "total_depth",
            "well_status",
            "well_type",
            "ground_elevation",
            "latitude",
            "longitude",
        ],
        "arcgis_params": {
            "where": "1=1",
            "outFields": "*",
            "f": "json",
            "returnGeometry": "true",
        },
    },
    "production": {
        "id": "bcer_production",
        "endpoint": "/arcgis/rest/services/BCER_PRODUCTION/FeatureServer/0/query",
        "description": "BC monthly production data",
        "base_url": "https://maps.bcer.gov.bc.ca",
        "fields": [
            "wa_num",
            "uwi",
            "production_month",
            "oil_volume_m3",
            "gas_volume_e3m3",
            "water_volume_m3",
            "condensate_volume_m3",
        ],
        "arcgis_params": {
            "where": "1=1",
            "outFields": "*",
            "f": "json",
        },
    },
    "facilities": {
        "id": "bcer_facilities",
        "endpoint": "/arcgis/rest/services/BCER_FACILITIES/FeatureServer/0/query",
        "description": "BC facility information (plants, compressors)",
        "base_url": "https://maps.bcer.gov.bc.ca",
        "fields": [
            "facility_id",
            "facility_name",
            "facility_type",
            "operator",
            "status",
            "latitude",
            "longitude",
        ],
        "arcgis_params": {
            "where": "1=1",
            "outFields": "*",
            "f": "json",
            "returnGeometry": "true",
        },
    },
    "pipelines": {
        "id": "bcer_pipelines",
        "endpoint": "/arcgis/rest/services/BCER_PIPELINES/FeatureServer/0/query",
        "description": "BC pipeline network information",
        "base_url": "https://maps.bcer.gov.bc.ca",
        "fields": [
            "pipeline_id",
            "pipeline_name",
            "operator",
            "status",
            "substance",
            "diameter_mm",
            "length_km",
        ],
        "arcgis_params": {
            "where": "1=1",
            "outFields": "*",
            "f": "json",
            "returnGeometry": "true",
        },
    },
    "pools": {
        "id": "bcer_pools",
        "endpoint": "/arcgis/rest/services/BCER_POOLS/FeatureServer/0/query",
        "description": "BC pool/reservoir information",
        "base_url": "https://maps.bcer.gov.bc.ca",
        "fields": [
            "pool_id",
            "pool_name",
            "field_name",
            "formation",
            "discovery_date",
            "pool_type",
        ],
        "arcgis_params": {
            "where": "1=1",
            "outFields": "*",
            "f": "json",
        },
    },
}

# BC Petrinex endpoints
BCER_PETRINEX_ENDPOINTS = {
    "volumetric_data": {
        "id": "petrinex_bc_volumetric",
        "endpoint": "/publicdata/volumetric",
        "description": "Petrinex volumetric production data for BC",
        "base_url": "https://www.petrinex.gov.bc.ca",
        "fields": [
            "uwi",
            "facility_id",
            "activity_type",
            "product_type",
            "volume",
            "volume_units",
            "reporting_month",
        ],
    },
}

# =============================================================================
# Combined API Configuration Defaults
# =============================================================================

AER_API_DEFAULTS = {
    "base_url": "https://www.aer.ca",
    "rate_limit": 5,  # requests per second
    "cache_ttl": 86400,  # 24 hours in seconds
    "timeout": 60,  # request timeout in seconds
    "max_retries": 3,
    "retry_delay": 2,  # seconds between retries
}

BCER_API_DEFAULTS = {
    "base_url": "https://maps.bcer.gov.bc.ca",
    "rate_limit": 10,  # requests per second
    "cache_ttl": 86400,  # 24 hours in seconds
    "timeout": 30,  # request timeout in seconds
    "max_retries": 3,
    "retry_delay": 1,  # seconds between retries
    "max_records_per_request": 1000,  # ArcGIS pagination limit
}

PETRINEX_API_DEFAULTS = {
    "ab_base_url": "https://www.petrinex.gov.ab.ca",
    "bc_base_url": "https://www.petrinex.gov.bc.ca",
    "rate_limit": 5,  # requests per second
    "cache_ttl": 86400,  # 24 hours in seconds
    "timeout": 120,  # longer timeout for large data requests
    "max_retries": 3,
    "retry_delay": 5,  # seconds between retries
}

# =============================================================================
# Province Code Mappings
# =============================================================================

PROVINCE_CODES = {
    "ab": {
        "name": "Alberta",
        "regulator": "AER",
        "uwi_prefix": "00",
        "endpoints": AER_ENDPOINTS,
        "api_defaults": AER_API_DEFAULTS,
    },
    "bc": {
        "name": "British Columbia",
        "regulator": "BCER",
        "uwi_prefix": "02",
        "endpoints": BCER_ENDPOINTS,
        "api_defaults": BCER_API_DEFAULTS,
    },
    "sk": {
        "name": "Saskatchewan",
        "regulator": "SER",
        "uwi_prefix": "01",
        "endpoints": {},  # Future implementation
        "api_defaults": {},
    },
}

# =============================================================================
# Data Type Mappings
# =============================================================================

VALID_DATA_TYPES = [
    "wells",
    "production",
    "facilities",
    "licenses",
    "operators",
    "pools",
    "pipelines",
]

# Mapping of data types available per province
PROVINCE_DATA_TYPES = {
    "ab": ["wells", "production", "facilities", "licenses", "operators"],
    "bc": ["wells", "production", "facilities", "pipelines", "pools"],
}
