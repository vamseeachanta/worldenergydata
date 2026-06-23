"""Casing and tubular data processing for ONG Field Development analysis.

This module contains functions for processing casing tubular data,
cleaning duplicate entries, and preparing tubular summaries.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd


def clean_tubulars_data(
    latest_tubulars_df_with_duplicates: pd.DataFrame,
) -> pd.DataFrame:
    """Clean duplicate entries from tubulars data.

    Removes duplicate tubular entries based on hole size and setting depths.

    Args:
        latest_tubulars_df_with_duplicates: DataFrame with potential duplicates

    Returns:
        Cleaned DataFrame without duplicates
    """
    casing_hole_size_array: list[Any] = list(
        latest_tubulars_df_with_duplicates.CSNG_HOLE_SIZE.unique()
    )
    drop_index_array: list[Any] = []

    for casing_hole_size in casing_hole_size_array:
        temp_df: pd.DataFrame = latest_tubulars_df_with_duplicates[
            (latest_tubulars_df_with_duplicates.CSNG_HOLE_SIZE == casing_hole_size)
        ].copy()

        if len(temp_df) > 1:
            casing_setting_top_md_array: Any = temp_df.CSNG_SETTING_TOP_MD.unique()
            casing_setting_bottom_md_array: Any = temp_df.CSNG_SETTING_BOTM_MD.unique()

            if len(casing_setting_top_md_array) == 1:
                drop_index_array = drop_index_array + list(temp_df.index)[0:-1]
            else:
                for casing_setting_bottom_md in casing_setting_bottom_md_array:
                    temp_df_1: pd.DataFrame = temp_df[
                        temp_df.CSNG_SETTING_BOTM_MD == casing_setting_bottom_md
                    ].copy()

                    if len(temp_df_1) > 1:
                        CSNG_LINER_TEST_PRSS_unique_count: int = len(
                            list(temp_df_1.CSNG_LINER_TEST_PRSS.unique())
                        )
                        CSNG_SHOE_TEST_PRSS_unique_count: int = len(
                            list(temp_df_1.CSNG_SHOE_TEST_PRSS.unique())
                        )
                        CSNG_CEMENT_VOL_unique_count: int = len(
                            list(temp_df_1.CSNG_CEMENT_VOL.unique())
                        )

                        if (
                            max(
                                CSNG_LINER_TEST_PRSS_unique_count,
                                CSNG_SHOE_TEST_PRSS_unique_count,
                                CSNG_CEMENT_VOL_unique_count,
                            )
                            == 1
                        ):
                            drop_index_array = (
                                drop_index_array + list(temp_df_1.index)[1:]
                            )

    latest_tubulars_df: pd.DataFrame = latest_tubulars_df_with_duplicates.copy()
    latest_tubulars_df.drop(drop_index_array, inplace=True)
    latest_tubulars_df.reset_index(inplace=True, drop=True)
    return latest_tubulars_df


def prepare_casing_data(
    well_data: pd.DataFrame,
    well_tubulars_data: pd.DataFrame,
    output_data_api12_df: pd.DataFrame,
    cfg: dict[str, Any],
) -> pd.DataFrame:
    """Prepare casing data from well tubulars.

    Args:
        well_data: Well data DataFrame
        well_tubulars_data: Well tubulars DataFrame
        output_data_api12_df: API12 DataFrame
        cfg: Configuration dictionary

    Returns:
        Casing tubulars DataFrame
    """
    casing_tubulars: pd.DataFrame = pd.DataFrame()

    if len(well_tubulars_data) > 0:
        well_tubulars_data.WAR_START_DT = pd.to_datetime(
            well_tubulars_data.WAR_START_DT
        )
        well_tubulars_data.sort_values(
            by=[
                "API12",
                "WAR_START_DT",
                "CSNG_HOLE_SIZE",
                "CASING_SIZE",
                "CSNG_SETTING_BOTM_MD",
            ],
            inplace=True,
        )

        for df_row in range(0, len(output_data_api12_df)):
            well_api12: Any = output_data_api12_df.API12.iloc[df_row]
            temp_df: pd.DataFrame = well_tubulars_data[
                (well_tubulars_data.API12 == well_api12)
            ].copy()
            max_date: Any = temp_df.WAR_START_DT.max()
            latest_tubulars_df_with_duplicates: pd.DataFrame = temp_df[
                temp_df.WAR_START_DT == max_date
            ].copy()
            latest_tubulars_df_with_duplicates.reset_index(inplace=True, drop=True)
            latest_tubulars_df: pd.DataFrame = clean_tubulars_data(
                latest_tubulars_df_with_duplicates
            )
            casing_tubulars = pd.concat(
                [casing_tubulars, latest_tubulars_df], ignore_index=True
            )

        casing_tubulars["Field NickName"] = cfg["custom_parameters"]["field_nickname"]
        logging.info("Tubing data is prepared")
    else:
        logging.info("Tubing data is not available")

    return casing_tubulars


def tubular_summary_based_on_api12_and_hole(
    casing_tubulars: pd.DataFrame,
    API12_list: list[Any],
    casing_hole_sizes: list[Any],
    well_type: str,
    cfg: dict[str, Any],
    tubular_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Create tubular summary based on API12 and hole size.

    Args:
        casing_tubulars: Casing tubulars DataFrame
        API12_list: List of API12 numbers
        casing_hole_sizes: List of casing hole sizes
        well_type: Well type string (ALL, PRODUCERS)
        cfg: Configuration dictionary
        tubular_summary: Existing tubular summary DataFrame

    Returns:
        Updated tubular summary DataFrame
    """
    index: list[str] = [
        "Well Name",
        "Top MD",
        "Bottom MD",
        "Casing Size",
        "Casing Grade",
        "Casing Wt",
        "Tubular Test Presssure",
        "Shoe Test Pressure",
        "Cement Vol",
    ]

    hole_tubular_summary: pd.DataFrame = pd.DataFrame(columns=API12_list, index=index)

    for casing_index in range(0, len(casing_hole_sizes)):
        casing_hole: Any = casing_hole_sizes[casing_index]
        df_tubular_select_hole: pd.DataFrame = casing_tubulars[
            casing_tubulars.CSNG_HOLE_SIZE == casing_hole
        ]

        for api12_index in range(0, len(API12_list)):
            api12: Any = API12_list[api12_index]
            df_tubular_select_hole_api12: pd.DataFrame = df_tubular_select_hole[
                df_tubular_select_hole.API12 == api12
            ].copy()

            if len(df_tubular_select_hole_api12) > 0:
                well_name: str = df_tubular_select_hole_api12.iloc[0].WELL_NAME
                Top_MD: float = df_tubular_select_hole_api12.iloc[0].CSNG_SETTING_TOP_MD
                Bottom_MD: float = df_tubular_select_hole_api12.iloc[
                    0
                ].CSNG_SETTING_BOTM_MD
                Casing_Size: float = df_tubular_select_hole_api12.iloc[0].CASING_SIZE
                Casing_Grade: str = df_tubular_select_hole_api12.iloc[0].CASING_GRADE
                Casing_Wt: float = df_tubular_select_hole_api12.iloc[0].CASING_WEIGHT
                Tubular_Test_Presssure: float = df_tubular_select_hole_api12.iloc[
                    0
                ].CSNG_LINER_TEST_PRSS
                Shoe_Test_Pressure: float = df_tubular_select_hole_api12.iloc[
                    0
                ].CSNG_SHOE_TEST_PRSS
                Cement_Vol: float = df_tubular_select_hole_api12.iloc[0].CSNG_CEMENT_VOL

                data_array: list[Any] = [
                    well_name,
                    Top_MD,
                    Bottom_MD,
                    Casing_Size,
                    Casing_Grade,
                    Casing_Wt,
                    Tubular_Test_Presssure,
                    Shoe_Test_Pressure,
                    Cement_Vol,
                ]
                hole_tubular_summary[api12] = data_array

        hole_tubular_summary_json: str = hole_tubular_summary.to_json()
        tubular_summary.loc[len(tubular_summary)] = [
            cfg["custom_parameters"]["field_nickname"],
            casing_hole,
            hole_tubular_summary_json,
            well_type,
        ]

    return tubular_summary


