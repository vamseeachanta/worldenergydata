# ABOUTME: Common utilities package for Canada energy data module.
# ABOUTME: Contains UWI parser, validators, and shared types.

"""
Common utilities for Canada energy data processing.

This package provides:
- UWIParser: Parse and validate Canadian Unique Well Identifiers
- UWIComponents: Dataclass containing parsed UWI components
- CanadaDataValidator: Validate Canadian energy data
"""

from worldenergydata.canada.common.uwi_parser import (
    UWIComponents,
    UWIParser,
    UWISurveySystem,
)
from worldenergydata.canada.common.validators import CanadaDataValidator

__all__ = [
    "UWIParser",
    "UWIComponents",
    "UWISurveySystem",
    "CanadaDataValidator",
]
