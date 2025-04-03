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

from assetutilities.common.ApplicationManager import ConfigureApplicationInputs
from assetutilities.common.yml_utilities import WorkingWithYAML

# Reader imports
from energydata.modules.bsee.bsee import bsee
#from energydata.modules.bsee.data.bsee_data import BSEEData
from energydata.modules.bsee.zip_data_dwnld.zip import zip

app_manager = ConfigureApplicationInputs()
save_data = SaveData()
wwyaml = WorkingWithYAML()

library_name = "energydata"


def engine(inputfile: str = None, cfg: dict = None, config_flag: bool = True) -> dict:
    
    cfg_argv_dict = {}
    if cfg is None:
        inputfile, cfg_argv_dict = app_manager.validate_arguments_run_methods(inputfile)
        cfg = wwyaml.ymlInput(inputfile, updateYml=None)
        cfg = AttributeDict(cfg)
        if cfg is None:
            raise ValueError("cfg is None")

    if 'basename' in cfg:
        basename = cfg["basename"]
    elif 'meta' in cfg:
        basename = cfg["meta"]["basename"]
    else:
        raise ValueError("basename not found in cfg")

    if config_flag:
        fm = FileManagement()
        cfg_base = app_manager.configure(cfg, library_name, basename, cfg_argv_dict)
        cfg_base = fm.router(cfg_base)
        result_folder_dict, cfg_base = app_manager.configure_result_folder(None, cfg_base)
    else:
        cfg_base = cfg

    logger.info(f"{basename}, application ... START")

    if basename in ["bsee"]:
        bsee_app = bsee()
        cfg_base = bsee_app.router(cfg_base)
    
    # TODO relocate to Assetutilities
    elif basename in ["zip_utils"]:
        zip_utils = zip()
        cfg_base = zip_utils.router(cfg_base)

    else:
        raise (Exception(f"Analysis for basename: {basename} not found. ... FAIL"))

    logger.info(f"{basename}, application ... END")
    app_manager.save_cfg(cfg_base=cfg_base)

    return cfg_base

