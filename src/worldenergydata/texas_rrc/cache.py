# ABOUTME: Caching implementation for Texas RRC API responses and downloaded files
# ABOUTME: Provides TTL-based in-memory cache with optional file system persistence

"""
Caching implementation for Texas RRC API responses.

Provides in-memory caching with TTL support for API responses and
downloaded file tracking to avoid redundant downloads.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""

    data: Any
    timestamp: float
    ttl: float

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.timestamp > self.ttl


class TexasRRCCache:
    """
    Simple in-memory cache for Texas RRC API responses.

    Features:
    - TTL-based expiration
    - Optional file tracking for downloaded files
    - Cache statistics
    """

    def __init__(self, default_ttl: int = 86400):
        """
        Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (24 hours)
        """
        self.cache: dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found/expired
        """
        if key in self.cache:
            entry = self.cache[key]
            if not entry.is_expired():
                self._hits += 1
                logger.debug(f"Cache hit for {key}")
                return entry.data
            else:
                logger.debug(f"Cache expired for {key}")
                del self.cache[key]
        self._misses += 1
        return None

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """
        Store item in cache.

        Args:
            key: Cache key
            data: Data to cache
            ttl: Optional TTL override
        """
        ttl = ttl or self.default_ttl
        self.cache[key] = CacheEntry(data=data, timestamp=time.time(), ttl=ttl)
        logger.debug(f"Cached {key} with TTL {ttl}")

    def delete(self, key: str) -> bool:
        """
        Delete item from cache.

        Args:
            key: Cache key

        Returns:
            True if item was deleted, False if not found
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Deleted cache key {key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self.cache[key]
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        return len(expired_keys)

    @property
    def stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
        return {
            "entries": len(self.cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }

    def __len__(self) -> int:
        """Return number of cache entries."""
        return len(self.cache)

    def __contains__(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None


class FileDownloadCache:
    """
    Cache for tracking downloaded files.

    Tracks downloaded files by their hash and modification time
    to avoid redundant downloads of unchanged data.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize file download cache.

        Args:
            cache_dir: Directory for cached files (defaults to temp)
        """
        self.cache_dir = (
            cache_dir or Path.home() / ".cache" / "worldenergydata" / "texas_rrc"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._file_hashes: dict[str, str] = {}

    def get_cache_path(self, url: str, suffix: str = "") -> Path:
        """
        Get cache path for a URL.

        Args:
            url: Source URL
            suffix: File suffix

        Returns:
            Path to cached file
        """
        url_hash = hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()[:16]
        filename = f"{url_hash}{suffix}"
        return self.cache_dir / filename

    def is_cached(self, url: str, max_age: Optional[int] = None) -> bool:
        """
        Check if URL content is cached and not expired.

        Args:
            url: Source URL
            max_age: Maximum age in seconds (None = no expiry)

        Returns:
            True if cached file exists and is valid
        """
        cache_path = self.get_cache_path(url)
        if not cache_path.exists():
            return False

        if max_age is not None:
            file_age = time.time() - cache_path.stat().st_mtime
            if file_age > max_age:
                logger.debug(f"Cached file expired: {cache_path}")
                return False

        return True

    def get_cached_file(self, url: str) -> Optional[Path]:
        """
        Get path to cached file if it exists.

        Args:
            url: Source URL

        Returns:
            Path to cached file or None
        """
        cache_path = self.get_cache_path(url)
        return cache_path if cache_path.exists() else None

    def save_to_cache(self, url: str, content: bytes, suffix: str = "") -> Path:
        """
        Save content to cache.

        Args:
            url: Source URL
            content: File content
            suffix: File suffix

        Returns:
            Path to cached file
        """
        cache_path = self.get_cache_path(url, suffix)
        cache_path.write_bytes(content)
        self._file_hashes[url] = hashlib.md5(content, usedforsecurity=False).hexdigest()
        logger.debug(f"Saved to cache: {cache_path}")
        return cache_path

    def clear(self) -> int:
        """
        Clear all cached files.

        Returns:
            Number of files removed
        """
        count = 0
        for file_path in self.cache_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()
                count += 1
        self._file_hashes.clear()
        logger.info(f"Cleared {count} cached files")
        return count
