"""
Cache optimization module for SODIR data operations.

Implements intelligent caching strategies to improve performance
for frequently accessed data and predictive pre-loading.
"""

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    total_size_bytes: int = 0
    avg_hit_time_ms: float = 0.0
    avg_miss_time_ms: float = 0.0
    most_accessed: List[Tuple[str, int]] = field(default_factory=list)
    cache_efficiency_score: float = 0.0


@dataclass
class CacheEntry:
    """Enhanced cache entry with metadata."""

    key: str
    value: Any
    timestamp: float
    ttl: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = 0
    priority: int = 0  # Higher priority items are kept longer


class SodirCacheOptimizer:
    """
    Intelligent cache optimizer for SODIR data.

    Features:
    - LRU with frequency consideration (LFU hybrid)
    - Predictive pre-loading based on access patterns
    - Adaptive TTL based on data stability
    - Cache warming for common queries
    - Memory-aware eviction
    """

    def __init__(
        self,
        max_size_mb: float = 100,
        default_ttl: int = 86400,
        enable_predictive: bool = True,
        enable_statistics: bool = True,
    ):
        """
        Initialize cache optimizer.

        Args:
            max_size_mb: Maximum cache size in megabytes
            default_ttl: Default time-to-live in seconds
            enable_predictive: Enable predictive pre-loading
            enable_statistics: Enable statistics collection
        """
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.default_ttl = default_ttl
        self.enable_predictive = enable_predictive
        self.enable_statistics = enable_statistics

        # Cache storage
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_size_bytes = 0

        # Access patterns for predictive loading
        self.access_patterns: defaultdict = defaultdict(list)
        self.access_sequences: List[str] = []
        self.pattern_lock = threading.Lock()

        # Statistics
        self.stats = CacheStats()
        self.access_frequency: defaultdict = defaultdict(int)

        # TTL adjustments based on data type
        self.ttl_adjustments = {
            "blocks": 604800,  # 7 days - very stable
            "fields": 86400,  # 1 day - relatively stable
            "wellbores": 43200,  # 12 hours - moderate changes
            "discoveries": 21600,  # 6 hours - more dynamic
            "surveys": 3600,  # 1 hour - frequently updated
            "production": 1800,  # 30 minutes - real-time data
        }

        # Common query patterns to pre-load
        self.common_patterns = [
            ("blocks", {"limit": 100}),
            ("fields", {"limit": 50, "status": "PRODUCING"}),
            ("wellbores", {"limit": 100, "status": "ACTIVE"}),
            ("discoveries", {"limit": 20, "year": datetime.now().year}),
        ]

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with intelligent handling.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        start_time = time.time()

        if key in self.cache:
            entry = self.cache[key]

            # Check if expired
            if time.time() - entry.timestamp > entry.ttl:
                self._evict(key)
                self._record_miss(time.time() - start_time)
                return None

            # Update access metadata
            entry.access_count += 1
            entry.last_accessed = time.time()

            # Move to end (most recently used)
            self.cache.move_to_end(key)

            # Record hit
            self._record_hit(time.time() - start_time)

            # Track access pattern
            self._track_access_pattern(key)

            return entry.value

        self._record_miss(time.time() - start_time)
        return None

    def set(
        self, key: str, value: Any, ttl: Optional[int] = None, priority: int = 0
    ) -> bool:
        """
        Set value in cache with intelligent TTL and priority.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for auto-detection)
            priority: Cache priority (higher = keep longer)

        Returns:
            True if cached successfully
        """
        # Estimate size
        size_bytes = self._estimate_size(value)

        # Check if we need to make room
        if size_bytes > self.max_size_bytes:
            logger.warning(f"Item too large for cache: {size_bytes} bytes")
            return False

        # Evict items if necessary
        while self.current_size_bytes + size_bytes > self.max_size_bytes:
            if not self._evict_lfu():
                logger.warning("Cannot evict enough items for new entry")
                return False

        # Determine TTL
        if ttl is None:
            ttl = self._determine_ttl(key, value)

        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl,
            size_bytes=size_bytes,
            priority=priority,
        )

        # Add to cache
        if key in self.cache:
            self.current_size_bytes -= self.cache[key].size_bytes

        self.cache[key] = entry
        self.current_size_bytes += size_bytes

        # Track for predictive loading
        self._track_access_pattern(key)

        return True

    def warm_cache(self, api_client: Any) -> Dict[str, int]:
        """
        Pre-load cache with common queries.

        Args:
            api_client: SODIR API client for fetching data

        Returns:
            Dictionary of warmed endpoints and item counts
        """
        warmed = {}

        for endpoint, params in self.common_patterns:
            try:
                # Fetch data
                if endpoint == "blocks":
                    data = api_client.get_blocks(**params)
                elif endpoint == "fields":
                    data = api_client.get_fields(**params)
                elif endpoint == "wellbores":
                    data = api_client.get_wellbores(**params)
                elif endpoint == "discoveries":
                    data = api_client.get_discoveries(**params)
                else:
                    continue

                # Cache with high priority
                cache_key = self._generate_key(endpoint, params)
                self.set(cache_key, data, priority=10)
                warmed[endpoint] = len(data) if isinstance(data, list) else 1

                logger.info(
                    f"Warmed cache for {endpoint} with {warmed[endpoint]} items"
                )

            except Exception as e:
                logger.error(f"Failed to warm cache for {endpoint}: {e}")

        return warmed

    def predict_next_queries(self, current_key: str, top_n: int = 5) -> List[str]:
        """
        Predict likely next queries based on access patterns.

        Args:
            current_key: Current query key
            top_n: Number of predictions to return

        Returns:
            List of predicted query keys
        """
        if not self.enable_predictive:
            return []

        predictions = []

        with self.pattern_lock:
            # Look for sequences containing current key
            pattern_counts = defaultdict(int)

            for i in range(len(self.access_sequences) - 1):
                if self.access_sequences[i] == current_key:
                    next_key = self.access_sequences[i + 1]
                    pattern_counts[next_key] += 1

            # Sort by frequency
            sorted_patterns = sorted(
                pattern_counts.items(), key=lambda x: x[1], reverse=True
            )

            predictions = [key for key, _ in sorted_patterns[:top_n]]

        return predictions

    def optimize_ttl(self) -> Dict[str, int]:
        """
        Optimize TTL values based on access patterns.

        Returns:
            Optimized TTL values by data type
        """
        optimized_ttl = self.ttl_adjustments.copy()

        # Analyze access patterns
        for key, entry in self.cache.items():
            data_type = self._extract_data_type(key)
            if data_type:
                # Calculate staleness factor
                age = time.time() - entry.timestamp
                access_rate = entry.access_count / (age + 1)

                # Adjust TTL based on access rate
                if access_rate > 1.0:  # Accessed more than once per second
                    optimized_ttl[data_type] = min(
                        optimized_ttl.get(data_type, self.default_ttl) * 2,
                        604800,  # Max 7 days
                    )
                elif access_rate < 0.001:  # Rarely accessed
                    optimized_ttl[data_type] = max(
                        optimized_ttl.get(data_type, self.default_ttl) // 2,
                        3600,  # Min 1 hour
                    )

        return optimized_ttl

    def get_statistics(self) -> CacheStats:
        """
        Get comprehensive cache statistics.

        Returns:
            CacheStats object with performance metrics
        """
        # Calculate hit rate
        if self.stats.total_requests > 0:
            hit_rate = self.stats.hits / self.stats.total_requests
        else:
            hit_rate = 0.0

        # Calculate efficiency score (considers hit rate, size usage, and evictions)
        size_efficiency = 1.0 - (self.current_size_bytes / self.max_size_bytes)
        eviction_penalty = max(
            0, 1.0 - (self.stats.evictions / max(1, self.stats.total_requests))
        )
        self.stats.cache_efficiency_score = (
            hit_rate * 0.5 + size_efficiency * 0.3 + eviction_penalty * 0.2
        )

        # Get most accessed keys
        sorted_access = sorted(
            self.access_frequency.items(), key=lambda x: x[1], reverse=True
        )
        self.stats.most_accessed = sorted_access[:10]

        # Update size
        self.stats.total_size_bytes = self.current_size_bytes

        return self.stats

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.current_size_bytes = 0
        self.access_patterns.clear()
        self.access_sequences.clear()
        self.stats = CacheStats()
        self.access_frequency.clear()
        logger.info("Cache cleared")

    def _determine_ttl(self, key: str, value: Any) -> int:
        """
        Determine appropriate TTL based on data type and characteristics.

        Args:
            key: Cache key
            value: Cached value

        Returns:
            TTL in seconds
        """
        data_type = self._extract_data_type(key)

        if data_type in self.ttl_adjustments:
            base_ttl = self.ttl_adjustments[data_type]
        else:
            base_ttl = self.default_ttl

        # Adjust based on data size (larger data gets longer TTL)
        if isinstance(value, (list, dict)):
            size_factor = min(2.0, 1.0 + len(str(value)) / 10000)
            base_ttl = int(base_ttl * size_factor)

        return base_ttl

    def _extract_data_type(self, key: str) -> Optional[str]:
        """
        Extract data type from cache key.

        Args:
            key: Cache key

        Returns:
            Data type or None
        """
        # Keys typically contain the endpoint/data type
        for data_type in self.ttl_adjustments.keys():
            if data_type in key.lower():
                return data_type
        return None

    def _evict_lfu(self) -> bool:
        """
        Evict least frequently used item with priority consideration.

        Returns:
            True if item was evicted
        """
        if not self.cache:
            return False

        # Calculate eviction scores (lower = evict first)
        eviction_candidates = []

        for key, entry in self.cache.items():
            # Skip high priority items unless necessary
            if (
                entry.priority > 5
                and self.current_size_bytes < self.max_size_bytes * 0.9
            ):
                continue

            # Calculate score based on frequency, recency, and priority
            age = time.time() - entry.last_accessed
            frequency_score = entry.access_count / (age + 1)
            priority_score = entry.priority * 10

            eviction_score = frequency_score + priority_score
            eviction_candidates.append((key, eviction_score))

        if not eviction_candidates:
            # Force evict oldest item
            key = next(iter(self.cache))
            return self._evict(key)

        # Evict item with lowest score
        eviction_candidates.sort(key=lambda x: x[1])
        key_to_evict = eviction_candidates[0][0]

        return self._evict(key_to_evict)

    def _evict(self, key: str) -> bool:
        """
        Evict item from cache.

        Args:
            key: Key to evict

        Returns:
            True if evicted
        """
        if key in self.cache:
            entry = self.cache[key]
            self.current_size_bytes -= entry.size_bytes
            del self.cache[key]
            self.stats.evictions += 1
            logger.debug(f"Evicted cache entry: {key}")
            return True
        return False

    def _estimate_size(self, value: Any) -> int:
        """
        Estimate size of value in bytes.

        Args:
            value: Value to estimate

        Returns:
            Estimated size in bytes
        """
        if value is None:
            return 0

        # Convert to JSON string for size estimation
        try:
            json_str = json.dumps(value, default=str)
            return len(json_str.encode("utf-8"))
        except Exception:
            # Fallback to string representation
            return len(str(value).encode("utf-8"))

    def _generate_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """
        Generate cache key from endpoint and parameters.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Cache key
        """
        # Sort params for consistent keys
        sorted_params = json.dumps(params, sort_keys=True)
        key_string = f"{endpoint}_{sorted_params}"

        # Hash if too long
        if len(key_string) > 100:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{endpoint}_{key_hash}"

        return key_string

    def _track_access_pattern(self, key: str):
        """
        Track access pattern for predictive loading.

        Args:
            key: Accessed key
        """
        if not self.enable_predictive:
            return

        with self.pattern_lock:
            # Track sequence
            self.access_sequences.append(key)

            # Limit sequence history
            if len(self.access_sequences) > 1000:
                self.access_sequences = self.access_sequences[-500:]

            # Track frequency
            self.access_frequency[key] += 1

    def _record_hit(self, response_time: float):
        """Record cache hit statistics."""
        if self.enable_statistics:
            self.stats.hits += 1
            self.stats.total_requests += 1

            # Update average hit time
            if self.stats.avg_hit_time_ms == 0:
                self.stats.avg_hit_time_ms = response_time * 1000
            else:
                self.stats.avg_hit_time_ms = (
                    self.stats.avg_hit_time_ms * 0.9 + response_time * 1000 * 0.1
                )

    def _record_miss(self, response_time: float):
        """Record cache miss statistics."""
        if self.enable_statistics:
            self.stats.misses += 1
            self.stats.total_requests += 1

            # Update average miss time
            if self.stats.avg_miss_time_ms == 0:
                self.stats.avg_miss_time_ms = response_time * 1000
            else:
                self.stats.avg_miss_time_ms = (
                    self.stats.avg_miss_time_ms * 0.9 + response_time * 1000 * 0.1
                )
