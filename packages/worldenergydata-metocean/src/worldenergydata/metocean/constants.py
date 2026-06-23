# ABOUTME: Constants and enumerations for the metocean module.
# ABOUTME: Defines data sources, station types, quality flags, and parameter types.

"""
Constants for Metocean Module

Defines enumerations and constants for data sources, station types,
quality flags, and other categorizations used throughout the module.
"""

from enum import Enum, IntEnum
from typing import Dict, Set, Tuple


class DataSource(str, Enum):
    """Data sources for metocean observations and forecasts"""

    NDBC = "ndbc"  # NOAA National Data Buoy Center
    COOPS = "coops"  # NOAA CO-OPS (tides, currents, water levels)
    OPEN_METEO = "open_meteo"  # Open-Meteo Marine API
    ERDDAP = "erddap"  # IOOS ERDDAP servers
    CMEMS = "cmems"  # Copernicus Marine Service
    MET_NORWAY = "met_norway"  # Norwegian Meteorological Institute
    HYCOM = "hycom"  # HYCOM ocean model
    NWS = "nws"  # National Weather Service
    ECMWF = "ecmwf"  # European Centre for Medium-Range Weather Forecasts
    GFS = "gfs"  # Global Forecast System
    OTHER = "other"


class DataType(str, Enum):
    """Types of metocean data based on temporal characteristics"""

    REALTIME = "realtime"  # Current/recent observations
    HISTORICAL = "historical"  # Archived historical data
    FORECAST = "forecast"  # Future predictions


class StationType(str, Enum):
    """Types of measurement stations/platforms"""

    BUOY = "buoy"  # Moored buoy
    COASTAL = "coastal"  # Coastal station
    PLATFORM = "platform"  # Offshore platform
    SHIP = "ship"  # Ship observation
    GRID_POINT = "grid_point"  # Model grid point
    CMAN = "cman"  # Coastal-Marine Automated Network station
    DART = "dart"  # Deep-ocean Assessment and Reporting of Tsunamis
    OIL_PLATFORM = "oil_platform"  # Oil/gas platform
    TIDE_GAUGE = "tide_gauge"  # Tide measurement station
    CURRENT_METER = "current_meter"  # Current measurement station
    WEATHER_STATION = "weather_station"  # Land-based weather station
    DRIFTER = "drifter"  # Drifting buoy
    ARGO = "argo"  # Argo float
    GLIDER = "glider"  # Ocean glider
    HF_RADAR = "hf_radar"  # High-frequency radar
    SATELLITE = "satellite"  # Satellite observation
    MODEL_GRID = "model_grid"  # Model grid point
    OTHER = "other"


class QualityFlag(str, Enum):
    """Quality control flags for observations"""

    NOT_CHECKED = "not_checked"  # Data has not been QC'd (-1)
    GOOD = "good"  # Data passed all QC checks (0)
    SUSPECT = "suspect"  # Data is questionable (1)
    BAD = "bad"  # Data failed QC checks (2)
    MISSING = "missing"  # Data is missing (9)


class MetoceanParameter(str, Enum):
    """Standard metocean parameters with units in the enum value suffix"""

    # Wave parameters
    WAVE_HEIGHT = "wave_height_m"
    WAVE_PERIOD = "wave_period_s"
    WAVE_DIRECTION = "wave_direction_deg"

    # Wind parameters
    WIND_SPEED = "wind_speed_ms"
    WIND_DIRECTION = "wind_direction_deg"

    # Current parameters
    CURRENT_SPEED = "current_speed_ms"
    CURRENT_DIRECTION = "current_direction_deg"

    # Temperature and other
    SEA_SURFACE_TEMP = "sea_surface_temp_c"
    WATER_LEVEL = "water_level_m"
    PRESSURE = "pressure_hpa"


class ParameterType(str, Enum):
    """Types of metocean parameters (extended set with more granular options)"""

    # Wave parameters
    WAVE_HEIGHT = "wave_height"
    WAVE_PERIOD = "wave_period"
    WAVE_DIRECTION = "wave_direction"
    SWELL_HEIGHT = "swell_height"
    SWELL_PERIOD = "swell_period"
    SWELL_DIRECTION = "swell_direction"

    # Wind parameters
    WIND_SPEED = "wind_speed"
    WIND_DIRECTION = "wind_direction"
    WIND_GUST = "wind_gust"

    # Current parameters
    CURRENT_SPEED = "current_speed"
    CURRENT_DIRECTION = "current_direction"

    # Temperature parameters
    SEA_SURFACE_TEMP = "sea_surface_temp"
    AIR_TEMP = "air_temp"
    WATER_TEMP = "water_temp"

    # Pressure and level
    PRESSURE = "pressure"
    WATER_LEVEL = "water_level"
    TIDE = "tide"

    # Other
    SALINITY = "salinity"
    VISIBILITY = "visibility"
    HUMIDITY = "humidity"
    DEWPOINT = "dewpoint"


class SeaState(IntEnum):
    """Sea state scale (Douglas scale 0-9)"""

    CALM = 0  # 0m waves
    SMOOTH = 1  # 0-0.1m
    SLIGHT = 2  # 0.1-0.5m
    MODERATE = 3  # 0.5-1.25m
    ROUGH = 4  # 1.25-2.5m
    VERY_ROUGH = 5  # 2.5-4m
    HIGH = 6  # 4-6m
    VERY_HIGH = 7  # 6-9m
    PHENOMENAL = 8  # 9-14m
    CONFUSED = 9  # >14m or mixed


