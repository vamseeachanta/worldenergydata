import os
import sys
from loguru import logger
from typing import Dict, Any, Optional

from assetutilities.common.yml_utilities import ymlInput

from worldenergydata.engine import engine


def run_application(input_file: str) -> Dict[str, Any]:
    """
    Run the application with the given input file.
    
    Args:
        input_file (str): Path to the YAML configuration file
        
    Returns:
        dict: Configuration after processing
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        Exception: If engine execution fails
    """
    if input_file is not None and not os.path.isfile(input_file):
        input_file = os.path.join(os.path.dirname(__file__), input_file)
    
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Configuration file not found: {input_file}")
    
    try:
        cfg = engine(input_file)
        return cfg
    except Exception as e:
        logger.error(
            "Failed to execute engine with %s: %s", input_file, str(e)
        )
        raise


def get_valid_pytest_output_file(
    pytest_output_file: Optional[str]
) -> Optional[str]:
    """Get valid pytest output file path."""
    if pytest_output_file is not None and not os.path.isfile(
            pytest_output_file):
        pytest_output_file = os.path.join(os.path.dirname(__file__),
                                          pytest_output_file)
    return pytest_output_file


def validate_anchor_field_config(cfg: Dict[str, Any]) -> bool:
    """
    Validate that the Anchor field configuration is correct.
    
    Args:
        cfg (dict): Configuration dictionary
        
    Returns:
        bool: True if validation passes
        
    Raises:
        AssertionError: If validation fails
    """
    # Validate basic structure
    assert 'meta' in cfg, "Configuration missing 'meta' section"
    assert 'data' in cfg, "Configuration missing 'data' section"
    assert 'analysis' in cfg, "Configuration missing 'analysis' section"
    
    # Validate Anchor field specific settings
    assert cfg['meta']['label'] == 'goa_anchor', "Incorrect field label"
    block_config = cfg['data']['groups'][0]['bottom_block']
    assert block_config['area'] == 'GC', "Incorrect block area"
    assert block_config['number'] == 807, "Incorrect block number"
    
    # Validate analysis settings (can be True or False)
    assert 'flag' in cfg['analysis'], "Analysis flag setting missing"
    
    logger.info("Anchor field configuration validation passed")
    return True


def test_application() -> None:
    """
    Test the Anchor field query application.
    
    This test addresses GitHub issue #39 by implementing proper validation
    and error handling for field query operations.
    """
    # Use simplified config that doesn't trigger production data analysis
    input_file = 'query_field_anchor_simple.yml'

    if len(sys.argv) > 1:
        sys.argv.pop()

    try:
        # Run the application and get configuration
        cfg = run_application(input_file)
        
        # Validate the configuration for Anchor field
        validate_anchor_field_config(cfg)
        
        logger.info("Anchor field test completed successfully")
        
    except Exception as e:
        logger.error("Test failed: %s", str(e))
        raise


def test_anchor_field_block_validation() -> None:
    """
    Test specific validation for Anchor field block GC807.
    """
    # Test with the simplified config file
    input_file = 'query_field_anchor_simple.yml'
    
    # Load configuration directly
    if not os.path.isfile(input_file):
        input_file = os.path.join(os.path.dirname(__file__), input_file)
    
    cfg_data = ymlInput(input_file, updateYml=None)
    
    # Test block configuration
    block_config = cfg_data['data']['groups'][0]['bottom_block']
    assert block_config['area'] == 'GC', "Expected Green Canyon (GC) area"
    assert block_config['number'] == 807, "Expected block number 807"
    
    logger.info("Anchor field block validation passed")


def test_config_file_loading() -> None:
    """
    Test that both configuration files can be loaded without errors.
    """
    config_files = [
        'query_field_anchor.yml',
        'query_field_anchor_simple.yml'
    ]
    
    for config_file in config_files:
        file_path = config_file
        if not os.path.isfile(file_path):
            file_path = os.path.join(os.path.dirname(__file__), config_file)
        
        try:
            cfg_data = ymlInput(file_path, updateYml=None)
            assert cfg_data is not None, f"Failed to load {config_file}"
            assert 'meta' in cfg_data, f"Meta section missing in {config_file}"
            assert 'data' in cfg_data, f"Data section missing in {config_file}"
            logger.info("Successfully loaded and validated %s", config_file)
        except Exception as e:
            logger.error("Failed to load %s: %s", config_file, str(e))
            raise


if __name__ == "__main__":
    # Configure logger
    logger.basicConfig(level=logger.INFO)
    
    # Run tests
    try:
        test_config_file_loading()
        test_anchor_field_block_validation()
        test_application()
        logger.info("All tests passed successfully!")
    except Exception as e:
        logger.error("Test suite failed: %s", str(e))
        sys.exit(1)
