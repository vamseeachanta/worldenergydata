# Standard library imports
import os
import json
from loguru import logger 
import datetime

# # # Third party imports
import pandas as pd
import numpy as np

from assetutilities.common.data import Transform
from worldenergydata.modules.bsee.analysis.well_rig_days import WellRigDays

from assetutilities.common.yml_utilities import WorkingWithYAML  # noqa

wwy = WorkingWithYAML()
transform = Transform()
well_rig_days = WellRigDays()

class WellAPI12():

    def __init__(self):
        pass

    def run_well_analysis(self, cfg, data):
        well_groups = data['well_data']

        groups_dict = {}
        if well_groups is None:
            raise ValueError("No well data found in the input data.")

        well_summary_df_groups = pd.DataFrame()
        for group_idx in range(0, len(well_groups)):
            group = well_groups[group_idx]
            well_summary_df_group = pd.DataFrame()
            for well_idx in range(0, len(group)):
                well_data = group[well_idx]
                cfg, api12_analysis = self.get_api12_analysis(cfg, well_data)
                well_summary_df_group = pd.concat([well_summary_df_group, api12_analysis], ignore_index=True)
                well_api12 = well_summary_df_group.API12.iloc[0]
                logger.debug("Well data is prepared for well: " + str(well_api12))
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
            file_label = 'block_api12_' + group_label
            file_name = os.path.join(cfg['Analysis']['result_folder'], file_label + '.csv')
            well_summary_df_group.to_csv(file_name, index=False)

            well_summary_df_groups = pd.concat([well_summary_df_groups, well_summary_df_group], ignore_index=True)
        
        well_timeline_df = self.well_timeline_analysis(cfg, well_summary_df_groups)

        groups_dict['well_summary_df_groups'] = well_summary_df_groups
        groups_dict['well_timeline_df'] = well_timeline_df

        self.save_result_groups(cfg, groups_dict)
        # self.plot_well_timeline_df(cfg, groups_dict)

        return cfg, groups_dict       

    def well_timeline_analysis(self, cfg, well_summary_df_groups):

        well_timeline_df = pd.DataFrame(columns=['date_time'])

        column_keyword_cfg = {'date_column': 'WELL_SPUD_DATE', 'well_count_column': 'WELL_SPUD_COUNT' }
        well_timeline_df = self.get_well_count_by_custom_cfg(well_timeline_df, well_summary_df_groups, column_keyword_cfg)
        column_keyword_cfg = {'date_column': 'TOTAL_DEPTH_DATE', 'well_count_column': 'TOTAL_DEPTH_COUNT' }
        well_timeline_df = self.get_well_count_by_custom_cfg(well_timeline_df, well_summary_df_groups, column_keyword_cfg)
        column_keyword_cfg = {'date_column': 'RIG_LAST_DATE_ON_WELL', 'well_count_column': 'RIG_LAST_DATE_COUNT' }
        well_timeline_df = self.get_well_count_by_custom_cfg(well_timeline_df, well_summary_df_groups, column_keyword_cfg)
        
        # Add production start and end dates to timeline
        column_keyword_cfg = {'date_column': 'START_PRODUCTION_DATE', 'well_count_column': 'PRODUCTION_START_COUNT' }
        well_timeline_df = self.get_well_count_by_custom_cfg(well_timeline_df, well_summary_df_groups, column_keyword_cfg)
        column_keyword_cfg = {'date_column': 'LAST_PRODUCTION_DATE', 'well_count_column': 'PRODUCTION_LAST_COUNT' }
        well_timeline_df = self.get_well_count_by_custom_cfg(well_timeline_df, well_summary_df_groups, column_keyword_cfg)

        well_timeline_df.sort_values(by=['date_time'], inplace=True, ignore_index=True)
        well_timeline_df.reset_index(drop=True, inplace=True)

        return well_timeline_df

    def get_well_count_by_custom_cfg(self, well_timeline_df, well_summary_df_groups, column_keyword_cfg):
        date_column = column_keyword_cfg['date_column']
        
        # Check if the column exists in the dataframe
        if date_column not in well_summary_df_groups.columns:
            return well_timeline_df
            
        df_temp = well_summary_df_groups[[date_column]].copy()
        
        # Filter out empty strings and NaN values before converting to datetime
        df_temp = df_temp[df_temp[date_column].notna() & (df_temp[date_column] != '')]
        
        if df_temp.empty:
            return well_timeline_df
            
        df_temp[date_column] = pd.to_datetime(df_temp[date_column], format='mixed')
        df_temp.sort_values(by=[date_column], inplace=True, ignore_index=True)
        df_temp.reset_index(drop=True, inplace=True)
        well_count_column = column_keyword_cfg['well_count_column']
        df_temp[well_count_column] = df_temp.index + 1
        df_temp.rename(columns={date_column: 'date_time'}, inplace=True)

        well_timeline_df = pd.merge(
            well_timeline_df,
            df_temp,
            on=['date_time'],
            how='outer'
        )
        well_timeline_df = well_timeline_df.replace({np.nan: None})
        well_timeline_df.sort_values(
        by=['date_time'],
        inplace=True
        )
        well_timeline_df.reset_index(drop=True, inplace=True)
        well_timeline_df['date_time'] = pd.to_datetime(well_timeline_df['date_time'])

        return well_timeline_df

    def save_result_groups(self, cfg, groups_dict):

        well_summary_df_groups = groups_dict['well_summary_df_groups']
        well_timeline_df = groups_dict['well_timeline_df']

        groups_label = cfg['meta'].get('label', None)
        if groups_label is None:
            groups_label = cfg['Analysis']['file_name_for_overwrite']

        file_label = 'well_summ_' + groups_label
        result_folder = cfg['Analysis']['result_folder']
        file_name = os.path.join(
            result_folder,
            file_label + '.csv'
        )
        well_summary_df_groups.to_csv(file_name, index=False)

        file_label = 'well_timeline_' + groups_label
        result_folder = cfg['Analysis']['result_folder']
        file_name = os.path.join(
            result_folder,
            file_label + '.csv'
        )
        well_timeline_df.to_csv(file_name, index=False)

    def get_api12_analysis(self, cfg, well_data):

        api12_analysis = None
        api12_analysis = self.get_well_borehole_data(well_data, api12_analysis)
        api12_analysis = self.get_sidetracklabel_and_rig_rigdays(cfg, well_data, api12_analysis)
        api10_directional_surveys = self.get_directional_surveys_by_api10(cfg)

        try:
            # TODO fix and Relocate as needed.
            #self.prepare_casing_data(api12_well_data, well_tubulars_data)
            #self.prepare_completion_data(completion_data)
            self.prepare_well_paths(api10_directional_surveys)
            self.prepare_formation_data()
        except Exception as e:
            logger.error(e)

        logger.info("API12 data analysis ... COMPLETE")

        return cfg, api12_analysis
    
    def get_directional_surveys_by_api10(self, cfg):
        """
        Fetches the survey data (dsptsdelimit) for API12 well 
        Analysis is performed on 1 well and visulaization is also done.
        """

        API12_num = cfg['data']['groups'][0]['api12'][0]
        survey_data_path = r"data\modules\bsee\bin\dsptsdelimit"
        library_name = 'worldenergydata'
        library_file_cfg = {
            'filepath': survey_data_path,
            'library_name': library_name
        }
        library_path = wwy.get_library_filepath(library_file_cfg, src_relative_location_flag=False)
        file = os.path.join(library_path, 'dsptsdelimit.bin')
        survey_df = pd.read_pickle(file)

        api12_survey_df = survey_df[survey_df['API_WELL_NUMBER'] == API12_num].copy()
        if api12_survey_df.empty:
            logger.warning(f"No survey data found for API12: {API12_num}")
            return 
        api12_survey_df['API10'] = api12_survey_df['API_WELL_NUMBER'].astype(str).str[:10]
        # Reorder columns: move API10 to front
        cols = ['API10'] + [col for col in api12_survey_df.columns if col != 'API10']
        api12_survey_df = api12_survey_df[cols]
        # rename column API_WELL_NUMBER to API12
        api12_survey_df.rename(columns={'API_WELL_NUMBER': 'API12'}, inplace=True)

        return api12_survey_df

    def get_well_borehole_data(self, well_data, api12_analysis):

        # api12_df = well_data['api12_df']
        #api12_eWellAPDRawData = well_data['api12_eWellAPDRawData']
        borehole_raw_data = well_data['api12_BoreholeRawData']

        if borehole_raw_data.empty:
            return pd.DataFrame([{
                'API12': '',
                'API10': '',
                'TOTAL_DEPTH_DATE': pd.NaT,
                'WELL_SPUD_DATE': pd.NaT,
                'COMPLETION_NAME': ''
            }])

        try:
            API12 = str(borehole_raw_data['API_WELL_NUMBER'].iloc[0])
        except (IndexError, KeyError):
            API12 = ''

        API10 = API12[:10] if API12 else ''

        TOTAL_DEPTH_DATE = pd.to_datetime(
            borehole_raw_data['TOTAL_DEPTH_DATE'].max(), errors='coerce'
        )

        WELL_SPUD_DATE = pd.to_datetime(
            borehole_raw_data['WELL_SPUD_DATE'].max(), errors='coerce'
        )

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
        API12_val = api12_analysis.API12.iloc[0]
        if pd.notna(API12_val) and str(API12_val).strip() != "":
            well_api12 = api12_analysis.API12.iloc[df_row]
            logger.debug(f"Processing well: {well_api12}")

        sidetrack_no, bypass_no, tree_elevation_aml = self.get_st_bp_tree_info(api12_df)
        api12_analysis.loc[df_row, ['Sidetrack No', 'Bypass No', 'Tree Height Above Mudline']] = [sidetrack_no, bypass_no, tree_elevation_aml]

        rig_analysis = well_rig_days.rig_analysis(cfg, api12_df, api12_eWellWARRawData_mv_war_main, api12_eWellWARRawData_mv_war_main_prop)
        rig_str = rig_analysis['rig_str']
        api12_war_days = rig_analysis['api12_war_days']
        rig_days_from_milestone = rig_analysis['rig_days_from_milestone']

        api12_analysis['Rigs'] = rig_str
        
        if api12_war_days is not None:
            api12_analysis['rigdays_by_war'] = json.dumps(api12_war_days)
            api12_analysis['rigdays_by_milestone'] = json.dumps(rig_days_from_milestone)
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

    def get_st_bp_tree_info(self, api12_df):
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

    def prepare_well_paths(self, directional_surveys):
        self.output_well_path_for_db = {}
        self.output_data_well_path = {}
        API12_list = list(directional_surveys.API_WELL_NUMBER.unique())
        count = 0
        for api12 in API12_list:
            count = count + 1
            api12_dir_survey_df = directional_surveys[directional_surveys.API12 == api12].copy()
            api12_dir_survey_df['az'] = 0
            api12_dir_survey_df['inc'] = 0
            api12_dir_survey_df['md'] = api12_dir_survey_df['SURVEY_POINT_MD']

            for df_row in range(0, len(api12_dir_survey_df)):
                WELL_N_S_CODE = api12_dir_survey_df.iloc[df_row]['WELL_N_S_CODE']
                WELL_E_W_CODE = api12_dir_survey_df.iloc[df_row]['WELL_E_W_CODE']
                Azimuth_quadrant_angle = api12_dir_survey_df.iloc[df_row][
                    'DIR_DEG_VAL'] + api12_dir_survey_df.iloc[df_row]['DIR_MINS_VAL'] / 60
                Inclination = api12_dir_survey_df.iloc[df_row][
                    'INCL_ANG_DEG_VAL'] + api12_dir_survey_df.iloc[df_row]['INCL_ANG_MIN_VAL'] / 60
                if (WELL_N_S_CODE == 'N'):
                    if (WELL_E_W_CODE == 'E'):
                        Azimuth = Azimuth_quadrant_angle
                    else:
                        Azimuth = 360 - Azimuth_quadrant_angle
                else:
                    if (WELL_E_W_CODE == 'E'):
                        Azimuth = 180 - Azimuth_quadrant_angle
                    else:
                        Azimuth = 180 + Azimuth_quadrant_angle
                api12_dir_survey_df['az'].iloc[df_row] = Azimuth
                api12_dir_survey_df['inc'].iloc[df_row] = Inclination

            print('Processing Survey for api12 {} of {}'.format(count, len(API12_list)))
            survey_xyz = self.process_survey_xyz(api12_dir_survey_df)
            survey_xyz_wh_adjusted = self.add_relative_WH_positions(api12, survey_xyz)
            self.output_data_well_path.update({api12: survey_xyz_wh_adjusted})
            survey_for_db = pd.DataFrame()
            survey_for_db['x'] = survey_xyz_wh_adjusted['x_coor']
            survey_for_db['y'] = survey_xyz_wh_adjusted['y_coor']
            survey_for_db['z'] = survey_xyz_wh_adjusted['z_coor']
            survey_for_db = survey_for_db.round(decimals=1)
            try:
                api10_value = self.get_API10_from_well_API(api12)
                label = self.output_data_well_df[self.output_data_well_df.API10 == api10_value]['Well Name'].values[
                    0] + '-' + self.output_data_well_df[self.output_data_well_df.API10 ==
                                                        api10_value]['Sidetrack and Bypass'].values[0]
                label = label.strip()
            except:
                label = str(api12)
            output_well_path_for_db = {"data": survey_for_db.to_dict(orient='records'), "label": label}
            temp_df = self.output_data_api12_df[(self.output_data_api12_df.API12 == api12)].copy()
            if len(temp_df) > 0 and len(survey_for_db) > 0:
                df_row_index = temp_df.index[0]
                self.output_data_api12_df['xyz'].iloc[df_row_index] = json.dumps(output_well_path_for_db)
    
    def prepare_formation_data(self):
        pass

    def plot_well_timeline_df(self, cfg, groups_dict):
        import plotly.express as px

        well_timeline_df = groups_dict['well_timeline_df']
        df_melted = well_timeline_df.melt(id_vars='date_time', value_vars=['WELL_SPUD_COUNT', 'TOTAL_DEPTH_COUNT','RIG_LAST_DATE_COUNT', 'PRODUCTION_START_COUNT', 'PRODUCTION_LAST_COUNT'],
                    var_name='type', value_name='count') 
               
        df_melted = df_melted.rename(columns={'date_time': 'Date'})
        df_melted['Date'] = pd.to_datetime(df_melted['Date'])
        #custom date range on x axis
        df_filtered = df_melted[
                (df_melted['Date'] >= '2007-01-01') &
                (df_melted['Date'] <= '2025-04-03') ]

        fig = px.line(
            df_filtered,
            x='Date',
            y='count',
            color='type',
            markers=True,
            title='Well Timeline Analysis'
        )
        groups_label = cfg['meta'].get('label', None)
        if groups_label is None:
            groups_label = cfg['Analysis']['file_name_for_overwrite']

        file_label = 'well_timeline_' + groups_label
        result_folder = cfg['Analysis']['result_folder']
        file_name = os.path.join(result_folder, 'Plot',file_label + '.html')
        fig.write_html(file_name, include_plotlyjs="cdn")
    
    def process_survey_xyz(self, survey):
        # calcualted x is northing and y is easting
        import numpy as np
        import pandas as pd
        survey_xyz = survey[['md', 'inc', 'az']]
        survey_xyz = survey_xyz.sort_values(by=['md'])
        survey_xyz = survey_xyz.reset_index(drop=True)
        survey_xyz = survey_xyz.drop_duplicates(subset=['md'], keep='first')

        survey_xyz.loc[:, 'inc_diff'] = survey_xyz['inc'].diff()
        survey_xyz.loc[:, 'md_diff'] = survey_xyz['md'].diff()
        survey_xyz.loc[:, 'az_diff'] = survey_xyz['az'].diff()
        survey_xyz = survey_xyz.fillna(0)

        for i in range(0, np.shape(survey_xyz)[0]):
            if survey_xyz['az_diff'].iloc[i] > 180:
                survey_xyz.loc[i, 'az_diff'] = survey_xyz.loc[i, 'az_diff'] - 360
            elif survey_xyz['az_diff'].iloc[i] < -180:
                survey_xyz.loc[i, 'az_diff'] = survey_xyz.loc[i, 'az_diff'] + 360

        survey_xyz.loc[:, 'inc_ave'] = survey_xyz['inc'].rolling(window=2).mean()
        survey_xyz.loc[:, 'build_rate'] = survey_xyz['inc_diff'] / survey_xyz['md_diff']
        survey_xyz.loc[:, 'turn_rate'] = survey_xyz['az_diff'] / survey_xyz['md_diff']

        md_diff = np.array(survey_xyz['md_diff'][1:])
        build_rate = np.array(survey_xyz['build_rate'])
        turn_rate = np.array(survey_xyz['turn_rate'])

        inc_ave = np.array(survey_xyz['inc_ave']) * np.pi / 180
        inc_start = np.array(survey_xyz['inc'][:-1]) * np.pi / 180
        inc_end = np.array(survey_xyz['inc'][1:]) * np.pi / 180
        az_start = np.array(survey_xyz['az'][:-1]) * np.pi / 180
        az_end = np.array(survey_xyz['az'][1:]) * np.pi / 180

        x_coor = np.array(np.zeros([np.shape(survey_xyz)[0], 1]))
        y_coor = np.array(np.zeros([np.shape(survey_xyz)[0], 1]))
        z_coor = np.array(np.zeros([np.shape(survey_xyz)[0], 1]))

        dog_leg_sq = np.sin((inc_end - inc_start) / 2) ** 2 + np.sin(inc_start) * np.sin(inc_end) * \
                     np.sin((az_end - az_start) / 2) ** 2
        dog_leg = 2 * np.arcsin(np.sqrt(dog_leg_sq))
        dog_leg[dog_leg < 10**-6] = 10**-6
        rf = md_diff / dog_leg * np.tan(dog_leg / 2)

        delta_x = (np.sin(inc_start) * np.cos(az_start) + np.sin(inc_end) * np.cos(az_end)) * rf
        delta_y = (np.sin(inc_start) * np.sin(az_start) + np.sin(inc_end) * np.sin(az_end)) * rf
        delta_z = (np.cos(inc_start) + np.cos(inc_end)) * rf

        x_coor[1:, 0] = np.cumsum(delta_x)
        y_coor[1:, 0] = np.cumsum(delta_y)
        z_coor[1:, 0] = np.cumsum(delta_z)
        dz = np.diff(z_coor, axis=0)
        dz = np.insert(dz, 0, 0, axis=0)

        dls = np.sqrt(build_rate**2 + (np.sin(inc_ave))**2 * turn_rate**2)
        dls = dls.reshape(dls.shape[0], 1)
        xyz_table = pd.DataFrame(np.hstack((x_coor, y_coor, z_coor, dz, dls)),
                                 columns=['x_coor', 'y_coor', 'z_coor', 'dz', 'dls'])
        survey_xyz = pd.concat([survey_xyz, xyz_table], axis=1)
        survey_xyz.fillna(0, inplace=True)

        return survey_xyz
    
    def add_relative_WH_positions(self, api12, survey_xyz):
        api12_df = self.output_data_api12_df[self.output_data_api12_df.API12 == api12].copy()
        survey_xyz_wh_adjusted = survey_xyz.copy()
        survey_xyz_wh_adjusted['x_coor'] = survey_xyz_wh_adjusted['x_coor'] + api12_df.SURF_x_rel.iloc[0]
        survey_xyz_wh_adjusted['y_coor'] = survey_xyz_wh_adjusted['y_coor'] + api12_df.SURF_y_rel.iloc[0]

        return survey_xyz_wh_adjusted
    
    def plot_field_wells(self):
        if self.output_data_well_path:
            import matplotlib.pyplot as plt
            from mpl_toolkits import mplot3d
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
            api12_list = list(self.output_data_well_path.keys())
            labels_plotted = []
            for api12 in api12_list:
                api10 = self.get_API10_from_well_API(api12)
                # stones_custom_list = [6081240095, 6081240099, 6081240117, 6081240104, 6081240123, 6081240112, 6081240110]
                # custom_list = [6081240095, 6081240099, 6081240117, 6081240104, 6081240123, 6081240112, 6081240110]
                # if api10 in custom_list:
                custom_list = []
                if api10 not in custom_list:
                    survey_xyz = self.output_data_well_path[api12]
                    x, y, z = survey_xyz['x_coor'], survey_xyz['y_coor'], survey_xyz['z_coor']
                    try:
                        api10_value = self.get_API10_from_well_API(api12)
                        label = self.output_data_well_df[self.output_data_well_df.API10 == api10_value][
                            'Well Name'].values[0] + '-' + self.output_data_well_df[
                                self.output_data_well_df.API10 == api10_value]['Sidetrack and Bypass'].values[0]
                        label = label.strip()
                    except:
                        label = str(api12)
                    if label not in labels_plotted:
                        labels_plotted.append(label)
                        ax.plot3D(x, y, z, label=label, linewidth=1)
                        ax.xaxis.set_tick_params(labelsize=7)
                        ax.yaxis.set_tick_params(labelsize=7)
                        ax.zaxis.set_tick_params(labelsize=7)
                        ax.set_xlabel('Easting (ft)', fontsize=8)
                        ax.set_ylabel('Northing (ft)', fontsize=8)
                        ax.set_zlabel('TVD (ft)', fontsize=8)

            ax.invert_zaxis()
            xy_equal_flag = True
            if xy_equal_flag:
                import math
                ylim_old = ax.get_ylim()
                xlim_old = ax.get_xlim()
                ylim_new = []
                xlim_new = []
                yrange = ylim_old[1] - ylim_old[0]
                xrange = xlim_old[1] - xlim_old[0]
                if yrange > xrange:
                    range = round(yrange / 1000) * 1000
                    ylim_new.append(math.floor(ylim_old[0] / 1000) * 1000)
                    ylim_new.append(math.ceil(ylim_old[1] / 1000) * 1000)
                    range = ylim_new[1] - ylim_new[0]
                    xlim_new.append(math.floor(xlim_old[0] / 1000) * 1000)
                    xlim_new.append(range + xlim_new[0])
                else:
                    xlim_new.append(math.floor(xlim_old[0] / 1000) * 1000)
                    xlim_new.append(math.ceil(xlim_old[1] / 1000) * 1000)
                    range = xlim_new[1] - xlim_new[0]
                    ylim_new.append(math.floor(ylim_old[0] / 1000) * 1000)
                    ylim_new.append(range + ylim_new[0])

                ax.set_xlim(xlim_new)
                ax.set_ylim(xlim_new)
            ax.legend(bbox_to_anchor=(1, 0), loc="lower right", bbox_transform=fig.transFigure, ncol=5, fontsize=6)
            fig.savefig(self.cfg['Analysis']['result_folder'] + self.cfg['Analysis']['file_name_for_overwrite'] +
                        '_well_paths.png',
                        bbox_inches='tight',
                        dpi=800)
            plt.close()

