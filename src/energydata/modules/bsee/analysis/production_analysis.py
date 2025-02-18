# Standard library imports
import json
import logging

# # # Third party imports
import pandas as pd
from energydata.modules.bsee.data.bsee_data import BSEEData

# from energydata.common.bsee_data_manager import BSEEData

# from energydata.common.data import AttributeDict, transform_df_datetime_to_str

bsee_data = BSEEData()

class ProductionAnalysis():

    def __init__(self):
        pass
        # self.bsee_data = BSEEData(self.cfg)

    def router(self, cfg):
        self.prepare_production_data(cfg)

    
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


    def prepare_production_data(self, production_data):
        self.output_data_production_df_array = {}
        completion_name_list = production_data.COMPLETION_NAME.unique()
        for completion_name in completion_name_list:
            df_temp = production_data[production_data.COMPLETION_NAME == completion_name].copy()
            df_temp = self.add_production_rate_and_date_to_df(df_temp)
            df_temp.sort_values(by=['PRODUCTION_DATETIME'], inplace=True)
            df_temp.reset_index(inplace=True)
            if df_temp.O_PROD_RATE_BOPD.max() > 0:
                well_api12 = df_temp.API12.iloc[0]
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
    
