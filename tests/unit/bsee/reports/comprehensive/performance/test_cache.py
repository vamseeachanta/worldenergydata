"""Tests for BSEE report performance cache module."""

import time

import pandas as pd
import pytest

from worldenergydata.bsee.reports.comprehensive.performance.cache import (
    CacheEntry,
    CacheManager,
    CachedAggregator,
    MetricsCache,
)


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------

class TestCacheEntryInit:
    def test_default_ttl(self):
        entry = CacheEntry("hello")
        assert entry.value == "hello"
        assert entry.ttl_seconds == 3600
        assert entry.access_count == 0

    def test_custom_ttl(self):
        entry = CacheEntry(42, ttl_seconds=120)
        assert entry.ttl_seconds == 120

    def test_size_bytes_string(self):
        entry = CacheEntry("abc")
        assert entry.size_bytes == len("abc".encode("utf-8"))

    def test_size_bytes_dict(self):
        entry = CacheEntry({"a": 1, "b": 2})
        assert entry.size_bytes > 0

    def test_size_bytes_list(self):
        entry = CacheEntry([1, 2, 3])
        assert entry.size_bytes > 0

    def test_size_bytes_dataframe(self):
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4.0, 5.0, 6.0]})
        entry = CacheEntry(df)
        assert entry.size_bytes > 0

    def test_size_bytes_unpicklable_fallback(self):
        """Objects that fail all size paths return 0."""
        class Unpicklable:
            def __reduce__(self):
                raise TypeError("nope")
            def __str__(self):
                raise TypeError("nope")
        entry = CacheEntry.__new__(CacheEntry)
        result = entry._calculate_size(Unpicklable())
        assert result == 0


class TestCacheEntryExpiration:
    def test_not_expired(self):
        entry = CacheEntry("data", ttl_seconds=3600)
        assert entry.is_expired() is False

    def test_expired(self):
        entry = CacheEntry("data", ttl_seconds=1)
        entry.created_at -= 10
        assert entry.is_expired() is True

    def test_zero_ttl_never_expires(self):
        entry = CacheEntry("data", ttl_seconds=0)
        entry.created_at -= 999999
        assert entry.is_expired() is False

    def test_negative_ttl_never_expires(self):
        entry = CacheEntry("data", ttl_seconds=-1)
        assert entry.is_expired() is False


class TestCacheEntryAccess:
    def test_access_increments_count(self):
        entry = CacheEntry("data")
        assert entry.access_count == 0
        entry.access()
        assert entry.access_count == 1
        entry.access()
        assert entry.access_count == 2

    def test_access_updates_last_accessed(self):
        entry = CacheEntry("data")
        old_time = entry.last_accessed
        time.sleep(0.01)
        entry.access()
        assert entry.last_accessed >= old_time


# ---------------------------------------------------------------------------
# MetricsCache
# ---------------------------------------------------------------------------

class TestMetricsCacheInit:
    def test_defaults(self):
        cache = MetricsCache()
        assert cache.max_size_mb == 100
        assert cache.ttl_seconds == 3600
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_custom_params(self):
        cache = MetricsCache(max_size_mb=50, ttl_seconds=1800)
        assert cache.max_size_mb == 50
        assert cache.ttl_seconds == 1800


class TestMetricsCacheSetGet:
    def test_set_and_get(self):
        cache = MetricsCache()
        assert cache.set("k1", "v1") is True
        assert cache.get("k1") == "v1"

    def test_get_missing_returns_none(self):
        cache = MetricsCache()
        assert cache.get("nonexistent") is None

    def test_set_overwrites(self):
        cache = MetricsCache()
        cache.set("k", "v1")
        cache.set("k", "v2")
        assert cache.get("k") == "v2"

    def test_set_with_custom_ttl(self):
        cache = MetricsCache(ttl_seconds=3600)
        cache.set("k", "v", ttl=1)
        assert cache.get("k") == "v"

    def test_get_expired_returns_none(self):
        cache = MetricsCache(ttl_seconds=1)
        cache.set("k", "v")
        # Backdate creation
        cache._cache["k"].created_at -= 10
        assert cache.get("k") is None

    def test_get_expired_removes_entry(self):
        cache = MetricsCache(ttl_seconds=1)
        cache.set("k", "v")
        cache._cache["k"].created_at -= 10
        cache.get("k")
        assert "k" not in cache._cache

    def test_stats_track_hits_and_misses(self):
        cache = MetricsCache()
        cache.set("k", "v")
        cache.get("k")       # hit
        cache.get("missing")  # miss
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1


