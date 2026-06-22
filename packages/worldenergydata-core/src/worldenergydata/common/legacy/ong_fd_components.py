from __future__ import annotations

import json
import logging
import os
from typing import Any

import pandas as pd
from assetutilities.common.data import AttributeDict
from assetutilities.common.database import Database, get_db_connection

from worldenergydata.common.legacy.bsee_data_manager import BSEEData
from worldenergydata.common.legacy.data import (
    DateTimeUtility,
    transform_df_datetime_to_str,
)
from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)

dtu = DateTimeUtility()


class ONGFDComponents:
    # https://plot.ly/python/v3/fft-filters/
    # http://scipy-lectures.org/intro/scipy/auto_examples/plot_fftpack.html
    # https://dsp.stackexchange.com/questions/724/low-pass-filter-and-fft-for-beginners-with-python

    def __init__(self, cfg: dict[str, Any]) -> None:

        self.max_allowed_npt: int = 90
        self.assign_cfg(cfg)
        self.bsee_data: BSEEData = BSEEData(self.cfg)
        output_db_properties: dict[str, Any] = cfg["output_bsee_db"]
        self.dbe_output: Any
        self.connection_status: Any
        self.dbe_output, self.connection_status = get_db_connection(
            output_db_properties
        )

        db_properties: dict[str, Any] = cfg["db"]
        self.dbe: Database = Database(db_properties)

    def assign_cfg(self, cfg: dict[str, Any]) -> None:
        self.cfg: dict[str, Any] = cfg
        self.output_data_field_production_df: pd.DataFrame | None = None
        self.oil_pressure_gradient: float = 0.37  # psi/ft
        self.over_balance_ppg: float = 0.5  # ppg
        self.rig_day_rate_loaded: int = 1100000  # USD
        self.sunk_cost_per_completed_well: int = 40000000  # USD
        self.cost_of_subsea_equipment: int = 200000000  # USD
        self.output_data_field_production_rate_df: pd.DataFrame | None = None
        self.field_summary: AttributeDict = AttributeDict(
            {
                "field_nickname": self.cfg["custom_parameters"]["field_nickname"],
                "wellhead_distances": [],
            }
        )
        self.tubular_summary: pd.DataFrame = pd.DataFrame(
            columns=["Field NickName", "Hole Size", "data", "Well_Type"]
        )
        self.well_activity_rig_days: pd.DataFrame = pd.DataFrame()

    def get_all_bsee_blocks(self) -> list[str]:
        all_bsee_blocks: list[str] = list(
            self.dbe.input_data_all_bsee_blocks["BOTM_FLD_NAME_CD"]
        )

        return all_bsee_blocks

    def get_raw_data_for_well_analysis(self) -> None:
        self.api10_list: list[str] = self.bsee_data.get_api10_list()

    def run_analysis_for_all_wells(self) -> None:
        for api10 in self.api10_list[0:20]:
            self.get_bsee_data_and_prepare_data_for_api10(api10)
            self.save_api10_result(api10)

    def save_api10_result(self, api10: str) -> None:
        self.delete_well_data_for_api10(api10)
        self.dbe_output.save_to_db(self.output_data_well_df, "analysis")

    def delete_well_data_for_api10(self, api10: str) -> None:
        filename: str = os.path.join(
            "data_manager\\sql", "bsee.delete_well_data_for_api10.sql"
        )
        fd = open(filename, "r")
        sqlFile: str = fd.read()
        fd.close()
        self.dbe_output.executeNoDataQuery(sqlFile, [api10])

    def get_bsee_data_and_prepare_data_for_api10(self, api10: str) -> None:
        well_data: pd.DataFrame = self.bsee_data.get_well_data_by_api10(api10)
        production_data: pd.DataFrame = self.bsee_data.get_production_data_by_api10(
            api10
        )
        WAR_summary: pd.DataFrame = self.bsee_data.get_WAR_summary_by_api10(api10)
        directional_surveys: pd.DataFrame = (
            self.bsee_data.get_directional_surveys_by_api10(api10)
        )
        ST_BP_and_tree_height: pd.DataFrame = (
            self.bsee_data.get_ST_BP_and_tree_height_by_api10(api10)
        )
        well_tubulars_data: pd.DataFrame = (
            self.bsee_data.get_well_tubulars_data_by_api10(api10)
        )
        completion_data: pd.DataFrame = self.bsee_data.get_completion_data_by_api10(
            api10
        )

        self.prepare_api12_data(well_data)
        self.prepare_production_data(production_data)
        self.add_sidetracklabel_rig_rigdays(WAR_summary, ST_BP_and_tree_height)
        # self.evaluate_well_distances()
        self.prepare_casing_data(well_data, well_tubulars_data)
        self.prepare_completion_data(completion_data)
        self.prepare_well_paths(directional_surveys)
        self.prepare_formation_data()
        self.prepare_field_well_data()

    def get_raw_data_for_field_analysis(self) -> None:
        if self.cfg["default"]["data_source"] == "db":
            if self.cfg["default"].__contains__("input_data"):
                cfg_input: dict[str, Any] = self.cfg["default"]["input_data"].copy()
                self.dbe.get_input_data(cfg_input)
            else:
                logger.info("No input data in configuration")
        else:
            import sys

            logger.info("No data source specified")
            sys.exit()

    def prepare_field_api12_data(self) -> None:
        self.prepare_api_data()

        well_data: pd.DataFrame = self.dbe.input_data_well
        production_data: pd.DataFrame = self.dbe.input_data_production
        WAR_summary: pd.DataFrame = self.dbe.input_data_well_activity_summary
        directional_surveys: pd.DataFrame = self.dbe.input_data_well_directional_surveys
        ST_BP_and_tree_height: pd.DataFrame = self.dbe.input_data_ST_BP_and_tree_height
        well_tubulars_data: pd.DataFrame = self.dbe.input_data_well_tubulars
        completion_data: pd.DataFrame = self.dbe.input_data_completion_properties

        self.prepare_api12_data(well_data)
        self.prepare_production_data(production_data)
        self.add_sidetracklabel_rig_rigdays(WAR_summary, ST_BP_and_tree_height)
        self.evaluate_well_distances()
        self.prepare_casing_data(well_data, well_tubulars_data)
        self.prepare_completion_data(completion_data)
        self.prepare_well_paths(directional_surveys)
        self.prepare_formation_data()

    def prepare_api_data(self) -> None:
        API10: list[int | str] = []
        for df_row in range(0, len(self.dbe.input_data_well)):
            well_api: Any = self.dbe.input_data_well.API12.iloc[df_row]
            api10_value: int | str = self.get_API10_from_well_API(well_api)
            API10.append(api10_value)
        self.dbe.input_data_well["API10"] = API10
        logger.info("Well API data is prepared")

    def get_API10_from_well_API(self, well_api: Any) -> int | str:
        well_api_str: str = str(well_api)
        if len(well_api_str) == 12:
            api10_value: int | str = int(well_api_str[0:10])
        else:
            api10_value = well_api_str
        return api10_value

    def prepare_api12_data(self, well_data: pd.DataFrame) -> None:

        self.output_data_api12_df: pd.DataFrame = well_data.copy()
        self.add_gis_info_to_well_data()
        self.output_data_api12_df["O_PROD_STATUS"] = 0
        self.output_data_api12_df["O_CUMMULATIVE_PROD_MMBBL"] = 0
        self.output_data_api12_df["DAYS_ON_PROD"] = 0
        self.output_data_api12_df["O_MEAN_PROD_RATE_BOPD"] = 0
        self.output_data_api12_df["Total Depth Date"] = pd.to_datetime(
            self.output_data_api12_df["Total Depth Date"]
        )
        self.output_data_api12_df["Spud Date"] = pd.to_datetime(
            self.output_data_api12_df["Spud Date"]
        )
        self.output_data_api12_df["COMPLETION_NAME"] = ""
        self.output_data_api12_df["monthly_production"] = None
        self.output_data_api12_df["xyz"] = None

    def add_gis_info_to_well_data(self) -> None:
        from assetutilities.common.data import Transform

        transform = Transform()
        gis_cfg: dict[str, str] = {
            "Longitude": "Bottom Longitude",
            "Latitude": "Bottom Latitude",
            "label": "BOT",
        }
        self.output_data_api12_df = transform.gis_deg_to_distance(
            self.output_data_api12_df, gis_cfg
        )
        gis_cfg = {
            "Longitude": "Surface Longitude",
            "Latitude": "Surface Latitude",
            "label": "SURF",
        }
        self.output_data_api12_df = transform.gis_deg_to_distance(
            self.output_data_api12_df, gis_cfg
        )
        self.field_x_ref: float = self.output_data_api12_df.SURF_x.min()
        self.field_y_ref: float = self.output_data_api12_df.SURF_y.min()
        self.output_data_api12_df["BOT_x_rel"] = (
            self.output_data_api12_df["BOT_x"] - self.field_x_ref
        )
        self.output_data_api12_df["BOT_y_rel"] = (
            self.output_data_api12_df["BOT_y"] - self.field_y_ref
        )
        self.output_data_api12_df["SURF_x_rel"] = (
            self.output_data_api12_df["SURF_x"] - self.field_x_ref
        )
        self.output_data_api12_df["SURF_y_rel"] = (
            self.output_data_api12_df["SURF_y"] - self.field_y_ref
        )

        logger.info("GIS data is formatted")

    def prepare_production_data(self, production_data: pd.DataFrame) -> None:
        self.output_data_production_df_array: dict[str, pd.DataFrame] = {}
        completion_name_list: list[str] = production_data.COMPLETION_NAME.unique()
        for completion_name in completion_name_list:
            df_temp: pd.DataFrame = production_data[
                production_data.COMPLETION_NAME == completion_name
            ].copy()
            df_temp = self.add_production_rate_and_date_to_df(df_temp)
            df_temp.sort_values(by=["PRODUCTION_DATETIME"], inplace=True)
            df_temp.reset_index(inplace=True)
            if df_temp.O_PROD_RATE_BOPD.max() > 0:
                well_api12: Any = df_temp.API12.iloc[0]
                well_api10: int | str = self.get_API10_from_well_API(well_api12)
                self.prepare_field_production_rate(df_temp, completion_name)
                self.prepare_field_production(df_temp, completion_name)
                self.add_production_and_completion_name_to_well_data(
                    well_api10, completion_name, df_temp
                )
                self.output_data_production_df_array.update({completion_name: df_temp})

        if len(self.output_data_production_df_array) != 0:
            self.add_production_from_all_wells()
        logger.info("Production data is prepared")

    def add_production_rate_and_date_to_df(self, df: pd.DataFrame) -> pd.DataFrame:
        import datetime

        production_date: list[Any] = []
        production_rate: list[float] = []
        for df_row in range(0, len(df)):
            year: int = int(df.PRODUCTION_DATE.iloc[df_row] / 100)
            month: int = df.PRODUCTION_DATE.iloc[df_row] % year
            date_time: datetime.datetime = datetime.datetime(year, month, 1)
            date_time_last: datetime.date = dtu.last_day_of_month(date_time.date())
            if df.DAYS_ON_PROD.iloc[df_row] != 0:
                rate: float = (
                    df.MON_O_PROD_VOL.iloc[df_row] / df.DAYS_ON_PROD.iloc[df_row]
                )
            else:
                rate = 0
            production_date.append(date_time_last)
            production_rate.append(rate)

        df["PRODUCTION_DATETIME"] = production_date
        df["O_PROD_RATE_BOPD"] = production_rate
        return df

    def prepare_field_production(
        self, df_temp: pd.DataFrame, df_column_label: str
    ) -> None:
        if self.output_data_field_production_df is None:
            self.output_data_field_production_df = pd.DataFrame(
                columns=["PRODUCTION_DATETIME"]
            )

        field_production_df: pd.DataFrame = pd.DataFrame()
        field_production_df["PRODUCTION_DATETIME"] = df_temp[
            "PRODUCTION_DATETIME"
        ].copy()
        field_production_df[df_column_label] = df_temp["MON_O_PROD_VOL"].copy()
        self.output_data_field_production_df = pd.merge(
            left=self.output_data_field_production_df,
            right=field_production_df,
            how="outer",
            left_on="PRODUCTION_DATETIME",
            right_on="PRODUCTION_DATETIME",
        )
        self.output_data_field_production_df.sort_values(
            by=["PRODUCTION_DATETIME"], inplace=True
        )
        self.output_data_field_production_df.drop_duplicates(inplace=True)

    def prepare_field_production_rate(
        self, df_temp: pd.DataFrame, df_column_label: str
    ) -> None:
        if self.output_data_field_production_rate_df is None:
            self.output_data_field_production_rate_df = pd.DataFrame(
                columns=["PRODUCTION_DATETIME"]
            )

        field_production_rate_df: pd.DataFrame = pd.DataFrame()
        field_production_rate_df["PRODUCTION_DATETIME"] = df_temp[
            "PRODUCTION_DATETIME"
        ].copy()
        field_production_rate_df[df_column_label] = df_temp["O_PROD_RATE_BOPD"].copy()
        self.output_data_field_production_rate_df = pd.merge(
            left=self.output_data_field_production_rate_df,
            right=field_production_rate_df,
            how="outer",
            left_on="PRODUCTION_DATETIME",
            right_on="PRODUCTION_DATETIME",
        )
        self.output_data_field_production_rate_df.sort_values(
            by=["PRODUCTION_DATETIME"], inplace=True
        )

    def add_production_from_all_wells(self) -> None:
        columns: list[str] = self.output_data_field_production_rate_df.columns.tolist()
        columns.remove("PRODUCTION_DATETIME")
        self.output_data_field_production_rate_df[
            "TOTAL_DAILY_PRODUCTION_rate_BOPD"
        ] = self.output_data_field_production_rate_df[columns].sum(axis=1)

        columns = self.output_data_field_production_df.columns.tolist()
        columns.remove("PRODUCTION_DATETIME")
        self.output_data_field_production_df["Total_MONTLY_PRODUCTION_MMbbl"] = (
            self.output_data_field_production_df[columns].sum(axis=1) / 1000 / 1000
        )
        self.output_data_field_production_df["CUMULATIVE_MONTLY_PRODUCTION_MMbbl"] = (
            self.output_data_field_production_df[
                "Total_MONTLY_PRODUCTION_MMbbl"
            ].cumsum()
        )

        self.field_summary["Cummulative Production, MMbbls"] = {
            "PRODUCTION_DATETIME": self.output_data_field_production_df[
                "PRODUCTION_DATETIME"
            ].tolist(),
            "CUMULATIVE_MONTLY_PRODUCTION_MMbbl": self.output_data_field_production_df[
                "CUMULATIVE_MONTLY_PRODUCTION_MMbbl"
            ].tolist(),
        }

        self.production_summary_df: pd.DataFrame = pd.DataFrame()
        self.production_summary_df["PRODUCTION_DATETIME"] = (
            self.output_data_field_production_rate_df["PRODUCTION_DATETIME"]
        )
        self.production_summary_df["Field NickName"] = self.cfg["custom_parameters"][
            "field_nickname"
        ]
        self.production_summary_df["BOEM_FIELDS"] = self.cfg["custom_parameters"][
            "boem_fields"
        ]
        self.production_summary_df["Production Rate, BOPD"] = (
            self.output_data_field_production_rate_df[
                "TOTAL_DAILY_PRODUCTION_rate_BOPD"
            ]
        )
        self.production_summary_df["CUMULATIVE_MONTLY_PRODUCTION_MMbbl"] = (
            self.output_data_field_production_df["CUMULATIVE_MONTLY_PRODUCTION_MMbbl"]
        )

    def add_production_and_completion_name_to_well_data(
        self, well_api10: int | str, completion_name: str, df_temp: pd.DataFrame
    ) -> None:
        total_well_production: float = df_temp.MON_O_PROD_VOL.sum() / 1000 / 1000
        api12_production: pd.DataFrame = df_temp[
            ["PRODUCTION_DATETIME", "O_PROD_RATE_BOPD"]
        ].copy()
        api12_production.rename(
            columns={"PRODUCTION_DATETIME": "date_time"}, inplace=True
        )
        api12_production = api12_production.round(decimals=3)
        api12_production["date_time"] = [
            item.strftime("%Y-%m-%d")
            for item in api12_production["date_time"].to_list()
        ]

        temp_df: pd.DataFrame = self.output_data_api12_df[
            (self.output_data_api12_df.API10 == well_api10)
        ].copy()
        if len(temp_df) > 0 and total_well_production > 0:
            df_row_index: int = temp_df.index[0]

            current_production: float = (
                self.output_data_api12_df.O_CUMMULATIVE_PROD_MMBBL.iloc[df_row_index]
            )
            self.output_data_api12_df.O_CUMMULATIVE_PROD_MMBBL.iloc[df_row_index] = (
                current_production + total_well_production
            )
            DAYS_ON_PROD: int = df_temp.DAYS_ON_PROD.sum()
            self.output_data_api12_df.DAYS_ON_PROD.iloc[df_row_index] = DAYS_ON_PROD
            self.output_data_api12_df.O_MEAN_PROD_RATE_BOPD.iloc[df_row_index] = (
                df_temp.MON_O_PROD_VOL.sum() / DAYS_ON_PROD
            )
            self.output_data_api12_df.O_PROD_STATUS.iloc[df_row_index] = 1
            current_completion_name: str = (
                self.output_data_api12_df.COMPLETION_NAME.iloc[df_row_index]
            )
            if current_completion_name == "":
                self.output_data_api12_df.COMPLETION_NAME.iloc[df_row_index] = (
                    completion_name
                )
            else:
                completion_name = current_completion_name + "," + completion_name
                self.output_data_api12_df.COMPLETION_NAME.iloc[df_row_index] = (
                    completion_name
                )
            self.output_data_api12_df["monthly_production"].iloc[df_row_index] = (
                json.dumps(api12_production.to_dict(orient="records"))
            )

    def add_sidetracklabel_rig_rigdays(
        self, WAR_summary: pd.DataFrame, ST_BP_and_tree_height: pd.DataFrame
    ) -> None:
        API10_list: list[int | str] = list(self.output_data_api12_df.API10)
        self.output_data_api12_df["Field NickName"] = self.cfg["custom_parameters"][
            "field_nickname"
        ]
        self.output_data_api12_df["BOEM_FIELDS"] = self.cfg["custom_parameters"][
            "boem_fields"
        ]
        self.output_data_api12_df["Side Tracks"] = 0
        self.output_data_api12_df["Sidetrack No"] = None
        self.output_data_api12_df["Bypass No"] = None
        self.output_data_api12_df["Tree Height Above Mudline"] = None
        self.output_data_api12_df["WELL_LABEL"] = self.output_data_api12_df["Well Name"]
        self.output_data_api12_df["BSEE Well Name"] = self.output_data_api12_df[
            "Well Name"
        ]
        self.output_data_api12_df["Rigs"] = ""
        self.output_data_api12_df["rigdays_dict"] = ""
        self.output_data_api12_df["Drilling Days"] = 0
        self.output_data_api12_df["Completion Days"] = 0
        self.output_data_api12_df["MAX_DRILL_FLUID_WGT"] = 0
        self.output_data_api12_df["drilling_footage_ft"] = 0
        self.output_data_api12_df["drilling_days_per_10000_ft"] = 0
        self.output_data_api12_df["RIG_LAST_DATE_ON_WELL"] = None

        for df_row in range(0, len(self.output_data_api12_df)):
            well_api12: Any = self.output_data_api12_df.API12.iloc[df_row]
            well_api10: int | str = self.output_data_api12_df.API10.iloc[df_row]

            api12_count: int = API10_list.count(well_api10)
            self.output_data_api12_df["Side Tracks"].iloc[df_row] = api12_count - 1
            if api12_count >= 2:
                self.output_data_api12_df["WELL_LABEL"] = (
                    self.output_data_api12_df["Well Name"]
                    + "-"
                    + self.output_data_api12_df["Sidetrack and Bypass"]
                )

            sidetrack_no: float
            bypass_no: float
            tree_elevation_aml: float | None
            sidetrack_no, bypass_no, tree_elevation_aml = self.assign_st_bp_tree_info(
                ST_BP_and_tree_height, well_api12
            )
            self.output_data_api12_df["Sidetrack No"].iloc[df_row] = sidetrack_no
            self.output_data_api12_df["Bypass No"].iloc[df_row] = bypass_no
            self.output_data_api12_df["Tree Height Above Mudline"].iloc[
                df_row
            ] = tree_elevation_aml

            rig_str: str
            MAX_DRILL_FLUID_WGT: float
            well_days_dict: dict[str, Any]
            rig_str, MAX_DRILL_FLUID_WGT, well_days_dict = (
                self.get_rig_days_and_drilling_wt_worked_on_api12(
                    WAR_summary, well_api12
                )
            )
            self.get_rig_days_by_well_activity(well_api12)
            self.output_data_api12_df["Rigs"].iloc[df_row] = rig_str
            self.output_data_api12_df["rigdays_dict"].iloc[df_row] = json.dumps(
                well_days_dict["rigdays_dict"]
            )
            try:
                self.output_data_api12_df["RIG_LAST_DATE_ON_WELL"].iloc[df_row] = (
                    self.dbe.input_data_well_activity_summary[
                        self.dbe.input_data_well_activity_summary.API12 == well_api12
                    ].WAR_END_DT.max()
                )
            except Exception:
                self.output_data_api12_df["RIG_LAST_DATE_ON_WELL"].iloc[df_row] = None
            self.output_data_api12_df["Drilling Days"].iloc[df_row] = well_days_dict[
                "drilling_days"
            ]
            self.output_data_api12_df["Completion Days"].iloc[df_row] = well_days_dict[
                "completion_days"
            ]

            try:
                drilling_footage_ft: float | None = (
                    float(
                        self.output_data_api12_df["Total Measured Depth"].iloc[df_row]
                    )
                    - self.output_data_api12_df["Water Depth"].iloc[df_row]
                )
            except Exception:
                drilling_footage_ft = None
            self.output_data_api12_df["drilling_footage_ft"].iloc[
                df_row
            ] = drilling_footage_ft

            if drilling_footage_ft is not None:
                drilling_days_per_10000_ft: float | None = round(
                    self.output_data_api12_df["Drilling Days"].iloc[df_row]
                    / drilling_footage_ft
                    * 10000,
                    1,
                )
            else:
                drilling_days_per_10000_ft = None
            self.output_data_api12_df["drilling_days_per_10000_ft"].iloc[
                df_row
            ] = drilling_days_per_10000_ft

            self.output_data_api12_df["MAX_DRILL_FLUID_WGT"].iloc[
                df_row
            ] = MAX_DRILL_FLUID_WGT

        self.output_data_api12_df.sort_values(
            by=["O_PROD_STATUS", "WELL_LABEL"], ascending=[False, True], inplace=True
        )
        self.output_data_api12_df.reset_index(inplace=True, drop=True)

    def get_rig_days_and_drilling_wt_worked_on_api12(
        self, WAR_summary: pd.DataFrame, well_api12: Any
    ) -> tuple[str, float, dict[str, Any]]:
        from dateutil.parser import parse

        well_war: pd.DataFrame = WAR_summary[WAR_summary.API12 == well_api12].copy()
        well_info_df: pd.DataFrame = self.output_data_api12_df[
            self.output_data_api12_df.API12 == well_api12
        ].copy()
        spud_date: Any = well_info_df["Spud Date"].iloc[0]
        td_date: Any = well_info_df["Total Depth Date"].iloc[0]

        well_war["Rig_days"] = 0
        well_war["npt_raw"] = 0
        well_war["npt"] = 0

        war_drilling_days_flag: bool = False
        for df_row in range(0, len(well_war)):
            war_days: int = (
                parse(well_war["WAR_END_DT"].iloc[df_row])
                - parse(well_war["WAR_START_DT"].iloc[df_row])
            ).days
            if war_days > 0:
                well_war["Rig_days"].iloc[df_row] = war_days + 1
            else:
                well_war["Rig_days"].iloc[df_row] = war_days
            if df_row > 0:
                start_date: Any = parse(well_war["WAR_START_DT"].iloc[df_row])
                end_date: Any = parse(well_war["WAR_END_DT"].iloc[df_row - 1])
                npt_raw: int = (start_date - end_date).days - 1
                if npt_raw <= self.max_allowed_npt:
                    if npt_raw > 0:
                        well_war["npt_raw"].iloc[df_row] = npt_raw
                elif td_date > start_date:
                    war_drilling_days_flag = True
                if (end_date <= td_date) and (start_date > td_date):
                    end_date = td_date
                npt: int = (start_date - end_date).days - 1
                if (start_date > td_date) and (npt <= self.max_allowed_npt):
                    if npt > 0:
                        well_war["npt"].iloc[df_row] = npt

        rigs: list[str | None] = list(well_war.RIG_NAME.unique())

        rigdays_list: list[int] = []
        rigdays_dict: list[dict[str, Any]] = []
        rigdays_str_array: list[str] = []
        total_rigdays: int = 0
        for rig in rigs:
            rig_days: int = well_war[well_war.RIG_NAME == rig].Rig_days.sum()
            rigdays_list.append(rig_days)
            total_rigdays = total_rigdays + rig_days
            if rig_days > 0:
                rigdays_dict.append({"rig": rig, "days": int(rig_days)})
                if rig is not None:
                    rigdays_str_array.append(rig + " (" + str(rig_days) + ")")
                else:
                    rigdays_str_array.append("unknown rig" + " (" + str(rig_days) + ")")

        # rigdays_str = ', '.join(rigdays_str_array)
        rigs_for_string: list[str] = [
            rig if rig is not None else "unknown rig" for rig in rigs
        ]
        rig_str: str = ", ".join(rigs_for_string)

        api12_war_days: pd.DataFrame = (
            well_war.groupby(["API12", "BOREHOLE_STAT_DESC"])["Rig_days"]
            .sum()
            .reset_index()
        )
        self.well_activity_rig_days = pd.concat(
            [self.well_activity_rig_days, api12_war_days], ignore_index=True
        )

        well_war_npt_days: int = well_war["npt"].sum()
        try:
            completion_days: int = api12_war_days[
                api12_war_days["BOREHOLE_STAT_DESC"] == "BOREHOLE COMPLETED"
            ].Rig_days.sum()
            npt_days: int = well_war[
                (well_war["BOREHOLE_STAT_DESC"] == "BOREHOLE COMPLETED")
            ].npt.sum()
            completion_days = completion_days + npt_days
        except Exception:
            completion_days = 0
        try:
            sidetrack_days: int = api12_war_days[
                (api12_war_days["BOREHOLE_STAT_DESC"] == "BOREHOLE SIDETRACKED")
            ].Rig_days.sum()
            npt_days = well_war[
                (well_war["BOREHOLE_STAT_DESC"] == "BOREHOLE SIDETRACKED")
            ].npt.sum()
            sidetrack_days = sidetrack_days + npt_days
        except Exception:
            sidetrack_days = 0
        try:
            abandon_days: int = api12_war_days[
                (api12_war_days["BOREHOLE_STAT_DESC"] == "PERMANENTLY ABANDONED")
                | (api12_war_days["BOREHOLE_STAT_DESC"] == "TEMPORARILY ABANDONED")
            ].Rig_days.sum()
            npt_days = well_war[
                (well_war["BOREHOLE_STAT_DESC"] == "PERMANENTLY ABANDONED")
                | (well_war["BOREHOLE_STAT_DESC"] == "TEMPORARILY ABANDONED")
            ].npt.sum()
            abandon_days = abandon_days + npt_days
        except Exception:
            abandon_days = 0
        try:
            war_drilling_days: int = api12_war_days[
                (api12_war_days["BOREHOLE_STAT_DESC"] == "DRILLING ACTIVE")
                | (api12_war_days["BOREHOLE_STAT_DESC"] == "DRILLING SUSPENDED")
            ].Rig_days.sum()
            spud_to_td_days: int = (td_date - spud_date).days + 1
            npt_days = well_war[
                (well_war["BOREHOLE_STAT_DESC"] == "DRILLING ACTIVE")
                | (well_war["BOREHOLE_STAT_DESC"] == "DRILLING SUSPENDED")
            ].npt.sum()
            if war_drilling_days_flag:
                spud_to_td_days = war_drilling_days
                npt_days = well_war[
                    (well_war["BOREHOLE_STAT_DESC"] == "DRILLING ACTIVE")
                    | (well_war["BOREHOLE_STAT_DESC"] == "DRILLING SUSPENDED")
                ].npt_raw.sum()
            drilling_days: int = (
                spud_to_td_days + abandon_days + sidetrack_days + npt_days
            )
        except Exception:
            drilling_days = 0

        well_days_dict: dict[str, Any] = {
            "drilling_days": drilling_days,
            "abandon_days": abandon_days,
            "completion_days": completion_days,
            "well_war_npt_days": well_war_npt_days,
            "rigdays_dict": rigdays_dict,
            "total_rigdays": total_rigdays,
        }

        MAX_DRILL_FLUID_WGT: float = well_war.DRILL_FLUID_WGT.max()

        return rig_str, MAX_DRILL_FLUID_WGT, well_days_dict

    def get_rig_days_by_well_activity(self, well_api12: Any) -> None:
        pass

    def assign_st_bp_tree_info(
        self, ST_BP_and_tree_height: pd.DataFrame, well_api12: Any
    ) -> tuple[float, float, float | None]:
        sidetrack_no: float = 0
        bypass_no: float = 0
        tree_elevation_aml: float | None = None
        bp_st_tree_info: pd.DataFrame = ST_BP_and_tree_height[
            ST_BP_and_tree_height.API12 == well_api12
        ].copy()
        if len(bp_st_tree_info) > 0:
            bp_st_tree_info.sort_values(by=["SN_EOR"])
            sidetrack_no = float(bp_st_tree_info.WELL_NM_ST_SFIX.iloc[0])
            bypass_no = float(bp_st_tree_info.WELL_NM_BP_SFIX.iloc[0])
            tree_elevation_aml = bp_st_tree_info.SUBSEA_TREE_HEIGHT_AML.iloc[0]
            if tree_elevation_aml is not None:
                tree_elevation_aml = float(tree_elevation_aml)

        return sidetrack_no, bypass_no, tree_elevation_aml

    def evaluate_well_distances(self) -> None:
        from worldenergydata.common.legacy.math_solvers import Geometry

        geom = Geometry()
        self.output_data_api12_df["HORZ_DEPARTURE"] = 0
        if len(self.output_data_api12_df) > 0:
            well_head_xy_sets: list[list[float]] = []
            for df_row in range(0, len(self.output_data_api12_df)):
                surface_x_y: list[float] = [
                    self.output_data_api12_df.SURF_x_rel.iloc[df_row],
                    self.output_data_api12_df.SURF_y_rel.iloc[df_row],
                ]
                well_head_xy_sets.append(surface_x_y)
                bottom_x_y: list[float] = [
                    self.output_data_api12_df.BOT_x_rel.iloc[df_row],
                    self.output_data_api12_df.BOT_y_rel.iloc[df_row],
                ]
                spatial_data_sets: list[list[float]] = [surface_x_y, bottom_x_y]
                result: dict[str, Any] = geom.max_distance_for_spatial_sets(
                    spatial_data_sets
                )
                self.output_data_api12_df.HORZ_DEPARTURE.iloc[df_row] = result[
                    "distance_max"
                ]

            if len(well_head_xy_sets) > 1:
                result = geom.max_distance_for_spatial_sets(well_head_xy_sets)
                self.field_summary.wellhead_distances.append(
                    {
                        "Description": "All Wellheads, Max Distance (ft)",
                        "Value": round(float(result["distance_max"] / 0.3048), 1),
                    }
                )
                self.field_summary.wellhead_distances.append(
                    {
                        "Description": "All Wellheads, Min Distance (ft)",
                        "Value": round(float(result["distance_min"] / 0.3048), 1),
                    }
                )
            else:
                self.field_summary.wellhead_distances.append(
                    {
                        "Description": "All Wellheads, Max Distance (ft)",  # noqa: F601
                        "Value": 0,
                        "Description": "All Wellheads, Min Distance (ft)",  # noqa: F601
                    }
                )

            horizontal_departure: float = round(
                (self.output_data_api12_df.HORZ_DEPARTURE.max() / 0.3048), 1
            )
            self.field_summary.wellhead_distances.append(
                {
                    "Description": "All Wells, Max Horizontal Departure (ft)",
                    "Value": horizontal_departure,
                }
            )

            self.output_data_producing_api12_df: pd.DataFrame = (
                self.output_data_api12_df[self.output_data_api12_df.O_PROD_STATUS == 1]
            )
            if len(self.output_data_producing_api12_df) > 0:
                producing_well_head_xy_sets: list[list[float]] = []
                for df_row in range(0, len(self.output_data_api12_df)):
                    if self.output_data_api12_df.O_PROD_STATUS.iloc[df_row] == 1:
                        surface_x_y = [
                            self.output_data_api12_df.SURF_x_rel.iloc[df_row],
                            self.output_data_api12_df.SURF_y_rel.iloc[df_row],
                        ]
                        producing_well_head_xy_sets.append(surface_x_y)
                if len(producing_well_head_xy_sets) > 1:
                    result = geom.max_distance_for_spatial_sets(
                        producing_well_head_xy_sets
                    )
                    self.field_summary.wellhead_distances.append(
                        {
                            "Description": "Producing Wellheads, Max Distance (ft)",
                            "Value": round(float(result["distance_max"] / 0.3048), 1),
                        }
                    )
                    self.field_summary.wellhead_distances.append(
                        {
                            "Description": "Producing Wellheads, Min Distance (ft)",
                            "Value": round(float(result["distance_min"] / 0.3048), 1),
                        }
                    )
                else:
                    self.field_summary.wellhead_distances.append(
                        {
                            "Description": "Producing Wellheads, Max Distance (ft)",  # noqa: F601
                            "Value": 0,
                            "Description": "Producing Wellheads, Min Distance (ft)",  # noqa: F601
                        }
                    )

                horizontal_departure = round(
                    (
                        self.output_data_api12_df[
                            self.output_data_api12_df.O_PROD_STATUS == 1
                        ].HORZ_DEPARTURE.max()
                        / 0.3048
                    ),
                    1,
                )
                self.field_summary.wellhead_distances.append(
                    {
                        "Description": "Producing Wellheads, Max Horizontal Departure (ft)",
                        "Value": horizontal_departure,
                    }
                )

    def prepare_casing_data(
        self, well_data: pd.DataFrame, well_tubulars_data: pd.DataFrame
    ) -> None:

        self.casing_tubulars: pd.DataFrame = pd.DataFrame()
        if len(well_tubulars_data) > 0:
            well_tubulars_data.WAR_START_DT = pd.to_datetime(
                well_tubulars_data.WAR_START_DT
            )
            well_tubulars_data.sort_values(
                by=[
                    "API12",
                    "WAR_START_DT",
                    "CSNG_HOLE_SIZE",
                    "CASING_SIZE",
                    "CSNG_SETTING_BOTM_MD",
                ],
                inplace=True,
            )
            for df_row in range(0, len(self.output_data_api12_df)):
                well_api12: Any = self.output_data_api12_df.API12.iloc[df_row]
                temp_df: pd.DataFrame = well_tubulars_data[
                    (well_tubulars_data.API12 == well_api12)
                ].copy()
                max_date: Any = temp_df.WAR_START_DT.max()
                latest_tubulars_df_with_duplicates: pd.DataFrame = temp_df[
                    temp_df.WAR_START_DT == max_date
                ].copy()
                latest_tubulars_df_with_duplicates.reset_index(inplace=True, drop=True)
                latest_tubulars_df: pd.DataFrame = self.clean_tubulars_data(
                    latest_tubulars_df_with_duplicates
                )
                self.casing_tubulars = pd.concat(
                    [self.casing_tubulars, latest_tubulars_df], ignore_index=True
                )

            self.casing_tubulars["Field NickName"] = self.cfg["custom_parameters"][
                "field_nickname"
            ]
            logging.info("Tubing data is prepared")
            self.prepare_casing_tubular_summary_all_wells(well_data)
        else:
            logging.info("Tubing data is not available")

    def clean_tubulars_data(
        self, latest_tubulars_df_with_duplicates: pd.DataFrame
    ) -> pd.DataFrame:
        casing_hole_size_array: list[Any] = list(
            latest_tubulars_df_with_duplicates.CSNG_HOLE_SIZE.unique()
        )
        drop_index_array: list[Any] = []
        for casing_hole_size in casing_hole_size_array:
            temp_df: pd.DataFrame = latest_tubulars_df_with_duplicates[
                (latest_tubulars_df_with_duplicates.CSNG_HOLE_SIZE == casing_hole_size)
            ].copy()
            if len(temp_df) > 1:
                casing_setting_top_md_array: Any = temp_df.CSNG_SETTING_TOP_MD.unique()
                casing_setting_bottom_md_array: Any = (
                    temp_df.CSNG_SETTING_BOTM_MD.unique()
                )
                if len(casing_setting_top_md_array) == 1:
                    pass  # Logic here
                    drop_index_array = drop_index_array + list(temp_df.index)[0:-1]
                else:
                    for casing_setting_bottom_md in casing_setting_bottom_md_array:
                        temp_df_1: pd.DataFrame = temp_df[
                            temp_df.CSNG_SETTING_BOTM_MD == casing_setting_bottom_md
                        ].copy()
                        if len(temp_df_1) > 1:
                            CSNG_LINER_TEST_PRSS_unique_count: int = len(
                                list(temp_df_1.CSNG_LINER_TEST_PRSS.unique())
                            )
                            CSNG_SHOE_TEST_PRSS_unique_count: int = len(
                                list(temp_df_1.CSNG_SHOE_TEST_PRSS.unique())
                            )
                            CSNG_CEMENT_VOL_unique_count: int = len(
                                list(temp_df_1.CSNG_CEMENT_VOL.unique())
                            )
                            if (
                                max(
                                    CSNG_LINER_TEST_PRSS_unique_count,
                                    CSNG_SHOE_TEST_PRSS_unique_count,
                                    CSNG_CEMENT_VOL_unique_count,
                                )
                                == 1
                            ):
                                drop_index_array = (
                                    drop_index_array + list(temp_df_1.index)[1:]
                                )

        latest_tubulars_df: pd.DataFrame = latest_tubulars_df_with_duplicates.copy()
        latest_tubulars_df.drop(drop_index_array, inplace=True)
        latest_tubulars_df.reset_index(inplace=True, drop=True)
        return latest_tubulars_df

    def prepare_casing_tubular_summary_all_wells(self, well_data: pd.DataFrame) -> None:
        API12_list: list[Any] = list(
            well_data.sort_values(by=["Well Name", "API12"])["API12"]
        )
        casing_hole_sizes: list[Any] = (
            self.casing_tubulars.CSNG_HOLE_SIZE.unique().tolist()
        )
        casing_hole_sizes = sorted(casing_hole_sizes, reverse=True)
        self.tubular_summary_based_on_api12_and_hole(
            API12_list, casing_hole_sizes, "ALL"
        )
        logging.info("Tubular data Summary is prepared for all wells")

        API12_list = list(
            self.output_data_api12_df[
                self.output_data_api12_df.O_PROD_STATUS == 1
            ].API12
        )
        casing_hole_sizes = (
            self.casing_tubulars[self.casing_tubulars.API12.isin(API12_list)]
            .CSNG_HOLE_SIZE.unique()
            .tolist()
        )
        casing_hole_sizes = sorted(casing_hole_sizes, reverse=True)
        self.tubular_summary_based_on_api12_and_hole(
            API12_list, casing_hole_sizes, "PRODUCERS"
        )
        logging.info("Tubular data Summary is prepared for producing wells")

    def tubular_summary_based_on_api12_and_hole(
        self, API12_list: list[Any], casing_hole_sizes: list[Any], well_type: str
    ) -> None:
        index: list[str] = [
            "Well Name",
            "Top MD",
            "Bottom MD",
            "Casing Size",
            "Casing Grade",
            "Casing Wt",
            "Tubular Test Presssure",
            "Shoe Test Pressure",
            "Cement Vol",
        ]
        hole_tubular_summary: pd.DataFrame = pd.DataFrame(
            columns=API12_list, index=index
        )
        for casing_index in range(0, len(casing_hole_sizes)):
            casing_hole: Any = casing_hole_sizes[casing_index]
            df_tubular_select_hole: pd.DataFrame = self.casing_tubulars[
                self.casing_tubulars.CSNG_HOLE_SIZE == casing_hole
            ]
            for api12_index in range(0, len(API12_list)):
                api12: Any = API12_list[api12_index]
                df_tubular_select_hole_api12: pd.DataFrame = df_tubular_select_hole[
                    df_tubular_select_hole.API12 == api12
                ].copy()
                if len(df_tubular_select_hole_api12) > 0:
                    well_name: str = df_tubular_select_hole_api12.iloc[0].WELL_NAME
                    Top_MD: float = df_tubular_select_hole_api12.iloc[
                        0
                    ].CSNG_SETTING_TOP_MD
                    Bottom_MD: float = df_tubular_select_hole_api12.iloc[
                        0
                    ].CSNG_SETTING_BOTM_MD
                    Casing_Size: float = df_tubular_select_hole_api12.iloc[
                        0
                    ].CASING_SIZE
                    Casing_Grade: str = df_tubular_select_hole_api12.iloc[
                        0
                    ].CASING_GRADE
                    Casing_Wt: float = df_tubular_select_hole_api12.iloc[
                        0
                    ].CASING_WEIGHT
                    Tubular_Test_Presssure: float = df_tubular_select_hole_api12.iloc[
                        0
                    ].CSNG_LINER_TEST_PRSS
                    Shoe_Test_Pressure: float = df_tubular_select_hole_api12.iloc[
                        0
                    ].CSNG_SHOE_TEST_PRSS
                    Cement_Vol: float = df_tubular_select_hole_api12.iloc[
                        0
                    ].CSNG_CEMENT_VOL
                    data_array: list[Any] = [
                        well_name,
                        Top_MD,
                        Bottom_MD,
                        Casing_Size,
                        Casing_Grade,
                        Casing_Wt,
                        Tubular_Test_Presssure,
                        Shoe_Test_Pressure,
                        Cement_Vol,
                    ]
                    hole_tubular_summary[api12] = data_array
            hole_tubular_summary_json: str = hole_tubular_summary.to_json()
            self.tubular_summary.loc[len(self.tubular_summary)] = [
                self.cfg["custom_parameters"]["field_nickname"],
                casing_hole,
                hole_tubular_summary_json,
                well_type,
            ]

    def prepare_completion_data(self, completion_data: pd.DataFrame) -> None:
        from assetutilities.common.data import Transform

        transform = Transform()
        self.output_completions: pd.DataFrame = completion_data.merge(
            completion_data, how="outer", left_on="API12", right_on="API12"
        )
        gis_cfg: dict[str, str] = {
            "Longitude": "COMP_LONGITUDE",
            "Latitude": "COMP_LATITUDE",
            "label": "COMP",
        }
        self.output_completions = transform.gis_deg_to_distance(
            self.output_completions, gis_cfg
        )
        self.output_completions["COMP_x_rel"] = (
            self.output_completions["COMP_x"] - self.field_x_ref
        )
        self.output_completions["COMP_y_rel"] = (
            self.output_completions["COMP_y"] - self.field_y_ref
        )
        self.output_completions["Field NickName"] = self.cfg["custom_parameters"][
            "field_nickname"
        ]

    def prepare_formation_data(self) -> None:
        pass

    def prepare_field_well_data(self) -> None:
        API10_list: list[int | str] = list(self.output_data_api12_df.API10.unique())
        sum_columns: list[str] = [
            "O_CUMMULATIVE_PROD_MMBBL",
            "DAYS_ON_PROD",
            "Drilling Days",
            "Completion Days",
        ]
        self.output_data_well_df: pd.DataFrame = self.output_data_api12_df.copy()
        drop_index_array: list[Any] = []
        for well_api10 in API10_list:
            temp_df: pd.DataFrame = self.output_data_api12_df[
                (self.output_data_api12_df.API10 == well_api10)
            ].copy()
            if len(temp_df) > 1:
                # Clean output_data_well_df
                temp_df.sort_values(by="API12", inplace=True)
                drop_index_array.extend(list(temp_df.index)[:-1])
                well_index: int = list(temp_df.index)[-1]

                for column in sum_columns:
                    self.output_data_well_df[column].iloc[well_index] = temp_df[
                        column
                    ].sum()

                try:
                    drilling_footage_ft: float | None = (
                        float(
                            self.output_data_well_df["Total Measured Depth"].iloc[
                                well_index
                            ]
                        )
                        - self.output_data_well_df["Water Depth"].iloc[well_index]
                    )
                except Exception:
                    drilling_footage_ft = None
                self.output_data_well_df["drilling_footage_ft"].iloc[
                    well_index
                ] = drilling_footage_ft

                if drilling_footage_ft is not None:
                    drilling_days_per_10000_ft: float | None = round(
                        self.output_data_well_df["Drilling Days"].iloc[well_index]
                        / drilling_footage_ft
                        * 10000,
                        1,
                    )
                else:
                    drilling_days_per_10000_ft = None
                self.output_data_well_df["drilling_days_per_10000_ft"].iloc[
                    well_index
                ] = drilling_days_per_10000_ft

                self.output_data_well_df["O_PROD_STATUS"].iloc[well_index] = temp_df[
                    "O_PROD_STATUS"
                ].max()
                self.output_data_well_df["RIG_LAST_DATE_ON_WELL"].iloc[well_index] = (
                    temp_df["RIG_LAST_DATE_ON_WELL"].dropna().max()
                )
                self.output_data_well_df["Spud Date"].iloc[well_index] = (
                    temp_df["Spud Date"].dropna().min()
                )
                if self.output_data_well_df["DAYS_ON_PROD"].iloc[well_index] > 0:
                    self.output_data_well_df["O_MEAN_PROD_RATE_BOPD"].iloc[
                        well_index
                    ] = (
                        self.output_data_well_df["O_CUMMULATIVE_PROD_MMBBL"].iloc[
                            well_index
                        ]
                        / self.output_data_well_df["DAYS_ON_PROD"].iloc[well_index]
                    )

        self.output_data_well_df.drop(drop_index_array, inplace=True)
        self.output_data_well_df["BSEE Well Name"] = self.output_data_well_df[
            "Well Name"
        ]
        if len(self.output_data_well_df["Well Name"].unique()) < len(
            self.output_data_well_df
        ):
            from assetutilities.common.data import Transform

            trans = Transform()
            old_list: list[str] = list(self.output_data_well_df["Well Name"])

            cfg_temp: dict[str, Any] = {
                "list": old_list,
                "transform_character": "trailing_alphabet",
            }
            new_list: list[str] = trans.transform_list_to_unique_list(cfg_temp)

            self.output_data_well_df["Well Name"] = new_list

    def get_drilling_completion_summary(self) -> list[dict[str, Any]]:
        self.output_data_api12_df[
            self.output_data_api12_df["Well Purpose"] == "D"
        ].copy()

        total_wellbores: int = (
            len(self.output_data_well_df)
            + self.output_data_well_df["Side Tracks"].sum()
        )

        avg_water_depth: float = round(
            self.output_data_well_df["Water Depth"].mean(), 0
        )

        avg_drilling_footage_ft: float = round(
            pd.to_numeric(
                self.output_data_well_df["drilling_footage_ft"], errors="coerce"
            ).mean(),
            0,
        )
        avg_drilling_days_per_10000_ft: float = round(
            pd.to_numeric(
                self.output_data_well_df["drilling_days_per_10000_ft"], errors="coerce"
            ).mean(),
            1,
        )
        avg_tvd_all_wellbores: float = round(
            pd.to_numeric(
                self.output_data_well_df["Total Vertical Depth"], errors="coerce"
            ).mean(),
            0,
        )
        avg_tmd_all_wellbores: float = round(
            pd.to_numeric(
                self.output_data_well_df["Total Measured Depth"], errors="coerce"
            ).mean(),
            0,
        )
        total_construction_time_all_wellbores: float = pd.to_numeric(
            self.output_data_well_df["Drilling Days"], errors="coerce"
        ).sum()
        total_completion_time_all_wellbores: float = pd.to_numeric(
            self.output_data_well_df["Completion Days"], errors="coerce"
        ).sum()
        total_d_c_time_all_wellbores: float = (
            total_construction_time_all_wellbores + total_completion_time_all_wellbores
        )

        completed_wells_df: pd.DataFrame = self.output_data_well_df[
            self.output_data_well_df["Wellbore Status"] == "COM"
        ].copy()
        completed_wellbores: int = len(completed_wells_df)

        avg_construction_time_all_wellbores: float = round(
            avg_drilling_footage_ft / 10000 * avg_drilling_days_per_10000_ft, 1
        )
        total_d_c_estimated_cost: float = (
            total_d_c_time_all_wellbores * self.rig_day_rate_loaded
            + completed_wellbores * self.sunk_cost_per_completed_well
        )

        if completed_wellbores > 0:
            avg_mud_weight: float = round(
                pd.to_numeric(
                    completed_wells_df["MAX_DRILL_FLUID_WGT"], errors="coerce"
                ).mean(),
                1,
            )
            estimated_reservoir_pressure: float = round(
                (avg_tvd_all_wellbores - 1000)
                * (avg_mud_weight - self.over_balance_ppg)
                * 0.052,
                0,
            )
            estimated_mudline_pressure: float = round(
                estimated_reservoir_pressure
                - self.oil_pressure_gradient
                * (avg_tvd_all_wellbores - avg_water_depth),
                0,
            )
            estimated_dry_tree_tubing_pressure: float = round(
                estimated_mudline_pressure
                - self.oil_pressure_gradient * avg_water_depth,
                0,
            )

            avg_d_c_time_completed_wellbores: float = round(
                total_d_c_time_all_wellbores / completed_wellbores, 1
            )
            avg_c_time_completed_wellbores: float = round(
                total_completion_time_all_wellbores / completed_wellbores, 1
            )
            d_c_estimated_cost_per_completion: float = (
                total_d_c_estimated_cost / completed_wellbores
            )
            d_c_estimated_cost_per_subsea_well: float = (
                d_c_estimated_cost_per_completion + self.cost_of_subsea_equipment
            )
        else:
            estimated_reservoir_pressure = 0
            estimated_mudline_pressure = 0
            estimated_dry_tree_tubing_pressure = 0
            avg_d_c_time_completed_wellbores = 0
            avg_c_time_completed_wellbores = 0
            d_c_estimated_cost_per_completion = 0
            d_c_estimated_cost_per_subsea_well = 0
        total_estimated_cost_for_subsea_wells: float = (
            d_c_estimated_cost_per_subsea_well * completed_wellbores
        )

        drilling_completion_summary: list[dict[str, Any]] = []
        drilling_completion_summary.append(
            {"Description": "Water Depth", "Value": float(avg_water_depth)}
        )
        drilling_completion_summary.append(
            {"Description": "Total Wellbores", "Value": int(total_wellbores)}
        )
        drilling_completion_summary.append(
            {
                "Description": "Avg TVD, All Wellbores",
                "Value": float(avg_tvd_all_wellbores),
            }
        )
        drilling_completion_summary.append(
            {
                "Description": "Avg TMD, All Wellbores",
                "Value": float(avg_tmd_all_wellbores),
            }
        )
        drilling_completion_summary.append(
            {
                "Description": "Avg Construction Time, All Wellbores (days)",
                "Value": float(avg_construction_time_all_wellbores),
            }
        )
        drilling_completion_summary.append(
            {
                "Description": "Completed Wellbores (#)",
                "Value": int(completed_wellbores),
            }
        )
        drilling_completion_summary.append(
            {
                "Description": "Total D&C Time, Completed Wellbores (days)",
                "Value": float(total_d_c_time_all_wellbores),
            }
        )
        drilling_completion_summary.append(
            {
                "Description": "Average D&C Time, Completed Wellbores (days)",
                "Value": float(avg_d_c_time_completed_wellbores),
            }
        )
        drilling_completion_summary.append(
            {
                "Description": "Total Completion Time (days)",
                "Value": float(avg_c_time_completed_wellbores),
            }
        )

        drilling_completion_summary.append(
            {
                "Description": "Total D&C Estimated Cost (USD)",
                "Value": float(total_d_c_estimated_cost),
            }
        )
        drilling_completion_summary.append(
            {
                "Description": "Estimated D&C Cost per Completion (USD)",
                "Value": float(d_c_estimated_cost_per_completion),
            }
        )
        drilling_completion_summary.append(
            {
                "Description": "Estimated Total Subsea Completion per Well (USD)",
                "Value": float(d_c_estimated_cost_per_subsea_well),
            }
        )
        drilling_completion_summary.append(
            {
                "Description": "Estimated Total Subsea Well Cost (USD)",
                "Value": float(total_estimated_cost_for_subsea_wells),
            }
        )

        drilling_completion_summary.append(
            {
                "Description": "Estimated Reservoir Pressure (psi)",
                "Value": float(estimated_reservoir_pressure),
            }
        )
        drilling_completion_summary.append(
            {
                "Description": "Estimated Mudline Pressure (psi)",
                "Value": float(estimated_mudline_pressure),
            }
        )
        drilling_completion_summary.append(
            {
                "Description": "Estimated Dry Tree Tbg Shut-in Pressure (psi)",
                "Value": float(estimated_dry_tree_tubing_pressure),
            }
        )

        return drilling_completion_summary

    def prepare_field_summary(self) -> None:

        df_columns: list[str] = []
        df_row_array: list[Any] = []
        df_columns.append("Field NickName")
        df_row_array.append(self.cfg["custom_parameters"]["field_nickname"])
        df_columns.append("BOEM_FIELDS")
        df_row_array.append(self.cfg["custom_parameters"]["boem_fields"])
        df_columns.append("wellhead_distances")
        df_row_array.append(json.dumps(self.field_summary.wellhead_distances.copy()))
        df_columns.append("drilling_completion_summary")
        drilling_completion_summary: list[dict[str, Any]] = (
            self.get_drilling_completion_summary()
        )
        df_row_array.append(json.dumps(drilling_completion_summary))
        df_columns.append("production")
        self.production_summary_df.drop(
            ["Field NickName", "BOEM_FIELDS"], axis=1, inplace=True, errors="ignore"
        )
        self.production_summary_df = self.production_summary_df.round(4)
        self.production_summary_df = transform_df_datetime_to_str(
            self.production_summary_df, date_format="%Y-%m-%d"
        )
        df_row_array.append(self.production_summary_df.to_json(orient="records"))

        self.output_field_summary_df: pd.DataFrame = pd.DataFrame(columns=df_columns)
        self.output_field_summary_df.loc[len(self.output_field_summary_df)] = (
            df_row_array
        )

    def prepare_visualizations(self) -> None:
        from assetutilities.common.visualization_components import (
            VisualizationComponents,
        )

        vc = VisualizationComponents(self.cfg)
        vc.prepare_visualizations(self)

    def save_data(self) -> None:
        # self.dbe.save_application_data(self)
        self.dbe_output.save_application_data(self)

    def save_output_data_to_local_computer(self) -> None:
        if (
            self.cfg.__contains__("save_output_data_to_local_computer")
            and self.cfg["save_output_data_to_local_computer"]["flag"]
        ):
            df_array: list[pd.DataFrame] = []
            label_array: list[str] = []
            cfg_sets: list[dict[str, Any]] = self.cfg[
                "save_output_data_to_local_computer"
            ]["sets"]
            for set_index in range(0, len(cfg_sets)):
                cfg_set: dict[str, Any] = cfg_sets[set_index]
                df_attribute: str = cfg_set["df_attribute"]
                label: str = cfg_set["label"]
                df: pd.DataFrame | None = getattr(self, df_attribute, None)
                if df is not None:
                    df_array.append(df)
                    label_array.append(label)

            from assetutilities.common.data import SaveData

            save_data = SaveData()
            file_name_without_extension: str = (
                self.cfg["Analysis"]["result_folder"]
                + self.cfg["Analysis"]["file_name"]
            )
            cfg_temp: dict[str, Any] = {
                "SheetNames": label_array,
                "FileName": file_name_without_extension + ".xlsx",
            }
            save_data.DataFrameArray_To_xlsx_openpyxl(df_array, cfg_temp)

    def prepare_well_paths(self, directional_surveys: pd.DataFrame) -> None:
        self.output_well_path_for_db: dict[str, Any] = {}
        self.output_data_well_path: dict[Any, pd.DataFrame] = {}
        API12_list: list[Any] = list(directional_surveys.API12.unique())
        count: int = 0
        for api12 in API12_list:
            count = count + 1
            api12_dir_survey_df: pd.DataFrame = directional_surveys[
                directional_surveys.API12 == api12
            ].copy()
            api12_dir_survey_df["az"] = 0
            api12_dir_survey_df["inc"] = 0
            api12_dir_survey_df["md"] = api12_dir_survey_df["SURVEY_POINT_MD"]

            for df_row in range(0, len(api12_dir_survey_df)):
                WELL_N_S_CODE: str = api12_dir_survey_df.iloc[df_row]["WELL_N_S_CODE"]
                WELL_E_W_CODE: str = api12_dir_survey_df.iloc[df_row]["WELL_E_W_CODE"]
                Azimuth_quadrant_angle: float = (
                    api12_dir_survey_df.iloc[df_row]["DIR_DEG_VAL"]
                    + api12_dir_survey_df.iloc[df_row]["DIR_MINS_VAL"] / 60
                )
                Inclination: float = (
                    api12_dir_survey_df.iloc[df_row]["INCL_ANG_DEG_VAL"]
                    + api12_dir_survey_df.iloc[df_row]["INCL_ANG_MIN_VAL"] / 60
                )
                if WELL_N_S_CODE == "N":
                    if WELL_E_W_CODE == "E":
                        Azimuth: float = Azimuth_quadrant_angle
                    else:
                        Azimuth = 360 - Azimuth_quadrant_angle
                else:
                    if WELL_E_W_CODE == "E":
                        Azimuth = 180 - Azimuth_quadrant_angle
                    else:
                        Azimuth = 180 + Azimuth_quadrant_angle
                api12_dir_survey_df["az"].iloc[df_row] = Azimuth
                api12_dir_survey_df["inc"].iloc[df_row] = Inclination

            logger.info(
                "Processing Survey for api12 {} of {}".format(count, len(API12_list))
            )
            survey_xyz: pd.DataFrame = self.process_survey_xyz(api12_dir_survey_df)
            survey_xyz_wh_adjusted: pd.DataFrame = self.add_relative_WH_positions(
                api12, survey_xyz
            )
            self.output_data_well_path.update({api12: survey_xyz_wh_adjusted})
            survey_for_db: pd.DataFrame = pd.DataFrame()
            survey_for_db["x"] = survey_xyz_wh_adjusted["x_coor"]
            survey_for_db["y"] = survey_xyz_wh_adjusted["y_coor"]
            survey_for_db["z"] = survey_xyz_wh_adjusted["z_coor"]
            survey_for_db = survey_for_db.round(decimals=1)
            try:
                api10_value: int | str = self.get_API10_from_well_API(api12)
                label: str = (
                    self.output_data_well_df[
                        self.output_data_well_df.API10 == api10_value
                    ]["Well Name"].values[0]
                    + "-"
                    + self.output_data_well_df[
                        self.output_data_well_df.API10 == api10_value
                    ]["Sidetrack and Bypass"].values[0]
                )
                label = label.strip()
            except Exception:
                label = str(api12)
            output_well_path_for_db: dict[str, Any] = {
                "data": survey_for_db.to_dict(orient="records"),
                "label": label,
            }
            temp_df: pd.DataFrame = self.output_data_api12_df[
                (self.output_data_api12_df.API12 == api12)
            ].copy()
            if len(temp_df) > 0 and len(survey_for_db) > 0:
                df_row_index: int = temp_df.index[0]
                self.output_data_api12_df["xyz"].iloc[df_row_index] = json.dumps(
                    output_well_path_for_db
                )

        # self.plot_field_wells()

    def process_survey_xyz(self, survey: pd.DataFrame) -> pd.DataFrame:
        # calcualted x is northing and y is easting
        import numpy as np

        survey_xyz: pd.DataFrame = survey[["md", "inc", "az"]]
        survey_xyz = survey_xyz.sort_values(by=["md"])
        survey_xyz = survey_xyz.reset_index(drop=True)
        survey_xyz = survey_xyz.drop_duplicates(subset=["md"], keep="first")

        survey_xyz.loc[:, "inc_diff"] = survey_xyz["inc"].diff()
        survey_xyz.loc[:, "md_diff"] = survey_xyz["md"].diff()
        survey_xyz.loc[:, "az_diff"] = survey_xyz["az"].diff()
        survey_xyz = survey_xyz.fillna(0)

        for i in range(0, np.shape(survey_xyz)[0]):
            if survey_xyz["az_diff"].iloc[i] > 180:
                survey_xyz.loc[i, "az_diff"] = survey_xyz.loc[i, "az_diff"] - 360
            elif survey_xyz["az_diff"].iloc[i] < -180:
                survey_xyz.loc[i, "az_diff"] = survey_xyz.loc[i, "az_diff"] + 360

        survey_xyz.loc[:, "inc_ave"] = survey_xyz["inc"].rolling(window=2).mean()
        survey_xyz.loc[:, "build_rate"] = survey_xyz["inc_diff"] / survey_xyz["md_diff"]
        survey_xyz.loc[:, "turn_rate"] = survey_xyz["az_diff"] / survey_xyz["md_diff"]

        md_diff: Any = np.array(survey_xyz["md_diff"][1:])
        build_rate: Any = np.array(survey_xyz["build_rate"])
        turn_rate: Any = np.array(survey_xyz["turn_rate"])

        inc_ave: Any = np.array(survey_xyz["inc_ave"]) * np.pi / 180
        inc_start: Any = np.array(survey_xyz["inc"][:-1]) * np.pi / 180
        inc_end: Any = np.array(survey_xyz["inc"][1:]) * np.pi / 180
        az_start: Any = np.array(survey_xyz["az"][:-1]) * np.pi / 180
        az_end: Any = np.array(survey_xyz["az"][1:]) * np.pi / 180

        x_coor: Any = np.array(np.zeros([np.shape(survey_xyz)[0], 1]))
        y_coor: Any = np.array(np.zeros([np.shape(survey_xyz)[0], 1]))
        z_coor: Any = np.array(np.zeros([np.shape(survey_xyz)[0], 1]))

        dog_leg_sq: Any = (
            np.sin((inc_end - inc_start) / 2) ** 2
            + np.sin(inc_start) * np.sin(inc_end) * np.sin((az_end - az_start) / 2) ** 2
        )
        dog_leg: Any = 2 * np.arcsin(np.sqrt(dog_leg_sq))
        dog_leg[dog_leg < 10**-6] = 10**-6
        rf: Any = md_diff / dog_leg * np.tan(dog_leg / 2)

        delta_x: Any = (
            np.sin(inc_start) * np.cos(az_start) + np.sin(inc_end) * np.cos(az_end)
        ) * rf
        delta_y: Any = (
            np.sin(inc_start) * np.sin(az_start) + np.sin(inc_end) * np.sin(az_end)
        ) * rf
        delta_z: Any = (np.cos(inc_start) + np.cos(inc_end)) * rf

        x_coor[1:, 0] = np.cumsum(delta_x)
        y_coor[1:, 0] = np.cumsum(delta_y)
        z_coor[1:, 0] = np.cumsum(delta_z)
        dz: Any = np.diff(z_coor, axis=0)
        dz = np.insert(dz, 0, 0, axis=0)

        dls: Any = np.sqrt(build_rate**2 + (np.sin(inc_ave)) ** 2 * turn_rate**2)
        dls = dls.reshape(dls.shape[0], 1)
        xyz_table: pd.DataFrame = pd.DataFrame(
            np.hstack((x_coor, y_coor, z_coor, dz, dls)),
            columns=["x_coor", "y_coor", "z_coor", "dz", "dls"],
        )
        survey_xyz = pd.concat([survey_xyz, xyz_table], axis=1)
        survey_xyz.fillna(0, inplace=True)

        return survey_xyz

    def add_relative_WH_positions(
        self, api12: Any, survey_xyz: pd.DataFrame
    ) -> pd.DataFrame:
        api12_df: pd.DataFrame = self.output_data_api12_df[
            self.output_data_api12_df.API12 == api12
        ].copy()
        survey_xyz_wh_adjusted: pd.DataFrame = survey_xyz.copy()
        survey_xyz_wh_adjusted["x_coor"] = (
            survey_xyz_wh_adjusted["x_coor"] + api12_df.SURF_x_rel.iloc[0]
        )
        survey_xyz_wh_adjusted["y_coor"] = (
            survey_xyz_wh_adjusted["y_coor"] + api12_df.SURF_y_rel.iloc[0]
        )

        return survey_xyz_wh_adjusted

    def plot_field_wells(self) -> None:
        if self.output_data_well_path:
            import math

            import matplotlib.pyplot as plt

            fig = plt.figure()
            ax = fig.add_subplot(111, projection="3d")
            api12_list: list[Any] = list(self.output_data_well_path.keys())
            labels_plotted: list[str] = []
            for api12 in api12_list:
                api10: int | str = self.get_API10_from_well_API(api12)
                # stones_custom_list = [6081240095, 6081240099, 6081240117, 6081240104, 6081240123, 6081240112, 6081240110]  # noqa: E501
                # custom_list = [6081240095, 6081240099, 6081240117, 6081240104, 6081240123, 6081240112, 6081240110]  # noqa: E501
                # if api10 in custom_list:
                custom_list: list[int] = []
                if api10 not in custom_list:
                    survey_xyz: pd.DataFrame = self.output_data_well_path[api12]
                    x: Any = survey_xyz["x_coor"]
                    y: Any = survey_xyz["y_coor"]
                    z: Any = survey_xyz["z_coor"]
                    try:
                        api10_value: int | str = self.get_API10_from_well_API(api12)
                        label: str = (
                            self.output_data_well_df[
                                self.output_data_well_df.API10 == api10_value
                            ]["Well Name"].values[0]
                            + "-"
                            + self.output_data_well_df[
                                self.output_data_well_df.API10 == api10_value
                            ]["Sidetrack and Bypass"].values[0]
                        )
                        label = label.strip()
                    except Exception:
                        label = str(api12)
                    if label not in labels_plotted:
                        labels_plotted.append(label)
                        ax.plot3D(x, y, z, label=label, linewidth=1)
                        ax.xaxis.set_tick_params(labelsize=7)
                        ax.yaxis.set_tick_params(labelsize=7)
                        ax.zaxis.set_tick_params(labelsize=7)
                        ax.set_xlabel("Easting (ft)", fontsize=8)
                        ax.set_ylabel("Northing (ft)", fontsize=8)
                        ax.set_zlabel("TVD (ft)", fontsize=8)

            ax.invert_zaxis()
            xy_equal_flag: bool = True
            if xy_equal_flag:
                ylim_old: tuple[float, float] = ax.get_ylim()
                xlim_old: tuple[float, float] = ax.get_xlim()
                ylim_new: list[float] = []
                xlim_new: list[float] = []
                yrange: float = ylim_old[1] - ylim_old[0]
                xrange: float = xlim_old[1] - xlim_old[0]
                if yrange > xrange:
                    range_val: float = round(yrange / 1000) * 1000
                    ylim_new.append(math.floor(ylim_old[0] / 1000) * 1000)
                    ylim_new.append(math.ceil(ylim_old[1] / 1000) * 1000)
                    range_val = ylim_new[1] - ylim_new[0]
                    xlim_new.append(math.floor(xlim_old[0] / 1000) * 1000)
                    xlim_new.append(range_val + xlim_new[0])
                else:
                    xlim_new.append(math.floor(xlim_old[0] / 1000) * 1000)
                    xlim_new.append(math.ceil(xlim_old[1] / 1000) * 1000)
                    range_val = xlim_new[1] - xlim_new[0]
                    ylim_new.append(math.floor(ylim_old[0] / 1000) * 1000)
                    ylim_new.append(range_val + ylim_new[0])

                ax.set_xlim(xlim_new)
                ax.set_ylim(xlim_new)
            ax.legend(
                bbox_to_anchor=(1, 0),
                loc="lower right",
                bbox_transform=fig.transFigure,
                ncol=5,
                fontsize=6,
            )
            fig.savefig(
                self.cfg["Analysis"]["result_folder"]
                + self.cfg["Analysis"]["file_name_for_overwrite"]
                + "_well_paths.png",
                bbox_inches="tight",
                dpi=800,
            )
            plt.close()
