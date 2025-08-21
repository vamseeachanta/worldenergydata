"""
Comprehensive tests for BSEE custom router module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.worldenergydata.modules.bsee.custom_router import CustomRouter


class TestCustomRouter:
    """Test suite for CustomRouter class"""
    
    @pytest.fixture
    def router(self):
        """Create CustomRouter instance"""
        return CustomRouter()
    
    @pytest.fixture
    def mock_drilling_analysis(self):
        """Mock the drilling analysis module"""
        with patch('src.worldenergydata.modules.bsee.custom_router.drilling_analysis') as mock:
            yield mock
    
    def test_init(self, router):
        """Test CustomRouter initialization"""
        assert router is not None
        assert isinstance(router, CustomRouter)
    
    def test_router_with_drilling_completion_days_flag(self, router, mock_drilling_analysis):
        """Test router with drilling_n_completion_days flag set"""
        cfg = {
            'drilling_n_completion_days': {
                'flag': True,
                'data': 'test_data'
            }
        }
        
        result = router.router(cfg)
        
        # Verify drilling_analysis.router was called
        mock_drilling_analysis.router.assert_called_once_with(cfg)
        assert result == cfg
    
    def test_router_with_drilling_completion_days_flag_false(self, router, mock_drilling_analysis):
        """Test router with drilling_n_completion_days flag False"""
        cfg = {
            'drilling_n_completion_days': {
                'flag': False,
                'data': 'test_data'
            }
        }
        
        result = router.router(cfg)
        
        # Verify drilling_analysis.router was NOT called
        mock_drilling_analysis.router.assert_not_called()
        assert result == cfg
    
    def test_router_without_drilling_completion_days(self, router, mock_drilling_analysis):
        """Test router without drilling_n_completion_days key"""
        cfg = {
            'other_config': {
                'flag': True
            }
        }
        
        result = router.router(cfg)
        
        # Verify drilling_analysis.router was NOT called
        mock_drilling_analysis.router.assert_not_called()
        assert result == cfg
    
    def test_router_with_custom_analysis_flag(self, router):
        """Test router with custom_analysis flag"""
        cfg = {
            'custom_analysis': {
                'flag': True,
                'data': 'test_data'
            }
        }
        
        result = router.router(cfg)
        
        # Should pass through without error (currently commented out)
        assert result == cfg
    
    def test_router_with_custom_analysis_flag_false(self, router):
        """Test router with custom_analysis flag False"""
        cfg = {
            'custom_analysis': {
                'flag': False
            }
        }
        
        result = router.router(cfg)
        assert result == cfg
    
    def test_router_with_custom_remarks_analysis_flag(self, router):
        """Test router with custom_remarks_analysis flag"""
        cfg = {
            'custom_remarks_analysis': {
                'flag': True,
                'remarks': 'test_remarks'
            }
        }
        
        result = router.router(cfg)
        
        # Should pass through without error (currently commented out)
        assert result == cfg
    
    def test_router_with_custom_remarks_analysis_flag_false(self, router):
        """Test router with custom_remarks_analysis flag False"""
        cfg = {
            'custom_remarks_analysis': {
                'flag': False
            }
        }
        
        result = router.router(cfg)
        assert result == cfg
    
    def test_router_with_multiple_flags_drilling_priority(self, router, mock_drilling_analysis):
        """Test router with multiple flags - drilling takes priority"""
        cfg = {
            'drilling_n_completion_days': {
                'flag': True
            },
            'custom_analysis': {
                'flag': True
            },
            'custom_remarks_analysis': {
                'flag': True
            }
        }
        
        result = router.router(cfg)
        
        # Only drilling_analysis should be called due to elif structure
        mock_drilling_analysis.router.assert_called_once_with(cfg)
        assert result == cfg
    
    def test_router_with_empty_config(self, router):
        """Test router with empty configuration"""
        cfg = {}
        result = router.router(cfg)
        assert result == {}
    
    def test_router_preserves_additional_config(self, router):
        """Test that router preserves additional configuration data"""
        cfg = {
            'drilling_n_completion_days': {
                'flag': False
            },
            'additional_data': {
                'key1': 'value1',
                'key2': 'value2'
            },
            'metadata': {
                'version': '1.0',
                'timestamp': '2024-01-01'
            }
        }
        
        result = router.router(cfg)
        
        # All original data should be preserved
        assert result == cfg
        assert 'additional_data' in result
        assert 'metadata' in result
        assert result['additional_data']['key1'] == 'value1'