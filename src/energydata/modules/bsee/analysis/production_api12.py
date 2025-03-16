# Standard library imports
import os
import json
import logging

# # # Third party imports
import pandas as pd
from energydata.modules.bsee.data.bsee_data import BSEEData
from energydata.common.legacy.data import DateTimeUtility

# from energydata.common.bsee_data_manager import BSEEData

# from energydata.common.data import AttributeDict, transform_df_datetime_to_str

bsee_data = BSEEData()
dtu = DateTimeUtility()

class ProductionAPI12Analysis():

    def __init__(self):
        pass

    def router(self, cfg, api12_production_data):
        self.prepare_production_data(cfg, api12_production_data)

    def prepare_production_data(self,cfg, production_data):
        self.output_data_production_df_array = {}
        completion_name_list = production_data.COMPLETION_NAME.unique()
        for completion_name in completion_name_list:
            df_temp = production_data[production_data.COMPLETION_NAME == completion_name].copy()
            df_temp = self.add_production_rate_and_date_to_df(df_temp)
            df_temp.sort_values(by=['PRODUCTION_DATETIME'], inplace=True)
            df_temp.reset_index(inplace=True)
            if df_temp.O_PROD_RATE_BOPD.max() > 0:
                well_api12 = df_temp.API_WELL_NUMBER.iloc[0]
                well_api10 = str(well_api12)[0:10]
                self.add_production_and_completion_name_to_well_data(well_api12, well_api10, completion_name, df_temp)
                self.output_data_production_df_array.update({completion_name: df_temp})
                file_name = str(well_api12) + '_' + completion_name + '_production_data.csv'
                file_name = os.path.join(cfg['Analysis']['result_folder'], file_name)
                df_temp.to_csv(file_name, index=False)
                logging.info("Production data is prepared for well: " + str(well_api12) + " completion: " + completion_name)

        print("Production data is prepared")


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
            production_summary_df.O_CUMMULATIVE_PROD_MMBBL.iloc[
                df_row_index] = current_value + total_well_production
            DAYS_ON_PROD = df_temp.DAYS_ON_PROD.sum()
            production_summary_df.DAYS_ON_PROD.iloc[df_row_index] = DAYS_ON_PROD
            production_summary_df.O_MEAN_PROD_RATE_BOPD.iloc[df_row_index] = df_temp.MON_O_PROD_VOL.sum(
            ) / DAYS_ON_PROD
            production_summary_df.O_PROD_STATUS.iloc[df_row_index] = 1
            current_completion_name = production_summary_df.COMPLETION_NAME.iloc[df_row_index]

            if current_completion_name == "":
                production_summary_df.COMPLETION_NAME.iloc[df_row_index] = completion_name
            else:
                completion_name = current_completion_name + ',' + completion_name
                production_summary_df.COMPLETION_NAME.iloc[df_row_index] = completion_name

            production_summary_df['monthly_production'].iloc[df_row_index] = json.dumps(
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