class FetchStatus(str, Enum):
    """Status of data fetch operations"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    NO_DATA = "no_data"


# Geographic bounds for Gulf of Mexico (lon_min, lon_max, lat_min, lat_max)
GOM_BBOX: Tuple[float, float, float, float] = (-98.0, -88.0, 25.0, 31.0)

# Test stations for validation (use active stations)
# Station 42001: Mid-Gulf buoy - primary test station for NDBC
# Station 8761724: Grand Isle, LA - primary test station for CO-OPS
TEST_STATIONS: Dict[str, Dict[str, str]] = {
    "NDBC": {
        "primary": "42001",  # Mid-Gulf buoy (active)
        "backup": "42002",  # West Gulf buoy
        "description": "NDBC Gulf of Mexico buoys for testing",
    },
    "COOPS": {
        "primary": "8761724",  # Grand Isle, LA
        "backup": "8760922",  # Pilots Station East, LA
        "description": "CO-OPS Gulf Coast tide stations for testing",
    },
}

# Geographic boundaries for common regions
REGION_BOUNDS: Dict[str, Dict[str, float]] = {
    "GOM": {"lat_min": 18.0, "lat_max": 31.0, "lon_min": -98.0, "lon_max": -80.0},
    "ATLANTIC": {"lat_min": 25.0, "lat_max": 45.0, "lon_min": -80.0, "lon_max": -60.0},
    "PACIFIC": {"lat_min": 30.0, "lat_max": 50.0, "lon_min": -130.0, "lon_max": -115.0},
    "ALASKA": {"lat_min": 50.0, "lat_max": 72.0, "lon_min": -180.0, "lon_max": -130.0},
    "CARIBBEAN": {"lat_min": 10.0, "lat_max": 25.0, "lon_min": -90.0, "lon_max": -60.0},
    "NORTH_SEA": {"lat_min": 50.0, "lat_max": 62.0, "lon_min": -5.0, "lon_max": 10.0},
}

# Validation constants
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0
MIN_DEPTH_M = 0.0
MAX_DEPTH_M = 12000.0  # Mariana Trench depth

# API base URLs for data sources
NDBC_BASE_URL = "https://www.ndbc.noaa.gov"
COOPS_BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod"
OPEN_METEO_BASE_URL = "https://marine-api.open-meteo.com/v1/marine"
ERDDAP_BASE_URL = "https://erddap.ioos.us/erddap"
CMEMS_BASE_URL = "https://nrt.cmems-du.eu/motu-web/Motu"
MET_NORWAY_BASE_URL = "https://api.met.no/weatherapi"
HYCOM_BASE_URL = "https://ncss.hycom.org/thredds/ncss"

# Data source API endpoints mapping
DATA_SOURCE_URLS: Dict[str, str] = {
    "NDBC": NDBC_BASE_URL,
    "COOPS": COOPS_BASE_URL,
    "OPEN_METEO": OPEN_METEO_BASE_URL,
    "ERDDAP": ERDDAP_BASE_URL,
    "CMEMS": CMEMS_BASE_URL,
    "MET_NORWAY": MET_NORWAY_BASE_URL,
    "HYCOM": HYCOM_BASE_URL,
}

# Parameter value ranges for quality control
PARAMETER_RANGES: Dict[str, Dict[str, float]] = {
    "wave_height_m": {"min": 0.0, "max": 30.0},
    "wave_period_s": {"min": 1.0, "max": 30.0},
    "wave_direction_deg": {"min": 0.0, "max": 360.0},
    "wind_speed_ms": {"min": 0.0, "max": 100.0},
    "wind_direction_deg": {"min": 0.0, "max": 360.0},
    "wind_gust_ms": {"min": 0.0, "max": 150.0},
    "current_speed_ms": {"min": 0.0, "max": 5.0},
    "current_direction_deg": {"min": 0.0, "max": 360.0},
    "sea_surface_temp_c": {"min": -2.0, "max": 40.0},
    "water_level_m": {"min": -15.0, "max": 15.0},
    "pressure_hpa": {"min": 870.0, "max": 1084.0},
    "air_temp_c": {"min": -60.0, "max": 60.0},
}

# NDBC station type codes mapping
NDBC_STATION_TYPES: Dict[str, StationType] = {
    "buoy": StationType.BUOY,
    "cman": StationType.CMAN,
    "dart": StationType.DART,
    "ship": StationType.SHIP,
    "other": StationType.OTHER,
}

# HTTP status codes to retry
RETRYABLE_HTTP_CODES: Set[int] = {408, 429, 500, 502, 503, 504}

# Default values
DEFAULT_FETCH_TIMEOUT = 30  # seconds
DEFAULT_RATE_LIMIT_DELAY = 1.0  # seconds between requests
MAX_CONCURRENT_REQUESTS = 5
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5  # seconds

# NDBC data format column mappings (standard meteorological format)
NDBC_COLUMNS: Dict[str, str] = {
    "YY": "year",
    "MM": "month",
    "DD": "day",
    "hh": "hour",
    "mm": "minute",
    "WDIR": "wind_direction_deg",
    "WSPD": "wind_speed_ms",
    "GST": "wind_gust_ms",
    "WVHT": "wave_height_m",
    "DPD": "dominant_wave_period_s",
    "APD": "average_wave_period_s",
    "MWD": "wave_direction_deg",
    "PRES": "pressure_hpa",
    "ATMP": "air_temp_c",
    "WTMP": "sea_surface_temp_c",
    "DEWP": "dew_point_c",
    "VIS": "visibility_nm",
    "PTDY": "pressure_tendency_hpa",
    "TIDE": "water_level_ft",
}

# Missing value indicators in NDBC data
NDBC_MISSING_VALUES: Set[str] = {
    "MM",
    "999",
    "999.0",
    "9999",
    "9999.0",
    "99.0",
    "99.00",
}
