"""Drilling and completion summary calculations for ONG Field Development analysis.

This module contains functions for calculating drilling and completion
summary statistics and cost estimates.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def calculate_drilling_completion_summary(
    output_data_api12_df: pd.DataFrame,
    output_data_well_df: pd.DataFrame,
    oil_pressure_gradient: float = 0.37,
    over_balance_ppg: float = 0.5,
    rig_day_rate_loaded: int = 1100000,
    sunk_cost_per_completed_well: int = 40000000,
    cost_of_subsea_equipment: int = 200000000,
) -> list[dict[str, Any]]:
    """Calculate drilling and completion summary statistics.

    Args:
        output_data_api12_df: API12 DataFrame
        output_data_well_df: Well DataFrame
        oil_pressure_gradient: Oil pressure gradient in psi/ft
        over_balance_ppg: Over balance in ppg
        rig_day_rate_loaded: Rig day rate in USD
        sunk_cost_per_completed_well: Sunk cost per completed well in USD
        cost_of_subsea_equipment: Cost of subsea equipment in USD

    Returns:
        List of summary dictionaries with Description and Value keys
    """
    output_data_api12_df[output_data_api12_df["Well Purpose"] == "D"].copy()

    total_wellbores: int = (
        len(output_data_well_df) + output_data_well_df["Side Tracks"].sum()
    )

    avg_water_depth: float = round(output_data_well_df["Water Depth"].mean(), 0)

    avg_drilling_footage_ft: float = round(
        pd.to_numeric(
            output_data_well_df["drilling_footage_ft"], errors="coerce"
        ).mean(),
        0,
    )
    avg_drilling_days_per_10000_ft: float = round(
        pd.to_numeric(
            output_data_well_df["drilling_days_per_10000_ft"], errors="coerce"
        ).mean(),
        1,
    )
    avg_tvd_all_wellbores: float = round(
        pd.to_numeric(
            output_data_well_df["Total Vertical Depth"], errors="coerce"
        ).mean(),
        0,
    )
    avg_tmd_all_wellbores: float = round(
        pd.to_numeric(
            output_data_well_df["Total Measured Depth"], errors="coerce"
        ).mean(),
        0,
    )
    total_construction_time_all_wellbores: float = pd.to_numeric(
        output_data_well_df["Drilling Days"], errors="coerce"
    ).sum()
    total_completion_time_all_wellbores: float = pd.to_numeric(
        output_data_well_df["Completion Days"], errors="coerce"
    ).sum()
    total_d_c_time_all_wellbores: float = (
        total_construction_time_all_wellbores + total_completion_time_all_wellbores
    )

    completed_wells_df: pd.DataFrame = output_data_well_df[
        output_data_well_df["Wellbore Status"] == "COM"
    ].copy()
    completed_wellbores: int = len(completed_wells_df)

    avg_construction_time_all_wellbores: float = round(
        avg_drilling_footage_ft / 10000 * avg_drilling_days_per_10000_ft, 1
    )
    total_d_c_estimated_cost: float = (
        total_d_c_time_all_wellbores * rig_day_rate_loaded
        + completed_wellbores * sunk_cost_per_completed_well
    )

    if completed_wellbores > 0:
        avg_mud_weight: float = round(
            pd.to_numeric(
                completed_wells_df["MAX_DRILL_FLUID_WGT"], errors="coerce"
            ).mean(),
            1,
        )
        estimated_reservoir_pressure: float = round(
            (avg_tvd_all_wellbores - 1000)
            * (avg_mud_weight - over_balance_ppg)
            * 0.052,
            0,
        )
        estimated_mudline_pressure: float = round(
            estimated_reservoir_pressure
            - oil_pressure_gradient * (avg_tvd_all_wellbores - avg_water_depth),
            0,
        )
        estimated_dry_tree_tubing_pressure: float = round(
            estimated_mudline_pressure - oil_pressure_gradient * avg_water_depth,
            0,
        )

        avg_d_c_time_completed_wellbores: float = round(
            total_d_c_time_all_wellbores / completed_wellbores, 1
        )
        avg_c_time_completed_wellbores: float = round(
            total_completion_time_all_wellbores / completed_wellbores, 1
        )
        d_c_estimated_cost_per_completion: float = (
            total_d_c_estimated_cost / completed_wellbores
        )
        d_c_estimated_cost_per_subsea_well: float = (
            d_c_estimated_cost_per_completion + cost_of_subsea_equipment
        )
    else:
        estimated_reservoir_pressure = 0
        estimated_mudline_pressure = 0
        estimated_dry_tree_tubing_pressure = 0
        avg_d_c_time_completed_wellbores = 0
        avg_c_time_completed_wellbores = 0
        d_c_estimated_cost_per_completion = 0
        d_c_estimated_cost_per_subsea_well = 0

    total_estimated_cost_for_subsea_wells: float = (
        d_c_estimated_cost_per_subsea_well * completed_wellbores
    )

    drilling_completion_summary: list[dict[str, Any]] = []
    drilling_completion_summary.append(
        {"Description": "Water Depth", "Value": float(avg_water_depth)}
    )
    drilling_completion_summary.append(
        {"Description": "Total Wellbores", "Value": int(total_wellbores)}
    )
    drilling_completion_summary.append(
        {
            "Description": "Avg TVD, All Wellbores",
            "Value": float(avg_tvd_all_wellbores),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Avg TMD, All Wellbores",
            "Value": float(avg_tmd_all_wellbores),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Avg Construction Time, All Wellbores (days)",
            "Value": float(avg_construction_time_all_wellbores),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Completed Wellbores (#)",
            "Value": int(completed_wellbores),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Total D&C Time, Completed Wellbores (days)",
            "Value": float(total_d_c_time_all_wellbores),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Average D&C Time, Completed Wellbores (days)",
            "Value": float(avg_d_c_time_completed_wellbores),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Total Completion Time (days)",
            "Value": float(avg_c_time_completed_wellbores),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Total D&C Estimated Cost (USD)",
            "Value": float(total_d_c_estimated_cost),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Estimated D&C Cost per Completion (USD)",
            "Value": float(d_c_estimated_cost_per_completion),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Estimated Total Subsea Completion per Well (USD)",
            "Value": float(d_c_estimated_cost_per_subsea_well),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Estimated Total Subsea Well Cost (USD)",
            "Value": float(total_estimated_cost_for_subsea_wells),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Estimated Reservoir Pressure (psi)",
            "Value": float(estimated_reservoir_pressure),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Estimated Mudline Pressure (psi)",
            "Value": float(estimated_mudline_pressure),
        }
    )
    drilling_completion_summary.append(
        {
            "Description": "Estimated Dry Tree Tbg Shut-in Pressure (psi)",
            "Value": float(estimated_dry_tree_tubing_pressure),
        }
    )

    return drilling_completion_summary
