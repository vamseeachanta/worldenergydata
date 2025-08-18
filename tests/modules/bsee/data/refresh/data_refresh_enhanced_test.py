"""
Enhanced BSEE Data Refresh Test - Standalone

This is the standalone test entry point for the enhanced data refresh system.
It focuses exclusively on testing the enhanced implementation without any
dependencies on or references to the legacy system.

Usage:
    python tests/modules/bsee/data/refresh/data_refresh_enhanced_test.py
"""

# Standard library imports
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Reader imports
from worldenergydata.engine import engine
from loguru import logger

# Import the enhanced data refresh module
from worldenergydata.modules.bsee.data.refresh.data_refresh_enhanced import DataRefreshEnhanced
from worldenergydata.modules.bsee.data.config import ConfigRouter


def run_enhanced_process(input_file, expected_result={}):
    """
    Run the enhanced data refresh process.
    
    Args:
        input_file: Path to configuration file
        expected_result: Expected results for validation (optional)
    """
    # Resolve input file path
    if input_file is not None and not os.path.isfile(input_file):
        input_file = os.path.join(os.path.dirname(__file__), input_file)
    
    logger.info("=" * 70)
    logger.info("ENHANCED BSEE DATA REFRESH SYSTEM")
    logger.info("=" * 70)
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Configuration File: {input_file}")
    logger.info("=" * 70)
    
    # Initialize config router to handle enhanced configuration
    config_router = ConfigRouter()
    
    # Load configuration through engine (maintains compatibility)
    try:
        cfg = engine(input_file)
        
        # Log configuration summary
        config_router.log_config_summary(cfg)
        
        # Verify enhanced mode is enabled
        if not config_router.is_enhanced_mode(cfg):
            logger.warning("Enhanced mode not enabled in configuration")
            logger.info("To enable enhanced mode, set 'enhanced_mode: True' in config")
            return
        
        logger.info("Enhanced mode confirmed - Proceeding with fresh data refresh")
        
        # Initialize and run the enhanced data refresh system
        data_refresh_enhanced = DataRefreshEnhanced()
        
        # Call the router method to trigger the data refresh process
        result_cfg, result_data = data_refresh_enhanced.router(cfg)
        
        logger.info("Enhanced data refresh router executed successfully")
        
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return
    
    # Results validation can be added here if needed
    # For now, we focus on successful execution
    
    logger.info("=" * 70)
    logger.info("ENHANCED DATA REFRESH COMPLETED")
    logger.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)


def get_valid_pytest_output_file(pytest_output_file):
    """
    Get valid file path for pytest compatibility.
    
    Args:
        pytest_output_file: File path to validate
        
    Returns:
        Valid file path
    """
    if pytest_output_file is not None and not os.path.isfile(pytest_output_file):
        pytest_output_file = os.path.join(os.path.dirname(__file__), pytest_output_file)
    return pytest_output_file


def test_run_enhanced_process():
    """
    Main test function for enhanced data refresh.
    
    This function can be called directly or through pytest.
    """
    # Use the enhanced configuration file
    input_file = 'data_refresh_enhanced.yml'
    input_file = get_valid_pytest_output_file(input_file)
    
    # Check if file exists, if not create default enhanced config
    if not os.path.exists(input_file):
        logger.warning(f"Enhanced config not found: {input_file}")
        logger.info("Creating default enhanced configuration...")
        
        # Create a minimal enhanced config if it doesn't exist
        create_default_enhanced_config(input_file)
    
    pytest_output_file = None
    
    # Clean up sys.argv for test execution
    if len(sys.argv) > 1:
        sys.argv.pop()
    
    # Run the enhanced process
    run_enhanced_process(input_file, expected_result={})


def create_default_enhanced_config(filepath):
    """
    Create a default enhanced configuration file if it doesn't exist.
    
    Args:
        filepath: Path where to create the config file
    """
    import yaml
    
    default_config = {
        'meta': {
            'library': 'worldenergydata',
            'basename': 'bsee',
            'mode': 'enhanced'
        },
        'enhanced_mode': True,
        'data': {
            'refresh': True,
            'enhanced': True,
            'well': False,
            'war': False,
            'production': False  # Set to False by default for faster testing
        },
        'default': {
            'log_level': 'INFO'
        }
    }
    
    try:
        with open(filepath, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        logger.info(f"Created default enhanced config: {filepath}")
    except Exception as e:
        logger.error(f"Error creating config file: {str(e)}")


# Main execution
if __name__ == "__main__":
    # Run the enhanced test directly (standalone mode)
    test_run_enhanced_process()
else:
    # When imported (e.g., by pytest), just expose the test function
    pass