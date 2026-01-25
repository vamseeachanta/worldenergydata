"""Backward compatibility shim - deprecated module path.

This module is deprecated and will be removed in version 2.0.0.
Please update your imports to use the new paths.

Example:
    # Old (deprecated):
    from worldenergydata.modules.bsee.data._by_api.well import WellData
    from worldenergydata.modules.bsee.data._by_api.router import WellRouter

    # New:
    from worldenergydata.modules.bsee.data.loaders.api.well import WellData
    from worldenergydata.modules.bsee.data.loaders.api.router import WellRouter
"""
import warnings

warnings.warn(
    "Importing from 'worldenergydata.modules.bsee.data._by_api' is deprecated. "
    "Please use 'worldenergydata.modules.bsee.data.loaders.api' instead. "
    "This import path will be removed in version 2.0.0.",
    DeprecationWarning,
    stacklevel=2
)

from worldenergydata.modules.bsee.data.loaders.api import *
