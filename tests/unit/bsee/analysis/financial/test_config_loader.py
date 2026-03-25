"""Tests for SMEConfigLoader constants, merge, validation, and accessors."""

import copy

import pytest

from worldenergydata.bsee.analysis.financial.config_loader import SMEConfigLoader


class TestDefaultConfig:
    def test_has_financial_key(self):
        assert "financial" in SMEConfigLoader.DEFAULT_CONFIG

    def test_lease_groups(self):
        groups = SMEConfigLoader.DEFAULT_CONFIG["financial"]["lease_groups"]
        assert "STONES" in groups
        assert "CASCADE_CHINOOK" in groups
        assert isinstance(groups["STONES"], list)

    def test_economic_parameters(self):
        params = SMEConfigLoader.DEFAULT_CONFIG["financial"]["economic_parameters"]
        assert params["oil_price_usd"] == 50.00
        assert params["gas_price_usd_mcf"] == 3.00
        assert params["discount_rate"] == 0.10
        assert params["tax_rate"] == 0.35
        assert params["royalty_rate"] == 0.1875

    def test_drilling_costs(self):
        costs = SMEConfigLoader.DEFAULT_CONFIG["financial"]["drilling_costs"]
        assert costs["rig_rate_usd_per_day"] == 300000
        assert costs["completion_rate_usd_per_day"] == 400000

    def test_output_options(self):
        opts = SMEConfigLoader.DEFAULT_CONFIG["financial"]["output_options"]
        assert opts["include_readme"] is True
        assert opts["decimal_places"] == 2


class TestMergeConfigs:
    def test_simple_merge(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        default = {"a": 1, "b": {"c": 2}}
        custom = {"b": {"c": 3}}
        result = loader._merge_configs(default, custom)
        assert result["a"] == 1
        assert result["b"]["c"] == 3

    def test_deep_merge(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        default = {"a": {"b": {"c": 1, "d": 2}}}
        custom = {"a": {"b": {"c": 99}}}
        result = loader._merge_configs(default, custom)
        assert result["a"]["b"]["c"] == 99
        assert result["a"]["b"]["d"] == 2

    def test_add_new_key(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        default = {"a": 1}
        custom = {"b": 2}
        result = loader._merge_configs(default, custom)
        assert result["a"] == 1
        assert result["b"] == 2

    def test_no_mutation(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        default = {"a": {"b": 1}}
        custom = {"a": {"b": 2}}
        loader._merge_configs(default, custom)
        assert default["a"]["b"] == 1


class TestValidateConfig:
    def _valid_config(self):
        return copy.deepcopy(SMEConfigLoader.DEFAULT_CONFIG)

    def test_valid_default(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        assert loader.validate_config(self._valid_config()) is True

    def test_missing_financial(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        with pytest.raises(ValueError, match="financial"):
            loader.validate_config({})

    def test_missing_lease_groups(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        cfg = {"financial": {"economic_parameters": {}, "drilling_costs": {}}}
        with pytest.raises(ValueError, match="lease_groups"):
            loader.validate_config(cfg)

    def test_missing_economic_parameters(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        cfg = {"financial": {"lease_groups": {}, "drilling_costs": {}}}
        with pytest.raises(ValueError, match="economic_parameters"):
            loader.validate_config(cfg)

    def test_negative_oil_price(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        cfg = self._valid_config()
        cfg["financial"]["economic_parameters"]["oil_price_usd"] = -10
        with pytest.raises(ValueError, match="Oil price"):
            loader.validate_config(cfg)

    def test_negative_gas_price(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        cfg = self._valid_config()
        cfg["financial"]["economic_parameters"]["gas_price_usd_mcf"] = -1
        with pytest.raises(ValueError, match="Gas price"):
            loader.validate_config(cfg)

    def test_discount_rate_out_of_range(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        cfg = self._valid_config()
        cfg["financial"]["economic_parameters"]["discount_rate"] = 1.5
        with pytest.raises(ValueError, match="Discount rate"):
            loader.validate_config(cfg)

    def test_tax_rate_out_of_range(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        cfg = self._valid_config()
        cfg["financial"]["economic_parameters"]["tax_rate"] = -0.1
        with pytest.raises(ValueError, match="Tax rate"):
            loader.validate_config(cfg)

    def test_negative_rig_rate(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        cfg = self._valid_config()
        cfg["financial"]["drilling_costs"]["rig_rate_usd_per_day"] = -100
        with pytest.raises(ValueError, match="Rig rate"):
            loader.validate_config(cfg)


class TestAccessors:
    def test_get_lease_groups(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        cfg = copy.deepcopy(SMEConfigLoader.DEFAULT_CONFIG)
        groups = loader.get_lease_groups(cfg)
        assert "STONES" in groups

    def test_get_economic_parameters(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        cfg = copy.deepcopy(SMEConfigLoader.DEFAULT_CONFIG)
        params = loader.get_economic_parameters(cfg)
        assert "oil_price_usd" in params

    def test_get_drilling_costs(self):
        loader = SMEConfigLoader(base_path="/tmp/test")
        cfg = copy.deepcopy(SMEConfigLoader.DEFAULT_CONFIG)
        costs = loader.get_drilling_costs(cfg)
        assert "rig_rate_usd_per_day" in costs


class TestSaveConfig:
    def test_save_valid_config(self, tmp_path):
        loader = SMEConfigLoader(base_path="/tmp/test")
        cfg = copy.deepcopy(SMEConfigLoader.DEFAULT_CONFIG)
        outfile = tmp_path / "subdir" / "config.yaml"
        loader.save_config(cfg, str(outfile))
        assert outfile.exists()

    def test_save_invalid_config_raises(self, tmp_path):
        loader = SMEConfigLoader(base_path="/tmp/test")
        outfile = tmp_path / "config.yaml"
        with pytest.raises(ValueError):
            loader.save_config({}, str(outfile))
