# ABOUTME: Texas RRC API endpoint definitions and URLs for data access
# ABOUTME: Defines PDQ dump URLs, wellbore data endpoints, and drilling permit URLs

"""
Texas RRC API endpoint definitions.

Defines all available Texas Railroad Commission data endpoints including:
- PDQ (Production Data Query) dump files
- Well information system endpoints
- Drilling permit data
- Completion reports
"""

# Texas RRC base URLs
RRC_BASE_URLS = {
    "main": "https://www.rrc.texas.gov",
    "gis": "https://gis.rrc.texas.gov",
    "webmap": "https://webmap.rrc.texas.gov",
    "pdq": "https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/",
}

# PDQ (Production Data Query) dump file endpoints
# These are downloadable CSV/ZIP files with production data
PDQ_ENDPOINTS = {
    "oil_gas_production": {
        "url": "https://www.rrc.texas.gov/media/ebxnoxbm/pdq-dump.zip",
        "description": "Monthly oil and gas production data by lease",
        "format": "zip",
        "update_frequency": "monthly",
        "fields": [
            "district",
            "lease_number",
            "operator_number",
            "operator_name",
            "lease_name",
            "field_number",
            "field_name",
            "county_code",
            "oil_production",
            "gas_production",
            "condensate",
            "water_production",
            "production_date",
            "well_count",
        ],
    },
    "well_bore_database": {
        "url": "https://www.rrc.texas.gov/media/kywh5qsj/wellboredump.zip",
        "description": "Well bore information including location and completion data",
        "format": "zip",
        "update_frequency": "monthly",
        "fields": [
            "api_number",
            "district",
            "county_code",
            "lease_name",
            "well_number",
            "operator_name",
            "field_name",
            "well_type",
            "latitude",
            "longitude",
            "total_depth",
            "completion_date",
            "plug_date",
            "well_status",
        ],
    },
    "drilling_permits": {
        "url": "https://www.rrc.texas.gov/media/mfqlrnsh/drillpermitdump.zip",
        "description": "Drilling permit applications and approvals",
        "format": "zip",
        "update_frequency": "weekly",
        "fields": [
            "permit_number",
            "api_number",
            "district",
            "county_code",
            "operator_name",
            "lease_name",
            "well_number",
            "permit_type",
            "approved_date",
            "total_depth",
            "latitude",
            "longitude",
        ],
    },
    "completions": {
        "url": "https://www.rrc.texas.gov/media/ngrn4gla/completiondump.zip",
        "description": "Well completion reports",
        "format": "zip",
        "update_frequency": "monthly",
        "fields": [
            "api_number",
            "district",
            "county_code",
            "completion_date",
            "operator_name",
            "lease_name",
            "well_number",
            "formation",
            "perforation_top",
            "perforation_bottom",
            "initial_production",
        ],
    },
    "operators": {
        "url": "https://www.rrc.texas.gov/media/rh3nkbrx/operatordump.zip",
        "description": "Registered operator information",
        "format": "zip",
        "update_frequency": "monthly",
        "fields": [
            "operator_number",
            "operator_name",
            "operator_type",
            "address",
            "city",
            "state",
            "zip_code",
            "status",
        ],
    },
}

# Well information query endpoints
WELL_QUERY_ENDPOINTS = {
    "well_inquiry": {
        "base_url": "https://webapps.rrc.texas.gov/WellInquiry/",
        "description": "Interactive well data lookup",
        "method": "GET",
        "parameters": ["api_number", "operator", "lease", "county", "district"],
    },
    "well_report": {
        "base_url": "https://webapps.rrc.texas.gov/WellReport/",
        "description": "Detailed well reports",
        "method": "GET",
        "parameters": ["api_number"],
    },
}

# GIS/Map service endpoints
GIS_ENDPOINTS = {
    "wells_layer": {
        "url": "https://gis.rrc.texas.gov/arcgis/rest/services/Public/Wells/MapServer",
        "description": "Well locations map service",
        "format": "ArcGIS REST",
        "layers": ["active_wells", "plugged_wells", "permits"],
    },
    "production_layer": {
        "url": "https://gis.rrc.texas.gov/arcgis/rest/services/Public/Production/MapServer",
        "description": "Production data map service",
        "format": "ArcGIS REST",
        "layers": ["oil_production", "gas_production"],
    },
    "fields_layer": {
        "url": "https://gis.rrc.texas.gov/arcgis/rest/services/Public/Fields/MapServer",
        "description": "Oil and gas field boundaries",
        "format": "ArcGIS REST",
        "layers": ["field_boundaries", "field_outlines"],
    },
}

