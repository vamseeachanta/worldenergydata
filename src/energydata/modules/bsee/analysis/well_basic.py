# Standard library imports
import json
import logging
import datetime

# # # Third party imports
import pandas as pd

from assetutilities.common.data import Transform
from energydata.modules.bsee.data.bsee_data import BSEEData

# from energydata.common.bsee_data_manager import BSEEData

# from energydata.common.data import AttributeDict, transform_df_datetime_to_str

transform = Transform()
bsee_data = BSEEData()

class WellAnalysis():

    def __init__(self):
        pass
        # self.bsee_data = BSEEData(self.cfg)

    def router(self, cfg, well_data_by_api,bore_hole_apd_df):
        # well_data_by_api['Total Depth Date'] = None
        # well_data_by_api['Total Depth Date'] = datetime.datetime.now()
        self.prepare_api12_data(well_data_by_api, bore_hole_apd_df)
        self.add_sidetracklabel_rig_rigdays(WAR_summary, ST_BP_and_tree_height)
        # self.evaluate_well_distances()
        self.prepare_casing_data(well_data, well_tubulars_data)
        self.prepare_completion_data(completion_data)
        self.prepare_well_paths(directional_surveys)
        self.prepare_formation_data()
        self.prepare_field_well_data()

    def prepare_api12_data(self, well_data,merged_data):

        self.output_data_api12_df = merged_data.copy()
        self.add_gis_info_to_well_data()
        self.output_data_api12_df['O_PROD_STATUS'] = 0
        self.output_data_api12_df['O_CUMMULATIVE_PROD_MMBBL'] = 0
        self.output_data_api12_df['DAYS_ON_PROD'] = 0
        self.output_data_api12_df['O_MEAN_PROD_RATE_BOPD'] = 0
        self.output_data_api12_df['TOTAL_DEPTH_DATE'] = pd.to_datetime(self.output_data_api12_df['TOTAL_DEPTH_DATE'])
        self.output_data_api12_df['WELL_SPUD_DATE'] = pd.to_datetime(self.output_data_api12_df['WELL_SPUD_DATE'])
        self.output_data_api12_df['COMPLETION_NAME'] = ""
        self.output_data_api12_df['monthly_production'] = None
        self.output_data_api12_df['xyz'] = None

    def add_gis_info_to_well_data(self):
        gis_cfg = {'Longitude': 'Bottom Longitude', 'Latitude': 'Bottom Latitude', 'label': 'BOT'}
        self.output_data_api12_df = transform.gis_deg_to_distance(self.output_data_api12_df, gis_cfg)
        gis_cfg = {'Longitude': 'Surface Longitude', 'Latitude': 'Surface Latitude', 'label': 'SURF'}
        self.output_data_api12_df = transform.gis_deg_to_distance(self.output_data_api12_df, gis_cfg)
        self.field_x_ref = self.output_data_api12_df.SURF_x.min()
        self.field_y_ref = self.output_data_api12_df.SURF_y.min()
        self.output_data_api12_df['BOT_x_rel'] = self.output_data_api12_df['BOT_x'] - self.field_x_ref
        self.output_data_api12_df['BOT_y_rel'] = self.output_data_api12_df['BOT_y'] - self.field_y_ref
        self.output_data_api12_df['SURF_x_rel'] = self.output_data_api12_df['SURF_x'] - self.field_x_ref
        self.output_data_api12_df['SURF_y_rel'] = self.output_data_api12_df['SURF_y'] - self.field_y_ref

        print("GIS data is formatted")


    def prepare_field_well_data(self):
        API10_list = list(self.output_data_api12_df.API10.unique())
        sum_columns = ['O_CUMMULATIVE_PROD_MMBBL', 'DAYS_ON_PROD', 'Drilling Days', 'Completion Days']
        self.output_data_well_df = self.output_data_api12_df.copy()
        drop_index_array = []
        for well_api10 in API10_list:
            temp_df = self.output_data_api12_df[(self.output_data_api12_df.API10 == well_api10)].copy()
            if len(temp_df) > 1:
                # Clean output_data_well_df
                temp_df.sort_values(by='API12', inplace=True)
                drop_index_array.extend(list(temp_df.index)[:-1])
                well_index = list(temp_df.index)[-1]

                for column in sum_columns:
                    self.output_data_well_df[column].iloc[well_index] = temp_df[column].sum()

                try:
                    drilling_footage_ft = float(self.output_data_well_df['Total Measured Depth'].iloc[well_index]
                                               ) - self.output_data_well_df['Water Depth'].iloc[well_index]
                except:
                    drilling_footage_ft = None
                self.output_data_well_df['drilling_footage_ft'].iloc[well_index] = drilling_footage_ft

                if drilling_footage_ft is not None:
                    drilling_days_per_10000_ft = round(
                        self.output_data_well_df['Drilling Days'].iloc[well_index] / drilling_footage_ft * 10000, 1)
                else:
                    drilling_days_per_10000_ft = None
                self.output_data_well_df['drilling_days_per_10000_ft'].iloc[well_index] = drilling_days_per_10000_ft

                self.output_data_well_df['O_PROD_STATUS'].iloc[well_index] = temp_df['O_PROD_STATUS'].max()
                self.output_data_well_df['RIG_LAST_DATE_ON_WELL'].iloc[well_index] = temp_df[
                    'RIG_LAST_DATE_ON_WELL'].dropna().max()
                self.output_data_well_df['Spud Date'].iloc[well_index] = temp_df['Spud Date'].dropna().min()
                if self.output_data_well_df['DAYS_ON_PROD'].iloc[well_index] > 0:
                    self.output_data_well_df['O_MEAN_PROD_RATE_BOPD'].iloc[
                        well_index] = self.output_data_well_df['O_CUMMULATIVE_PROD_MMBBL'].iloc[
                            well_index] / self.output_data_well_df['DAYS_ON_PROD'].iloc[well_index]

        self.output_data_well_df.drop(drop_index_array, inplace=True)
        self.output_data_well_df['BSEE Well Name'] = self.output_data_well_df['Well Name']
        if len(self.output_data_well_df['Well Name'].unique()) < len(self.output_data_well_df):
            # Third party imports
            from common.data import Transform
            trans = Transform()
            old_list = list(self.output_data_well_df['Well Name'])

            cfg_temp = {'list': old_list, 'transform_character': 'trailing_alphabet'}
            new_list = trans.transform_list_to_unique_list(cfg_temp)

            self.output_data_well_df['Well Name'] = new_list

    def prepare_well_paths(self, directional_surveys):
        self.output_well_path_for_db = {}
        self.output_data_well_path = {}
        API12_list = list(directional_surveys.API12.unique())
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
                
    def prepare_well_paths(self, directional_surveys):
        self.output_well_path_for_db = {}
        self.output_data_well_path = {}
        API12_list = list(directional_surveys.API12.unique())
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

    def assign_st_bp_tree_info(self, ST_BP_and_tree_height, well_api12):
        sidetrack_no = 0
        bypass_no = 0
        tree_elevation_aml = None
        bp_st_tree_info = ST_BP_and_tree_height[ST_BP_and_tree_height.API12 == well_api12].copy()
        if len(bp_st_tree_info) > 0:
            bp_st_tree_info.sort_values(by=['SN_EOR'])
            sidetrack_no = float(bp_st_tree_info.WELL_NM_ST_SFIX.iloc[0])
            bypass_no = float(bp_st_tree_info.WELL_NM_BP_SFIX.iloc[0])
            tree_elevation_aml = bp_st_tree_info.SUBSEA_TREE_HEIGHT_AML.iloc[0]
            if tree_elevation_aml is not None:
                tree_elevation_aml = float(tree_elevation_aml)

        return sidetrack_no, bypass_no, tree_elevation_aml
    
    def get_drilling_completion_summary(self):
        development_wells_df = self.output_data_api12_df[self.output_data_api12_df['Well Purpose'] == 'D'].copy()

        total_wellbores = len(self.output_data_well_df) + self.output_data_well_df['Side Tracks'].sum()

        avg_water_depth = round(self.output_data_well_df['Water Depth'].mean(), 0)

        avg_drilling_footage_ft = round(
            pd.to_numeric(self.output_data_well_df['drilling_footage_ft'], errors='coerce').mean(), 0)
        avg_drilling_days_per_10000_ft = round(
            pd.to_numeric(self.output_data_well_df['drilling_days_per_10000_ft'], errors='coerce').mean(), 1)
        avg_tvd_all_wellbores = round(
            pd.to_numeric(self.output_data_well_df['Total Vertical Depth'], errors='coerce').mean(), 0)
        avg_tmd_all_wellbores = round(
            pd.to_numeric(self.output_data_well_df['Total Measured Depth'], errors='coerce').mean(), 0)
        total_construction_time_all_wellbores = pd.to_numeric(self.output_data_well_df['Drilling Days'],
                                                              errors='coerce').sum()
        total_completion_time_all_wellbores = pd.to_numeric(self.output_data_well_df['Completion Days'],
                                                            errors='coerce').sum()
        total_d_c_time_all_wellbores = total_construction_time_all_wellbores + total_completion_time_all_wellbores

        completed_wells_df = self.output_data_well_df[self.output_data_well_df['Wellbore Status'] == 'COM'].copy()
        completed_wellbores = len(completed_wells_df)

        avg_construction_time_all_wellbores = round(avg_drilling_footage_ft / 10000 * avg_drilling_days_per_10000_ft,
                                                    1)
        total_d_c_estimated_cost = total_d_c_time_all_wellbores * self.rig_day_rate_loaded + completed_wellbores * self.sunk_cost_per_completed_well

        if completed_wellbores > 0:
            avg_mud_weight = round(pd.to_numeric(completed_wells_df['MAX_DRILL_FLUID_WGT'], errors='coerce').mean(), 1)
            estimated_reservoir_pressure = round(
                (avg_tvd_all_wellbores - 1000) * (avg_mud_weight - self.over_balance_ppg) * 0.052, 0)
            estimated_mudline_pressure = round(
                estimated_reservoir_pressure - self.oil_pressure_gradient * (avg_tvd_all_wellbores - avg_water_depth),
                0)
            estimated_dry_tree_tubing_pressure = round(
                estimated_mudline_pressure - self.oil_pressure_gradient * avg_water_depth, 0)

            avg_d_c_time_completed_wellbores = round(total_d_c_time_all_wellbores / completed_wellbores, 1)
            avg_c_time_completed_wellbores = round(total_completion_time_all_wellbores / completed_wellbores, 1)
            d_c_estimated_cost_per_completion = total_d_c_estimated_cost / completed_wellbores
            d_c_estimated_cost_per_subsea_well = d_c_estimated_cost_per_completion + self.cost_of_subsea_equipment
        else:
            estimated_reservoir_pressure = 0
            estimated_mudline_pressure = 0
            estimated_dry_tree_tubing_pressure = 0
            avg_d_c_time_completed_wellbores = 0
            avg_c_time_completed_wellbores = 0
            d_c_estimated_cost_per_completion = 0
            d_c_estimated_cost_per_subsea_well = 0
        total_estimated_cost_for_subsea_wells = d_c_estimated_cost_per_subsea_well * completed_wellbores

        drilling_completion_summary = []
        drilling_completion_summary.append({'Description': 'Water Depth', 'Value': float(avg_water_depth)})
        drilling_completion_summary.append({'Description': 'Total Wellbores', 'Value': int(total_wellbores)})
        drilling_completion_summary.append({
            'Description': 'Avg TVD, All Wellbores',
            'Value': float(avg_tvd_all_wellbores)
        })
        drilling_completion_summary.append({
            'Description': 'Avg TMD, All Wellbores',
            'Value': float(avg_tmd_all_wellbores)
        })
        drilling_completion_summary.append({
            'Description': 'Avg Construction Time, All Wellbores (days)',
            'Value': float(avg_construction_time_all_wellbores)
        })
        drilling_completion_summary.append({
            'Description': 'Completed Wellbores (#)',
            'Value': int(completed_wellbores)
        })
        drilling_completion_summary.append({
            'Description': 'Total D&C Time, Completed Wellbores (days)',
            'Value': float(total_d_c_time_all_wellbores)
        })
        drilling_completion_summary.append({
            'Description': 'Average D&C Time, Completed Wellbores (days)',
            'Value': float(avg_d_c_time_completed_wellbores)
        })
        drilling_completion_summary.append({
            'Description': 'Total Completion Time (days)',
            'Value': float(avg_c_time_completed_wellbores)
        })

        drilling_completion_summary.append({
            'Description': 'Total D&C Estimated Cost (USD)',
            'Value': float(total_d_c_estimated_cost)
        })
        drilling_completion_summary.append({
            'Description': 'Estimated D&C Cost per Completion (USD)',
            'Value': float(d_c_estimated_cost_per_completion)
        })
        drilling_completion_summary.append({
            'Description': 'Estimated Total Subsea Completion per Well (USD)',
            'Value': float(d_c_estimated_cost_per_subsea_well)
        })
        drilling_completion_summary.append({
            'Description': 'Estimated Total Subsea Well Cost (USD)',
            'Value': float(total_estimated_cost_for_subsea_wells)
        })

        drilling_completion_summary.append({
            'Description': 'Estimated Reservoir Pressure (psi)',
            'Value': float(estimated_reservoir_pressure)
        })
        drilling_completion_summary.append({
            'Description': 'Estimated Mudline Pressure (psi)',
            'Value': float(estimated_mudline_pressure)
        })
        drilling_completion_summary.append({
            'Description': 'Estimated Dry Tree Tbg Shut-in Pressure (psi)',
            'Value': float(estimated_dry_tree_tubing_pressure)
        })

        return drilling_completion_summary

    def prepare_casing_data(self, well_data, well_tubulars_data):

        # Third party imports
        import pandas as pd
        self.casing_tubulars = pd.DataFrame()
        if len(well_tubulars_data) > 0:
            well_tubulars_data.WAR_START_DT = pd.to_datetime(well_tubulars_data.WAR_START_DT)
            well_tubulars_data.sort_values(
                by=['API12', 'WAR_START_DT', 'CSNG_HOLE_SIZE', 'CASING_SIZE', 'CSNG_SETTING_BOTM_MD'], inplace=True)
            for df_row in range(0, len(self.output_data_api12_df)):
                well_api12 = self.output_data_api12_df.API12.iloc[df_row]
                temp_df = well_tubulars_data[(well_tubulars_data.API12 == well_api12)].copy()
                max_date = temp_df.WAR_START_DT.max()
                latest_tubulars_df_with_duplicates = temp_df[temp_df.WAR_START_DT == max_date].copy()
                latest_tubulars_df_with_duplicates.reset_index(inplace=True, drop=True)
                latest_tubulars_df = self.clean_tubulars_data(latest_tubulars_df_with_duplicates)
                self.casing_tubulars = pd.concat([self.casing_tubulars, latest_tubulars_df], ignore_index=True)

            self.casing_tubulars['Field NickName'] = self.cfg['custom_parameters']['field_nickname']
            logging.info("Tubing data is prepared")
            self.prepare_casing_tubular_summary_all_wells(well_data)
        else:
            logging.info("Tubing data is not available")
    
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
        self.output_completions['COMP_x_rel'] = self.output_completions['COMP_x'] - self.field_x_ref
        self.output_completions['COMP_y_rel'] = self.output_completions['COMP_y'] - self.field_y_ref
        self.output_completions['Field NickName'] = self.cfg['custom_parameters']['field_nickname']
    
    def prepare_formation_data(self):
        pass

                