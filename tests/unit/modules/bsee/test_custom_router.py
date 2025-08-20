"""
Unit tests for the CustomRouter module.

Tests the custom routing functionality for special analysis types.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from worldenergydata.modules.bsee.custom_router import CustomRouter
from tests.test_markers import unit


@unit
class TestCustomRouter:
    """Unit tests for the CustomRouter class."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.router = CustomRouter()
    
    def test_init(self):
        """Test CustomRouter initialization."""
        router = CustomRouter()
        assert router is not None
    
    @patch('worldenergydata.modules.bsee.custom_router.drilling_analysis')
    def test_router_with_drilling_completion_flag(self, mock_drilling):
        """Test router with drilling_n_completion_days flag."""
        # Setup
        cfg = {
            'drilling_n_completion_days': {'flag': True},
            'test': 'data'
        }
        mock_drilling.router.return_value = None
        
        # Execute
        result = self.router.router(cfg)
        
        # Verify
        assert result == cfg
        mock_drilling.router.assert_called_once_with(cfg)
    
    @patch('worldenergydata.modules.bsee.custom_router.drilling_analysis')
    def test_router_without_drilling_flag(self, mock_drilling):
        """Test router when drilling flag is False."""
        # Setup
        cfg = {
            'drilling_n_completion_days': {'flag': False},
            'test': 'data'
        }
        
        # Execute
        result = self.router.router(cfg)
        
        # Verify
        assert result == cfg
        mock_drilling.router.assert_not_called()
    
    def test_router_with_custom_analysis_flag(self):
        """Test router with custom_analysis flag."""
        # Setup
        cfg = {
            'custom_analysis': {'flag': True},
            'test': 'data'
        }
        
        # Execute
        result = self.router.router(cfg)
        
        # Verify - should pass through since implementations are commented
        assert result == cfg
    
    def test_router_with_custom_remarks_analysis_flag(self):
        """Test router with custom_remarks_analysis flag."""
        # Setup
        cfg = {
            'custom_remarks_analysis': {'flag': True},
            'test': 'data'
        }
        
        # Execute
        result = self.router.router(cfg)
        
        # Verify - should pass through since implementations are commented
        assert result == cfg
    
    def test_router_with_no_flags(self):
        """Test router with no special flags."""
        # Setup
        cfg = {'test': 'data', 'other': 'value'}
        
        # Execute
        result = self.router.router(cfg)
        
        # Verify - should return unchanged
        assert result == cfg
    
    def test_router_with_multiple_flags_false(self):
        """Test router with multiple flags set to False."""
        # Setup
        cfg = {
            'drilling_n_completion_days': {'flag': False},
            'custom_analysis': {'flag': False},
            'custom_remarks_analysis': {'flag': False},
            'test': 'data'
        }
        
        # Execute
        result = self.router.router(cfg)
        
        # Verify - should return unchanged
        assert result == cfg
    
    @patch('worldenergydata.modules.bsee.custom_router.drilling_analysis')
    def test_router_exception_handling(self, mock_drilling):
        """Test that exceptions from drilling analysis propagate."""
        # Setup
        cfg = {
            'drilling_n_completion_days': {'flag': True}
        }
        mock_drilling.router.side_effect = RuntimeError("Drilling analysis failed")
        
        # Execute and verify exception propagates
        with pytest.raises(RuntimeError, match="Drilling analysis failed"):
            self.router.router(cfg)
    
    def test_router_missing_flag_key(self):
        """Test router when flag key is missing."""
        # Setup - has the drilling_n_completion_days but no flag
        cfg = {
            'drilling_n_completion_days': {'data': 'value'},
            'test': 'data'
        }
        
        # Execute - should handle gracefully (will raise KeyError currently)
        # This test documents the current behavior
        with pytest.raises(KeyError):
            self.router.router(cfg)


@unit
class TestCustomRouterParameterized:
    """Parameterized tests for CustomRouter."""
    
    @pytest.fixture
    def router(self):
        """Create CustomRouter instance."""
        return CustomRouter()
    
    @pytest.mark.parametrize("config,should_call_drilling", [
        ({'drilling_n_completion_days': {'flag': True}}, True),
        ({'drilling_n_completion_days': {'flag': False}}, False),
        ({}, False),
        ({'custom_analysis': {'flag': True}}, False),
        ({'custom_remarks_analysis': {'flag': True}}, False),
    ])
    @patch('worldenergydata.modules.bsee.custom_router.drilling_analysis')
    def test_router_flag_combinations(self, mock_drilling, router, config, should_call_drilling):
        """Test router with various flag combinations."""
        # Execute
        result = router.router(config)
        
        # Verify
        assert result == config
        if should_call_drilling:
            mock_drilling.router.assert_called_once_with(config)
        else:
            mock_drilling.router.assert_not_called()