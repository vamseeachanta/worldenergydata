"""HSE Risk Index Configuration Loader.

Loads scoring weights and parameters from a YAML file,
falling back to sensible defaults when the file is missing or invalid.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Union

import yaml

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "composite_weights": {"acute": 0.50, "chronic": 0.25, "compliance": 0.25},
    "acute_weights": {"fatality_rate": 0.40, "injury_rate": 0.35, "frequency": 0.25},
    "chronic_weights": {"tri_carcinogen_lbs": 1.0},
    "compliance_weights": {"inc_rate": 1.0},
    "default_missing_score": 5.5,
    "normalization_method": "percentile_rank",
    "water_depth_bands": {"shallow": 500, "mid": 5000},
}


@dataclass
class RiskConfig:
    """Container for risk index configuration parameters."""

    composite_weights: Dict[str, float] = field(default_factory=dict)
    acute_weights: Dict[str, float] = field(default_factory=dict)
    chronic_weights: Dict[str, float] = field(default_factory=dict)
    compliance_weights: Dict[str, float] = field(default_factory=dict)
    default_missing_score: float = 5.5
    normalization_method: str = "percentile_rank"
    water_depth_bands: Dict[str, int] = field(default_factory=dict)

    def get_water_depth_band(self, depth_ft: float) -> str:
        """Classify a water depth (feet) into a band name.

        Returns 'shallow', 'mid', or 'deep' based on configured thresholds.
        """
        shallow_limit = self.water_depth_bands.get("shallow", 500)
        mid_limit = self.water_depth_bands.get("mid", 5000)
        if depth_ft <= shallow_limit:
            return "shallow"
        if depth_ft <= mid_limit:
            return "mid"
        return "deep"


def default_config() -> RiskConfig:
    """Return a RiskConfig with default values."""
    defaults = copy.deepcopy(_DEFAULTS)
    return RiskConfig(
        composite_weights=defaults["composite_weights"],
        acute_weights=defaults["acute_weights"],
        chronic_weights=defaults["chronic_weights"],
        compliance_weights=defaults["compliance_weights"],
        default_missing_score=defaults["default_missing_score"],
        normalization_method=defaults["normalization_method"],
        water_depth_bands=defaults["water_depth_bands"],
    )


def load_config(path: Union[str, Path]) -> RiskConfig:
    """Load risk config from a YAML file.

    Falls back to defaults for missing keys or if the file
    cannot be read.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        A populated RiskConfig instance.
    """
    path = Path(path)
    if not path.exists():
        logger.warning("Config file not found: %s — using defaults", path)
        return default_config()

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Failed to parse config: %s — using defaults", path, exc_info=True)
        return default_config()

    if not isinstance(raw, dict):
        return default_config()

    defaults = copy.deepcopy(_DEFAULTS)
    return RiskConfig(
        composite_weights=raw.get("composite_weights", defaults["composite_weights"]),
        acute_weights=raw.get("acute_weights", defaults["acute_weights"]),
        chronic_weights=raw.get("chronic_weights", defaults["chronic_weights"]),
        compliance_weights=raw.get("compliance_weights", defaults["compliance_weights"]),
        default_missing_score=raw.get("default_missing_score", defaults["default_missing_score"]),
        normalization_method=raw.get("normalization_method", defaults["normalization_method"]),
        water_depth_bands=raw.get("water_depth_bands", defaults["water_depth_bands"]),
    )
