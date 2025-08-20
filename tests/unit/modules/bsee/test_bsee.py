"""
Unit tests for the bsee module.

Tests the main bsee router class and its integration with data and analysis components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from worldenergydata.modules.bsee.bsee import bsee
from tests.test_markers import unit


@unit
class TestBSEE:
    """Unit tests for the bsee class."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.bsee_instance = bsee()
        self.mock_cfg = {
            'basename': 'bsee',
            'data': {'test_data': 'value'},
            'analysis': {'test_analysis': 'value'}
        }
    
    def test_init(self):
        """Test bsee initialization."""
        instance = bsee()
        assert instance is not None
    
    @patch('worldenergydata.modules.bsee.bsee.bsee_analysis')
    @patch('worldenergydata.modules.bsee.bsee.bsee_data')
    def test_router_basic(self, mock_bsee_data, mock_bsee_analysis):
        """Test basic router functionality."""
        # Setup mocks
        test_data = {'processed': 'data'}
        mock_bsee_data.router.return_value = (self.mock_cfg, test_data)
        mock_bsee_analysis.router.return_value = self.mock_cfg
        
        # Execute
        result = self.bsee_instance.router(self.mock_cfg)
        
        # Verify
        assert result == self.mock_cfg
        assert 'bsee' in result
        assert result['bsee']['data'] == {'test_data': 'value'}
        assert result['bsee']['analysis'] == {'test_analysis': 'value'}
        
        # Verify calls
        mock_bsee_data.router.assert_called_once_with(self.mock_cfg)
        mock_bsee_analysis.router.assert_called_once_with(self.mock_cfg, test_data)
    
    @patch('worldenergydata.modules.bsee.bsee.bsee_analysis')
    @patch('worldenergydata.modules.bsee.bsee.bsee_data')
    def test_router_without_analysis_key(self, mock_bsee_data, mock_bsee_analysis):
        """Test router when cfg doesn't have analysis key."""
        # Setup cfg without analysis
        cfg = {
            'basename': 'bsee',
            'data': {'test_data': 'value'}
        }
        
        test_data = {'processed': 'data'}
        mock_bsee_data.router.return_value = (cfg, test_data)
        mock_bsee_analysis.router.return_value = cfg
        
        # Execute
        result = self.bsee_instance.router(cfg)
        
        # Verify
        assert 'bsee' in result
        assert result['bsee']['analysis'] == {}  # Should be empty dict
    
    @patch('worldenergydata.modules.bsee.bsee.bsee_analysis')
    @patch('worldenergydata.modules.bsee.bsee.bsee_data')
    def test_router_data_copy(self, mock_bsee_data, mock_bsee_analysis):
        """Test that router creates copies of data and analysis."""
        # Setup
        original_data = {'key': 'value'}
        original_analysis = {'analysis_key': 'analysis_value'}
        cfg = {
            'basename': 'bsee',
            'data': original_data,
            'analysis': original_analysis
        }
        
        test_data = {'processed': 'data'}
        mock_bsee_data.router.return_value = (cfg, test_data)
        mock_bsee_analysis.router.return_value = cfg
        
        # Execute
        result = self.bsee_instance.router(cfg)
        
        # Modify the original
        original_data['key'] = 'modified'
        original_analysis['analysis_key'] = 'modified'
        
        # Verify copies were made
        assert result['bsee']['data']['key'] == 'value'
        assert result['bsee']['analysis']['analysis_key'] == 'analysis_value'
    
    @patch('worldenergydata.modules.bsee.bsee.bsee_analysis')
    @patch('worldenergydata.modules.bsee.bsee.bsee_data')
    def test_router_exception_propagation(self, mock_bsee_data, mock_bsee_analysis):
        """Test that exceptions in sub-routers propagate."""
        # Setup data router to raise exception
        mock_bsee_data.router.side_effect = RuntimeError("Data router failed")
        
        # Execute and verify exception propagates
        with pytest.raises(RuntimeError, match="Data router failed"):
            self.bsee_instance.router(self.mock_cfg)
    
    @patch('worldenergydata.modules.bsee.bsee.bsee_analysis')
    @patch('worldenergydata.modules.bsee.bsee.bsee_data')
    def test_router_with_different_basename(self, mock_bsee_data, mock_bsee_analysis):
        """Test router with different basename."""
        cfg = {
            'basename': 'custom_bsee',
            'data': {'test': 'data'},
            'analysis': {'test': 'analysis'}
        }
        
        test_data = {'processed': 'data'}
        mock_bsee_data.router.return_value = (cfg, test_data)
        mock_bsee_analysis.router.return_value = cfg
        
        # Execute
        result = self.bsee_instance.router(cfg)
        
        # Verify the key matches basename
        assert 'custom_bsee' in result
        assert result['custom_bsee']['data'] == {'test': 'data'}


@unit
class TestBSEEIntegration:
    """Integration tests for bsee module with its components."""
    
    def test_module_imports(self):
        """Test that all required modules can be imported."""
        from worldenergydata.modules.bsee.bsee import bsee
        from worldenergydata.modules.bsee.data.bsee_data import BSEEData
        from worldenergydata.modules.bsee.analysis.bsee_analysis import BSEEAnalysis
        
        assert bsee is not None
        assert BSEEData is not None
        assert BSEEAnalysis is not None
    
    def test_global_instances(self):
        """Test that global instances are created."""
        from worldenergydata.modules.bsee.bsee import bsee_data, bsee_analysis
        
        assert bsee_data is not None
        assert bsee_analysis is not None