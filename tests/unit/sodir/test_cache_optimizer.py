"""Tests for SODIR cache optimizer."""

import time

from worldenergydata.sodir.cache_optimizer import (
    CacheEntry,
    CacheStats,
    SodirCacheOptimizer,
)


class TestCacheStats:
    def test_defaults(self):
        s = CacheStats()
        assert s.hits == 0
        assert s.misses == 0
        assert s.evictions == 0
        assert s.total_requests == 0
        assert s.cache_efficiency_score == 0.0
        assert s.most_accessed == []


class TestCacheEntry:
    def test_defaults(self):
        e = CacheEntry(key="k", value="v", timestamp=time.time(), ttl=60.0)
        assert e.access_count == 0
        assert e.priority == 0


class TestSodirCacheOptimizer:
    def test_set_and_get(self):
        cache = SodirCacheOptimizer()
        cache.set("key1", "value1", ttl=60)
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        cache = SodirCacheOptimizer()
        assert cache.get("missing") is None

    def test_get_expired(self):
        cache = SodirCacheOptimizer()
        cache.set("key1", "value1", ttl=0)
        # Ensure TTL expires
        entry = cache.cache["key1"]
        entry.timestamp = time.time() - 10
        assert cache.get("key1") is None

    def test_overwrite(self):
        cache = SodirCacheOptimizer()
        cache.set("k", "v1", ttl=60)
        cache.set("k", "v2", ttl=60)
        assert cache.get("k") == "v2"

    def test_clear(self):
        cache = SodirCacheOptimizer()
        cache.set("k1", "v1", ttl=60)
        cache.set("k2", "v2", ttl=60)
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None
        assert cache.current_size_bytes == 0

    def test_item_too_large(self):
        cache = SodirCacheOptimizer(max_size_mb=0.0001)  # ~100 bytes
        large_value = "x" * 10000
        result = cache.set("big", large_value, ttl=60)
        assert result is False

    def test_eviction_on_full(self):
        cache = SodirCacheOptimizer(max_size_mb=0.001)  # ~1KB
        cache.set("k1", "small", ttl=60)
        cache.set("k2", "a" * 500, ttl=60)
        cache.set("k3", "b" * 500, ttl=60)
        # Cache should have evicted something
        assert cache.current_size_bytes <= cache.max_size_bytes

    def test_statistics_initial(self):
        cache = SodirCacheOptimizer()
        stats = cache.get_statistics()
        assert stats.total_requests == 0
        assert stats.hits == 0

    def test_statistics_after_operations(self):
        cache = SodirCacheOptimizer()
        cache.set("k1", "v1", ttl=60)
        cache.get("k1")  # hit
        cache.get("missing")  # miss
        stats = cache.get_statistics()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.total_requests == 2

    def test_generate_key(self):
        cache = SodirCacheOptimizer()
        key1 = cache._generate_key("blocks", {"limit": 100})
        key2 = cache._generate_key("blocks", {"limit": 100})
        assert key1 == key2

    def test_generate_key_different_params(self):
        cache = SodirCacheOptimizer()
        key1 = cache._generate_key("blocks", {"limit": 100})
        key2 = cache._generate_key("blocks", {"limit": 50})
        assert key1 != key2

    def test_determine_ttl_known_type(self):
        cache = SodirCacheOptimizer()
        ttl = cache._determine_ttl("blocks_list", "data")
        assert ttl == 604800  # 7 days for blocks

    def test_determine_ttl_unknown_type(self):
        cache = SodirCacheOptimizer(default_ttl=3600)
        ttl = cache._determine_ttl("random_key", "data")
        assert ttl == 3600

    def test_extract_data_type(self):
        cache = SodirCacheOptimizer()
        assert cache._extract_data_type("blocks_100") == "blocks"
        assert cache._extract_data_type("fields_list") == "fields"
        assert cache._extract_data_type("unknown_key") is None

    def test_estimate_size(self):
        cache = SodirCacheOptimizer()
        assert cache._estimate_size(None) == 0
        assert cache._estimate_size("hello") > 0
        assert cache._estimate_size([1, 2, 3]) > 0

    def test_predict_next_queries_disabled(self):
        cache = SodirCacheOptimizer(enable_predictive=False)
        assert cache.predict_next_queries("key") == []

    def test_predict_next_queries_no_history(self):
        cache = SodirCacheOptimizer()
        assert cache.predict_next_queries("key") == []

    def test_predict_next_queries_with_patterns(self):
        cache = SodirCacheOptimizer()
        # Build access sequence
        cache.set("blocks", "data", ttl=60)
        cache.set("fields", "data", ttl=60)
        cache.get("blocks")
        cache.get("fields")
        cache.get("blocks")
        cache.get("fields")
        predictions = cache.predict_next_queries("blocks")
        assert isinstance(predictions, list)

    def test_optimize_ttl_empty(self):
        cache = SodirCacheOptimizer()
        optimized = cache.optimize_ttl()
        assert isinstance(optimized, dict)

    def test_set_with_priority(self):
        cache = SodirCacheOptimizer()
        cache.set("important", "data", ttl=60, priority=10)
        entry = cache.cache["important"]
        assert entry.priority == 10

    def test_access_count_incremented(self):
        cache = SodirCacheOptimizer()
        cache.set("k", "v", ttl=60)
        cache.get("k")
        cache.get("k")
        entry = cache.cache["k"]
        assert entry.access_count == 2