# Texas RRC districts
TEXAS_DISTRICTS = {
    "01": {"name": "District 1", "headquarters": "San Antonio", "counties": 27},
    "02": {"name": "District 2", "headquarters": "Refugio", "counties": 21},
    "03": {"name": "District 3", "headquarters": "Houston", "counties": 39},
    "04": {"name": "District 4", "headquarters": "Corpus Christi", "counties": 22},
    "05": {"name": "District 5", "headquarters": "Kilgore", "counties": 15},
    "06": {"name": "District 6", "headquarters": "Kilgore", "counties": 16},
    "7B": {"name": "District 7B", "headquarters": "San Angelo", "counties": 19},
    "7C": {"name": "District 7C", "headquarters": "San Angelo", "counties": 13},
    "08": {"name": "District 8", "headquarters": "Midland", "counties": 30},
    "8A": {"name": "District 8A", "headquarters": "Lubbock", "counties": 22},
    "09": {"name": "District 9", "headquarters": "Wichita Falls", "counties": 20},
    "10": {"name": "District 10", "headquarters": "Pampa", "counties": 10},
}

# API configuration defaults
API_DEFAULTS = {
    "base_url": "https://www.rrc.texas.gov",
    "rate_limit": 5,  # requests per second (be respectful to public server)
    "cache_ttl": 86400,  # 24 hours in seconds
    "timeout": 60,  # request timeout in seconds (larger files need more time)
    "max_retries": 3,
    "retry_delay": 2,  # seconds between retries
    "chunk_size": 8192,  # bytes for streaming downloads
}

# Texas state and county FIPS codes relevant to API numbers
TEXAS_FIPS = {
    "state_code": "42",  # Texas state FIPS code for API numbers
    "county_codes": {
        # Partial list of major oil/gas counties
        "001": "Anderson",
        "003": "Andrews",
        "013": "Atascosa",
        "025": "Bee",
        "041": "Brazos",
        "051": "Burleson",
        "055": "Caldwell",
        "061": "Cameron",
        "079": "Cochran",
        "103": "Crane",
        "105": "Crockett",
        "117": "DeWitt",
        "123": "Dimmit",
        "127": "Duvall",
        "135": "Ector",
        "151": "Fisher",
        "173": "Glasscock",
        "195": "Hansford",
        "227": "Howard",
        "229": "Hudspeth",
        "243": "Jeff Davis",
        "263": "Kent",
        "269": "King",
        "301": "Loving",
        "303": "Lubbock",
        "317": "Martin",
        "329": "Midland",
        "353": "Nolan",
        "371": "Pecos",
        "383": "Reagan",
        "389": "Reeves",
        "415": "Scurry",
        "435": "Sutton",
        "461": "Upton",
        "475": "Ward",
        "495": "Winkler",
        "501": "Yoakum",
    },
}

# Data type to endpoint mapping
DATA_TYPE_ENDPOINTS = {
    "production": "oil_gas_production",
    "wells": "well_bore_database",
    "drilling_permits": "drilling_permits",
    "completions": "completions",
    "operators": "operators",
}


def get_pdq_endpoint(data_type: str) -> dict:
    """
    Get PDQ endpoint configuration for a data type.

    Args:
        data_type: Type of data (production, wells, drilling_permits, etc.)

    Returns:
        Endpoint configuration dictionary

    Raises:
        ValueError: If data type is not recognized
    """
    endpoint_key = DATA_TYPE_ENDPOINTS.get(data_type)
    if endpoint_key is None:
        raise ValueError(
            f"Unknown data type: {data_type}. "
            f"Valid types: {list(DATA_TYPE_ENDPOINTS.keys())}"
        )
    return PDQ_ENDPOINTS[endpoint_key]


def get_district_info(district_code: str) -> dict:
    """
    Get information about a Texas RRC district.

    Args:
        district_code: District code (01-10, 7B, 7C, 8A)

    Returns:
        District information dictionary

    Raises:
        ValueError: If district code is not valid
    """
    # Normalize district code
    normalized = (
        district_code.upper().zfill(2)
        if district_code.isdigit()
        else district_code.upper()
    )
    if normalized not in TEXAS_DISTRICTS:
        raise ValueError(
            f"Invalid district code: {district_code}. "
            f"Valid codes: {list(TEXAS_DISTRICTS.keys())}"
        )
    return TEXAS_DISTRICTS[normalized]


def build_api_number(county_code: str, well_number: str) -> str:
    """
    Build a Texas API number from components.

    Args:
        county_code: 3-digit county FIPS code
        well_number: 5-digit well sequence number

    Returns:
        Formatted API number (42-XXX-XXXXX)
    """
    return f"{TEXAS_FIPS['state_code']}-{county_code.zfill(3)}-{well_number.zfill(5)}"
