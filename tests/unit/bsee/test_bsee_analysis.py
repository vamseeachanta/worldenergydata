"""
Unit tests for BSEE analysis module.

Tests the BSEEAnalysis class including routing, well analysis,
and production data integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from worldenergydata.bsee.analysis.bsee_analysis import BSEEAnalysis
from tests.test_markers import unit, smoke


@unit
class TestBSEEAnalysis:
    """Unit tests for BSEEAnalysis class."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.analysis = BSEEAnalysis()
        self.mock_cfg = {
            'analysis': {
                'flag': True,
                'type': 'production'
            },
            'output': {
                'directory': 'test_output'
            }
        }
        self.mock_data = {
            'well_data': pd.DataFrame({
                'API12': ['123456789012', '234567890123'],
                'WELL_NAME': ['WELL-1', 'WELL-2']
            }),
            'production_data': pd.DataFrame({
                'API12': ['123456789012', '234567890123'],
                'PRODUCTION': [1000, 2000]
            })
        }
    
    def test_init(self):
        """Test BSEEAnalysis initialization."""
        analysis = BSEEAnalysis()
        assert analysis is not None
    
    @patch('worldenergydata.bsee.analysis.bsee_analysis.logger')
    def test_router_with_analysis_flag_true(self, mock_logger):
        """Test router when analysis flag is True."""
        with patch.object(self.analysis, 'run_analysis_for_all_wells') as mock_run:
            mock_run.return_value = self.mock_cfg
            
            result = self.analysis.router(self.mock_cfg, self.mock_data)
            
            assert result == self.mock_cfg
            mock_run.assert_called_once_with(self.mock_cfg, self.mock_data)
            mock_logger.info.assert_any_call("Running analysis for all wells...")
    
    @patch('worldenergydata.bsee.analysis.bsee_analysis.logger')
    def test_router_with_analysis_flag_false(self, mock_logger):
        """Test router when analysis flag is False."""
        cfg = {'analysis': {'flag': False}}
        
        result = self.analysis.router(cfg, self.mock_data)
        
        assert result == cfg
        mock_logger.info.assert_any_call("Analysis not enabled or flag is False")
    
    @patch('worldenergydata.bsee.analysis.bsee_analysis.logger')
    def test_router_without_analysis_key(self, mock_logger):
        """Test router when analysis key is missing."""
        cfg = {'other': 'data'}
        
        result = self.analysis.router(cfg, self.mock_data)
        
        assert result == cfg
        mock_logger.info.assert_any_call("Analysis not enabled or flag is False")
    
    @patch('worldenergydata.bsee.analysis.bsee_analysis.well_api12_analysis')
    @patch('worldenergydata.bsee.analysis.bsee_analysis.prod_api12_analysis')
    def test_run_analysis_for_all_wells(self, mock_prod_analysis, mock_well_analysis):
        """Test run_analysis_for_all_wells method."""
        # Setup mocks
        well_groups = {
            'well_summary_df_groups': pd.DataFrame({
                'API12': ['123456789012'],
                'WELL_NAME': ['WELL-1']
            })
        }
        prod_groups = {
            'production_summary_df_groups': pd.DataFrame({
                'API12': ['123456789012'],
                'START_PRODUCTION_DATE': '2020-01-01',
                'LAST_PRODUCTION_DATE': '2023-12-31'
            })
        }
        
        mock_well_analysis.run_well_analysis.return_value = (self.mock_cfg, well_groups)
        mock_prod_analysis.run_production_analysis.return_value = (self.mock_cfg, prod_groups)
        mock_well_analysis.well_timeline_analysis.return_value = pd.DataFrame()
        
        with patch.object(self.analysis, 'add_production_dates_to_well_summary'):
            result = self.analysis.run_analysis_for_all_wells(self.mock_cfg, self.mock_data)
            
            assert result == self.mock_cfg
            mock_well_analysis.run_well_analysis.assert_called_once()
            mock_prod_analysis.run_production_analysis.assert_called_once()
            mock_well_analysis.save_result_groups.assert_called_once()
            mock_well_analysis.plot_well_timeline_df.assert_called_once()
    
    @patch('worldenergydata.bsee.analysis.bsee_analysis.well_api12_analysis')
    def test_run_analysis_with_no_production_data(self, mock_well_analysis):
        """Test analysis when production data is None."""
        data = {'production_data': None}
        well_groups = {'well_summary_df_groups': pd.DataFrame()}
        
        mock_well_analysis.run_well_analysis.return_value = (self.mock_cfg, well_groups)
        
        result = self.analysis.run_analysis_for_all_wells(self.mock_cfg, data)
        
        assert result == self.mock_cfg
        mock_well_analysis.run_well_analysis.assert_called_once()
    
    @patch('worldenergydata.bsee.analysis.bsee_analysis.well_api12_analysis')
    @patch('worldenergydata.bsee.analysis.bsee_analysis.logger')
    def test_add_production_dates_to_well_summary(self, mock_logger, mock_well_api12):
        """Test adding production dates to well summary."""
        # Mock save_result_groups to avoid file operations
        mock_well_api12.save_result_groups = Mock()
        
        well_groups = {
            'well_summary_df_groups': pd.DataFrame({
                'API12': ['123456789012', '234567890123'],
                'WELL_NAME': ['WELL-1', 'WELL-2']
            })
        }
        prod_groups = {
            'production_summary_df_groups': pd.DataFrame({
                'API12': ['123456789012'],
                'START_PRODUCTION_DATE': '2020-01-01',
                'LAST_PRODUCTION_DATE': '2023-12-31'
            })
        }
        
        self.analysis.add_production_dates_to_well_summary(
            self.mock_cfg, well_groups, prod_groups
        )
        
        # Check that dates were added
        well_df = well_groups['well_summary_df_groups']
        assert 'START_PRODUCTION_DATE' in well_df.columns
        assert 'LAST_PRODUCTION_DATE' in well_df.columns
        assert well_df.loc[0, 'START_PRODUCTION_DATE'] == '2020-01-01'
        assert well_df.loc[0, 'LAST_PRODUCTION_DATE'] == '2023-12-31'
    
    @patch('worldenergydata.bsee.analysis.bsee_analysis.logger')
    def test_add_production_dates_empty_dataframes(self, mock_logger):
        """Test adding production dates with empty dataframes."""
        well_groups = {'well_summary_df_groups': pd.DataFrame()}
        prod_groups = {'production_summary_df_groups': pd.DataFrame()}
        
        self.analysis.add_production_dates_to_well_summary(
            self.mock_cfg, well_groups, prod_groups
        )
        
        mock_logger.warning.assert_called_with(
            "Production or well summary data is empty - skipping production date integration"
        )
    
    @patch('worldenergydata.bsee.analysis.bsee_analysis.well_api12_analysis')
    @patch('worldenergydata.bsee.analysis.bsee_analysis.logger')
    def test_add_production_dates_no_matching_wells(self, mock_logger, mock_well_api12):
        """Test adding production dates when no wells match."""
        # Mock save_result_groups to avoid file operations
        mock_well_api12.save_result_groups = Mock()
        
        well_groups = {
            'well_summary_df_groups': pd.DataFrame({
                'API12': ['999999999999'],
                'WELL_NAME': ['WELL-X']
            })
        }
        prod_groups = {
            'production_summary_df_groups': pd.DataFrame({
                'API12': ['123456789012'],
                'START_PRODUCTION_DATE': '2020-01-01',
                'LAST_PRODUCTION_DATE': '2023-12-31'
            })
        }
        
        self.analysis.add_production_dates_to_well_summary(
            self.mock_cfg, well_groups, prod_groups
        )
        
        mock_logger.warning.assert_called_with(
            "No matching well found for production API12: 123456789012"
        )


