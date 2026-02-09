"""Base collector ABC with rate limiting, retry, and caching."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

_DEFAULT_USER_AGENT = (
    "worldenergydata/0.1.0 "
    "(+https://github.com/vamseeachanta/worldenergydata; "
    "data collection for public energy research)"
)


class BaseCollector(ABC):
    """Abstract base for all vessel fleet data collectors.

    Provides:
    - Rate limiting (configurable requests/second)
    - Retry with exponential backoff
    - Simple TTL-based response cache
    - Shared requests.Session with User-Agent

    Subclasses must implement ``collect()``.
    """

    def __init__(
        self,
        *,
        name: str,
        rate_limit: float = 1.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        timeout: int = 30,
        cache_ttl: float = 3600.0,
        cache_enabled: bool = True,
    ) -> None:
        self.name = name
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.cache_enabled = cache_enabled

        self._min_interval = 1.0 / rate_limit if rate_limit > 0 else 0.0
        self._last_request_time: float = 0.0
        self._cache: dict[str, tuple[float, Any]] = {}

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": _DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        })

    @abstractmethod
    def collect(self) -> Any:
        """Run the collection. Subclasses must implement."""

    def _apply_rate_limit(self) -> None:
        """Sleep if needed to honour the rate limit."""
        if self._min_interval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def _get_cache(self, key: str) -> Optional[Any]:
        """Return cached value if not expired, else None."""
        if not self.cache_enabled:
            return None
        entry = self._cache.get(key)
        if entry is None:
            return None
        cached_time, value = entry
        if (time.monotonic() - cached_time) > self.cache_ttl:
            del self._cache[key]
            return None
        return value

    def _set_cache(self, key: str, value: Any) -> None:
        """Store a value in the cache."""
        if not self.cache_enabled:
            return
        self._cache[key] = (time.monotonic(), value)

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """HTTP GET with rate limiting, caching, and retry.

        Returns the requests.Response on success. Raises the last
        exception after all retries are exhausted.
        """
        cached = self._get_cache(url)
        if cached is not None:
            return cached

        self._apply_rate_limit()

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url, timeout=self.timeout, **kwargs,
                )
                response.raise_for_status()
                self._set_cache(url, response)
                return response
            except Exception as exc:
                last_exc = exc
                delay = self.retry_base_delay * (2 ** attempt)
                logger.warning(
                    "%s: attempt %d/%d for %s failed: %s (retry in %.1fs)",
                    self.name, attempt + 1, self.max_retries, url, exc, delay,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(delay)

        raise last_exc  # type: ignore[misc]

    def get_text(self, url: str, **kwargs: Any) -> str:
        """HTTP GET returning response text."""
        return self.get(url, **kwargs).text

    def get_bytes(self, url: str, **kwargs: Any) -> bytes:
        """HTTP GET returning response content bytes."""
        return self.get(url, **kwargs).content
