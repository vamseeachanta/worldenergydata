# ABOUTME: Caching implementation for Canada API responses with TTL support
# ABOUTME: Provides in-memory and file-based caching for AER, BCER, and Petrinex data

"""
Canada Module Caching Implementation.

This module provides caching for Canadian oil and gas data APIs,
including in-memory caching with TTL and file-based caching for
large downloads like CSV data files.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

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


class CanadaCache:
    """
    In-memory cache for Canada API responses.

    Provides simple key-value storage with time-to-live (TTL) support
    for caching API responses and reducing redundant requests.
    """

    def __init__(self, default_ttl: int = 86400):
        """
        Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (default 24 hours)
        """
        self._cache: Dict[str, CacheEntry] = {}
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
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                self._hits += 1
                logger.debug(f"Cache hit for {key}")
                return entry.data
            else:
                logger.debug(f"Cache expired for {key}")
                del self._cache[key]

        self._misses += 1
        return None

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """
        Store item in cache.

        Args:
            key: Cache key
            data: Data to cache
            ttl: Optional TTL override in seconds
        """
        ttl = ttl or self.default_ttl
        self._cache[key] = CacheEntry(data=data, timestamp=time.time(), ttl=ttl)
        logger.debug(f"Cached {key} with TTL {ttl}")

    def delete(self, key: str) -> bool:
        """
        Delete item from cache.

        Args:
            key: Cache key

        Returns:
            True if item was deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        return len(expired_keys)

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }


class FileDownloadCache:
    """
    File-based cache for large data downloads.

    Caches downloaded files (CSV, ZIP) to disk with metadata
    tracking for TTL-based invalidation.
    """

    DEFAULT_CACHE_DIR = Path.home() / ".worldenergydata" / "cache" / "canada"

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        default_ttl: int = 86400,
    ):
        """
        Initialize file download cache.

        Args:
            cache_dir: Directory for cached files
            default_ttl: Default TTL in seconds (24 hours)
        """
        self.cache_dir = cache_dir or self.DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load cache metadata from disk."""
        metadata_file = self.cache_dir / ".metadata.json"
        if metadata_file.exists():
            try:
                import json

                with open(metadata_file, "r") as f:
                    self._metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
                self._metadata = {}

    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        metadata_file = self.cache_dir / ".metadata.json"
        try:
            import json

            with open(metadata_file, "w") as f:
                json.dump(self._metadata, f)
        except Exception as e:
            logger.warning(f"Failed to save cache metadata: {e}")

    def _generate_key(self, url: str) -> str:
        """Generate cache key from URL."""
        return hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()

    def is_cached(self, url: str, max_age: Optional[int] = None) -> bool:
        """
        Check if URL is cached and not expired.

        Args:
            url: URL to check
            max_age: Optional max age override in seconds

        Returns:
            True if cached and valid
        """
        key = self._generate_key(url)
        if key not in self._metadata:
            return False

        meta = self._metadata[key]
        cached_file = self.cache_dir / meta.get("filename", "")

        if not cached_file.exists():
            return False

        max_age = max_age or self.default_ttl
        age = time.time() - meta.get("timestamp", 0)
        return age < max_age

    def get_cached_file(self, url: str) -> Optional[Path]:
        """
        Get path to cached file if it exists.

        Args:
            url: URL that was cached

        Returns:
            Path to cached file or None
        """
        key = self._generate_key(url)
        if key not in self._metadata:
            return None

        meta = self._metadata[key]
        cached_file = self.cache_dir / meta.get("filename", "")

        if cached_file.exists():
            return cached_file
        return None

    def save_to_cache(
        self,
        url: str,
        data: bytes,
        suffix: str = "",
    ) -> Path:
        """
        Save downloaded data to cache.

        Args:
            url: Source URL
            data: File data as bytes
            suffix: File suffix (e.g., ".csv", ".zip")

        Returns:
            Path to cached file
        """
        key = self._generate_key(url)
        filename = f"{key}{suffix}"
        cached_file = self.cache_dir / filename

        cached_file.write_bytes(data)

        self._metadata[key] = {
            "url": url,
            "filename": filename,
            "timestamp": time.time(),
            "size": len(data),
        }
        self._save_metadata()

        logger.debug(f"Cached {len(data)} bytes to {cached_file}")
        return cached_file

    def invalidate(self, url: str) -> bool:
        """
        Invalidate cached file.

        Args:
            url: URL to invalidate

        Returns:
            True if cache entry was removed
        """
        key = self._generate_key(url)
        if key not in self._metadata:
            return False

        meta = self._metadata[key]
        cached_file = self.cache_dir / meta.get("filename", "")

        if cached_file.exists():
            cached_file.unlink()

        del self._metadata[key]
        self._save_metadata()
        return True

    def clear(self) -> int:
        """
        Clear all cached files.

        Returns:
            Number of files removed
        """
        count = 0
        for key, meta in list(self._metadata.items()):
            cached_file = self.cache_dir / meta.get("filename", "")
            if cached_file.exists():
                cached_file.unlink()
                count += 1
            del self._metadata[key]

        self._save_metadata()
        logger.info(f"Cleared {count} cached files")
        return count


__all__ = ["CanadaCache", "FileDownloadCache"]
