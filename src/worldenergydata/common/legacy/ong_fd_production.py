"""Production data processing for ONG Field Development analysis.

This module contains functions for processing oil and gas production data,
calculating production rates, and preparing field production summaries.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from common.data import DateTimeUtility

from .ong_fd_utils import get_api10_from_well_api

dtu = DateTimeUtility()


def add_production_rate_and_date(df: pd.DataFrame) -> pd.DataFrame:
    """Add production rate and datetime columns to a production DataFrame.

    Args:
        df: Production DataFrame with PRODUCTION_DATE, MON_O_PROD_VOL, DAYS_ON_PROD

    Returns:
        DataFrame with added PRODUCTION_DATETIME and O_PROD_RATE_BOPD columns
    """
    import datetime

    production_date: list[Any] = []
    production_rate: list[float] = []

    for df_row in range(0, len(df)):
        year: int = int(df.PRODUCTION_DATE.iloc[df_row] / 100)
        month: int = df.PRODUCTION_DATE.iloc[df_row] % year
        date_time: datetime.datetime = datetime.datetime(year, month, 1)
        date_time_last: datetime.date = dtu.last_day_of_month(date_time.date())

        if df.DAYS_ON_PROD.iloc[df_row] != 0:
            rate: float = df.MON_O_PROD_VOL.iloc[df_row] / df.DAYS_ON_PROD.iloc[df_row]
        else:
            rate = 0

        production_date.append(date_time_last)
        production_rate.append(rate)

    df["PRODUCTION_DATETIME"] = production_date
    df["O_PROD_RATE_BOPD"] = production_rate
    return df


def prepare_field_production(
    df_temp: pd.DataFrame,
    df_column_label: str,
    output_data_field_production_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Prepare field production data by merging completion production.

    Args:
        df_temp: Completion production DataFrame
        df_column_label: Column label for this completion
        output_data_field_production_df: Existing field production DataFrame or None

    Returns:
        Updated field production DataFrame
    """
    if output_data_field_production_df is None:
        output_data_field_production_df = pd.DataFrame(columns=["PRODUCTION_DATETIME"])

    field_production_df: pd.DataFrame = pd.DataFrame()
    field_production_df["PRODUCTION_DATETIME"] = df_temp["PRODUCTION_DATETIME"].copy()
    field_production_df[df_column_label] = df_temp["MON_O_PROD_VOL"].copy()

    output_data_field_production_df = pd.merge(
        left=output_data_field_production_df,
        right=field_production_df,
        how="outer",
        left_on="PRODUCTION_DATETIME",
        right_on="PRODUCTION_DATETIME",
    )
    output_data_field_production_df.sort_values(
        by=["PRODUCTION_DATETIME"], inplace=True
    )
    output_data_field_production_df.drop_duplicates(inplace=True)

    return output_data_field_production_df


