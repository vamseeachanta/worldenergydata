import os
from copy import deepcopy

import pandas as pd
from assetutilities.common.utilities import is_dir_valid_func

from worldenergydata.bsee.data.sources.bin.lease_data import LeaseData


class DataFromLocalFiles:

    def __init__(self):
        self._lease_data = LeaseData()

    def router(self, cfg):
        cfg, lease_data_groups = self.get_lease_data_groups(cfg)

        return cfg, lease_data_groups

    def get_lease_data_groups(self, cfg):

        cfg = self.get_lease_data_from_local_files(cfg)

        lease_data_groups = []
        for group in cfg[cfg["basename"]]["data"]["groups"]:
            lease_data_group = group.copy()
            lease_array = group["bottom_lease"]["number"]
            lease_array_well_data = []
            for lease in lease_array:
                lease_df = self.get_cfg_df(group)

            lease_data_group.update({"lease_df": lease_df})

            lease_array_well_data.append(lease_data_group)

        lease_data_groups.append(lease_array_well_data)

        return cfg, lease_data_groups

    def get_cfg_df(self, group):

        cfg_lease_df = pd.read_csv(group["file_name"], low_memory=False)
        return cfg_lease_df

    def get_lease_data_from_local_files(self, cfg):

        groups = cfg[cfg["basename"]]["data"]["groups"]

        lease_group_data = []
        for group_idx in range(len(groups)):
            group = groups[group_idx]
            self._lease_data.router(cfg, group)
            lease_metadata = self.generate_output_item(cfg, group)

            lease_group_data.append(lease_metadata)
            lease_df = pd.read_csv(lease_metadata["file_name"], low_memory=False)
            api12_list = lease_df["API_WELL_NUMBER"].dropna().unique().tolist()
            lease_metadata["api12"] = api12_list

            cfg[cfg["basename"]]["data"]["groups"][group_idx] = lease_metadata

        return cfg

    def generate_output_item(self, cfg, input_item):

        lease_num = (
            str(input_item["bottom_lease"]["number"])
            if "bottom_lease" in input_item
            and input_item["bottom_lease"]["number"] is not None
            else ""
        )
        label = "lease_" + lease_num
        output_path = os.path.join(cfg["Analysis"]["result_folder"], "Data")
        if output_path is None:
            result_folder = cfg["Analysis"]["result_folder"]
            output_path = os.path.join(result_folder, "Data")

        analysis_root_folder = cfg["Analysis"]["analysis_root_folder"]
        is_dir_valid, output_path = is_dir_valid_func(output_path, analysis_root_folder)

        output_file = os.path.join(output_path, str(label) + ".csv")

        input_item_csv_cfg = deepcopy(input_item)
        input_item_csv_cfg.update({"label": label, "file_name": output_file})

        return input_item_csv_cfg
