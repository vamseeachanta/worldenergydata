"""BSEE data loaders by lease number.

This module provides classes for loading data indexed by lease numbers.
"""

from worldenergydata.bsee.data.loaders.lease.local_files import DataFromLocalFiles
from worldenergydata.bsee.data.loaders.lease.router import LeaseRouter

__all__ = ["LeaseRouter", "DataFromLocalFiles"]