def prepare_field_production_rate(
    df_temp: pd.DataFrame,
    df_column_label: str,
    output_data_field_production_rate_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Prepare field production rate data by merging completion rates.

    Args:
        df_temp: Completion production rate DataFrame
        df_column_label: Column label for this completion
        output_data_field_production_rate_df: Existing field production rate DataFrame or None

    Returns:
        Updated field production rate DataFrame
    """
    if output_data_field_production_rate_df is None:
        output_data_field_production_rate_df = pd.DataFrame(
            columns=["PRODUCTION_DATETIME"]
        )

    field_production_rate_df: pd.DataFrame = pd.DataFrame()
    field_production_rate_df["PRODUCTION_DATETIME"] = df_temp[
        "PRODUCTION_DATETIME"
    ].copy()
    field_production_rate_df[df_column_label] = df_temp["O_PROD_RATE_BOPD"].copy()

    output_data_field_production_rate_df = pd.merge(
        left=output_data_field_production_rate_df,
        right=field_production_rate_df,
        how="outer",
        left_on="PRODUCTION_DATETIME",
        right_on="PRODUCTION_DATETIME",
    )
    output_data_field_production_rate_df.sort_values(
        by=["PRODUCTION_DATETIME"], inplace=True
    )

    return output_data_field_production_rate_df


def add_production_from_all_wells(
    output_data_field_production_rate_df: pd.DataFrame,
    output_data_field_production_df: pd.DataFrame,
    cfg: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Add total and cumulative production from all wells.

    Args:
        output_data_field_production_rate_df: Field production rate DataFrame
        output_data_field_production_df: Field production DataFrame
        cfg: Configuration dictionary

    Returns:
        Tuple of (updated rate df, updated production df, production summary df)
    """
    # Calculate total daily production rate
    columns: list[str] = output_data_field_production_rate_df.columns.tolist()
    columns.remove("PRODUCTION_DATETIME")
    output_data_field_production_rate_df["TOTAL_DAILY_PRODUCTION_rate_BOPD"] = (
        output_data_field_production_rate_df[columns].sum(axis=1)
    )

    # Calculate monthly and cumulative production
    columns = output_data_field_production_df.columns.tolist()
    columns.remove("PRODUCTION_DATETIME")
    output_data_field_production_df["Total_MONTLY_PRODUCTION_MMbbl"] = (
        output_data_field_production_df[columns].sum(axis=1) / 1000 / 1000
    )
    output_data_field_production_df["CUMULATIVE_MONTLY_PRODUCTION_MMbbl"] = (
        output_data_field_production_df["Total_MONTLY_PRODUCTION_MMbbl"].cumsum()
    )

    # Create production summary DataFrame
    production_summary_df: pd.DataFrame = pd.DataFrame()
    production_summary_df["PRODUCTION_DATETIME"] = output_data_field_production_rate_df[
        "PRODUCTION_DATETIME"
    ]
    production_summary_df["Field NickName"] = cfg["custom_parameters"]["field_nickname"]
    production_summary_df["BOEM_FIELDS"] = cfg["custom_parameters"]["boem_fields"]
    production_summary_df["Production Rate, BOPD"] = (
        output_data_field_production_rate_df["TOTAL_DAILY_PRODUCTION_rate_BOPD"]
    )
    production_summary_df["CUMULATIVE_MONTLY_PRODUCTION_MMbbl"] = (
        output_data_field_production_df["CUMULATIVE_MONTLY_PRODUCTION_MMbbl"]
    )

    return (
        output_data_field_production_rate_df,
        output_data_field_production_df,
        production_summary_df,
    )


def add_production_to_well_data(
    output_data_api12_df: pd.DataFrame,
    well_api10: int | str,
    completion_name: str,
    df_temp: pd.DataFrame,
) -> pd.DataFrame:
    """Add production data and completion name to well data.

    Args:
        output_data_api12_df: API12 DataFrame to update
        well_api10: Well API10 number
        completion_name: Completion name
        df_temp: Production data DataFrame

    Returns:
        Updated API12 DataFrame
    """
    total_well_production: float = df_temp.MON_O_PROD_VOL.sum() / 1000 / 1000
    api12_production: pd.DataFrame = df_temp[
        ["PRODUCTION_DATETIME", "O_PROD_RATE_BOPD"]
    ].copy()
    api12_production.rename(columns={"PRODUCTION_DATETIME": "date_time"}, inplace=True)
    api12_production = api12_production.round(decimals=3)
    api12_production["date_time"] = [
        item.strftime("%Y-%m-%d") for item in api12_production["date_time"].to_list()
    ]

    temp_df: pd.DataFrame = output_data_api12_df[
        (output_data_api12_df.API10 == well_api10)
    ].copy()

    if len(temp_df) > 0 and total_well_production > 0:
        df_row_index: int = temp_df.index[0]

        current_production: float = output_data_api12_df.O_CUMMULATIVE_PROD_MMBBL.iloc[
            df_row_index
        ]
        output_data_api12_df.O_CUMMULATIVE_PROD_MMBBL.iloc[df_row_index] = (
            current_production + total_well_production
        )

        DAYS_ON_PROD: int = df_temp.DAYS_ON_PROD.sum()
        output_data_api12_df.DAYS_ON_PROD.iloc[df_row_index] = DAYS_ON_PROD
        output_data_api12_df.O_MEAN_PROD_RATE_BOPD.iloc[df_row_index] = (
            df_temp.MON_O_PROD_VOL.sum() / DAYS_ON_PROD
        )
        output_data_api12_df.O_PROD_STATUS.iloc[df_row_index] = 1

        current_completion_name: str = output_data_api12_df.COMPLETION_NAME.iloc[
            df_row_index
        ]
        if current_completion_name == "":
            output_data_api12_df.COMPLETION_NAME.iloc[df_row_index] = completion_name
        else:
            completion_name = current_completion_name + "," + completion_name
            output_data_api12_df.COMPLETION_NAME.iloc[df_row_index] = completion_name

        output_data_api12_df["monthly_production"].iloc[df_row_index] = json.dumps(
            api12_production.to_dict(orient="records")
        )

    return output_data_api12_df
