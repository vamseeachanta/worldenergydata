import logging
import os
import pickle

from assetutilities.common.yml_utilities import WorkingWithYAML  # noqa
from assetutilities.modules.zip_utilities.zip_files_to_dataframe import ZipFilestoDf

logger = logging.getLogger(__name__)

wwy = WorkingWithYAML()
zip_files_to_df = ZipFilestoDf()


class APMData:

    def __init__(self, cfg):
        self.load_bin_data(cfg)

    def load_bin_data(self, cfg):
        folder_path_bin = cfg["parameters"]["filepath"]["apm"]["bin"]
        library_name = "worldenergydata"
        library_file_cfg = {"filepath": folder_path_bin, "library_name": library_name}
        folder_path_bin = wwy.get_library_filepath(
            library_file_cfg, src_relative_location_flag=False
        )

        self.apm_data = {}
        if not os.path.isdir(folder_path_bin) or not os.listdir(folder_path_bin):
            logger.warning(
                "BSEE data not found: %s. Run: python3 scripts/refresh_bsee_all.py",
                folder_path_bin,
            )
            return

        for file_name in os.listdir(folder_path_bin):
            file_name_with_path = os.path.join(folder_path_bin, file_name)
            file_name_without_extension, extension = os.path.splitext(file_name)
            try:
                with open(file_name_with_path, "rb") as file:
                    df = pickle.load(file)  # nosec B301 - trusted pipeline-generated local .bin/.pkl (BSEE), not untrusted input
                    self.apm_data[file_name_without_extension] = df
            except (FileNotFoundError, OSError) as e:
                logger.warning("Failed to load %s: %s", file_name_with_path, e)

    def get_apm_data(self, cfg, api12_metadata):
        api12_metadata["api12"][0]
