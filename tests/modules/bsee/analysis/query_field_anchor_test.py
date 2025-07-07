import os
import sys
import logging

from assetutilities.common.yml_utilities import ymlInput

from worldenergydata.engine import engine


def run_application(input_file, expected_result={}):
    """
    Run the application with the given input file and validate results.
    
    Args:
        input_file (str): Path to the YAML configuration file
        expected_result (dict): Expected results for validation
        
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
        logging.error(f"Failed to execute engine with {input_file}: {str(e)}")
        raise


def get_valid_pytest_output_file(pytest_output_file):
    """Get valid pytest output file path."""
    if pytest_output_file is not None and not os.path.isfile(
            pytest_output_file):
        pytest_output_file = os.path.join(os.path.dirname(__file__),
                                          pytest_output_file)
    return pytest_output_file


def validate_anchor_field_config(cfg):
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
    
    # Validate analysis settings
    assert cfg['analysis']['flag'] is True, "Analysis flag should be enabled"
    
    logging.info("Anchor field configuration validation passed")
    return True


def test_application():
    """
    Test the Anchor field query application.
    
    This test addresses GitHub issue #39 by implementing proper validation
    and error handling for field query operations.
    """
    input_file = 'query_field_anchor.yml'

    # pytest_output_file = get_valid_pytest_output_file(pytest_output_file)
    # expected_result = ymlInput(pytest_output_file, updateYml=None)

    if len(sys.argv) > 1:
        sys.argv.pop()

    try:
        # Run the application and get configuration
        cfg = run_application(input_file, expected_result={})
        
        # Validate the configuration for Anchor field
        validate_anchor_field_config(cfg)
        
        logging.info("Anchor field test completed successfully")
        
    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        raise


def test_anchor_field_block_validation():
    """
    Test specific validation for Anchor field block GC807.
    """
    input_file = 'query_field_anchor.yml'
    
    # Load configuration directly
    if not os.path.isfile(input_file):
        input_file = os.path.join(os.path.dirname(__file__), input_file)
    
    cfg_data = ymlInput(input_file, updateYml=None)
    
    # Test block configuration
    block_config = cfg_data['data']['groups'][0]['bottom_block']
    assert block_config['area'] == 'GC', "Expected Green Canyon (GC) area"
    assert block_config['number'] == 807, "Expected block number 807"
    
    logging.info("Anchor field block validation passed")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    test_application()
    test_anchor_field_block_validation()
