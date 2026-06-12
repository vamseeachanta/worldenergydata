from pathlib import Path

import pandas as pd

from worldenergydata.bsee.data.sources.zip.production_data import GetProdDataFromZip

# Backward-compatible module-level handle used by legacy tests and callers that
# patch ``worldenergydata.bsee.data.production.production_data_sources.production_from_zip``.
production_from_zip = GetProdDataFromZip()


class ProductionDataFromSources:

    def __init__(self):
        pass

    @property
    def _production_from_zip(self):
        """Return the active zip source, honoring module-level monkeypatches."""
        return production_from_zip

    def router(self, cfg):

        pass

    def get_data(self, cfg):

        if cfg["data"].get("source") == "csv":
            return cfg, self.get_production_from_csv(cfg)

        # cfg = self.get_groups_data(cfg)
        production_data_groups = []
        if "by" in cfg["data"] and cfg["data"]["by"] == "zip":
            api12 = cfg["data"]["groups"][0]["api12"][0]
            cfg = self.get_production_from_zip(cfg, api12)

        for group_idx in range(0, len(cfg["data"]["groups"])):
            production_data_group = cfg["data"]["groups"][group_idx].copy()
            api12_array = production_data_group["api12"]

            df_api12_array = self._production_from_zip.get_data_by_api12_array(
                cfg, api12_array
            )
            production_data_groups.append(df_api12_array)

        return cfg, production_data_groups

    def get_production_from_csv(self, cfg):
        """Load grouped API12 production frames from local workflow CSV files."""
        production_data_groups = []
        analysis_root = Path(cfg["Analysis"]["analysis_root_folder"])

        for group in cfg["data"].get("groups", []):
            api12_array = [str(api12) for api12 in group.get("api12", [])]
            frames = []
            for file_name in group.get("production", {}).get("files", []):
                file_path = Path(file_name)
                if not file_path.is_absolute():
                    file_path = analysis_root / file_path
                df = pd.read_csv(file_path, dtype={"API_WELL_NUMBER": str})
                frames.append(self._normalize_production_csv(df))

            if frames:
                group_df = pd.concat(frames, ignore_index=True)
            else:
                group_df = pd.DataFrame()

            api12_dataframes = {}
            for api12 in api12_array:
                if group_df.empty:
                    api12_dataframes[api12] = pd.DataFrame()
                else:
                    api12_dataframes[api12] = group_df[
                        group_df["API_WELL_NUMBER"].astype(str) == api12
                    ].copy()
            production_data_groups.append(api12_dataframes)

        return production_data_groups

    def _normalize_production_csv(self, df):
        rename_map = {
            "PROD_DATE": "PRODUCTION_DATE",
            "OIL_PRODUCTION": "MON_O_PROD_VOL",
            "GAS_PRODUCTION": "MON_G_PROD_VOL",
            "WATER_PRODUCTION": "MON_WTR_PROD_VOL",
        }
        normalized = df.rename(columns=rename_map).copy()

        defaults = {
            "LEASE_NUMBER": "",
            "COMPLETION_NAME": "",
            "DAYS_ON_PROD": 0,
            "PRODUCT_CODE": "O",
            "MON_O_PROD_VOL": 0,
            "MON_G_PROD_VOL": 0,
            "MON_WTR_PROD_VOL": 0,
            "API_WELL_NUMBER": "",
            "WELL_STAT_CD": "",
            "AREA_CODE_BLOCK_NUM": "",
            "OPERATOR_NUM": "",
            "SORT_NAME": "",
            "BOEM_FIELD": "",
            "INJECTION_VOLUME": 0,
            "PROD_INTERVAL_CD": "",
            "FIRST_PROD_DATE": "",
            "UNIT_AGT_NUMBER": "",
            "UNIT_ALOC_SUFFIX": "",
        }
        for column, default in defaults.items():
            if column not in normalized.columns:
                normalized[column] = default

        normalized["API_WELL_NUMBER"] = normalized["API_WELL_NUMBER"].astype(str)
        normalized["PRODUCTION_DATE"] = normalized["PRODUCTION_DATE"].apply(
            self._production_month
        )
        for column in [
            "DAYS_ON_PROD",
            "MON_O_PROD_VOL",
            "MON_G_PROD_VOL",
            "MON_WTR_PROD_VOL",
            "INJECTION_VOLUME",
        ]:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
            normalized[column] = normalized[column].fillna(0)

        return normalized

    def _production_month(self, value):
        if pd.isna(value):
            return 0
        text = str(value).strip()
        if text.endswith(".0"):
            text = text[:-2]
        if len(text) == 6 and text.isdigit():
            return int(text)
        timestamp = pd.to_datetime(text, errors="raise")
        return int(timestamp.strftime("%Y%m"))

    def get_production_from_zip(self, cfg, api12):

        self._production_from_zip.get_production_data_by_wellapi12(cfg, api12)
        return cfg

    # Old methods that are not used anymore but kept for reference

    # def get_groups_data(self, cfg):

    #     production_data_flag = cfg['data'].get('production_data', False)

    #     output_data = []
    #     if production_data_flag:
    #         input_items = cfg['data']['groups']
    #         for input in input_items:
    #             api12_array = input.get('api12', [])
    #             for api12 in api12_array:
    #                 input_item = {'api12': [api12], 'label': str(api12)}
    #                 output_data = self.generate_output_item(cfg, output_data, input_item)

    #     production_data = {'type': 'csv', 'groups': output_data }
    #     cfg[cfg['basename']].update({'production_data': production_data})

    #     return cfg

    # def generate_output_item(self, cfg, output_data, input_item):

    #     label = input_item['api12'][0]
    #     output_path = os.path.join(cfg['Analysis']['result_folder'], 'Data')
    #     if output_path is None:
    #         result_folder = cfg['Analysis']['result_folder']
    #         output_path = os.path.join(result_folder, 'Data')

    #     analysis_root_folder = cfg['Analysis']['analysis_root_folder']
    #     is_dir_valid, output_path = is_dir_valid_func(output_path, analysis_root_folder)

    #     output_file = os.path.join(output_path, str(label) + '.csv')

    #     input_item_csv_cfg = deepcopy(input_item)
    #     input_item_csv_cfg.update({'label': label, 'file_name': output_file})
    #     output_data.append(input_item_csv_cfg)

    #     return output_data
