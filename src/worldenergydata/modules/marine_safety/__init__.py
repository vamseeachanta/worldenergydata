"""
Marine Safety Module - Offshore Energy Industry Safety Incident Tracking

This module provides comprehensive tracking and analysis of marine safety incidents
in the offshore energy industry, including oil rigs, wind farms, and related vessels.

Version: 1.0.0
Author: WorldEnergyData Team
License: MIT
"""

from typing import List

__version__ = "1.0.0"
__author__ = "WorldEnergyData Team"
__all__: List[str] = [
    "config",
    "constants",
    "exceptions",
    "database",
    "scrapers",
    "utils",
]

# Module-level exports
from worldenergydata.modules.marine_safety import config
from worldenergydata.modules.marine_safety import constants
from worldenergydata.modules.marine_safety import exceptions
from worldenergydata.modules.marine_safety import database
from worldenergydata.modules.marine_safety import scrapers
from worldenergydata.modules.marine_safety import utils