# ---------------------------------------------------------------------------
# warm_cache
# ---------------------------------------------------------------------------

class TestWarmCache:
    def test_warms_blocks_and_fields(self):
        from unittest.mock import MagicMock
        cache = SodirCacheOptimizer()
        client = MagicMock()
        client.get_blocks.return_value = [{"id": 1}, {"id": 2}]
        client.get_fields.return_value = [{"name": "Troll"}]
        client.get_wellbores.return_value = []
        client.get_discoveries.return_value = [{"name": "d1"}]
        warmed = cache.warm_cache(client)
        assert "blocks" in warmed
        assert warmed["blocks"] == 2
        assert "fields" in warmed
        assert warmed["fields"] == 1

    def test_warm_cache_api_error(self):
        from unittest.mock import MagicMock
        cache = SodirCacheOptimizer()
        client = MagicMock()
        client.get_blocks.side_effect = Exception("network error")
        client.get_fields.return_value = [{"f": 1}]
        client.get_wellbores.return_value = []
        client.get_discoveries.return_value = []
        warmed = cache.warm_cache(client)
        # blocks should be missing due to error
        assert "blocks" not in warmed
        assert "fields" in warmed


# ---------------------------------------------------------------------------
# optimize_ttl with data
# ---------------------------------------------------------------------------

class TestOptimizeTtlWithData:
    def test_high_access_rate(self):
        cache = SodirCacheOptimizer()
        cache.set("blocks_list", "data", ttl=60)
        entry = cache.cache["blocks_list"]
        # Simulate high access rate: many accesses in short time
        entry.access_count = 1000
        entry.timestamp = time.time() - 1  # 1 second ago
        optimized = cache.optimize_ttl()
        # Should increase TTL for blocks
        assert optimized.get("blocks", 0) > 0

    def test_low_access_rate(self):
        cache = SodirCacheOptimizer()
        cache.set("fields_data", "data", ttl=60)
        entry = cache.cache["fields_data"]
        # Simulate low access rate: few accesses over long time
        entry.access_count = 1
        entry.timestamp = time.time() - 100000  # Very old
        optimized = cache.optimize_ttl()
        assert isinstance(optimized, dict)


# ---------------------------------------------------------------------------
# _evict and _evict_lfu
# ---------------------------------------------------------------------------

class TestEviction:
    def test_evict_existing_key(self):
        cache = SodirCacheOptimizer()
        cache.set("k1", "v1", ttl=60)
        initial_size = cache.current_size_bytes
        result = cache._evict("k1")
        assert result is True
        assert cache.current_size_bytes < initial_size
        assert "k1" not in cache.cache

    def test_evict_nonexistent_key(self):
        cache = SodirCacheOptimizer()
        result = cache._evict("missing")
        assert result is False

    def test_evict_lfu_empty_cache(self):
        cache = SodirCacheOptimizer()
        result = cache._evict_lfu()
        assert result is False

    def test_evict_lfu_selects_lowest_score(self):
        cache = SodirCacheOptimizer()
        cache.set("rarely_used", "data1", ttl=60, priority=0)
        cache.set("often_used", "data2", ttl=60, priority=0)
        # Access often_used many times
        for _ in range(10):
            cache.get("often_used")
        result = cache._evict_lfu()
        assert result is True
        # The rarely_used entry should have been evicted
        assert "often_used" in cache.cache

    def test_evict_lfu_respects_priority(self):
        cache = SodirCacheOptimizer()
        cache.set("low_priority", "data", ttl=60, priority=1)
        cache.set("high_priority", "data", ttl=60, priority=10)
        result = cache._evict_lfu()
        assert result is True
        # High priority should be kept
        assert "high_priority" in cache.cache


# ---------------------------------------------------------------------------
# _determine_ttl with size factor
# ---------------------------------------------------------------------------

class TestDetermineTtlSizeFactor:
    def test_large_data_longer_ttl(self):
        cache = SodirCacheOptimizer()
        small_ttl = cache._determine_ttl("blocks_data", "small")
        large_ttl = cache._determine_ttl("blocks_data", list(range(10000)))
        assert large_ttl >= small_ttl

    def test_generate_key_long_params(self):
        cache = SodirCacheOptimizer()
        long_params = {"key": "x" * 200}
        key = cache._generate_key("blocks", long_params)
        # Should use hash since key is too long
        assert len(key) <= 200


# ---------------------------------------------------------------------------
# Statistics efficiency score
# ---------------------------------------------------------------------------

class TestStatisticsEfficiencyScore:
    def test_efficiency_score_with_hits(self):
        cache = SodirCacheOptimizer()
        cache.set("k1", "v1", ttl=60)
        cache.get("k1")  # hit
        cache.get("k1")  # hit
        cache.get("missing")  # miss
        stats = cache.get_statistics()
        assert stats.cache_efficiency_score > 0
        assert stats.total_requests == 3
        assert len(stats.most_accessed) > 0
