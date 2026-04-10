"""ONG Field Development Components - Refactored.

This module provides the main ONGFDComponents class that coordinates
field development analysis. Functions have been extracted to focused modules:

- ong_fd_utils.py: Utility functions (GIS, API conversion, saving)
- ong_fd_production.py: Production data processing
- ong_fd_drilling.py: Drilling and rig days calculations
- ong_fd_wellpath.py: Well path and survey processing
- ong_fd_tubulars.py: Casing and tubular data
- ong_fd_geometry.py: Well distances and geometry calculations
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd
from assetutilities.common.data import AttributeDict
from assetutilities.common.database import Database, get_db_connection

from worldenergydata.common.legacy.bsee_data_manager import BSEEData
from worldenergydata.common.legacy.data import (
    DateTimeUtility,
    transform_df_datetime_to_str,
)

# Import from refactored modules
from .ong_fd_drilling import assign_st_bp_tree_info, get_rig_days_and_drilling_wt
from .ong_fd_geometry import evaluate_well_distances, prepare_completion_data
from .ong_fd_production import (
    add_production_from_all_wells,
    add_production_rate_and_date,
    add_production_to_well_data,
    prepare_field_production,
    prepare_field_production_rate,
)
from .ong_fd_summary import calculate_drilling_completion_summary
from .ong_fd_tubulars import (
    prepare_casing_data,
    prepare_casing_tubular_summary_all_wells,
)
from .ong_fd_utils import (
    add_gis_info_to_df,
    delete_well_data_for_api10,
    get_api10_from_well_api,
    save_output_data_to_excel,
    transform_list_to_unique,
)
from .ong_fd_wellpath import plot_field_wells, prepare_well_paths

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)

dtu = DateTimeUtility()


class ONGFDComponents:
    """ONG Field Development Components for field analysis.

    This class coordinates field development analysis including:
    - Well data preparation
    - Production data processing
    - Drilling/completion analysis
    - Well path calculations
    - Field summary generation
    """

    def __init__(self, cfg: dict[str, Any]) -> None:
        """Initialize ONGFDComponents with configuration.

        Args:
            cfg: Configuration dictionary
        """
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
        """Assign configuration and initialize instance variables.

        Args:
            cfg: Configuration dictionary
        """
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
        self.field_x_ref: float = 0.0
        self.field_y_ref: float = 0.0

    def get_all_bsee_blocks(self) -> list[str]:
        """Get all BSEE blocks from input data.

        Returns:
            List of BSEE block names
        """
        all_bsee_blocks: list[str] = list(
            self.dbe.input_data_all_bsee_blocks["BOTM_FLD_NAME_CD"]
        )
        return all_bsee_blocks

    def get_raw_data_for_well_analysis(self) -> None:
        """Get raw data for well analysis."""
        self.api10_list: list[str] = self.bsee_data.get_api10_list()

    def run_analysis_for_all_wells(self) -> None:
        """Run analysis for all wells in the API10 list."""
        for api10 in self.api10_list[0:20]:
            self.get_bsee_data_and_prepare_data_for_api10(api10)
            self.save_api10_result(api10)

    def save_api10_result(self, api10: str) -> None:
        """Save analysis result for a specific API10.

        Args:
            api10: API10 number
        """
        delete_well_data_for_api10(self.dbe_output, api10)
        self.dbe_output.save_to_db(self.output_data_well_df, "analysis")

    def get_bsee_data_and_prepare_data_for_api10(self, api10: str) -> None:
        """Get BSEE data and prepare analysis for a specific API10.

        Args:
            api10: API10 number
        """
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
        self.prepare_casing_data(well_data, well_tubulars_data)
        self.prepare_completion_data(completion_data)
        self.prepare_well_paths(directional_surveys)
        self.prepare_formation_data()
        self.prepare_field_well_data()

    def get_raw_data_for_field_analysis(self) -> None:
        """Get raw data for field analysis."""
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
        """Prepare field API12 data for analysis."""
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
        """Prepare API10 data from API12."""
        API10: list[int | str] = []
        for df_row in range(0, len(self.dbe.input_data_well)):
            well_api: Any = self.dbe.input_data_well.API12.iloc[df_row]
            api10_value: int | str = get_api10_from_well_api(well_api)
            API10.append(api10_value)
        self.dbe.input_data_well["API10"] = API10
        logger.info("Well API data is prepared")

    def prepare_api12_data(self, well_data: pd.DataFrame) -> None:
        """Prepare API12 data with GIS and production columns.

        Args:
            well_data: Well data DataFrame
        """
        self.output_data_api12_df: pd.DataFrame = well_data.copy()

        # Add GIS info using utility function
        self.output_data_api12_df, self.field_x_ref, self.field_y_ref = (
            add_gis_info_to_df(self.output_data_api12_df)
        )
        logger.info("GIS data is formatted")

        # Add production columns
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

    def prepare_production_data(self, production_data: pd.DataFrame) -> None:
        """Prepare production data for analysis.

        Args:
            production_data: Production data DataFrame
        """
        self.output_data_production_df_array: dict[str, pd.DataFrame] = {}
        completion_name_list: list[str] = production_data.COMPLETION_NAME.unique()

        for completion_name in completion_name_list:
            df_temp: pd.DataFrame = production_data[
                production_data.COMPLETION_NAME == completion_name
            ].copy()
            df_temp = add_production_rate_and_date(df_temp)
            df_temp.sort_values(by=["PRODUCTION_DATETIME"], inplace=True)
            df_temp.reset_index(inplace=True)

            if df_temp.O_PROD_RATE_BOPD.max() > 0:
                well_api12: Any = df_temp.API12.iloc[0]
                well_api10: int | str = get_api10_from_well_api(well_api12)

                self.output_data_field_production_rate_df = (
                    prepare_field_production_rate(
                        df_temp,
                        completion_name,
                        self.output_data_field_production_rate_df,
                    )
                )
                self.output_data_field_production_df = prepare_field_production(
                    df_temp, completion_name, self.output_data_field_production_df
                )
                self.output_data_api12_df = add_production_to_well_data(
                    self.output_data_api12_df, well_api10, completion_name, df_temp
                )
                self.output_data_production_df_array.update({completion_name: df_temp})

        if len(self.output_data_production_df_array) != 0:
            (
                self.output_data_field_production_rate_df,
                self.output_data_field_production_df,
                self.production_summary_df,
            ) = add_production_from_all_wells(
                self.output_data_field_production_rate_df,
                self.output_data_field_production_df,
                self.cfg,
            )

            self.field_summary["Cummulative Production, MMbbls"] = {
                "PRODUCTION_DATETIME": self.output_data_field_production_df[
                    "PRODUCTION_DATETIME"
                ].tolist(),
                "CUMULATIVE_MONTLY_PRODUCTION_MMbbl": self.output_data_field_production_df[
                    "CUMULATIVE_MONTLY_PRODUCTION_MMbbl"
                ].tolist(),
            }

        logger.info("Production data is prepared")

    def add_sidetracklabel_rig_rigdays(
        self, WAR_summary: pd.DataFrame, ST_BP_and_tree_height: pd.DataFrame
    ) -> None:
        """Add sidetrack labels, rig info, and rig days to well data.

        Args:
            WAR_summary: Well Activity Report summary DataFrame
            ST_BP_and_tree_height: Sidetrack/Bypass and tree height DataFrame
        """
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

            sidetrack_no, bypass_no, tree_elevation_aml = assign_st_bp_tree_info(
                ST_BP_and_tree_height, well_api12
            )
            self.output_data_api12_df["Sidetrack No"].iloc[df_row] = sidetrack_no
            self.output_data_api12_df["Bypass No"].iloc[df_row] = bypass_no
            self.output_data_api12_df["Tree Height Above Mudline"].iloc[
                df_row
            ] = tree_elevation_aml

            rig_str, MAX_DRILL_FLUID_WGT, well_days_dict = get_rig_days_and_drilling_wt(
                WAR_summary,
                well_api12,
                self.output_data_api12_df,
                self.max_allowed_npt,
            )

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

    def evaluate_well_distances(self) -> None:
        """Evaluate well distances and horizontal departures."""
        (
            self.output_data_api12_df,
            self.field_summary,
            self.output_data_producing_api12_df,
        ) = evaluate_well_distances(self.output_data_api12_df, self.field_summary)

    def prepare_casing_data(
        self, well_data: pd.DataFrame, well_tubulars_data: pd.DataFrame
    ) -> None:
        """Prepare casing data from well tubulars.

        Args:
            well_data: Well data DataFrame
            well_tubulars_data: Well tubulars DataFrame
        """
        self.casing_tubulars = prepare_casing_data(
            well_data, well_tubulars_data, self.output_data_api12_df, self.cfg
        )

        if len(self.casing_tubulars) > 0:
            self.tubular_summary = prepare_casing_tubular_summary_all_wells(
                well_data, self.casing_tubulars, self.output_data_api12_df, self.cfg
            )

    def prepare_completion_data(self, completion_data: pd.DataFrame) -> None:
        """Prepare completion data with GIS coordinates.

        Args:
            completion_data: Completion data DataFrame
        """
        self.output_completions = prepare_completion_data(
            completion_data, self.field_x_ref, self.field_y_ref, self.cfg
        )

    def prepare_formation_data(self) -> None:
        """Prepare formation data (placeholder)."""
        pass

    def prepare_field_well_data(self) -> None:
        """Prepare field well data by aggregating sidetracks."""
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
            old_list: list[str] = list(self.output_data_well_df["Well Name"])
            new_list: list[str] = transform_list_to_unique(old_list)
            self.output_data_well_df["Well Name"] = new_list

    def get_drilling_completion_summary(self) -> list[dict[str, Any]]:
        """Get drilling and completion summary statistics.

        Returns:
            List of summary dictionaries with Description and Value keys
        """
        return calculate_drilling_completion_summary(
            self.output_data_api12_df,
            self.output_data_well_df,
            self.oil_pressure_gradient,
            self.over_balance_ppg,
            self.rig_day_rate_loaded,
            self.sunk_cost_per_completed_well,
            self.cost_of_subsea_equipment,
        )

    def prepare_field_summary(self) -> None:
        """Prepare field summary DataFrame."""
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
        """Prepare visualizations using VisualizationComponents."""
        from assetutilities.common.visualization_components import (
            VisualizationComponents,
        )

        vc = VisualizationComponents(self.cfg)
        vc.prepare_visualizations(self)

    def save_data(self) -> None:
        """Save application data to output database."""
        self.dbe_output.save_application_data(self)

    def save_output_data_to_local_computer(self) -> None:
        """Save output data to local Excel file."""
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

            file_name_without_extension: str = (
                self.cfg["Analysis"]["result_folder"]
                + self.cfg["Analysis"]["file_name"]
            )
            save_output_data_to_excel(
                df_array, label_array, file_name_without_extension
            )

    def prepare_well_paths(self, directional_surveys: pd.DataFrame) -> None:
        """Prepare well paths from directional surveys.

        Args:
            directional_surveys: Directional survey DataFrame
        """
        self.output_data_well_path, self.output_data_api12_df = prepare_well_paths(
            directional_surveys, self.output_data_api12_df, self.output_data_well_df
        )

    def plot_field_wells(self) -> None:
        """Plot 3D well paths for the field."""
        plot_field_wells(self.output_data_well_path, self.output_data_well_df, self.cfg)

    # Backward compatibility - keep method name
    def get_API10_from_well_API(self, well_api: Any) -> int | str:
        """Get API10 from well API (backward compatibility).

        Args:
            well_api: Well API number

        Returns:
            API10 number
        """
        return get_api10_from_well_api(well_api)

    def get_rig_days_by_well_activity(self, well_api12: Any) -> None:
        """Get rig days by well activity (placeholder).

        Args:
            well_api12: Well API12 number
        """
        pass
