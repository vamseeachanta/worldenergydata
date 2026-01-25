"""Backward compatibility shim - deprecated module path.

This module is deprecated and will be removed in version 2.0.0.
Please update your imports to use the new paths.

Example:
    # Old (deprecated):
    from worldenergydata.modules.bsee.data._from_zip.production_data import GetProdDataFromZip
    from worldenergydata.modules.bsee.data._from_zip.well_data import WellDataFromZip

    # New:
    from worldenergydata.modules.bsee.data.sources.zip.production_data import GetProdDataFromZip
    from worldenergydata.modules.bsee.data.sources.zip.well_data import WellDataFromZip
"""
import warnings

warnings.warn(
    "Importing from 'worldenergydata.modules.bsee.data._from_zip' is deprecated. "
    "Please use 'worldenergydata.modules.bsee.data.sources.zip' instead. "
    "This import path will be removed in version 2.0.0.",
    DeprecationWarning,
    stacklevel=2
)

from worldenergydata.modules.bsee.data.sources.zip import *
