# Standard library imports
import sys
from contextlib import contextmanager

from assetutilities.common.ApplicationManager import ConfigureApplicationInputs

# Third party imports
from assetutilities.common.data import (
    AttributeDict,  # noqa
    SaveData,
)
from assetutilities.common.file_management import FileManagement
from assetutilities.common.yml_utilities import WorkingWithYAML
from loguru import logger

# Reader imports — module-level so test doubles can patch
# worldenergydata.engine.bsee / worldenergydata.engine.zip
from worldenergydata.bsee.bsee import bsee
from worldenergydata.bsee.zip_data_dwnld.zip import zip

app_manager = ConfigureApplicationInputs()
save_data = SaveData()
wwyaml = WorkingWithYAML()

library_name = "worldenergydata"


@contextmanager
def _configure_argv_inputfile(inputfile):
    """Expose programmatic inputfile calls to legacy argv-based config merging."""
    if inputfile is None:
        yield
        return

    original_argv = sys.argv[:]
    if len(sys.argv) < 2 or sys.argv[1] != inputfile:
        sys.argv = [sys.argv[0], inputfile, *sys.argv[1:]]
    try:
        yield
    finally:
        sys.argv = original_argv


def engine(inputfile: str = None, cfg: dict = None, config_flag: bool = True) -> dict:
    cfg_argv_dict = {}
    if cfg is None:
        inputfile, cfg_argv_dict = app_manager.validate_arguments_run_methods(inputfile)
        cfg = wwyaml.ymlInput(inputfile, updateYml=None)
        cfg = AttributeDict(cfg)
        if cfg is None:
            raise ValueError("cfg is None")

    if "basename" in cfg:
        basename = cfg["basename"]
    elif "meta" in cfg:
        basename = cfg["meta"]["basename"]
    else:
        raise ValueError("basename not found in cfg")

    if config_flag:
        fm = FileManagement()
        if inputfile is None:
            cfg_base = app_manager.configure(cfg, library_name, basename, cfg_argv_dict)
        else:
            with _configure_argv_inputfile(inputfile):
                cfg_base = app_manager.configure(
                    cfg, library_name, basename, cfg_argv_dict, inputfile=inputfile
                )
        cfg_base = fm.router(cfg_base)
        result_folder_dict, cfg_base = app_manager.configure_result_folder(
            None, cfg_base
        )
    else:
        cfg_base = cfg

    logger.info(f"{basename}, application ... START")

    # try:
    if basename in ["bsee"]:
        bsee_app = bsee()
        cfg_base = bsee_app.router(cfg_base)

    elif basename in ["sodir"]:
        from worldenergydata.sodir.sodir import Sodir

        sodir_app = Sodir()
        cfg_base = sodir_app.router(cfg_base)

    elif basename in ["texas_rrc"]:
        from worldenergydata.texas_rrc.texas_rrc import TexasRRC

        texas_app = TexasRRC()
        cfg_base = texas_app.router(cfg_base)

    elif basename in ["canada"]:
        from worldenergydata.canada.canada import Canada

        canada_app = Canada()
        cfg_base = canada_app.router(cfg_base)

    elif basename in ["mexico_cnh"]:
        from worldenergydata.mexico_cnh.mexico_cnh import MexicoCNH

        mexico_app = MexicoCNH()
        cfg_base = mexico_app.router(cfg_base)

    elif basename in ["landman"]:
        from worldenergydata.landman.landman import Landman

        landman_app = Landman()
        cfg_base = landman_app.router(cfg_base)

    elif basename in ["fdas"]:
        from worldenergydata.fdas.fdas import FDAS

        fdas_app = FDAS()
        cfg_base = fdas_app.router(cfg_base)

    elif basename in ["pipeline_safety"]:
        from worldenergydata.pipeline_safety.pipeline_safety import PipelineSafety

        pipeline_safety_app = PipelineSafety()
        cfg_base = pipeline_safety_app.router(cfg_base)

    elif basename in ["production_forecast"]:
        from worldenergydata.production.forecast.router import ProductionForecast

        production_forecast_app = ProductionForecast()
        cfg_base = production_forecast_app.router(cfg_base)

    elif basename in ["marine_safety"]:
        from worldenergydata.marine_safety.marine_safety import MarineSafety

        marine_safety_app = MarineSafety()
        cfg_base = marine_safety_app.router(cfg_base)

    elif basename in ["dwnld_from_zipurl"]:
        dwnld_from_zipurl = zip()
        cfg_base = dwnld_from_zipurl.router(cfg_base)

    else:
        raise (Exception(f"Analysis for basename: {basename} not found. ... FAIL"))

    # except Exception as e:
    #     logger.error(f"Error in {basename} application: {e}")
    #     raise

    logger.info(f"{basename}, application ... END")
    app_manager.save_cfg(cfg_base=cfg_base)

    return cfg_base


if __name__ == "__main__":
    engine()
