"""Well path and survey processing for ONG Field Development analysis.

This module contains functions for processing directional surveys,
calculating well paths, and plotting 3D well trajectories.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from .ong_fd_utils import get_api10_from_well_api


def process_survey_xyz(survey: pd.DataFrame) -> pd.DataFrame:
    """Process survey data to calculate XYZ coordinates.

    Uses minimum curvature method to calculate well path coordinates
    from inclination and azimuth measurements.

    Args:
        survey: Survey DataFrame with md, inc, az columns

    Returns:
        DataFrame with added x_coor, y_coor, z_coor, dz, dls columns
    """
    survey_xyz: pd.DataFrame = survey[["md", "inc", "az"]]
    survey_xyz = survey_xyz.sort_values(by=["md"])
    survey_xyz = survey_xyz.reset_index(drop=True)
    survey_xyz = survey_xyz.drop_duplicates(subset=["md"], keep="first")

    survey_xyz.loc[:, "inc_diff"] = survey_xyz["inc"].diff()
    survey_xyz.loc[:, "md_diff"] = survey_xyz["md"].diff()
    survey_xyz.loc[:, "az_diff"] = survey_xyz["az"].diff()
    survey_xyz = survey_xyz.fillna(0)

    # Handle azimuth wrap-around
    for i in range(0, np.shape(survey_xyz)[0]):
        if survey_xyz["az_diff"].iloc[i] > 180:
            survey_xyz.loc[i, "az_diff"] = survey_xyz.loc[i, "az_diff"] - 360
        elif survey_xyz["az_diff"].iloc[i] < -180:
            survey_xyz.loc[i, "az_diff"] = survey_xyz.loc[i, "az_diff"] + 360

    survey_xyz.loc[:, "inc_ave"] = survey_xyz["inc"].rolling(window=2).mean()
    survey_xyz.loc[:, "build_rate"] = survey_xyz["inc_diff"] / survey_xyz["md_diff"]
    survey_xyz.loc[:, "turn_rate"] = survey_xyz["az_diff"] / survey_xyz["md_diff"]

    md_diff: Any = np.array(survey_xyz["md_diff"][1:])
    build_rate: Any = np.array(survey_xyz["build_rate"])
    turn_rate: Any = np.array(survey_xyz["turn_rate"])

    inc_ave: Any = np.array(survey_xyz["inc_ave"]) * np.pi / 180
    inc_start: Any = np.array(survey_xyz["inc"][:-1]) * np.pi / 180
    inc_end: Any = np.array(survey_xyz["inc"][1:]) * np.pi / 180
    az_start: Any = np.array(survey_xyz["az"][:-1]) * np.pi / 180
    az_end: Any = np.array(survey_xyz["az"][1:]) * np.pi / 180

    x_coor: Any = np.array(np.zeros([np.shape(survey_xyz)[0], 1]))
    y_coor: Any = np.array(np.zeros([np.shape(survey_xyz)[0], 1]))
    z_coor: Any = np.array(np.zeros([np.shape(survey_xyz)[0], 1]))

    # Calculate dogleg and ratio factor
    dog_leg_sq: Any = (
        np.sin((inc_end - inc_start) / 2) ** 2
        + np.sin(inc_start) * np.sin(inc_end) * np.sin((az_end - az_start) / 2) ** 2
    )
    dog_leg: Any = 2 * np.arcsin(np.sqrt(dog_leg_sq))
    dog_leg[dog_leg < 10**-6] = 10**-6
    rf: Any = md_diff / dog_leg * np.tan(dog_leg / 2)

    # Calculate coordinate deltas
    delta_x: Any = (
        np.sin(inc_start) * np.cos(az_start) + np.sin(inc_end) * np.cos(az_end)
    ) * rf
    delta_y: Any = (
        np.sin(inc_start) * np.sin(az_start) + np.sin(inc_end) * np.sin(az_end)
    ) * rf
    delta_z: Any = (np.cos(inc_start) + np.cos(inc_end)) * rf

    # Calculate cumulative coordinates
    x_coor[1:, 0] = np.cumsum(delta_x)
    y_coor[1:, 0] = np.cumsum(delta_y)
    z_coor[1:, 0] = np.cumsum(delta_z)
    dz: Any = np.diff(z_coor, axis=0)
    dz = np.insert(dz, 0, 0, axis=0)

    # Calculate dogleg severity
    dls: Any = np.sqrt(build_rate**2 + (np.sin(inc_ave)) ** 2 * turn_rate**2)
    dls = dls.reshape(dls.shape[0], 1)

    xyz_table: pd.DataFrame = pd.DataFrame(
        np.hstack((x_coor, y_coor, z_coor, dz, dls)),
        columns=["x_coor", "y_coor", "z_coor", "dz", "dls"],
    )
    survey_xyz = pd.concat([survey_xyz, xyz_table], axis=1)
    survey_xyz.fillna(0, inplace=True)

    return survey_xyz


def add_relative_wh_positions(
    api12: Any,
    survey_xyz: pd.DataFrame,
    output_data_api12_df: pd.DataFrame,
) -> pd.DataFrame:
    """Add wellhead-relative positions to survey coordinates.

    Args:
        api12: Well API12 number
        survey_xyz: Survey DataFrame with x_coor, y_coor columns
        output_data_api12_df: API12 DataFrame with surface coordinates

    Returns:
        Survey DataFrame with adjusted coordinates
    """
    api12_df: pd.DataFrame = output_data_api12_df[
        output_data_api12_df.API12 == api12
    ].copy()

    survey_xyz_wh_adjusted: pd.DataFrame = survey_xyz.copy()
    survey_xyz_wh_adjusted["x_coor"] = (
        survey_xyz_wh_adjusted["x_coor"] + api12_df.SURF_x_rel.iloc[0]
    )
    survey_xyz_wh_adjusted["y_coor"] = (
        survey_xyz_wh_adjusted["y_coor"] + api12_df.SURF_y_rel.iloc[0]
    )

    return survey_xyz_wh_adjusted


def convert_survey_to_azimuth_inclination(
    api12_dir_survey_df: pd.DataFrame,
) -> pd.DataFrame:
    """Convert BSEE survey format to azimuth and inclination.

    Converts quadrant-based azimuth to compass azimuth.

    Args:
        api12_dir_survey_df: Directional survey DataFrame in BSEE format

    Returns:
        DataFrame with added az, inc, md columns
    """
    api12_dir_survey_df["az"] = 0
    api12_dir_survey_df["inc"] = 0
    api12_dir_survey_df["md"] = api12_dir_survey_df["SURVEY_POINT_MD"]

    for df_row in range(0, len(api12_dir_survey_df)):
        WELL_N_S_CODE: str = api12_dir_survey_df.iloc[df_row]["WELL_N_S_CODE"]
        WELL_E_W_CODE: str = api12_dir_survey_df.iloc[df_row]["WELL_E_W_CODE"]
        Azimuth_quadrant_angle: float = (
            api12_dir_survey_df.iloc[df_row]["DIR_DEG_VAL"]
            + api12_dir_survey_df.iloc[df_row]["DIR_MINS_VAL"] / 60
        )
        Inclination: float = (
            api12_dir_survey_df.iloc[df_row]["INCL_ANG_DEG_VAL"]
            + api12_dir_survey_df.iloc[df_row]["INCL_ANG_MIN_VAL"] / 60
        )

        if WELL_N_S_CODE == "N":
            if WELL_E_W_CODE == "E":
                Azimuth: float = Azimuth_quadrant_angle
            else:
                Azimuth = 360 - Azimuth_quadrant_angle
        else:
            if WELL_E_W_CODE == "E":
                Azimuth = 180 - Azimuth_quadrant_angle
            else:
                Azimuth = 180 + Azimuth_quadrant_angle

        api12_dir_survey_df["az"].iloc[df_row] = Azimuth
        api12_dir_survey_df["inc"].iloc[df_row] = Inclination

    return api12_dir_survey_df


def prepare_well_paths(
    directional_surveys: pd.DataFrame,
    output_data_api12_df: pd.DataFrame,
    output_data_well_df: pd.DataFrame,
) -> tuple[dict[Any, pd.DataFrame], pd.DataFrame]:
    """Prepare well paths from directional surveys.

    Args:
        directional_surveys: Directional survey DataFrame
        output_data_api12_df: API12 DataFrame
        output_data_well_df: Well DataFrame

    Returns:
        Tuple of (well path dictionary, updated API12 DataFrame)
    """
    output_data_well_path: dict[Any, pd.DataFrame] = {}
    API12_list: list[Any] = list(directional_surveys.API12.unique())
    count: int = 0

    for api12 in API12_list:
        count = count + 1
        api12_dir_survey_df: pd.DataFrame = directional_surveys[
            directional_surveys.API12 == api12
        ].copy()

        # Convert to azimuth/inclination format
        api12_dir_survey_df = convert_survey_to_azimuth_inclination(api12_dir_survey_df)

        print("Processing Survey for api12 {} of {}".format(count, len(API12_list)))

        # Process survey to XYZ
        survey_xyz: pd.DataFrame = process_survey_xyz(api12_dir_survey_df)
        survey_xyz_wh_adjusted: pd.DataFrame = add_relative_wh_positions(
            api12, survey_xyz, output_data_api12_df
        )
        output_data_well_path.update({api12: survey_xyz_wh_adjusted})

        # Prepare survey for database storage
        survey_for_db: pd.DataFrame = pd.DataFrame()
        survey_for_db["x"] = survey_xyz_wh_adjusted["x_coor"]
        survey_for_db["y"] = survey_xyz_wh_adjusted["y_coor"]
        survey_for_db["z"] = survey_xyz_wh_adjusted["z_coor"]
        survey_for_db = survey_for_db.round(decimals=1)

        try:
            api10_value: int | str = get_api10_from_well_api(api12)
            label: str = (
                output_data_well_df[output_data_well_df.API10 == api10_value][
                    "Well Name"
                ].values[0]
                + "-"
                + output_data_well_df[output_data_well_df.API10 == api10_value][
                    "Sidetrack and Bypass"
                ].values[0]
            )
            label = label.strip()
        except Exception:
            label = str(api12)

        output_well_path_for_db: dict[str, Any] = {
            "data": survey_for_db.to_dict(orient="records"),
            "label": label,
        }

        temp_df: pd.DataFrame = output_data_api12_df[
            (output_data_api12_df.API12 == api12)
        ].copy()

        if len(temp_df) > 0 and len(survey_for_db) > 0:
            df_row_index: int = temp_df.index[0]
            output_data_api12_df["xyz"].iloc[df_row_index] = json.dumps(
                output_well_path_for_db
            )

    return output_data_well_path, output_data_api12_df


def plot_field_wells(
    output_data_well_path: dict[Any, pd.DataFrame],
    output_data_well_df: pd.DataFrame,
    cfg: dict[str, Any],
) -> None:
    """Plot 3D well paths for a field.

    Args:
        output_data_well_path: Dictionary of well path DataFrames
        output_data_well_df: Well DataFrame
        cfg: Configuration dictionary
    """
    if not output_data_well_path:
        return

    import math

    import matplotlib.pyplot as plt

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    api12_list: list[Any] = list(output_data_well_path.keys())
    labels_plotted: list[str] = []

    for api12 in api12_list:
        api10: int | str = get_api10_from_well_api(api12)
        custom_list: list[int] = []

        if api10 not in custom_list:
            survey_xyz: pd.DataFrame = output_data_well_path[api12]
            x: Any = survey_xyz["x_coor"]
            y: Any = survey_xyz["y_coor"]
            z: Any = survey_xyz["z_coor"]

            try:
                api10_value: int | str = get_api10_from_well_api(api12)
                label: str = (
                    output_data_well_df[output_data_well_df.API10 == api10_value][
                        "Well Name"
                    ].values[0]
                    + "-"
                    + output_data_well_df[output_data_well_df.API10 == api10_value][
                        "Sidetrack and Bypass"
                    ].values[0]
                )
                label = label.strip()
            except Exception:
                label = str(api12)

            if label not in labels_plotted:
                labels_plotted.append(label)
                ax.plot3D(x, y, z, label=label, linewidth=1)
                ax.xaxis.set_tick_params(labelsize=7)
                ax.yaxis.set_tick_params(labelsize=7)
                ax.zaxis.set_tick_params(labelsize=7)
                ax.set_xlabel("Easting (ft)", fontsize=8)
                ax.set_ylabel("Northing (ft)", fontsize=8)
                ax.set_zlabel("TVD (ft)", fontsize=8)

    ax.invert_zaxis()

    # Make XY axes equal
    xy_equal_flag: bool = True
    if xy_equal_flag:
        ylim_old: tuple[float, float] = ax.get_ylim()
        xlim_old: tuple[float, float] = ax.get_xlim()
        ylim_new: list[float] = []
        xlim_new: list[float] = []
        yrange: float = ylim_old[1] - ylim_old[0]
        xrange: float = xlim_old[1] - xlim_old[0]

        if yrange > xrange:
            range_val: float = round(yrange / 1000) * 1000
            ylim_new.append(math.floor(ylim_old[0] / 1000) * 1000)
            ylim_new.append(math.ceil(ylim_old[1] / 1000) * 1000)
            range_val = ylim_new[1] - ylim_new[0]
            xlim_new.append(math.floor(xlim_old[0] / 1000) * 1000)
            xlim_new.append(range_val + xlim_new[0])
        else:
            xlim_new.append(math.floor(xlim_old[0] / 1000) * 1000)
            xlim_new.append(math.ceil(xlim_old[1] / 1000) * 1000)
            range_val = xlim_new[1] - xlim_new[0]
            ylim_new.append(math.floor(ylim_old[0] / 1000) * 1000)
            ylim_new.append(range_val + ylim_new[0])

        ax.set_xlim(xlim_new)
        ax.set_ylim(xlim_new)

    ax.legend(
        bbox_to_anchor=(1, 0),
        loc="lower right",
        bbox_transform=fig.transFigure,
        ncol=5,
        fontsize=6,
    )
    fig.savefig(
        cfg["Analysis"]["result_folder"]
        + cfg["Analysis"]["file_name_for_overwrite"]
        + "_well_paths.png",
        bbox_inches="tight",
        dpi=800,
    )
    plt.close()
