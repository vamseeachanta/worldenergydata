import logging
import os

import pandas as pd
from assetutilities.common.yml_utilities import WorkingWithYAML

logger = logging.getLogger(__name__)


wwy = WorkingWithYAML()


class WARDataFromBin:

    def __init__(self):
        pass

    def router(self, cfg):
        cfg, block_data_groups = self.get_block_data_groups(cfg)

        return cfg, block_data_groups

    def get_block_data_groups(self, cfg):
        cfg = self.get_war_block_data_from_bin(cfg)

        block_data_groups = []
        for group in cfg[cfg["basename"]]["data"]["groups"]:
            block_data_group = group.copy()
            block_array_well_data = []

            block_array_well_data.append(block_data_group)

        block_data_groups.append(block_array_well_data)

        return cfg, block_data_groups

    def get_war_block_data_from_bin(self, cfg):

        bottom_block = cfg["data"]["groups"][0]["bottom_block"]["number"]
        area = cfg["data"]["groups"][0]["bottom_block"]["area"]
        mv_war_path = cfg["data"]["groups"][0]["war_main"]

        library_name = "worldenergydata"
        library_file_cfg = {"filepath": mv_war_path, "library_name": library_name}
        mv_war_path = wwy.get_library_filepath(
            library_file_cfg, src_relative_location_flag=False
        )
        mv_war_path = os.path.join(mv_war_path, "mv_war_main.bin")

        war_df = self.read_file(mv_war_path)

        unique_api12s = (
            war_df[
                (war_df["BOTM_BLOCK_NUM"] == str(bottom_block))
                & (war_df["BOTM_AREA_CODE"] == str(area))
            ]["API_WELL_NUMBER"]
            .unique()
            .tolist()
        )

        cfg[cfg["basename"]]["data"]["groups"][0]["api12"] = unique_api12s

        return cfg

    def read_file(self, filepath):
        try:
            df = pd.read_pickle(filepath)
        except (FileNotFoundError, OSError):
            logger.warning(
                "BSEE data not found: %s. Run: python3 scripts/refresh_bsee_all.py",
                filepath,
            )
            return pd.DataFrame()
        for column in df.select_dtypes(include="object"):
            df[column] = df[column].str.strip().str.strip('"')
        return df
