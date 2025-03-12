import os
import pandas as pd
from copy import deepcopy

from energydata.modules.bsee.data.scrapy_well_data import  ScrapyRunnerAPI

from assetutilities.common.utilities import is_dir_valid_func
from assetutilities.common.utilities import is_file_valid_func

class WellData:

    def __init__(self):
        pass

    def get_well_data_all_wells(self, cfg):
        Borehole_apd_df = self.get_Borehole_apd_for_all_wells(cfg)
        eWellEORRawData_df = self.get_eWellEORRawData_from_csv(cfg)
        eWellWARRawData_mv_war_main_df = self.get_eWellWARRawData_mv_war_main_from_csv(cfg)
        eWellWARRawData_mv_war_main_prop_df = self.get_eWellWARRawData_mv_war_main_prop_from_csv(cfg)
        
        bsee_csv_data = {'Borehole_apd_df': Borehole_apd_df, 'eWellEORRawData_df': eWellEORRawData_df, 'eWellWARRawData_mv_war_main_df': eWellWARRawData_mv_war_main_df, 'eWellWARRawData_mv_war_main_prop_df': eWellWARRawData_mv_war_main_prop_df}
        
        cfg = self.get_well_data_from_website(cfg)

        well_data_groups = []
        for group in cfg[cfg['basename']]['well_data']['groups']:
            well_data_group = group.copy()
            api12_array = group['api12']
            api12_array_well_data = []
            for api12 in api12_array:
                api12_df = self.get_api12_data_from_all_sources(cfg, bsee_csv_data, group, api12)

            well_data_group.update({'api12_df': api12_df})

            api12_array_well_data.append(well_data_group)

        well_data_groups.append(api12_array_well_data)

        return cfg, well_data_groups

    def get_data_source_file(self, cfg, group):
        #TODO SS
        library = 'digitalmodel'
        filename = cfg['filename']
        file_path = os.path.join(cfg['Analysis']['analysis_root_folder'], library, filename)
        

    def get_api12_data_from_all_sources(self, cfg, bsee_csv_data, group, api12):
        Borehole_apd_df = bsee_csv_data['Borehole_apd_df']
        eWellEORRawData_df = bsee_csv_data['eWellEORRawData_df']
        eWellWARRawData_mv_war_main_df = bsee_csv_data['eWellWARRawData_mv_war_main_df']
        eWellWARRawData_mv_war_main_prop_df = bsee_csv_data['eWellWARRawData_mv_war_main_prop_df']

        api12_well_data = pd.read_csv(group['file_name'])
        api12_Borehole_apd = self.get_Borehole_apd_for_api12(cfg, Borehole_apd_df, api12)
        api12_eWellEORRawData = eWellEORRawData_df[eWellEORRawData_df['API_WELL_NUMBER'] == api12].copy()
        api12_eWellWARRawData_mv_war_main = eWellWARRawData_mv_war_main_df[eWellWARRawData_mv_war_main_df['API_WELL_NUMBER'] == api12].copy()
        # api12_eWellWARRawData_mv_war_main_prop = eWellWARRawData_mv_war_main_prop_df[eWellWARRawData_mv_war_main_prop_df['API_WELL_NUMBER'] == api12].copy()
        
        api12_df = pd.merge(api12_Borehole_apd, api12_well_data, how='inner' ,
                                    left_on=['API_WELL_NUMBER'], right_on=['API Well Number'])
        api12_df = pd.merge(api12_eWellEORRawData, api12_df, how='outer' ,
                                    left_on=['API_WELL_NUMBER'], right_on=['API Well Number'])
        api12_df = self.pd_merge_clean_column_names(api12_df)

        api12_df = pd.merge(api12_eWellWARRawData_mv_war_main, api12_df, how='outer' ,
                                    left_on=['API_WELL_NUMBER'], right_on=['API Well Number'])
        api12_df = self.pd_merge_clean_column_names(api12_df)

        api12_df = pd.merge(api12_df, eWellWARRawData_mv_war_main_prop_df, how='left' ,
                                    left_on=['SN_WAR'], right_on=['SN_WAR'])
        api12_df = self.pd_merge_clean_column_names(api12_df)
        
        return api12_df

    def get_Borehole_apd_for_all_wells(self, cfg):
        BoreholeRawData_df = self.get_BoreholeRawData_from_csv(cfg)
        eWellAPDRawData_df = self.get_eWellAPDRawData_from_csv(cfg)

        self.Borehole_apd_df = self.get_merged_data(BoreholeRawData_df, eWellAPDRawData_df)
        
        return self.Borehole_apd_df

    def get_Borehole_apd_for_api12(self, cfg, Borehole_apd_df, api12):
        api12_Borehole_apd = Borehole_apd_df[Borehole_apd_df['API_WELL_NUMBER'] == api12].copy()


        return api12_Borehole_apd

    def get_well_data_from_website(self, cfg):
        output_data = []
        if cfg['data']['by'] == 'API12':
            website_data = self.get_well_data_by_api12(cfg, output_data)

        elif cfg['data']['by'] == 'block':
            website_data = self.get_well_data_by_block(cfg, output_data)

        well_data = {'type': 'csv', 'groups': output_data}
        cfg[cfg['basename']].update({'well_data': well_data})

        return cfg
    
    def get_well_data_by_api12(self, cfg, output_data):
        input_items = cfg['data']['groups']
        scrapy_runner_api = ScrapyRunnerAPI()

        for input in input_items:

            api12_array = input.get('api12', [])  # Get API numbers list

            for api12 in api12_array:
                input_item = {'api12': [api12], 'label': str(api12)}

                api12_data = scrapy_runner_api.run_spider(cfg, input_item)
                output_data = self.generate_output_item(cfg, output_data, input_item)

        return output_data, api12_data

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

        file_name = 'data/modules/bsee/full_data/BoreholeRawData_mv_boreholes_all.csv'

        file_is_valid, file_name = is_file_valid_func(file_name)
        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
        else:
            raise Exception(f"File not found: {file_name}")

        return df

    def get_eWellEORRawData_from_csv(self, cfg):

        file_name = 'data/modules/bsee/full_data/eWellEORRawData_mv_eor_mainquery.csv'

        file_is_valid, file_name = is_file_valid_func(file_name)
        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
        else:
            raise Exception(f"File not found: {file_name}")

        return df


    def get_eWellAPDRawData_from_csv(self, cfg):

        # Load CSV files
        file_name = 'data/modules/bsee/full_data/eWellAPDRawData_mv_apd_main.csv'

        file_is_valid, file_name = is_file_valid_func(file_name)
        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
        else:
            raise Exception(f"File not found: {file_name}")

        return df

    def get_eWellWARRawData_mv_war_main_from_csv(self, cfg):
        
        # Load CSV files
        file_name = 'data/modules/bsee/full_data/eWellWARRawData_mv_war_main.csv'

        file_is_valid, file_name = is_file_valid_func(file_name)
        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
        else:
            raise Exception(f"File not found: {file_name}")

        return df

    def get_eWellWARRawData_mv_war_main_prop_from_csv(self, cfg):
        
        # Load CSV files
        file_name = 'data/modules/bsee/full_data/eWellWARRawData_mv_war_main_prop.csv'

        file_is_valid, file_name = is_file_valid_func(file_name)
        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
        else:
            raise Exception(f"File not found: {file_name}")

        return df


    def get_merged_data(self, df1, df2):

        # Identify the join key (first column)
        join_key = df1.columns[0]

        # Merge on the first column (inner join to keep only matching rows)
        merged_df = pd.merge(df1, df2, on=join_key, how="right")

        merged_df = self.pd_merge_clean_column_names(merged_df)

        output_path = r'data\modules\bsee\well'
        # Save to a new CSV file
        merged_df.to_csv(os.path.join(output_path, 'Join_Borehole_APD.csv'), index=False)

        return merged_df

    def pd_merge_clean_column_names(self, merged_df):
        merged_df = merged_df.loc[:, ~merged_df.columns.str.endswith('_y')]
        merged_df.columns = merged_df.columns.str.replace('_x', '', regex=True)
        return merged_df