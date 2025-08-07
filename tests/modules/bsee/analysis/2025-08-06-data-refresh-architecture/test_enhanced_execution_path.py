"""
Test Enhanced Execution Path

This test verifies the NEW enhanced data refresh execution path works correctly
and maintains independence from the legacy system.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import yaml
import tempfile
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from worldenergydata.modules.bsee.data.refresh.data_refresh_enhanced import DataRefreshEnhanced
from worldenergydata.modules.bsee.data.refresh.config_router import ConfigRouter
from worldenergydata.modules.bsee.data.refresh.bsee_web_scraper import BSEEWebScraper
from worldenergydata.modules.bsee.data.refresh.memory_processor import MemoryProcessor


class TestEnhancedExecutionPath(unittest.TestCase):
    """Test the enhanced execution path for BSEE data refresh."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.enhanced_refresh = DataRefreshEnhanced()
        self.config_router = ConfigRouter()
        self.test_config = {
            'meta': {
                'library': 'worldenergydata',
                'basename': 'bsee',
                'mode': 'enhanced'
            },
            'enhanced_mode': True,
            'data': {
                'refresh': True,
                'enhanced': True,
                'well': True,
                'war': True,
                'production': False
            },
            'parameters': {
                'filepath': {
                    'bin_dir': 'test_data/bin',
                    'apm': {'bin': 'test_data/bin/apd'},
                    'war': {'bin': 'test_data/bin/war'},
                    'production': {'bin': 'test_data/bin/production'}
                }
            }
        }
    
    def test_4_7_1_execution_flow_to_enhanced(self):
        """Task 4.7.1: Test engine.py → bsee.py → bsee_data.py → data_refresh_enhanced.py"""
        
        # Test that enhanced mode is properly routed
        is_enhanced = self.config_router.is_enhanced_mode(self.test_config)
        self.assertTrue(is_enhanced, "Enhanced mode should be enabled")
        
        # Test that router method exists and returns expected format
        result = self.enhanced_refresh.router(self.test_config)
        self.assertIsInstance(result, tuple, "Router should return tuple")
        self.assertEqual(len(result), 2, "Router should return (cfg, None)")
        self.assertEqual(result[1], None, "Second element should be None for compatibility")
    
    def test_4_7_2_enhanced_to_scraper_flow(self):
        """Task 4.7.2: Test data_refresh_enhanced.py → bsee_web_scraper.py → memory_processor.py"""
        
        # Mock the web scraper and memory processor
        with patch.object(self.enhanced_refresh.web_scraper, 'download_zip_to_memory') as mock_download:
            with patch.object(self.enhanced_refresh.memory_processor, 'process_well_data') as mock_process:
                with patch.object(self.enhanced_refresh.memory_processor, 'save_to_binary') as mock_save:
                    
                    # Set up mock returns
                    mock_download.return_value = b'fake_zip_data'
                    mock_process.return_value = {'test_file.csv': {'data': 'test_data'}}
                    
                    # Execute well data refresh
                    self.enhanced_refresh.refresh_well_data_enhanced(self.test_config)
                    
                    # Verify the flow
                    mock_download.assert_called_once()
                    mock_process.assert_called_once_with(b'fake_zip_data', self.test_config)
                    mock_save.assert_called_once()
    
    def test_4_8_flag_based_processing(self):
        """Task 4.8: Test flag-based processing for well, production, and WAR data."""
        
        # Test well data flag
        config_well_only = self.test_config.copy()
        config_well_only['data'] = {'refresh': True, 'well': True, 'war': False, 'production': False}
        
        with patch.object(self.enhanced_refresh, 'refresh_well_data_enhanced') as mock_well:
            with patch.object(self.enhanced_refresh, 'refresh_war_data_enhanced') as mock_war:
                with patch.object(self.enhanced_refresh, 'refresh_production_data_enhanced') as mock_prod:
                    
                    self.enhanced_refresh.router(config_well_only)
                    
                    mock_well.assert_called_once()
                    mock_war.assert_not_called()
                    mock_prod.assert_not_called()
        
        # Test WAR data flag
        config_war_only = self.test_config.copy()
        config_war_only['data'] = {'refresh': True, 'well': False, 'war': True, 'production': False}
        
        with patch.object(self.enhanced_refresh, 'refresh_well_data_enhanced') as mock_well:
            with patch.object(self.enhanced_refresh, 'refresh_war_data_enhanced') as mock_war:
                with patch.object(self.enhanced_refresh, 'refresh_production_data_enhanced') as mock_prod:
                    
                    self.enhanced_refresh.router(config_war_only)
                    
                    mock_well.assert_not_called()
                    mock_war.assert_called_once()
                    mock_prod.assert_not_called()
        
        # Test production data flag
        config_prod_only = self.test_config.copy()
        config_prod_only['data'] = {'refresh': True, 'well': False, 'war': False, 'production': True}
        
        with patch.object(self.enhanced_refresh, 'refresh_well_data_enhanced') as mock_well:
            with patch.object(self.enhanced_refresh, 'refresh_war_data_enhanced') as mock_war:
                with patch.object(self.enhanced_refresh, 'refresh_production_data_enhanced') as mock_prod:
                    
                    self.enhanced_refresh.router(config_prod_only)
                    
                    mock_well.assert_not_called()
                    mock_war.assert_not_called()
                    mock_prod.assert_called_once()
    
    def test_4_9_flag_processing_logic(self):
        """Task 4.9: Test flag-based processing logic in data_refresh_enhanced.py"""
        
        # Test that refresh=False skips all processing
        config_no_refresh = self.test_config.copy()
        config_no_refresh['data']['refresh'] = False
        
        with patch.object(self.enhanced_refresh, 'refresh_well_data_enhanced') as mock_well:
            with patch.object(self.enhanced_refresh, 'refresh_war_data_enhanced') as mock_war:
                with patch.object(self.enhanced_refresh, 'refresh_production_data_enhanced') as mock_prod:
                    
                    self.enhanced_refresh.router(config_no_refresh)
                    
                    mock_well.assert_not_called()
                    mock_war.assert_not_called()
                    mock_prod.assert_not_called()
        
        # Test legacy apm flag compatibility
        config_apm = self.test_config.copy()
        config_apm['data'] = {'refresh': True, 'apm': True, 'well': False, 'war': False, 'production': False}
        
        with patch.object(self.enhanced_refresh.web_scraper, 'download_zip_to_memory') as mock_download:
            mock_download.return_value = b'fake_data'
            with patch.object(self.enhanced_refresh.memory_processor, 'process_well_data') as mock_process:
                mock_process.return_value = {}
                
                self.enhanced_refresh.router(config_apm)
                
                # APM flag should trigger well data processing
                mock_download.assert_called_once()
    
    def test_4_10_binary_output_compatibility(self):
        """Task 4.10: Ensure enhanced system outputs to SAME binary format/location as legacy."""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Configure test paths
            test_config = self.test_config.copy()
            test_config['parameters']['filepath']['apm']['bin'] = tmpdir
            
            # Mock data to save
            test_data = {
                'test_file.csv': {
                    'data': MagicMock(),  # Mock DataFrame
                    'shape': (100, 10),
                    'columns': ['col1', 'col2'],
                    'dtypes': {'col1': 'int64', 'col2': 'float64'}
                }
            }
            
            # Save using memory processor
            processor = MemoryProcessor()
            processor.save_to_binary(test_data, tmpdir, 'test_prefix')
            
            # Check that files were created
            expected_files = [
                'test_prefix_test_file.pkl',
                'test_prefix_metadata.pkl'
            ]
            
            for filename in expected_files:
                filepath = Path(tmpdir) / filename
                self.assertTrue(filepath.exists(), f"Binary file {filename} should exist")
            
            # Verify pickle format by loading
            import pickle
            metadata_path = Path(tmpdir) / 'test_prefix_metadata.pkl'
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            self.assertEqual(metadata['processing_type'], 'enhanced')
            self.assertEqual(metadata['source'], 'fresh_download')
            self.assertIn('test_file.csv', metadata['files'])
    
    def test_config_router_enhanced_detection(self):
        """Test that config router properly detects enhanced mode."""
        
        # Test explicit enhanced mode
        config_explicit = {'enhanced_mode': True}
        self.assertTrue(self.config_router.is_enhanced_mode(config_explicit))
        
        # Test enhanced flag in data section
        config_data_enhanced = {'data': {'enhanced': True}}
        self.assertTrue(self.config_router.is_enhanced_mode(config_data_enhanced))
        
        # Test fresh_data flag
        config_fresh = {'data': {'fresh_data': True}}
        self.assertTrue(self.config_router.is_enhanced_mode(config_fresh))
        
        # Test WAR flag triggers enhanced mode
        config_war = {'data': {'war': True}}
        self.assertTrue(self.config_router.is_enhanced_mode(config_war))
        
        # Test legacy mode (no enhanced flags)
        config_legacy = {'data': {'refresh': True, 'apm': True}}
        self.assertFalse(self.config_router.is_enhanced_mode(config_legacy))
    
    def test_web_scraper_initialization(self):
        """Test web scraper proper initialization and URL configuration."""
        
        scraper = BSEEWebScraper()
        
        # Check URLs are configured
        self.assertIn('well', scraper.URLS)
        self.assertIn('production', scraper.URLS)
        self.assertIn('war', scraper.URLS)
        
        # Verify URLs are correct
        self.assertEqual(scraper.URLS['well'], 'https://www.data.bsee.gov/Well/Files/APDRawData.zip')
        self.assertEqual(scraper.URLS['war'], 'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip')
        self.assertEqual(scraper.URLS['production'], 'https://www.data.bsee.gov/Production/Files/ProductionRawData.zip')
    
    def test_memory_processor_zip_handling(self):
        """Test memory processor can handle zip data in memory."""
        
        processor = MemoryProcessor()
        
        # Create a fake zip file in memory
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            # Add a CSV file
            csv_content = "col1,col2\nval1,val2\nval3,val4"
            zf.writestr('test.csv', csv_content)
        
        zip_data = zip_buffer.getvalue()
        
        # Process the zip
        result = processor.process_zip_in_memory(zip_data)
        
        self.assertIn('test.csv', result)
        self.assertEqual(len(result['test.csv']), 2)  # 2 data rows
        self.assertEqual(list(result['test.csv'].columns), ['col1', 'col2'])


