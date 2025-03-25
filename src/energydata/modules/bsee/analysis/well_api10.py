# Standard library imports
import json
from loguru import logger 
import datetime

# # # Third party imports
import pandas as pd

from assetutilities.common.data import Transform
# from energydata.common.data import AttributeDict, transform_df_datetime_to_str

transform = Transform()

class WellAPI10():

    def __init__(self):
        pass

    def router(self, cfg, well_group_api12_summary_df):

        well_group_api10_summary_df = well_group_api12_summary_df.copy()
        cfg, well_group_api10_summary_df = self.field_analysis(cfg, well_group_api10_summary_df)

        return cfg, well_group_api10_summary_df

    def field_analysis(self, cfg, well_group_api10_summary_df):

        well_group_api10_summary_df['Field NickName'] = None
        well_group_api10_summary_df['BOEM_FIELDS'] = None
        well_group_api10_summary_df['SIDETRACK_COUNT'] = 0

        if len(well_group_api10_summary_df) > 1:
            for idx in range(0, len(well_group_api10_summary_df)):
                well_name = well_group_api10_summary_df.loc[idx, 'WELL_NAME']
                side_track_by_pass = well_group_api10_summary_df.loc[idx, 'Sidetrack and Bypass']
                well_group_api10_summary_df.loc[idx, 'WELL_LABEL'] = well_name + '_' + side_track_by_pass

        return cfg, well_group_api10_summary_df