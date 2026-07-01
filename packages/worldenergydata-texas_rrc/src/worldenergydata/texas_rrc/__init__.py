# ABOUTME: Texas Railroad Commission module for oil and gas data integration
# ABOUTME: Provides access to Texas production, well, and drilling permit data

"""Texas Railroad Commission Integration Module for WorldEnergyData.

This module provides integration with the Texas Railroad Commission (RRC)
data sources, enabling collection and analysis of Texas oil and gas data.

Key Features:
- PDQ data dump integration for production data
- Wellbore data access via RRC public queries
- Drilling permit tracking
- API number validation (42-XXX-XXXXX format)
- District-based data organization
- Data normalization and validation
- Rate limiting and caching
- Comprehensive error handling

Example usage:
    from worldenergydata.texas_rrc import TexasRRCClient

    # Create client
    client = TexasRRCClient()

    # Download production data
    pdq_path = client.download_pdq_dump(
        output_dir=Path("./data"),
        data_type="og_production"
    )

    # Query specific well
    well_data = client.get_well_by_api("42-123-45678")
"""

from importlib import import_module

__version__ = "1.0.0"
_LAZY_EXPORTS = {
    "TexasRRC": ".texas_rrc",
    "TexasRRCClient": ".api_client",
    "TexasRRCCache": ".cache",
    "FileDownloadCache": ".cache",
    "TexasRRCError": ".errors",
    "TexasRRCAPIError": ".errors",
    "TexasRRCRateLimitError": ".errors",
    "TexasRRCConfigurationError": ".errors",
    "TexasRRCDataError": ".errors",
    "TexasRRCValidationError": ".errors",
}


def __getattr__(name: str):
    """Load public Texas RRC exports only when they are requested."""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_LAZY_EXPORTS[name], __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = [
    # Main class
    "TexasRRC",
    # API Client
    "TexasRRCClient",
    # Cache
    "TexasRRCCache",
    "FileDownloadCache",
    # Errors
    "TexasRRCError",
    "TexasRRCAPIError",
    "TexasRRCRateLimitError",
    "TexasRRCConfigurationError",
    "TexasRRCDataError",
    "TexasRRCValidationError",
]
