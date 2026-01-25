"""
WorldEnergyData Common Layer - Cross-Cutting Concerns

This module provides shared utilities, configuration, logging, exceptions,
constants, and type definitions used across all WorldEnergyData modules.

Example usage:
    from worldenergydata.common import get_logger, WorldEnergyDataError
    from worldenergydata.common.config import Settings
    from worldenergydata.common.constants import EnergyUnits
"""

from worldenergydata.common.logging import get_logger, configure_logging
from worldenergydata.common.exceptions import (
    WorldEnergyDataError,
    DataError,
    ValidationError,
    ConfigError,
    APIError,
    DataSourceError,
    ProcessingError,
)
from worldenergydata.common.config import Settings, get_settings
from worldenergydata.common.constants import EnergyUnits, UNIT_CONVERSIONS
from worldenergydata.common.types import (
    JSONDict,
    JSONList,
    PathLike,
    DataFrameLike,
    DataSourceProtocol,
    ValidatorProtocol,
    CacheProtocol,
)

__all__ = [
    # Logging
    "get_logger",
    "configure_logging",
    # Exceptions
    "WorldEnergyDataError",
    "DataError",
    "ValidationError",
    "ConfigError",
    "APIError",
    "DataSourceError",
    "ProcessingError",
    # Configuration
    "Settings",
    "get_settings",
    # Constants
    "EnergyUnits",
    "UNIT_CONVERSIONS",
    # Types
    "JSONDict",
    "JSONList",
    "PathLike",
    "DataFrameLike",
    "DataSourceProtocol",
    "ValidatorProtocol",
    "CacheProtocol",
]