def prepare_casing_tubular_summary_all_wells(
    well_data: pd.DataFrame,
    casing_tubulars: pd.DataFrame,
    output_data_api12_df: pd.DataFrame,
    cfg: dict[str, Any],
) -> pd.DataFrame:
    """Prepare casing tubular summary for all wells.

    Args:
        well_data: Well data DataFrame
        casing_tubulars: Casing tubulars DataFrame
        output_data_api12_df: API12 DataFrame
        cfg: Configuration dictionary

    Returns:
        Tubular summary DataFrame
    """
    tubular_summary: pd.DataFrame = pd.DataFrame(
        columns=["Field NickName", "Hole Size", "data", "Well_Type"]
    )

    # Process all wells
    API12_list: list[Any] = list(
        well_data.sort_values(by=["Well Name", "API12"])["API12"]
    )
    casing_hole_sizes: list[Any] = casing_tubulars.CSNG_HOLE_SIZE.unique().tolist()
    casing_hole_sizes = sorted(casing_hole_sizes, reverse=True)
    tubular_summary = tubular_summary_based_on_api12_and_hole(
        casing_tubulars, API12_list, casing_hole_sizes, "ALL", cfg, tubular_summary
    )
    logging.info("Tubular data Summary is prepared for all wells")

    # Process producing wells
    API12_list = list(
        output_data_api12_df[output_data_api12_df.O_PROD_STATUS == 1].API12
    )
    casing_hole_sizes = (
        casing_tubulars[casing_tubulars.API12.isin(API12_list)]
        .CSNG_HOLE_SIZE.unique()
        .tolist()
    )
    casing_hole_sizes = sorted(casing_hole_sizes, reverse=True)
    tubular_summary = tubular_summary_based_on_api12_and_hole(
        casing_tubulars,
        API12_list,
        casing_hole_sizes,
        "PRODUCERS",
        cfg,
        tubular_summary,
    )
    logging.info("Tubular data Summary is prepared for producing wells")

    return tubular_summary
