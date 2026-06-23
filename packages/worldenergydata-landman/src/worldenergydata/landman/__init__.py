# ABOUTME: Landman module for mineral ownership, lease records, and title data
# ABOUTME: Provides unified access to county records and future subscription services

"""
Landman Module for WorldEnergyData.

This module provides integration with public county records and commercial
title/lease data services for mineral ownership research and due diligence.

Key Features:
- County clerk record searches (deed, mortgage, mineral lease records)
- State GIS data for oil/gas wells and permits
- BLM federal land records (mining claims, fluid mineral leases)
- Legal description parsing and validation (Section-Township-Range)
- Mineral ownership chain of title analysis
- Lease term tracking and expiration monitoring
- Multiple provider support (county records, commercial services)
- Standardized data models for ownership and lease records
- Rate limiting and caching for public record sources

Example usage:
    from worldenergydata.landman import Landman

    # Create landman instance
    landman = Landman()

    # Search for mineral ownership
    results = landman.search_ownership(
        state="TX",
        county="MIDLAND",
        legal_description="Section 12, Block 42, T-1-S"
    )

    # Get lease records
    leases = landman.get_lease_records(
        state="TX",
        county="MIDLAND",
        owner_name="Smith"
    )

    # Using providers directly
    from worldenergydata.landman import StateGISProvider

    with StateGISProvider() as provider:
        wells = provider.search_wells_by_location("TX", "REEVES")
"""

from .exceptions import (
    APIError,
    ConfigurationError,
    CountyNotFoundError,
    LandmanError,
    ParsingError,
)
from .exceptions import ProviderError as LandmanProviderError
from .exceptions import (
    RateLimitError,
)
from .exceptions import RecordNotFoundError as LandmanRecordNotFoundError
from .exceptions import (
    StateNotSupportedError,
)
from .exceptions import TimeoutError as LandmanTimeoutError
from .landman import Landman, LandmanValidationError
from .models import (
    CountyClerkInfo,
    FluidMineralLease,
    FluidMineralSearchResult,
    FluidMineralType,
    InterestType,
    LeaseRecord,
    LeaseStatus,
    MineralClaimType,
    MineralOwnershipRecord,
    MiningClaim,
    MiningClaimSearchResult,
    OwnerSearchResult,
    PermitInfo,
    PermitSearchResult,
    RecordType,
    SearchResult,
    TitleRecord,
    WellInfo,
    WellSearchResult,
    WellStatus,
)
from .providers import (
    BaseProvider,
    BLMProvider,
    CountyReferenceProvider,
    StateGISProvider,
)
from .validators import LandmanDataValidator

# Alias for backward compatibility
LandmanAuthError = ConfigurationError

__version__ = "1.0.0"
__all__ = [
    # Main class
    "Landman",
    # Providers
    "BaseProvider",
    "StateGISProvider",
    "BLMProvider",
    "CountyReferenceProvider",
    # Models - Wells and Permits
    "WellInfo",
    "WellStatus",
    "WellSearchResult",
    "PermitInfo",
    "PermitSearchResult",
    # Models - Mining and BLM
    "MiningClaim",
    "MiningClaimSearchResult",
    "MineralClaimType",
    "FluidMineralLease",
    "FluidMineralSearchResult",
    "FluidMineralType",
    # Models - County Records
    "CountyClerkInfo",
    "RecordType",
    "SearchResult",
    # Models - Ownership and Leases
    "MineralOwnershipRecord",
    "LeaseRecord",
    "LeaseStatus",
    "InterestType",
    "TitleRecord",
    "OwnerSearchResult",
    # Validators
    "LandmanDataValidator",
    # Errors
    "LandmanError",
    "LandmanProviderError",
    "LandmanRecordNotFoundError",
    "LandmanValidationError",
    "LandmanAuthError",
]
