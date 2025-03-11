import pytest
import deepdiff
import os
import sys

from assetutilities.common.yml_utilities import ymlInput

from energydata.engine import engine


def run_application(input_file, expected_result={}):
    if input_file is not None and not os.path.isfile(input_file):
        input_file = os.path.join(os.path.dirname(__file__), input_file)
    cfg = engine(input_file)


def get_valid_pytest_output_file(pytest_output_file):
    if pytest_output_file is not None and not os.path.isfile(
            pytest_output_file):
        pytest_output_file = os.path.join(os.path.dirname(__file__),
                                          pytest_output_file)
    return pytest_output_file


def test_application():

    # Well Analysis Tests
    input_file = 'query_api_01_wells_basic.yml'
    #input_file = 'query_api_02_wells_basic.yml'

    # Well Data Tests
    # input_file = 'query_api_01_wells_basic.yml'
    # input_file = 'query_api_04_well_data.yml'

    # Well Production Tests
    # input_file = 'query_api_01_wells_production.yml'
    
    #input_file = 'query_api_01_production_basic.yml'

    # input_file = 'query_api_01_block_basic.yml'


    # All well data
    # input_file = 'query_blk_julia.yml'


    pytest_output_file = None
    # pytest_output_file = get_valid_pytest_output_file(pytest_output_file)
    # expected_result = ymlInput(pytest_output_file, updateYml=None)

    if len(sys.argv) > 1:
        sys.argv.pop()

    run_application(input_file, expected_result={})


test_application()