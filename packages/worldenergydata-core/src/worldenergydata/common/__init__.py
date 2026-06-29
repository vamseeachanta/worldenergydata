"""
WorldEnergyData Common Layer - Cross-Cutting Concerns

This module provides shared utilities, configuration, logging, exceptions,
constants, and type definitions used across all WorldEnergyData modules.

Submodules:
    logging: Centralized logging configuration with module-specific loggers
    config: Settings management with environment variable support
    exceptions: Hierarchical exception classes for error handling
    constants: Energy unit constants and conversion factors
    types: Type aliases and protocol definitions
    validators: Common validation utilities
    decorators: Shared decorators (retry, cache, timing)

Example usage:

```python
# Logging
from worldenergydata.common import get_logger, configure_logging
logger = get_logger(__name__)
logger.info("Processing data")

# Exception handling
from worldenergydata.common import DataError, ValidationError
try:
    process_data(data)
except ValidationError as e:
    logger.error(f"Validation failed: {e}")

# Configuration
from worldenergydata.common import Settings, get_settings
settings = get_settings()
data_dir = settings.data_dir

# Constants
from worldenergydata.common import EnergyUnits, UNIT_CONVERSIONS
conversion = UNIT_CONVERSIONS[EnergyUnits.BTU][EnergyUnits.MWH]

# Type hints
from worldenergydata.common import JSONDict, PathLike, DataFrameLike
def load_config(path: PathLike) -> JSONDict:
    ...
```
"""

from worldenergydata.common.config import Settings, get_settings
from worldenergydata.common.constants import UNIT_CONVERSIONS, EnergyUnits
from worldenergydata.common.exceptions import (
    APIError,
    ConfigError,
    DataError,
    DataSourceError,
    ProcessingError,
    ValidationError,
    WorldEnergyDataError,
)
from worldenergydata.common.logging import configure_logging, get_logger
from worldenergydata.common.types import (
    CacheProtocol,
    DataFrameLike,
    DataSourceProtocol,
    JSONDict,
    JSONList,
    PathLike,
    ValidatorProtocol,
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
