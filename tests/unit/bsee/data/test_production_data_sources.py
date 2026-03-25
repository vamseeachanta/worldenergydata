"""
Unit tests for ProductionDataFromSources module.

Tests the production data source routing and data retrieval functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import pandas as pd
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "src"))

from worldenergydata.bsee.data.production.production_data_sources import ProductionDataFromSources
from tests.test_markers import unit


@unit
class TestProductionDataFromSources:
    """Unit tests for ProductionDataFromSources class."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.prod_source = ProductionDataFromSources()
        self.mock_cfg = {
            'basename': 'bsee',
            'data': {
                'groups': [
                    {'api12': ['123456789012']},
                    {'api12': ['234567890123']}
                ]
            }
        }
    
    def test_init(self):
        """Test ProductionDataFromSources initialization."""
        source = ProductionDataFromSources()
        assert source is not None
    
    def test_router(self):
        """Test router method."""
        # Router method just passes through
        result = self.prod_source.router(self.mock_cfg)
        assert result is None
    
    @patch('worldenergydata.bsee.data.production.production_data_sources.production_from_zip')
    def test_get_data_without_zip(self, mock_prod_zip):
        """Test get_data without zip flag."""
        # Setup
        mock_df = pd.DataFrame({'data': [1, 2, 3]})
        mock_prod_zip.get_data_by_api12_array.return_value = mock_df
        
        # Execute
        cfg, production_data_groups = self.prod_source.get_data(self.mock_cfg)
        
        # Verify
        assert cfg == self.mock_cfg
        assert len(production_data_groups) == 2
        assert all(df.equals(mock_df) for df in production_data_groups)
        
        # Check calls
        assert mock_prod_zip.get_data_by_api12_array.call_count == 2
        calls = mock_prod_zip.get_data_by_api12_array.call_args_list
        assert calls[0] == call(self.mock_cfg, ['123456789012'])
        assert calls[1] == call(self.mock_cfg, ['234567890123'])
    
    @patch('worldenergydata.bsee.data.production.production_data_sources.production_from_zip')
    def test_get_data_with_zip(self, mock_prod_zip):
        """Test get_data with zip flag."""
        # Setup
        cfg = {
            'basename': 'bsee',
            'data': {
                'by': 'zip',
                'groups': [
                    {'api12': ['123456789012']},
                    {'api12': ['234567890123']}
                ]
            }
        }
        
        mock_df = pd.DataFrame({'data': [1, 2, 3]})
        mock_prod_zip.get_data_by_api12_array.return_value = mock_df
        mock_prod_zip.get_production_data_by_wellapi12.return_value = None
        
        # Execute
        result_cfg, production_data_groups = self.prod_source.get_data(cfg)
        
        # Verify
        assert result_cfg == cfg
        assert len(production_data_groups) == 2
        
        # Check that get_production_from_zip was called
        mock_prod_zip.get_production_data_by_wellapi12.assert_called_once_with(cfg, '123456789012')
    
    @patch('worldenergydata.bsee.data.production.production_data_sources.production_from_zip')
    def test_get_production_from_zip(self, mock_prod_zip):
        """Test get_production_from_zip method."""
        # Setup
        api12 = '123456789012'
        mock_prod_zip.get_production_data_by_wellapi12.return_value = None
        
        # Execute
        result = self.prod_source.get_production_from_zip(self.mock_cfg, api12)
        
        # Verify
        assert result == self.mock_cfg
        mock_prod_zip.get_production_data_by_wellapi12.assert_called_once_with(self.mock_cfg, api12)
    
    @patch('worldenergydata.bsee.data.production.production_data_sources.production_from_zip')
    def test_get_data_empty_groups(self, mock_prod_zip):
        """Test get_data with empty groups."""
        # Setup
        cfg = {
            'basename': 'bsee',
            'data': {
                'groups': []
            }
        }
        
        # Execute
        result_cfg, production_data_groups = self.prod_source.get_data(cfg)
        
        # Verify
        assert result_cfg == cfg
        assert production_data_groups == []
        mock_prod_zip.get_data_by_api12_array.assert_not_called()
    
    @patch('worldenergydata.bsee.data.production.production_data_sources.production_from_zip')
    def test_get_data_multiple_api12_per_group(self, mock_prod_zip):
        """Test get_data with multiple API12s per group."""
        # Setup
        cfg = {
            'basename': 'bsee',
            'data': {
                'groups': [
                    {'api12': ['123456789012', '234567890123', '345678901234']}
                ]
            }
        }
        
        mock_df = pd.DataFrame({'data': [1, 2, 3]})
        mock_prod_zip.get_data_by_api12_array.return_value = mock_df
        
        # Execute
        result_cfg, production_data_groups = self.prod_source.get_data(cfg)
        
        # Verify
        assert len(production_data_groups) == 1
        mock_prod_zip.get_data_by_api12_array.assert_called_once_with(
            cfg, ['123456789012', '234567890123', '345678901234']
        )


@unit
class TestProductionDataFromSourcesIntegration:
    """Integration tests for ProductionDataFromSources."""
    
    def test_module_imports(self):
        """Test that all required modules can be imported."""
        from worldenergydata.bsee.data.production.production_data_sources import (
            ProductionDataFromSources,
            production_from_zip
        )
        
        assert ProductionDataFromSources is not None
        assert production_from_zip is not None
    
    def test_class_instantiation(self):
        """Test that class can be instantiated."""
        source = ProductionDataFromSources()
        assert source is not None
        assert hasattr(source, 'router')
        assert hasattr(source, 'get_data')
        assert hasattr(source, 'get_production_from_zip')