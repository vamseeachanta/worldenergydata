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

    # Comprehensive analysis
    #input_file = 'query_api_01_wells.yml' # SUCCESS

    # API12 analysis
    #input_file = 'query_api_01_wells_api12.yml'  # SUCCESS
    #input_file = 'query_api_03_wells_api12.yml'  # SUCCESS

    # Production Analysis
    #input_file = 'query_api_01_production.yml'  # SUCCESS
    #input_file = 'query_api_03_wells_production.yml' # CHECK

    input_file = 'query_api_01_block_api12.yml'  #TODO
    #input_file = 'query_api_03_blocks_api12.yml'  #TODO
 

    # All well data
    # input_file = 'query_blk_julia.yml'


    pytest_output_file = None
    # pytest_output_file = get_valid_pytest_output_file(pytest_output_file)
    # expected_result = ymlInput(pytest_output_file, updateYml=None)

    if len(sys.argv) > 1:
        sys.argv.pop()

    run_application(input_file, expected_result={})


test_application()