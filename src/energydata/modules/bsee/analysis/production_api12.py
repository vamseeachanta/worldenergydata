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
        if production_groups is not None:
            production_group_api12_summary_df = pd.DataFrame()
            production_group_data_df = pd.DataFrame()
            production_api12_array = []
            for group_idx in range(0, len(production_groups)):
                production_group = production_groups[group_idx]
                api12_array = cfg['data']['groups'][group_idx]['api12']
                for api12_idx in range(0, len(api12_array)):
                    api12 = api12_array[api12_idx]
                    api12_df = production_group[api12]

                    cfg, prod_anal_api12_dict= self.analyze_data_for_api12(cfg, api12, api12_df)
                    summary_df = prod_anal_api12_dict['summary_df']
                    prod_anal_api12_df = prod_anal_api12_dict['api12_df']
                    production_api12_array.append(prod_anal_api12_df)
                    production_group_api12_summary_df = pd.concat([production_group_api12_summary_df, summary_df], ignore_index=True)
                    if len(prod_anal_api12_df) == 0:
                        prod_anal_api12_df = pd.DataFrame(columns=['PRODUCTION_DATETIME', 'O_PROD_RATE_BOPD'])
                    prod_anal_api12_df_PROD_RATE = prod_anal_api12_df[['PRODUCTION_DATETIME', 'O_PROD_RATE_BOPD']]
                    prod_anal_api12_df_PROD_RATE = prod_anal_api12_df_PROD_RATE.rename(columns={'O_PROD_RATE_BOPD': api12})
                    production_group_data_df = pd.concat([production_group_data_df, prod_anal_api12_df_PROD_RATE], ignore_index=True)
                    production_group_data_df = production_group_data_df.replace({np.nan: None})

                block_number = cfg['data']['groups'][group_idx].get('bottom_block', [None])[0]
                if block_number is None:
                    label = str(group_idx)
                else:
                    label = str(block_number)

                file_label = 'block_prod_summ_' + label
                file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.csv')
                production_group_api12_summary_df.to_csv(file_name, index=False)

                file_label = 'block_prod_all_' + label
                file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.csv')
                production_group_data_df.to_csv(file_name, index=False)

                file_label = 'block_prod_raw_' + label
                SheetNames = [str(item) for item in api12_array]
                file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.xlsx')
                cfg_temp = {'FileName': file_name,
                        'SheetNames': SheetNames,
                        "thin_border": True}
                save_data.DataFrameArray_To_xlsx_openpyxl(production_api12_array, cfg_temp)
                
                
        return cfg

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

        values = [well_api12, well_api10, 0, 0, 0, 0, completion_name, None]
        production_summary_df.loc[0] = values

        total_well_production = df_temp.MON_O_PROD_VOL.sum() / 1000 / 1000
        api12_production = df_temp[['PRODUCTION_DATETIME', 'O_PROD_RATE_BOPD']].copy()
        api12_production.rename(columns={'PRODUCTION_DATETIME': 'date_time'}, inplace=True)
        api12_production = api12_production.round(decimals=3)
        api12_production['date_time'] = [item.strftime('%Y-%m-%d') for item in api12_production['date_time'].to_list()]

        if len(df_temp) > 0 and total_well_production > 0:
            df_row_index = df_temp.index[0]

            current_value = production_summary_df.O_CUMMULATIVE_PROD_MMBBL.iloc[0]
            production_summary_df.loc[df_row_index, "O_CUMMULATIVE_PROD_MMBBL"] = current_value + total_well_production

            DAYS_ON_PROD = df_temp.DAYS_ON_PROD.sum()
            production_summary_df.loc[df_row_index, "DAYS_ON_PROD"] = DAYS_ON_PROD

            production_summary_df.loc[df_row_index, "O_MEAN_PROD_RATE_BOPD"] = df_temp.MON_O_PROD_VOL.sum() / DAYS_ON_PROD

            production_summary_df.loc[df_row_index, "O_PROD_STATUS"] = 1

            current_completion_name = production_summary_df.loc[df_row_index, "COMPLETION_NAME"]


            if current_completion_name == "":
                production_summary_df.loc[df_row_index, "COMPLETION_NAME"] = completion_name
            else:
                completion_name = current_completion_name + ',' + completion_name
                production_summary_df.loc[df_row_index, "COMPLETION_NAME"] = completion_name

            production_summary_df.loc[df_row_index, "monthly_production"] = json.dumps(
                api12_production.to_dict(orient='records'))


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
