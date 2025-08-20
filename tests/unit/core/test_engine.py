"""
Unit tests for the worldenergydata engine module.

Tests the core engine functionality including configuration handling,
routing, and application execution.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from worldenergydata.engine import engine
from tests.test_markers import unit, smoke


@unit
class TestEngine:
    """Unit tests for the engine function."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.mock_cfg = {
            'basename': 'bsee',
            'meta': {
                'project': 'test_project'
            },
            'data': {
                'input': 'test_input.csv'
            }
        }
        
    @patch('worldenergydata.engine.bsee')
    def test_engine_with_bsee_basename(self, mock_bsee):
        """Test engine with bsee basename."""
        # Setup mocks
        mock_bsee_instance = Mock()
        mock_bsee.return_value = mock_bsee_instance
        mock_bsee_instance.router.return_value = self.mock_cfg
        
        # Mock app_manager.save_cfg to avoid AttributeError
        with patch('worldenergydata.engine.app_manager') as mock_app_manager:
            mock_app_manager.save_cfg.return_value = None
            
            # Execute with config_flag=False to avoid complex configuration
            result = engine(cfg=self.mock_cfg, config_flag=False)
            
            # Verify
            assert result == self.mock_cfg
            mock_bsee_instance.router.assert_called_once_with(self.mock_cfg)
            mock_app_manager.save_cfg.assert_called_once()
    
    @patch('worldenergydata.engine.app_manager')
    @patch('worldenergydata.engine.zip')
    def test_engine_with_zip_basename(self, mock_zip, mock_app_manager):
        """Test engine with dwnld_from_zipurl basename."""
        # Setup
        cfg = {'basename': 'dwnld_from_zipurl'}
        mock_app_manager.save_cfg.return_value = None
        
        mock_zip_instance = Mock()
        mock_zip.return_value = mock_zip_instance
        mock_zip_instance.router.return_value = cfg
        
        # Execute
        result = engine(cfg=cfg, config_flag=False)
        
        # Verify
        assert result == cfg
        mock_zip_instance.router.assert_called_once_with(cfg)
    
    @patch('worldenergydata.engine.app_manager')
    @patch('worldenergydata.engine.CustomRouter')
    def test_engine_with_custom_basename(self, mock_custom, mock_app_manager):
        """Test engine with bsee_custom basename."""
        # Setup
        cfg = {'basename': 'bsee_custom'}
        mock_app_manager.save_cfg.return_value = None
        
        mock_custom_instance = Mock()
        mock_custom.return_value = mock_custom_instance
        mock_custom_instance.router.return_value = cfg
        
        # Execute
        result = engine(cfg=cfg, config_flag=False)
        
        # Verify
        assert result == cfg
        mock_custom_instance.router.assert_called_once_with(cfg)
    
    def test_engine_with_invalid_basename(self):
        """Test engine raises exception with invalid basename."""
        cfg = {'basename': 'invalid_basename'}
        
        with pytest.raises(Exception) as exc_info:
            engine(cfg=cfg, config_flag=False)
        
        assert "Analysis for basename: invalid_basename not found" in str(exc_info.value)
    
    def test_engine_with_missing_basename(self):
        """Test engine raises ValueError when basename is missing."""
        cfg = {'data': 'test'}  # No basename
        
        with pytest.raises(ValueError) as exc_info:
            engine(cfg=cfg, config_flag=False)
        
        assert "basename not found in cfg" in str(exc_info.value)
    
    @patch('worldenergydata.engine.app_manager')
    def test_engine_with_basename_in_meta(self, mock_app_manager):
        """Test engine finds basename in meta section."""
        cfg = {
            'meta': {'basename': 'bsee'},
            'data': 'test'
        }
        
        # Mock the save_cfg method
        mock_app_manager.save_cfg.return_value = None
        
        with patch('worldenergydata.engine.bsee') as mock_bsee:
            mock_bsee_instance = Mock()
            mock_bsee.return_value = mock_bsee_instance
            mock_bsee_instance.router.return_value = cfg
            
            result = engine(cfg=cfg, config_flag=False)
            
            assert result == cfg
            mock_app_manager.save_cfg.assert_called_once()
    
    @patch('worldenergydata.engine.app_manager')
    @patch('worldenergydata.engine.wwyaml')
    def test_engine_with_inputfile(self, mock_wwyaml, mock_app_manager):
        """Test engine with input file path."""
        # Setup
        test_cfg = {'basename': 'bsee', 'test': 'data'}
        mock_app_manager.validate_arguments_run_methods.return_value = ('test.yml', {})
        mock_wwyaml.ymlInput.return_value = test_cfg
        mock_app_manager.save_cfg.return_value = None
        
        with patch('worldenergydata.engine.bsee') as mock_bsee:
            mock_bsee_instance = Mock()
            mock_bsee.return_value = mock_bsee_instance
            mock_bsee_instance.router.return_value = test_cfg
            
            result = engine(inputfile='test.yml', config_flag=False)
            
            assert result['basename'] == 'bsee'
            mock_wwyaml.ymlInput.assert_called_once_with('test.yml', updateYml=None)
    
    def test_engine_with_none_cfg_from_yaml(self):
        """Test engine raises ValueError when YAML returns None."""
        with patch('worldenergydata.engine.AttributeDict') as mock_attr_dict:
            with patch('worldenergydata.engine.wwyaml') as mock_wwyaml:
                with patch('worldenergydata.engine.app_manager') as mock_app_manager:
                    mock_app_manager.validate_arguments_run_methods.return_value = ('test.yml', {})
                    mock_wwyaml.ymlInput.return_value = None
                    mock_attr_dict.return_value = None
                    
                    with pytest.raises(ValueError) as exc_info:
                        engine(inputfile='test.yml')
                    
                    assert "cfg is None" in str(exc_info.value)
    
    @patch('worldenergydata.engine.app_manager')
    @patch('worldenergydata.engine.logger')
    def test_engine_logging(self, mock_logger, mock_app_manager):
        """Test that engine logs start and end messages."""
        cfg = {'basename': 'bsee'}
        
        # Mock the save_cfg method
        mock_app_manager.save_cfg.return_value = None
        
        with patch('worldenergydata.engine.bsee') as mock_bsee:
            mock_bsee_instance = Mock()
            mock_bsee.return_value = mock_bsee_instance
            mock_bsee_instance.router.return_value = cfg
            
            engine(cfg=cfg, config_flag=False)
            
            # Check logging calls
            mock_logger.info.assert_any_call("bsee, application ... START")
            mock_logger.info.assert_any_call("bsee, application ... END")


