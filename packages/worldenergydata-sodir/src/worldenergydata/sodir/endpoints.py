"""
SODIR API endpoint definitions.

Defines all available SODIR REST API endpoints with their IDs and metadata.
Migrated from factpages.sodir.no to factmaps.sodir.no (May 2025).
"""

# SODIR dataset endpoint definitions
# Current API uses ArcGIS FeatureServer layer query endpoints.
SODIR_ENDPOINTS = {
    "blocks": {
        "id": "1001",
        "table_id": "1001",
        "endpoint": "/api/rest/services/DataService/Data/FeatureServer/1001/query",
        "description": "Norwegian Continental Shelf block information",
        "fields": [
            "npdidBlock",
            "blockName",
            "blockArea",
            "blockStatus",
            "blockGeometry",
            "blockOperator",
            "blockLicensee",
        ],
    },
    "wellbores": {
        "id": "5000",
        "table_id": "5000",
        "endpoint": "/api/rest/services/DataService/Data/FeatureServer/5000/query",
        "description": "Wellbore drilling and completion data",
        "fields": [
            "npdidWellbore",
            "wellboreName",
            "wellboreType",
            "drillingOperator",
            "spudDate",
            "totalDepth",
            "waterDepth",
            "nsDeg",
            "ewDeg",
            "wellboreStatus",
            "wellborePurpose",
            "completionDate",
        ],
    },
    "fields": {
        "id": "7100",
        "table_id": "7100",
        "endpoint": "/api/rest/services/DataService/Data/FeatureServer/7100/query",
        "description": "Field information including reserves and production",
        "fields": [
            "npdidField",
            "fieldName",
            "fieldOperator",
            "discoveryDate",
            "fieldStatus",
            "recoverableOil",
            "recoverableGas",
            "recoverableNGL",
            "recoverableCondensate",
            "productionStartYear",
        ],
    },
    "discoveries": {
        "id": "7000",
        "table_id": "7000",
        "endpoint": "/api/rest/services/DataService/Data/FeatureServer/7000/query",
        "description": "Discovery information and reserve classifications",
        "fields": [
            "npdidDiscovery",
            "discoveryName",
            "discoveryYear",
            "mainArea",
            "hydrocarbon",
            "resourceClass",
            "recoverableOilEstimate",
            "recoverableGasEstimate",
        ],
    },
    "surveys": {
        "id": "4000",
        "table_id": "4000",
        "endpoint": "/api/rest/services/DataService/Data/FeatureServer/4000/query",
        "description": "Seismic surveys and geological studies",
        "fields": [
            "npdidSurvey",
            "surveyName",
            "surveyType",
            "acquisitionYear",
            "surveyCompany",
            "surveyArea",
            "surveyGeometry",
        ],
    },
    "facilities": {
        "id": "3000",
        "table_id": "3000",
        "endpoint": "/api/rest/services/DataService/Data/FeatureServer/3000/query",
        "description": "Offshore facilities and infrastructure",
        "fields": [
            "npdidFacility",
            "facilityName",
            "facilityType",
            "operator",
            "facilityStatus",
            "startupDate",
            "waterDepth",
        ],
    },
}

# API configuration defaults
API_DEFAULTS = {
    "base_url": "https://factmaps.sodir.no/api/rest",
    "rate_limit": 10,  # requests per second
    "cache_ttl": 86400,  # 24 hours in seconds
    "timeout": 30,  # request timeout in seconds
    "max_retries": 3,
    "retry_delay": 1,  # seconds between retries
}
