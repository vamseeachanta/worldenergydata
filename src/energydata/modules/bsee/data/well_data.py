import os
import pandas as pd
from copy import deepcopy

from energydata.modules.bsee.analysis.scrapy_for_block import ScrapyRunnerBlock
from energydata.modules.bsee.data.scrapy_for_API import  ScrapyRunnerAPI


from assetutilities.common.utilities import is_dir_valid_func


class WellData:
    
    def __init__(self):
        pass

    def get_well_data(self, cfg):
        cfg = self.get_well_data_from_website(cfg)
        BoreholeRawData_df = self.get_BoreholeRawData_from_csv(cfg)
        eWellAPDRawData_df = self.get_eWellAPDRawData_from_csv(cfg)
        Borehole_apd_df = self.get_merged_data(BoreholeRawData_df, eWellAPDRawData_df)
        
        return cfg

    def get_well_data_with_borehole_apd(self, cfg, Borehole_apd_df):
        pass

    def get_well_data_from_website(self, cfg):
        output_data = [] 
        if "well_data" in cfg and cfg['well_data']['flag']:
            input_items = cfg['data']['groups']
            scrapy_runner_api = ScrapyRunnerAPI()

            for input_item in input_items:

                scrapy_runner_api.run_spider(cfg, input_item)

                output_data = self.generate_output_item(cfg, output_data, input_item)



        elif "block_data" in cfg and cfg['block_data']['flag']:
            input_items = cfg['data']['groups']
            scrapy_runner_block = ScrapyRunnerBlock()

            for input_item in input_items:
                scrapy_runner_block.run_spider(cfg, input_item)
                output_data = self.generate_output_item(cfg, output_data, input_item)

        well_data = {'type': 'csv', 'groups': output_data}
        cfg[cfg['basename']].update({'well_data': well_data})

        return cfg

    def generate_output_item(self, cfg, output_data, input_item):

        label = input_item['label']
        output_path = os.path.join(cfg['Analysis']['result_folder'], 'Data')
        if output_path is None:
            result_folder = cfg['Analysis']['result_folder']
            output_path = os.path.join(result_folder, 'Data')

        analysis_root_folder = cfg['Analysis']['analysis_root_folder']
        is_dir_valid, output_path = is_dir_valid_func(output_path, analysis_root_folder)

        output_file = os.path.join(output_path, str(label) + '.csv')

        input_item_csv_cfg = deepcopy(input_item)
        input_item_csv_cfg.update({'label': label, 'file_name': output_file})
        output_data.append(input_item_csv_cfg)
        
        return output_data
    
    def get_BoreholeRawData_from_csv(self, cfg):

        # Load CSV files
        file1 = r'data\modules\bsee\full_data\BoreholeRawData_mv_boreholes_all.csv'

        df = pd.read_csv(file1, low_memory=False)

        return df


    def get_eWellAPDRawData_from_csv(self, cfg):

        # Load CSV files
        file = r'data\modules\bsee\full_data\eWellAPDRawData_mv_apd_main.csv'

        df = pd.read_csv(file, low_memory=False)

        return df


    def get_merged_data(self, df1, df2):

        # Identify the join key (first column)
        join_key = df1.columns[0]

        # Merge on the first column (inner join to keep only matching rows)
        merged_df = pd.merge(df1, df2, on=join_key, how="right")

        merged_df = merged_df.loc[:, ~merged_df.columns.str.endswith('_y')]
        merged_df.columns = merged_df.columns.str.replace('_x', '', regex=True)

        output_path = r'data\modules\bsee\well'
        # Save to a new CSV file
        merged_df.to_csv(os.path.join(output_path, 'Join_Borehole_APD.csv'), index=False)

        return merged_df