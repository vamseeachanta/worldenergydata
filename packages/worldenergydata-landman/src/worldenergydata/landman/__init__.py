# ABOUTME: Fixture-only Landman ownership routing and county office reference data.
# ABOUTME: Exposes validated synthetic/custom records without live-source claims.
# ruff: noqa: E402

"""Fixture-only Landman ownership routing for WorldEnergyData.

The executable router supports ownership records from exactly one validated
source: the packaged synthetic sample or a direct-child custom JSON fixture.
County office information is embedded reference data, not a router provider.
Configured live providers and non-ownership operations are not executable.

Example:
    from worldenergydata.landman import Landman

    results = Landman().search_ownership(
        state="TX",
        county="MIDLAND",
        sample=True,
    )
"""

import importlib.util
import sys
import types


def _prepare_common_exceptions_import() -> bool:
    """Avoid executing unrelated heavy common exports for this leaf package."""
    if "worldenergydata.common" in sys.modules:
        return False
    spec = importlib.util.find_spec("worldenergydata.common")
    if spec is None or spec.submodule_search_locations is None:
        return False
    package = types.ModuleType("worldenergydata.common")
    package.__path__ = list(spec.submodule_search_locations)
    package.__package__ = "worldenergydata.common"
    package.__spec__ = spec
    sys.modules["worldenergydata.common"] = package
    return True


_LIGHTWEIGHT_COMMON = _prepare_common_exceptions_import()

from .exceptions import (
    APIError,
    CapabilityUnavailableError,
    ConfigurationError,
    CountyNotFoundError,
    FixtureValidationError,
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

if _LIGHTWEIGHT_COMMON:
    sys.modules.pop("worldenergydata.common", None)

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
    CountyRecordsProvider,
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
    "CountyRecordsProvider",
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
    "CapabilityUnavailableError",
    "FixtureValidationError",
    "APIError",
    "CountyNotFoundError",
    "ParsingError",
    "RateLimitError",
    "StateNotSupportedError",
    "LandmanTimeoutError",
]
