# Standard library imports
import os
import sys
# Reader imports
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
<<<<<<< HEAD:tests/modules/bsee/analysis/legacy_2025_02_21/test_apd_stmalo_by_block.py
    input_file = 'apd_stmalo_by_block.yml'
=======
    input_file = 'apd_jack_by_block.yml'
>>>>>>> 202502:tests/modules/bsee/analysis/legacy/test_apd_jack_by_block.py
    pytest_output_file = None
    # pytest_output_file = get_valid_pytest_output_file(pytest_output_file)
    # expected_result = ymlInput(pytest_output_file, updateYml=None)

    if len(sys.argv) > 1:
        sys.argv.pop()

    run_application(input_file, expected_result={})


test_application()