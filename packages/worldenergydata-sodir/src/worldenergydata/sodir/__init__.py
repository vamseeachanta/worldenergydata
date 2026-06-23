"""
SODIR Integration Module for WorldEnergyData.

This module provides integration with the Norwegian Offshore Directorate (SODIR)
data sources, enabling collection and analysis of Norwegian Continental Shelf
petroleum data.

Key Features:
- REST API integration with factmaps.sodir.no
- Support for blocks, wellbores, fields, discoveries, and surveys data
- Cross-regional analysis with BSEE data
- Rate-limited API client with caching
- Data normalization and validation
"""

from .sodir import Sodir

__version__ = "1.0.0"
__all__ = ["Sodir"]
