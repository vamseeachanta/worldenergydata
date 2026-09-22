import logging

import pandas as pd

nm_witsml_channel_mappings = {
            'FLOW_IN': ('flow_in_rate', 'galUS/min'),
            'DIFF_PRESS': ('diff_pressure', 'psi'),
            'BIT_ON_BTM': ('bit_status',None),
            'BIT_DEPTH': ('depth', 'ft'),
            'TD_SPEED': ('top_drive_rpm', 'rpm'),
            'Bit Wt. - Auto Driller': ('wob', 'klb'),
            'AVG_ROP_FT_HR': ('rop_average', 'ft/h'),
            'GAMMA_RAY': ('gamma_ray', None),
            'BIT_DPT_MD': ('bit_position', 'ft'),
            'TD_TORQUE': ('top_drive_torque', 'ft.lbf'),
            'STP_PRS_1': ('pump_pressure', 'psi')
        }

unit_conversions = {'kft.lbf': {
                        'ft.lbf': lambda x: x * 1000}}


nov_witml_units_special_characters = {
    '\u00b7': '.'
}


def change_units_by_configuration(input_data:pd.DataFrame, input_units:dict):
    logger = logging.getLogger("drilltrek")
    input_data = input_data.loc[:, nm_witsml_channel_mappings.keys()]  # This is done to avoid two columns with same name when columns are renamed.
    new_column_names = [mapping[0] for mapping in list(nm_witsml_channel_mappings.values())]
    column_mappings = dict(zip(nm_witsml_channel_mappings.keys(), new_column_names))
    input_data.rename(columns=column_mappings, inplace=True)

    for nov_channel_name in nm_witsml_channel_mappings:
        expected_channel, expected_unit = nm_witsml_channel_mappings[nov_channel_name]
        input_unit = input_units[nov_channel_name]

        for special_character, value in nov_witml_units_special_characters.items():
            input_unit = input_unit.replace(special_character, value)

        if expected_unit is not None and expected_unit != input_units[nov_channel_name]:
            transformation_function = unit_conversions.get(input_unit, {}).get(expected_unit, None)
            if transformation_function is None:
                logger.critical("Transformation function None for {0} - unit mapping {1}:{2}".format(nov_channel_name,
                                                                                                     input_unit, expected_unit))
            else:
                logger.info("Transforming channel {0} - unit mapping {1}:{2}".format(nov_channel_name,
                                                                                     input_unit, expected_unit))
                input_data[expected_channel] = transformation_function(input_data[expected_channel])

    return input_data


def change_output_columns(general_results_df:pd.DataFrame):
    results_column_mappings = {'Selected Bit RPM': 'selected_bit_rpm',
                               'Selected MSE': 'selected_mse',
                               'selected Flow Rate': 'selected_flow_rate'}

    if general_results_df is not None:
        general_results_df.rename(columns=results_column_mappings, inplace=True)

    return general_results_df

