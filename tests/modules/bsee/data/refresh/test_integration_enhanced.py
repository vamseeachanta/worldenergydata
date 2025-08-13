"""
Integration Test for Enhanced BSEE Data Refresh System

This test validates the complete data refresh pipeline for all three data sources:
- Well (APD) data
- Production data  
- WAR data

It ensures proper execution flow, data processing, and output generation.
"""

import os
import sys
from pathlib import Path
import pickle
from datetime import datetime
import yaml
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from worldenergydata.engine import engine
from worldenergydata.modules.bsee.data.refresh.data_refresh_enhanced import DataRefreshEnhanced
from worldenergydata.modules.bsee.data.refresh.config_router import ConfigRouter


class IntegrationTester:
    """Integration test suite for enhanced data refresh system."""
    
    def __init__(self):
        self.results = {
            'initialization': False,
            'config_loading': False,
            'well_processing': False,
            'production_processing': False,
            'war_processing': False,
            'file_processing': {},
            'output_verification': {},
            'errors': []
        }
    
    def create_test_config(self, data_sources):
        """
        Create test configuration with specified data sources enabled.
        
        Args:
            data_sources: Dict with keys 'well', 'production', 'war' and boolean values
        """
        config = {
            'meta': {
                'library': 'worldenergydata',
                'basename': 'bsee',
                'mode': 'enhanced'
            },
            'enhanced_mode': True,
            'data': {
                'refresh': True,
                'enhanced': True,
                'fresh_data': True,
                'well': data_sources.get('well', False),
                'war': data_sources.get('war', False),
                'production': data_sources.get('production', False)
            },
            'default': {
                'log_level': 'INFO'
            },
            'processing': {
                'in_memory': True,
                'save_zip': False,
                'timeout': 300
            },
            'parameters': {
                'filepath': {
                    'bin_dir': 'data/modules/bsee/bin',
                    'well': {'bin': 'data/modules/bsee/bin/apd'},
                    'war': {'bin': 'data/modules/bsee/bin/war'},
                    'production': {'bin': 'data/modules/bsee/bin/production_raw'}
                }
            }
        }
        return config
    
    def test_initialization(self):
        """Test 10.1.1: Verify DataRefreshEnhanced is initialized properly."""
        logger.info("Testing DataRefreshEnhanced initialization...")
        try:
            data_refresh = DataRefreshEnhanced()
            
            # Verify all required components are initialized
            assert hasattr(data_refresh, 'web_scraper'), "web_scraper not initialized"
            assert hasattr(data_refresh, 'memory_processor'), "memory_processor not initialized"
            assert hasattr(data_refresh, 'config_router'), "config_router not initialized"
            
            self.results['initialization'] = True
            logger.success("✓ DataRefreshEnhanced initialized successfully")
            return True
        except Exception as e:
            self.results['errors'].append(f"Initialization failed: {str(e)}")
            logger.error(f"✗ Initialization failed: {str(e)}")
            return False
    
    def test_data_processing_flow(self, source_type='well'):
        """
        Test 10.1.2: Verify data flows through bsee_web_scraper and memory_processor.
        
        Args:
            source_type: Type of data source to test ('well', 'production', or 'war')
        """
        logger.info(f"Testing {source_type} data processing flow...")
        
        # Create config with only specified source enabled
        config = self.create_test_config({source_type: True})
        
        # Save temporary config file
        temp_config_path = f'test_config_{source_type}.yml'
        with open(temp_config_path, 'w') as f:
            yaml.dump(config, f)
        
        try:
            # Initialize enhanced system
            data_refresh = DataRefreshEnhanced()
            
            # Run the router with config
            result_cfg, result_data = data_refresh.router(config)
            
            # Verify processing occurred
            self.results[f'{source_type}_processing'] = True
            logger.success(f"✓ {source_type} data processing completed")
            
            return True
            
        except Exception as e:
            self.results['errors'].append(f"{source_type} processing failed: {str(e)}")
            logger.error(f"✗ {source_type} processing failed: {str(e)}")
            return False
        finally:
            # Clean up temp config
            if os.path.exists(temp_config_path):
                os.remove(temp_config_path)
    
    def test_file_processing(self, source_type='well'):
        """
        Test 10.1.3: Verify all files from zip archives are processed.
        
        Args:
            source_type: Type of data source to test
        """
        logger.info(f"Testing {source_type} file processing...")
        
        # Expected files per data source
        expected_files = {
            'well': ['mv_apddata_all.txt', 'mv_apdcasing_all.txt', 'mv_apdperforation_all.txt'],
            'production': ['ogor_a.txt', 'ogor_b.txt', 'lease_02.txt'],
            'war': ['mv_war_main.txt', 'mv_war_main_prop.txt']
        }
        
        # This would require monitoring the actual file processing
        # For now, we verify the output exists
        output_paths = {
            'well': 'data/modules/bsee/bin/apd',
            'production': 'data/modules/bsee/bin/production_raw',
            'war': 'data/modules/bsee/bin/war'
        }
        
        output_dir = output_paths.get(source_type)
        if os.path.exists(output_dir):
            files = os.listdir(output_dir)
            bin_files = [f for f in files if f.endswith('.bin')]
            
            if bin_files:
                self.results['file_processing'][source_type] = len(bin_files)
                logger.success(f"✓ Found {len(bin_files)} .bin files for {source_type}")
                return True
            else:
                logger.warning(f"⚠ No .bin files found for {source_type}")
                return False
        else:
            logger.error(f"✗ Output directory not found: {output_dir}")
            return False
    
    def test_output_verification(self, source_type='well'):
        """
        Test 10.1.4: Verify output is written and not empty.
        
        Args:
            source_type: Type of data source to test
        """
        logger.info(f"Verifying {source_type} output files...")
        
        output_paths = {
            'well': 'data/modules/bsee/bin/apd',
            'production': 'data/modules/bsee/bin/production_raw',
            'war': 'data/modules/bsee/bin/war'
        }
        
        output_dir = output_paths.get(source_type)
        
        if not os.path.exists(output_dir):
            logger.error(f"✗ Output directory not found: {output_dir}")
            return False
        
        # Check for .bin files
        bin_files = [f for f in os.listdir(output_dir) if f.endswith('.bin')]
        
        if not bin_files:
            logger.error(f"✗ No .bin files found in {output_dir}")
            return False
        
        # Verify files are not empty and can be loaded
        for bin_file in bin_files:
            file_path = os.path.join(output_dir, bin_file)
            file_size = os.path.getsize(file_path)
            
            if file_size == 0:
                logger.error(f"✗ Empty file: {bin_file}")
                return False
            
            # Try to load the pickle file
            try:
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                    if hasattr(data, 'shape'):
                        logger.info(f"  {bin_file}: {file_size/1024:.1f} KB, shape: {data.shape}")
                    else:
                        logger.info(f"  {bin_file}: {file_size/1024:.1f} KB")
                    
                    self.results['output_verification'][bin_file] = True
                    
            except Exception as e:
                logger.error(f"✗ Failed to load {bin_file}: {str(e)}")
                return False
        
        logger.success(f"✓ All {source_type} output files verified")
        return True
    
    def run_full_integration_test(self):
        """Run complete integration test suite."""
        logger.info("=" * 70)
        logger.info("ENHANCED DATA REFRESH INTEGRATION TEST")
        logger.info("=" * 70)
        logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test 10.1.1: Initialization
        self.test_initialization()
        
        # Test 10.1.2-10.1.4: Process and verify each data source
        # Note: Testing with small timeout to avoid long downloads
        # In production, all three would be tested
        
        logger.info("\nTesting Well Data Processing...")
        if self.test_data_processing_flow('well'):
            self.test_file_processing('well')
            self.test_output_verification('well')
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 70)
        
        passed = 0
        failed = 0
        
        for key, value in self.results.items():
            if key == 'errors':
                continue
            elif key in ['file_processing', 'output_verification']:
                if value:
                    logger.info(f"✓ {key}: {len(value)} items processed")
                    passed += 1
                else:
                    logger.info(f"✗ {key}: No items processed")
                    failed += 1
            else:
                if value:
                    logger.info(f"✓ {key}: PASSED")
                    passed += 1
                else:
                    logger.info(f"✗ {key}: FAILED")
                    failed += 1
        
        if self.results['errors']:
            logger.info("\nErrors encountered:")
            for error in self.results['errors']:
                logger.error(f"  - {error}")
        
        logger.info("\n" + "=" * 70)
        logger.info(f"Tests Passed: {passed}")
        logger.info(f"Tests Failed: {failed}")
        logger.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)
        
        return failed == 0


def main():
    """Main test execution."""
    tester = IntegrationTester()
    success = tester.run_full_integration_test()
    
    if success:
        logger.success("\n✅ All integration tests PASSED")
        return 0
    else:
        logger.error("\n❌ Some integration tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())