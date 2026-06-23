# ABOUTME: Base provider class for Landman module data sources
# ABOUTME: Provides common HTTP client, caching, rate limiting, and error handling

"""
Base Provider for Landman Module

Abstract base class for all data providers with common functionality
including HTTP client, caching, rate limiting, and retry logic.
"""

import hashlib
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, TypeVar

import httpx
from loguru import logger

from worldenergydata.landman.exceptions import (
    APIError,
    ParsingError,
    RateLimitError,
    TimeoutError,
)

T = TypeVar("T")


class CacheEntry:
    """Cache entry with expiration."""

    def __init__(self, data: Any, ttl_seconds: int = 3600) -> None:
        """
        Initialize cache entry.

        Args:
            data: Cached data
            ttl_seconds: Time to live in seconds
        """
        self.data = data
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() > self.expires_at


class MemoryCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 3600, max_entries: int = 1000) -> None:
        """
        Initialize memory cache.

        Args:
            default_ttl: Default time to live in seconds
            max_entries: Maximum number of entries
        """
        self._cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._hits = 0
        self._misses = 0

    def _make_key(self, key: str) -> str:
        """Generate cache key hash."""
        return hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        hashed_key = self._make_key(key)
        entry = self._cache.get(hashed_key)

        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired():
            del self._cache[hashed_key]
            self._misses += 1
            return None

        self._hits += 1
        return entry.data

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override
        """
        if len(self._cache) >= self.max_entries:
            self._evict_expired()

        if len(self._cache) >= self.max_entries:
            oldest_key = min(
                self._cache.keys(), key=lambda k: self._cache[k].created_at
            )
            del self._cache[oldest_key]

        hashed_key = self._make_key(key)
        self._cache[hashed_key] = CacheEntry(value, ttl or self.default_ttl)

    def _evict_expired(self) -> None:
        """Remove expired entries."""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired_keys:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }


class BaseProvider(ABC):
    """
    Abstract base class for all data providers.

    Provides common functionality for HTTP requests, caching,
    rate limiting, and error handling.
    """

    PROVIDER_NAME: str = "base"
    BASE_URL: str = ""
    RETRYABLE_STATUS_CODES = {500, 502, 503, 504}

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        rate_limit_delay: float = 0.5,
        cache_ttl: int = 3600,
        user_agent: str = "WorldEnergyData-Landman/1.0",
    ) -> None:
        """
        Initialize base provider.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_delay: Base delay between retries in seconds
            rate_limit_delay: Delay between requests in seconds
            cache_ttl: Cache time to live in seconds
            user_agent: User agent string for requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit_delay = rate_limit_delay
        self.cache_ttl = cache_ttl
        self.user_agent = user_agent

        self._client: Optional[httpx.Client] = None
        self._cache = MemoryCache(default_ttl=cache_ttl)
        self._last_request_time: Optional[float] = None
        self._request_count = 0

        self.logger = logger.bind(provider=self.PROVIDER_NAME)

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialized HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/json, text/html, */*",
                },
                follow_redirects=True,
            )
        return self._client

    def _wait_for_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                wait_time = self.rate_limit_delay - elapsed
                self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                time.sleep(wait_time)
        self._last_request_time = time.time()

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = True,
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic and caching.

        Args:
            url: URL to request
            method: HTTP method
            params: Query parameters
            data: Request body data
            headers: Additional headers
            use_cache: Whether to use caching for GET requests

        Returns:
            HTTP response

        Raises:
            APIError: If request fails after retries
            TimeoutError: If request times out
            RateLimitError: If rate limited by server
        """
        cache_key = None
        if use_cache and method == "GET":
            cache_key = f"{method}:{url}:{json.dumps(params or {}, sort_keys=True)}"
            cached = self._cache.get(cache_key)
            if cached is not None:
                self.logger.debug(f"Cache hit for {url}")
                return cached

        self._wait_for_rate_limit()

        retries = 0
        last_error = None

        while retries <= self.max_retries:
            try:
                self.logger.debug(
                    f"Request {method} {url} (attempt {retries + 1}/{self.max_retries + 1})"
                )

                response = self.client.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    headers=headers,
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if retries >= self.max_retries:
                        raise RateLimitError(
                            provider=self.PROVIDER_NAME,
                            retry_after=retry_after,
                        )
                    self.logger.warning(
                        f"Rate limited, waiting {retry_after}s before retry"
                    )
                    time.sleep(retry_after)
                    retries += 1
                    continue

                if (
                    response.status_code in self.RETRYABLE_STATUS_CODES
                    and retries < self.max_retries
                ):
                    retries += 1
                    delay = self.retry_delay * (2**retries)
                    self.logger.warning(
                        f"Retryable error {response.status_code}, waiting {delay}s"
                    )
                    time.sleep(delay)
                    continue

                response.raise_for_status()

                self._request_count += 1

                if cache_key:
                    self._cache.set(cache_key, response)

                return response

            except httpx.TimeoutException as e:
                last_error = e
                if retries >= self.max_retries:
                    raise TimeoutError(url=url, timeout=self.timeout)
                retries += 1
                delay = self.retry_delay * (2**retries)
                self.logger.warning(f"Timeout, retrying in {delay}s")
                time.sleep(delay)

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if (
                    status_code not in self.RETRYABLE_STATUS_CODES
                    or retries >= self.max_retries
                ):
                    raise APIError(url=url, status_code=status_code)
                retries += 1
                delay = self.retry_delay * (2**retries)
                time.sleep(delay)

            except httpx.RequestError as e:
                last_error = e
                if retries >= self.max_retries:
                    raise APIError(
                        url=url,
                        message=f"Request failed: {str(e)}",
                    )
                retries += 1
                delay = self.retry_delay * (2**retries)
                time.sleep(delay)

        raise APIError(
            url=url,
            message=f"Max retries exceeded. Last error: {last_error}",
        )

    def _get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Make GET request and parse JSON response.

        Args:
            url: URL to request
            params: Query parameters
            use_cache: Whether to use caching

        Returns:
            Parsed JSON response

        Raises:
            ParsingError: If response is not valid JSON
        """
        response = self._make_request(url, params=params, use_cache=use_cache)
        try:
            return response.json()
        except json.JSONDecodeError as e:
            raise ParsingError(
                source=url,
                reason=f"Invalid JSON response: {str(e)}",
            )

    def clear_cache(self) -> None:
        """Clear the provider cache."""
        self._cache.clear()
        self.logger.info("Cache cleared")

    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.stats()

    def request_count(self) -> int:
        """Get total request count."""
        return self._request_count

    def close(self) -> None:
        """Close HTTP client and clean up resources."""
        if self._client is not None:
            self._client.close()
            self._client = None
        self.logger.info(f"Provider closed. Total requests: {self._request_count}")

    def __enter__(self) -> "BaseProvider":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the provider is operational.

        Returns:
            True if provider is healthy
        """
        pass
