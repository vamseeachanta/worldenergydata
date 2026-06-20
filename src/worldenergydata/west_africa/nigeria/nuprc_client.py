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

import hashlib
import io
import logging
from typing import Any, Dict, List, Optional

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
        # Many regulator sites block the default ``python-requests/2.x`` UA.
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; WorldEnergyData/1.0; "
                "+https://github.com/vamseeachanta/worldenergydata)"
            )
        }

    def _cache_key(self, url: str) -> str:
        return hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()

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

                resp = requests.get(
                    url, timeout=self.timeout, headers=self.headers
                )
                if resp.status_code == 200:
                    data = resp.content
                    if self.cache_enabled:
                        self._cache[cache_key] = data
                    return data

                # Transient server / rate-limit errors are common on
                # nuprc.gov.ng during heavy report releases — retry those.
                # Client errors (4xx, except 429) are terminal: raise now.
                if resp.status_code in (429,) or resp.status_code >= 500:
                    last_error = NuprcAPIError(
                        f"HTTP {resp.status_code} downloading {url}",
                        status_code=resp.status_code,
                    )
                    logger.warning(
                        "Download attempt %d/%d got HTTP %d, retrying",
                        attempt + 1,
                        self.max_retries + 1,
                        resp.status_code,
                    )
                    continue

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
    This function handles gracefully, returning an empty list on failure.

    Args:
        pdf_bytes: Raw PDF content bytes, or None.

    Returns:
        List of dicts with keys: blend, volume_kbd, month, year.
        Returns empty list if parsing fails or input is empty/None.
    """
    if not pdf_bytes:
        return []

    if pdfplumber is None:
        logger.warning("pdfplumber not installed; cannot parse PDF tables")
        return []

    results: List[Dict[str, Any]] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    rows = _parse_blend_rows_from_table(table)
                    results.extend(rows)
    except Exception as exc:
        logger.warning("PDF parsing failed: %s", exc)

    return results


def _parse_blend_rows_from_table(
    table: Optional[List[List[Any]]],
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

    if blend_col is None or vol_col is None:
        return []

    for row in table[1:]:
        if not row or len(row) <= max(blend_col, vol_col):
            continue

        blend_name = str(row[blend_col]).strip().upper() if row[blend_col] else None
        volume_raw = str(row[vol_col]).strip() if row[vol_col] else None

        if not blend_name or not volume_raw:
            continue

        try:
            volume_kbd = float(volume_raw.replace(",", ""))
        except (ValueError, AttributeError):
            continue

        rows.append(
            {
                "blend": blend_name,
                "volume_kbd": volume_kbd,
                "month": None,
                "year": None,
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
        Returns empty list on network or parsing error.
    """
    if requests is None or BeautifulSoup is None:
        logger.warning("requests or bs4 not installed; cannot scrape links")
        return []

    try:
        resp = requests.get(portal_url, timeout=30)
        if resp.status_code != 200:
            logger.warning("Portal returned HTTP %d", resp.status_code)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        pdf_urls = []
        for tag in soup.find_all("a", href=True):
            href: str = tag["href"]
            if href.lower().endswith(".pdf"):
                if href.startswith("http"):
                    pdf_urls.append(href)
                else:
                    pdf_urls.append(NUPRC_BASE_URL + href)

        return pdf_urls

    except Exception as exc:
        logger.warning("Failed to scrape report URLs: %s", exc)
        return []
