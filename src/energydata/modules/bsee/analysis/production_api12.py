# Standard library imports
import os
import json
import logging

# # # Third party imports
import numpy as np
import pandas as pd
from energydata.modules.bsee.data.bsee_data import BSEEData
from energydata.common.legacy.data import DateTimeUtility

from assetutilities.common.data import SaveData
# from energydata.common.bsee_data_manager import BSEEData

# from energydata.common.data import AttributeDict, transform_df_datetime_to_str

bsee_data = BSEEData()
dtu = DateTimeUtility()
save_data = SaveData()

class ProductionAPI12Analysis():

    def __init__(self):
        pass

    def router(self, cfg):
        pass

    def run_production_data_analysis(self, cfg, data):
        production_groups = data.get('production_data', None)
        production_data_analysis_groups = {}
        if production_groups is None:
            raise ValueError("No production data found in the provided data.")

        production_summary_df_groups = pd.DataFrame()
        production_df_api12s = []  # Reset for each group to avoid unintended data accumulation
        production_analysis_df_groups = pd.DataFrame(columns=['PRODUCTION_DATETIME'])
        for group_idx in range(0, len(production_groups)):
            production_analysis_df_group = pd.DataFrame(columns=['PRODUCTION_DATETIME'])
            production_group = production_groups[group_idx]
            api12_array = cfg['data']['groups'][group_idx]['api12']
            for api12_idx in range(0, len(api12_array)):
                api12 = api12_array[api12_idx]
                production_df_api12 = production_group[api12]

                cfg, production_analysis_dict_api12= self.analyze_data_for_api12(cfg, api12, production_df_api12)
                summary_df_api12 = production_analysis_dict_api12['summary_df']
                production_analysis_df_api12 = production_analysis_dict_api12['api12_df']

                production_df_api12s.append(production_analysis_df_api12)
                production_summary_df_groups = pd.concat([production_summary_df_groups, summary_df_api12], ignore_index=True)
                if len(production_analysis_df_api12) == 0:
                    production_analysis_df_api12 = pd.DataFrame(columns=['PRODUCTION_DATETIME', 'O_PROD_RATE_BOPD'])
                prod_anal_api12_df_PROD_RATE = production_analysis_df_api12[['PRODUCTION_DATETIME', 'O_PROD_RATE_BOPD']]
                prod_anal_api12_df_PROD_RATE = prod_anal_api12_df_PROD_RATE.rename(columns={'O_PROD_RATE_BOPD': api12})
                if len(production_analysis_df_api12) > 0:
                    production_analysis_df_group = pd.merge(production_analysis_df_group, prod_anal_api12_df_PROD_RATE, on=['PRODUCTION_DATETIME'], how='outer')
                    production_analysis_df_group = production_analysis_df_group.replace({np.nan: None})
                    production_analysis_df_group.sort_values(by=['PRODUCTION_DATETIME'], inplace=True)
                    production_analysis_df_group.reset_index(inplace=True, drop=True)

            production_analysis_df_groups = pd.merge(production_analysis_df_groups, production_analysis_df_group, on=['PRODUCTION_DATETIME'], how='outer')

            self.group_save_result(cfg, group_idx, production_analysis_df_group)

        self.groups_save_result(cfg, production_summary_df_groups, production_df_api12s, production_analysis_df_groups, api12_array)

        production_data_analysis_groups['production_df_api12s'] = production_df_api12s
        production_data_analysis_groups['production_analysis_df_groups'] = production_analysis_df_groups
        production_data_analysis_groups['production_summary_df_groups'] = production_summary_df_groups

        return cfg, production_data_analysis_groups

    def group_save_result(self, cfg, group_idx, production_analysis_df_group):
        block_number = cfg['data']['groups'][group_idx].get('bottom_block', [None])[0]
        if block_number is None:
            group_label = str(group_idx)
        else:
            group_label = str(block_number)

        file_label = 'prod_all_block_' + group_label
        file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.csv')
        production_analysis_df_group.to_csv(file_name, index=False)

    def groups_save_result(self, cfg, production_summary_df_groups, production_df_api12s, production_analysis_df_groups, api12_array, group_label):
        groups_label = cfg['meta'].get('label', None)
        if groups_label is None:
            groups_label = cfg['Analysis']['file_name_for_overwrite']

        file_label = 'prod_raw_block_' + group_label
        SheetNames = [str(item) for item in api12_array]
        file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.xlsx')
        cfg_temp = {"FileName": file_name,
                        "SheetNames": SheetNames,
                        "thin_border": True}
        save_data.DataFrameArray_To_xlsx_openpyxl(
                production_df_api12s, cfg_temp
            )

        file_label = 'prod_summ_block_' + group_label
        file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.csv')
        production_summary_df_groups.to_csv(file_name, index=False)


    def analyze_data_for_api12(self, cfg, api12, api12_df):
        api12_df_analyzed = api12_df.copy()
        summary_df = pd.DataFrame()
        completion_names = []
        if not api12_df.empty:
            completion_names = api12_df.COMPLETION_NAME.unique()

            for completion_name in completion_names:
                api12_df_analyzed = api12_df[api12_df.COMPLETION_NAME == completion_name].copy()
                api12_df_analyzed = self.add_production_rate_and_date_to_df(api12_df_analyzed)
                api12_df_analyzed.sort_values(by=['PRODUCTION_DATETIME'], inplace=True)
                api12_df_analyzed.reset_index(inplace=True)
                if api12_df_analyzed.O_PROD_RATE_BOPD.max() > 0:
                    api10 = str(api12)[0:10]
                    summary_df = self.add_production_and_completion_name_to_well_data(api12, api10, completion_name, api12_df_analyzed)

        prod_anal_api12_dict = {'api12_df': api12_df_analyzed, 'api12': api12, 'summary_df': summary_df, 'completion_names': completion_names}

        return cfg, prod_anal_api12_dict

    def add_production_and_completion_name_to_well_data(self, well_api12, well_api10, completion_name, df_temp):

        columns = ['API12', 'API10', 'O_PROD_STATUS', 'O_CUMMULATIVE_PROD_MMBBL', 'DAYS_ON_PROD', 'O_MEAN_PROD_RATE_BOPD', 'COMPLETION_NAME', 'monthly_production']
        production_summary_df = pd.DataFrame(columns=columns)
        production_summary_df = production_summary_df.astype({'API12': str, 'API10': str, 'O_PROD_STATUS': int, 'O_CUMMULATIVE_PROD_MMBBL': float, 'DAYS_ON_PROD': int, 'O_MEAN_PROD_RATE_BOPD': float, 'COMPLETION_NAME': str, 'monthly_production': float})

        values = [well_api12, well_api10, 0.0, 0.0, 0.0, 0.0, completion_name, None]
        production_summary_df.loc[0] = values

        total_well_production = df_temp.MON_O_PROD_VOL.sum() / 1000 / 1000
        api12_production = df_temp[['PRODUCTION_DATETIME', 'O_PROD_RATE_BOPD']].copy()
        api12_production.rename(columns={'PRODUCTION_DATETIME': 'date_time'}, inplace=True)
        api12_production = api12_production.round(decimals=3)
        api12_production['date_time'] = [item.strftime('%Y-%m-%d') for item in api12_production['date_time'].to_list()]

        if len(df_temp) > 0 and total_well_production > 0:
            df_row_index = df_temp.index[0]

            current_value = production_summary_df.O_CUMMULATIVE_PROD_MMBBL.iloc[0]
            O_CUMMULATIVE_PROD_MMBBL = current_value + total_well_production
            production_summary_df.loc[df_row_index, "O_CUMMULATIVE_PROD_MMBBL"] = float(O_CUMMULATIVE_PROD_MMBBL)

            DAYS_ON_PROD = df_temp.DAYS_ON_PROD.sum()
            production_summary_df.loc[df_row_index, "DAYS_ON_PROD"] = DAYS_ON_PROD

            O_MEAN_PROD_RATE_BOPD = df_temp.MON_O_PROD_VOL.sum() / DAYS_ON_PROD
            production_summary_df.loc[df_row_index, "O_MEAN_PROD_RATE_BOPD"] = float(O_MEAN_PROD_RATE_BOPD)

            production_summary_df.loc[df_row_index, "O_PROD_STATUS"] = 1

            current_completion_name = production_summary_df.loc[df_row_index, "COMPLETION_NAME"]

            if current_completion_name == "":
                production_summary_df.loc[df_row_index, "COMPLETION_NAME"] = completion_name
            else:
                completion_name = current_completion_name + ',' + completion_name
                production_summary_df.loc[df_row_index, "COMPLETION_NAME"] = completion_name

        return production_summary_df

    def add_production_rate_and_date_to_df(self, df):
        import datetime
        production_date = []
        production_rate = []
        for df_row in range(0, len(df)):
            year = int(df.PRODUCTION_DATE.iloc[df_row] / 100)
            month = df.PRODUCTION_DATE.iloc[df_row] % year
            date_time = datetime.datetime(year, month, 1)
            date_time = dtu.last_day_of_month(date_time.date())
            if df.DAYS_ON_PROD.iloc[df_row] != 0:
                rate = df.MON_O_PROD_VOL.iloc[df_row] / df.DAYS_ON_PROD.iloc[df_row]
            else:
                rate = 0
            production_date.append(date_time)
            production_rate.append(rate)

        df['PRODUCTION_DATETIME'] = production_date
        df['O_PROD_RATE_BOPD'] = production_rate
        return df
