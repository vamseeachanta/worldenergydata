"""Backward compatibility shim - deprecated module path.

This module is deprecated and will be removed in version 2.0.0.
Please update your imports to use the new paths.

Example:
    # Old (deprecated):
    from worldenergydata.modules.bsee.data._by_block.router import BlockRouter
    from worldenergydata.modules.bsee.data._by_block.data_from_local_files import DataFromLocalFiles
    from worldenergydata.modules.bsee.data._by_block.war_data import WARDataFromBin

    # New:
    from worldenergydata.modules.bsee.data.loaders.block.router import BlockRouter
    from worldenergydata.modules.bsee.data.loaders.block.local_files import DataFromLocalFiles
    from worldenergydata.modules.bsee.data.loaders.block.war_data import WARDataFromBin
"""
import warnings

warnings.warn(
    "Importing from 'worldenergydata.modules.bsee.data._by_block' is deprecated. "
    "Please use 'worldenergydata.modules.bsee.data.loaders.block' instead. "
    "This import path will be removed in version 2.0.0.",
    DeprecationWarning,
    stacklevel=2
)

from worldenergydata.modules.bsee.data.loaders.block import *
