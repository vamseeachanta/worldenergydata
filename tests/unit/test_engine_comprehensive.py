"""
Comprehensive tests for the worldenergydata engine module
Target: 100% coverage for engine.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from worldenergydata.engine import engine


class TestEngine:
    """Comprehensive test suite for engine function"""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        with patch('worldenergydata.engine.ConfigureApplicationInputs') as mock_app_manager_class, \
             patch('worldenergydata.engine.SaveData') as mock_save_data_class, \
             patch('worldenergydata.engine.WorkingWithYAML') as mock_wwyaml_class, \
             patch('worldenergydata.engine.FileManagement') as mock_fm_class, \
             patch('worldenergydata.engine.bsee') as mock_bsee_class, \
             patch('worldenergydata.engine.zip') as mock_zip_class, \
             patch('worldenergydata.engine.CustomRouter') as mock_custom_router_class, \
             patch('worldenergydata.engine.logger') as mock_logger, \
             patch('worldenergydata.engine.AttributeDict') as mock_attr_dict:
            
            # Create mock instances
            mock_app_manager = Mock()
            mock_save_data = Mock()
            mock_wwyaml = Mock()
            mock_fm = Mock()
            mock_bsee = Mock()
            mock_zip = Mock()
            mock_custom_router = Mock()
            
            # Configure class constructors
            mock_app_manager_class.return_value = mock_app_manager
            mock_save_data_class.return_value = mock_save_data
            mock_wwyaml_class.return_value = mock_wwyaml
            mock_fm_class.return_value = mock_fm
            mock_bsee_class.return_value = mock_bsee
            mock_zip_class.return_value = mock_zip
            mock_custom_router_class.return_value = mock_custom_router
            
            # Configure AttributeDict to return input as-is
            mock_attr_dict.side_effect = lambda x: x
            
            yield {
                'app_manager': mock_app_manager,
                'save_data': mock_save_data,
                'wwyaml': mock_wwyaml,
                'fm': mock_fm,
                'bsee': mock_bsee,
                'zip': mock_zip,
                'custom_router': mock_custom_router,
                'logger': mock_logger,
                'attr_dict': mock_attr_dict,
                'app_manager_class': mock_app_manager_class,
                'fm_class': mock_fm_class,
                'bsee_class': mock_bsee_class,
                'zip_class': mock_zip_class,
                'custom_router_class': mock_custom_router_class
            }
    
    def test_engine_with_bsee_basename(self, mock_dependencies):
        """Test engine with bsee basename"""
        # Setup
        cfg = {'basename': 'bsee', 'data': 'test_data', 'Analysis': {'analysis_root_folder': '/tmp'}}
        mock_cfg = Mock()
        mock_cfg.basename = 'bsee'
        mock_cfg.Analysis = {'analysis_root_folder': '/tmp'}
        mock_dependencies['attr_dict'].return_value = mock_cfg
        mock_dependencies['bsee'].router.return_value = mock_cfg
        mock_dependencies['app_manager'].save_cfg.return_value = None
        
        # Execute
        result = engine(cfg=cfg, config_flag=False)
        
        # Verify
        assert result == mock_cfg
        mock_dependencies['bsee'].router.assert_called_once_with(cfg)
        mock_dependencies['logger'].info.assert_any_call("bsee, application ... START")
        mock_dependencies['logger'].info.assert_any_call("bsee, application ... END")
        mock_dependencies['app_manager'].save_cfg.assert_called_once()
    
    def test_engine_with_dwnld_from_zipurl_basename(self, mock_dependencies):
        """Test engine with dwnld_from_zipurl basename"""
        # Setup
        cfg = {'basename': 'dwnld_from_zipurl', 'data': 'test_data'}
        mock_dependencies['zip'].router.return_value = cfg
        mock_dependencies['app_manager'].save_cfg.return_value = None
        
        # Execute
        result = engine(cfg=cfg, config_flag=False)
        
        # Verify
        assert result == cfg
        mock_dependencies['zip'].router.assert_called_once_with(cfg)
        mock_dependencies['logger'].info.assert_any_call("dwnld_from_zipurl, application ... START")
        mock_dependencies['logger'].info.assert_any_call("dwnld_from_zipurl, application ... END")
    
    def test_engine_with_bsee_custom_basename(self, mock_dependencies):
        """Test engine with bsee_custom basename"""
        # Setup
        cfg = {'basename': 'bsee_custom', 'data': 'test_data'}
        mock_dependencies['custom_router'].router.return_value = cfg
        mock_dependencies['app_manager'].save_cfg.return_value = None
        
        # Execute
        result = engine(cfg=cfg, config_flag=False)
        
        # Verify
        assert result == cfg
        mock_dependencies['custom_router'].router.assert_called_once_with(cfg)
        mock_dependencies['logger'].info.assert_any_call("bsee_custom, application ... START")
        mock_dependencies['logger'].info.assert_any_call("bsee_custom, application ... END")
    
    def test_engine_with_meta_basename(self, mock_dependencies):
        """Test engine with basename in meta section"""
        # Setup
        cfg = {'meta': {'basename': 'bsee'}, 'data': 'test_data'}
        mock_dependencies['bsee'].router.return_value = cfg
        mock_dependencies['app_manager'].save_cfg.return_value = None
        
        # Execute
        result = engine(cfg=cfg, config_flag=False)
        
        # Verify
        assert result == cfg
        mock_dependencies['bsee'].router.assert_called_once_with(cfg)
    
    def test_engine_with_invalid_basename(self, mock_dependencies):
        """Test engine with invalid basename raises exception"""
        # Setup
        cfg = {'basename': 'invalid_basename', 'data': 'test_data'}
        
        # Execute and verify
        with pytest.raises(Exception) as exc_info:
            engine(cfg=cfg, config_flag=False)
        
        assert "Analysis for basename: invalid_basename not found" in str(exc_info.value)
    
    def test_engine_without_basename(self, mock_dependencies):
        """Test engine without basename raises ValueError"""
        # Setup
        cfg = {'data': 'test_data'}  # No basename
        
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            engine(cfg=cfg, config_flag=False)
        
        assert "basename not found in cfg" in str(exc_info.value)
    
    def test_engine_with_inputfile(self, mock_dependencies):
        """Test engine with inputfile parameter"""
        # Setup
        test_cfg = {'basename': 'bsee', 'data': 'from_file'}
        mock_dependencies['app_manager'].validate_arguments_run_methods.return_value = ('test.yml', {})
        mock_dependencies['wwyaml'].ymlInput.return_value = test_cfg
        mock_dependencies['app_manager'].configure.return_value = test_cfg
        mock_dependencies['fm'].router.return_value = test_cfg
        mock_dependencies['app_manager'].configure_result_folder.return_value = ({}, test_cfg)
        mock_dependencies['bsee'].router.return_value = test_cfg
        mock_dependencies['app_manager'].save_cfg.return_value = None
        
        # Execute
        result = engine(inputfile='test.yml')
        
        # Verify
        mock_dependencies['app_manager'].validate_arguments_run_methods.assert_called_once_with('test.yml')
        mock_dependencies['wwyaml'].ymlInput.assert_called_once_with('test.yml', updateYml=None)
        assert result == test_cfg
    
    def test_engine_with_config_flag_true(self, mock_dependencies):
        """Test engine with config_flag=True"""
        # Setup
        test_cfg = {'basename': 'bsee', 'data': 'test'}
        mock_dependencies['app_manager'].configure.return_value = test_cfg
        mock_dependencies['fm'].router.return_value = test_cfg
        mock_dependencies['app_manager'].configure_result_folder.return_value = ({}, test_cfg)
        mock_dependencies['bsee'].router.return_value = test_cfg
        mock_dependencies['app_manager'].save_cfg.return_value = None
        
        # Execute
        result = engine(cfg=test_cfg, config_flag=True)
        
        # Verify
        mock_dependencies['fm_class'].assert_called_once()
        mock_dependencies['app_manager'].configure.assert_called_once()
        mock_dependencies['fm'].router.assert_called_once_with(test_cfg)
        mock_dependencies['app_manager'].configure_result_folder.assert_called_once()
        assert result == test_cfg
    
    def test_engine_with_null_cfg_from_file(self, mock_dependencies):
        """Test engine when cfg from file is None"""
        # Setup
        mock_dependencies['app_manager'].validate_arguments_run_methods.return_value = ('test.yml', {})
        mock_dependencies['wwyaml'].ymlInput.return_value = None
        
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            engine(inputfile='test.yml')
        
        assert "cfg is None" in str(exc_info.value)
    
    def test_engine_saves_cfg_after_processing(self, mock_dependencies):
        """Test that engine saves configuration after processing"""
        # Setup
        cfg = {'basename': 'bsee', 'data': 'test_data'}
        processed_cfg = {'basename': 'bsee', 'data': 'processed_data'}
        mock_dependencies['bsee'].router.return_value = processed_cfg
        mock_dependencies['app_manager'].save_cfg.return_value = None
        
        # Execute
        result = engine(cfg=cfg, config_flag=False)
        
        # Verify
        assert result == processed_cfg
        mock_dependencies['app_manager'].save_cfg.assert_called_once_with(cfg_base=processed_cfg)
    
    def test_engine_with_all_basenames_sequentially(self, mock_dependencies):
        """Test engine with all supported basenames"""
        basenames = ['bsee', 'dwnld_from_zipurl', 'bsee_custom']
        routers = [mock_dependencies['bsee'], mock_dependencies['zip'], mock_dependencies['custom_router']]
        
        for basename, router in zip(basenames, routers):
            # Setup
            cfg = {'basename': basename, 'data': f'{basename}_data'}
            router.router.return_value = cfg
            mock_dependencies['app_manager'].save_cfg.return_value = None
            
            # Execute
            result = engine(cfg=cfg, config_flag=False)
            
            # Verify
            assert result == cfg
            router.router.assert_called_with(cfg)
            
            # Reset mock for next iteration
            router.router.reset_mock()
    
    def test_engine_logger_calls(self, mock_dependencies):
        """Test that logger is called with correct messages"""
        # Setup
        cfg = {'basename': 'bsee', 'test': 'data'}
        mock_dependencies['bsee'].router.return_value = cfg
        mock_dependencies['app_manager'].save_cfg.return_value = None
        
        # Execute
        engine(cfg=cfg, config_flag=False)
        
        # Verify logger calls
        expected_calls = [
            call("bsee, application ... START"),
            call("bsee, application ... END")
        ]
        mock_dependencies['logger'].info.assert_has_calls(expected_calls)
    
    def test_engine_with_complex_nested_config(self, mock_dependencies):
        """Test engine with complex nested configuration"""
        # Setup
        cfg = {
            'meta': {
                'basename': 'bsee',
                'version': '1.0'
            },
            'data': {
                'source': 'test',
                'nested': {
                    'level1': {
                        'level2': 'value'
                    }
                }
            }
        }
        mock_dependencies['bsee'].router.return_value = cfg
        mock_dependencies['app_manager'].save_cfg.return_value = None
        
        # Execute
        result = engine(cfg=cfg, config_flag=False)
        
        # Verify
        assert result == cfg
        assert result['data']['nested']['level1']['level2'] == 'value'