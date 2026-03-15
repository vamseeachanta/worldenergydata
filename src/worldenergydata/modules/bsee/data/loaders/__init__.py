"""BSEE data loaders.

This package provides modules for loading data by different identifiers:
- api: Load data by API12 well numbers
- block: Load data by block numbers
- lease: Load data by lease numbers
"""

from worldenergydata.modules.bsee.data.loaders.api import WellData, WellRouter
from worldenergydata.modules.bsee.data.loaders.block import BlockRouter
from worldenergydata.modules.bsee.data.loaders.block import (
    DataFromLocalFiles as BlockDataFromLocalFiles,
)
from worldenergydata.modules.bsee.data.loaders.block import WARDataFromBin
from worldenergydata.modules.bsee.data.loaders.lease import (
    DataFromLocalFiles as LeaseDataFromLocalFiles,
)
from worldenergydata.modules.bsee.data.loaders.lease import LeaseRouter

__all__ = [
    "WellRouter",
    "WellData",
    "BlockRouter",
    "BlockDataFromLocalFiles",
    "WARDataFromBin",
    "LeaseRouter",
    "LeaseDataFromLocalFiles",
]
