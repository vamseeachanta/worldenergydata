"""
Additional unit tests for engine.py to improve code coverage.
Focus on uncovered paths and edge cases.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from worldenergydata.engine import engine


class TestEngineUncoveredPaths:
    """Tests for uncovered code paths in engine.py"""

    @patch("worldenergydata.engine.app_manager")
    @patch("worldenergydata.engine.wwyaml")
    def test_engine_with_valid_inputfile_path(self, mock_wwyaml, mock_app_manager):
        """Test engine successfully loads configuration from file (covers lines 32-36, 40-43)."""
        # Setup
        test_cfg = {"basename": "bsee", "data": "test"}

        # Mock file validation and loading
        mock_app_manager.validate_arguments_run_methods.return_value = (
            "test.yml",
            {"extra": "param"},
        )
        mock_wwyaml.ymlInput.return_value = test_cfg
        mock_app_manager.save_cfg.return_value = None

        with patch("worldenergydata.engine.bsee") as mock_bsee:
            mock_bsee_instance = Mock()
            mock_bsee.return_value = mock_bsee_instance
            mock_bsee_instance.router.return_value = test_cfg

            # Execute
            result = engine(inputfile="test.yml", config_flag=False)

            # Verify
            assert result == test_cfg
            mock_app_manager.validate_arguments_run_methods.assert_called_once_with(
                "test.yml"
            )
            mock_wwyaml.ymlInput.assert_called_once_with("test.yml", updateYml=None)

    @patch("worldenergydata.engine.app_manager")
    @patch("worldenergydata.engine.FileManagement")
    def test_engine_with_config_flag_true(self, mock_file_mgmt, mock_app_manager):
        """Test engine with config_flag=True (covers lines 46-49)."""
        # Setup
        cfg = {"basename": "bsee", "data": "test"}
        cfg_base = {"processed": "config", "basename": "bsee"}

        # Mock configuration processing
        mock_app_manager.configure.return_value = cfg_base
        mock_app_manager.configure_result_folder.return_value = ({}, cfg_base)
        mock_app_manager.save_cfg.return_value = None

        # Mock file management
        mock_fm_instance = Mock()
        mock_file_mgmt.return_value = mock_fm_instance
        mock_fm_instance.router.return_value = cfg_base

        with patch("worldenergydata.engine.bsee") as mock_bsee:
            mock_bsee_instance = Mock()
            mock_bsee.return_value = mock_bsee_instance
            mock_bsee_instance.router.return_value = cfg_base

            # Execute
            result = engine(cfg=cfg, config_flag=True)

            # Verify
            assert result == cfg_base
            mock_app_manager.configure.assert_called_once_with(
                cfg, "worldenergydata", "bsee", {}
            )
            mock_file_mgmt.assert_called_once()

    @pytest.mark.skip(
        reason="CustomRouter does not exist in engine module - bsee_custom basename not supported"
    )
    def test_engine_with_custom_router(self):
        """Test engine routes to CustomRouter for bsee_custom basename."""
        pass

    @patch("worldenergydata.engine.app_manager")
    @patch("worldenergydata.engine.zip")
    def test_engine_with_zip_basename(self, mock_zip, mock_app_manager):
        """Test engine routes to zip module for dwnld_from_zipurl basename."""
        # Setup
        cfg = {"basename": "dwnld_from_zipurl", "data": "test"}

        mock_app_manager.save_cfg.return_value = None

        # Mock zip module
        mock_zip_instance = Mock()
        mock_zip.return_value = mock_zip_instance
        mock_zip_instance.router.return_value = cfg

        # Execute
        result = engine(cfg=cfg, config_flag=False)

        # Verify
        assert result == cfg
        mock_zip.assert_called_once()
        mock_zip_instance.router.assert_called_once_with(cfg)

    @patch("worldenergydata.engine.app_manager")
    @patch("worldenergydata.engine.wwyaml")
    def test_engine_with_empty_cfg_argv_dict(self, mock_wwyaml, mock_app_manager):
        """Test engine handles empty cfg_argv_dict from validate_arguments."""
        # Setup
        test_cfg = {"basename": "bsee"}

        # Return empty dict for cfg_argv_dict
        mock_app_manager.validate_arguments_run_methods.return_value = ("test.yml", {})
        mock_wwyaml.ymlInput.return_value = test_cfg
        mock_app_manager.save_cfg.return_value = None

        with patch("worldenergydata.engine.bsee") as mock_bsee:
            mock_bsee_instance = Mock()
            mock_bsee.return_value = mock_bsee_instance
            mock_bsee_instance.router.return_value = test_cfg

            # Execute
            result = engine(inputfile="test.yml", config_flag=False)

            # Verify - engine always passes None as updateYml
            assert result == test_cfg
            mock_wwyaml.ymlInput.assert_called_once_with("test.yml", updateYml=None)

    @patch("worldenergydata.engine.app_manager")
    def test_engine_with_both_inputfile_and_cfg(self, mock_app_manager):
        """Test engine prioritizes cfg over inputfile when both provided."""
        # Setup
        cfg = {"basename": "bsee", "priority": "cfg"}

        mock_app_manager.save_cfg.return_value = None

        with patch("worldenergydata.engine.bsee") as mock_bsee:
            mock_bsee_instance = Mock()
            mock_bsee.return_value = mock_bsee_instance
            mock_bsee_instance.router.return_value = cfg

            # Execute - provide both inputfile and cfg
            result = engine(inputfile="ignored.yml", cfg=cfg, config_flag=False)

            # Verify cfg was used, not inputfile
            assert result == cfg
            assert result["priority"] == "cfg"
            # validate_arguments should not be called when cfg is provided
            mock_app_manager.validate_arguments_run_methods.assert_not_called()


class TestEngineErrorPaths:
    """Tests for error handling in engine.py"""

    @patch("worldenergydata.engine.AttributeDict")
    @patch("worldenergydata.engine.app_manager")
    @patch("worldenergydata.engine.wwyaml")
    def test_engine_yaml_returns_none_error(
        self, mock_wwyaml, mock_app_manager, mock_attr_dict
    ):
        """Test engine raises ValueError when YAML returns None."""
        # Setup
        mock_app_manager.validate_arguments_run_methods.return_value = ("test.yml", {})
        mock_wwyaml.ymlInput.return_value = None  # Simulate YAML load failure
        mock_attr_dict.return_value = None

        # Execute and verify
        with pytest.raises(ValueError, match="cfg is None"):
            engine(inputfile="test.yml")

    @patch("worldenergydata.engine.app_manager")
    def test_engine_missing_basename_error(self, mock_app_manager):
        """Test engine raises ValueError when basename is missing."""
        # Setup
        cfg = {"data": "test"}  # No basename

        # Execute and verify
        with pytest.raises(ValueError, match="basename not found in cfg"):
            engine(cfg=cfg)

    @patch("worldenergydata.engine.app_manager")
    @patch("worldenergydata.engine.bsee")
    def test_engine_router_exception_propagates(self, mock_bsee, mock_app_manager):
        """Test that exceptions from routers propagate correctly."""
        # Setup
        cfg = {"basename": "bsee"}
        mock_app_manager.save_cfg.return_value = None

        # Make router raise an exception
        mock_bsee_instance = Mock()
        mock_bsee.return_value = mock_bsee_instance
        mock_bsee_instance.router.side_effect = RuntimeError("Router failed")

        # Execute and verify exception propagates
        with pytest.raises(RuntimeError, match="Router failed"):
            engine(cfg=cfg, config_flag=False)
