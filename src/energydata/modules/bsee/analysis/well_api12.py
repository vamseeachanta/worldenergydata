# Standard library imports
import os
import json
from loguru import logger 
import datetime

# # # Third party imports
import pandas as pd

from assetutilities.common.data import Transform
from energydata.modules.bsee.analysis.well_rig_days import WellRigDays
# from energydata.common.data import AttributeDict, transform_df_datetime_to_str


transform = Transform()
well_rig_days = WellRigDays()

class WellAPI12():

    def __init__(self):
        pass

    def run_well_analysis(self, cfg, data):
        well_groups = data['well_data']

        well_data_analysis_groups = []
        if well_groups is None:
            raise ValueError("No well data found in the input data.")

        well_group_api12_summary_df = pd.DataFrame()
        for group_idx in range(0, len(well_groups)):
            group = well_groups[group_idx]
            for well_idx in range(0, len(group)):
                well_data = group[well_idx]
                cfg, api12_analysis = self.router(cfg, well_data)
                well_group_api12_summary_df = pd.concat([well_group_api12_summary_df, api12_analysis], ignore_index=True)
                well_api12 = well_group_api12_summary_df.API12.iloc[0]
                # api12_label = str(well_api12)
                # file_name = 'api12_' + api12_label + '_data.csv'
                # file_name = os.path.join(cfg['Analysis']['result_folder'], file_name)
                # well_group_api12_summary_df.to_csv(file_name, index=False)
                logger.info("Well data is prepared for well: " + str(well_api12))

            block_number = cfg['data']['groups'][group_idx].get('bottom_block', [None])[0]
            if block_number is None:
                label = str(group_idx)
            else:
                label = str(block_number)
            file_label = 'block_api12_' + label
            file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.csv')
            well_group_api12_summary_df.to_csv(file_name, index=False)

            # cfg, well_group_api10_summary_df = well_api10_analysis.router(cfg, well_group_api12_summary_df)
            # file_label = 'api10_' + cfg['Analysis']['file_name_for_overwrite'] + '_' + label
            # file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.csv')
            # well_group_api10_summary_df.to_csv(file_name)

        groups_dict['production_df_api12s'] = production_df_api12s

        return cfg, groups_dicts


    def router(self, cfg, well_data):

        api12_analysis = None
        api12_analysis = self.get_well_borehole_data(well_data, api12_analysis)
        api12_analysis = self.get_sidetracklabel_and_rig_rigdays(cfg, well_data, api12_analysis)

        try:
            # TODO fix and Relocate as needed.
            #self.prepare_casing_data(api12_well_data, well_tubulars_data)
            #self.prepare_completion_data(completion_data)
            self.prepare_formation_data()
        except Exception as e:
            logger.error(e)

        logger.info("API12 data analysis ... COMPLETE")

        return cfg, api12_analysis

    def get_well_borehole_data(self, well_data, api12_analysis):

        # api12_df = well_data['api12_df']
        #api12_eWellAPDRawData = well_data['api12_eWellAPDRawData']
        borehole_raw_data = well_data['api12_BoreholeRawData']
        if not borehole_raw_data.empty:
            api12_BoreholeRawData = well_data['api12_BoreholeRawData']
            
        API12 = str(api12_BoreholeRawData['API_WELL_NUMBER'].iloc[0])
        API10 = API12[0:10]
        TOTAL_DEPTH_DATE = pd.to_datetime(api12_BoreholeRawData['TOTAL_DEPTH_DATE'].max())
        WELL_SPUD_DATE = pd.to_datetime(api12_BoreholeRawData['WELL_SPUD_DATE'].max())
        COMPLETION_NAME = ""

        api12_analysis_dict = {
            'API12': API12,
            'API10': API10,
            'TOTAL_DEPTH_DATE': TOTAL_DEPTH_DATE,
            'WELL_SPUD_DATE': WELL_SPUD_DATE,
            'COMPLETION_NAME': COMPLETION_NAME,
        }

        api12_analysis = pd.DataFrame([api12_analysis_dict])

        return api12_analysis

    def get_sidetracklabel_and_rig_rigdays(self, cfg, well_data, api12_analysis):

        api12_eWellAPDRawData = well_data['api12_eWellAPDRawData']
        api12_BoreholeRawData = well_data['api12_BoreholeRawData']
        api12_eWellEORRawData = well_data['api12_eWellEORRawData']
        api12_df = well_data['merged_api12_df']
        api12_eWellWARRawData_mv_war_main = well_data['api12_eWellWARRawData_mv_war_main']
        api12_eWellWARRawData_mv_war_main_prop = well_data['api12_eWellWARRawData_mv_war_main_prop']

        if not api12_eWellAPDRawData.empty:
            api12_analysis['WELL_NM_ST_SFIX'] = api12_eWellAPDRawData['WELL_NM_ST_SFIX'].iloc[0]
            api12_analysis['WELL_NM_BP_SFIX'] = api12_eWellAPDRawData['WELL_NM_BP_SFIX'].iloc[0]
            api12_analysis['WELL_LABEL'] = api12_eWellAPDRawData['WELL_NAME'].iloc[0]
            api12_analysis['WELL_NAME'] = api12_eWellAPDRawData['WELL_NAME'].iloc[0]
        if not api12_BoreholeRawData.empty:
            api12_analysis['WELL_NAME_SUFFIX'] = api12_BoreholeRawData['WELL_NAME_SUFFIX'].iloc[0]
        
        if not api12_eWellEORRawData.empty:
            api12_analysis['SUBSEA_TREE_HEIGHT_AML'] = api12_eWellEORRawData['SUBSEA_TREE_HEIGHT_AML'].max()

        if not api12_eWellWARRawData_mv_war_main_prop.empty:
            api12_analysis['MAX_DRILL_FLUID_WGT'] = float(api12_eWellWARRawData_mv_war_main_prop['DRILL_FLUID_WGT'].max())

        api12_analysis['drilling_footage_ft'] = 0
        api12_analysis['drilling_days_per_10000_ft'] = 0

        if not api12_eWellWARRawData_mv_war_main.empty:
            api12_analysis['RIG_LAST_DATE_ON_WELL'] = api12_eWellWARRawData_mv_war_main.WAR_END_DT.max()
        
        if not api12_df.empty:
            api12_analysis['Water Depth (feet)'] = api12_df['Water Depth (feet)'].iloc[0]
            api12_analysis['Total Measured Depth'] = api12_df['BH_TOTAL_MD'].iloc[0]
            api12_analysis['O_PROD_STATUS'] = 0
            api12_analysis['Sidetrack and Bypass'] = api12_df['WELL_NAME_SUFFIX']

        api12_analysis['Rigs'] = ""
        api12_analysis['rigdays_dict'] = ""
        api12_analysis['Drilling Days'] = 0
        api12_analysis['Completion Days'] = 0


        df_row = 0
        well_api12 = api12_analysis.API12.iloc[df_row]
        well_api10 = api12_analysis.API10.iloc[df_row]
        logger.debug(f"Processing well: {well_api12}")

        sidetrack_no, bypass_no, tree_elevation_aml = self.get_st_bp_tree_info(api12_df, well_api12)
        api12_analysis.loc[df_row, ['Sidetrack No', 'Bypass No', 'Tree Height Above Mudline']] = [sidetrack_no, bypass_no, tree_elevation_aml]

        rig_str, api12_war_days = well_rig_days.rig_analysis(cfg, api12_df, api12_eWellWARRawData_mv_war_main, api12_eWellWARRawData_mv_war_main_prop)

        self.get_rig_days_by_well_activity(well_api12)
        api12_analysis['Rigs'] = rig_str
        
        if api12_war_days is not None:
            api12_analysis['rigdays_dict'] = json.dumps(api12_war_days)
            api12_analysis['Drilling Days'] = api12_war_days.get('DRL', 0)
            api12_analysis['Completion Days'] = api12_war_days.get('COM', 0)
        else:
            api12_analysis['rigdays_dict'] = None
            api12_analysis['Drilling Days'] = None
            api12_analysis['Completion Days'] = None


        try:
            drilling_footage_ft = float(api12_analysis['Total Measured Depth'].iloc[df_row]
                                        ) - api12_analysis['Water Depth (feet)'].iloc[df_row]
        except:
            drilling_footage_ft = None
        api12_analysis.loc[df_row, 'drilling_footage_ft'] = drilling_footage_ft

        if drilling_footage_ft is not None:
            drilling_days_per_10000_ft = round(
                api12_analysis['Drilling Days'].iloc[df_row] / drilling_footage_ft * 10000, 1)
        else:
            drilling_days_per_10000_ft = None

        api12_analysis['drilling_days_per_10000_ft'] = api12_analysis['drilling_days_per_10000_ft'].astype(float)
        api12_analysis.loc[df_row, 'drilling_days_per_10000_ft'] = drilling_days_per_10000_ft

        return api12_analysis

    def get_st_bp_tree_info(self, api12_df, api12):
        sidetrack_no = 0
        bypass_no = 0
        tree_elevation_aml = None
        bp_st_tree_info = api12_df[['SN_EOR', 'WELL_NM_ST_SFIX', 'WELL_NM_BP_SFIX', 'SUBSEA_TREE_HEIGHT_AML']].copy()
        if len(bp_st_tree_info) > 0:
            bp_st_tree_info.sort_values(by=['SN_EOR'])
            sidetrack_no = float(bp_st_tree_info.WELL_NM_ST_SFIX.iloc[0])
            bypass_no = float(bp_st_tree_info.WELL_NM_BP_SFIX.iloc[0])
            tree_elevation_aml = bp_st_tree_info.SUBSEA_TREE_HEIGHT_AML.iloc[0]
            if tree_elevation_aml is not None:
                tree_elevation_aml = float(tree_elevation_aml)

        return sidetrack_no, bypass_no, tree_elevation_aml

    def prepare_casing_data(self, well_data, well_tubulars_data):

        # Third party imports
        import pandas as pd
        self.casing_tubulars = pd.DataFrame()
        if len(well_tubulars_data) > 0:
            well_tubulars_data.WAR_START_DT = pd.to_datetime(well_tubulars_data.WAR_START_DT)
            well_tubulars_data.sort_values(
                by=['API12', 'WAR_START_DT', 'CSNG_HOLE_SIZE', 'CASING_SIZE', 'CSNG_SETTING_BOTM_MD'], inplace=True)
            for df_row in range(0, len(api12_df)):
                well_api12 = api12_df.API12.iloc[df_row]
                temp_df = well_tubulars_data[(well_tubulars_data.API12 == well_api12)].copy()
                max_date = temp_df.WAR_START_DT.max()
                latest_tubulars_df_with_duplicates = temp_df[temp_df.WAR_START_DT == max_date].copy()
                latest_tubulars_df_with_duplicates.reset_index(inplace=True, drop=True)
                latest_tubulars_df = self.clean_tubulars_data(latest_tubulars_df_with_duplicates)
                self.casing_tubulars = pd.concat([self.casing_tubulars, latest_tubulars_df], ignore_index=True)

            self.casing_tubulars['Field NickName'] = self.cfg['custom_parameters']['field_nickname']
            logger.info("Tubing data is prepared")
            self.prepare_casing_tubular_summary_all_wells(well_data)
        else:
            logger.info("Tubing data is not available")

    def prepare_completion_data(self, completion_data):
        # Third party imports
        from common.data import Transform
        transform = Transform()
        self.output_completions = completion_data.merge(completion_data,
                                                        how='outer',
                                                        left_on='API12',
                                                        right_on='API12')
        gis_cfg = {'Longitude': 'COMP_LONGITUDE', 'Latitude': 'COMP_LATITUDE', 'label': 'COMP'}
        self.output_completions = transform.gis_deg_to_distance(self.output_completions, gis_cfg)
        self.output_completions['COMP_x_rel'] = self.output_completions['COMP_x'] - field_x_ref
        self.output_completions['COMP_y_rel'] = self.output_completions['COMP_y'] - field_y_ref
        self.output_completions['Field NickName'] = self.cfg['custom_parameters']['field_nickname']

    def prepare_formation_data(self):
        pass

    def get_rig_days_by_well_activity(self, well_api12):
        pass