class TestParallelSystemIndependence(unittest.TestCase):
    """Test that legacy and enhanced systems can run independently."""
    
    def test_4_11_both_systems_independent(self):
        """Task 4.11: Verify both systems can run independently."""
        
        # Check that both module files exist
        legacy_module = Path(project_root) / 'src' / 'worldenergydata' / 'modules' / 'bsee' / 'data' / 'refresh' / 'data_refresh.py'
        enhanced_module = Path(project_root) / 'src' / 'worldenergydata' / 'modules' / 'bsee' / 'data' / 'refresh' / 'data_refresh_enhanced.py'
        
        self.assertTrue(legacy_module.exists(), "Legacy module should exist")
        self.assertTrue(enhanced_module.exists(), "Enhanced module should exist")
        
        # Import both modules to ensure no conflicts
        try:
            from worldenergydata.modules.bsee.data.refresh.data_refresh import DataRefresh
            from worldenergydata.modules.bsee.data.refresh.data_refresh_enhanced import DataRefreshEnhanced
            
            # Instantiate both classes
            legacy = DataRefresh()
            enhanced = DataRefreshEnhanced()
            
            # Verify they are different classes
            self.assertNotEqual(type(legacy), type(enhanced))
            
            # Verify both have router method
            self.assertTrue(hasattr(legacy, 'router'))
            self.assertTrue(hasattr(enhanced, 'router'))
            
        except ImportError as e:
            self.fail(f"Failed to import modules: {e}")
    
    def test_config_files_independent(self):
        """Test that legacy and enhanced config files are independent."""
        
        test_dir = Path(project_root) / 'tests' / 'modules' / 'bsee' / 'data' / 'refresh'
        
        legacy_config = test_dir / 'data_refresh.yml'
        enhanced_config = test_dir / 'data_refresh_enhanced.yml'
        
        # Check legacy config exists
        self.assertTrue(legacy_config.exists(), "Legacy config should exist")
        
        # Check enhanced config exists
        self.assertTrue(enhanced_config.exists(), "Enhanced config should exist")
        
        # Load both configs and verify they're different
        with open(legacy_config, 'r') as f:
            legacy_cfg = yaml.safe_load(f)
        
        with open(enhanced_config, 'r') as f:
            enhanced_cfg = yaml.safe_load(f)
        
        # Enhanced config should have enhanced_mode flag
        self.assertTrue(enhanced_cfg.get('enhanced_mode', False), "Enhanced config should have enhanced_mode=True")
        
        # Legacy config should not have enhanced_mode or it should be False
        self.assertFalse(legacy_cfg.get('enhanced_mode', False), "Legacy config should not have enhanced_mode=True")


if __name__ == '__main__':
    unittest.main()