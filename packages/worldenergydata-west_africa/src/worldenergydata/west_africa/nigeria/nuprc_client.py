"""
Nigeria NUPRC PDF downloader and blend table extractor.

NUPRC (Nigerian Upstream Petroleum Regulatory Commission) publishes
monthly crude oil and condensate production reports as PDFs at:
  https://www.nuprc.gov.ng/oil-production-status-report/

This module provides:
- PDF download with caching and retry
- pdfplumber-based table extraction for blend production tables
- Link scraping for available report URLs
"""

import calendar
import hashlib
import io
import logging
import math
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlsplit

try:
    import requests
    from requests.exceptions import RequestException
except ImportError:
    requests = None
    RequestException = Exception

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

logger = logging.getLogger(__name__)

NUPRC_BASE_URL = "https://www.nuprc.gov.ng"
NUPRC_PORTAL_PATH = "/oil-production-status-report/"

# Column keywords to identify blend production tables in PDFs
BLEND_TABLE_KEYWORDS = [
    "crude",
    "blend",
    "stream",
    "production",
    "thousand barrels",
]


class NuprcAPIError(Exception):
    """Raised when NUPRC PDF download or parsing fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class NuprcClient:
    """
    HTTP client for downloading NUPRC production report PDFs.

    Features:
    - PDF download with in-memory caching
    - Configurable timeout and retry
    - Link scraping for report index page
    """

    def __init__(
        self,
        base_url: str = NUPRC_BASE_URL,
        timeout: int = 30,
        cache_enabled: bool = True,
        max_retries: int = 2,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self.max_retries = max_retries
        self._cache: Dict[str, bytes] = {}

    def _cache_key(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def download_pdf(self, url: str) -> bytes:
        """
        Download a PDF by URL, using cache if enabled.

        Args:
            url: Full URL of the PDF to download.

        Returns:
            Raw PDF bytes.

        Raises:
            NuprcAPIError: On HTTP error or network failure.
        """
        cache_key = self._cache_key(url)
        if self.cache_enabled and cache_key in self._cache:
            logger.debug("Cache hit for %s", url)
            return self._cache[cache_key]

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                if requests is None:
                    raise NuprcAPIError("requests library not installed")

                resp = requests.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.content
                    if self.cache_enabled:
                        self._cache[cache_key] = data
                    return data

                raise NuprcAPIError(
                    f"HTTP {resp.status_code} downloading {url}",
                    status_code=resp.status_code,
                )

            except NuprcAPIError:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Download attempt %d/%d failed: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                )

        raise NuprcAPIError(
            f"Failed to download {url} after {self.max_retries + 1} attempts"
            + (f": {last_error}" if last_error else "")
        )


def parse_blend_table_from_pdf(pdf_bytes: Optional[bytes]) -> List[Dict[str, Any]]:
    """
    Extract blend production table rows from NUPRC PDF bytes.

    NUPRC PDFs use inconsistent table layouts across years.
    A nonempty PDF must supply an unambiguous period and explicit kbd units.
    Repeated blend/period values are retained once; conflicts raise an error.

    Args:
        pdf_bytes: Raw PDF content bytes, or None.

    Returns:
        List of dicts with keys: blend, volume_kbd, month, year.
        Returns empty list for empty/None input. Unsupported or malformed
        nonempty reports raise NuprcAPIError rather than returning partial data.
    """
    if not pdf_bytes:
        return []

    if pdfplumber is None:
        raise NuprcAPIError("pdfplumber not installed; cannot parse PDF tables")

    records = {}
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                tables = page.extract_tables()
                for table in tables:
                    rows = _parse_blend_rows_from_table(table, text)
                    for row in rows:
                        key = (row["blend"], row["year"], row["month"])
                        if key in records and records[key] != row:
                            raise NuprcAPIError(
                                "Conflicting repeated blend/period rows"
                            )
                        records[key] = row
    except NuprcAPIError:
        raise
    except Exception as exc:
        raise NuprcAPIError("PDF parsing failed") from exc

    if not records:
        raise NuprcAPIError("No supported blend records in PDF")
    return list(records.values())


def _report_period(text: str):
    """Accept one named calendar month/year, never the requested period.

    Multiple dates are ambiguous; caller must supply a supported table rather
    than infer which date labels the data. Calendar names: Python Library
    Reference, calendar.month_name (2025).
    """
    names = {
        name.casefold(): month for month, name in enumerate(calendar.month_name) if name
    }
    pattern = r"\b(" + "|".join(names) + r")[\s,\-/]+(\d{4})\b"
    periods = {
        (int(year), names[name.casefold()])
        for name, year in re.findall(pattern, text, flags=re.IGNORECASE)
    }
    if len(periods) != 1:
        raise NuprcAPIError("Report period is missing or ambiguous")
    return periods.pop()


def _parse_blend_rows_from_table(
    table: Optional[List[List[Any]]],
    page_text: str = "",
) -> List[Dict[str, Any]]:
    """
    Parse blend/volume rows from a pdfplumber-extracted table.

    Args:
        table: 2D list of cell values from pdfplumber.

    Returns:
        List of parsed blend record dicts.
    """
    if not table or len(table) < 2:
        return []

    rows = []
    header = [str(cell).lower().strip() if cell else "" for cell in table[0]]

    # Identify column indices heuristically
    blend_col = _find_column(header, ["blend", "stream", "crude", "name"])
    vol_col = _find_column(header, ["volume", "kbd", "production", "quantity"])

    if blend_col is None or vol_col is None or blend_col == vol_col:
        return []

    # No volume-to-rate inference: only explicit thousand-barrels/day labels
    # are supported. BIPM SI Brochure, 9th ed. (2019), section 3, Table 7.
    context = " ".join(header) + " " + page_text.lower()
    if not re.search(r"\bkbd\b|thousand barrels (?:per day|/day)", context):
        raise NuprcAPIError("Production units are not explicitly kbd")
    year, month = _report_period(" ".join(header) + " " + page_text)

    for row in table[1:]:
        if not row or len(row) <= max(blend_col, vol_col):
            continue

        blend_name = str(row[blend_col]).strip().upper() if row[blend_col] else None
        volume_raw = str(row[vol_col]).strip() if row[vol_col] is not None else None

        if not blend_name or not volume_raw:
            continue
        # Total labels are report aggregates, not blend identities (SF1).
        if re.match(r"^(?:(?:GRAND|SUB)[\s-]*)?TOTAL\b", blend_name):
            continue
        if blend_name.lower() == header[blend_col]:
            continue  # Repeated table header on a continuation page.

        try:
            volume_kbd = float(volume_raw.replace(",", ""))
        except (ValueError, AttributeError) as exc:
            raise NuprcAPIError("Invalid blend production value") from exc
        if not math.isfinite(volume_kbd) or volume_kbd < 0:
            raise NuprcAPIError("Blend production must be finite and nonnegative")

        rows.append(
            {
                "blend": blend_name,
                "volume_kbd": volume_kbd,
                "month": month,
                "year": year,
            }
        )

    return rows


def _find_column(header: List[str], keywords: List[str]) -> Optional[int]:
    """Return index of first header column matching any keyword."""
    for idx, cell in enumerate(header):
        for kw in keywords:
            if kw in cell:
                return idx
    return None


def list_report_urls(
    portal_url: str = NUPRC_BASE_URL + NUPRC_PORTAL_PATH,
) -> List[str]:
    """
    Scrape PDF report links from the NUPRC production status portal.

    Args:
        portal_url: URL of the NUPRC report index page.

    Returns:
        List of absolute PDF URLs found on the page.
        Raises NuprcAPIError on dependency, transport, HTTP or discovery failure.
    """
    if requests is None or BeautifulSoup is None:
        raise NuprcAPIError("requests or bs4 not installed; cannot scrape links")

    try:
        resp = requests.get(portal_url, timeout=30)
        if resp.status_code != 200:
            raise NuprcAPIError(
                "Report portal HTTP error", status_code=resp.status_code
            )

        soup = BeautifulSoup(resp.text, "html.parser")
        pdf_urls = []
        for tag in soup.find_all("a", href=True):
            href: str = tag["href"]
            # RFC 3986 (2005), section 5: resolve against the actual portal.
            url = urljoin(portal_url, href)
            parts = urlsplit(url)
            if (
                parts.scheme in {"http", "https"}
                and parts.path.lower().endswith(".pdf")
                and url not in pdf_urls
            ):
                pdf_urls.append(url)

        if not pdf_urls:
            raise NuprcAPIError("No PDF report links found in portal")
        return pdf_urls

    except NuprcAPIError:
        raise
    except Exception as exc:
        raise NuprcAPIError("Failed to discover report URLs") from exc
