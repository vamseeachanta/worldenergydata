"""
Configuration Management for Marine Safety Module

Uses pydantic-settings for environment-based configuration with validation.
"""

from pathlib import Path
from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from worldenergydata.common.data_resolver import get_data_root_safe


class DatabaseConfig(BaseSettings):
    """Database connection configuration"""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="worldenergydata", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")
    schema: str = Field(default="marine_safety", description="Database schema")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max connection overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    echo: bool = Field(default=False, description="Echo SQL statements")

    model_config = SettingsConfigDict(
        env_prefix="MARINE_SAFETY_DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def url(self) -> str:
        """Generate SQLAlchemy database URL"""
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    @property
    def async_url(self) -> str:
        """Generate async SQLAlchemy database URL"""
        return (
            f"postgresql+asyncpg://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


class ScraperConfig(BaseSettings):
    """Web scraping configuration"""

    user_agent: str = Field(
        default="WorldEnergyData-MarineSafety/1.0",
        description="User agent for HTTP requests",
    )
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: int = Field(default=5, description="Delay between retries in seconds")
    rate_limit_delay: float = Field(
        default=1.0, description="Delay between requests in seconds"
    )
    concurrent_requests: int = Field(
        default=5, description="Maximum concurrent requests"
    )
    respect_robots_txt: bool = Field(
        default=True, description="Respect robots.txt directives"
    )

    # Source-specific configurations
    bsee_enabled: bool = Field(default=True, description="Enable BSEE scraping")
    uscg_enabled: bool = Field(default=True, description="Enable USCG scraping")
    ntsb_enabled: bool = Field(default=True, description="Enable NTSB scraping")
    maib_enabled: bool = Field(default=True, description="Enable MAIB scraping")

    model_config = SettingsConfigDict(
        env_prefix="MARINE_SAFETY_SCRAPER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class StorageConfig(BaseSettings):
    """Storage configuration for documents and files"""

    base_path: Path = Field(
        default_factory=lambda: get_data_root_safe() / "marine_safety",
        description="Base path for data storage",
    )
    documents_path: Path = Field(
        default_factory=lambda: get_data_root_safe() / "marine_safety" / "documents",
        description="Path for storing documents",
    )
    cache_path: Path = Field(
        default_factory=lambda: get_data_root_safe() / "marine_safety" / "cache",
        description="Path for caching data",
    )
    max_file_size: int = Field(
        default=100 * 1024 * 1024, description="Maximum file size in bytes"  # 100MB
    )

    model_config = SettingsConfigDict(
        env_prefix="MARINE_SAFETY_STORAGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("base_path", "documents_path", "cache_path", mode="before")
    @classmethod
    def resolve_paths(cls, v: Any) -> Path:
        """Resolve and create paths if they don't exist"""
        path = Path(v) if not isinstance(v, Path) else v
        path = path.expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


class LoggingConfig(BaseSettings):
    """Logging configuration"""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    file_path: Optional[Path] = Field(
        default=Path("logs/marine_safety.log"), description="Log file path"
    )
    max_bytes: int = Field(
        default=10 * 1024 * 1024, description="Maximum log file size"  # 10MB
    )
    backup_count: int = Field(default=5, description="Number of backup log files")
    console_output: bool = Field(default=True, description="Enable console output")

    model_config = SettingsConfigDict(
        env_prefix="MARINE_SAFETY_LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("file_path", mode="before")
    @classmethod
    def resolve_log_path(cls, v: Any) -> Optional[Path]:
        """Resolve log file path and create directory"""
        if v is None:
            return None
        path = Path(v) if not isinstance(v, Path) else v
        path = path.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


class MarineSafetyConfig(BaseSettings):
    """Main configuration for Marine Safety Module"""

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # General settings
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="production", description="Environment name")

    model_config = SettingsConfigDict(
        env_prefix="MARINE_SAFETY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value"""
        valid_environments = {"development", "staging", "production", "test"}
        if v.lower() not in valid_environments:
            raise ValueError(
                f"Invalid environment: {v}. Must be one of {valid_environments}"
            )
        return v.lower()


# Global configuration instance
_config: Optional[MarineSafetyConfig] = None


def get_config() -> MarineSafetyConfig:
    """
    Get or create the global configuration instance.

    Returns:
        MarineSafetyConfig: The global configuration instance
    """
    global _config
    if _config is None:
        _config = MarineSafetyConfig()
    return _config


def reload_config() -> MarineSafetyConfig:
    """
    Reload the global configuration instance.

    Returns:
        MarineSafetyConfig: The reloaded configuration instance
    """
    global _config
    _config = MarineSafetyConfig()
    return _config


# Convenience export
config = get_config()
