# ABOUTME: TTL-based cache manager for metocean API responses.
# ABOUTME: Reduces redundant API requests with configurable expiry and disk persistence.

"""
Cache Manager for Metocean Data

Provides TTL-based caching for API responses to reduce redundant requests.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generic, Optional, TypeVar

from ..config import get_config
from ..constants import DataSource
from ..exceptions import CacheReadError, CacheWriteError

T = TypeVar("T")


@dataclass
class CacheKey:
    """
    Unique cache key for an API request.

    Components:
    - source: Data source (NDBC, COOPS, etc.)
    - endpoint: API endpoint or query type
    - params: Query parameters
    """

    source: DataSource
    endpoint: str
    params: Dict[str, Any] = field(default_factory=dict)

    def to_hash(self) -> str:
        """Generate unique hash for cache filename."""
        key_str = (
            f"{self.source.value}:{self.endpoint}:"
            f"{json.dumps(self.params, sort_keys=True, default=str)}"
        )
        return hashlib.md5(key_str.encode()).hexdigest()

    def __str__(self) -> str:
        return f"{self.source.value}/{self.endpoint}"


@dataclass
class CacheEntry(Generic[T]):
    """
    Cached data with metadata.

    Stores the data along with creation time, expiration time,
    and usage statistics.
    """

    key: CacheKey
    data: T
    created_at: datetime
    expires_at: datetime
    size_bytes: int = 0
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def age_hours(self) -> float:
        """Get the age of the cache entry in hours."""
        return (datetime.utcnow() - self.created_at).total_seconds() / 3600

    @property
    def ttl_remaining_hours(self) -> float:
        """Get the remaining TTL in hours (negative if expired)."""
        return (self.expires_at - datetime.utcnow()).total_seconds() / 3600


class CacheManager:
    """
    TTL-based cache manager for metocean data.

    Features:
    - Configurable TTL (default 24 hours)
    - Size-limited storage
    - Automatic cleanup of expired entries
    - Disk persistence for offline use
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_hours: Optional[float] = None,
        max_size_mb: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        """
        Initialize the cache manager.

        Args:
            cache_dir: Directory for cache storage (default from config)
            ttl_hours: Time-to-live for cache entries in hours
            max_size_mb: Maximum cache size in megabytes
            enabled: Whether caching is enabled
        """
        config = get_config().cache

        self.cache_dir = cache_dir or config.cache_path
        self.ttl_hours = ttl_hours if ttl_hours is not None else config.ttl_hours
        self.max_size_mb = (
            max_size_mb if max_size_mb is not None else config.max_size_mb
        )
        self.enabled = enabled if enabled is not None else config.enabled
        self.logger = logging.getLogger("metocean.cache")

        # In-memory cache
        self._cache: Dict[str, CacheEntry] = {}

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load existing cache entries from disk
        self._load_from_disk()

        self.logger.info(
            f"Cache initialized: {self.cache_dir}, TTL={self.ttl_hours}h, "
            f"max={self.max_size_mb}MB, enabled={self.enabled}"
        )

    def get(self, key: CacheKey) -> Optional[Any]:
        """
        Get cached data if available and not expired.

        Args:
            key: The cache key to look up

        Returns:
            The cached data, or None if not cached or expired
        """
        if not self.enabled:
            return None

        hash_key = key.to_hash()
        entry = self._cache.get(hash_key)

        if entry is None:
            # Try loading from disk
            entry = self._load_entry(hash_key)
            if entry:
                self._cache[hash_key] = entry

        if entry is None:
            self.logger.debug(f"Cache miss: {key}")
            return None

        if entry.is_expired:
            self.logger.debug(f"Cache expired: {key} (age={entry.age_hours:.1f}h)")
            self._remove(hash_key)
            return None

        entry.hit_count += 1
        self.logger.debug(
            f"Cache hit: {key} (age={entry.age_hours:.1f}h, hits={entry.hit_count})"
        )
        return entry.data

    def set(
        self,
        key: CacheKey,
        data: Any,
        ttl_hours: Optional[float] = None,
    ) -> None:
        """
        Store data in cache.

        Args:
            key: Cache key
            data: Data to cache (must be JSON serializable)
            ttl_hours: Optional custom TTL (default uses configured TTL)
        """
        if not self.enabled:
            return

        ttl = ttl_hours if ttl_hours is not None else self.ttl_hours
        hash_key = key.to_hash()

        now = datetime.utcnow()

        # Calculate size
        try:
            serialized = json.dumps(data, default=str)
            size_bytes = len(serialized.encode())
        except (TypeError, ValueError) as e:
            self.logger.warning(f"Could not serialize data for size calculation: {e}")
            size_bytes = 0

        entry = CacheEntry(
            key=key,
            data=data,
            created_at=now,
            expires_at=now + timedelta(hours=ttl),
            size_bytes=size_bytes,
        )

        self._cache[hash_key] = entry
        self._save_entry(hash_key, entry)

        self.logger.debug(f"Cached: {key} (size={size_bytes} bytes, ttl={ttl}h)")

        # Check if cleanup needed
        self._maybe_cleanup()

    def invalidate(self, key: CacheKey) -> bool:
        """
        Invalidate (remove) a cache entry.

        Args:
            key: The cache key to invalidate

        Returns:
            True if an entry was removed, False otherwise
        """
        hash_key = key.to_hash()
        removed = self._remove(hash_key)
        if removed:
            self.logger.debug(f"Invalidated: {key}")
        return removed

    def invalidate_source(self, source: DataSource) -> int:
        """
        Invalidate all entries for a data source.

        Args:
            source: The data source to invalidate

        Returns:
            Number of entries removed
        """
        removed = 0
        for hash_key, entry in list(self._cache.items()):
            if entry.key.source == source:
                self._remove(hash_key)
                removed += 1

        self.logger.info(f"Invalidated {removed} entries for source {source.value}")
        return removed

    def invalidate_pattern(self, source: DataSource, endpoint_pattern: str) -> int:
        """
        Invalidate entries matching a pattern.

        Args:
            source: The data source
            endpoint_pattern: Pattern to match against endpoint (substring match)

        Returns:
            Number of entries removed
        """
        removed = 0
        for hash_key, entry in list(self._cache.items()):
            if entry.key.source == source and endpoint_pattern in entry.key.endpoint:
                self._remove(hash_key)
                removed += 1

        self.logger.info(
            f"Invalidated {removed} entries matching {source.value}/{endpoint_pattern}"
        )
        return removed

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries removed
        """
        count = len(self._cache)
        self._cache.clear()

        # Remove disk cache
        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink()
            except OSError as e:
                self.logger.warning(f"Failed to remove cache file {f}: {e}")

        self.logger.info(f"Cache cleared: {count} entries removed")
        return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        expired_keys = [k for k, e in self._cache.items() if e.is_expired]
        for k in expired_keys:
            self._remove(k)

        self.logger.info(f"Cleaned up {len(expired_keys)} expired entries")
        return len(expired_keys)

    def status(self) -> Dict[str, Any]:
        """
        Get cache status information.

        Returns:
            Dictionary with cache statistics
        """
        total_size = sum(e.size_bytes for e in self._cache.values())
        expired = sum(1 for e in self._cache.values() if e.is_expired)
        total_hits = sum(e.hit_count for e in self._cache.values())

        # Group by source
        by_source: Dict[str, int] = {}
        for entry in self._cache.values():
            source_name = entry.key.source.value
            by_source[source_name] = by_source.get(source_name, 0) + 1

        return {
            "enabled": self.enabled,
            "entries": len(self._cache),
            "expired": expired,
            "active": len(self._cache) - expired,
            "total_hits": total_hits,
            "size_bytes": total_size,
            "size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": self.max_size_mb,
            "ttl_hours": self.ttl_hours,
            "cache_dir": str(self.cache_dir),
            "by_source": by_source,
        }

    def _load_from_disk(self) -> None:
        """Load existing cache entries from disk."""
        loaded = 0
        for f in self.cache_dir.glob("*.json"):
            try:
                entry = self._load_entry_from_file(f)
                if entry and not entry.is_expired:
                    hash_key = f.stem
                    self._cache[hash_key] = entry
                    loaded += 1
                elif entry and entry.is_expired:
                    # Clean up expired file
                    f.unlink()
            except Exception as e:
                self.logger.warning(f"Failed to load cache file {f}: {e}")

        if loaded > 0:
            self.logger.info(f"Loaded {loaded} cache entries from disk")

    def _load_entry_from_file(self, filepath: Path) -> Optional[CacheEntry]:
        """Load a cache entry from a file."""
        try:
            with open(filepath, "r") as fp:
                raw = json.load(fp)
                key = CacheKey(
                    source=DataSource(raw["key"]["source"]),
                    endpoint=raw["key"]["endpoint"],
                    params=raw["key"]["params"],
                )
                return CacheEntry(
                    key=key,
                    data=raw["data"],
                    created_at=datetime.fromisoformat(raw["created_at"]),
                    expires_at=datetime.fromisoformat(raw["expires_at"]),
                    size_bytes=raw.get("size_bytes", 0),
                    hit_count=raw.get("hit_count", 0),
                )
        except Exception as e:
            self.logger.debug(f"Failed to parse cache file {filepath}: {e}")
            return None

    def _save_entry(self, hash_key: str, entry: CacheEntry) -> None:
        """Save cache entry to disk."""
        try:
            cache_file = self.cache_dir / f"{hash_key}.json"
            with open(cache_file, "w") as fp:
                json.dump(
                    {
                        "key": {
                            "source": entry.key.source.value,
                            "endpoint": entry.key.endpoint,
                            "params": entry.key.params,
                        },
                        "data": entry.data,
                        "created_at": entry.created_at.isoformat(),
                        "expires_at": entry.expires_at.isoformat(),
                        "size_bytes": entry.size_bytes,
                        "hit_count": entry.hit_count,
                    },
                    fp,
                    default=str,
                )
        except Exception as e:
            raise CacheWriteError(
                f"Failed to write cache entry {hash_key}: {e}",
                details={"hash_key": hash_key, "error": str(e)},
            )

    def _load_entry(self, hash_key: str) -> Optional[CacheEntry]:
        """Load a single cache entry from disk."""
        cache_file = self.cache_dir / f"{hash_key}.json"
        if not cache_file.exists():
            return None

        try:
            return self._load_entry_from_file(cache_file)
        except Exception as e:
            self.logger.warning(f"Failed to load cache entry {hash_key}: {e}")
            return None

    def _remove(self, hash_key: str) -> bool:
        """Remove cache entry from memory and disk."""
        removed = False

        if hash_key in self._cache:
            del self._cache[hash_key]
            removed = True

        cache_file = self.cache_dir / f"{hash_key}.json"
        if cache_file.exists():
            try:
                cache_file.unlink()
                removed = True
            except OSError as e:
                self.logger.warning(f"Failed to remove cache file {cache_file}: {e}")

        return removed

    def _maybe_cleanup(self) -> None:
        """Clean up expired entries and enforce size limit if needed."""
        # Remove expired entries
        expired_keys = [k for k, e in self._cache.items() if e.is_expired]
        for k in expired_keys:
            self._remove(k)

        # Check size limit
        total_size_mb = sum(e.size_bytes for e in self._cache.values()) / (1024 * 1024)

        if total_size_mb > self.max_size_mb:
            # Remove oldest entries first (LRU-like behavior based on creation time)
            sorted_entries = sorted(self._cache.items(), key=lambda x: x[1].created_at)

            target_size_mb = self.max_size_mb * 0.8  # Keep 80% of limit

            while total_size_mb > target_size_mb and sorted_entries:
                hash_key, entry = sorted_entries.pop(0)
                total_size_mb -= entry.size_bytes / (1024 * 1024)
                self._remove(hash_key)
                self.logger.debug(
                    f"Evicted cache entry to enforce size limit: {entry.key}"
                )