@unit
class TestEngineParameterized:
    """Parameterized tests for engine function."""
    
    @pytest.mark.parametrize("basename,router_class", [
        ('bsee', 'bsee'),
        ('dwnld_from_zipurl', 'zip'),
        ('bsee_custom', 'CustomRouter'),
    ])
    @patch('worldenergydata.engine.app_manager')
    def test_engine_routing(self, mock_app_manager, basename, router_class):
        """Test engine routes to correct handler based on basename."""
        cfg = {'basename': basename}
        
        # Mock the save_cfg method
        mock_app_manager.save_cfg.return_value = None
        
        with patch(f'worldenergydata.engine.{router_class}') as mock_router:
            mock_router_instance = Mock()
            mock_router.return_value = mock_router_instance
            mock_router_instance.router.return_value = cfg
            
            result = engine(cfg=cfg, config_flag=False)
            
            assert result == cfg
            mock_router_instance.router.assert_called_once_with(cfg)
    
    @pytest.mark.parametrize("config_flag", [True, False])
    @patch('worldenergydata.engine.FileManagement')
    @patch('worldenergydata.engine.app_manager')
    def test_engine_config_flag(self, mock_app_manager, mock_fm, config_flag):
        """Test engine behavior with different config_flag values."""
        cfg = {'basename': 'bsee'}
        
        mock_app_manager.configure.return_value = cfg
        mock_app_manager.configure_result_folder.return_value = ({}, cfg)
        mock_app_manager.save_cfg.return_value = None
        
        mock_fm_instance = Mock()
        mock_fm.return_value = mock_fm_instance
        mock_fm_instance.router.return_value = cfg
        
        with patch('worldenergydata.engine.bsee') as mock_bsee:
            mock_bsee_instance = Mock()
            mock_bsee.return_value = mock_bsee_instance
            mock_bsee_instance.router.return_value = cfg
            
            result = engine(cfg=cfg, config_flag=config_flag)
            
            if config_flag:
                mock_app_manager.configure.assert_called_once()
                mock_fm_instance.router.assert_called_once()
            else:
                mock_app_manager.configure.assert_not_called()
                mock_fm_instance.router.assert_not_called()


@smoke
@unit  
class TestEngineSmoke:
    """Smoke tests for engine module."""
    
    def test_engine_module_imports(self):
        """Test that engine module can be imported."""
        import worldenergydata.engine
        assert worldenergydata.engine.engine is not None
    
    def test_engine_function_exists(self):
        """Test that engine function exists and is callable."""
        from worldenergydata.engine import engine
        assert callable(engine)
    
    def test_engine_global_objects(self):
        """Test that global objects are initialized."""
        import worldenergydata.engine as eng
        assert eng.app_manager is not None
        assert eng.save_data is not None
        assert eng.wwyaml is not None
        assert eng.library_name == "worldenergydata"