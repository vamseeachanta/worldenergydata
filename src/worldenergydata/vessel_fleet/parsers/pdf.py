"""PDF spec sheet parser for vessel fleet data."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore[assignment]


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    if pdfplumber is None:
        raise ImportError("pdfplumber is required: pip install pdfplumber")

    text_parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_tables_from_pdf(pdf_path: str) -> list[list[list[str]]]:
    """Extract tables from a PDF file.

    Returns a list of tables, each table is a list of rows,
    each row is a list of cell strings.
    """
    if pdfplumber is None:
        raise ImportError("pdfplumber is required: pip install pdfplumber")

    all_tables: list[list[list[str]]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    cleaned = [
                        [cell.strip() if cell else "" for cell in row]
                        for row in table
                        if row
                    ]
                    if cleaned:
                        all_tables.append(cleaned)
    return all_tables


def extract_key_value_from_text(
    text: str,
    separator: str = ":",
) -> dict[str, str]:
    """Extract key-value pairs from colon-separated text lines.

    Handles spec sheet formats like:
        Water Depth Rating: 12,000 ft
        Year Built: 2014
    """
    pairs: dict[str, str] = {}
    for line in text.split("\n"):
        line = line.strip()
        if separator in line:
            parts = line.split(separator, 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip()
                if key and val:
                    pairs[key] = val
    return pairs
