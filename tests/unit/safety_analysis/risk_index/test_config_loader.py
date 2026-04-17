"""Tests for HSE Risk Index config loader."""

import pytest
import yaml

from worldenergydata.safety_analysis.risk_index.config_loader import (
    RiskConfig,
    default_config,
    load_config,
)


class TestDefaultConfig:
    """Default config returns valid values without any file."""

    def test_returns_risk_config(self):
        cfg = default_config()
        assert isinstance(cfg, RiskConfig)

    def test_composite_weights_sum_to_one(self):
        cfg = default_config()
        assert abs(sum(cfg.composite_weights.values()) - 1.0) < 1e-9

    def test_acute_weights_sum_to_one(self):
        cfg = default_config()
        assert abs(sum(cfg.acute_weights.values()) - 1.0) < 1e-9

    def test_default_missing_score(self):
        cfg = default_config()
        assert 1.0 <= cfg.default_missing_score <= 10.0

    def test_water_depth_bands_ordered(self):
        cfg = default_config()
        assert cfg.water_depth_bands["shallow"] < cfg.water_depth_bands["mid"]


class TestLoadConfig:
    """Load config from YAML file."""

    def test_load_from_yaml(self, tmp_path):
        yaml_content = {
            "composite_weights": {"acute": 0.60, "chronic": 0.20, "compliance": 0.20},
            "acute_weights": {
                "fatality_rate": 0.50,
                "injury_rate": 0.30,
                "frequency": 0.20,
            },
            "chronic_weights": {"tri_carcinogen_lbs": 1.0},
            "compliance_weights": {"inc_rate": 1.0},
            "default_missing_score": 4.0,
            "water_depth_bands": {"shallow": 400, "mid": 4000},
        }
        cfg_path = tmp_path / "risk_config.yaml"
        cfg_path.write_text(yaml.dump(yaml_content))

        cfg = load_config(cfg_path)
        assert cfg.composite_weights["acute"] == 0.60
        assert cfg.acute_weights["fatality_rate"] == 0.50
        assert cfg.default_missing_score == 4.0

    def test_partial_yaml_uses_defaults(self, tmp_path):
        yaml_content = {
            "composite_weights": {"acute": 0.70, "chronic": 0.15, "compliance": 0.15}
        }
        cfg_path = tmp_path / "partial.yaml"
        cfg_path.write_text(yaml.dump(yaml_content))

        cfg = load_config(cfg_path)
        assert cfg.composite_weights["acute"] == 0.70
        # Acute weights should still have defaults
        assert "fatality_rate" in cfg.acute_weights

    def test_missing_file_returns_default(self, tmp_path):
        cfg = load_config(tmp_path / "nonexistent.yaml")
        assert isinstance(cfg, RiskConfig)
        assert cfg.composite_weights["acute"] == 0.50  # default

    def test_invalid_yaml_returns_default(self, tmp_path):
        cfg_path = tmp_path / "bad.yaml"
        cfg_path.write_text("{{{{invalid yaml")
        cfg = load_config(cfg_path)
        assert isinstance(cfg, RiskConfig)


class TestRiskConfig:
    """RiskConfig dataclass behavior."""

    def test_immutable_defaults(self):
        cfg1 = default_config()
        cfg2 = default_config()
        cfg1.composite_weights["acute"] = 0.99
        assert cfg2.composite_weights["acute"] == 0.50

    def test_get_water_depth_band(self):
        cfg = default_config()
        assert cfg.get_water_depth_band(200) == "shallow"
        assert cfg.get_water_depth_band(500) == "shallow"
        assert cfg.get_water_depth_band(501) == "mid"
        assert cfg.get_water_depth_band(5000) == "mid"
        assert cfg.get_water_depth_band(5001) == "deep"
        assert cfg.get_water_depth_band(10000) == "deep"
