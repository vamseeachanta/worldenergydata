"""HTML table extraction for vessel fleet pages."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]
    Tag = None  # type: ignore[assignment,misc]


def extract_tables(
    html: str,
    css_selector: Optional[str] = None,
) -> list[list[dict[str, str]]]:
    """Extract tables from HTML as lists of row dicts.

    Each table becomes a list of dicts keyed by header text.
    If css_selector is given, only tables matching it are extracted.

    Returns a list of tables, each table is a list of row dicts.
    """
    if BeautifulSoup is None:
        raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4")

    soup = BeautifulSoup(html, "html.parser")

    if css_selector:
        tables = soup.select(css_selector)
    else:
        tables = soup.find_all("table")

    results: list[list[dict[str, str]]] = []
    for table in tables:
        rows = _parse_table(table)
        if rows:
            results.append(rows)
    return results


def extract_key_value_pairs(
    html: str,
    css_selector: Optional[str] = None,
) -> dict[str, str]:
    """Extract key-value pairs from HTML definition lists or two-column tables.

    Useful for vessel spec pages where data is presented as label/value pairs.
    """
    if BeautifulSoup is None:
        raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4")

    soup = BeautifulSoup(html, "html.parser")
    pairs: dict[str, str] = {}

    # Definition lists (<dl><dt>Key</dt><dd>Value</dd></dl>)
    container = soup.select_one(css_selector) if css_selector else soup
    if container is None:
        return pairs

    for dl in container.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        for dt, dd in zip(dts, dds):
            key = _clean_text(dt.get_text())
            val = _clean_text(dd.get_text())
            if key:
                pairs[key] = val

    # Two-column tables
    for table in container.find_all("table"):
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) == 2:
                key = _clean_text(cells[0].get_text())
                val = _clean_text(cells[1].get_text())
                if key and key not in pairs:
                    pairs[key] = val

    return pairs


def _parse_table(table: Any) -> list[dict[str, str]]:
    """Parse an HTML table element into a list of row dicts."""
    rows_data: list[dict[str, str]] = []
    header_row = table.find("thead")
    if header_row:
        headers = [
            _clean_text(th.get_text()) for th in header_row.find_all(["th", "td"])
        ]
    else:
        first_row = table.find("tr")
        if first_row is None:
            return []
        headers = [
            _clean_text(th.get_text()) for th in first_row.find_all(["th", "td"])
        ]

    if not headers:
        return []

    body = table.find("tbody") or table
    for tr in body.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) == len(headers):
            row = {
                headers[i]: _clean_text(cells[i].get_text())
                for i in range(len(headers))
            }
            if any(v for v in row.values()):
                rows_data.append(row)

    return rows_data


def _clean_text(text: str) -> str:
    """Normalise whitespace and strip."""
    return re.sub(r"\s+", " ", text).strip()
