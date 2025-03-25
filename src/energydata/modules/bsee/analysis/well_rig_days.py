import numpy as np
import pandas as pd
from dateutil.parser import parse
from loguru import logger

class WellRigDays:
    """
    Class for calculating the number of days a rig is on a well.
    """

    def __init__(self):
        pass

    def rig_analysis(self, cfg, api12_df, api12_eWellWARRawData_mv_war_main, api12_eWellWARRawData_mv_war_main_prop):

        war_data = pd.merge(api12_eWellWARRawData_mv_war_main, api12_eWellWARRawData_mv_war_main_prop, how='left' ,
                                    left_on=['SN_WAR'], right_on=['SN_WAR'])

        spud_date = None
        if api12_df['WELL_SPUD_DATE'].iloc[0] is not np.nan:
            spud_date = parse(api12_df['WELL_SPUD_DATE'].iloc[0])
        
        td_date = None
        if api12_df['TOTAL_DEPTH_DATE'].iloc[0] is not np.nan:
            td_date = parse(api12_df['TOTAL_DEPTH_DATE'].iloc[0])

        war_data['WAR_START_DT'] = [parse(item) for item in war_data['WAR_START_DT']]
        war_data['WAR_END_DT'] = [parse(item) for item in war_data['WAR_END_DT']]
        war_data.sort_values(by=['WAR_START_DT'], inplace=True)

        war_summary = self.get_war_days(cfg, war_data, td_date)

        try:
            rig_str, api12_war_days = self.get_rig_info_and_rig_days(cfg, spud_date, td_date, war_summary)
        except Exception as e:
            logger.error(e)
            rig_str = None
            api12_war_days = None


        return rig_str, api12_war_days

    def get_rig_info_and_rig_days(self, cfg,spud_date, td_date, war_summary):
        try:
            rigs = list(war_summary.RIG_NAME.unique())

            rigdays_list = []
            rigdays_dict = []
            rigdays_str_array = []
            total_rigdays = 0

            for rig in rigs:
                rig_days = war_summary[war_summary.RIG_NAME == rig].rig_days.sum()
                rigdays_list.append(rig_days)
                total_rigdays = total_rigdays + rig_days
                if rig_days > 0:
                    rigdays_dict.append({'rig': rig, 'days': int(rig_days)})
                    if rig is not None:
                        rigdays_str_array.append(rig + " (" + str(rig_days) + ")")
                    else:
                        rigdays_str_array.append('unknown rig' + " (" + str(rig_days) + ")")

            # rigdays_str = ', '.join(rigdays_str_array)
            rigs_for_string = [rig if rig not in [None or np.nan] else 'unknown rig' for rig in rigs]
            rig_str = ', '.join(rigs_for_string)

            api12_war_days_df = war_summary.groupby(['WELL_ACTIVITY_CD'])['rig_days'].sum().reset_index()
            api12_war_days_df_records = api12_war_days_df.to_dict('records')
            
            api12_war_days_dict = {}
            for item in api12_war_days_df_records:
                api12_war_days_dict.update({item['WELL_ACTIVITY_CD']: item['rig_days']})
            

            # well_war_npt_days = war_summary['npt'].sum()
            # try:
            #     completion_days = api12_war_days[api12_war_days['WELL_ACTIVITY_CD'] ==
            #                                     'BOREHOLE COMPLETED'].Rig_days.sum()
            #     npt_days = war_summary[(war_summary['WELL_ACTIVITY_CD'] == 'BOREHOLE COMPLETED')].npt.sum()
            #     completion_days = completion_days + npt_days
            # except Exception as e:
            #     logger.error(e)
            #     completion_days = 0
            # try:
            #     sidetrack_days = api12_war_days[(
            #         api12_war_days['WELL_ACTIVITY_CD'] == 'BOREHOLE SIDETRACKED')].Rig_days.sum()
            #     npt_days = war_summary[(war_summary['WELL_ACTIVITY_CD'] == 'BOREHOLE SIDETRACKED')].npt.sum()
            #     sidetrack_days = sidetrack_days + npt_days
            # except Exception as e:
            #     logger.error(e)
            #     sidetrack_days = 0
            # try:
            #     abandon_days = api12_war_days[(api12_war_days['WELL_ACTIVITY_CD'] == 'PERMANENTLY ABANDONED') | (
            #         api12_war_days['WELL_ACTIVITY_CD'] == 'TEMPORARILY ABANDONED')].Rig_days.sum()
            #     npt_days = war_summary[(war_summary['WELL_ACTIVITY_CD'] == 'PERMANENTLY ABANDONED') |
            #                         (war_summary['WELL_ACTIVITY_CD'] == 'TEMPORARILY ABANDONED')].npt.sum()
            #     abandon_days = abandon_days + npt_days
            # except Exception as e:
            #     logger.error(e)
            #     abandon_days = 0
            # try:
            #     war_drilling_days = api12_war_days[(api12_war_days['WELL_ACTIVITY_CD'] == 'DRILLING ACTIVE') | (
            #         api12_war_days['WELL_ACTIVITY_CD'] == 'DRILLING SUSPENDED')].Rig_days.sum()
            #     spud_to_td_days = (td_date - spud_date).days + 1
            #     npt_days = war_summary[(war_summary['WELL_ACTIVITY_CD'] == 'DRILLING ACTIVE') |
            #                         (war_summary['WELL_ACTIVITY_CD'] == 'DRILLING SUSPENDED')].npt.sum()
            #     if war_drilling_days_flag:
            #         spud_to_td_days = war_drilling_days
            #         npt_days = war_summary[(war_summary['WELL_ACTIVITY_CD'] == 'DRILLING ACTIVE') |
            #                             (war_summary['WELL_ACTIVITY_CD'] == 'DRILLING SUSPENDED')].npt_raw.sum()
            #     drilling_days = spud_to_td_days + abandon_days + sidetrack_days + npt_days
            # except Exception as e:
            #     logger.error(e)
            #     drilling_days = 0

            # well_days_dict = {
            #     'drilling_days': None,
            #     'abandon_days': None,
            #     'completion_days': None,
            #     'well_war_npt_days': None,
            #     'rigdays_dict': None,
            #     'total_rigdays': None,
            #     'api12_war_days': api12_war_days_dict
            # }

        except Exception as e:
            logger.error(e)
            rig_str = {}
            api12_war_days_dict = {}
        
        return rig_str, api12_war_days_dict

    def get_war_days(self, cfg, war_data, td_date):

        max_allowed_npt = cfg['parameters']['max_allowed_npt']
        columns = ['rig_days', 'war_gap_days', 'npt', 'war_drilling_days_flag']
        war_summary = pd.DataFrame(columns=columns, index=range(0, len(war_data)))
        war_summary['RIG_NAME'] = war_data['RIG_NAME']
        war_summary['WELL_ACTIVITY_CD'] = war_data['WELL_ACTIVITY_CD']

        for df_row in range(0, len(war_data)):
            war_drilling_days_flag = False
            rig_days = 0
            war_gap_days = 0
            npt = 0
            
            war_days = (war_data['WAR_END_DT'].iloc[df_row] - war_data['WAR_START_DT'].iloc[df_row]).days

            rig_days = war_days + 1 if war_days > 0 else war_days

            if df_row > 0:
                gap_start_date = war_data['WAR_START_DT'].iloc[df_row]
                gap_end_date = war_data['WAR_END_DT'].iloc[df_row - 1]
                war_gap_days = (gap_start_date - gap_end_date).days - 1
                if (war_gap_days > max_allowed_npt):
                    war_gap_days = 0
                elif td_date is not None and td_date > gap_start_date:
                    war_drilling_days_flag = True
                else:
                    war_drilling_days_flag = None

                if td_date is not None:
                    if (gap_end_date <= td_date) and (gap_start_date > td_date):
                        gap_end_date = td_date
                    npt = (gap_start_date - gap_end_date).days - 1

                    if (gap_start_date > td_date) and (npt <= max_allowed_npt):
                        if (npt <= 0):
                            npt = 0

            values = [rig_days, war_gap_days, npt, war_drilling_days_flag]
            war_summary.loc[df_row, columns] = values

        return war_summary

