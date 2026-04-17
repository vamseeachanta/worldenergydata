"""Drilling and rig days calculations for ONG Field Development analysis.

This module contains functions for calculating drilling days, rig time,
and sidetrack/bypass information.

For drilling completion summaries, see ong_fd_summary.py.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

# Re-export for backward compatibility
from .ong_fd_summary import calculate_drilling_completion_summary
from .ong_fd_utils import get_api10_from_well_api

__all__ = [
    "get_rig_days_and_drilling_wt",
    "assign_st_bp_tree_info",
    "calculate_drilling_completion_summary",
]


def get_rig_days_and_drilling_wt(
    WAR_summary: pd.DataFrame,
    well_api12: Any,
    output_data_api12_df: pd.DataFrame,
    max_allowed_npt: int = 90,
) -> tuple[str, float, dict[str, Any]]:
    """Calculate rig days and drilling weight for a well.

    Args:
        WAR_summary: Well Activity Report summary DataFrame
        well_api12: Well API12 number
        output_data_api12_df: API12 DataFrame with well info
        max_allowed_npt: Maximum allowed non-productive time in days

    Returns:
        Tuple of (rig string, max drilling fluid weight, well days dict)
    """
    from dateutil.parser import parse

    well_war: pd.DataFrame = WAR_summary[WAR_summary.API12 == well_api12].copy()
    well_info_df: pd.DataFrame = output_data_api12_df[
        output_data_api12_df.API12 == well_api12
    ].copy()
    spud_date: Any = well_info_df["Spud Date"].iloc[0]
    td_date: Any = well_info_df["Total Depth Date"].iloc[0]

    well_war["Rig_days"] = 0
    well_war["npt_raw"] = 0
    well_war["npt"] = 0

    war_drilling_days_flag: bool = False
    for df_row in range(0, len(well_war)):
        war_days: int = (
            parse(well_war["WAR_END_DT"].iloc[df_row])
            - parse(well_war["WAR_START_DT"].iloc[df_row])
        ).days
        if war_days > 0:
            well_war["Rig_days"].iloc[df_row] = war_days + 1
        else:
            well_war["Rig_days"].iloc[df_row] = war_days

        if df_row > 0:
            start_date: Any = parse(well_war["WAR_START_DT"].iloc[df_row])
            end_date: Any = parse(well_war["WAR_END_DT"].iloc[df_row - 1])
            npt_raw: int = (start_date - end_date).days - 1

            if npt_raw <= max_allowed_npt:
                if npt_raw > 0:
                    well_war["npt_raw"].iloc[df_row] = npt_raw
            elif td_date > start_date:
                war_drilling_days_flag = True

            if (end_date <= td_date) and (start_date > td_date):
                end_date = td_date
            npt: int = (start_date - end_date).days - 1
            if (start_date > td_date) and (npt <= max_allowed_npt):
                if npt > 0:
                    well_war["npt"].iloc[df_row] = npt

    rigs: list[str | None] = list(well_war.RIG_NAME.unique())

    rigdays_list: list[int] = []
    rigdays_dict: list[dict[str, Any]] = []
    rigdays_str_array: list[str] = []
    total_rigdays: int = 0

    for rig in rigs:
        rig_days: int = well_war[well_war.RIG_NAME == rig].Rig_days.sum()
        rigdays_list.append(rig_days)
        total_rigdays = total_rigdays + rig_days
        if rig_days > 0:
            rigdays_dict.append({"rig": rig, "days": int(rig_days)})
            if rig is not None:
                rigdays_str_array.append(rig + " (" + str(rig_days) + ")")
            else:
                rigdays_str_array.append("unknown rig" + " (" + str(rig_days) + ")")

    rigs_for_string: list[str] = [
        rig if rig is not None else "unknown rig" for rig in rigs
    ]
    rig_str: str = ", ".join(rigs_for_string)

    api12_war_days: pd.DataFrame = (
        well_war.groupby(["API12", "BOREHOLE_STAT_DESC"])["Rig_days"]
        .sum()
        .reset_index()
    )

    well_war_npt_days: int = well_war["npt"].sum()

    # Calculate completion days
    try:
        completion_days: int = api12_war_days[
            api12_war_days["BOREHOLE_STAT_DESC"] == "BOREHOLE COMPLETED"
        ].Rig_days.sum()
        npt_days: int = well_war[
            (well_war["BOREHOLE_STAT_DESC"] == "BOREHOLE COMPLETED")
        ].npt.sum()
        completion_days = completion_days + npt_days
    except Exception:
        completion_days = 0

    # Calculate sidetrack days
    try:
        sidetrack_days: int = api12_war_days[
            (api12_war_days["BOREHOLE_STAT_DESC"] == "BOREHOLE SIDETRACKED")
        ].Rig_days.sum()
        npt_days = well_war[
            (well_war["BOREHOLE_STAT_DESC"] == "BOREHOLE SIDETRACKED")
        ].npt.sum()
        sidetrack_days = sidetrack_days + npt_days
    except Exception:
        sidetrack_days = 0

    # Calculate abandon days
    try:
        abandon_days: int = api12_war_days[
            (api12_war_days["BOREHOLE_STAT_DESC"] == "PERMANENTLY ABANDONED")
            | (api12_war_days["BOREHOLE_STAT_DESC"] == "TEMPORARILY ABANDONED")
        ].Rig_days.sum()
        npt_days = well_war[
            (well_war["BOREHOLE_STAT_DESC"] == "PERMANENTLY ABANDONED")
            | (well_war["BOREHOLE_STAT_DESC"] == "TEMPORARILY ABANDONED")
        ].npt.sum()
        abandon_days = abandon_days + npt_days
    except Exception:
        abandon_days = 0

    # Calculate drilling days
    try:
        war_drilling_days: int = api12_war_days[
            (api12_war_days["BOREHOLE_STAT_DESC"] == "DRILLING ACTIVE")
            | (api12_war_days["BOREHOLE_STAT_DESC"] == "DRILLING SUSPENDED")
        ].Rig_days.sum()
        spud_to_td_days: int = (td_date - spud_date).days + 1
        npt_days = well_war[
            (well_war["BOREHOLE_STAT_DESC"] == "DRILLING ACTIVE")
            | (well_war["BOREHOLE_STAT_DESC"] == "DRILLING SUSPENDED")
        ].npt.sum()
        if war_drilling_days_flag:
            spud_to_td_days = war_drilling_days
            npt_days = well_war[
                (well_war["BOREHOLE_STAT_DESC"] == "DRILLING ACTIVE")
                | (well_war["BOREHOLE_STAT_DESC"] == "DRILLING SUSPENDED")
            ].npt_raw.sum()
        drilling_days: int = spud_to_td_days + abandon_days + sidetrack_days + npt_days
    except Exception:
        drilling_days = 0

    well_days_dict: dict[str, Any] = {
        "drilling_days": drilling_days,
        "abandon_days": abandon_days,
        "completion_days": completion_days,
        "well_war_npt_days": well_war_npt_days,
        "rigdays_dict": rigdays_dict,
        "total_rigdays": total_rigdays,
    }

    MAX_DRILL_FLUID_WGT: float = well_war.DRILL_FLUID_WGT.max()

    return rig_str, MAX_DRILL_FLUID_WGT, well_days_dict


def assign_st_bp_tree_info(
    ST_BP_and_tree_height: pd.DataFrame, well_api12: Any
) -> tuple[float, float, float | None]:
    """Assign sidetrack, bypass, and tree height information.

    Args:
        ST_BP_and_tree_height: DataFrame with ST/BP and tree height data
        well_api12: Well API12 number

    Returns:
        Tuple of (sidetrack_no, bypass_no, tree_elevation_aml)
    """
    sidetrack_no: float = 0
    bypass_no: float = 0
    tree_elevation_aml: float | None = None

    bp_st_tree_info: pd.DataFrame = ST_BP_and_tree_height[
        ST_BP_and_tree_height.API12 == well_api12
    ].copy()

    if len(bp_st_tree_info) > 0:
        bp_st_tree_info.sort_values(by=["SN_EOR"])
        sidetrack_no = float(bp_st_tree_info.WELL_NM_ST_SFIX.iloc[0])
        bypass_no = float(bp_st_tree_info.WELL_NM_BP_SFIX.iloc[0])
        tree_elevation_aml = bp_st_tree_info.SUBSEA_TREE_HEIGHT_AML.iloc[0]
        if tree_elevation_aml is not None:
            tree_elevation_aml = float(tree_elevation_aml)

    return sidetrack_no, bypass_no, tree_elevation_aml
