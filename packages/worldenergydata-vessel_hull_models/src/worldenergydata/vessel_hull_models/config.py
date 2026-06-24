# ABOUTME: Configuration management for vessel hull models module
# ABOUTME: Uses pydantic-settings for environment-based configuration

"""
Configuration Management for Vessel Hull Models Module

Uses pydantic-settings for environment-based configuration with validation.
"""

from pathlib import Path
from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from worldenergydata.common.data_resolver import get_module_data_safe


class StorageConfig(BaseSettings):
    """Storage configuration for hull models and cache"""

    base_path: Path = Field(
        default_factory=lambda: get_module_data_safe("vessel_hull_models"),
        description="Base path for hull model storage",
    )
    hulls_path: Path = Field(
        default_factory=lambda: get_module_data_safe("vessel_hull_models") / "hulls",
        description="Path for storing acquired hull models",
    )
    synthetic_path: Path = Field(
        default_factory=lambda: get_module_data_safe("vessel_hull_models")
        / "synthetic",
        description="Path for parametrically generated hulls",
    )
    cache_path: Path = Field(
        default_factory=lambda: get_module_data_safe("vessel_hull_models") / "cache",
        description="Path for caching data",
    )
    max_file_size: int = Field(
        default=500 * 1024 * 1024, description="Maximum file size in bytes"  # 500MB
    )

    model_config = SettingsConfigDict(
        env_prefix="VESSEL_HULL_STORAGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "base_path", "hulls_path", "synthetic_path", "cache_path", mode="before"
    )
    @classmethod
    def resolve_paths(cls, v: Any) -> Path:
        """Resolve paths"""
        path = Path(v) if not isinstance(v, Path) else v
        return path.expanduser().resolve()


class AcquisitionConfig(BaseSettings):
    """Configuration for 3D model acquisition"""

    user_agent: str = Field(
        default="WorldEnergyData-VesselHullModels/1.0",
        description="User agent for HTTP requests",
    )
    request_timeout: int = Field(default=60, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(
        default=2.0, description="Delay between retries in seconds"
    )
    rate_limit_delay: float = Field(
        default=1.0, description="Delay between requests in seconds"
    )

    # Repository-specific settings
    cgtrader_enabled: bool = Field(default=True, description="Enable CGTrader search")
    sketchfab_enabled: bool = Field(default=True, description="Enable SketchFab search")
    grabcad_enabled: bool = Field(default=True, description="Enable GrabCAD search")

    # API keys (optional - for premium features)
    sketchfab_api_key: Optional[str] = Field(
        default=None, description="SketchFab API key"
    )

    model_config = SettingsConfigDict(
        env_prefix="VESSEL_HULL_ACQUISITION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class GeometryConfig(BaseSettings):
    """Configuration for geometry processing"""

    dimension_tolerance: float = Field(
        default=0.05, description="Tolerance for dimension validation (0.05 = 5%)"
    )
    default_decimation: int = Field(
        default=50_000, description="Default face count for mesh decimation"
    )
    enable_mesh_repair: bool = Field(
        default=True, description="Enable automatic mesh repair"
    )
    max_vertex_count: int = Field(
        default=10_000_000, description="Maximum vertex count to process"
    )

    model_config = SettingsConfigDict(
        env_prefix="VESSEL_HULL_GEOMETRY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class VisualizationConfig(BaseSettings):
    """Configuration for 3D visualization"""

    default_colorscale: str = Field(
        default="Viridis", description="Default Plotly colorscale for depth coloring"
    )
    show_waterline: bool = Field(
        default=True, description="Show waterline plane by default"
    )
    background_color: str = Field(
        default="rgb(230, 240, 250)", description="Default background color"
    )
    html_template_dir: Path = Field(
        default=Path(
            "src/worldenergydata/modules/vessel_hull_models/visualization/templates"
        ),
        description="Directory for HTML templates",
    )

    model_config = SettingsConfigDict(
        env_prefix="VESSEL_HULL_VIZ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class VesselHullModelsConfig(BaseSettings):
    """Main configuration for Vessel Hull Models Module"""

    # Sub-configurations
    storage: StorageConfig = Field(default_factory=StorageConfig)
    acquisition: AcquisitionConfig = Field(default_factory=AcquisitionConfig)
    geometry: GeometryConfig = Field(default_factory=GeometryConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)

    # General settings
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="production", description="Environment name")

    model_config = SettingsConfigDict(
        env_prefix="VESSEL_HULL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global configuration instance
_config: Optional[VesselHullModelsConfig] = None


def get_config() -> VesselHullModelsConfig:
    """
    Get or create the global configuration instance.

    Returns:
        VesselHullModelsConfig: The global configuration instance
    """
    global _config
    if _config is None:
        _config = VesselHullModelsConfig()
    return _config


def reload_config() -> VesselHullModelsConfig:
    """
    Reload the global configuration instance.

    Returns:
        VesselHullModelsConfig: The reloaded configuration instance
    """
    global _config
    _config = VesselHullModelsConfig()
    return _config


# Convenience export
config = get_config()
