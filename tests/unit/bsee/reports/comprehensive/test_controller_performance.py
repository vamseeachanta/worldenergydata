"""Tests for PerformanceConfiguration dataclass defaults."""

import pytest

from worldenergydata.bsee.reports.comprehensive.controller_performance import (
    PerformanceConfiguration,
)


class TestPerformanceConfiguration:
    def test_defaults(self):
        cfg = PerformanceConfiguration()
        assert cfg.cache_enabled is True
        assert cfg.cache_ttl_seconds == 3600
        assert cfg.cache_max_size_mb == 500

    def test_parallel_defaults(self):
        cfg = PerformanceConfiguration()
        assert cfg.parallel_enabled is True
        assert cfg.max_workers is None
        assert cfg.use_threads is False
        assert cfg.batch_size == 1000

    def test_memory_defaults(self):
        cfg = PerformanceConfiguration()
        assert cfg.max_memory_mb == 2000
        assert cfg.enable_memory_monitoring is True

    def test_profiling_defaults(self):
        cfg = PerformanceConfiguration()
        assert cfg.enable_profiling is False
        assert cfg.log_performance_metrics is True

    def test_custom_values(self):
        cfg = PerformanceConfiguration(
            cache_enabled=False,
            cache_ttl_seconds=7200,
            max_workers=4,
            batch_size=500,
        )
        assert cfg.cache_enabled is False
        assert cfg.cache_ttl_seconds == 7200
        assert cfg.max_workers == 4
        assert cfg.batch_size == 500
