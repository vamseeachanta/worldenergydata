# Standard library imports
import os
import json
import datetime
from loguru import logger
# import matplotlib.pyplot as plt
# import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go

# # # Third party imports
import numpy as np
import pandas as pd
from typing import Dict, List
from worldenergydata.modules.bsee.data.bsee_data import BSEEData
from worldenergydata.common.legacy.data import DateTimeUtility

from assetutilities.common.data import SaveData
from assetutilities.common.yml_utilities import WorkingWithYAML  # noqa

wwy = WorkingWithYAML()

bsee_data = BSEEData()
dtu = DateTimeUtility()
save_data = SaveData()

class ProductionAPI12Analysis():

    def __init__(self):
        pass

    def router(self, cfg):
        pass

    def run_production_analysis(self, cfg, data):
        production_groups = data.get('production_data', None)
        groups_dict = {}
        if production_groups is None:
            raise ValueError("No production data found in the provided data.")

        production_summary_df_groups = pd.DataFrame()
        production_df_api12s = []
        prod_rate_bopd_groups = pd.DataFrame(columns=['PRODUCTION_DATETIME'])
        prod_cumulative_mmbbl_groups = pd.DataFrame(columns=['PRODUCTION_DATETIME'])
        api12_array_groups = []
        for group_idx, production_group in enumerate(production_groups):
            prod_rate_bopd_group = pd.DataFrame(columns=['PRODUCTION_DATETIME'])
            prod_cumulative_mmbbl_group = pd.DataFrame(columns=['PRODUCTION_DATETIME'])
            api12_array_group = cfg['data']['groups'][group_idx]['api12']
            api12_array_groups = api12_array_groups + api12_array_group

            for api12_idx, api12 in enumerate(api12_array_group):
                production_df_api12 = production_group[api12]

                _, production_analysis_dict_api12 = self.analyze_data_for_api12(
                    cfg, api12, production_df_api12)
                summary_df_api12 = production_analysis_dict_api12['summary_df_api12']
                production_analysis_df_api12 = production_analysis_dict_api12['api12_df']

                production_df_api12s.append(production_analysis_df_api12)
                production_summary_df_groups = pd.concat(
                    [production_summary_df_groups, summary_df_api12], 
                    ignore_index=True
                )

                if not len(production_analysis_df_api12):
                    production_analysis_df_api12 = pd.DataFrame(
                    columns=['PRODUCTION_DATETIME', 'O_PROD_RATE_BOPD', 'O_CUMMULATIVE_PROD_MMBBL']
                    )

                prod_rate_bopd_api12 = production_analysis_df_api12[
                    ['PRODUCTION_DATETIME', 'O_PROD_RATE_BOPD']
                ].rename(columns={'O_PROD_RATE_BOPD': api12})

                prod_rate_bopd_group = pd.merge(
                prod_rate_bopd_group,
                prod_rate_bopd_api12,
                on=['PRODUCTION_DATETIME'],
                how='outer'
                )

                prod_cumulative_mmbbl_api12 = production_analysis_df_api12[
                    ['PRODUCTION_DATETIME', 'O_CUMMULATIVE_PROD_MMBBL']
                ].rename(columns={'O_CUMMULATIVE_PROD_MMBBL': api12})
                prod_cumulative_mmbbl_group = pd.merge(
                prod_cumulative_mmbbl_group,
                prod_cumulative_mmbbl_api12,
                on=['PRODUCTION_DATETIME'],
                how='outer'
                )

            prod_rate_bopd_group = prod_rate_bopd_group.replace({np.nan: None})
            prod_rate_bopd_group.sort_values(
            by=['PRODUCTION_DATETIME'], 
            inplace=True
            )
            prod_rate_bopd_group.reset_index(inplace=True, drop=True)

            prod_cumulative_mmbbl_group = prod_cumulative_mmbbl_group.replace({np.nan: None})
            prod_cumulative_mmbbl_group.sort_values(
            by=['PRODUCTION_DATETIME'],
            inplace=True
            )
            prod_cumulative_mmbbl_group.reset_index(inplace=True, drop=True)

            self.save_result_group(cfg, group_idx, prod_rate_bopd_group)

            prod_rate_bopd_groups = pd.merge(
                prod_rate_bopd_groups,
                prod_rate_bopd_group,
                on=['PRODUCTION_DATETIME'],
                how='outer'
            )
            self.pd_merge_clean_column_names(prod_rate_bopd_groups)
            prod_rate_bopd_groups = prod_rate_bopd_groups.replace({np.nan: None})
            prod_rate_bopd_groups.sort_values(
            by=['PRODUCTION_DATETIME'],
            inplace=True
            )
            prod_rate_bopd_groups.reset_index(inplace=True, drop=True)

            prod_cumulative_mmbbl_groups = pd.merge(
                prod_cumulative_mmbbl_groups,
                prod_cumulative_mmbbl_group,
                on=['PRODUCTION_DATETIME'],
                how='outer'
            )
            self.pd_merge_clean_column_names(prod_cumulative_mmbbl_groups)
            prod_cumulative_mmbbl_groups = prod_cumulative_mmbbl_groups.replace({np.nan: None})
            prod_cumulative_mmbbl_groups.sort_values(
            by=['PRODUCTION_DATETIME'],
            inplace=True
            )

            prod_cumulative_mmbbl_groups.reset_index(inplace=True, drop=True)
        
        api12_df = production_analysis_dict_api12['api12_df']

        self.save_result_groups(cfg, api12_array_groups, production_df_api12s, production_summary_df_groups, prod_rate_bopd_groups, prod_cumulative_mmbbl_groups)

        self.plot_production_rate_by_well(cfg, prod_rate_bopd_groups)
        self.plot_prod_cumulative_mmbbl_by_well(cfg, prod_cumulative_mmbbl_groups)

        prod_cumulative_mmbbl_groups_by_block = self.convert_well_df_to_block_df(cfg,prod_cumulative_mmbbl_groups)
        self.plot_prod_cumulative_mmbbl_by_block(cfg, prod_cumulative_mmbbl_groups_by_block)

        prod_cumulative_mmbbl_groups_by_field = self.convert_block_to_field(prod_cumulative_mmbbl_groups_by_block)
        self.plot_prod_cumulative_mmbbl_by_field(cfg, prod_cumulative_mmbbl_groups_by_field)

        revenue_df = self.generate_revenue_table(cfg,api12_df)
        self.plot_revenues(cfg, revenue_df)

        groups_dict['production_df_api12s'] = production_df_api12s
        groups_dict['prod_rate_bopd_groups'] = prod_rate_bopd_groups
        groups_dict['prod_cumulative_mmbbl_groups'] = prod_cumulative_mmbbl_groups
        groups_dict['production_summary_df_groups'] = production_summary_df_groups

        return cfg, groups_dict

    def pd_merge_clean_column_names(self, merged_df):

        merged_df.columns = merged_df.columns.map(str)
        merged_df = merged_df.loc[:, ~merged_df.columns.str.endswith('_y')]
        merged_df.columns = merged_df.columns.str.replace('_x', '', regex=True)

        return merged_df

    def save_result_group(self, cfg, group_idx, production_analysis_df_group):

        cfg_group = cfg['data']['groups'][group_idx]
        block_number = None
        block_area = None
        bottom_block = cfg_group.get('bottom_block', None)
        if bottom_block is not None:
            block_number = bottom_block.get('number', None)
            block_area = bottom_block.get('area', None)
        if block_number is None:
            group_label = str(group_idx)
        else:
            group_label = block_area + '_' + str(block_number)
        file_label = 'prod_all_block_' + group_label
        file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.csv')
        production_analysis_df_group.to_csv(file_name, index=False)

    def save_result_groups(self, cfg, api12_array_groups, production_df_api12s, production_summary_df_groups, prod_rate_bopd_groups, prod_cumulative_mmbbl_groups):
        groups_label = cfg['meta'].get('label', None)
        if groups_label is None:
            groups_label = cfg['Analysis']['file_name_for_overwrite']

        file_label = 'prod_raw_' + groups_label
        sheet_names = [str(item) for item in api12_array_groups]
        result_folder = cfg['Analysis']['result_folder']
        file_name = os.path.join(result_folder, file_label + '.xlsx')
        cfg_xlsx = {
            "FileName": file_name,
            "SheetNames": sheet_names,
            "thin_border": True
        }
        save_data.DataFrameArray_To_xlsx_openpyxl(
            production_df_api12s, cfg_xlsx
        )

        file_label = 'prod_summ_' + groups_label
        file_name = os.path.join(
            result_folder,
            file_label + '.csv'
        )
        production_summary_df_groups.to_csv(file_name, index=False)

        file_label = 'prod_rate_bopd_' + groups_label
        file_name = os.path.join(
            result_folder,
            file_label + '.csv'
        )
        prod_rate_bopd_groups.to_csv(file_name, index=False)

        file_label = 'prod_cumulative_mmbbl_' + groups_label
        file_name = os.path.join(
            result_folder,
            file_label + '.csv'
        )
        prod_cumulative_mmbbl_groups.to_csv(file_name, index=False)

    def analyze_data_for_api12(self, cfg, api12, api12_df):
        api12_df_analyzed = api12_df.copy()
        summary_df_api12 = pd.DataFrame()
        completion_names = []
        if not api12_df.empty:
            completion_names = api12_df.COMPLETION_NAME.unique()

        for completion_name in completion_names:
            api12_df_analyzed = api12_df[api12_df.COMPLETION_NAME == completion_name].copy()
            api12_df_analyzed = self.add_production_rate_and_date_to_df(cfg,api12_df_analyzed)
            api12_df_analyzed.sort_values(by=['PRODUCTION_DATETIME'], inplace=True)
            api12_df_analyzed.reset_index(inplace=True)
            if api12_df_analyzed.O_PROD_RATE_BOPD.max() > 0:
                summary_df_api12_by_completion_name = self.get_summary_df_api12(
                    api12,
                    completion_name,
                    api12_df_analyzed
                )
                summary_df_api12 = pd.concat(
                    [summary_df_api12, summary_df_api12_by_completion_name],
                    ignore_index=True
                )

        prod_anal_api12_dict = {
            'api12_df': api12_df_analyzed,
            'api12': api12,
            'summary_df_api12': summary_df_api12,
            'completion_names': completion_names
        }

        return cfg, prod_anal_api12_dict

    def get_summary_df_api12(self, well_api12, completion_name, api12_df):

        columns = ['API12', 'API10', 'O_PROD_STATUS', 'O_CUMMULATIVE_PROD_MMBBL', 'DAYS_ON_PROD', 'O_MEAN_PROD_RATE_BOPD', 'COMPLETION_NAME']
        production_summary_df = pd.DataFrame(columns=columns)
        production_summary_df = production_summary_df.astype({'API12': str, 'API10': str, 'O_PROD_STATUS': int, 'O_CUMMULATIVE_PROD_MMBBL': float, 'DAYS_ON_PROD': int, 'O_MEAN_PROD_RATE_BOPD': float, 'COMPLETION_NAME': str})

        well_api10 = str(well_api12)[0:10]
        values = [well_api12, well_api10, 0.0, 0.0, 0.0, 0.0, completion_name]
        production_summary_df.loc[0] = values

        total_well_production = api12_df.MON_O_PROD_VOL.sum() / 1000 / 1000
        api12_production = api12_df[['PRODUCTION_DATETIME', 'O_PROD_RATE_BOPD']].copy()
        api12_production.rename(columns={'PRODUCTION_DATETIME': 'date_time'}, inplace=True)
        api12_production = api12_production.round(decimals=3)
        api12_production['date_time'] = [item.strftime('%Y-%m-%d') for item in api12_production['date_time'].to_list()]

        if len(api12_df) > 0 and total_well_production > 0:
            df_row_index = api12_df.index[0]

            current_value = production_summary_df.O_CUMMULATIVE_PROD_MMBBL.iloc[0]
            O_CUMMULATIVE_PROD_MMBBL = current_value + total_well_production
            production_summary_df.loc[df_row_index, "O_CUMMULATIVE_PROD_MMBBL"] = float(O_CUMMULATIVE_PROD_MMBBL)

            DAYS_ON_PROD = api12_df.DAYS_ON_PROD.sum()
            production_summary_df.loc[df_row_index, "DAYS_ON_PROD"] = DAYS_ON_PROD

            O_MEAN_PROD_RATE_BOPD = api12_df.MON_O_PROD_VOL.sum() / DAYS_ON_PROD
            production_summary_df.loc[df_row_index, "O_MEAN_PROD_RATE_BOPD"] = float(O_MEAN_PROD_RATE_BOPD)

            production_summary_df.loc[df_row_index, "O_PROD_STATUS"] = 1

        return production_summary_df

    def add_production_rate_and_date_to_df(self, cfg,api12_df):
        import datetime
        production_date_time = []
        production_rate = []
        O_CUMMULATIVE_PROD_MMBBL_array = []
        for df_row in range(0, len(api12_df)):

            year = int(api12_df.PRODUCTION_DATE.iloc[df_row] / 100)
            month = api12_df.PRODUCTION_DATE.iloc[df_row] % year
            date_time = datetime.datetime(year, month, 1)
            date_time = dtu.last_day_of_month(date_time.date())
            if api12_df.DAYS_ON_PROD.iloc[df_row] != 0:
                rate = api12_df.MON_O_PROD_VOL.iloc[df_row] / api12_df.DAYS_ON_PROD.iloc[df_row]
            else:
                rate = 0
            production_date_time.append(date_time)
            production_rate.append(rate)
            O_CUMMULATIVE_PROD_MMBBL_previous_df_row = 0
            if len(O_CUMMULATIVE_PROD_MMBBL_array) > 0:
                O_CUMMULATIVE_PROD_MMBBL_previous_df_row = O_CUMMULATIVE_PROD_MMBBL_array[-1]
            O_CUMMULATIVE_PROD_MMBBL = api12_df.MON_O_PROD_VOL.iloc[df_row] / 1000 / 1000 + O_CUMMULATIVE_PROD_MMBBL_previous_df_row
            O_CUMMULATIVE_PROD_MMBBL_array.append(O_CUMMULATIVE_PROD_MMBBL)

        api12_df['PRODUCTION_DATETIME'] = production_date_time
        api12_df['O_PROD_RATE_BOPD'] = production_rate
        api12_df['O_CUMMULATIVE_PROD_MMBBL'] = O_CUMMULATIVE_PROD_MMBBL_array

        return api12_df

    def convert_well_df_to_block_df(self,cfg,df_api12: pd.DataFrame) -> pd.DataFrame:
        """
        Convert production DataFrame by well into production DataFrame by block.
        Args:
            df_api12 (pd.DataFrame): Input DataFrame with datetime and API12 columns.
            block_to_api12s (Dict[str, List[str]]): Mapping from block number to list of API12s.
        Returns:
            pd.DataFrame: New DataFrame with prod datetime and block production data.
        """
        datetime_col = df_api12.columns[0]
        block_to_api12s = self.extract_block_mapping(cfg)
        df_block = pd.DataFrame()
        df_block[datetime_col] = df_api12[datetime_col]

        for block, api12s_list in block_to_api12s.items():
            block_col_name = f"block_{block}"
            existing_api12s = [api12 for api12 in api12s_list if api12 in df_api12.columns]
            if not existing_api12s:
                df_block[block_col_name] = 0
            else:
                df_block[block_col_name] = df_api12[existing_api12s].sum(axis=1)

        return df_block
    
    def extract_block_mapping(self, cfg):
        mapping = {}
        for group in cfg.get("data", {}).get("groups", []):
            block_ids = []
            block_id = group['bottom_block'].get("number")
            if block_id is not None:
                block_ids.append(block_id)
            api12s = group.get("api12", [])
            for block in block_ids:
                block_str = str(block)
                api12_strs = [str(api12) for api12 in api12s]
                mapping[block_str] = api12_strs
        return mapping
    
    def convert_block_to_field(self,df_block: pd.DataFrame) -> pd.DataFrame:
        """
        Convert block-level DataFrame to field-level DataFrame.
        Args:
            df_block (pd.DataFrame): DataFrame with datetime and block columns.
        Returns:
            pd.DataFrame: New DataFrame with datetime and 'st_malo' column.
        """
        datetime_col = df_block.columns[0]
        field_df = pd.DataFrame()
        field_df[datetime_col] = df_block[datetime_col]

        block_columns = [col for col in df_block.columns if col.startswith("block_")]
        field_df["St Malo"] = df_block[block_columns].sum(axis=1)

        return field_df

    def plot_production_rate_by_well(self, cfg, prod_rates_df):

        df_melted = prod_rates_df.melt(id_vars=['PRODUCTION_DATETIME'], 
                            var_name='api12', 
                            value_name='production')

        df_melted = df_melted.rename(columns={'PRODUCTION_DATETIME': 'Date'})

        df_melted = df_melted.dropna(subset=['production'])
        df_melted['Date'] = pd.to_datetime(df_melted['Date'])
        df_filtered = df_melted[
                (df_melted['Date'] >= '2014-01-01') &
                (df_melted['Date'] <= '2025-04-03') &
                (df_melted['production'] >= 10) &
                (df_melted['production'] <= 50000) 
            ]

        fig = px.line(
            df_filtered,
            x='Date',
            y='production',
            color='api12',
            markers=True,
            title="Production Data for API12"
        )
        groups_label = cfg['meta'].get('label', None)
        if groups_label is None:
            groups_label = cfg['Analysis']['file_name_for_overwrite']

        file_label = 'prod_rate_by_well_' + groups_label
        result_folder = cfg['Analysis']['result_folder']
        file_name = os.path.join(result_folder, 'Plot',file_label + '.html')
        fig.write_html(file_name, include_plotlyjs="cdn")

    def plot_prod_cumulative_mmbbl_by_well(self, cfg, prod_cumulative_mmbbl_groups):

        df_melted = prod_cumulative_mmbbl_groups.melt(id_vars=['PRODUCTION_DATETIME'], 
                            var_name='api12', 
                            value_name='cumulative_production')

        df_melted = df_melted.rename(columns={'PRODUCTION_DATETIME': 'Date'})

        df_melted = df_melted.dropna(subset=['cumulative_production'])
        df_melted['Date'] = pd.to_datetime(df_melted['Date'])
        
        df_filtered = df_melted[
                (df_melted['Date'] >= '2010-01-01') &
                (df_melted['Date'] <= '2025-04-03') &
                (df_melted['cumulative_production'] >= 10) &
                (df_melted['cumulative_production'] <= 50) 
            ]

        fig = px.line(
            df_filtered,
            x='Date',
            y='cumulative_production',
            color='api12',
            markers=True,
            title="Cumulative Production by well"
        )

        groups_label = cfg['meta'].get('label', None)
        if groups_label is None:
            groups_label = cfg['Analysis']['file_name_for_overwrite']

        file_label = 'prod_cumulative_mmbbl_by_well_' + groups_label
        result_folder = cfg['Analysis']['result_folder']
        file_name = os.path.join(result_folder,'Plot', file_label + '.html')
        fig.write_html(file_name, include_plotlyjs="cdn")
    
    def plot_prod_cumulative_mmbbl_by_block(self, cfg, prod_cumulative_mmbbl_groups_by_block):

        df_melted = prod_cumulative_mmbbl_groups_by_block.melt(id_vars=['PRODUCTION_DATETIME'], 
                            var_name='block', 
                            value_name='cumulative_production')

        df_melted = df_melted.rename(columns={'PRODUCTION_DATETIME': 'Date'})
        df_melted = df_melted.dropna(subset=['cumulative_production'])
        df_melted['Date'] = pd.to_datetime(df_melted['Date'])
        
        df_filtered = df_melted[
                (df_melted['Date'] >= '2014-01-01') &
                (df_melted['Date'] <= '2025-04-03') &
                (df_melted['cumulative_production'] >= 1) &
                (df_melted['cumulative_production'] <= 200) 
            ]

        fig = px.line(
            df_filtered,
            x='Date',
            y='cumulative_production',
            color='block',
            markers=True,
            title="Cumulative Production by block"
        )

        groups_label = cfg['meta'].get('label', None)
        if groups_label is None:
            groups_label = cfg['Analysis']['file_name_for_overwrite']

        file_label = 'prod_cumulative_mmbbl_by_block_' + groups_label
        result_folder = cfg['Analysis']['result_folder']
        file_name = os.path.join(result_folder,'Plot', file_label + '.html')
        fig.write_html(file_name, include_plotlyjs="cdn")
    
    def plot_prod_cumulative_mmbbl_by_field(self, cfg, prod_cumulative_mmbbl_groups_by_field):
            
        df_melted = prod_cumulative_mmbbl_groups_by_field.melt(id_vars=['PRODUCTION_DATETIME'], 
                            var_name='field', 
                            value_name='cumulative_production')

        df_melted = df_melted.rename(columns={'PRODUCTION_DATETIME': 'Date'})
        df_melted = df_melted.dropna(subset=['cumulative_production'])
        df_melted['Date'] = pd.to_datetime(df_melted['Date'])
        
        df_filtered = df_melted[
                (df_melted['Date'] >= '2013-01-01') &
                (df_melted['Date'] <= '2025-04-03') &
                (df_melted['cumulative_production'] >= 1) &
                (df_melted['cumulative_production'] <= 200) 
            ]

        fig = px.line(
            df_filtered,
            x='Date',
            y='cumulative_production',
            color='field',
            markers=True,
            title="Cumulative Production by field"
        )

        groups_label = cfg['meta'].get('label', None)
        if groups_label is None:
            groups_label = cfg['Analysis']['file_name_for_overwrite']

        file_label = 'prod_cumulative_mmbbl_by_field_' + groups_label
        result_folder = cfg['Analysis']['result_folder']
        file_name = os.path.join(result_folder,'Plot', file_label + '.html')
        fig.write_html(file_name, include_plotlyjs="cdn")
    
    def plot_revenues(self, cfg, revenue_df):
        
        revenue_df['Revenue (USD)'] = revenue_df['Revenue (USD)'].replace('[\$,]', '', regex=True).astype(float)
        revenue_df['Month'] = pd.to_datetime(revenue_df['Month'], format='%Y%m', errors='coerce')
        months = revenue_df['Month'].tolist()
        revenue_usd = revenue_df['Revenue (USD)'].tolist()

        fig = go.Figure(data=[
            go.Bar(name='Revenue (USD)', x=months, y=revenue_usd)
        ])

        fig.update_layout(
            title='Monthly Revenue from Oil Production',
            xaxis=dict(
                title='Month',
                dtick='M3'  # Set the interval to 1 month
            ),
            yaxis=dict(
                title='Revenue (USD)',
                tickprefix='$',
                tickformat=',',
                range=[0, 40000000]  # Customize Y-axis range
            ),
            template='plotly_white'
        )

        groups_label = cfg['meta'].get('label', None)
        if groups_label is None:
            groups_label = cfg['Analysis']['file_name_for_overwrite']

        file_label = 'monthly_revenues_' + groups_label
        result_folder = cfg['Analysis']['result_folder']
        file_name = os.path.join(result_folder,'Plot', file_label + '.html')
        fig.write_html(file_name, include_plotlyjs="cdn")

    def generate_revenue_table(self, cfg, api12_df):

        folder_path = r'data\modules\oil_price'
        library_name = 'worldenergydata'
        library_file_cfg = {
            'filepath': folder_path,
            'library_name': library_name
        }
        folder_path= wwy.get_library_filepath(library_file_cfg, src_relative_location_flag=False)
        file = os.path.join(folder_path, 'F000000__3m.xls')
        oil_prices = pd.read_excel(file, engine='xlrd')

        avg_price = oil_prices['Oil Purchase Price'].tail(13).tolist()

        months = []
        if not api12_df['PRODUCTION_DATE'].empty:
            months = api12_df['PRODUCTION_DATE'].tolist()
        MON_O_PROD_VOL = []
        if not api12_df['MON_O_PROD_VOL'].empty:
            MON_O_PROD_VOL = api12_df['MON_O_PROD_VOL'].tolist()

        min_len = min(len(months), len(MON_O_PROD_VOL), len(avg_price))
        if min_len == 0:
            return pd.DataFrame()
        
        months = months[-min_len:]
        MON_O_PROD_VOL = MON_O_PROD_VOL[-min_len:]
        avg_price = avg_price[-min_len:]
        
        # Calculate revenue for each year
        revenue = [MON_O_PROD_VOL[i] * avg_price[i] for i in range(0, len(MON_O_PROD_VOL))]

       
        df = pd.DataFrame({
            'Month': months,
            'Monthly Oil Production': MON_O_PROD_VOL,
            'Avg Price (USD/bbl)': [f"${price:,.2f}" for price in avg_price],
            'Revenue (USD)': [f"${rev:,.2f}" for rev in revenue]
        })

        total_revenue = sum(revenue)
        total_row = {
            'Month': '',
            'Monthly Oil Production': '',
            'Avg Price (USD/bbl)': '',
            'Revenue (USD)': f"${total_revenue:,.2f}"
        }

        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

        result_folder = cfg['Analysis']['result_folder']
        file_label = 'revenues_table'
        file_name = os.path.join(result_folder, file_label + '.csv')
        df.to_csv(file_name, index=False)

        return df

    def perform_decline_analysis_api12(self, cfg, api12_df):
        #TODO

        pass
        # peakvalue = max(
        # api12_df.O_PROD_RATE_BOPD
        # )
        # tdatetime_peak = api12_df.loc[

        # lastest date, last ValueError

        # no of years = 9
        # annual decline = (peak/latest)^(1 + no of years) - 1
        # laetst = peak *(1 + annual decline)^(1/no of years)
        # annual decline = -16

