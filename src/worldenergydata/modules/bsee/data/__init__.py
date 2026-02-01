"""BSEE data package.

This package provides data loading and processing functionality for BSEE data.

Subpackages:
- loaders: Data loaders by identifier type (api, block, lease, infrastructure)
- sources: Data source handlers (bin files, zip files)
"""

from worldenergydata.modules.bsee.data.loaders import (
    BlockDataFromLocalFiles,
    BlockRouter,
    InfrastructureRouter,
    LeaseDataFromLocalFiles,
    LeaseRouter,
    PipelineLoader,
    PlatformLoader,
    WARDataFromBin,
    WellData,
    WellRouter,
)
from worldenergydata.modules.bsee.data.sources import (
    APIData,
    BlockData,
    DeepwaterStructureDataFromZip,
    GetProdDataFromZip,
    LeaseData,
    PipelineLocationDataFromZip,
    PipelinePermitDataFromZip,
    PlatformDataFromZip,
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
    "InfrastructureRouter",
    "PlatformLoader",
    "PipelineLoader",
    # Sources
    "APIData",
    "BlockData",
    "LeaseData",
    "GetProdDataFromZip",
    "WellDataFromZip",
    "PlatformDataFromZip",
    "PipelinePermitDataFromZip",
    "DeepwaterStructureDataFromZip",
    "PipelineLocationDataFromZip",
]
