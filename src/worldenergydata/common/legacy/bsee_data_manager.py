from __future__ import annotations

import os
from typing import Any

import pandas as pd
from assetutilities.common.database import get_db_connection


class BSEEData:

    def __init__(self, cfg: dict[str, Any] | None = None) -> None:
        self.cfg: dict[str, Any] | None = None
        self.dbe: Any = None
        self.connection_status: Any = None
        self.assign_cfg(cfg)
        input_bsee_db_properties = cfg["input_bsee_db"]
        self.dbe, self.connection_status = get_db_connection(input_bsee_db_properties)

    def assign_cfg(self, cfg: dict[str, Any] | None) -> None:
        self.cfg = cfg

    def get_api10_list(self) -> list[str]:
        api10_list: list[str] = []
        filename = os.path.join("data_manager\\sql", "bsee.get_all_wells.sql")
        if os.path.isfile(filename):
            try:
                df = self.dbe.executeScriptsFromFile(filename)
                api10_list = df.API10.to_list()
            except Exception:
                print("Error getting data from Database")
        else:
            print("Not a valid filename")

        return api10_list

    def get_well_data_by_api10(self, api10: str) -> pd.DataFrame:
        filename = os.path.join("data_manager\\sql", "bsee.well_data_by_api10.sql")
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_production_data_by_api10(self, api10: str) -> pd.DataFrame:
        filename = os.path.join(
            "data_manager\\sql", "bsee.production_data_by_api10.sql"
        )
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_WAR_summary_by_api10(self, api10: str) -> pd.DataFrame:
        filename = os.path.join(
            "data_manager\\sql", "bsee.WAR_summary_data_by_api10.sql"
        )
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_directional_surveys_by_api10(self, api10: str) -> pd.DataFrame:
        filename = os.path.join(
            "data_manager\\sql", "bsee.directional_surveys_data_by_api10.sql"
        )
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_ST_BP_and_tree_height_by_api10(self, api10: str) -> pd.DataFrame:
        filename = os.path.join(
            "data_manager\\sql", "bsee.ST_BP_and_tree_height_data_by_api10.sql"
        )
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_well_tubulars_data_by_api10(self, api10: str) -> pd.DataFrame:
        filename = os.path.join(
            "data_manager\\sql", "bsee.well_tubulars_data_by_api10.sql"
        )
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_completion_data_by_api10(self, api10: str) -> pd.DataFrame:
        filename = os.path.join(
            "data_manager\\sql", "bsee.completion_data_by_api10.sql"
        )
        df = self.get_data_by_api12(api10, filename)
        return df

    def get_data_by_api12(self, api10: str, filename: str) -> pd.DataFrame:
        df = pd.DataFrame()
        if os.path.isfile(filename):
            try:
                df = self.dbe.executeScriptsFromFile(filename, [api10])
            except Exception:
                print("Error getting data from Database")
        else:
            print("Not a valid filename: {}".format(filename))
        return df
