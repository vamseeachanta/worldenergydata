from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Module base paths
MODULE_DIR = Path(__file__).parent
# Curated/runtime data ships INSIDE this member as package data (ADR 0001
# Phase 2 batch 4, #529 — option (i): data travels with the package), at
# ``worldenergydata/lng_terminals/_data/``. Resolve it package-relative so the
# module works identically from an editable workspace install or the built
# wheel (the previous ``__file__``-relative repo-root walk broke once this
# domain moved under ``packages/``).
DATA_DIR = MODULE_DIR / "_data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = DATA_DIR / "reports"
CACHE_DIR = DATA_DIR / "cache"
# The optional ``config/lng_terminals.yml`` override is per-domain config DATA
# that stays at the workspace root (ADR 0001 — base_configs/config stay with
# the root distribution). Resolve it via the common data resolver's workspace
# root; ``_load_config`` falls back to defaults when absent.
CONFIG_PATH = MODULE_DIR / "_data" / "lng_terminals.yml"


class ScraperConfig(BaseModel):
    """HTTP scraper configuration."""

    user_agent: str = "WorldEnergyData-LNGTerminals/1.0"
    request_timeout: float = 30.0
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    retry_delay: float = 2.0


class SourceConfig(BaseModel):
    """Data source configuration."""

    name: str
    enabled: bool = True
    base_url: str = ""
    api_url: str = ""
    rate_limit: float = 1.0
    cache_ttl: int = 86400


class CacheConfig(BaseModel):
    """Cache configuration for data collection."""

    enabled: bool = True
    cache_dir: str = ""
    default_refresh_mode: str = "cache_first"
    max_age_seconds: int = 86400  # 24 hours default


class ProcessingConfig(BaseModel):
    """Processing pipeline configuration."""

    fuzzy_match_threshold: float = 0.85
    coordinate_proximity_km: float = 50.0
    max_pipelines_per_terminal: int = 8


class LNGTerminalsConfig(BaseModel):
    """Main configuration for LNG terminals module."""

    scraper: ScraperConfig = ScraperConfig()
    sources: dict[str, SourceConfig] = {}
    processing: ProcessingConfig = ProcessingConfig()
    cache: CacheConfig = CacheConfig()
    output_formats: list[str] = ["csv", "parquet"]


_config: Optional[LNGTerminalsConfig] = None


def get_cache_dir() -> Path:
    """Return the cache directory, creating it if needed.

    Uses the ``cache.cache_dir`` config value when set, otherwise
    falls back to the module-level ``CACHE_DIR`` constant.
    """
    cfg = get_config()
    if cfg.cache.cache_dir:
        cache_path = Path(cfg.cache.cache_dir)
    else:
        cache_path = CACHE_DIR
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


def get_config() -> LNGTerminalsConfig:
    """Get or load configuration."""
    global _config
    if _config is None:
        _config = _load_config()
    return _config


def _load_config() -> LNGTerminalsConfig:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        import yaml

        with open(CONFIG_PATH) as f:
            data = yaml.safe_load(f) or {}
        return LNGTerminalsConfig(**data)
    logger.warning(f"Config not found at {CONFIG_PATH}, using defaults")
    return LNGTerminalsConfig()
