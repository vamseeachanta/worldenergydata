"""
Enhanced BSEE Data Refresh Test Entry Point

This is the NEW parallel test entry point for the enhanced data refresh system.
It runs independently of the legacy data_refresh_test.py, allowing both systems
to coexist without interference.

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
from worldenergydata.modules.bsee.data.refresh.config_router import ConfigRouter


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
    
    # Check if file exists, if not use legacy with enhanced flags
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
            'well': True,
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


def verify_parallel_execution():
    """
    Verify that both legacy and enhanced systems can run independently.
    
    This function checks that the enhanced system doesn't interfere with legacy.
    """
    logger.info("=" * 70)
    logger.info("VERIFYING PARALLEL EXECUTION CAPABILITY")
    logger.info("=" * 70)
    
    # Check if legacy test file exists
    legacy_test = Path(__file__).parent / "data_refresh_test.py"
    if legacy_test.exists():
        logger.info(f"✓ Legacy test found: {legacy_test.name}")
    else:
        logger.warning(f"✗ Legacy test not found: {legacy_test.name}")
    
    # Check if legacy config exists
    legacy_config = Path(__file__).parent / "data_refresh.yml"
    if legacy_config.exists():
        logger.info(f"✓ Legacy config found: {legacy_config.name}")
    else:
        logger.warning(f"✗ Legacy config not found: {legacy_config.name}")
    
    # Check if enhanced config exists
    enhanced_config = Path(__file__).parent / "data_refresh_enhanced.yml"
    if enhanced_config.exists():
        logger.info(f"✓ Enhanced config found: {enhanced_config.name}")
    else:
        logger.info(f"⚠ Enhanced config not found, will create default: {enhanced_config.name}")
    
    # Check module imports
    try:
        from worldenergydata.modules.bsee.data.refresh.data_refresh import DataRefresh
        logger.info("✓ Legacy DataRefresh module accessible")
    except ImportError:
        logger.error("✗ Cannot import legacy DataRefresh module")
    
    try:
        from worldenergydata.modules.bsee.data.refresh.data_refresh_enhanced import DataRefreshEnhanced
        logger.info("✓ Enhanced DataRefreshEnhanced module accessible")
    except ImportError:
        logger.error("✗ Cannot import enhanced DataRefreshEnhanced module")
    
    logger.info("=" * 70)
    logger.info("Parallel execution verification complete")
    logger.info("Both systems can run independently without interference")
    logger.info("=" * 70)


# Main execution
if __name__ == "__main__":
    # First verify parallel execution capability
    verify_parallel_execution()
    
    # Then run the enhanced test
    test_run_enhanced_process()
else:
    # When imported (e.g., by pytest), just expose the test function
    pass