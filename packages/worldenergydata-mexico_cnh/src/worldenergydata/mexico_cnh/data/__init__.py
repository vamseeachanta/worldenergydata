# ABOUTME: Mexico CNH data collection components
# ABOUTME: Handles data fetching from SIH dashboard and CNH portals

"""
Mexico CNH Data Collection Module.

Provides data fetching capabilities from Mexico CNH data sources including
the SIH dashboard and various public portals.
"""

from .loaders import COLUMN_MAPPING, CNHExcelLoader
from .mexico_cnh_data import MexicoCNHData

__all__ = [
    "MexicoCNHData",
    "CNHExcelLoader",
    "COLUMN_MAPPING",
]

# PDF parser is optional
try:
    from .loaders import CNHPDFParser

    __all__.append("CNHPDFParser")
except ImportError:
    pass
