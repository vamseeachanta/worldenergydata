# Standard library imports
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

class ProductionAnalysis():

    def __init__(self):
        self.output_data_field_production_rate_df = None
        self.output_data_field_production_df = None
        self.output_data_api12_df = None


    def router(self, cfg, api12_production_data):
        self.prepare_production_data(cfg,api12_production_data)

    
    def get_production_data_for_api(self):
        pass

    def prepare_api12_data(self, well_data):

        self.output_data_api12_df = well_data.copy()
        self.add_gis_info_to_well_data()
        self.output_data_api12_df['O_PROD_STATUS'] = 0
        self.output_data_api12_df['O_CUMMULATIVE_PROD_MMBBL'] = 0
        self.output_data_api12_df['DAYS_ON_PROD'] = 0
        self.output_data_api12_df['O_MEAN_PROD_RATE_BOPD'] = 0
        self.output_data_api12_df['Total Depth Date'] = pd.to_datetime(self.output_data_api12_df['Total Depth Date'])
        self.output_data_api12_df['Spud Date'] = pd.to_datetime(self.output_data_api12_df['Spud Date'])
        self.output_data_api12_df['COMPLETION_NAME'] = ""
        self.output_data_api12_df['monthly_production'] = None
        self.output_data_api12_df['xyz'] = None
        self.output_data_field_production_rate_df = None
        self.output_data_field_production_df = None


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
                well_api10 = self.get_API10_from_well_API(well_api12)
                self.prepare_field_production_rate(df_temp, completion_name)
                self.prepare_field_production(df_temp, completion_name)
                self.add_production_and_completion_name_to_well_data(well_api10, completion_name, df_temp)
                self.output_data_production_df_array.update({completion_name: df_temp})

        if len(self.output_data_production_df_array) != 0:
            self.add_production_from_all_wells()
        print("Production data is prepared")


    def add_production_from_all_wells(self):
        # Third party imports
        import pandas as pd
        columns = self.output_data_field_production_rate_df.columns.tolist()
        columns.remove('PRODUCTION_DATETIME')
        self.output_data_field_production_rate_df[
            'TOTAL_DAILY_PRODUCTION_rate_BOPD'] = self.output_data_field_production_rate_df[columns].sum(axis=1)

        columns = self.output_data_field_production_df.columns.tolist()
        columns.remove('PRODUCTION_DATETIME')
        self.output_data_field_production_df[
            'Total_MONTLY_PRODUCTION_MMbbl'] = self.output_data_field_production_df[columns].sum(axis=1) / 1000 / 1000
        self.output_data_field_production_df[
            'CUMULATIVE_MONTLY_PRODUCTION_MMbbl'] = self.output_data_field_production_df[
                'Total_MONTLY_PRODUCTION_MMbbl'].cumsum()

        self.field_summary['Cummulative Production, MMbbls'] = {
            'PRODUCTION_DATETIME':
                self.output_data_field_production_df['PRODUCTION_DATETIME'].tolist(),
            'CUMULATIVE_MONTLY_PRODUCTION_MMbbl':
                self.output_data_field_production_df['CUMULATIVE_MONTLY_PRODUCTION_MMbbl'].tolist()
        }

        self.production_summary_df = pd.DataFrame()
        self.production_summary_df['PRODUCTION_DATETIME'] = self.output_data_field_production_rate_df[
            'PRODUCTION_DATETIME']
        self.production_summary_df['Field NickName'] = self.cfg['custom_parameters']['field_nickname']
        self.production_summary_df['BOEM_FIELDS'] = self.cfg['custom_parameters']['boem_fields']
        self.production_summary_df['Production Rate, BOPD'] = self.output_data_field_production_rate_df[
            'TOTAL_DAILY_PRODUCTION_rate_BOPD']
        self.production_summary_df['CUMULATIVE_MONTLY_PRODUCTION_MMbbl'] = self.output_data_field_production_df[
            'CUMULATIVE_MONTLY_PRODUCTION_MMbbl']

    def add_production_and_completion_name_to_well_data(self, well_api10, completion_name, df_temp):
        if self.output_data_api12_df is None:
            raise ValueError("output_data_api12_df is not set. Call 'prepare_api12_data' first.")

        total_well_production = df_temp.MON_O_PROD_VOL.sum() / 1000 / 1000
        api12_production = df_temp[['PRODUCTION_DATETIME', 'O_PROD_RATE_BOPD']].copy()
        api12_production.rename(columns={'PRODUCTION_DATETIME': 'date_time'}, inplace=True)
        api12_production = api12_production.round(decimals=3)
        api12_production['date_time'] = [item.strftime('%Y-%m-%d') for item in api12_production['date_time'].to_list()]

        temp_df = self.output_data_api12_df[(self.output_data_api12_df.API10 == well_api10)].copy()
        if len(temp_df) > 0 and total_well_production > 0:
            df_row_index = temp_df.index[0]

            current_production = self.output_data_api12_df.O_CUMMULATIVE_PROD_MMBBL.iloc[df_row_index]
            self.output_data_api12_df.O_CUMMULATIVE_PROD_MMBBL.iloc[
                df_row_index] = current_production + total_well_production
            DAYS_ON_PROD = df_temp.DAYS_ON_PROD.sum()
            self.output_data_api12_df.DAYS_ON_PROD.iloc[df_row_index] = DAYS_ON_PROD
            self.output_data_api12_df.O_MEAN_PROD_RATE_BOPD.iloc[df_row_index] = df_temp.MON_O_PROD_VOL.sum(
            ) / DAYS_ON_PROD
            self.output_data_api12_df.O_PROD_STATUS.iloc[df_row_index] = 1
            current_completion_name = self.output_data_api12_df.COMPLETION_NAME.iloc[df_row_index]
            if current_completion_name == "":
                self.output_data_api12_df.COMPLETION_NAME.iloc[df_row_index] = completion_name
            else:
                completion_name = current_completion_name + ',' + completion_name
                self.output_data_api12_df.COMPLETION_NAME.iloc[df_row_index] = completion_name
            self.output_data_api12_df['monthly_production'].iloc[df_row_index] = json.dumps(
                api12_production.to_dict(orient='records'))
            
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
    
    def get_API10_from_well_API(self, well_api):
        well_api_str = str(well_api)
        if len(well_api_str) == 12:
            api10_value = int(well_api_str[0:10])
        else:
            api10_value = well_api_str
        return api10_value
    
    def prepare_field_production_rate(self, df_temp, df_column_label):
        import pandas as pd
        if self.output_data_field_production_rate_df is None:
            self.output_data_field_production_rate_df = pd.DataFrame(columns=['PRODUCTION_DATETIME'])

        field_production_rate_df = pd.DataFrame()
        field_production_rate_df['PRODUCTION_DATETIME'] = df_temp['PRODUCTION_DATETIME'].copy()
        field_production_rate_df[df_column_label] = df_temp['O_PROD_RATE_BOPD'].copy()
        self.output_data_field_production_rate_df = pd.merge(left=self.output_data_field_production_rate_df,
                                                                right=field_production_rate_df,
                                                                how='outer',
                                                                left_on='PRODUCTION_DATETIME',
                                                                right_on='PRODUCTION_DATETIME')
        self.output_data_field_production_rate_df.sort_values(by=['PRODUCTION_DATETIME'], inplace=True)

    def prepare_field_production(self, df_temp, df_column_label):
        import pandas as pd
        if self.output_data_field_production_df is None:
            self.output_data_field_production_df = pd.DataFrame(columns=['PRODUCTION_DATETIME'])

        field_production_df = pd.DataFrame()
        field_production_df['PRODUCTION_DATETIME'] = df_temp['PRODUCTION_DATETIME'].copy()
        field_production_df[df_column_label] = df_temp['MON_O_PROD_VOL'].copy()
        self.output_data_field_production_df = pd.merge(left=self.output_data_field_production_df,
                                                        right=field_production_df,
                                                        how='outer',
                                                        left_on='PRODUCTION_DATETIME',
                                                        right_on='PRODUCTION_DATETIME')
        self.output_data_field_production_df.sort_values(by=['PRODUCTION_DATETIME'], inplace=True)
        self.output_data_field_production_df.drop_duplicates(inplace=True)
