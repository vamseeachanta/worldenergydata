"""Legacy module for ONG Field Development components.

This module provides backward-compatible imports for the refactored
ONG Field Development components.
"""

from .ong_fd_components_refactored import ONGFDComponents

# Re-export utility functions for backward compatibility
from .ong_fd_utils import (
    add_gis_info_to_df,
    delete_well_data_for_api10,
    get_api10_from_well_api,
    save_output_data_to_excel,
    transform_list_to_unique,
)

# Re-export production functions
from .ong_fd_production import (
    add_production_from_all_wells,
    add_production_rate_and_date,
    add_production_to_well_data,
    prepare_field_production,
    prepare_field_production_rate,
)

# Re-export drilling functions
from .ong_fd_drilling import (
    assign_st_bp_tree_info,
    get_rig_days_and_drilling_wt,
)

# Re-export summary functions
from .ong_fd_summary import (
    calculate_drilling_completion_summary,
)

# Re-export wellpath functions
from .ong_fd_wellpath import (
    add_relative_wh_positions,
    convert_survey_to_azimuth_inclination,
    plot_field_wells,
    prepare_well_paths,
    process_survey_xyz,
)

# Re-export tubular functions
from .ong_fd_tubulars import (
    clean_tubulars_data,
    prepare_casing_data,
    prepare_casing_tubular_summary_all_wells,
    tubular_summary_based_on_api12_and_hole,
)

# Re-export geometry functions
from .ong_fd_geometry import (
    evaluate_well_distances,
    prepare_completion_data,
)

__all__ = [
    # Main class
    "ONGFDComponents",
    # Utils
    "add_gis_info_to_df",
    "delete_well_data_for_api10",
    "get_api10_from_well_api",
    "save_output_data_to_excel",
    "transform_list_to_unique",
    # Production
    "add_production_from_all_wells",
    "add_production_rate_and_date",
    "add_production_to_well_data",
    "prepare_field_production",
    "prepare_field_production_rate",
    # Drilling
    "assign_st_bp_tree_info",
    "calculate_drilling_completion_summary",
    "get_rig_days_and_drilling_wt",
    # Wellpath
    "add_relative_wh_positions",
    "convert_survey_to_azimuth_inclination",
    "plot_field_wells",
    "prepare_well_paths",
    "process_survey_xyz",
    # Tubulars
    "clean_tubulars_data",
    "prepare_casing_data",
    "prepare_casing_tubular_summary_all_wells",
    "tubular_summary_based_on_api12_and_hole",
    # Geometry
    "evaluate_well_distances",
    "prepare_completion_data",
]
