# Standard library imports
#import logging
from loguru import logger 
import os
import sys

# Third party imports
from assetutilities.common.data import (
    AttributeDict,  #noqa
    SaveData,
)
from assetutilities.common.file_management import FileManagement
from assetutilities.common.yml_utilities import ymlInput  #noqa

from assetutilities.common.ApplicationManager import ConfigureApplicationInputs

# Reader imports
from energydata.modules.bsee.bsee import bsee
from energydata.modules.zip_data_dwnld.zip_utils import zip_utils

save_data = SaveData()
library_name = "energydata"


def engine(inputfile: str = None, cfg: dict = None) -> dict:
    fm = FileManagement()
    if cfg is None:
        inputfile = validate_arguments_run_methods(inputfile)
        cfg = ymlInput(inputfile, updateYml=None)
        cfg = AttributeDict(cfg)
        if cfg is None:
            raise ValueError("cfg is None")

    basename = cfg["basename"]
    application_manager = ConfigureApplicationInputs(basename)
    application_manager.configure(cfg, library_name)
    cfg_base = application_manager.cfg
    cfg_base = fm.router(cfg_base)

    logger.info(f"{basename}, application ... START")


    if basename in ["bsee"]:
        bsee_app = bsee()
        cfg_base = bsee_app.router(cfg_base)
    
    elif basename in ["zip_utils"]:
        zip_utilities = zip_utils()
        cfg_base = zip_utilities.router(cfg_base)

    else:
        raise (Exception(f"Analysis for basename: {basename} not found. ... FAIL"))

    logger.info(f"{basename}, application ... END")
    save_cfg(cfg_base=cfg_base)

    return cfg_base


def validate_arguments_run_methods(inputfile):
    """
    Validate inputs for following run methods:
    - module (i.e. python -m digitalmodel input.yml)
    - from python file (i.e. )
    """

    if len(sys.argv) > 1 and inputfile is not None:
        raise (
            Exception(
                "2 Input files provided via arguments & function. Please provide only 1 file ... FAIL"
            )
        )

    if len(sys.argv) > 1:
        if not os.path.isfile(sys.argv[1]):
            raise (FileNotFoundError(f"Input file {sys.argv[1]} not found ... FAIL"))
        else:
            inputfile = sys.argv[1]

    if len(sys.argv) <= 1:
        if not os.path.isfile(inputfile):
            raise (FileNotFoundError(f"Input file {inputfile} not found ... FAIL"))
        else:
            sys.argv.append(inputfile)
    return inputfile


def save_cfg(cfg_base):
    output_dir = cfg_base.Analysis["analysis_root_folder"]

    filename = cfg_base.Analysis["file_name"]
    filename_path = os.path.join(output_dir, 'results', filename)

    save_data.saveDataYaml(cfg_base, filename_path, default_flow_style=False)
