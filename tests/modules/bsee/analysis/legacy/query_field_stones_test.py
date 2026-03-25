import deepdiff
import pytest

DEEPDIFF_AVAILABLE = True
import os
import sys

from assetutilities.common.yml_utilities import ymlInput

from worldenergydata.engine import engine

ENGINE_AVAILABLE = True


def run_application(input_file, expected_result={}):
    if input_file is not None and not os.path.isfile(input_file):
        input_file = os.path.join(os.path.dirname(__file__), input_file)

    if not ENGINE_AVAILABLE:
        pytest.skip("Engine not available - dependencies missing")

    cfg = engine(input_file)


def get_valid_pytest_output_file(pytest_output_file):
    if pytest_output_file is not None and not os.path.isfile(pytest_output_file):
        pytest_output_file = os.path.join(os.path.dirname(__file__), pytest_output_file)
    return pytest_output_file


def test_application():

    input_file = "query_field_stones.yml"

    pytest_output_file = None
    # pytest_output_file = get_valid_pytest_output_file(pytest_output_file)
    # expected_result = ymlInput(pytest_output_file, updateYml=None)

    if len(sys.argv) > 1:
        sys.argv.pop()

    run_application(input_file, expected_result={})


if __name__ == "__main__":
    test_application()
