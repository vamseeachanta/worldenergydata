"""
ABOUTME: Configuration management for the Metocean module.
ABOUTME: Uses pydantic-settings for environment-based configuration with validation.
"""

from pathlib import Path
from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database connection configuration for metocean data storage."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="worldenergydata", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")
    schema: str = Field(default="metocean", description="Database schema")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max connection overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    echo: bool = Field(default=False, description="Echo SQL statements")

    model_config = SettingsConfigDict(
        env_prefix="METOCEAN_DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def url(self) -> str:
        """Generate SQLAlchemy database URL."""
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    @property
    def async_url(self) -> str:
        """Generate async SQLAlchemy database URL."""
        return (
            f"postgresql+asyncpg://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


class APIConfig(BaseSettings):
    """Configuration for external API connections."""

    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: int = Field(default=5, description="Delay between retries in seconds")
    rate_limit_delay: float = Field(
        default=1.0, description="Delay between requests in seconds"
    )
    concurrent_requests: int = Field(
        default=5, description="Maximum concurrent requests"
    )
    user_agent: str = Field(
        default="WorldEnergyData-Metocean/1.0",
        description="User agent for HTTP requests",
    )

    # Copernicus Marine Service credentials (optional)
    cmems_username: Optional[str] = Field(
        default=None, description="CMEMS username for authentication"
    )
    cmems_password: Optional[str] = Field(
        default=None, description="CMEMS password for authentication"
    )

    model_config = SettingsConfigDict(
        env_prefix="METOCEAN_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class CacheConfig(BaseSettings):
    """Configuration for data caching."""

    ttl_hours: int = Field(default=24, description="Cache time-to-live in hours")
    max_size_mb: int = Field(default=500, description="Maximum cache size in MB")
    cache_path: Path = Field(
        default=Path("data/metocean/cache"), description="Path for cache storage"
    )
    enabled: bool = Field(default=True, description="Enable caching")

    model_config = SettingsConfigDict(
        env_prefix="METOCEAN_CACHE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cache_path", mode="before")
    @classmethod
    def resolve_cache_path(cls, v: Any) -> Path:
        """Resolve and create cache path if it doesn't exist."""
        path = Path(v) if not isinstance(v, Path) else v
        path = path.expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


class StorageConfig(BaseSettings):
    """Configuration for data storage."""

    base_path: Path = Field(
        default=Path("data/metocean"), description="Base path for data storage"
    )
    raw_path: Path = Field(
        default=Path("data/metocean/raw"), description="Path for raw data"
    )
    processed_path: Path = Field(
        default=Path("data/metocean/processed"), description="Path for processed data"
    )

    model_config = SettingsConfigDict(
        env_prefix="METOCEAN_STORAGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("base_path", "raw_path", "processed_path", mode="before")
    @classmethod
    def resolve_paths(cls, v: Any) -> Path:
        """Resolve and create paths if they don't exist."""
        path = Path(v) if not isinstance(v, Path) else v
        path = path.expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    file_path: Optional[Path] = Field(
        default=Path("logs/metocean.log"), description="Log file path"
    )

    model_config = SettingsConfigDict(
        env_prefix="METOCEAN_LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("file_path", mode="before")
    @classmethod
    def resolve_log_path(cls, v: Any) -> Optional[Path]:
        """Resolve log file path and create directory."""
        if v is None:
            return None
        path = Path(v) if not isinstance(v, Path) else v
        path = path.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


class MetoceanConfig(BaseSettings):
    """Main configuration for Metocean module."""

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # General settings
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="production", description="Environment name")

    model_config = SettingsConfigDict(
        env_prefix="METOCEAN_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        valid_environments = {"development", "staging", "production", "test"}
        if v.lower() not in valid_environments:
            raise ValueError(
                f"Invalid environment: {v}. Must be one of {valid_environments}"
            )
        return v.lower()


# Global configuration instance
_config: Optional[MetoceanConfig] = None


def get_config() -> MetoceanConfig:
    """
    Get or create the global configuration instance.

    Returns:
        MetoceanConfig: The global configuration instance
    """
    global _config
    if _config is None:
        _config = MetoceanConfig()
    return _config


def reload_config() -> MetoceanConfig:
    """
    Reload the global configuration instance.

    Returns:
        MetoceanConfig: The reloaded configuration instance
    """
    global _config
    _config = MetoceanConfig()
    return _config
