"""Retained legacy utilities for field development and data processing.

The unused field-development coordinator and its drilling helpers were retired
together. For WAR rig attribution, fluid weights and phase durations, use
``worldenergydata.bsee.analysis.war_rig_days``. See the retirement note in
``docs/modules/bsee/analysis/legacy_component_retirement.md``.
"""

# Re-export geometry functions
from .ong_fd_geometry import (
    evaluate_well_distances,
    prepare_completion_data,
)

# Re-export production functions
from .ong_fd_production import (
    add_production_from_all_wells,
    add_production_rate_and_date,
    add_production_to_well_data,
    prepare_field_production,
    prepare_field_production_rate,
)

# Re-export summary functions
from .ong_fd_summary import (
    calculate_drilling_completion_summary,
)

# Re-export tubular functions
from .ong_fd_tubulars import (
    clean_tubulars_data,
    prepare_casing_data,
    prepare_casing_tubular_summary_all_wells,
    tubular_summary_based_on_api12_and_hole,
)

# Re-export utility functions for backward compatibility
from .ong_fd_utils import (
    add_gis_info_to_df,
    delete_well_data_for_api10,
    get_api10_from_well_api,
    save_output_data_to_excel,
    transform_list_to_unique,
)

# Re-export wellpath functions
from .ong_fd_wellpath import (
    add_relative_wh_positions,
    convert_survey_to_azimuth_inclination,
    plot_field_wells,
    prepare_well_paths,
    process_survey_xyz,
)

__all__ = [
    "add_gis_info_to_df",
    "add_production_from_all_wells",
    "add_production_rate_and_date",
    "add_production_to_well_data",
    "add_relative_wh_positions",
    "calculate_drilling_completion_summary",
    "clean_tubulars_data",
    "convert_survey_to_azimuth_inclination",
    "delete_well_data_for_api10",
    "evaluate_well_distances",
    "get_api10_from_well_api",
    "plot_field_wells",
    "prepare_casing_data",
    "prepare_casing_tubular_summary_all_wells",
    "prepare_completion_data",
    "prepare_field_production",
    "prepare_field_production_rate",
    "prepare_well_paths",
    "process_survey_xyz",
    "save_output_data_to_excel",
    "transform_list_to_unique",
    "tubular_summary_based_on_api12_and_hole",
]