class TestMetricsCacheInvalidate:
    def test_invalidate_existing(self):
        cache = MetricsCache()
        cache.set("k", "v")
        assert cache.invalidate("k") is True
        assert cache.get("k") is None

    def test_invalidate_missing(self):
        cache = MetricsCache()
        assert cache.invalidate("nope") is False

    def test_invalidate_tracks_stats(self):
        cache = MetricsCache()
        cache.set("k", "v")
        cache.invalidate("k")
        assert cache.get_stats()["invalidations"] == 1


class TestMetricsCacheInvalidatePattern:
    def test_pattern_match(self):
        cache = MetricsCache()
        cache.set("metrics:oil:2024", "a")
        cache.set("metrics:gas:2024", "b")
        cache.set("reports:q1", "c")
        removed = cache.invalidate_pattern("metrics:*")
        assert removed == 2
        assert cache.get("metrics:oil:2024") is None
        assert cache.get("reports:q1") == "c"

    def test_pattern_no_match(self):
        cache = MetricsCache()
        cache.set("k1", "v1")
        removed = cache.invalidate_pattern("nonexistent:*")
        assert removed == 0

    def test_pattern_wildcard_all(self):
        cache = MetricsCache()
        cache.set("a", 1)
        cache.set("b", 2)
        removed = cache.invalidate_pattern("*")
        assert removed == 2


class TestMetricsCacheFlush:
    def test_flush_clears_all(self):
        cache = MetricsCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.flush()
        assert cache.get("k1") is None
        assert cache.get("k2") is None
        assert cache.get_stats()["total_keys"] == 0


class TestMetricsCacheGenerateKey:
    def test_positional_args(self):
        cache = MetricsCache()
        key = cache.generate_key("level1", "entity1")
        assert key == "level1:entity1"

    def test_kwargs_sorted(self):
        cache = MetricsCache()
        k1 = cache.generate_key(year=2024, month=1)
        k2 = cache.generate_key(month=1, year=2024)
        assert k1 == k2

    def test_mixed_args_kwargs(self):
        cache = MetricsCache()
        key = cache.generate_key("prefix", x=1, y=2)
        assert "prefix" in key
        assert "x:1" in key
        assert "y:2" in key


class TestMetricsCacheGenerateComplexKey:
    def test_with_level_and_entity(self):
        cache = MetricsCache()
        key = cache.generate_complex_key(level="field", entity="GOM001")
        assert key.startswith("field:GOM001:")
        assert len(key.split(":")[-1]) == 32  # md5 hex

    def test_without_prefix_parts(self):
        cache = MetricsCache()
        key = cache.generate_complex_key(year=2024)
        assert len(key) == 32  # just the md5 hash

    def test_deterministic(self):
        cache = MetricsCache()
        k1 = cache.generate_complex_key(a=1, b=2)
        k2 = cache.generate_complex_key(a=1, b=2)
        assert k1 == k2


class TestMetricsCacheSize:
    def test_get_size_mb_empty(self):
        cache = MetricsCache()
        assert cache.get_size_mb() == 0.0

    def test_get_size_mb_with_data(self):
        cache = MetricsCache()
        cache.set("k", "x" * 1000)
        assert cache.get_size_mb() > 0


