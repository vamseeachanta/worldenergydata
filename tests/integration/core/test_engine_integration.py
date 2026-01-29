"""
Integration tests for the worldenergydata engine module.

These tests execute the actual engine code with minimal mocking,
only mocking external dependencies like file I/O and network calls.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from tests.integration.test_config_helper import (
    get_complete_test_config,
    get_minimal_test_config,
)
from tests.test_markers import integration, smoke
from worldenergydata.engine import engine


@integration
class TestEngineIntegration:
    """Integration tests for engine with real code execution."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test environment with temporary files."""
        self.temp_dir = tmp_path
        self.test_yml_file = self.temp_dir / "test_config.yml"

        # Use the complete test configuration
        self.test_cfg = get_complete_test_config(tmp_path)

        # Create test YAML file
        with open(self.test_yml_file, "w") as f:
            yaml.dump(self.test_cfg, f)

        # Patch app_manager.save_cfg to avoid AttributeError
        self.patcher = patch("worldenergydata.engine.app_manager.save_cfg")
        mock_save = self.patcher.start()
        mock_save.return_value = None

    def teardown_method(self):
        """Clean up patches."""
        if hasattr(self, "patcher"):
            self.patcher.stop()

    @patch("worldenergydata.engine.bsee")
    def test_engine_bsee_real_execution(self, mock_bsee_class):
        """Test engine with BSEE basename - real execution path."""
        # Mock only the final router to avoid complex dependencies
        mock_instance = MagicMock()
        mock_bsee_class.return_value = mock_instance
        mock_instance.router.return_value = self.test_cfg

        # Execute engine with real configuration processing
        result = engine(cfg=self.test_cfg, config_flag=False)

        # Verify execution
        assert result is not None
        assert result["basename"] == "bsee"
        mock_instance.router.assert_called_once()

    @patch("worldenergydata.engine.zip")
    def test_engine_zip_download_real_execution(self, mock_zip_class):
        """Test engine with zip download - real execution."""
        cfg = self.test_cfg.copy()
        cfg["basename"] = "dwnld_from_zipurl"
        mock_instance = MagicMock()
        mock_zip_class.return_value = mock_instance
        mock_instance.router.return_value = cfg

        result = engine(cfg=cfg, config_flag=False)

        assert result is not None
        assert result["basename"] == "dwnld_from_zipurl"

    @pytest.mark.skip(
        reason="custom_router module does not exist; engine has no bsee_custom handler"
    )
    def test_engine_custom_router_real_execution(self):
        """Test engine with custom router - real execution."""
        pass

    def test_engine_invalid_basename_raises_exception(self):
        """Test that invalid basename raises proper exception."""
        cfg = self.test_cfg.copy()
        cfg["basename"] = "invalid_module"

        with pytest.raises(Exception) as exc_info:
            engine(cfg=cfg, config_flag=False)

        assert "Analysis for basename: invalid_module not found" in str(exc_info.value)

    def test_engine_missing_basename_raises_error(self):
        """Test that missing basename raises ValueError."""
        cfg = {"data": "test"}  # No basename

        with pytest.raises(ValueError) as exc_info:
            engine(cfg=cfg, config_flag=False)

        assert "basename not found" in str(exc_info.value)

    @patch("worldenergydata.engine.FileManagement")
    @patch("worldenergydata.engine.ConfigureApplicationInputs.configure")
    @patch("worldenergydata.engine.ConfigureApplicationInputs.configure_result_folder")
    @patch("worldenergydata.engine.bsee")
    def test_engine_with_config_flag_true(
        self, mock_bsee_class, mock_result_folder, mock_configure, mock_fm
    ):
        """Test engine with config_flag=True for full configuration."""
        # Setup mocks for configuration only
        mock_configure.return_value = self.test_cfg
        mock_result_folder.return_value = ({}, self.test_cfg)
        mock_fm_instance = MagicMock()
        mock_fm.return_value = mock_fm_instance
        mock_fm_instance.router.return_value = self.test_cfg

        mock_instance = MagicMock()
        mock_bsee_class.return_value = mock_instance
        mock_instance.router.return_value = self.test_cfg

        result = engine(cfg=self.test_cfg, config_flag=True)

        assert result is not None
        mock_configure.assert_called_once()
        mock_result_folder.assert_called_once()

    @patch("worldenergydata.engine.app_manager")
    @patch("worldenergydata.engine.wwyaml")
    @patch("worldenergydata.engine.bsee")
    def test_engine_with_yaml_input_file(
        self, mock_bsee_class, mock_wwyaml, mock_app_mgr
    ):
        """Test engine loading configuration from YAML file."""
        # Setup app_manager mock
        mock_app_mgr.validate_arguments_run_methods.return_value = (
            str(self.test_yml_file),
            {},
        )
        mock_app_mgr.save_cfg.return_value = None

        # Setup YAML mock (patch the instance, not the class)
        mock_wwyaml.ymlInput.return_value = self.test_cfg

        # Setup BSEE mock
        mock_bsee_instance = MagicMock()
        mock_bsee_class.return_value = mock_bsee_instance
        mock_bsee_instance.router.return_value = self.test_cfg

        result = engine(inputfile=str(self.test_yml_file), config_flag=False)

        assert result is not None
        assert result["basename"] == "bsee"
        mock_wwyaml.ymlInput.assert_called_once()


