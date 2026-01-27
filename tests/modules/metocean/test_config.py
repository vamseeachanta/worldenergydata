# ABOUTME: Tests for metocean configuration.
# ABOUTME: Validates config loading, defaults, and environment variable handling.

"""Tests for metocean configuration"""

import os
from unittest.mock import patch

import pytest


class TestMetoceanConfig:
    """Tests for MetoceanConfig class."""

    def test_config_loads_defaults(self):
        """Test that config loads with default values."""
        from worldenergydata.modules.metocean.config import MetoceanConfig

        config = MetoceanConfig()

        # Check API defaults
        assert config.api.request_timeout == 30
        assert config.api.max_retries == 3
        assert config.api.rate_limit_delay == 1.0
        assert config.api.concurrent_requests == 5

        # Check cache defaults
        assert config.cache.ttl_hours == 24
        assert config.cache.max_size_mb == 500
        assert config.cache.enabled is True

        # Check database defaults
        assert config.database.host == "localhost"
        assert config.database.port == 5432
        assert config.database.database == "worldenergydata"

    def test_get_config_singleton(self):
        """Test that get_config returns the same instance."""
        from worldenergydata.modules.metocean.config import get_config, reload_config

        # Force reload to start fresh
        reload_config()

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reload_config_creates_new_instance(self):
        """Test that reload_config creates a new instance."""
        from worldenergydata.modules.metocean.config import get_config, reload_config

        config1 = get_config()
        config2 = reload_config()

        # After reload, get_config should return the new instance
        config3 = get_config()
        assert config2 is config3

    def test_database_url_generation(self):
        """Test database URL generation."""
        from worldenergydata.modules.metocean.config import DatabaseConfig

        db_config = DatabaseConfig(
            host="testhost",
            port=5433,
            database="testdb",
            username="testuser",
            password="testpass",
        )

        assert "testhost" in db_config.url
        assert "5433" in db_config.url
        assert "testdb" in db_config.url
        assert "testuser" in db_config.url
        assert "testpass" in db_config.url

    def test_async_database_url(self):
        """Test async database URL generation."""
        from worldenergydata.modules.metocean.config import DatabaseConfig

        db_config = DatabaseConfig()
        assert "asyncpg" in db_config.async_url

    def test_environment_validation(self):
        """Test that invalid environment raises error."""
        from pydantic import ValidationError

        from worldenergydata.modules.metocean.config import MetoceanConfig

        with pytest.raises(ValidationError):
            MetoceanConfig(environment="invalid_env")

    def test_valid_environments(self):
        """Test that valid environments are accepted."""
        from worldenergydata.modules.metocean.config import MetoceanConfig

        for env in ["development", "staging", "production", "test"]:
            config = MetoceanConfig(environment=env)
            assert config.environment == env

    def test_cache_path_resolution(self):
        """Test that cache path is resolved and created."""
        import tempfile
        from pathlib import Path

        from worldenergydata.modules.metocean.config import CacheConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache"
            config = CacheConfig(cache_path=cache_path)

            # Path should be resolved and created
            assert config.cache_path.is_absolute()
            assert config.cache_path.exists()


class TestAPIConfig:
    """Tests for APIConfig class."""

    def test_api_config_defaults(self):
        """Test API config default values."""
        from worldenergydata.modules.metocean.config import APIConfig

        config = APIConfig()

        assert config.request_timeout == 30
        assert config.max_retries == 3
        assert config.retry_delay == 5
        assert config.rate_limit_delay == 1.0
        assert config.concurrent_requests == 5
        assert "WorldEnergyData" in config.user_agent

    def test_cmems_credentials_optional(self):
        """Test that CMEMS credentials are optional."""
        from worldenergydata.modules.metocean.config import APIConfig

        config = APIConfig()
        assert config.cmems_username is None
        assert config.cmems_password is None


class TestStorageConfig:
    """Tests for StorageConfig class."""

    def test_storage_paths_created(self):
        """Test that storage paths are created on initialization."""
        import tempfile
        from pathlib import Path

        from worldenergydata.modules.metocean.config import StorageConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "metocean"
            raw = Path(tmpdir) / "metocean" / "raw"
            processed = Path(tmpdir) / "metocean" / "processed"

            config = StorageConfig(
                base_path=base,
                raw_path=raw,
                processed_path=processed,
            )

            assert config.base_path.exists()
            assert config.raw_path.exists()
            assert config.processed_path.exists()
