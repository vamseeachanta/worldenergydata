"""
Redis-like In-Memory Caching System for BSEE Report Performance

Provides high-performance caching for aggregated metrics to achieve
50-70% performance improvement in report generation.
"""

import hashlib
import json
import pickle
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

import pandas as pd


class CacheEntry:
    """Represents a single cache entry with metadata."""

    def __init__(self, value: Any, ttl_seconds: int = 3600):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
        self.last_accessed = time.time()
        self.size_bytes = self._calculate_size(value)

    def _calculate_size(self, obj: Any) -> int:
        """Calculate approximate size of object in bytes."""
        try:
            if isinstance(obj, pd.DataFrame):
                return obj.memory_usage(deep=True).sum()
            elif isinstance(obj, (dict, list)):
                return len(pickle.dumps(obj))
            else:
                return len(str(obj).encode("utf-8"))
        except Exception:
            return 0

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds <= 0:
            return False
        return time.time() - self.created_at > self.ttl_seconds

    def access(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()


class MetricsCache:
    """
    Redis-like in-memory cache for BSEE report metrics.

    Features:
    - TTL support for automatic expiration
    - LRU eviction when size limit reached
    - Pattern-based invalidation
    - Thread-safe operations
    - Statistics tracking
    """

    def __init__(self, max_size_mb: int = 100, ttl_seconds: int = 3600):
        """
        Initialize cache with size and TTL limits.

        Args:
            max_size_mb: Maximum cache size in megabytes
            ttl_seconds: Default time-to-live in seconds
        """
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ttl_seconds = ttl_seconds

        # Use OrderedDict for LRU implementation
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "invalidations": 0,
        }

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override

        Returns:
            True if successfully cached
        """
        with self._lock:
            ttl_seconds = ttl if ttl is not None else self.ttl_seconds
            entry = CacheEntry(value, ttl_seconds)

            # Check if we need to evict entries
            self._evict_if_needed(entry.size_bytes)

            # Add or update entry
            if key in self._cache:
                del self._cache[key]  # Remove to re-add at end

            self._cache[key] = entry
            self._stats["sets"] += 1

            return True

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                self._stats["misses"] += 1
                return None

            # Update LRU order
            entry.access()
            del self._cache[key]
            self._cache[key] = entry

            self._stats["hits"] += 1
            return entry.value

    def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific cache key.

        Args:
            key: Cache key to invalidate

        Returns:
            True if key was found and invalidated
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["invalidations"] += 1
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.

        Args:
            pattern: Pattern to match (supports * wildcard)

        Returns:
            Number of keys invalidated
        """
        import fnmatch

        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)
            ]

            for key in keys_to_remove:
                del self._cache[key]

            self._stats["invalidations"] += len(keys_to_remove)
            return len(keys_to_remove)

    def flush(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats["invalidations"] += len(self._cache)

    def generate_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.

        Args:
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key

        Returns:
            Cache key string
        """
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
        return ":".join(key_parts)

    def generate_complex_key(self, **params) -> str:
        """
        Generate a complex cache key from parameters.

        Args:
            **params: Parameters to include in key

        Returns:
            Hashed cache key
        """
        key_str = json.dumps(params, sort_keys=True)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()

        # Include readable prefix
        prefix_parts = []
        if "level" in params:
            prefix_parts.append(params["level"])
        if "entity" in params:
            prefix_parts.append(params["entity"])

        if prefix_parts:
            return f"{':'.join(prefix_parts)}:{key_hash}"
        return key_hash

    def get_size_mb(self) -> float:
        """Get current cache size in megabytes."""
        with self._lock:
            total_bytes = sum(entry.size_bytes for entry in self._cache.values())
            return total_bytes / (1024 * 1024)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary of cache statistics
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "evictions": self._stats["evictions"],
                "invalidations": self._stats["invalidations"],
                "hit_rate": hit_rate,
                "total_keys": len(self._cache),
                "size_mb": self.get_size_mb(),
                "max_size_mb": self.max_size_mb,
            }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        with self._lock:
            self._stats = {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "evictions": 0,
                "invalidations": 0,
            }

    def _evict_if_needed(self, new_size: int) -> None:
        """
        Evict entries if adding new entry would exceed size limit.

        Args:
            new_size: Size of new entry to be added
        """
        current_size = sum(entry.size_bytes for entry in self._cache.values())

        if current_size + new_size <= self.max_size_bytes:
            return

        # Evict least recently used entries
        entries_to_remove = []
        size_to_free = (current_size + new_size) - self.max_size_bytes
        freed_size = 0

        for key, entry in self._cache.items():
            if freed_size >= size_to_free:
                break
            entries_to_remove.append(key)
            freed_size += entry.size_bytes

        for key in entries_to_remove:
            del self._cache[key]
            self._stats["evictions"] += 1


class CachedAggregator:
    """
    Wrapper for aggregators with caching capability.

    Provides transparent caching layer for any aggregator.
    """

    def __init__(self, aggregator: Any, cache: MetricsCache):
        """
        Initialize cached aggregator.

        Args:
            aggregator: The underlying aggregator instance
            cache: Cache instance to use
        """
        self.aggregator = aggregator
        self.cache = cache

    def aggregate(self, data: pd.DataFrame, **params) -> Any:
        """
        Aggregate data with caching.

        Args:
            data: Input data to aggregate
            **params: Additional aggregation parameters

        Returns:
            Aggregated result (from cache or fresh calculation)
        """
        # Generate cache key
        cache_key_params = {
            "aggregator": self.aggregator.__class__.__name__,
            "data_shape": str(data.shape),
            "data_hash": hashlib.md5(
                pd.util.hash_pandas_object(data).values
            ).hexdigest()[:8],
            **params,
        }
        cache_key = self.cache.generate_complex_key(**cache_key_params)

        # Try to get from cache
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Perform aggregation
        result = self.aggregator.aggregate(data, **params)

        # Cache the result
        self.cache.set(cache_key, result)

        return result


class CacheManager:
    """
    Global cache manager for BSEE report system.

    Manages multiple cache instances for different data types.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize cache manager."""
        if self._initialized:
            return

        self.caches = {
            "metrics": MetricsCache(max_size_mb=200, ttl_seconds=3600),
            "aggregations": MetricsCache(max_size_mb=500, ttl_seconds=7200),
            "reports": MetricsCache(max_size_mb=100, ttl_seconds=1800),
            "templates": MetricsCache(max_size_mb=50, ttl_seconds=86400),
        }

        self._initialized = True

    def get_cache(self, cache_type: str = "metrics") -> MetricsCache:
        """
        Get a specific cache instance.

        Args:
            cache_type: Type of cache to get

        Returns:
            Cache instance
        """
        return self.caches.get(cache_type, self.caches["metrics"])

    def flush_all(self) -> None:
        """Flush all caches."""
        for cache in self.caches.values():
            cache.flush()

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        return {name: cache.get_stats() for name, cache in self.caches.items()}


# Global cache manager instance
cache_manager = CacheManager()
