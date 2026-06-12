# Standard library imports
import datetime
import json
import os

# Third party imports
import numpy as np
import pandas as pd
import plotly.express as px  # noqa: F401
import plotly.graph_objects as go  # noqa: F401
from assetutilities.common.data import SaveData
from assetutilities.common.visualization.visualization_templates_plotly import (
    VisualizationTemplatesPlotly,
)
from assetutilities.common.yml_utilities import WorkingWithYAML  # noqa
from loguru import logger

from worldenergydata.bsee.data.bsee_data import BSEEData
from worldenergydata.common.legacy.data import DateTimeUtility
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.core.financial import calculate_npv as fdas_calculate_npv
from worldenergydata.lower_tertiary.wti_prices import load_extended_wti_prices

# Backward-compatible module-level handle used by legacy tests and callers that
# patch ``worldenergydata.bsee.analysis.production_api12.save_data`` directly.
save_data = SaveData()


def _currency_to_float(value) -> float:
    """Parse currency-like values used by legacy API12 revenue tables."""
    if pd.isna(value) or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace("$", "").replace(",", "").strip() or 0.0)


def _production_month(value) -> pd.Timestamp:
    """Normalize BSEE PRODUCTION_DATE values such as 202401 to month start."""
    if isinstance(value, pd.Timestamp):
        return value.to_period("M").to_timestamp()
    if isinstance(value, datetime.datetime):
        return pd.Timestamp(value).to_period("M").to_timestamp()
    text = str(int(value)) if isinstance(value, (int, float)) else str(value)
    text = text.strip()
    if len(text) == 6 and text.isdigit():
        return pd.Timestamp(year=int(text[:4]), month=int(text[4:6]), day=1)
    return pd.to_datetime(text).to_period("M").to_timestamp()