class TestMetricsCacheStats:
    def test_full_stats(self):
        cache = MetricsCache(max_size_mb=10)
        cache.set("a", "1")
        cache.get("a")
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["sets"] == 1
        assert stats["total_keys"] == 1
        assert stats["max_size_mb"] == 10
        assert 0 < stats["hit_rate"] <= 1.0

    def test_hit_rate_zero_when_no_requests(self):
        cache = MetricsCache()
        assert cache.get_stats()["hit_rate"] == 0

    def test_reset_stats(self):
        cache = MetricsCache()
        cache.set("k", "v")
        cache.get("k")
        cache.reset_stats()
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["sets"] == 0


class TestMetricsCacheEviction:
    def test_evict_lru_entries(self):
        # Tiny cache: 1 byte max
        cache = MetricsCache(max_size_mb=0)
        cache.max_size_bytes = 50  # override to tiny size
        cache.set("first", "a" * 100)
        # first should be evicted when second is added
        cache.set("second", "b" * 10)
        stats = cache.get_stats()
        assert stats["evictions"] > 0


# ---------------------------------------------------------------------------
# CachedAggregator
# ---------------------------------------------------------------------------

class TestCachedAggregator:
    def test_aggregate_caches_result(self):
        class FakeAggregator:
            call_count = 0
            def aggregate(self, data, **params):
                self.call_count += 1
                return {"sum": data["A"].sum()}

        agg = FakeAggregator()
        cache = MetricsCache()
        cached = CachedAggregator(agg, cache)
        df = pd.DataFrame({"A": [1, 2, 3]})

        r1 = cached.aggregate(df, level="field")
        r2 = cached.aggregate(df, level="field")
        assert r1 == {"sum": 6}
        assert r2 == {"sum": 6}
        assert agg.call_count == 1  # second call served from cache

    def test_aggregate_different_params_not_cached(self):
        class FakeAggregator:
            call_count = 0
            def aggregate(self, data, **params):
                self.call_count += 1
                return params.get("level", "default")

        agg = FakeAggregator()
        cache = MetricsCache()
        cached = CachedAggregator(agg, cache)
        df = pd.DataFrame({"A": [1]})

        cached.aggregate(df, level="field")
        cached.aggregate(df, level="platform")
        assert agg.call_count == 2


# ---------------------------------------------------------------------------
# CacheManager (singleton)
# ---------------------------------------------------------------------------

class TestCacheManager:
    def _reset_singleton(self):
        """Reset CacheManager singleton for test isolation."""
        CacheManager._instance = None

    def test_singleton(self):
        self._reset_singleton()
        try:
            m1 = CacheManager()
            m2 = CacheManager()
            assert m1 is m2
        finally:
            self._reset_singleton()

    def test_default_caches(self):
        self._reset_singleton()
        try:
            mgr = CacheManager()
            assert "metrics" in mgr.caches
            assert "aggregations" in mgr.caches
            assert "reports" in mgr.caches
            assert "templates" in mgr.caches
        finally:
            self._reset_singleton()

    def test_get_cache_existing(self):
        self._reset_singleton()
        try:
            mgr = CacheManager()
            cache = mgr.get_cache("metrics")
            assert isinstance(cache, MetricsCache)
        finally:
            self._reset_singleton()

    def test_get_cache_unknown_returns_metrics(self):
        self._reset_singleton()
        try:
            mgr = CacheManager()
            cache = mgr.get_cache("nonexistent")
            assert cache is mgr.caches["metrics"]
        finally:
            self._reset_singleton()

    def test_flush_all(self):
        self._reset_singleton()
        try:
            mgr = CacheManager()
            mgr.get_cache("metrics").set("k", "v")
            mgr.get_cache("reports").set("k2", "v2")
            mgr.flush_all()
            assert mgr.get_cache("metrics").get("k") is None
            assert mgr.get_cache("reports").get("k2") is None
        finally:
            self._reset_singleton()

    def test_get_all_stats(self):
        self._reset_singleton()
        try:
            mgr = CacheManager()
            all_stats = mgr.get_all_stats()
            assert "metrics" in all_stats
            assert "aggregations" in all_stats
            assert "hits" in all_stats["metrics"]
        finally:
            self._reset_singleton()
