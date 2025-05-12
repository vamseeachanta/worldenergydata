import pytest
import deepdiff
import os
import sys

from assetutilities.common.yml_utilities import ymlInput

from worldenergydata.engine import engine


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

    # input_file = 'data_refresh.yml'
    
    # Well Data Tests
    # input_file = 'query_api_01_well_scrapy.yml'
    # input_file = 'query_api_04_wells_scrapy.yml'

    # Well Production Tests
    # input_file = 'query_api_production_from_zip_01_well.yml'
    # input_file = 'query_api_production_from_zip_04_wells.yml'

    # block tests
    # input_file = 'query_api_01_block_scrapy.yml'
    input_file = 'query_api_04_blocks_scrapy.yml'

    pytest_output_file = None
    # pytest_output_file = get_valid_pytest_output_file(pytest_output_file)
    # expected_result = ymlInput(pytest_output_file, updateYml=None)

    if len(sys.argv) > 1:
        sys.argv.pop()

    run_application(input_file, expected_result={})


test_application()