"""EIA REST API v2 client with series ID resolution, rate limiting, and caching.

API base: https://api.eia.gov/v2/
Auth: API key via EIA_API_KEY environment variable.
Request spacing is configurable; the default is a local client policy.

Key series IDs:
  PET.MCRFPUS2.M  — US total monthly crude production
  PET.MCRFPAK2.M  — Alaska monthly crude production
  PET.MCRFPTX2.M  — Texas monthly crude production (XX = state code)
  INTL.57-1-*.A   — International annual country production
"""

import hashlib
import logging
import os
import time
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# EIA API v2 base URL
EIA_BASE_URL: str = "https://api.eia.gov/v2"

# Existing client policy at f82ff2f, not a documented EIA service quota.
RATE_LIMIT_PER_HOUR: int = 500

# Default cache TTL: 24 hours
DEFAULT_CACHE_TTL: float = 86400.0


# ── Error classes ──────────────────────────────────────────────────────────────


class EIAApiError(Exception):
    """Raised when EIA API requests fail or configuration is invalid."""


class EIARateLimitError(EIAApiError):
    """Raised when the EIA service reports a rate-limit response."""


# ── Cache ──────────────────────────────────────────────────────────────────────


class _CacheEntry:
    """In-memory cache entry with TTL."""

    def __init__(self, data: Any, ttl: float) -> None:
        self.data = data
        self.expires_at = time.monotonic() + ttl

    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class EIACache:
    """Simple in-memory cache for EIA API responses."""

    def __init__(self, default_ttl: float = DEFAULT_CACHE_TTL) -> None:
        self.default_ttl = default_ttl
        self._store: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        """Return cached value if present and not expired, else None."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._store[key]
            return None
        return entry.data

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store value with given TTL (defaults to instance default)."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        self._store[key] = _CacheEntry(data=value, ttl=effective_ttl)

    def clear(self) -> None:
        """Remove all cached entries."""
        self._store.clear()


# ── EIA API Client ─────────────────────────────────────────────────────────────

# Mock data for tests — avoids any live HTTP calls
_MOCK_SERIES_DATA: dict[str, list[dict[str, Any]]] = {
    "PET.MCRFPUS2.M": [
        {"period": "2024-01", "value": "12500", "unit": "Thousand Barrels"},
        {"period": "2024-02", "value": "12300", "unit": "Thousand Barrels"},
        {"period": "2024-03", "value": "12450", "unit": "Thousand Barrels"},
    ],
    "PET.MCRFPAK2.M": [
        {"period": "2024-01", "value": "450", "unit": "Thousand Barrels"},
        {"period": "2024-02", "value": "440", "unit": "Thousand Barrels"},
    ],
    "PET.MCRFPTX2.M": [
        {"period": "2024-01", "value": "5200", "unit": "Thousand Barrels"},
        {"period": "2024-02", "value": "5150", "unit": "Thousand Barrels"},
    ],
}


class EIAApiClient:
    """
    HTTP client for EIA API v2.

    Features:
    - API key from constructor or EIA_API_KEY environment variable
    - Configurable spacing between live request attempts
    - In-memory response cache with configurable TTL
    - Mock mode for testing (no live HTTP calls)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = EIA_BASE_URL,
        rate_limit_per_hour: int = RATE_LIMIT_PER_HOUR,
        cache_enabled: bool = True,
        cache_ttl: float = DEFAULT_CACHE_TTL,
    ) -> None:
        """
        Initialise EIA API client.

        Args:
            api_key: EIA API key. Falls back to EIA_API_KEY env var.
            base_url: EIA API v2 base URL.
            rate_limit_per_hour: Maximum requests per hour (default 500).
            cache_enabled: Whether to cache responses.
            cache_ttl: Cache time-to-live in seconds.

        Raises:
            EIAApiError: If no API key is available.
        """
        resolved_key = api_key or os.environ.get("EIA_API_KEY")
        if not resolved_key:
            raise EIAApiError(
                "EIA API key not provided. Set EIA_API_KEY environment variable "
                "or pass api_key= to EIAApiClient()."
            )

        self.api_key = resolved_key
        self.base_url = base_url.rstrip("/")
        self.rate_limit_per_hour = rate_limit_per_hour
        self.cache_enabled = cache_enabled
        self.cache = EIACache(default_ttl=cache_ttl)

        # Existing spacing policy at f82ff2f: interval = seconds/hour / rate.
        # This spaces attempts rather than permitting token-bucket bursts.
        self._min_interval = (
            3600.0 / rate_limit_per_hour if rate_limit_per_hour > 0 else 0.0
        )
        self._last_request_time: float | None = None

    # ── URL + cache key helpers ───────────────────────────────────────────────

    def build_series_url(self, series_id: str) -> str:
        """Build EIA API v2 URL for a given series ID."""
        # EIA v2 uses /seriesid/ path for backward-compat series access
        return f"{self.base_url}/seriesid/{series_id}"

    def generate_cache_key(
        self, series_id: str, params: dict[str, Any], use_mock: bool = False
    ) -> str:
        """Key by mode, series and query; omitted mode selects the live namespace."""
        sorted_params = sorted(params.items())
        param_str = urlencode(sorted_params)
        mode = "mock" if use_mock else "live"
        raw = f"{mode}:{series_id}?{param_str}"
        return hashlib.md5(raw.encode()).hexdigest()

    # ── Response parsing ──────────────────────────────────────────────────────

    def parse_series_response(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract data records from an EIA API v2 JSON response.

        Args:
            raw: Full JSON response dict from EIA API.

        Returns:
            List of record dicts with 'period' and 'value' (float or None).

        Raises:
            EIAApiError: If response.data is not an array of objects.
        """
        # EIA API Technical Documentation, APIv2, "Parameters" and
        # "Understanding returned error codes" (accessed 2026-10-19):
        # https://www.eia.gov/opendata/documentation.php
        # An explicit empty array is valid; missing data is not an empty series.
        response = raw.get("response") if isinstance(raw, dict) else None
        records = response.get("data") if isinstance(response, dict) else None
        if not isinstance(records, list):
            raise EIAApiError("EIA API response.data must be an array")
        result = []
        for rec in records:
            if not isinstance(rec, dict):
                raise EIAApiError("EIA API response.data records must be objects")
            value_raw = rec.get("value")
            if value_raw is None:
                value = None
            else:
                try:
                    value = float(value_raw)
                except (TypeError, ValueError):
                    value = None

            result.append(
                {
                    "period": rec.get("period"),
                    "value": value,
                    "unit": rec.get("unit", ""),
                }
            )
        return result

    # ── Main fetch interface ──────────────────────────────────────────────────

    def fetch_series(
        self,
        series_id: str,
        params: dict[str, Any] | None = None,
        use_mock: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Fetch time-series data for a given EIA series ID.

        Uses a separate cache namespace for each mode. Mock mode returns built-in
        data without HTTP requests. Live mode fetches one page: pass offset and
        length explicitly to request other pages; total does not trigger prefetch.

        Args:
            series_id: EIA series identifier (e.g. 'PET.MCRFPUS2.M').
            params: Optional query parameters (start, end, frequency, etc.).
            use_mock: If True, return mock data without HTTP calls.

        Returns:
            List of record dicts with 'period', 'value', 'unit'.
        """
        if params is None:
            params = {}

        cache_key = self.generate_cache_key(series_id, params, use_mock=use_mock)

        # Cache hit
        if self.cache_enabled:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for series %s", series_id)
                return cached

        # Mock mode: return built-in mock without HTTP
        if use_mock:
            mock_records = _MOCK_SERIES_DATA.get(series_id, [])
            parsed = []
            for rec in mock_records:
                val = rec.get("value")
                parsed.append(
                    {
                        "period": rec.get("period"),
                        "value": float(val) if val is not None else None,
                        "unit": rec.get("unit", ""),
                    }
                )
            if self.cache_enabled:
                self.cache.set(cache_key, parsed)
            return parsed

        # Live transport is replaced by a mock in offline contract tests.
        return self._fetch_live(series_id, params, cache_key)

    def _fetch_live(
        self,
        series_id: str,
        params: dict[str, Any],
        cache_key: str,
    ) -> list[dict[str, Any]]:
        """Fetch one live page and cache it only after response validation."""
        try:
            import requests
        except ImportError as exc:
            raise EIAApiError(
                "requests library required for live EIA API calls. "
                "Install it with: pip install requests"
            ) from exc

        self._apply_rate_limit()

        url = self.build_series_url(series_id)
        query = {"api_key": self.api_key, **params}

        logger.debug("EIA API GET %s params=%s", url, list(query.keys()))

        try:
            response = requests.get(url, params=query, timeout=30)
        except requests.exceptions.RequestException as exc:
            raise EIAApiError(f"EIA API request failed: {exc}") from exc

        if response.status_code == 429:
            raise EIARateLimitError("EIA API rate limit exceeded")
        if response.status_code != 200:
            raise EIAApiError(
                f"EIA API returned status {response.status_code}: {response.text[:200]}"
            )

        try:
            raw = response.json()
        except ValueError as exc:
            raise EIAApiError("EIA API response must contain valid JSON") from exc
        records = self.parse_series_response(raw)

        if self.cache_enabled:
            self.cache.set(cache_key, records)

        return records

    def _apply_rate_limit(self) -> None:
        """Space live attempts at the configured rate; the first starts immediately."""
        if self._min_interval <= 0:
            return
        if self._last_request_time is not None:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()
