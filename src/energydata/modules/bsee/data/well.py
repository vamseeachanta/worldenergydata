from energydata.modules.bsee.data.block_data import BlockData

import os
import pandas as pd
from copy import deepcopy

from energydata.modules.bsee.data.scrapy_well_data import  ScrapyRunnerAPI

from assetutilities.common.utilities import is_dir_valid_func
from assetutilities.common.utilities import is_file_valid_func

block_data = BlockData()

class WellData:

    def __init__(self):
        pass

    def router(self, cfg):
        if "data" in cfg:
            if cfg['data']['by'] == 'block':
                cfg, block_data_groups, api12_array = self.get_api12_array_by_block(cfg)
            elif cfg['data']['by'] == 'API12':
                api12_array = self.get_api12_array_by_api12(cfg)
            cfg[cfg['basename']].update({'groups': [{'api12': api12_array}]})

        well_data_flag = cfg['data'].get('well_data', False)
        well_data_groups = None
        if well_data_flag:
            cfg, well_data_groups  = self.get_well_data_all_wells(cfg)

        #TODO
        # WAR_summary = self.get_WAR_summary_by_api10(api10)
        # directional_surveys = self.bsee_data.get_directional_surveys_by_api10(api10)
        # ST_BP_and_tree_height = self.get_ST_BP_and_tree_height_by_api10(api10)
        # well_tubulars_data = self.bsee_data.get_well_tubulars_data_by_api10(api10)
        # completion_data = self.bsee_data.get_completion_data_by_api10(api10)

        return cfg, well_data_groups

    def get_well_data_all_wells(self, cfg):
        BoreholeRawData_df = self.get_BoreholeRawData_from_csv(cfg)
        eWellAPDRawData_df = self.get_eWellAPDRawData_from_csv(cfg)
        eWellEORRawData_df = self.get_eWellEORRawData_from_csv(cfg)
        eWellWARRawData_mv_war_main_df = self.get_eWellWARRawData_mv_war_main_from_csv(cfg)
        eWellWARRawData_mv_war_main_prop_df = self.get_eWellWARRawData_mv_war_main_prop_from_csv(cfg)
        
        bsee_csv_data = {'BoreholeRawData_df': BoreholeRawData_df, 
                         'eWellAPDRawData_df': eWellAPDRawData_df, 
                         'eWellEORRawData_df': eWellEORRawData_df, 
                         'eWellWARRawData_mv_war_main_df': eWellWARRawData_mv_war_main_df, 
                         'eWellWARRawData_mv_war_main_prop_df': eWellWARRawData_mv_war_main_prop_df}
        
        cfg = self.get_well_data_from_website(cfg)

        well_data_groups = []
        for group in cfg[cfg['basename']]['well_data']['groups']:
            api12_array = group['api12']
            api12_array_well_data = []
            for api12 in api12_array:
                well_data_group = group.copy()
                merged_api12_df = self.get_api12_merged_df_from_all_sources(cfg, bsee_csv_data, group, api12)
                individual_df_data = self.get_api12_data_from_all_sources(cfg, bsee_csv_data, group, api12)

                well_data_group.update({'merged_api12_df': merged_api12_df})
                well_data_group.update(individual_df_data)

                api12_array_well_data.append(well_data_group)

            well_data_groups.append(api12_array_well_data)

        return cfg, well_data_groups

    def get_data_source_file(self, cfg, group):
        #TODO SS
        library = 'digitalmodel'
        filename = cfg['filename']
        file_path = os.path.join(cfg['Analysis']['analysis_root_folder'], library, filename)


    def get_api12_merged_df_from_all_sources(self, cfg, bsee_csv_data, group, api12):
        BoreholeRawData_df = bsee_csv_data['BoreholeRawData_df']
        eWellAPDRawData_df = bsee_csv_data['eWellAPDRawData_df']
        eWellEORRawData_df = bsee_csv_data['eWellEORRawData_df']
        eWellWARRawData_mv_war_main_df = bsee_csv_data['eWellWARRawData_mv_war_main_df']
        eWellWARRawData_mv_war_main_prop_df = bsee_csv_data['eWellWARRawData_mv_war_main_prop_df']

        api12_well_data = pd.read_csv(group['file_name'])
        api12_eWellEORRawData = eWellEORRawData_df[eWellEORRawData_df['API_WELL_NUMBER'] == api12].copy()
        api12_eWellWARRawData_mv_war_main = eWellWARRawData_mv_war_main_df[eWellWARRawData_mv_war_main_df['API_WELL_NUMBER'] == api12].copy()
        # api12_eWellWARRawData_mv_war_main_prop = eWellWARRawData_mv_war_main_prop_df[eWellWARRawData_mv_war_main_prop_df['API_WELL_NUMBER'] == api12].copy()
        
        Borehole_apd_df = self.get_Borehole_apd_for_all_wells(BoreholeRawData_df, eWellAPDRawData_df)
        api12_Borehole_apd = self.get_Borehole_apd_for_api12(cfg, Borehole_apd_df, api12)

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

    def get_api12_data_from_all_sources(self, cfg, bsee_csv_data, group, api12):
        api12_df = pd.read_csv(group['file_name'])

        BoreholeRawData_df = bsee_csv_data['BoreholeRawData_df']
        eWellAPDRawData_df = bsee_csv_data['eWellAPDRawData_df']
        eWellEORRawData_df = bsee_csv_data['eWellEORRawData_df']
        eWellWARRawData_mv_war_main_df = bsee_csv_data['eWellWARRawData_mv_war_main_df']
        eWellWARRawData_mv_war_main_prop_df = bsee_csv_data['eWellWARRawData_mv_war_main_prop_df']

        api12_BoreholeRawData = BoreholeRawData_df[BoreholeRawData_df['API_WELL_NUMBER'] == api12].copy()
        api12_eWellAPDRawData = eWellAPDRawData_df[eWellAPDRawData_df['API_WELL_NUMBER'] == api12].copy()
        api12_eWellEORRawData = eWellEORRawData_df[eWellEORRawData_df['API_WELL_NUMBER'] == api12].copy()
        api12_eWellWARRawData_mv_war_main = eWellWARRawData_mv_war_main_df[eWellWARRawData_mv_war_main_df['API_WELL_NUMBER'] == api12].copy()

        api12_eWellWARRawData_mv_war_main_prop = eWellWARRawData_mv_war_main_prop_df[eWellWARRawData_mv_war_main_prop_df['SN_WAR'].isin(api12_eWellWARRawData_mv_war_main['SN_WAR'])]

        data = {'api12_df': api12_df,
                'api12_BoreholeRawData': api12_BoreholeRawData,
                'api12_eWellAPDRawData': api12_eWellAPDRawData,
                'api12_eWellEORRawData': api12_eWellEORRawData,
                'api12_eWellWARRawData_mv_war_main': api12_eWellWARRawData_mv_war_main,
                'api12_eWellWARRawData_mv_war_main_prop': api12_eWellWARRawData_mv_war_main_prop}

        return data


    def get_Borehole_apd_for_all_wells(self, BoreholeRawData_df, eWellAPDRawData_df):

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

        file_name = 'data/modules/bsee/csv/online_query_raw_data/BoreholeRawData_mv_boreholes_all.csv'

        file_is_valid, file_name = is_file_valid_func(file_name)
        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
            borehole_codes = cfg['parameters']['borehole_codes']

            BOREHOLE_STAT_CD = df['BOREHOLE_STAT_CD']

            df['BOREHOLE_STAT_DESC'] = None
            BOREHOLE_STAT_DESC = [None]*len(BOREHOLE_STAT_CD)
            for idx in range(0, len(BOREHOLE_STAT_CD)):
                code = BOREHOLE_STAT_CD.iloc[idx]
                for item in borehole_codes:
                    if code == item['BOREHOLE_STAT_CD']:
                        BOREHOLE_STAT_DESC[idx] = item['BOREHOLE_STAT_DESC']

            df['BOREHOLE_STAT_DESC'] = BOREHOLE_STAT_DESC
        else:
            raise Exception(f"File not found: {file_name}")




        return df

    def get_eWellEORRawData_from_csv(self, cfg):

        file_name = 'data/modules/bsee/csv/online_query_raw_data/eWellEORRawData_mv_eor_mainquery.csv'

        file_is_valid, file_name = is_file_valid_func(file_name)
        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
        else:
            raise Exception(f"File not found: {file_name}")

        return df


    def get_eWellAPDRawData_from_csv(self, cfg):

        # Load CSV files
        file_name = 'data/modules/bsee/csv/online_query_raw_data/eWellAPDRawData_mv_apd_main.csv'

        file_is_valid, file_name = is_file_valid_func(file_name)
        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
        else:
            raise Exception(f"File not found: {file_name}")

        return df

    def get_eWellWARRawData_mv_war_main_from_csv(self, cfg):
        
        # Load CSV files
        file_name = 'data/modules/bsee/csv/online_query_raw_data/eWellWARRawData_mv_war_main.csv'

        file_is_valid, file_name = is_file_valid_func(file_name)
        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
        else:
            raise Exception(f"File not found: {file_name}")

        return df

    def get_eWellWARRawData_mv_war_main_prop_from_csv(self, cfg):
        
        # Load CSV files
        file_name = 'data/modules/bsee/csv/online_query_raw_data/eWellWARRawData_mv_war_main_prop.csv'

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

        output_path = 'data/modules/bsee/csv/well'
        # Save to a new CSV file
        merged_df.to_csv(os.path.join(output_path, 'Join_Borehole_APD.csv'), index=False)

        return merged_df

    def pd_merge_clean_column_names(self, merged_df):
        merged_df = merged_df.loc[:, ~merged_df.columns.str.endswith('_y')]
        merged_df.columns = merged_df.columns.str.replace('_x', '', regex=True)
        return merged_df
    
    def get_api12_data(self, cfg):

        if cfg['data']['by'] == 'API12':
            api12_array = self.get_api12_array_by_api12(cfg)
        elif cfg['data']['by'] == 'block':
            api12_array = self.get_api12_array_by_block(cfg)

        cfg[cfg['basename']].update({'api12': api12_array})

        return cfg

    def get_api12_array_by_api12(self, cfg):
        
        api12_array = []
        groups = cfg['data']['groups']
        for group in groups:
            api12 = [group['api12']]
            api12_array = api12_array + api12

        return api12_array

    def get_api12_array_by_block(self, cfg):
        cfg, block_data_groups = block_data.router(cfg)
        
        api12_array = []
        if cfg[cfg['basename']]['well_data']['type'] == 'csv':
            csv_groups = cfg[cfg['basename']]['well_data']['groups']
            for csv_group in csv_groups:
                df = pd.read_csv(csv_group['file_name'])
                api12_csv_group = df['API Well Number'].unique().tolist()
                api12_array = api12_array + api12_csv_group

        return cfg, block_data_groups, api12_array
    
