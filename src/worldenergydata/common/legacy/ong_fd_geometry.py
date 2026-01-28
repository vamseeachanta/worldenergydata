"""Geometry and well distance calculations for ONG Field Development analysis.

This module contains functions for calculating well distances,
horizontal departures, and wellhead spatial analysis.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from common.data import AttributeDict


def evaluate_well_distances(
    output_data_api12_df: pd.DataFrame,
    field_summary: AttributeDict,
) -> tuple[pd.DataFrame, AttributeDict, pd.DataFrame | None]:
    """Evaluate well distances and horizontal departures.

    Calculates distances between wellheads and horizontal departures
    for all wells and producing wells.

    Args:
        output_data_api12_df: API12 DataFrame with well coordinates
        field_summary: Field summary AttributeDict

    Returns:
        Tuple of (updated API12 df, updated field_summary, producing wells df or None)
    """
    from common.math_solvers import Geometry

    geom = Geometry()
    output_data_api12_df["HORZ_DEPARTURE"] = 0
    output_data_producing_api12_df: pd.DataFrame | None = None

    if len(output_data_api12_df) > 0:
        well_head_xy_sets: list[list[float]] = []

        for df_row in range(0, len(output_data_api12_df)):
            surface_x_y: list[float] = [
                output_data_api12_df.SURF_x_rel.iloc[df_row],
                output_data_api12_df.SURF_y_rel.iloc[df_row],
            ]
            well_head_xy_sets.append(surface_x_y)

            bottom_x_y: list[float] = [
                output_data_api12_df.BOT_x_rel.iloc[df_row],
                output_data_api12_df.BOT_y_rel.iloc[df_row],
            ]
            spatial_data_sets: list[list[float]] = [surface_x_y, bottom_x_y]
            result: dict[str, Any] = geom.max_distance_for_spatial_sets(
                spatial_data_sets
            )
            output_data_api12_df.HORZ_DEPARTURE.iloc[df_row] = result["distance_max"]

        # Calculate wellhead distances for all wells
        if len(well_head_xy_sets) > 1:
            result = geom.max_distance_for_spatial_sets(well_head_xy_sets)
            field_summary.wellhead_distances.append(
                {
                    "Description": "All Wellheads, Max Distance (ft)",
                    "Value": round(float(result["distance_max"] / 0.3048), 1),
                }
            )
            field_summary.wellhead_distances.append(
                {
                    "Description": "All Wellheads, Min Distance (ft)",
                    "Value": round(float(result["distance_min"] / 0.3048), 1),
                }
            )
        else:
            field_summary.wellhead_distances.append(
                {
                    "Description": "All Wellheads, Max Distance (ft)",
                    "Value": 0,
                    "Description": "All Wellheads, Min Distance (ft)",
                    "Value": 0,
                }
            )

        horizontal_departure: float = round(
            (output_data_api12_df.HORZ_DEPARTURE.max() / 0.3048), 1
        )
        field_summary.wellhead_distances.append(
            {
                "Description": "All Wells, Max Horizontal Departure (ft)",
                "Value": horizontal_departure,
            }
        )

        # Calculate for producing wells
        output_data_producing_api12_df = output_data_api12_df[
            output_data_api12_df.O_PROD_STATUS == 1
        ]

        if len(output_data_producing_api12_df) > 0:
            producing_well_head_xy_sets: list[list[float]] = []

            for df_row in range(0, len(output_data_api12_df)):
                if output_data_api12_df.O_PROD_STATUS.iloc[df_row] == 1:
                    surface_x_y = [
                        output_data_api12_df.SURF_x_rel.iloc[df_row],
                        output_data_api12_df.SURF_y_rel.iloc[df_row],
                    ]
                    producing_well_head_xy_sets.append(surface_x_y)

            if len(producing_well_head_xy_sets) > 1:
                result = geom.max_distance_for_spatial_sets(producing_well_head_xy_sets)
                field_summary.wellhead_distances.append(
                    {
                        "Description": "Producing Wellheads, Max Distance (ft)",
                        "Value": round(float(result["distance_max"] / 0.3048), 1),
                    }
                )
                field_summary.wellhead_distances.append(
                    {
                        "Description": "Producing Wellheads, Min Distance (ft)",
                        "Value": round(float(result["distance_min"] / 0.3048), 1),
                    }
                )
            else:
                field_summary.wellhead_distances.append(
                    {
                        "Description": "Producing Wellheads, Max Distance (ft)",
                        "Value": 0,
                        "Description": "Producing Wellheads, Min Distance (ft)",
                        "Value": 0,
                    }
                )

            horizontal_departure = round(
                (
                    output_data_api12_df[
                        output_data_api12_df.O_PROD_STATUS == 1
                    ].HORZ_DEPARTURE.max()
                    / 0.3048
                ),
                1,
            )
            field_summary.wellhead_distances.append(
                {
                    "Description": "Producing Wellheads, Max Horizontal Departure (ft)",
                    "Value": horizontal_departure,
                }
            )

    return output_data_api12_df, field_summary, output_data_producing_api12_df


def prepare_completion_data(
    completion_data: pd.DataFrame,
    field_x_ref: float,
    field_y_ref: float,
    cfg: dict[str, Any],
) -> pd.DataFrame:
    """Prepare completion data with GIS coordinates.

    Args:
        completion_data: Completion data DataFrame
        field_x_ref: Field x reference coordinate
        field_y_ref: Field y reference coordinate
        cfg: Configuration dictionary

    Returns:
        Output completions DataFrame with GIS coordinates
    """
    from common.data import Transform

    transform = Transform()

    output_completions: pd.DataFrame = completion_data.merge(
        completion_data, how="outer", left_on="API12", right_on="API12"
    )

    gis_cfg: dict[str, str] = {
        "Longitude": "COMP_LONGITUDE",
        "Latitude": "COMP_LATITUDE",
        "label": "COMP",
    }
    output_completions = transform.gis_deg_to_distance(output_completions, gis_cfg)

    output_completions["COMP_x_rel"] = output_completions["COMP_x"] - field_x_ref
    output_completions["COMP_y_rel"] = output_completions["COMP_y"] - field_y_ref
    output_completions["Field NickName"] = cfg["custom_parameters"]["field_nickname"]

    return output_completions
