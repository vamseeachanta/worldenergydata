"""
Tests for worldenergydata.common.config module.

Tests cover:
- Settings loads from environment
- DatabaseSettings validates URLs
- CacheSettings has correct defaults
- get_settings() returns singleton
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestDatabaseSettings:
    """Tests for DatabaseSettings class."""

    def test_default_values(self):
        """Test DatabaseSettings has correct default values."""
        from worldenergydata.common.config import DatabaseSettings

        settings = DatabaseSettings()

        assert settings.host == "localhost"
        assert settings.port == 5432
        assert settings.name == "worldenergydata"
        assert settings.user == ""
        assert settings.password == ""
        assert settings.pool_size == 5
        assert settings.max_overflow == 10
        assert settings.pool_timeout == 30
        assert settings.ssl_mode == "prefer"

    def test_url_without_user_returns_sqlite(self):
        """Test URL generation falls back to SQLite without user."""
        from worldenergydata.common.config import DatabaseSettings

        settings = DatabaseSettings()

        assert settings.url == "sqlite:///worldenergydata.db"

    def test_url_with_user_returns_postgresql(self):
        """Test URL generation returns PostgreSQL with user."""
        from worldenergydata.common.config import DatabaseSettings

        settings = DatabaseSettings(
            host="db.example.com",
            port=5433,
            name="energydb",
            user="admin",
            password="secret",
        )

        expected = "postgresql://admin:secret@db.example.com:5433/energydb"
        assert settings.url == expected

    def test_async_url_without_user(self):
        """Test async URL generation falls back to aiosqlite."""
        from worldenergydata.common.config import DatabaseSettings

        settings = DatabaseSettings()

        assert settings.async_url == "sqlite+aiosqlite:///worldenergydata.db"

    def test_async_url_with_user(self):
        """Test async URL generation returns asyncpg."""
        from worldenergydata.common.config import DatabaseSettings

        settings = DatabaseSettings(
            host="db.example.com",
            port=5433,
            name="energydb",
            user="admin",
            password="secret",
        )

        expected = "postgresql+asyncpg://admin:secret@db.example.com:5433/energydb"
        assert settings.async_url == expected

    def test_settings_from_environment(self):
        """Test DatabaseSettings loads from environment variables."""
        from worldenergydata.common.config import DatabaseSettings

        env = {
            "DB_HOST": "proddb.example.com",
            "DB_PORT": "5434",
            "DB_NAME": "production",
            "DB_USER": "produser",
            "DB_PASSWORD": "prodpass",
        }

        with patch.dict(os.environ, env, clear=False):
            settings = DatabaseSettings()

        assert settings.host == "proddb.example.com"
        assert settings.port == 5434
        assert settings.name == "production"
        assert settings.user == "produser"


class TestCacheSettings:
    """Tests for CacheSettings class."""

    def test_default_values(self):
        """Test CacheSettings has correct default values."""
        from worldenergydata.common.config import CacheSettings

        settings = CacheSettings()

        assert settings.backend == "memory"
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.directory == Path(".cache")
        assert settings.ttl_seconds == 3600
        assert settings.max_size_mb == 100
        assert settings.enabled is True

    def test_settings_from_environment(self):
        """Test CacheSettings loads from environment variables."""
        from worldenergydata.common.config import CacheSettings

        env = {
            "CACHE_BACKEND": "redis",
            "CACHE_REDIS_URL": "redis://cache.example.com:6380/1",
            "CACHE_TTL_SECONDS": "7200",
            "CACHE_ENABLED": "false",
        }

        with patch.dict(os.environ, env, clear=False):
            settings = CacheSettings()

        assert settings.backend == "redis"
        assert settings.redis_url == "redis://cache.example.com:6380/1"
        assert settings.ttl_seconds == 7200


class TestAPISettings:
    """Tests for APISettings class."""

    def test_default_values(self):
        """Test APISettings has correct default values."""
        from worldenergydata.common.config import APISettings

        settings = APISettings()

        assert settings.bsee_base_url == "https://www.data.bsee.gov"
        assert settings.bsee_timeout == 60
        assert settings.bsee_retries == 3
        assert settings.eia_api_key == ""
        assert settings.eia_base_url == "https://api.eia.gov"
        assert settings.sodir_base_url == "https://factpages.sodir.no"
        assert settings.rate_limit_requests == 10
        assert settings.rate_limit_period == 1

    def test_eia_api_key_validation_short(self):
        """Test EIA API key validation rejects short keys."""
        from worldenergydata.common.config import APISettings
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            APISettings(eia_api_key="short")

        assert "too short" in str(exc_info.value).lower()

    def test_eia_api_key_validation_empty_allowed(self):
        """Test empty EIA API key is allowed."""
        from worldenergydata.common.config import APISettings

        settings = APISettings(eia_api_key="")

        assert settings.eia_api_key == ""

    def test_eia_api_key_validation_valid(self):
        """Test valid EIA API key is accepted."""
        from worldenergydata.common.config import APISettings

        valid_key = "abcdefghij12345"
        settings = APISettings(eia_api_key=valid_key)

        assert settings.eia_api_key == valid_key


class TestSettings:
    """Tests for main Settings class."""

    def test_default_values(self):
        """Test Settings has correct default values."""
        from worldenergydata.common.config import Settings

        settings = Settings()

        assert settings.app_name == "WorldEnergyData"
        assert settings.debug is False
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.log_json is False
        assert settings.parallel_workers == 4
        assert settings.batch_size == 1000
        assert settings.chunk_size_mb == 50

    def test_nested_settings(self):
        """Test nested settings objects are created."""
        from worldenergydata.common.config import Settings, DatabaseSettings, CacheSettings, APISettings

        settings = Settings()

        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.cache, CacheSettings)
        assert isinstance(settings.api, APISettings)

    def test_log_level_validation_valid(self):
        """Test valid log levels are accepted."""
        from worldenergydata.common.config import Settings

        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = Settings(log_level=level)
            assert settings.log_level == level

    def test_log_level_validation_case_insensitive(self):
        """Test log level validation is case insensitive."""
        from worldenergydata.common.config import Settings

        settings = Settings(log_level="debug")

        assert settings.log_level == "DEBUG"

    def test_log_level_validation_invalid(self):
        """Test invalid log level is rejected."""
        from worldenergydata.common.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            Settings(log_level="INVALID")

        assert "Invalid log level" in str(exc_info.value)

    def test_environment_validation_valid(self):
        """Test valid environment values are accepted."""
        from worldenergydata.common.config import Settings

        for env in ["development", "staging", "production", "test"]:
            settings = Settings(environment=env)
            assert settings.environment == env

    def test_environment_validation_case_insensitive(self):
        """Test environment validation is case insensitive."""
        from worldenergydata.common.config import Settings

        settings = Settings(environment="PRODUCTION")

        assert settings.environment == "production"

    def test_environment_validation_invalid(self):
        """Test invalid environment is rejected."""
        from worldenergydata.common.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            Settings(environment="invalid")

        assert "Invalid environment" in str(exc_info.value)

    def test_is_production(self):
        """Test is_production() method."""
        from worldenergydata.common.config import Settings

        dev_settings = Settings(environment="development")
        prod_settings = Settings(environment="production")

        assert dev_settings.is_production() is False
        assert prod_settings.is_production() is True

    def test_is_debug(self):
        """Test is_debug() method."""
        from worldenergydata.common.config import Settings

        dev_settings = Settings(environment="development", debug=False)
        prod_debug_settings = Settings(environment="production", debug=True)
        prod_settings = Settings(environment="production", debug=False)

        assert dev_settings.is_debug() is True  # development = debug
        assert prod_debug_settings.is_debug() is True
        assert prod_settings.is_debug() is False

    def test_get_module_data_dir(self, tmp_path):
        """Test get_module_data_dir() creates and returns module directory."""
        from worldenergydata.common.config import Settings

        settings = Settings(data_dir=tmp_path / "data")

        module_dir = settings.get_module_data_dir("bsee")

        assert module_dir == tmp_path / "data" / "bsee"
        assert module_dir.exists()

    def test_settings_from_environment(self, tmp_path):
        """Test Settings loads from environment variables."""
        from worldenergydata.common.config import Settings

        env = {
            "WED_APP_NAME": "TestApp",
            "WED_DEBUG": "true",
            "WED_ENVIRONMENT": "test",
            "WED_LOG_LEVEL": "DEBUG",
            "WED_DATA_DIR": str(tmp_path / "data"),
        }

        with patch.dict(os.environ, env, clear=False):
            settings = Settings()

        assert settings.app_name == "TestApp"
        assert settings.debug is True
        assert settings.environment == "test"
        assert settings.log_level == "DEBUG"


class TestGetSettings:
    """Tests for get_settings() function."""

    def test_returns_settings_instance(self):
        """Test get_settings returns Settings instance."""
        from worldenergydata.common.config import get_settings, Settings, clear_settings

        clear_settings()
        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_returns_cached_singleton(self):
        """Test get_settings returns the same instance (singleton)."""
        from worldenergydata.common.config import get_settings, clear_settings

        clear_settings()
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_clear_settings_resets_cache(self):
        """Test clear_settings allows new instance creation."""
        from worldenergydata.common.config import get_settings, clear_settings

        clear_settings()
        settings1 = get_settings()
        clear_settings()
        settings2 = get_settings()

        # They should be different instances
        assert settings1 is not settings2


class TestGetModuleSettings:
    """Tests for get_module_settings() function."""

    def test_returns_module_specific_settings(self):
        """Test get_module_settings returns module-specific env vars."""
        from worldenergydata.common.config import get_module_settings

        env = {
            "MODULE_BSEE_API_URL": "https://bsee.example.com",
            "MODULE_BSEE_TIMEOUT": "120",
            "OTHER_VAR": "ignored",
        }

        with patch.dict(os.environ, env, clear=False):
            settings = get_module_settings("bsee")

        assert settings["api_url"] == "https://bsee.example.com"
        assert settings["timeout"] == "120"
        assert "other_var" not in settings

    def test_empty_when_no_module_vars(self):
        """Test get_module_settings returns empty dict when no matching vars."""
        from worldenergydata.common.config import get_module_settings

        with patch.dict(os.environ, {}, clear=True):
            settings = get_module_settings("nonexistent")

        assert settings == {}

    def test_case_sensitivity(self):
        """Test get_module_settings uses uppercase module name prefix."""
        from worldenergydata.common.config import get_module_settings

        env = {
            "MODULE_SODIR_BASE_URL": "https://sodir.example.com",
        }

        with patch.dict(os.environ, env, clear=False):
            settings = get_module_settings("sodir")

        assert settings["base_url"] == "https://sodir.example.com"
