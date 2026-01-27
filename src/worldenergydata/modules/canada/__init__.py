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
    from worldenergydata.modules.canada import UWIParser, CanadaDataValidator

    parser = UWIParser()
    components = parser.parse("100.16-09-010-09W4.00")
    print(f"Survey system: {components.survey_system}")

    validator = CanadaDataValidator()
    result = validator.validate_uwi("100.16-09-010-09W4.00")
    print(f"Valid: {result.is_valid}")
"""

from worldenergydata.modules.canada.aer.api_client import AERClient
from worldenergydata.modules.canada.bcer.api_client import BCERClient
from worldenergydata.modules.canada.cache import CanadaCache, FileDownloadCache
from worldenergydata.modules.canada.common.uwi_parser import (
    UWIComponents,
    UWIParseError,
    UWIParser,
    UWISurveySystem,
)
from worldenergydata.modules.canada.common.validators import (
    CanadaDataValidator,
    ValidationError,
    ValidationResult,
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
]