@integration
class TestEngineDataFlow:
    """Test data flow through the engine."""

    @pytest.fixture
    def sample_data_cfg(self, tmp_path):
        """Create configuration with sample data."""
        # Get complete configuration
        config = get_complete_test_config(tmp_path)

        # Add sample data
        config["data"].update(
            {
                "well_data": [
                    {"api": "123456789012", "name": "WELL-1"},
                    {"api": "234567890123", "name": "WELL-2"},
                ],
                "production_data": [
                    {"api": "123456789012", "production": 1000},
                    {"api": "234567890123", "production": 2000},
                ],
            }
        )

        return config

    @patch("worldenergydata.engine.bsee")
    def test_data_flow_through_engine(self, mock_bsee_class, sample_data_cfg):
        """Test that data flows correctly through engine."""
        mock_instance = MagicMock()
        mock_bsee_class.return_value = mock_instance
        mock_instance.router.return_value = sample_data_cfg

        # Patch save_cfg for this test
        with patch("worldenergydata.engine.app_manager.save_cfg"):
            result = engine(cfg=sample_data_cfg, config_flag=False)

        assert result is not None
        assert "data" in result
        assert "well_data" in result["data"]
        assert len(result["data"]["well_data"]) == 2

    @patch("worldenergydata.engine.logger")
    @patch("worldenergydata.engine.bsee")
    def test_engine_logging_integration(
        self, mock_bsee_class, mock_logger, sample_data_cfg
    ):
        """Test that logging works correctly in engine."""
        mock_instance = MagicMock()
        mock_bsee_class.return_value = mock_instance
        mock_instance.router.return_value = sample_data_cfg

        # Patch save_cfg for this test
        with patch("worldenergydata.engine.app_manager.save_cfg"):
            engine(cfg=sample_data_cfg, config_flag=False)

        # Verify logging calls
        assert mock_logger.info.call_count >= 2
        mock_logger.info.assert_any_call("bsee, application ... START")
        mock_logger.info.assert_any_call("bsee, application ... END")


@integration
@smoke
class TestEngineSmoke:
    """Smoke tests for engine integration."""

    def test_engine_imports_work(self):
        """Test that all engine imports work."""
        from worldenergydata import engine as eng_module

        # Verify global objects are initialized
        assert eng_module.app_manager is not None
        assert eng_module.save_data is not None
        assert eng_module.wwyaml is not None
        assert eng_module.library_name == "worldenergydata"

    def test_engine_function_callable(self):
        """Test that engine function is callable."""
        from worldenergydata.engine import engine

        assert callable(engine)

    @patch("worldenergydata.engine.bsee")
    def test_minimal_engine_execution(self, mock_bsee_class, tmp_path):
        """Test minimal engine execution."""
        # Use minimal test configuration
        minimal_cfg = get_minimal_test_config(tmp_path)

        mock_instance = MagicMock()
        mock_bsee_class.return_value = mock_instance
        mock_instance.router.return_value = minimal_cfg

        # Patch save_cfg for this test
        with patch("worldenergydata.engine.app_manager.save_cfg"):
            result = engine(cfg=minimal_cfg, config_flag=False)

        assert result is not None
        assert result["basename"] == "bsee"
