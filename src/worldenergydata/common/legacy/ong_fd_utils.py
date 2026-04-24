"""Utility functions for ONG Field Development analysis.

This module contains utility functions for GIS transformations, geometry calculations,
and data saving operations.
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd


def get_api10_from_well_api(well_api: Any) -> int | str:
    """Extract API10 from a 12-digit API number.

    Args:
        well_api: The 12-digit API number

    Returns:
        The 10-digit API number as int, or original string if not 12 digits
    """
    well_api_str: str = str(well_api)
    if len(well_api_str) == 12:
        return int(well_api_str[0:10])
    return well_api_str


def add_gis_info_to_df(
    df: pd.DataFrame,
    field_x_ref: float | None = None,
    field_y_ref: float | None = None,
) -> tuple[pd.DataFrame, float, float]:
    """Add GIS coordinate information to a DataFrame.

    Converts latitude/longitude to distance coordinates and adds relative positions.

    Args:
        df: DataFrame with Surface/Bottom Longitude/Latitude columns
        field_x_ref: Optional reference x coordinate
        field_y_ref: Optional reference y coordinate

    Returns:
        Tuple of (modified DataFrame, field_x_ref, field_y_ref)
    """
    from assetutilities.common.data import Transform

    transform = Transform()

    # Add bottom coordinates
    gis_cfg: dict[str, str] = {
        "Longitude": "Bottom Longitude",
        "Latitude": "Bottom Latitude",
        "label": "BOT",
    }
    df = transform.gis_deg_to_distance(df, gis_cfg)

    # Add surface coordinates
    gis_cfg = {
        "Longitude": "Surface Longitude",
        "Latitude": "Surface Latitude",
        "label": "SURF",
    }
    df = transform.gis_deg_to_distance(df, gis_cfg)

    # Calculate reference points if not provided
    if field_x_ref is None:
        field_x_ref = df.SURF_x.min()
    if field_y_ref is None:
        field_y_ref = df.SURF_y.min()

    # Add relative coordinates
    df["BOT_x_rel"] = df["BOT_x"] - field_x_ref
    df["BOT_y_rel"] = df["BOT_y"] - field_y_ref
    df["SURF_x_rel"] = df["SURF_x"] - field_x_ref
    df["SURF_y_rel"] = df["SURF_y"] - field_y_ref

    return df, field_x_ref, field_y_ref


def delete_well_data_for_api10(dbe_output: Any, api10: str) -> None:
    """Delete well data for a specific API10 from the database.

    Args:
        dbe_output: Database engine for output
        api10: The API10 number to delete
    """
    filename: str = os.path.join(
        "data_manager\\sql", "bsee.delete_well_data_for_api10.sql"
    )
    with open(filename, "r") as fd:
        sql_file: str = fd.read()
    dbe_output.executeNoDataQuery(sql_file, [api10])


def save_output_data_to_excel(
    df_array: list[pd.DataFrame],
    label_array: list[str],
    file_name_without_extension: str,
) -> None:
    """Save DataFrames to an Excel file with multiple sheets.

    Args:
        df_array: List of DataFrames to save
        label_array: List of sheet names
        file_name_without_extension: Base filename without extension
    """
    from assetutilities.common.data import SaveData

    save_data = SaveData()
    cfg_temp: dict[str, Any] = {
        "SheetNames": label_array,
        "FileName": file_name_without_extension + ".xlsx",
    }
    save_data.DataFrameArray_To_xlsx_openpyxl(df_array, cfg_temp)


def transform_list_to_unique(old_list: list[str]) -> list[str]:
    """Transform a list to have unique values by adding trailing alphabet.

    Args:
        old_list: List with potential duplicates

    Returns:
        List with unique values
    """
    from assetutilities.common.data import Transform

    trans = Transform()
    cfg_temp: dict[str, Any] = {
        "list": old_list,
        "transform_character": "trailing_alphabet",
    }
    return trans.transform_list_to_unique_list(cfg_temp)
