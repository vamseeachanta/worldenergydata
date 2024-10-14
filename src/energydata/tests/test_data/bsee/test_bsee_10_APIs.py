# Standard library imports
import os
import sys
import yaml
# Reader imports
from energydata.engine import engine


def run_application(input_file: str, api_config: dict):
    """
    Runs the engine with specified input file and additional API config.
    """
    # Load YAML if it's the primary configuration file
    with open(input_file, 'r') as file:
        cfg = yaml.safe_load(file)

    # Update the main configuration with the current API configuration
    cfg.update(api_config)

    # Pass both input file path and config dictionary to engine
    engine(inputfile=input_file)
   


def get_valid_pytest_output_file(pytest_output_file):

    if pytest_output_file is not None and not os.path.isfile(pytest_output_file):
        pytest_output_file = os.path.join(os.path.dirname(__file__), pytest_output_file)
    return pytest_output_file

def test_application():
    
    input_file = r'src\energydata\tests\test_data\bsee\bsee_10_APIs.yml'
    pytest_output_file = None

    with open(input_file, 'r') as file:
        config = yaml.safe_load(file)

    for api_config in config['input']:

        print(f"Running test for API: {api_config['label']} with well_api12: {api_config['Api14']}")

        # Run application for the current API configuration
        run_application(input_file, api_config)

    if len(sys.argv) > 1:
        sys.argv.pop()

    run_application(input_file, expected_result={})


test_application()