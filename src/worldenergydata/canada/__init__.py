# ABOUTME: Canada energy data module package initialization.
# ABOUTME: Provides UWI parsing, validation, and API clients for AER/BCER data.

"""
Canada Energy Data Module.

This module provides functionality for working with Canadian energy data,
including:
- UWI (Unique Well Identifier) parsing and validation
- AER (Alberta Energy Regulator) data integration
- BCER (British Columbia Energy Regulator) data integration
- Province-specific coordinate validation (NAD83)

Supported provinces:
- Alberta (AB) - Uses DLS survey system
- British Columbia (BC) - Uses NTS survey system
- Saskatchewan (SK) - Uses DLS survey system
- Manitoba (MB) - Uses DLS survey system
- Yukon (YT) - Uses NTS survey system
- Northwest Territories (NT) - Uses NTS survey system

Example usage:
    from worldenergydata.canada import UWIParser, CanadaDataValidator

    parser = UWIParser()
    components = parser.parse("100.16-09-010-09W4.00")
    logger.info(f"Survey system: {components.survey_system}")

    validator = CanadaDataValidator()
    result = validator.validate_uwi("100.16-09-010-09W4.00")
    logger.info(f"Valid: {result.is_valid}")
"""

from worldenergydata.canada.aer.api_client import AERClient
from worldenergydata.canada.bcer.api_client import BCERClient
from worldenergydata.canada.cache import CanadaCache, FileDownloadCache
from worldenergydata.canada.common.uwi_parser import (
    UWIComponents,
    UWIParseError,
    UWIParser,
    UWISurveySystem,
)
from worldenergydata.canada.common.validators import (
    CanadaDataValidator,
    ValidationError,
    ValidationResult,
)
from worldenergydata.canada.emerging_basins.watch_list import (
    EMERGING_BASINS,
    EmergingBasinStub,
    get_basin,
    get_emerging_basins,
)
from worldenergydata.canada.production.cnloer_loader import (

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)
    CnloerLoader,
    CnloerProductionRecord,
)

__version__ = "1.0.0"
__all__ = [
    # UWI Parsing
    "UWIParser",
    "UWIComponents",
    "UWISurveySystem",
    "UWIParseError",
    # Validation
    "CanadaDataValidator",
    "ValidationResult",
    "ValidationError",
    # API Clients
    "AERClient",
    "BCERClient",
    # Caching
    "CanadaCache",
    "FileDownloadCache",
    # C-NLOER offshore production
    "CnloerLoader",
    "CnloerProductionRecord",
    # Emerging basins
    "EmergingBasinStub",
    "EMERGING_BASINS",
    "get_emerging_basins",
    "get_basin",
]
