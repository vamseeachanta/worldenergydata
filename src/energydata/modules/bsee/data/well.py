import os
import pandas as pd
from copy import deepcopy
import logging
from loguru import logger

from energydata.modules.bsee.data.scrapy_well_data import ScrapyRunnerAPI
from energydata.modules.bsee.data.block_data import BlockData

from assetutilities.common.utilities import is_dir_valid_func
from assetutilities.common.yml_utilities import WorkingWithYAML  # noqa
from assetutilities.common.utilities import get_repository_filename, get_repository_filepath
from assetutilities.modules.zip_utilities.zip_files_to_dataframe import ZipFilestoDf

wwy = WorkingWithYAML()
zip_files_to_df = ZipFilestoDf()

block_data = BlockData()

class WellData:

    def __init__(self):
        pass

    def router(self, cfg):
        
        cfg, well_data  = self.get_well_data_all_wells(cfg)

        #TODO Other data sources
        # directional_surveys = self.bsee_data.get_directional_surveys_by_api10(api10)
        # well_tubulars_data = self.bsee_data.get_well_tubulars_data_by_api10(api10)
        # completion_data = self.bsee_data.get_completion_data_by_api10(api10)

        return cfg, well_data

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

        cfg = self.fetch_well_data_from_websites(cfg)

        well_data_groups = []
        for group in cfg[cfg['basename']]['data']['groups']:
            if 'api12' not in group:
                logger.error(f"API12 not found in group: {group}")
            api12_array = group['api12']
            api12_array_well_data = []
            for api12_idx in range(0, len(api12_array)):
                api12_metadata = group['well_data'][api12_idx].copy()

                merged_api12_df = self.get_api12_merged_df_from_all_sources(cfg, bsee_csv_data, api12_metadata)
                individual_df_data = self.get_api12_data_from_all_sources(cfg, bsee_csv_data, api12_metadata)

                api12_metadata.update({'merged_api12_df': merged_api12_df})
                api12_metadata.update(individual_df_data)

                api12_array_well_data.append(api12_metadata)

            well_data_groups.append(api12_array_well_data)

        return cfg, well_data_groups

    def get_data_source_file(self, cfg, group):
        #TODO SS
        library = 'digitalmodel'
        filename = cfg['filename']
        file_path = os.path.join(cfg['Analysis']['analysis_root_folder'], library, filename)


    def get_api12_merged_df_from_all_sources(self, cfg, bsee_csv_data, api12_metadata):
        api12 = api12_metadata['api12'][0]
        BoreholeRawData_df = bsee_csv_data['BoreholeRawData_df']
        eWellAPDRawData_df = bsee_csv_data['eWellAPDRawData_df']
        eWellEORRawData_df = bsee_csv_data['eWellEORRawData_df']
        eWellWARRawData_mv_war_main_df = bsee_csv_data['eWellWARRawData_mv_war_main_df']
        eWellWARRawData_mv_war_main_prop_df = bsee_csv_data['eWellWARRawData_mv_war_main_prop_df']

        api12_well_data = pd.read_csv(api12_metadata['file_name'])
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

    def get_api12_data_from_all_sources(self, cfg, bsee_csv_data, api12_metadata):
        api12 = api12_metadata['api12'][0]
        api12_df = pd.read_csv(api12_metadata['file_name'])

        BoreholeRawData_df = bsee_csv_data['BoreholeRawData_df']
        eWellAPDRawData_df = bsee_csv_data['eWellAPDRawData_df']
        eWellEORRawData_df = bsee_csv_data['eWellEORRawData_df']
        eWellWARRawData_mv_war_main_df = bsee_csv_data['eWellWARRawData_mv_war_main_df']
        eWellWARRawData_mv_war_main_prop_df = bsee_csv_data['eWellWARRawData_mv_war_main_prop_df']

        datasets = {
            'api12_BoreholeRawData': BoreholeRawData_df,
            'api12_eWellAPDRawData': eWellAPDRawData_df,
            'api12_eWellEORRawData': eWellEORRawData_df,
            'api12_eWellWARRawData_mv_war_main': eWellWARRawData_mv_war_main_df
        }
        data = {'api12_df': api12_df}

        # Filter dataframes by API12 which are not empty 
        for key, df in datasets.items():
            filtered_df = df[df['API_WELL_NUMBER'] == api12].copy()           
            data[key] = filtered_df
        
        # Handling api12_eWellWARRawData_mv_war_main_prop separately since it depends on another dataset
        if 'api12_eWellWARRawData_mv_war_main' in data:
            api12_eWellWARRawData_mv_war_main_prop = eWellWARRawData_mv_war_main_prop_df[
                eWellWARRawData_mv_war_main_prop_df['SN_WAR'].isin(data['api12_eWellWARRawData_mv_war_main']['SN_WAR'])
            ]           
            data['api12_eWellWARRawData_mv_war_main_prop'] = api12_eWellWARRawData_mv_war_main_prop

        return data

    def get_Borehole_apd_for_all_wells(self, BoreholeRawData_df, eWellAPDRawData_df):

        self.Borehole_apd_df = self.get_merged_data(BoreholeRawData_df, eWellAPDRawData_df)
        
        return self.Borehole_apd_df

    def get_Borehole_apd_for_api12(self, cfg, Borehole_apd_df, api12):
        api12_Borehole_apd = Borehole_apd_df[Borehole_apd_df['API_WELL_NUMBER'] == api12].copy()


        return api12_Borehole_apd

    def fetch_well_data_from_websites(self, cfg):
        cfg[cfg['basename']]['data'].update({'type': 'csv'})
        cfg = self.get_well_data_from_website(cfg)

        return cfg
    
    def get_well_data_from_website(self, cfg):
        groups = cfg[cfg['basename']]['data']['groups']
        scrapy_runner_api = ScrapyRunnerAPI()

        for group_idx in range(0, len(groups)):
            group = groups[group_idx]
            api12_array = group.get('api12', [])  # Get API numbers list

            api12_group_output = []
            for api12_idx in range(0, len(api12_array)):
                api12 = api12_array[api12_idx]
                api12_meta_data = {'api12': [api12], 'label': str(api12)}

                api12_data = scrapy_runner_api.run_spider(cfg, api12_meta_data)
                api12_output_cfg = self.generate_output_item(cfg, api12_meta_data)
                api12_group_output.append(api12_output_cfg)

            cfg[cfg['basename']]['data']['groups'][group_idx].update({'well_data': api12_group_output})

        return cfg

    def generate_output_item(self, cfg, input_item):

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
        output_data = input_item_csv_cfg
        
        return output_data
    
    def get_BoreholeRawData_from_csv(self, cfg):

        file_name = 'BoreholeRawData_mv_boreholes_all.csv'

        library_name = 'energydata'
        library_file_cfg = {
            'filename': f"data/modules/bsee/csv/online_query_raw_data/{file_name}",
            'library_name': library_name,
            'repository_path': None
        }

        file_is_valid, file_name = get_repository_filename(library_file_cfg)
        logging.debug(f"file_name: {file_name}")

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

        file_name = 'eWellEORRawData_mv_eor_mainquery.csv'

        library_name = 'energydata'
        library_file_cfg = {
            'filename': f"data/modules/bsee/csv/online_query_raw_data/{file_name}",
            'library_name': library_name,
            'repository_path': None
        }

        file_is_valid, file_name = get_repository_filename(library_file_cfg)
        logging.debug(f"file_name: {file_name}")

        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
        else:
            raise Exception(f"File not found: {file_name}")

        return df


    def get_eWellAPDRawData_from_csv(self, cfg):

        # Load CSV files
        file_name = 'eWellAPDRawData_mv_apd_main.csv'

        library_name = 'energydata'
        library_file_cfg = {
            'filename': f"data/modules/bsee/csv/online_query_raw_data/{file_name}",
            'library_name': library_name,
            'repository_path': None
        }

        file_is_valid, file_name = get_repository_filename(library_file_cfg)
        logging.debug(f"file_name: {file_name}")

        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
        else:
            raise Exception(f"File not found: {file_name}")

        return df

    def get_eWellWARRawData_mv_war_main_from_csv(self, cfg):
        
        # Load CSV files
        file_name = 'eWellWARRawData_mv_war_main.csv'

        library_name = 'energydata'
        library_file_cfg = {
            'filename': f"data/modules/bsee/csv/online_query_raw_data/{file_name}",
            'library_name': library_name,
            'repository_path': None
        }

        file_is_valid, file_name = get_repository_filename(library_file_cfg)
        logging.debug(f"file_name: {file_name}")

        if file_is_valid:
            df = pd.read_csv(file_name, low_memory=False)
        else:
            raise Exception(f"File not found: {file_name}")

        return df

    def get_eWellWARRawData_mv_war_main_prop_from_csv(self, cfg):
        
        # Load CSV files
        file_name = 'eWellWARRawData_mv_war_main_prop.csv'

        library_name = 'energydata'
        library_file_cfg = {
            'filename': f"data/modules/bsee/csv/online_query_raw_data/{file_name}",
            'library_name': library_name,
            'repository_path': None
        }

        file_is_valid, file_name = get_repository_filename(library_file_cfg)
        logging.debug(f"file_name: {file_name}")

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

        filepath = 'data/modules/bsee/csv/well'

        library_name = 'energydata'
        library_file_cfg = {
            'filepath': filepath,
            'library_name': library_name,
            'repository_path': None
        }

        dir_is_valid, repo_filepath = get_repository_filepath(library_file_cfg)
        # Save to a new CSV file
        merged_df.to_csv(os.path.join(repo_filepath, 'Join_Borehole_APD.csv'), index=False)

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

        return cfg, api12_array
    
    def update_cfg_to_wells_api12(self, cfg, api12_array):
        '''
        function which transforms cfg into desired cfg
        '''

        updated_cfg = cfg.copy()
    
        # Update 'data' section
        updated_cfg['data']['by'] = 'API12'
        updated_cfg['data']['well_data'] = True
        updated_cfg['data']['production_data'] = False
        
        # Replace 'groups' with 'api12' array
        updated_cfg['data']['groups'] = [{'api12': api12_array}]
        
        return updated_cfg
        

        
    def get_eWellAPMRawData_from_zip(self, cfg):
        
        columns = [MMS_COMPANY_NUM,
                    API_WELL_NUMBER,
                    WATER_DEPTH,
                    WELL_NM_BP_SFIX,
                    WELL_NM_ST_SFIX,
                    SURF_AREA_CODE,
                    SURF_BLOCK_NUM,
                    SURF_LEASE_NUM,
                    BOTM_AREA_CODE,
                    BOTM_BLOCK_NUM,
                    BOTM_LEASE_NUM,
                    RIG_ID_NUM,
                    BOREHOLE_STAT_CD,
                    WELL_TYPE_CODE,
                    BUS_ASC_NAME]

        #TODO 
        
    