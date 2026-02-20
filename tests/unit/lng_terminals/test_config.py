"""Tests for LNG terminals configuration."""

import pytest

from worldenergydata.lng_terminals.config import (
    CacheConfig,
    LNGTerminalsConfig,
    ProcessingConfig,
    ScraperConfig,
    SourceConfig,
)


# ---------------------------------------------------------------------------
# ScraperConfig
# ---------------------------------------------------------------------------

class TestScraperConfig:
    def test_defaults(self):
        c = ScraperConfig()
        assert c.user_agent == "WorldEnergyData-LNGTerminals/1.0"
        assert c.request_timeout == 30.0
        assert c.max_retries == 3

    def test_custom(self):
        c = ScraperConfig(request_timeout=60.0, max_retries=5)
        assert c.request_timeout == 60.0
        assert c.max_retries == 5


# ---------------------------------------------------------------------------
# SourceConfig
# ---------------------------------------------------------------------------

class TestSourceConfig:
    def test_defaults(self):
        c = SourceConfig(name="test_source")
        assert c.name == "test_source"
        assert c.enabled is True
        assert c.cache_ttl == 86400

    def test_disabled(self):
        c = SourceConfig(name="disabled", enabled=False)
        assert c.enabled is False


# ---------------------------------------------------------------------------
# CacheConfig
# ---------------------------------------------------------------------------

class TestCacheConfig:
    def test_defaults(self):
        c = CacheConfig()
        assert c.enabled is True
        assert c.default_refresh_mode == "cache_first"
        assert c.max_age_seconds == 86400


# ---------------------------------------------------------------------------
# ProcessingConfig
# ---------------------------------------------------------------------------

class TestProcessingConfig:
    def test_defaults(self):
        c = ProcessingConfig()
        assert c.fuzzy_match_threshold == 0.85
        assert c.coordinate_proximity_km == 50.0
        assert c.max_pipelines_per_terminal == 8


# ---------------------------------------------------------------------------
# LNGTerminalsConfig
# ---------------------------------------------------------------------------

class TestLNGTerminalsConfig:
    def test_defaults(self):
        c = LNGTerminalsConfig()
        assert isinstance(c.scraper, ScraperConfig)
        assert isinstance(c.processing, ProcessingConfig)
        assert isinstance(c.cache, CacheConfig)
        assert c.output_formats == ["csv", "parquet"]

    def test_with_sources(self):
        c = LNGTerminalsConfig(
            sources={"giignl": SourceConfig(name="GIIGNL")}
        )
        assert "giignl" in c.sources
        assert c.sources["giignl"].name == "GIIGNL"
