"""BSEE data loaders.

This package provides modules for loading data by different identifiers:
- api: Load data by API12 well numbers
- block: Load data by block numbers
- lease: Load data by lease numbers
"""

from worldenergydata.modules.bsee.data.loaders.api import WellRouter, WellData
from worldenergydata.modules.bsee.data.loaders.block import BlockRouter, DataFromLocalFiles as BlockDataFromLocalFiles, WARDataFromBin
from worldenergydata.modules.bsee.data.loaders.lease import LeaseRouter, DataFromLocalFiles as LeaseDataFromLocalFiles

__all__ = [
    "WellRouter",
    "WellData",
    "BlockRouter",
    "BlockDataFromLocalFiles",
    "WARDataFromBin",
    "LeaseRouter",
    "LeaseDataFromLocalFiles",
]
