"""Backward compatibility shim - deprecated module path.

This module is deprecated and will be removed in version 2.0.0.
Please update your imports to use the new paths.

Example:
    # Old (deprecated):
    from worldenergydata.modules.bsee.data._from_bin.api_data import APIData
    from worldenergydata.modules.bsee.data._from_bin.block_data import BlockData
    from worldenergydata.modules.bsee.data._from_bin.lease_data import LeaseData

    # New:
    from worldenergydata.modules.bsee.data.sources.bin.api_data import APIData
    from worldenergydata.modules.bsee.data.sources.bin.block_data import BlockData
    from worldenergydata.modules.bsee.data.sources.bin.lease_data import LeaseData
"""
import warnings

warnings.warn(
    "Importing from 'worldenergydata.modules.bsee.data._from_bin' is deprecated. "
    "Please use 'worldenergydata.modules.bsee.data.sources.bin' instead. "
    "This import path will be removed in version 2.0.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export classes explicitly for backward compatibility with submodule imports
from worldenergydata.modules.bsee.data.sources.bin.api_data import APIData
from worldenergydata.modules.bsee.data.sources.bin.block_data import BlockData
from worldenergydata.modules.bsee.data.sources.bin.lease_data import LeaseData

__all__ = ["APIData", "BlockData", "LeaseData"]
