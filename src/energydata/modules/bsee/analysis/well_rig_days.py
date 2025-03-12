import numpy as np
import pandas as pd
from dateutil.parser import parse

class WellRigDays:
    """
    Class for calculating the number of days a rig is on a well.
    """

    def __init__(self):
        pass

    def get_rig_days_and_drilling_wt_worked_on_api12(self, cfg, api12_df , api12):
        self.well_activity_rig_days = pd.DataFrame()

        max_allowed_npt = cfg['parameters']['max_allowed_npt']
        borehole_codes = cfg['parameters']['borehole_codes']
        BOREHOLE_STAT_CD = api12_df['BOREHOLE_STAT_CD']

        api12_df['BOREHOLE_STAT_DESC'] = None
        BOREHOLE_STAT_DESC = [None]*len(BOREHOLE_STAT_CD)
        for idx in range(0, len(BOREHOLE_STAT_CD)):
            code = BOREHOLE_STAT_CD.iloc[idx]
            for item in borehole_codes:
                if code == item['BOREHOLE_STAT_CD']:
                    BOREHOLE_STAT_DESC[idx] = item['BOREHOLE_STAT_DESC']

        api12_df['BOREHOLE_STAT_DESC'] = BOREHOLE_STAT_DESC

        well_war = api12_df[api12_df.API12 == api12].copy()
        well_info_df = api12_df[api12_df.API12 == api12].copy()
        spud_date = well_info_df['WELL_SPUD_DATE'].iloc[0]
        td_date = well_info_df['TOTAL_DEPTH_DATE'].iloc[0]

        well_war['Rig_days'] = 0
        well_war['npt_raw'] = 0
        well_war['npt'] = 0

        war_drilling_days_flag = False
        for df_row in range(0, len(well_war)):
            war_days = (parse(well_war['WAR_END_DT'].iloc[df_row]) - parse(well_war['WAR_START_DT'].iloc[df_row])).days
            
            well_war.loc[df_row, 'Rig_days'] = war_days + 1 if war_days > 0 else war_days
            
            if df_row > 0:
                start_date = parse(well_war['WAR_START_DT'].iloc[df_row])
                end_date = parse(well_war['WAR_END_DT'].iloc[df_row - 1])
                npt_raw = (start_date - end_date).days - 1
                if (npt_raw <= max_allowed_npt):
                    if (npt_raw > 0):
                        well_war.loc[df_row, 'npt_raw'] = npt_raw
                elif (td_date > start_date):
                    war_drilling_days_flag = True
                if (end_date <= td_date) and (start_date > td_date):
                    end_date = td_date
                npt = (start_date - end_date).days - 1
                if (start_date > td_date) and (npt <= max_allowed_npt):
                    if (npt > 0):
                        well_war.loc[df_row, 'npt'] = npt

        rigs = list(well_war.RIG_NAME.unique())

        rigdays_list = []
        rigdays_dict = []
        rigdays_str_array = []
        total_rigdays = 0
        for rig in rigs:
            rig_days = well_war[well_war.RIG_NAME == rig].Rig_days.sum()
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

        api12_war_days = well_war.groupby(['API12', 'BOREHOLE_STAT_DESC'])['Rig_days'].sum().reset_index()
        self.well_activity_rig_days = pd.concat([self.well_activity_rig_days, api12_war_days], ignore_index=True)

        well_war_npt_days = well_war['npt'].sum()
        try:
            completion_days = api12_war_days[api12_war_days['BOREHOLE_STAT_DESC'] ==
                                             'BOREHOLE COMPLETED'].Rig_days.sum()
            npt_days = well_war[(well_war['BOREHOLE_STAT_DESC'] == 'BOREHOLE COMPLETED')].npt.sum()
            completion_days = completion_days + npt_days
        except:
            completion_days = 0
        try:
            sidetrack_days = api12_war_days[(
                api12_war_days['BOREHOLE_STAT_DESC'] == 'BOREHOLE SIDETRACKED')].Rig_days.sum()
            npt_days = well_war[(well_war['BOREHOLE_STAT_DESC'] == 'BOREHOLE SIDETRACKED')].npt.sum()
            sidetrack_days = sidetrack_days + npt_days
        except:
            sidetrack_days = 0
        try:
            abandon_days = api12_war_days[(api12_war_days['BOREHOLE_STAT_DESC'] == 'PERMANENTLY ABANDONED') | (
                api12_war_days['BOREHOLE_STAT_DESC'] == 'TEMPORARILY ABANDONED')].Rig_days.sum()
            npt_days = well_war[(well_war['BOREHOLE_STAT_DESC'] == 'PERMANENTLY ABANDONED') |
                                (well_war['BOREHOLE_STAT_DESC'] == 'TEMPORARILY ABANDONED')].npt.sum()
            abandon_days = abandon_days + npt_days
        except:
            abandon_days = 0
        try:
            war_drilling_days = api12_war_days[(api12_war_days['BOREHOLE_STAT_DESC'] == 'DRILLING ACTIVE') | (
                api12_war_days['BOREHOLE_STAT_DESC'] == 'DRILLING SUSPENDED')].Rig_days.sum()
            spud_to_td_days = (td_date - spud_date).days + 1
            npt_days = well_war[(well_war['BOREHOLE_STAT_DESC'] == 'DRILLING ACTIVE') |
                                (well_war['BOREHOLE_STAT_DESC'] == 'DRILLING SUSPENDED')].npt.sum()
            if war_drilling_days_flag:
                spud_to_td_days = war_drilling_days
                npt_days = well_war[(well_war['BOREHOLE_STAT_DESC'] == 'DRILLING ACTIVE') |
                                    (well_war['BOREHOLE_STAT_DESC'] == 'DRILLING SUSPENDED')].npt_raw.sum()
            drilling_days = spud_to_td_days + abandon_days + sidetrack_days + npt_days
        except:
            drilling_days = 0

        well_days_dict = {
            'drilling_days': drilling_days,
            'abandon_days': abandon_days,
            'completion_days': completion_days,
            'well_war_npt_days': well_war_npt_days,
            'rigdays_dict': rigdays_dict,
            'total_rigdays': total_rigdays
        }

        MAX_DRILL_FLUID_WGT = well_war.DRILL_FLUID_WGT.max()

        return rig_str, MAX_DRILL_FLUID_WGT, well_days_dict

