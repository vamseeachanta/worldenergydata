"""Backward compatibility shim for data_from_local_files module.

This module is deprecated and will be removed in version 2.0.0.
Please use worldenergydata.modules.bsee.data.loaders.lease.local_files instead.
"""
import warnings

warnings.warn(
    "Importing from 'worldenergydata.modules.bsee.data._by_lease.data_from_local_files' is deprecated. "
    "Please use 'worldenergydata.modules.bsee.data.loaders.lease.local_files' instead. "
    "This import path will be removed in version 2.0.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from the new location
from worldenergydata.modules.bsee.data.loaders.lease.local_files import DataFromLocalFiles

__all__ = ["DataFromLocalFiles"]
