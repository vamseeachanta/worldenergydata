"""
Environment-Based Configuration for WorldEnergyData

This module provides centralized configuration management using pydantic-settings.
All configuration is loaded from environment variables with sensible defaults.

Environment variables can be set directly or loaded from a .env file.

Example usage:
    from worldenergydata.common.config import get_settings, Settings

    settings = get_settings()
    logger.info(settings.data_dir)
    logger.info(settings.bsee_api_base_url)
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from worldenergydata.common.data_resolver import get_data_root_safe
from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Connection settings
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="worldenergydata", description="Database name")
    user: str = Field(default="", description="Database user")
    password: str = Field(default="", description="Database password")

    # Connection pool settings
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")

    # SSL settings
    ssl_mode: str = Field(
        default="prefer", description="SSL mode (disable, prefer, require)"
    )

    @property
    def url(self) -> str:
        """Generate database connection URL."""
        if not self.user:
            return f"sqlite:///{self.name}.db"
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def async_url(self) -> str:
        """Generate async database connection URL."""
        if not self.user:
            return f"sqlite+aiosqlite:///{self.name}.db"
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class CacheSettings(BaseSettings):
    """Cache configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="CACHE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Cache type (memory, redis, file)
    backend: str = Field(default="memory", description="Cache backend type")

    # Redis settings (if using redis backend)
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")

    # File cache settings
    directory: Path = Field(
        default=Path(".cache"), description="Directory for file-based cache"
    )

    # Cache behavior
    ttl_seconds: int = Field(default=3600, description="Default TTL in seconds")
    max_size_mb: int = Field(default=100, description="Max cache size in MB")
    enabled: bool = Field(default=True, description="Enable/disable caching")


class APISettings(BaseSettings):
    """API configuration for external data sources."""

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # BSEE API settings
    bsee_base_url: str = Field(
        default="https://www.data.bsee.gov", description="BSEE data portal base URL"
    )
    bsee_timeout: int = Field(default=60, description="BSEE API timeout in seconds")
    bsee_retries: int = Field(default=3, description="BSEE API retry count")

    # EIA API settings
    eia_api_key: str = Field(default="", description="EIA API key")
    eia_base_url: str = Field(
        default="https://api.eia.gov", description="EIA API base URL"
    )

    # SODIR (Norwegian) API settings
    sodir_base_url: str = Field(
        default="https://factmaps.sodir.no", description="SODIR data portal base URL"
    )

    # General API settings
    rate_limit_requests: int = Field(
        default=10, description="Max requests per rate_limit_period"
    )
    rate_limit_period: int = Field(
        default=1, description="Rate limit period in seconds"
    )

    @field_validator("eia_api_key")
    @classmethod
    def validate_eia_key(cls, v: str) -> str:
        """Validate EIA API key format if provided."""
        if v and len(v) < 10:
            raise ValueError("EIA API key appears to be invalid (too short)")
        return v


class Settings(BaseSettings):
    """
    Main application settings.

    All settings can be overridden via environment variables.
    Variables are prefixed with WED_ (WorldEnergyData).

    Example:
        WED_DEBUG=true
        WED_DATA_DIR=/data/energy
        DB_HOST=postgres.example.com
    """

    model_config = SettingsConfigDict(
        env_prefix="WED_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default="WorldEnergyData", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment name")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_json: bool = Field(default=False, description="Output logs as JSON")

    # Data directories
    data_dir: Path = Field(
        default_factory=get_data_root_safe, description="Base data directory"
    )
    raw_data_dir: Path = Field(
        default_factory=lambda: get_data_root_safe() / "raw",
        description="Raw data directory",
    )
    processed_data_dir: Path = Field(
        default_factory=lambda: get_data_root_safe() / "processed",
        description="Processed data directory",
    )
    reports_dir: Path = Field(
        default=Path("reports"), description="Reports output directory"
    )

    # Processing settings
    parallel_workers: int = Field(default=4, description="Number of parallel workers")
    batch_size: int = Field(
        default=1000, description="Default batch size for processing"
    )
    chunk_size_mb: int = Field(
        default=50, description="Chunk size for large file processing in MB"
    )

    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    api: APISettings = Field(default_factory=APISettings)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment name."""
        valid_envs = {"development", "staging", "production", "test"}
        v = v.lower()
        if v not in valid_envs:
            raise ValueError(f"Invalid environment: {v}. Must be one of {valid_envs}")
        return v

    @model_validator(mode="after")
    def create_directories(self) -> "Settings":
        """Create data directories if they don't exist."""
        for dir_path in [
            self.data_dir,
            self.raw_data_dir,
            self.processed_data_dir,
            self.reports_dir,
        ]:
            if not dir_path.is_absolute():
                # Make relative paths absolute based on current working directory
                dir_path = Path.cwd() / dir_path
            dir_path.mkdir(parents=True, exist_ok=True)
        return self

    def get_module_data_dir(self, module_name: str) -> Path:
        """
        Get data directory for a specific module.

        Args:
            module_name: Name of the module (e.g., "bsee", "sodir")

        Returns:
            Path to the module's data directory
        """
        module_dir = self.data_dir / module_name
        module_dir.mkdir(parents=True, exist_ok=True)
        return module_dir

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug or self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get the application settings singleton.

    Settings are cached after first load. Use clear_settings() to reload.

    Returns:
        Settings instance

    Example:
        settings = get_settings()
        logger.info(settings.data_dir)
    """
    return Settings()


def clear_settings() -> None:
    """
    Clear the cached settings.

    Call this to force a reload of settings from environment.
    """
    get_settings.cache_clear()


def get_module_settings(module_name: str) -> Dict[str, Any]:
    """
    Get settings specific to a module.

    Loads module-specific environment variables with prefix MODULE_{NAME}_.

    Args:
        module_name: Name of the module (e.g., "bsee", "sodir")

    Returns:
        Dictionary of module-specific settings
    """
    prefix = f"MODULE_{module_name.upper()}_"
    return {
        key[len(prefix) :].lower(): value
        for key, value in os.environ.items()
        if key.startswith(prefix)
    }
