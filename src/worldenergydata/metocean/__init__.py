"""
ABOUTME: Metocean data module for ocean and atmospheric observation data.
ABOUTME: Provides unified access to buoy, tide, current, and marine weather data.

Metocean Data Module

Provides retrieval and management of meteorological and oceanographic data
from public APIs including NOAA NDBC, CO-OPS, Open-Meteo, and more.
"""

# Cache
from worldenergydata.metocean.cache import (
    CacheEntry,
    CacheKey,
    CacheManager,
    OfflineStore,
)

# CLI
from worldenergydata.metocean.cli import app as cli_app

# Clients
from worldenergydata.metocean.clients import (
    BaseClient,
    COOPSClient,
    COOPSCurrent,
    COOPSStation,
    COOPSTidePrediction,
    COOPSWaterLevel,
    FetchResult,
    NDBCClient,
    NDBCObservation,
    NDBCStation,
    OpenMeteoClient,
    OpenMeteoForecast,
)

# Configuration
from worldenergydata.metocean.config import (
    MetoceanConfig,
    get_config,
    reload_config,
)

# Constants and types
from worldenergydata.metocean.constants import (
    GOM_BBOX,
    REGION_BOUNDS,
    DataSource,
    DataType,
    FetchStatus,
    MetoceanParameter,
    ParameterType,
    QualityFlag,
    SeaState,
    StationType,
)

# Database
from worldenergydata.metocean.database import (
    Base,
    DatabaseManager,
    FetchLog,
    Forecast,
    GridPoint,
    Observation,
    Station,
    get_db_manager,
    init_database,
)

# Exceptions
from worldenergydata.metocean.exceptions import (
    CacheError,
    ClientError,
    ConfigurationError,
    DatabaseError,
    DataNotFoundError,
    ExportError,
    HTTPError,
    MetoceanError,
    ParsingError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

# NDBC facade — scatter matrix, seasonal filtering, Weibull, wave rose (WRK-316)
from worldenergydata.metocean.ndbc import (
    build_scatter_matrix,
    filter_by_season,
    fit_weibull_hs,
    parse_stdmet_file,
    parse_stdmet_line,
    wave_rose,
)

# Processors
from worldenergydata.metocean.processors import (
    DataHarmonizer,
    HarmonizedObservation,
    LengthUnit,
    PressureUnit,
    QualityCheckResult,
    QualityFilter,
    SpeedUnit,
    TempUnit,
    UnitConverter,
)

__all__ = [
    # Config
    "MetoceanConfig",
    "get_config",
    "reload_config",
    # Constants
    "DataSource",
    "DataType",
    "StationType",
    "MetoceanParameter",
    "ParameterType",
    "QualityFlag",
    "FetchStatus",
    "SeaState",
    "GOM_BBOX",
    "REGION_BOUNDS",
    # Exceptions
    "MetoceanError",
    "ConfigurationError",
    "DatabaseError",
    "ValidationError",
    "ClientError",
    "HTTPError",
    "RateLimitError",
    "TimeoutError",
    "ParsingError",
    "DataNotFoundError",
    "CacheError",
    "ExportError",
    # Clients
    "BaseClient",
    "FetchResult",
    "NDBCClient",
    "NDBCStation",
    "NDBCObservation",
    "COOPSClient",
    "COOPSStation",
    "COOPSWaterLevel",
    "COOPSCurrent",
    "COOPSTidePrediction",
    "OpenMeteoClient",
    "OpenMeteoForecast",
    # Processors
    "DataHarmonizer",
    "HarmonizedObservation",
    "UnitConverter",
    "SpeedUnit",
    "LengthUnit",
    "TempUnit",
    "PressureUnit",
    "QualityFilter",
    "QualityCheckResult",
    # Cache
    "CacheManager",
    "CacheKey",
    "CacheEntry",
    "OfflineStore",
    # Database
    "Base",
    "Station",
    "Observation",
    "GridPoint",
    "Forecast",
    "FetchLog",
    "DatabaseManager",
    "get_db_manager",
    "init_database",
    # CLI
    "cli_app",
    # NDBC scatter / seasonal / Weibull / wave-rose helpers (WRK-316)
    "build_scatter_matrix",
    "filter_by_season",
    "fit_weibull_hs",
    "parse_stdmet_file",
    "parse_stdmet_line",
    "wave_rose",
]
