"""Backward compatibility shim for lease_data module.

This module is deprecated and will be removed in version 2.0.0.
Please use worldenergydata.modules.bsee.data.sources.bin.lease_data instead.
"""
import warnings

warnings.warn(
    "Importing from 'worldenergydata.modules.bsee.data._from_bin.lease_data' is deprecated. "
    "Please use 'worldenergydata.modules.bsee.data.sources.bin.lease_data' instead. "
    "This import path will be removed in version 2.0.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new location
from worldenergydata.modules.bsee.data.sources.bin.lease_data import *
from worldenergydata.modules.bsee.data.sources.bin.lease_data import LeaseData

__all__ = ["LeaseData"]
