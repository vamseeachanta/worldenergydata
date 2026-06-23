"""EIA API v2 client for weekly petroleum and natural gas feed ingestion.

API base: https://api.eia.gov/v2/
Auth: EIA_API_KEY environment variable (validated at startup).

Key weekly endpoints:
  petroleum/sum/snd/w/           — Weekly petroleum status (crude, stocks, imports)
  natural-gas/stor/sum/dcu/nus/w/ — Weekly natural gas storage

Response format: JSON with response.data array.
Pagination: offset + length query params.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

EIA_BASE_URL: str = "https://api.eia.gov/v2"

# Weekly petroleum endpoint path
PETROLEUM_WEEKLY_PATH: str = "petroleum/sum/snd/w"

# Weekly natural gas storage endpoint path
GAS_STORAGE_WEEKLY_PATH: str = "natural-gas/stor/sum/dcu/nus/w"

# Default page size for paginated requests
DEFAULT_PAGE_SIZE: int = 5000


# ── Error classes ──────────────────────────────────────────────────────────────


class EIAFeedError(Exception):
    """Raised when EIA API requests fail or return unexpected status codes."""


class EIAKeyError(EIAFeedError):
    """Raised when EIA_API_KEY is not configured."""


# ── EIA Feed Client ────────────────────────────────────────────────────────────


class EIAFeedClient:
    """HTTP client for EIA API v2 weekly petroleum and natural gas endpoints.

    The API key is read from the EIA_API_KEY environment variable at
    construction time if not supplied explicitly. An EIAKeyError is raised
    immediately if neither source provides a key.

    Args:
        api_key: EIA API key. Falls back to EIA_API_KEY env var.
        base_url: Override the EIA API v2 base URL (useful for tests).
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = EIA_BASE_URL,
        timeout: int = 30,
    ) -> None:
        resolved_key = api_key or os.environ.get("EIA_API_KEY")
        if not resolved_key:
            raise EIAKeyError(
                "EIA_API_KEY not set. Export EIA_API_KEY=<your_key> or "
                "pass api_key= to EIAFeedClient()."
            )
        self.api_key: str = resolved_key
        self.base_url: str = base_url.rstrip("/")
        self.timeout: int = timeout

    # ── URL helpers ───────────────────────────────────────────────────────────

    def build_endpoint_url(self, path: str) -> str:
        """Construct an EIA API v2 URL for the given endpoint path.

        The API key is NOT embedded in the URL — it is passed as a query
        parameter at request time.

        Args:
            path: Endpoint path, e.g. 'petroleum/sum/snd/w'.

        Returns:
            Full HTTPS URL string.
        """
        clean_path = path.strip("/")
        return f"{self.base_url}/{clean_path}/data/"

    # ── Response parsing ──────────────────────────────────────────────────────

    def parse_response(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and normalise records from an EIA API v2 JSON response.

        Args:
            raw: Full JSON response dict from EIA API v2.

        Returns:
            List of record dicts. Each record preserves all original fields
            from the API response, with 'value' coerced to float (or None).
        """
        data_items: List[Dict[str, Any]] = raw.get("response", {}).get("data", [])
        records: List[Dict[str, Any]] = []
        for item in data_items:
            record = dict(item)
            raw_value = record.get("value")
            if raw_value is None:
                record["value"] = None
            else:
                try:
                    record["value"] = float(raw_value)
                except (TypeError, ValueError):
                    record["value"] = None
            records.append(record)
        return records

    # ── Fetch helpers ─────────────────────────────────────────────────────────

    def _get(
        self,
        path: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a paginated GET against an EIA v2 data endpoint.

        Fetches all pages using offset/length pagination, merging results.

        Args:
            path: Endpoint path (no leading/trailing slash needed).
            extra_params: Additional query params (e.g. start date filter).

        Returns:
            Flat list of all record dicts across all pages.

        Raises:
            EIAFeedError: On HTTP error status (non-200) or network failures.
        """
        url = self.build_endpoint_url(path)
        params: Dict[str, Any] = {
            "api_key": self.api_key,
            "frequency": "weekly",
            "data[]": "value",
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": DEFAULT_PAGE_SIZE,
            "offset": 0,
        }
        if extra_params:
            params.update(extra_params)

        all_records: List[Dict[str, Any]] = []
        offset = 0

        while True:
            params["offset"] = offset
            logger.debug("EIA GET %s offset=%d", url, offset)

            try:
                response = requests.get(url, params=params, timeout=self.timeout)
            except requests.exceptions.RequestException as exc:
                raise EIAFeedError(f"EIA API request failed: {exc}") from exc

            if response.status_code == 429:
                raise EIAFeedError("EIA API rate limit exceeded. Retry after backoff.")
            if response.status_code != 200:
                raise EIAFeedError(
                    f"EIA API returned status {response.status_code}: "
                    f"{response.text[:200]}"
                )

            raw = response.json()
            page_records = self.parse_response(raw)
            all_records.extend(page_records)

            total = raw.get("response", {}).get("total", 0)
            offset += DEFAULT_PAGE_SIZE
            if offset >= total or not page_records:
                break

        return all_records

    # ── Public feed methods ───────────────────────────────────────────────────

    def fetch_petroleum_weekly(
        self,
        start_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch weekly petroleum status report data.

        Covers crude production, stocks, imports, and refinery utilisation
        from the EIA Weekly Petroleum Status Report.

        Args:
            start_date: ISO date string 'YYYY-MM-DD' for incremental fetch.
                        If None, fetches all available history.

        Returns:
            List of record dicts with a '_feed' key set to 'petroleum_weekly'.
        """
        extra: Dict[str, Any] = {}
        if start_date:
            extra["start"] = start_date

        records = self._get(PETROLEUM_WEEKLY_PATH, extra_params=extra)
        for rec in records:
            rec["_feed"] = "petroleum_weekly"
        return records

    def fetch_gas_storage_weekly(
        self,
        start_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch weekly natural gas storage report data.

        Covers US working gas in underground storage (Lower 48 states).

        Args:
            start_date: ISO date string 'YYYY-MM-DD' for incremental fetch.
                        If None, fetches all available history.

        Returns:
            List of record dicts with a '_feed' key set to 'gas_storage_weekly'.
        """
        extra: Dict[str, Any] = {}
        if start_date:
            extra["start"] = start_date

        records = self._get(GAS_STORAGE_WEEKLY_PATH, extra_params=extra)
        for rec in records:
            rec["_feed"] = "gas_storage_weekly"
        return records
