"""EIA REST API v2 client with series ID resolution, rate limiting, and caching.

API base: https://api.eia.gov/v2/
Auth: API key via EIA_API_KEY environment variable.
Rate limit: 500 requests per hour per key — enforced via token bucket.

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
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# EIA API v2 base URL
EIA_BASE_URL: str = "https://api.eia.gov/v2"

# Rate limit: 500 requests per hour per API key
RATE_LIMIT_PER_HOUR: int = 500

# Default cache TTL: 24 hours
DEFAULT_CACHE_TTL: float = 86400.0


# ── Error classes ──────────────────────────────────────────────────────────────


class EIAApiError(Exception):
    """Raised when EIA API requests fail or configuration is invalid."""


class EIARateLimitError(EIAApiError):
    """Raised when EIA API rate limit (500 req/hr) is exceeded."""


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
        self._store: Dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        """Return cached value if present and not expired, else None."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._store[key]
            return None
        return entry.data

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store value with given TTL (defaults to instance default)."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        self._store[key] = _CacheEntry(data=value, ttl=effective_ttl)

    def clear(self) -> None:
        """Remove all cached entries."""
        self._store.clear()


# ── EIA API Client ─────────────────────────────────────────────────────────────

# Mock data for tests — avoids any live HTTP calls
_MOCK_SERIES_DATA: Dict[str, List[Dict[str, Any]]] = {
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
    - Rate limiting: 500 requests per hour
    - In-memory response cache with configurable TTL
    - Mock mode for testing (no live HTTP calls)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
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

        # Token bucket: allow up to rate_limit_per_hour / 3600 per second
        self._min_interval = (
            3600.0 / rate_limit_per_hour if rate_limit_per_hour > 0 else 0.0
        )
        self._last_request_time: float = 0.0

    # ── URL + cache key helpers ───────────────────────────────────────────────

    def build_series_url(self, series_id: str) -> str:
        """Build EIA API v2 URL for a given series ID."""
        # EIA v2 uses /seriesid/ path for backward-compat series access
        return f"{self.base_url}/seriesid/{series_id}"

    def generate_cache_key(self, series_id: str, params: Dict[str, Any]) -> str:
        """Generate a deterministic cache key from series ID and query params."""
        sorted_params = sorted(params.items())
        param_str = urlencode(sorted_params)
        raw = f"{series_id}?{param_str}"
        return hashlib.md5(raw.encode()).hexdigest()

    # ── Response parsing ──────────────────────────────────────────────────────

    def parse_series_response(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract data records from an EIA API v2 JSON response.

        Args:
            raw: Full JSON response dict from EIA API.

        Returns:
            List of record dicts with 'period' and 'value' (float or None).
        """
        records = raw.get("response", {}).get("data", [])
        result = []
        for rec in records:
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
        params: Optional[Dict[str, Any]] = None,
        use_mock: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch time-series data for a given EIA series ID.

        Uses cache if enabled. In test/mock mode returns built-in mock data
        without making any HTTP requests.

        Args:
            series_id: EIA series identifier (e.g. 'PET.MCRFPUS2.M').
            params: Optional query parameters (start, end, frequency, etc.).
            use_mock: If True, return mock data without HTTP calls.

        Returns:
            List of record dicts with 'period', 'value', 'unit'.
        """
        if params is None:
            params = {}

        cache_key = self.generate_cache_key(series_id, params)

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

        # Live HTTP (guarded — not called in tests)
        return self._fetch_live(series_id, params, cache_key)

    def _fetch_live(
        self,
        series_id: str,
        params: Dict[str, Any],
        cache_key: str,
    ) -> List[Dict[str, Any]]:
        """Make live HTTP request to EIA API. Not called in test suite."""
        try:
            import requests  # noqa: PLC0415
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
            raise EIARateLimitError("EIA API rate limit exceeded (500 req/hr)")
        if response.status_code != 200:
            raise EIAApiError(
                f"EIA API returned status {response.status_code}: {response.text[:200]}"
            )

        raw = response.json()
        records = self.parse_series_response(raw)

        if self.cache_enabled:
            self.cache.set(cache_key, records)

        return records

    def _apply_rate_limit(self) -> None:
        """Sleep if needed to stay within 500 req/hr."""
        if self._min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()
