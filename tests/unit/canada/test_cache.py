"""Tests for Canada caching implementation."""

import time

from worldenergydata.canada.cache import CacheEntry, CanadaCache, FileDownloadCache


class TestCacheEntry:
    def test_not_expired(self):
        entry = CacheEntry(data="test", timestamp=time.time(), ttl=60)
        assert entry.is_expired() is False

    def test_expired(self):
        entry = CacheEntry(data="test", timestamp=time.time() - 120, ttl=60)
        assert entry.is_expired() is True

    def test_zero_ttl_expired(self):
        entry = CacheEntry(data="test", timestamp=time.time() - 1, ttl=0)
        assert entry.is_expired() is True


class TestCanadaCache:
    def test_init_defaults(self):
        cache = CanadaCache()
        assert cache.default_ttl == 86400
        assert len(cache._cache) == 0

    def test_custom_ttl(self):
        cache = CanadaCache(default_ttl=3600)
        assert cache.default_ttl == 3600

    def test_set_and_get(self):
        cache = CanadaCache()
        cache.set("key1", {"data": "value"})
        assert cache.get("key1") == {"data": "value"}

    def test_get_missing(self):
        cache = CanadaCache()
        assert cache.get("missing") is None

    def test_get_expired(self):
        cache = CanadaCache()
        cache.set("key1", "value", ttl=1)
        cache._cache["key1"].timestamp -= 10
        assert cache.get("key1") is None

    def test_get_expired_removes_entry(self):
        cache = CanadaCache()
        cache.set("key1", "value", ttl=1)
        cache._cache["key1"].timestamp -= 10
        cache.get("key1")
        assert "key1" not in cache._cache

    def test_set_overwrites(self):
        cache = CanadaCache()
        cache.set("k", "v1")
        cache.set("k", "v2")
        assert cache.get("k") == "v2"

    def test_set_custom_ttl(self):
        cache = CanadaCache(default_ttl=86400)
        cache.set("k", "v", ttl=100)
        assert cache._cache["k"].ttl == 100

    def test_delete_existing(self):
        cache = CanadaCache()
        cache.set("k", "v")
        assert cache.delete("k") is True
        assert cache.get("k") is None

    def test_delete_missing(self):
        cache = CanadaCache()
        assert cache.delete("missing") is False

    def test_clear(self):
        cache = CanadaCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_cleanup_expired(self):
        cache = CanadaCache()
        cache.set("fresh", "value", ttl=3600)
        cache.set("old", "value", ttl=1)
        cache._cache["old"].timestamp -= 10
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("fresh") == "value"
        assert "old" not in cache._cache

    def test_cleanup_expired_none(self):
        cache = CanadaCache()
        cache.set("fresh", "value", ttl=3600)
        removed = cache.cleanup_expired()
        assert removed == 0

    def test_stats_initial(self):
        cache = CanadaCache()
        stats = cache.stats
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == "0.0%"

    def test_stats_after_operations(self):
        cache = CanadaCache()
        cache.set("k", "v")
        cache.get("k")  # hit
        cache.get("missing")  # miss
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == "50.0%"

    def test_stats_size(self):
        cache = CanadaCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        assert cache.stats["size"] == 2


class TestFileDownloadCacheInit:
    def test_init_custom_dir(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        assert cache.cache_dir == tmp_path
        assert cache.default_ttl == 86400

    def test_init_custom_ttl(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path, default_ttl=7200)
        assert cache.default_ttl == 7200

    def test_init_creates_dir(self, tmp_path):
        cache_dir = tmp_path / "sub" / "cache"
        cache = FileDownloadCache(cache_dir=cache_dir)
        assert cache_dir.exists()


class TestFileDownloadCacheGenerateKey:
    def test_key_is_md5(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        key = cache._generate_key("https://example.com/data.csv")
        assert isinstance(key, str)
        assert len(key) == 32

    def test_same_url_same_key(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        k1 = cache._generate_key("https://example.com/data")
        k2 = cache._generate_key("https://example.com/data")
        assert k1 == k2

    def test_different_url_different_key(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        k1 = cache._generate_key("https://example.com/a")
        k2 = cache._generate_key("https://example.com/b")
        assert k1 != k2


class TestFileDownloadCacheSaveAndRetrieve:
    def test_save_and_is_cached(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        url = "https://example.com/data.csv"
        cache.save_to_cache(url, b"col1,col2\n1,2\n", suffix=".csv")
        assert cache.is_cached(url) is True

    def test_not_cached(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        assert cache.is_cached("https://example.com/missing") is False

    def test_get_cached_file(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        url = "https://example.com/data.csv"
        cache.save_to_cache(url, b"test data", suffix=".csv")
        path = cache.get_cached_file(url)
        assert path is not None
        assert path.exists()
        assert path.read_bytes() == b"test data"

    def test_get_cached_file_missing(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        assert cache.get_cached_file("https://example.com/none") is None

    def test_save_returns_path(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        path = cache.save_to_cache("https://example.com/f", b"data", suffix=".zip")
        assert path.exists()
        assert str(path).endswith(".zip")

    def test_expired_cache(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path, default_ttl=0)
        url = "https://example.com/data.csv"
        cache.save_to_cache(url, b"test", suffix=".csv")
        time.sleep(0.01)
        assert cache.is_cached(url) is False

    def test_max_age_override(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path, default_ttl=99999)
        url = "https://example.com/data.csv"
        cache.save_to_cache(url, b"test", suffix=".csv")
        # Backdate the timestamp to make it expired with a short max_age
        key = cache._generate_key(url)
        cache._metadata[key]["timestamp"] = time.time() - 100
        cache._save_metadata()
        assert cache.is_cached(url, max_age=10) is False


class TestFileDownloadCacheInvalidate:
    def test_invalidate_existing(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        url = "https://example.com/data.csv"
        cache.save_to_cache(url, b"data", suffix=".csv")
        assert cache.invalidate(url) is True
        assert cache.is_cached(url) is False

    def test_invalidate_missing(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        assert cache.invalidate("https://example.com/none") is False

    def test_invalidate_removes_file(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        url = "https://example.com/data.csv"
        path = cache.save_to_cache(url, b"data", suffix=".csv")
        cache.invalidate(url)
        assert not path.exists()


class TestFileDownloadCacheClear:
    def test_clear_all(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        cache.save_to_cache("https://example.com/a", b"a", suffix=".csv")
        cache.save_to_cache("https://example.com/b", b"b", suffix=".csv")
        count = cache.clear()
        assert count == 2
        assert cache.is_cached("https://example.com/a") is False
        assert cache.is_cached("https://example.com/b") is False

    def test_clear_empty(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        assert cache.clear() == 0


class TestFileDownloadCacheMetadata:
    def test_metadata_persists(self, tmp_path):
        cache1 = FileDownloadCache(cache_dir=tmp_path)
        url = "https://example.com/data.csv"
        cache1.save_to_cache(url, b"persistent", suffix=".csv")

        # Create new instance that reads metadata from disk
        cache2 = FileDownloadCache(cache_dir=tmp_path)
        assert cache2.is_cached(url) is True
        path = cache2.get_cached_file(url)
        assert path is not None
        assert path.read_bytes() == b"persistent"

    def test_metadata_size_tracking(self, tmp_path):
        cache = FileDownloadCache(cache_dir=tmp_path)
        data = b"hello world"
        url = "https://example.com/data.csv"
        cache.save_to_cache(url, data, suffix=".csv")
        key = cache._generate_key(url)
        assert cache._metadata[key]["size"] == len(data)
