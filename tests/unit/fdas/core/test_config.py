"""Tests for FDAS configuration management module."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.fdas.core.config import (
    AssumptionsManager,
    ConfigurationError,
    DEFAULT_ASSUMPTIONS,
    PriceDeckManager,
    classify_dev_system_by_depth,
    load_configuration,
    normalize_dev_system,
)
from worldenergydata.common.exceptions import ConfigError


# ---------------------------------------------------------------------------
# ConfigurationError
# ---------------------------------------------------------------------------

class TestConfigurationError:
    def test_inherits_from_config_error(self):
        err = ConfigurationError("bad config")
        assert isinstance(err, ConfigError)

    def test_default_code(self):
        err = ConfigurationError("msg")
        assert err.code == "FDAS_CONFIG_ERROR"


# ---------------------------------------------------------------------------
# normalize_dev_system
# ---------------------------------------------------------------------------

class TestNormalizeDevSystem:
    def test_none(self):
        assert normalize_dev_system(None) == "unknown"

    def test_nan(self):
        assert normalize_dev_system(float("nan")) == "unknown"

    def test_dry_tree(self):
        assert normalize_dev_system("DRY TREE") == "dry"

    def test_dry_lower(self):
        assert normalize_dev_system("dry") == "dry"

    def test_subsea_15(self):
        assert normalize_dev_system("Subsea 15") == "subsea15"

    def test_subsea_bare(self):
        assert normalize_dev_system("subsea") == "subsea15"

    def test_subsea_20(self):
        assert normalize_dev_system("Subsea-20") == "subsea20"

    def test_ultra(self):
        assert normalize_dev_system("ultra deep") == "subsea20"

    def test_unknown_passthrough(self):
        assert normalize_dev_system("something_else") == "somethingelse"

    def test_whitespace_handling(self):
        assert normalize_dev_system("  Subsea 15  ") == "subsea15"


# ---------------------------------------------------------------------------
# classify_dev_system_by_depth
# ---------------------------------------------------------------------------

class TestClassifyDevSystemByDepth:
    def test_none_depth(self):
        assert classify_dev_system_by_depth(None) == "unknown"

    def test_nan_depth(self):
        assert classify_dev_system_by_depth(float("nan")) == "unknown"

    def test_shallow_dry(self):
        assert classify_dev_system_by_depth(400) == "dry"

    def test_boundary_500_is_subsea15(self):
        assert classify_dev_system_by_depth(500) == "subsea15"

    def test_mid_depth_subsea15(self):
        assert classify_dev_system_by_depth(3000) == "subsea15"

    def test_boundary_6000_is_subsea20(self):
        assert classify_dev_system_by_depth(6000) == "subsea20"

    def test_deep_subsea20(self):
        assert classify_dev_system_by_depth(8000) == "subsea20"

    def test_string_depth_cast_to_float(self):
        assert classify_dev_system_by_depth(400.0) == "dry"


# ---------------------------------------------------------------------------
# AssumptionsManager
# ---------------------------------------------------------------------------

class TestAssumptionsManagerInit:
    def test_default_assumptions(self):
        mgr = AssumptionsManager()
        assert "DEV_SYSTEM" in mgr.assumptions.columns
        systems = list(mgr.assumptions["DEV_SYSTEM"])
        assert "dry" in systems
        assert "subsea15" in systems
        assert "subsea20" in systems
        assert "default" in systems

    def test_custom_dataframe(self):
        df = pd.DataFrame({
            "DEV_SYSTEM": ["DRY TREE", "Subsea 15"],
            "HOST_CAPEX_MM": [0.0, 300.0],
        })
        mgr = AssumptionsManager(df)
        # Names should be normalized
        systems = list(mgr.assumptions["DEV_SYSTEM"])
        assert "dry" in systems
        assert "subsea15" in systems


class TestAssumptionsManagerFromDict:
    def test_from_dict(self):
        d = {
            "DEV_SYSTEM": ["dry", "subsea15"],
            "HOST_CAPEX_MM": [0.0, 300.0],
        }
        mgr = AssumptionsManager.from_dict(d)
        assert len(mgr.assumptions) == 2

    def test_from_default_assumptions_dict(self):
        mgr = AssumptionsManager.from_dict(DEFAULT_ASSUMPTIONS)
        assert len(mgr.assumptions) == 4


class TestAssumptionsManagerGet:
    def test_exact_match(self):
        mgr = AssumptionsManager()
        val = mgr.get("subsea15", "HOST_CAPEX_MM")
        assert val == 300.0

    def test_dry_tree_capex(self):
        mgr = AssumptionsManager()
        val = mgr.get("dry", "HOST_CAPEX_MM")
        assert val == 0.0

    def test_subsea20_surf(self):
        mgr = AssumptionsManager()
        val = mgr.get("subsea20", "SURF_PER_WELL_MM")
        assert val == 12.0

    def test_fallback_to_default_system(self):
        mgr = AssumptionsManager()
        val = mgr.get("unknown_system", "HOST_CAPEX_MM")
        # Should fall back to "default" system
        assert val == 300.0  # default system HOST_CAPEX_MM

    def test_missing_parameter_returns_default(self):
        mgr = AssumptionsManager()
        val = mgr.get("dry", "NONEXISTENT_PARAM", default=99.9)
        assert val == 99.9

    def test_case_insensitive_parameter(self):
        mgr = AssumptionsManager()
        val = mgr.get("subsea15", "host_capex_mm")
        assert val == 300.0

    def test_normalized_system_name(self):
        mgr = AssumptionsManager()
        val = mgr.get("Subsea 15", "HOST_CAPEX_MM")
        assert val == 300.0


class TestAssumptionsManagerGetAllForSystem:
    def test_known_system(self):
        mgr = AssumptionsManager()
        params = mgr.get_all_for_system("dry")
        assert "HOST_CAPEX_MM" in params
        assert params["HOST_CAPEX_MM"] == 0.0
        assert "ROYALTY_RATE" in params

    def test_unknown_system_fallback(self):
        mgr = AssumptionsManager()
        params = mgr.get_all_for_system("nonexistent")
        # Falls back to "default"
        assert len(params) > 0

    def test_completely_missing_returns_empty(self):
        df = pd.DataFrame({
            "DEV_SYSTEM": ["dry"],
            "HOST_CAPEX_MM": [0.0],
        })
        mgr = AssumptionsManager(df)
        params = mgr.get_all_for_system("subsea20")
        # No "default" system either
        assert params == {}


class TestAssumptionsManagerValidate:
    def test_valid_defaults(self):
        mgr = AssumptionsManager()
        result = mgr.validate()
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_systems_found(self):
        mgr = AssumptionsManager()
        result = mgr.validate()
        assert "dry" in result["systems_found"]
        assert "subsea15" in result["systems_found"]

    def test_missing_systems_warning(self):
        df = pd.DataFrame({
            "DEV_SYSTEM": ["dry"],
            "HOST_CAPEX_MM": [0.0],
            "SURF_PER_WELL_MM": [0.0],
            "ROYALTY_RATE": [0.125],
            "VARIABLE_OPEX_$/BBL": [8.0],
            "DISCOUNT_RATE_ANNUAL": [0.10],
        })
        mgr = AssumptionsManager(df)
        result = mgr.validate()
        assert len(result["warnings"]) > 0
        assert any("Missing development systems" in w for w in result["warnings"])

    def test_missing_params_error(self):
        df = pd.DataFrame({
            "DEV_SYSTEM": ["dry"],
            "HOST_CAPEX_MM": [0.0],
        })
        mgr = AssumptionsManager(df)
        result = mgr.validate()
        assert result["valid"] is False
        assert any("Missing required parameters" in e for e in result["errors"])

    def test_negative_values_error(self):
        df = pd.DataFrame({
            "DEV_SYSTEM": ["dry", "subsea15", "subsea20", "default"],
            "HOST_CAPEX_MM": [-100.0, 300.0, 450.0, 300.0],
            "SURF_PER_WELL_MM": [0.0, 8.0, 12.0, 8.0],
            "ROYALTY_RATE": [0.125, 0.188, 0.188, 0.188],
            "VARIABLE_OPEX_$/BBL": [8.0, 12.0, 15.0, 12.0],
            "DISCOUNT_RATE_ANNUAL": [0.10, 0.10, 0.10, 0.10],
        })
        mgr = AssumptionsManager(df)
        result = mgr.validate()
        assert result["valid"] is False
        assert any("Negative values" in e for e in result["errors"])

    def test_parameters_found_list(self):
        mgr = AssumptionsManager()
        result = mgr.validate()
        assert "HOST_CAPEX_MM" in result["parameters_found"]
        assert "DEV_SYSTEM" not in result["parameters_found"]


# ---------------------------------------------------------------------------
# PriceDeckManager
# ---------------------------------------------------------------------------

class TestPriceDeckManagerInit:
    def test_none_wti_df(self):
        mgr = PriceDeckManager()
        assert mgr.wti_df is None


class TestPriceDeckManagerGetPrice:
    def test_no_data_returns_default(self):
        mgr = PriceDeckManager()
        assert mgr.get_price("2024-01") == 75.0

    def test_no_data_custom_default(self):
        mgr = PriceDeckManager()
        assert mgr.get_price("2024-01", default=80.0) == 80.0

    def test_exact_match(self):
        df = pd.DataFrame({
            "year_month": ["2024-01", "2024-02", "2024-03"],
            "wti_price": [72.5, 78.0, 80.5],
        })
        mgr = PriceDeckManager(df)
        assert mgr.get_price("2024-02") == 78.0

    def test_no_match_returns_default(self):
        df = pd.DataFrame({
            "year_month": ["2024-01"],
            "wti_price": [72.5],
        })
        mgr = PriceDeckManager(df)
        assert mgr.get_price("2025-06") == 75.0

    def test_nan_price_returns_default(self):
        df = pd.DataFrame({
            "year_month": ["2024-01"],
            "wti_price": [float("nan")],
        })
        mgr = PriceDeckManager(df)
        assert mgr.get_price("2024-01") == 75.0


# ---------------------------------------------------------------------------
# load_configuration
# ---------------------------------------------------------------------------

class TestLoadConfiguration:
    def test_missing_dir_raises(self, tmp_path):
        with pytest.raises(ConfigurationError, match="not found"):
            load_configuration(tmp_path / "nonexistent")

    def test_empty_dir_uses_defaults(self, tmp_path):
        config = load_configuration(tmp_path)
        assert "assumptions_manager" in config
        assert "price_deck_manager" in config
        assert isinstance(config["assumptions_manager"], AssumptionsManager)
        assert isinstance(config["price_deck_manager"], PriceDeckManager)

    def test_default_assumptions_have_all_systems(self, tmp_path):
        config = load_configuration(tmp_path)
        mgr = config["assumptions_manager"]
        systems = list(mgr.assumptions["DEV_SYSTEM"])
        assert "dry" in systems
        assert "subsea15" in systems