class ProductionAPI12Analysis:
    """
    Production analysis for BSEE API12 well data.

    This class handles production data analysis, aggregation, and visualization
    for oil wells identified by API12 codes. It provides functionality for:
    - Well-level production analysis
    - Block and field level aggregations
    - Production rate and cumulative production tracking
    - Visualization of production trends

    Note: For revenue and NPV calculations, use the financial module at
    worldenergydata.bsee.analysis.financial
    """

    def __init__(self):
        self._wwy = WorkingWithYAML()
        self._viz_templates_plotly = VisualizationTemplatesPlotly()
        self._bsee_data = BSEEData()
        self._dtu = DateTimeUtility()
        self._save_data = SaveData()

    def router(self, cfg):
        return cfg

    def run_production_analysis(self, cfg, data):
        """
        Run production analysis on BSEE well data.

        Analyzes production data by well, block, and field levels.
        Generates production rate and cumulative production metrics.

        Args:
            cfg: Configuration dictionary
            data: Dictionary containing production data

        Returns:
            tuple: (cfg, groups_dict) with analysis results
        """
        logger.info("Starting production analysis...")
        production_groups = data.get("production_data", None)
        logger.info(f"Production groups found: {production_groups is not None}")
        groups_dict = {}
        if production_groups is None:
            logger.error("No production data found in the provided data.")

        production_summary_df_groups = pd.DataFrame()
        production_df_api12s = []
        prod_rate_bopd_groups = pd.DataFrame(columns=["PRODUCTION_DATETIME"])
        prod_cumulative_mmbbl_groups = pd.DataFrame(columns=["PRODUCTION_DATETIME"])
        api12_array_groups = []
        for group_idx, production_group in enumerate(production_groups):
            prod_rate_bopd_group = pd.DataFrame(columns=["PRODUCTION_DATETIME"])
            prod_cumulative_mmbbl_group = pd.DataFrame(columns=["PRODUCTION_DATETIME"])
            api12_array_group = cfg["data"]["groups"][group_idx]["api12"]
            api12_array_groups = api12_array_groups + api12_array_group

            for api12_idx, api12 in enumerate(api12_array_group):
                production_df_api12 = production_group[api12]

                _, production_analysis_dict_api12 = self.analyze_data_for_api12(
                    cfg, api12, production_df_api12
                )
                summary_df_api12 = production_analysis_dict_api12["summary_df_api12"]
                production_analysis_df_api12 = production_analysis_dict_api12[
                    "api12_df"
                ]

                production_df_api12s.append(production_analysis_df_api12)
                production_summary_df_groups = pd.concat(
                    [production_summary_df_groups, summary_df_api12], ignore_index=True
                )

                if not len(production_analysis_df_api12):
                    production_analysis_df_api12 = pd.DataFrame(
                        columns=[
                            "PRODUCTION_DATETIME",
                            "O_PROD_RATE_BOPD",
                            "O_CUMMULATIVE_PROD_MMBBL",
                        ]
                    )

                prod_rate_bopd_api12 = production_analysis_df_api12[
                    ["PRODUCTION_DATETIME", "O_PROD_RATE_BOPD"]
                ].rename(columns={"O_PROD_RATE_BOPD": api12})

                prod_rate_bopd_group = pd.merge(
                    prod_rate_bopd_group,
                    prod_rate_bopd_api12,
                    on=["PRODUCTION_DATETIME"],
                    how="outer",
                )

                prod_cumulative_mmbbl_api12 = production_analysis_df_api12[
                    ["PRODUCTION_DATETIME", "O_CUMMULATIVE_PROD_MMBBL"]
                ].rename(columns={"O_CUMMULATIVE_PROD_MMBBL": api12})
                prod_cumulative_mmbbl_group = pd.merge(
                    prod_cumulative_mmbbl_group,
                    prod_cumulative_mmbbl_api12,
                    on=["PRODUCTION_DATETIME"],
                    how="outer",
                )

            prod_rate_bopd_group = prod_rate_bopd_group.replace({np.nan: None})
            prod_rate_bopd_group.sort_values(by=["PRODUCTION_DATETIME"], inplace=True)
            prod_rate_bopd_group.reset_index(inplace=True, drop=True)

            prod_cumulative_mmbbl_group = prod_cumulative_mmbbl_group.replace(
                {np.nan: None}
            )
            prod_cumulative_mmbbl_group.sort_values(
                by=["PRODUCTION_DATETIME"], inplace=True
            )
            prod_cumulative_mmbbl_group.reset_index(inplace=True, drop=True)

            self.save_result_group(cfg, group_idx, prod_rate_bopd_group)

            prod_rate_bopd_groups = pd.merge(
                prod_rate_bopd_groups,
                prod_rate_bopd_group,
                on=["PRODUCTION_DATETIME"],
                how="outer",
            )
            self.pd_merge_clean_column_names(prod_rate_bopd_groups)
            prod_rate_bopd_groups = prod_rate_bopd_groups.replace({np.nan: None})
            prod_rate_bopd_groups.sort_values(by=["PRODUCTION_DATETIME"], inplace=True)
            prod_rate_bopd_groups.reset_index(inplace=True, drop=True)

            prod_cumulative_mmbbl_groups = pd.merge(
                prod_cumulative_mmbbl_groups,
                prod_cumulative_mmbbl_group,
                on=["PRODUCTION_DATETIME"],
                how="outer",
            )
            self.pd_merge_clean_column_names(prod_cumulative_mmbbl_groups)
            prod_cumulative_mmbbl_groups = prod_cumulative_mmbbl_groups.replace(
                {np.nan: None}
            )
            prod_cumulative_mmbbl_groups.sort_values(
                by=["PRODUCTION_DATETIME"], inplace=True
            )

            prod_cumulative_mmbbl_groups.reset_index(inplace=True, drop=True)

        production_analysis_dict_api12["api12_df"]

        self.save_result_groups(
            cfg,
            api12_array_groups,
            production_df_api12s,
            production_summary_df_groups,
            prod_rate_bopd_groups,
            prod_cumulative_mmbbl_groups,
        )

        # self.plot_production_rate_by_well(cfg, prod_rate_bopd_groups)
        # self.plot_prod_cumulative_mmbbl_by_well(cfg, prod_cumulative_mmbbl_groups)

        prod_cumulative_mmbbl_groups_by_block = self.convert_well_df_to_block_df(
            cfg, prod_cumulative_mmbbl_groups
        )
        # self.plot_prod_cumulative_mmbbl_by_block(cfg, prod_cumulative_mmbbl_groups_by_block)

        self.convert_block_to_field(prod_cumulative_mmbbl_groups_by_block)
        # self.plot_prod_cumulative_mmbbl_by_field(cfg, prod_cumulative_mmbbl_groups_by_field)

        groups_dict["production_df_api12s"] = production_df_api12s
        groups_dict["prod_rate_bopd_groups"] = prod_rate_bopd_groups
        groups_dict["prod_cumulative_mmbbl_groups"] = prod_cumulative_mmbbl_groups
        groups_dict["production_summary_df_groups"] = production_summary_df_groups

        return cfg, groups_dict

    def pd_merge_clean_column_names(self, merged_df):
        """Clean column names after pandas merge operation."""
        merged_df.columns = merged_df.columns.map(str)
        merged_df = merged_df.loc[:, ~merged_df.columns.str.endswith("_y")]
        merged_df.columns = merged_df.columns.str.replace("_x", "", regex=True)

        return merged_df

    def save_result_group(self, cfg, group_idx, production_analysis_df_group):
        """Save production analysis results for a group."""
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
        cfg,
        api12_array_groups,
        production_df_api12s,
        production_summary_df_groups,
        prod_rate_bopd_groups,
        prod_cumulative_mmbbl_groups,
    ):
        """Save production analysis results for all groups."""
        groups_label = cfg["meta"].get("label", None)
        if groups_label is None:
            groups_label = cfg["Analysis"]["file_name_for_overwrite"]

        file_label = "prod_raw_" + groups_label
        sheet_names = [str(item) for item in api12_array_groups]
        result_folder = cfg["Analysis"]["result_folder"]
        file_name = os.path.join(result_folder, file_label + ".xlsx")
        cfg_xlsx = {
            "FileName": file_name,
            "SheetNames": sheet_names,
            "thin_border": True,
        }
        self._save_data.DataFrameArray_To_xlsx_openpyxl(production_df_api12s, cfg_xlsx)

        file_label = "prod_summ_" + groups_label
        file_name = os.path.join(result_folder, file_label + ".csv")
        production_summary_df_groups.to_csv(file_name, index=False)
        json_file_name = os.path.join(result_folder, file_label + ".json")
        payload = {
            "records": production_summary_df_groups.to_dict(orient="records"),
            "totals": {
                "oil_bbl": float(
                    production_summary_df_groups["O_CUMMULATIVE_PROD_MMBBL"].sum()
                    * 1_000_000
                ),
                "days_on_prod": int(production_summary_df_groups["DAYS_ON_PROD"].sum()),
                "well_count": int(production_summary_df_groups["API12"].nunique()),
            },
        }
        with open(json_file_name, "w") as fp:
            json.dump(payload, fp, indent=2, default=str)

        file_label = "prod_rate_bopd_" + groups_label
        file_name = os.path.join(result_folder, file_label + ".csv")
        prod_rate_bopd_groups.to_csv(file_name, index=False)

        file_label = "prod_cumulative_mmbbl_" + groups_label
        file_name = os.path.join(result_folder, file_label + ".csv")
        prod_cumulative_mmbbl_groups.to_csv(file_name, index=False)

    def analyze_data_for_api12(self, cfg, api12, api12_df):
        """
        Analyze production data for a specific API12 well.

        Args:
            cfg: Configuration dictionary
            api12: API12 well identifier
            api12_df: DataFrame with production data for the well

        Returns:
            tuple: (cfg, production analysis dictionary)
        """
        api12_df_analyzed = api12_df.copy()
        summary_df_api12 = pd.DataFrame()
        completion_names = []
        if not api12_df.empty:
            completion_names = api12_df.COMPLETION_NAME.unique()

        for completion_name in completion_names:
            api12_df_analyzed = api12_df[
                api12_df.COMPLETION_NAME == completion_name
            ].copy()
            api12_df_analyzed = self.add_production_rate_and_date_to_df(
                cfg, api12_df_analyzed
            )
            api12_df_analyzed.sort_values(by=["PRODUCTION_DATETIME"], inplace=True)
            api12_df_analyzed.reset_index(inplace=True)
            if api12_df_analyzed.O_PROD_RATE_BOPD.max() > 0:
                summary_df_api12_by_completion_name = self.get_summary_df_api12(
                    api12, completion_name, api12_df_analyzed
                )
                summary_df_api12 = pd.concat(
                    [summary_df_api12, summary_df_api12_by_completion_name],
                    ignore_index=True,
                )

        prod_anal_api12_dict = {
            "api12_df": api12_df_analyzed,
            "api12": api12,
            "summary_df_api12": summary_df_api12,
            "completion_names": completion_names,
        }

        return cfg, prod_anal_api12_dict

    def get_summary_df_api12(self, well_api12, completion_name, api12_df):
        """Generate summary statistics for an API12 well."""
        columns = [
            "API12",
            "API10",
            "O_PROD_STATUS",
            "O_CUMMULATIVE_PROD_MMBBL",
            "DAYS_ON_PROD",
            "O_MEAN_PROD_RATE_BOPD",
            "COMPLETION_NAME",
            "START_PRODUCTION_DATE",
            "LAST_PRODUCTION_DATE",
        ]
        production_summary_df = pd.DataFrame(columns=columns)
        production_summary_df = production_summary_df.astype(
            {
                "API12": str,
                "API10": str,
                "O_PROD_STATUS": int,
                "O_CUMMULATIVE_PROD_MMBBL": float,
                "DAYS_ON_PROD": int,
                "O_MEAN_PROD_RATE_BOPD": float,
                "COMPLETION_NAME": str,
                "START_PRODUCTION_DATE": str,
                "LAST_PRODUCTION_DATE": str,
            }
        )

        well_api10 = str(well_api12)[0:10]
        values = [well_api12, well_api10, 0.0, 0.0, 0.0, 0.0, completion_name, "", ""]
        production_summary_df.loc[0] = values

        total_well_production = api12_df.MON_O_PROD_VOL.sum() / 1000 / 1000
        api12_production = api12_df[["PRODUCTION_DATETIME", "O_PROD_RATE_BOPD"]].copy()
        api12_production.rename(
            columns={"PRODUCTION_DATETIME": "date_time"}, inplace=True
        )
        api12_production = api12_production.round(decimals=3)
        api12_production["date_time"] = [
            item.strftime("%Y-%m-%d")
            for item in api12_production["date_time"].to_list()
        ]

        if len(api12_df) > 0 and total_well_production > 0:
            df_row_index = api12_df.index[0]

            current_value = production_summary_df.O_CUMMULATIVE_PROD_MMBBL.iloc[0]
            O_CUMMULATIVE_PROD_MMBBL = current_value + total_well_production
            production_summary_df.loc[df_row_index, "O_CUMMULATIVE_PROD_MMBBL"] = float(
                O_CUMMULATIVE_PROD_MMBBL
            )

            DAYS_ON_PROD = api12_df.DAYS_ON_PROD.sum()
            production_summary_df.loc[df_row_index, "DAYS_ON_PROD"] = DAYS_ON_PROD

            O_MEAN_PROD_RATE_BOPD = api12_df.MON_O_PROD_VOL.sum() / DAYS_ON_PROD
            production_summary_df.loc[df_row_index, "O_MEAN_PROD_RATE_BOPD"] = float(
                O_MEAN_PROD_RATE_BOPD
            )

            # Calculate start and last production dates
            production_dates_df = api12_df[api12_df.O_PROD_RATE_BOPD > 0]
            if len(production_dates_df) > 0:
                try:
                    start_production_date = (
                        production_dates_df.PRODUCTION_DATETIME.min().strftime(
                            "%Y-%m-%d"
                        )
                    )
                    last_production_date = (
                        production_dates_df.PRODUCTION_DATETIME.max().strftime(
                            "%Y-%m-%d"
                        )
                    )
                    production_summary_df.loc[df_row_index, "START_PRODUCTION_DATE"] = (
                        start_production_date
                    )
                    production_summary_df.loc[df_row_index, "LAST_PRODUCTION_DATE"] = (
                        last_production_date
                    )
                    logger.info(
                        f"Calculated production dates for API12 {well_api12}: {start_production_date} to {last_production_date}"  # noqa: E501
                    )
                except Exception as e:
                    logger.error(
                        f"Error calculating production dates for API12 {well_api12}: {e}"
                    )
                    production_summary_df.loc[df_row_index, "START_PRODUCTION_DATE"] = (
                        ""
                    )
                    production_summary_df.loc[df_row_index, "LAST_PRODUCTION_DATE"] = ""
            else:
                logger.warning(f"No production data found for API12 {well_api12}")
                production_summary_df.loc[df_row_index, "START_PRODUCTION_DATE"] = ""
                production_summary_df.loc[df_row_index, "LAST_PRODUCTION_DATE"] = ""

            production_summary_df.loc[df_row_index, "O_PROD_STATUS"] = 1

        return production_summary_df

    def add_production_rate_and_date_to_df(self, cfg, api12_df):
        """Add calculated production rate and datetime columns to dataframe."""
        production_date_time = []
        production_rate = []
        O_CUMMULATIVE_PROD_MMBBL_array = []
        for df_row in range(0, len(api12_df)):
            year = int(api12_df.PRODUCTION_DATE.iloc[df_row] / 100)
            month = api12_df.PRODUCTION_DATE.iloc[df_row] % year
            date_time = datetime.datetime(year, month, 1)
            date_time = self._dtu.last_day_of_month(date_time.date())
            if api12_df.DAYS_ON_PROD.iloc[df_row] != 0:
                rate = (
                    api12_df.MON_O_PROD_VOL.iloc[df_row]
                    / api12_df.DAYS_ON_PROD.iloc[df_row]
                )
            else:
                rate = 0
            production_date_time.append(date_time)
            production_rate.append(rate)
            O_CUMMULATIVE_PROD_MMBBL_previous_df_row = 0
            if len(O_CUMMULATIVE_PROD_MMBBL_array) > 0:
                O_CUMMULATIVE_PROD_MMBBL_previous_df_row = (
                    O_CUMMULATIVE_PROD_MMBBL_array[-1]
                )

            O_CUMMULATIVE_PROD_MMBBL = (
                api12_df.MON_O_PROD_VOL.iloc[df_row] / 1000 / 1000
                + O_CUMMULATIVE_PROD_MMBBL_previous_df_row
            )
            O_CUMMULATIVE_PROD_MMBBL_array.append(O_CUMMULATIVE_PROD_MMBBL)

        api12_df["PRODUCTION_DATETIME"] = production_date_time
        api12_df["O_PROD_RATE_BOPD"] = production_rate
        api12_df["O_CUMMULATIVE_PROD_MMBBL"] = O_CUMMULATIVE_PROD_MMBBL_array

        return api12_df

    def convert_well_df_to_block_df(self, cfg, df_api12: pd.DataFrame) -> pd.DataFrame:
        """
        Convert production DataFrame by well into production DataFrame by block.

        Args:
            cfg: Configuration dictionary
            df_api12: Input DataFrame with datetime and API12 columns.

        Returns:
            pd.DataFrame: New DataFrame with prod datetime and block production data.
        """
        datetime_col = df_api12.columns[0]
        block_to_api12s = self.extract_block_mapping(cfg)
        df_block = pd.DataFrame()
        df_block[datetime_col] = df_api12[datetime_col]

        for block, api12s_list in block_to_api12s.items():
            block_col_name = f"block_{block}"
            existing_api12s = [
                api12 for api12 in api12s_list if api12 in df_api12.columns
            ]
            if not existing_api12s:
                df_block[block_col_name] = 0
            else:
                df_block[block_col_name] = df_api12[existing_api12s].sum(axis=1)

        return df_block

    def extract_block_mapping(self, cfg):
        """Extract block to API12 well mapping from configuration."""
        mapping = {}
        for group in cfg.get("data", {}).get("groups", []):
            block_ids = []
            block_id = (
                group["bottom_block"].get("number")
                if group["bottom_block"] is not None
                else None
            )
            if block_id is not None:
                block_ids.append(block_id)
            api12s = group.get("api12", [])
            for block in block_ids:
                block_str = str(block)
                api12_strs = [str(api12) for api12 in api12s]
                mapping[block_str] = api12_strs
        return mapping

    def convert_block_to_field(self, df_block: pd.DataFrame) -> pd.DataFrame:
        """
        Convert block-level DataFrame to field-level DataFrame.

        Args:
            df_block: DataFrame with datetime and block columns.

        Returns:
            pd.DataFrame: New DataFrame with datetime and field column.
        """
        datetime_col = df_block.columns[0]
        field_df = pd.DataFrame()
        field_df[datetime_col] = df_block[datetime_col]

        block_columns = [col for col in df_block.columns if col.startswith("block_")]
        field_df["St Malo"] = df_block[block_columns].sum(axis=1)

        return field_df

    def plot_production_rate_by_well(self, cfg, prod_rates_df):
        """Plot production rates by well."""
        from assetutilities.engine import engine as au_engine

        plot_yml = self._viz_templates_plotly.get_xy_line_df(cfg["Analysis"].copy())

        plot_yml["data"]["groups"][0]["file_name"] = prod_rates_df
        groups_label = cfg["meta"].get("label", None)
        if groups_label is None:
            groups_label = cfg["Analysis"]["file_name_for_overwrite"]

        file_label = "prod_rate_by_well_" + groups_label
        result_folder = cfg["Analysis"]["result_folder"]
        file_name = os.path.join(result_folder, "Plot", file_label)

        settings = {
            "file_name": file_name,
            "title": "Production Data for API12",
            "xlabel": "PRODUCTION_DATETIME",
            "ylabel": "production",
            "columns_var_name": "api12",
            "customize_xdate_ticks": {
                "flag": True,
                "start_time": "2018-01-01",
                "end_time": "2025-04-03",
            },
        }
        plot_yml["settings"].update(settings)
        au_engine(inputfile=None, cfg=plot_yml, config_flag=False)

    def plot_prod_cumulative_mmbbl_by_well(self, cfg, prod_cumulative_mmbbl_groups):
        """Plot cumulative production by well."""
        from assetutilities.engine import engine as au_engine

        plot_yml = self._viz_templates_plotly.get_xy_line_df(cfg["Analysis"].copy())

        plot_yml["data"]["groups"][0]["file_name"] = prod_cumulative_mmbbl_groups
        groups_label = cfg["meta"].get("label", None)
        if groups_label is None:
            groups_label = cfg["Analysis"]["file_name_for_overwrite"]

        file_label = "prod_cumulative_mmbbl_by_well_" + groups_label
        result_folder = cfg["Analysis"]["result_folder"]
        file_name = os.path.join(result_folder, "Plot", file_label)

        settings = {
            "file_name": file_name,
            "title": "Cumulative Production by well",
            "xlabel": "PRODUCTION_DATETIME",
            "ylabel": "cumulative_production",
            "columns_var_name": "api12",
            "customize_xdate_ticks": {
                "flag": True,
                "start_time": "2010-01-01",
                "end_time": "2025-06-03",
            },
        }
        plot_yml["settings"].update(settings)
        au_engine(inputfile=None, cfg=plot_yml, config_flag=False)

    def plot_prod_cumulative_mmbbl_by_block(
        self, cfg, prod_cumulative_mmbbl_groups_by_block
    ):
        """Plot cumulative production by block."""
        from assetutilities.engine import engine as au_engine

        plot_yml = self._viz_templates_plotly.get_xy_line_df(cfg["Analysis"].copy())

        plot_yml["data"]["groups"][0][
            "file_name"
        ] = prod_cumulative_mmbbl_groups_by_block
        groups_label = cfg["meta"].get("label", None)
        if groups_label is None:
            groups_label = cfg["Analysis"]["file_name_for_overwrite"]

        file_label = "prod_cumulative_mmbbl_by_block_" + groups_label
        result_folder = cfg["Analysis"]["result_folder"]
        file_name = os.path.join(result_folder, "Plot", file_label)
        settings = {
            "file_name": file_name,
            "title": "Cumulative Production by block",
            "xlabel": "PRODUCTION_DATETIME",
            "ylabel": "cumulative_production",
            "columns_var_name": "block",
            "customize_xdate_ticks": {
                "flag": True,
                "start_time": "2015-01-01",
                "end_time": "2025-06-03",
            },
        }

        plot_yml["settings"].update(settings)
        au_engine(inputfile=None, cfg=plot_yml, config_flag=False)

    def plot_prod_cumulative_mmbbl_by_field(
        self, cfg, prod_cumulative_mmbbl_groups_by_field
    ):
        """Plot cumulative production by field."""
        from assetutilities.engine import engine as au_engine

        plot_yml = self._viz_templates_plotly.get_xy_line_df(cfg["Analysis"].copy())

        plot_yml["data"]["groups"][0][
            "file_name"
        ] = prod_cumulative_mmbbl_groups_by_field
        groups_label = cfg["meta"].get("label", None)
        if groups_label is None:
            groups_label = cfg["Analysis"]["file_name_for_overwrite"]

        file_label = "prod_cumulative_mmbbl_by_field_" + groups_label
        result_folder = cfg["Analysis"]["result_folder"]
        file_name = os.path.join(result_folder, "Plot", file_label)
        settings = {
            "file_name": file_name,
            "title": "Cumulative Production by field",
            "xlabel": "PRODUCTION_DATETIME",
            "ylabel": "cumulative_production",
            "columns_var_name": "field",
            "customize_xdate_ticks": {
                "flag": True,
                "start_time": "2013-01-01",
                "end_time": "2025-06-03",
            },
        }

        plot_yml["settings"].update(settings)
        au_engine(inputfile=None, cfg=plot_yml, config_flag=False)

    def generate_revenue_table(self, cfg, api12_df):
        """Generate API12 revenue from production and Lower Tertiary WTI prices."""
        revenue_df = self._generate_revenue_table_from_wti(cfg, api12_df)
        self.calculate_npv(cfg, revenue_df)
        return revenue_df

    def _generate_revenue_table_from_wti(self, cfg, api12_df):
        """Build a revenue table using the Lower Tertiary WTI price deck."""
        if api12_df.empty:
            return pd.DataFrame()

        production_df = api12_df.copy()
        production_df["Month_Timestamp"] = production_df["PRODUCTION_DATE"].apply(
            _production_month
        )
        max_month = production_df["Month_Timestamp"].max().strftime("%Y-%m-%d")
        prices_df = load_extended_wti_prices(through_date=max_month).copy()
        prices_df["Month_Timestamp"] = (
            prices_df["Month"].dt.to_period("M").dt.to_timestamp()
        )
        price_by_month = prices_df.set_index("Month_Timestamp")["WTI_USD"].to_dict()

        production_df["Monthly Oil Production"] = pd.to_numeric(
            production_df["MON_O_PROD_VOL"], errors="coerce"
        ).fillna(0.0)
        production_df["Avg Price (USD/bbl)"] = production_df["Month_Timestamp"].map(
            price_by_month
        )
        if production_df["Avg Price (USD/bbl)"].isna().any():
            missing = production_df.loc[
                production_df["Avg Price (USD/bbl)"].isna(), "Month_Timestamp"
            ]
            missing_months = ", ".join(item.strftime("%Y-%m") for item in missing)
            raise ValueError(
                f"Missing WTI prices for production months: {missing_months}"
            )

        production_df["Revenue (USD)"] = (
            production_df["Monthly Oil Production"]
            * production_df["Avg Price (USD/bbl)"]
        )

        df = pd.DataFrame(
            {
                "Month": production_df["PRODUCTION_DATE"].tolist(),
                "Monthly Oil Production": production_df[
                    "Monthly Oil Production"
                ].tolist(),
                "Avg Price (USD/bbl)": [
                    f"${price:,.2f}"
                    for price in production_df["Avg Price (USD/bbl)"].tolist()
                ],
                "Revenue (USD)": [
                    f"${revenue:,.2f}"
                    for revenue in production_df["Revenue (USD)"].tolist()
                ],
            }
        )

        total_row = {
            "Month": "",
            "Monthly Oil Production": "",
            "Avg Price (USD/bbl)": "",
            "Revenue (USD)": f"${production_df['Revenue (USD)'].sum():,.2f}",
        }
        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

        result_folder = cfg.get("Analysis", {}).get("result_folder")
        if result_folder:
            file_name = os.path.join(result_folder, "revenues_table.csv")
            df.to_csv(file_name, index=False)

        return df

    def _economic_assumptions(self, cfg, dev_system="default"):
        """Resolve FDAS assumptions plus legacy config overrides."""
        assumptions_df = cfg.get("fdas_assumptions")
        assumptions = (
            AssumptionsManager.from_dict(assumptions_df)
            if assumptions_df is not None
            else AssumptionsManager()
        )
        cost_cfg = cfg.get("economics", {}).get("cost", {})
        discount_rate = float(
            cost_cfg.get(
                "discount_rate_annual",
                assumptions.get(dev_system, "DISCOUNT_RATE_ANNUAL"),
            )
        )
        capex = float(
            cost_cfg.get(
                "CAPEX",
                assumptions.get(dev_system, "HOST_CAPEX_MM") * 1_000_000,
            )
        )
        opex = float(
            cost_cfg.get(
                "OPEX",
                assumptions.get(dev_system, "VARIABLE_OPEX_$/BBL"),
            )
        )
        return capex, opex, discount_rate

    def calculate_npv(self, cfg, revenue_df, dev_system="default", period="monthly"):
        """Calculate API12 NPV through the FDAS financial layer."""
        capex, opex_per_bbl, discount_rate = self._economic_assumptions(
            cfg, dev_system=dev_system
        )
        working = revenue_df.copy()
        if "Month" in working.columns:
            working = working[working["Month"].astype(str).str.strip() != ""]

        revenues = (
            working["Revenue (USD)"].apply(_currency_to_float).to_numpy(dtype=float)
        )
        production = pd.to_numeric(
            working["Monthly Oil Production"], errors="coerce"
        ).fillna(0.0)
        operating_cashflows = revenues - (
            production.to_numpy(dtype=float) * opex_per_bbl
        )
        cashflows = np.concatenate(
            (np.array([-capex], dtype=float), operating_cashflows)
        )
        return fdas_calculate_npv(cashflows, discount_rate, period=period)

    def perform_npv_calculation(self, cfg, revenue_df):
        """Backward-compatible wrapper around the FDAS API12 NPV path."""
        return self.calculate_npv(cfg, revenue_df)

    def perform_excel_aligned_npv_calculation(self, cfg, revenue_df):
        """Backward-compatible wrapper around the FDAS API12 NPV path."""
        return self.calculate_npv(cfg, revenue_df)

    def perform_decline_analysis_api12(self, cfg, api12_df):
        """
        Perform decline curve analysis for API12 well.

        Calculate annual decline rates based on peak and latest production values.

        Note: This is a placeholder for future implementation.
        """
        # TODO: Implement decline curve analysis
        # Placeholder for decline curve analysis implementation
        # This would calculate:
        # - Peak production rate and date
        # - Latest production rate and date
        # - Annual decline rate
        # - Forecasted production based on decline curve
        pass
