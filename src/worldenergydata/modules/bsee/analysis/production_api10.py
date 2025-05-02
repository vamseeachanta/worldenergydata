# Standard library imports
import os
import json
import logging

# # # Third party imports
import pandas as pd
from worldenergydata.modules.bsee.data.bsee_data import BSEEData
from worldenergydata.common.legacy.data import DateTimeUtility


bsee_data = BSEEData()
dtu = DateTimeUtility()

class ProductionAPI10Analysis():

    def __init__(self):
        pass

    def router(self, cfg, api12_production_data):
        self.prepare_production_data(cfg, api12_production_data)

        self.prepare_field_production_rate(df_temp, completion_name)
        self.prepare_field_production(df_temp, completion_name)

        # api12_analysis.sort_values(by=['O_PROD_STATUS', 'WELL_LABEL'],
        #                                     ascending=[False, True],
        #                                     inplace=True)
        # api12_analysis.reset_index(inplace=True, drop=True)


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


    def prepare_field_production_rate(self, df_temp, df_column_label):
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
