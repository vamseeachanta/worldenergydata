"""BSEE data loaders.

This package provides modules for loading data by different identifiers:
- api: Load data by API12 well numbers
- block: Load data by block numbers
- lease: Load data by lease numbers
- infrastructure: Load platform and pipeline data
"""

from worldenergydata.bsee.data.loaders.api import WellData, WellRouter
from worldenergydata.bsee.data.loaders.block import BlockRouter
from worldenergydata.bsee.data.loaders.block import (
    DataFromLocalFiles as BlockDataFromLocalFiles,
)
from worldenergydata.bsee.data.loaders.block import WARDataFromBin
from worldenergydata.bsee.data.loaders.infrastructure import (
    InfrastructureRouter,
    PipelineLoader,
    PlatformLoader,
)
from worldenergydata.bsee.data.loaders.lease import (
    DataFromLocalFiles as LeaseDataFromLocalFiles,
)
from worldenergydata.bsee.data.loaders.lease import LeaseRouter

__all__ = [
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
]
