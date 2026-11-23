# ABOUTME: Data loaders for Mexico CNH module
# ABOUTME: Exports Excel and PDF parsers for CNH data files

"""
Mexico CNH Data Loaders.

Provides loaders for various data formats including Excel, CSV, and PDF.
"""

from worldenergydata.mexico_cnh.data.loaders.excel_loader import (
    COLUMN_MAPPING,
    CNHExcelLoader,
)

__all__ = [
    "CNHExcelLoader",
    "COLUMN_MAPPING",
]

# PDF parser is optional (requires pdfplumber)
try:
    from worldenergydata.mexico_cnh.data.loaders.pdf_parser import CNHPDFParser

    __all__.append("CNHPDFParser")
except ImportError:
    pass
