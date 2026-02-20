"""Tests for vessel hull models configuration module."""

import pytest

from worldenergydata.vessel_hull_models.config import (
    AcquisitionConfig,
    GeometryConfig,
    StorageConfig,
    VesselHullModelsConfig,
    VisualizationConfig,
    get_config,
    reload_config,
)


# ---------------------------------------------------------------------------
# StorageConfig
# ---------------------------------------------------------------------------

class TestStorageConfig:
    def test_defaults(self):
        config = StorageConfig()
        assert "vessel_hull_models" in str(config.base_path)
        assert config.max_file_size == 500 * 1024 * 1024

    def test_paths_are_resolved(self):
        config = StorageConfig()
        assert config.base_path.is_absolute()
        assert config.hulls_path.is_absolute()
        assert config.synthetic_path.is_absolute()
        assert config.cache_path.is_absolute()


# ---------------------------------------------------------------------------
# AcquisitionConfig
# ---------------------------------------------------------------------------

class TestAcquisitionConfig:
    def test_defaults(self):
        config = AcquisitionConfig()
        assert config.user_agent == "WorldEnergyData-VesselHullModels/1.0"
        assert config.request_timeout == 60
        assert config.max_retries == 3
        assert config.retry_delay == 2.0
        assert config.rate_limit_delay == 1.0

    def test_repository_flags(self):
        config = AcquisitionConfig()
        assert config.cgtrader_enabled is True
        assert config.sketchfab_enabled is True
        assert config.grabcad_enabled is True

    def test_api_key_optional(self):
        config = AcquisitionConfig()
        assert config.sketchfab_api_key is None


# ---------------------------------------------------------------------------
# GeometryConfig
# ---------------------------------------------------------------------------

class TestGeometryConfig:
    def test_defaults(self):
        config = GeometryConfig()
        assert config.dimension_tolerance == 0.05
        assert config.default_decimation == 50_000
        assert config.enable_mesh_repair is True
        assert config.max_vertex_count == 10_000_000


# ---------------------------------------------------------------------------
# VisualizationConfig
# ---------------------------------------------------------------------------

class TestVisualizationConfig:
    def test_defaults(self):
        config = VisualizationConfig()
        assert config.default_colorscale == "Viridis"
        assert config.show_waterline is True
        assert "230" in config.background_color


# ---------------------------------------------------------------------------
# VesselHullModelsConfig (main)
# ---------------------------------------------------------------------------

class TestVesselHullModelsConfig:
    def test_defaults(self):
        config = VesselHullModelsConfig()
        assert config.debug is False
        assert config.environment == "production"

    def test_sub_configs(self):
        config = VesselHullModelsConfig()
        assert isinstance(config.storage, StorageConfig)
        assert isinstance(config.acquisition, AcquisitionConfig)
        assert isinstance(config.geometry, GeometryConfig)
        assert isinstance(config.visualization, VisualizationConfig)


# ---------------------------------------------------------------------------
# Module-level functions
# ---------------------------------------------------------------------------

class TestGetConfig:
    def test_returns_config(self):
        config = get_config()
        assert isinstance(config, VesselHullModelsConfig)

    def test_singleton(self):
        c1 = get_config()
        c2 = get_config()
        # Should return same instance (cached)
        assert c1 is c2


class TestReloadConfig:
    def test_returns_new_config(self):
        c1 = get_config()
        c2 = reload_config()
        assert isinstance(c2, VesselHullModelsConfig)
