"""BSEE data package.

This package provides data loading and processing functionality for BSEE data.

Subpackages:
- loaders: Data loaders by identifier type (api, block, lease)
- sources: Data source handlers (bin files, zip files)
"""

from worldenergydata.modules.bsee.data.loaders import (
    WellRouter,
    WellData,
    BlockRouter,
    BlockDataFromLocalFiles,
    WARDataFromBin,
    LeaseRouter,
    LeaseDataFromLocalFiles,
)
from worldenergydata.modules.bsee.data.sources import (
    APIData,
    BlockData,
    LeaseData,
    GetProdDataFromZip,
    WellDataFromZip,
)

__all__ = [
    # Loaders
    "WellRouter",
    "WellData",
    "BlockRouter",
    "BlockDataFromLocalFiles",
    "WARDataFromBin",
    "LeaseRouter",
    "LeaseDataFromLocalFiles",
    # Sources
    "APIData",
    "BlockData",
    "LeaseData",
    "GetProdDataFromZip",
    "WellDataFromZip",
]
