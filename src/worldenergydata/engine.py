# Standard library imports
import logging
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
from worldenergydata.modules.bsee.bsee import bsee
from worldenergydata.modules.bsee.zip_data_dwnld.zip import zip

app_manager = ConfigureApplicationInputs()
save_data = SaveData()
wwyaml = WorkingWithYAML()

library_name = "worldenergydata"


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

    logging.info(f"{basename}, application ... START")

    # try:
    if basename in ["bsee"]:
        bsee_app = bsee()
        cfg_base = bsee_app.router(cfg_base)

    elif basename in ["dwnld_from_zipurl"]:
        dwnld_from_zipurl = zip()
        cfg_base = dwnld_from_zipurl.router(cfg_base)

    else:
        raise (Exception(f"Analysis for basename: {basename} not found. ... FAIL"))

    # except Exception as e:
    #     logger.error(f"Error in {basename} application: {e}")
    #     raise

    logging.info(f"{basename}, application ... END")
    app_manager.save_cfg(cfg_base=cfg_base)

    return cfg_base