@unit
class TestBSEEAnalysisParameterized:
    """Parameterized tests for BSEEAnalysis."""
    
    @pytest.fixture
    def analysis(self):
        """Create BSEEAnalysis instance."""
        return BSEEAnalysis()
    
    @pytest.mark.parametrize("cfg,expected_call", [
        ({'analysis': {'flag': True}}, True),
        ({'analysis': {'flag': False}}, False),
        ({'analysis': {}}, False),
        ({}, False),
        ({'other': 'data'}, False),
    ])
    def test_router_analysis_flag_variations(self, analysis, cfg, expected_call):
        """Test router with various analysis flag configurations."""
        data = {'test': 'data'}
        
        with patch.object(analysis, 'run_analysis_for_all_wells') as mock_run:
            mock_run.return_value = cfg
            
            result = analysis.router(cfg, data)
            
            assert result == cfg
            if expected_call:
                mock_run.assert_called_once_with(cfg, data)
            else:
                mock_run.assert_not_called()
    
    @pytest.mark.parametrize("api12,expected_matches", [
        (['123456789012'], 1),
        (['123456789012', '234567890123'], 2),
        (['999999999999'], 0),
        ([], 0),
    ])
    @patch('worldenergydata.bsee.analysis.bsee_analysis.well_api12_analysis')
    @patch('worldenergydata.bsee.analysis.bsee_analysis.logger')
    def test_production_date_matching(self, mock_logger, mock_well_api12, analysis, api12, expected_matches):
        """Test production date matching with various API12 values."""
        # Mock save_result_groups to avoid file operations
        mock_well_api12.save_result_groups = Mock()
        
        well_groups = {
            'well_summary_df_groups': pd.DataFrame({
                'API12': ['123456789012', '234567890123'],
                'WELL_NAME': ['WELL-1', 'WELL-2']
            })
        }
        
        prod_data = []
        for api in api12:
            prod_data.append({
                'API12': api,
                'START_PRODUCTION_DATE': '2020-01-01',
                'LAST_PRODUCTION_DATE': '2023-12-31'
            })
        
        prod_groups = {
            'production_summary_df_groups': pd.DataFrame(prod_data) if prod_data else pd.DataFrame()
        }
        
        if not prod_data:
            prod_groups['production_summary_df_groups'] = pd.DataFrame()
            
        cfg = {}
        analysis.add_production_dates_to_well_summary(cfg, well_groups, prod_groups)
        
        if prod_data:
            # Check number of matches logged
            info_calls = [call for call in mock_logger.info.call_args_list 
                         if 'Total matches found' in str(call)]
            if info_calls:
                assert f"{expected_matches} out of" in str(info_calls[0])


@smoke
@unit
class TestBSEEAnalysisSmoke:
    """Smoke tests for BSEEAnalysis module."""
    
    def test_module_imports(self):
        """Test that BSEEAnalysis module can be imported."""
        from worldenergydata.bsee.analysis import bsee_analysis
        assert bsee_analysis.BSEEAnalysis is not None
    
    def test_global_objects_initialized(self):
        """Test that global objects are initialized."""
        from worldenergydata.bsee.analysis import bsee_analysis
        assert bsee_analysis.bsee_data is not None
        assert bsee_analysis.well_api12_analysis is not None
        assert bsee_analysis.well_api10_analysis is not None
        assert bsee_analysis.prod_api12_analysis is not None
        assert bsee_analysis.prod_api10_analysis is not None
    
    def test_class_instantiation(self):
        """Test that BSEEAnalysis class can be instantiated."""
        analysis = BSEEAnalysis()
        assert analysis is not None
        assert hasattr(analysis, 'router')
        assert hasattr(analysis, 'run_analysis_for_all_wells')
        assert hasattr(analysis, 'add_production_dates_to_well_summary')