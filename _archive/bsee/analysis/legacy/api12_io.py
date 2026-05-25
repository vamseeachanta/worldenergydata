# Standard library imports
import os

# Third party imports
import pandas as pd
from assetutilities.common.data import SaveData

save_data = SaveData()


class ProductionResultSaver:
    """Handles saving production analysis results to files."""

    def save_result_group(
        self, cfg: dict, group_idx: int, production_analysis_df_group: pd.DataFrame
    ) -> None:
        """
        Save production analysis results for a single group.

        Args:
            cfg: Configuration dictionary with result folder path
            group_idx: Index of the group being saved
            production_analysis_df_group: DataFrame to save
        """
        cfg_group = cfg["data"]["groups"][group_idx]
        block_number = None
        block_area = None
        bottom_block = cfg_group.get("bottom_block", None)

        if bottom_block is not None:
            block_number = bottom_block.get("number", None)
            block_area = bottom_block.get("area", None)

        if block_number is None:
            group_label = str(group_idx)
        else:
            group_label = block_area + "_" + str(block_number)

        file_label = "prod_all_block_" + group_label
        file_name = os.path.join(cfg["Analysis"]["result_folder"], file_label + ".csv")
        production_analysis_df_group.to_csv(file_name, index=False)

    def save_result_groups(
        self,
        cfg: dict,
        api12_array_groups: list,
        production_df_api12s: list,
        production_summary_df_groups: pd.DataFrame,
        prod_rate_bopd_groups: pd.DataFrame,
        prod_cumulative_mmbbl_groups: pd.DataFrame,
    ) -> None:
        """
        Save all production analysis results for multiple groups.

        Args:
            cfg: Configuration dictionary
            api12_array_groups: List of API12 identifiers
            production_df_api12s: List of DataFrames with raw production data
            production_summary_df_groups: Summary DataFrame for all groups
            prod_rate_bopd_groups: Production rate DataFrame
            prod_cumulative_mmbbl_groups: Cumulative production DataFrame
        """
        groups_label = cfg["meta"].get("label", None)
        if groups_label is None:
            groups_label = cfg["Analysis"]["file_name_for_overwrite"]

        result_folder = cfg["Analysis"]["result_folder"]

        # Save raw production data as Excel with multiple sheets
        file_label = "prod_raw_" + groups_label
        sheet_names = [str(item) for item in api12_array_groups]
        file_name = os.path.join(result_folder, file_label + ".xlsx")
        cfg_xlsx = {
            "FileName": file_name,
            "SheetNames": sheet_names,
            "thin_border": True,
        }
        save_data.DataFrameArray_To_xlsx_openpyxl(production_df_api12s, cfg_xlsx)

        # Save summary DataFrame
        file_label = "prod_summ_" + groups_label
        file_name = os.path.join(result_folder, file_label + ".csv")
        production_summary_df_groups.to_csv(file_name, index=False)

        # Save production rate DataFrame
        file_label = "prod_rate_bopd_" + groups_label
        file_name = os.path.join(result_folder, file_label + ".csv")
        prod_rate_bopd_groups.to_csv(file_name, index=False)

        # Save cumulative production DataFrame
        file_label = "prod_cumulative_mmbbl_" + groups_label
        file_name = os.path.join(result_folder, file_label + ".csv")
        prod_cumulative_mmbbl_groups.to_csv(file_name, index=False)
