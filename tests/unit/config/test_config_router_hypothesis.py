"""
Property-based tests for ConfigRouter using Hypothesis.

This module uses property-based testing to thoroughly test the configuration
router's behavior with a wide range of inputs.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from worldenergydata.bsee.data.config.config_router import ConfigRouter


# Custom strategies for generating configuration data
@composite
def config_mode_strategy(draw):
    """Generate valid configuration modes."""
    modes = ["legacy", "enhanced", "LEGACY", "ENHANCED", "Legacy", "Enhanced"]
    return draw(st.sampled_from(modes))


@composite
def data_flags_strategy(draw):
    """Generate data flags dictionary."""
    return {
        "refresh": draw(st.booleans()),
        "well": draw(st.booleans()),
        "war": draw(st.booleans()),
        "production": draw(st.booleans()),
        "apm": draw(st.booleans()),
    }


@composite
def source_config_strategy(draw):
    """Generate source configuration."""
    return {
        "url": draw(st.text(min_size=1, max_size=200)),
        "update_frequency": draw(
            st.sampled_from(["daily", "weekly", "monthly", "bi_monthly"])
        ),
    }


@composite
def processing_config_strategy(draw):
    """Generate processing configuration."""
    return {
        "in_memory": draw(st.booleans()),
        "save_zip": draw(st.booleans()),
        "chunk_size": draw(st.integers(min_value=1024, max_value=65536)),
        "timeout": draw(st.integers(min_value=10, max_value=3600)),
    }


@composite
def full_config_strategy(draw):
    """Generate a complete configuration dictionary."""
    config = {}

    # Meta section
    if draw(st.booleans()):
        config["meta"] = {
            "library": draw(st.text(min_size=1, max_size=50)),
            "basename": draw(st.text(min_size=1, max_size=50)),
            "mode": draw(config_mode_strategy()),
        }

    # Data section
    if draw(st.booleans()):
        config["data"] = draw(data_flags_strategy())

    # Sources section
    if draw(st.booleans()):
        config["sources"] = {}
        for source in ["well", "war", "production"]:
            if draw(st.booleans()):
                config["sources"][source] = draw(source_config_strategy())

    # Processing section
    if draw(st.booleans()):
        config["processing"] = draw(processing_config_strategy())

    # Parameters section (for legacy mode)
    if draw(st.booleans()):
        config["parameters"] = {
            "filepath": {
                "apm_zip": draw(st.text(min_size=1, max_size=200)),
                "directional_zip": draw(st.text(min_size=1, max_size=200)),
                "production_zip": draw(st.text(min_size=1, max_size=200)),
            }
        }

    # Default section
    if draw(st.booleans()):
        config["default"] = {
            "log_level": draw(st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR"]))
        }

    return config


class TestConfigRouterProperties:
    """Property-based tests for ConfigRouter."""

    @given(config=full_config_strategy())
    @settings(max_examples=100)
    def test_is_enhanced_mode_consistency(self, config):
        """Test that enhanced mode detection is consistent."""
        router = ConfigRouter()

        # First call should determine the mode
        result1 = router.is_enhanced_mode(config)

        # Subsequent calls should return the same result
        result2 = router.is_enhanced_mode(config)

        assert result1 == result2
        assert router.enhanced_mode == result1

    @given(mode=config_mode_strategy())
    def test_mode_case_insensitive(self, mode):
        """Test that mode detection is case-insensitive."""
        router = ConfigRouter()
        config = {"meta": {"mode": mode}}

        is_enhanced = router.is_enhanced_mode(config)

        # Should be True only if mode is 'enhanced' (case-insensitive)
        expected = mode.lower() == "enhanced"
        assert is_enhanced == expected

    @given(config=full_config_strategy())
    def test_validate_config_never_crashes(self, config):
        """Test that validate_config handles any input without crashing."""
        router = ConfigRouter()

        # Set mode first
        router.is_enhanced_mode(config)

        # Should not raise any exceptions
        try:
            result = router.validate_config(config)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"validate_config crashed with: {e}")

    @given(base_cfg=full_config_strategy(), enhanced_cfg=full_config_strategy())
    def test_merge_configs_preserves_structure(self, base_cfg, enhanced_cfg):
        """Test that merge_configs preserves dictionary structure."""
        router = ConfigRouter()

        merged = router.merge_configs(base_cfg, enhanced_cfg)

        # Result should be a dictionary
        assert isinstance(merged, dict)

        # All keys from enhanced_cfg should be in merged
        def check_keys(source, target, path=""):
            for key in source:
                assert key in target, f"Key {path}.{key} missing"
                if isinstance(source[key], dict) and isinstance(target.get(key), dict):
                    check_keys(source[key], target[key], f"{path}.{key}")

        check_keys(enhanced_cfg, merged)

    @given(config=full_config_strategy())
    def test_get_system_info_structure(self, config):
        """Test that get_system_info returns expected structure."""
        router = ConfigRouter()

        info = router.get_system_info(config)

        # Check required keys
        assert "mode" in info
        assert "config_source" in info
        assert "features" in info
        assert "data_sources" in info

        # Check nested structure
        assert isinstance(info["features"], dict)
        assert isinstance(info["data_sources"], dict)

        # Check mode is either 'enhanced' or 'legacy'
        assert info["mode"] in ["enhanced", "legacy"]

    @given(config_path=st.text(min_size=1, max_size=200))
    def test_load_enhanced_config_with_invalid_path(self, config_path):
        """Test loading config with various invalid paths."""
        router = ConfigRouter()

        # Assume the path doesn't exist
        assume(not Path(config_path).exists())

        with patch("pathlib.Path.exists", return_value=False):
            result = router.load_enhanced_config(config_path)

        # Should return default config without crashing
        assert isinstance(result, dict)
        assert result == router.get_default_enhanced_config()

    @given(
        yaml_content=st.text(
            alphabet=st.characters(
                blacklist_categories=("Cc", "Cs"), blacklist_characters="\x00"
            )
        )
    )
    def test_load_enhanced_config_with_invalid_yaml(self, yaml_content):
        """Test loading config with invalid YAML content."""
        router = ConfigRouter()

        # Create a temporary file with the content
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as f:
            try:
                f.write(yaml_content)
                temp_path = f.name
            except (UnicodeEncodeError, UnicodeDecodeError):
                # Skip if content can't be written
                Path(f.name).unlink(missing_ok=True)
                return

        try:
            result = router.load_enhanced_config(temp_path)
            # Should always return a dict (either parsed or default)
            assert isinstance(result, dict)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @given(st.data())
    def test_enhanced_mode_data_flags(self, data):
        """Test that enhanced mode handles data flags correctly."""
        router = ConfigRouter()

        # Generate a config with enhanced mode
        config = {
            "meta": {"mode": "enhanced"},
            "data": data.draw(data_flags_strategy()),
        }

        is_enhanced = router.is_enhanced_mode(config)
        is_valid = router.validate_config(config)

        assert is_enhanced is True

        # Enhanced mode should be valid if at least one data flag is set
        data_flags = ["well", "war", "production", "apm"]
        has_data_flag = any(config["data"].get(flag) for flag in data_flags)

        if has_data_flag:
            assert is_valid is True
        else:
            assert is_valid is False

    @given(st.data())
    def test_legacy_mode_requirements(self, data):
        """Test that legacy mode enforces its requirements."""
        router = ConfigRouter()

        # Generate a config with legacy mode
        config = {
            "meta": {"mode": "legacy"},
            "data": data.draw(data_flags_strategy()),
            "parameters": (
                {
                    "filepath": {
                        "apm_zip": data.draw(st.text(min_size=1)),
                        "production_zip": data.draw(st.text(min_size=1)),
                    }
                }
                if data.draw(st.booleans())
                else {}
            ),
        }

        is_enhanced = router.is_enhanced_mode(config)
        is_valid = router.validate_config(config)

        assert is_enhanced is False

        # Legacy mode requires refresh flag and file paths
        has_refresh = config.get("data", {}).get("refresh", False)
        has_filepath = bool(config.get("parameters", {}).get("filepath"))
        data_flags = ["well", "war", "production", "apm"]
        has_data_flag = any(config["data"].get(flag) for flag in data_flags)

        # Valid only if all requirements are met
        expected_valid = has_refresh and has_filepath and has_data_flag
        assert is_valid == expected_valid

    @given(
        mode=config_mode_strategy(),
        chunk_size=st.integers(min_value=1, max_value=100000),
        timeout=st.integers(min_value=1, max_value=10000),
    )
    def test_default_config_overrides(self, mode, chunk_size, timeout):
        """Test that specific values override defaults correctly."""
        router = ConfigRouter()

        base_config = router.get_default_enhanced_config()
        override_config = {
            "meta": {"mode": mode},
            "processing": {"chunk_size": chunk_size, "timeout": timeout},
        }

        merged = router.merge_configs(base_config, override_config)

        # Check overrides are applied
        assert merged["meta"]["mode"] == mode
        assert merged["processing"]["chunk_size"] == chunk_size
        assert merged["processing"]["timeout"] == timeout

        # Check other defaults are preserved
        assert "data" in merged
        assert "sources" in merged

    @given(
        st.lists(
            st.sampled_from(["well", "war", "production", "apm"]),
            min_size=0,
            max_size=4,
        )
    )
    def test_data_flags_combinations(self, flags):
        """Test various combinations of data flags."""
        router = ConfigRouter()

        config = {"meta": {"mode": "enhanced"}, "data": {flag: True for flag in flags}}

        # Add other flags as False
        for flag in ["well", "war", "production", "apm"]:
            if flag not in config["data"]:
                config["data"][flag] = False

        router.is_enhanced_mode(config)
        is_valid = router.validate_config(config)

        # Should be valid if at least one flag is set
        assert is_valid == (len(flags) > 0)

    @given(
        st.dictionaries(
            st.text(),
            st.one_of(
                st.text(),
                st.dictionaries(st.text(), st.text()),
                st.booleans(),
                st.integers(),
                st.none(),
            ),
        )
    )
    @example({})  # Always test empty dict
    @example({"meta": {"mode": "enhanced"}})  # Test minimal enhanced
    @example({"meta": {"mode": "legacy"}})  # Test minimal legacy
    def test_config_without_required_sections(self, partial_config):
        """Test handling of configs missing required sections."""
        router = ConfigRouter()

        # Should handle gracefully without crashing
        try:
            is_enhanced = router.is_enhanced_mode(partial_config)
            is_valid = router.validate_config(partial_config)
            info = router.get_system_info(partial_config)

            # Basic assertions
            assert isinstance(is_enhanced, bool)
            assert isinstance(is_valid, bool)
            assert isinstance(info, dict)
        except AttributeError:
            # This is acceptable if config structure is invalid
            # (e.g., 'meta' is not a dict)
            pass

    @given(st.integers(min_value=0, max_value=10))
    def test_repeated_operations_consistency(self, num_operations):
        """Test that repeated operations on the same config are consistent."""
        router = ConfigRouter()
        config = {
            "meta": {"mode": "enhanced"},
            "data": {"well": True, "production": True},
        }

        results = []
        for _ in range(num_operations):
            is_enhanced = router.is_enhanced_mode(config)
            is_valid = router.validate_config(config)
            info = router.get_system_info(config)
            results.append((is_enhanced, is_valid, info["mode"]))

        # All results should be the same
        if results:
            first = results[0]
            for result in results:
                assert result == first


class TestConfigRouterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_config(self):
        """Test with completely empty configuration."""
        router = ConfigRouter()
        config = {}

        is_enhanced = router.is_enhanced_mode(config)
        is_valid = router.validate_config(config)
        info = router.get_system_info(config)

        # Should default to legacy mode
        assert is_enhanced is False
        assert is_valid is False  # No data flags set
        assert info["mode"] == "legacy"

    def test_null_values_in_config(self):
        """Test with None/null values in configuration."""
        router = ConfigRouter()
        config = {
            "meta": {"mode": None},
            "data": {"well": None, "war": None},
            "processing": None,
        }

        # Should handle None values gracefully
        is_enhanced = router.is_enhanced_mode(config)
        is_valid = router.validate_config(config)

        assert is_enhanced is False  # None != 'enhanced'
        assert is_valid is False

    def test_deeply_nested_merge(self):
        """Test merging deeply nested configurations."""
        router = ConfigRouter()

        base = {"level1": {"level2": {"level3": {"value": "base"}}}}

        override = {
            "level1": {
                "level2": {"level3": {"value": "override", "new_value": "added"}}
            }
        }

        merged = router.merge_configs(base, override)

        assert merged["level1"]["level2"]["level3"]["value"] == "override"
        assert merged["level1"]["level2"]["level3"]["new_value"] == "added"

    def test_special_characters_in_paths(self):
        """Test handling special characters in file paths."""
        router = ConfigRouter()

        special_paths = [
            "path with spaces/config.yml",
            "path\\with\\backslashes.yml",
            "path/with/../../traversal.yml",
            "path/with/unicode/文件.yml",
            "path/with/.hidden/file.yml",
        ]

        for path in special_paths:
            with patch("pathlib.Path.exists", return_value=False):
                result = router.load_enhanced_config(path)
                assert isinstance(result, dict)

    def test_circular_reference_prevention(self):
        """Test that circular references don't cause infinite loops."""
        router = ConfigRouter()

        # Create a config with potential circular reference
        config = {"data": {}}
        config["data"]["circular"] = config  # Circular reference

        # Should handle without infinite loop
        try:
            router.is_enhanced_mode(config)
            router.validate_config(config)
        except RecursionError:
            pytest.fail("Circular reference caused infinite recursion")

    def test_log_config_summary_with_mock(self):
        """Test logging functionality with mocked logger."""
        router = ConfigRouter()
        config = {
            "meta": {"mode": "enhanced"},
            "data": {"well": True, "war": True, "production": False},
        }

        with patch(
            "worldenergydata.bsee.data.config.config_router.logger"
        ) as mock_logger:
            router.log_config_summary(config)

            # Verify logging was called
            assert mock_logger.info.called

            # Check that summary contains expected information
            calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("ENHANCED" in str(call) for call in calls)
            assert any("Features:" in str(call) for call in calls)
