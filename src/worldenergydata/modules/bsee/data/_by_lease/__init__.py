"""Backward compatibility shim - deprecated module path.

This module is deprecated and will be removed in version 2.0.0.
Please update your imports to use the new paths.

Example:
    # Old (deprecated):
    from worldenergydata.modules.bsee.data._by_lease.router import LeaseRouter
    from worldenergydata.modules.bsee.data._by_lease.data_from_local_files import DataFromLocalFiles

    # New:
    from worldenergydata.modules.bsee.data.loaders.lease.router import LeaseRouter
    from worldenergydata.modules.bsee.data.loaders.lease.local_files import DataFromLocalFiles
"""
import warnings

warnings.warn(
    "Importing from 'worldenergydata.modules.bsee.data._by_lease' is deprecated. "
    "Please use 'worldenergydata.modules.bsee.data.loaders.lease' instead. "
    "This import path will be removed in version 2.0.0.",
    DeprecationWarning,
    stacklevel=2
)

from worldenergydata.modules.bsee.data.loaders.lease import *
