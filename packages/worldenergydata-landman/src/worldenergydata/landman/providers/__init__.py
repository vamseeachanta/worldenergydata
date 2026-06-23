# ABOUTME: Providers package for Landman module
# ABOUTME: Exports all data providers for county records and land data

"""
Landman Providers Package

This package contains data providers for accessing county records,
state GIS data, and federal land information.

Providers:
    - StateGISProvider: State oil/gas commission GIS data
    - BLMProvider: Bureau of Land Management federal land records
    - CountyReferenceProvider: County clerk office information

Example usage:
    from worldenergydata.landman.providers import (
        StateGISProvider,
        BLMProvider,
        CountyReferenceProvider,
    )

    # Search Texas wells
    with StateGISProvider() as provider:
        results = provider.search_wells_by_location("TX", "REEVES")

    # Search BLM mining claims
    with BLMProvider() as provider:
        claims = provider.search_mining_claims("NM", county="LEA")

    # Get county clerk info
    with CountyReferenceProvider() as provider:
        info = provider.get_county_clerk_info("TX", "MIDLAND")
"""

from worldenergydata.landman.providers.base import (
    BaseProvider,
    CacheEntry,
    MemoryCache,
)
from worldenergydata.landman.providers.blm import BLMProvider
from worldenergydata.landman.providers.county_reference import (
    CountyReferenceProvider,
)
from worldenergydata.landman.providers.state_gis import StateGISProvider

__all__ = [
    # Base classes
    "BaseProvider",
    "MemoryCache",
    "CacheEntry",
    # Providers
    "StateGISProvider",
    "BLMProvider",
    "CountyReferenceProvider",
]
