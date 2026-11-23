# Standard library imports
import datetime

# Third party imports
import pandas as pd
from loguru import logger

from worldenergydata.common.legacy.data import DateTimeUtility

dtu = DateTimeUtility()


class API12SummaryBuilder:
    """Builds summary DataFrames for API12 production data."""

    def get_summary_df_api12(
        self, well_api12: str, completion_name: str, api12_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create a summary DataFrame for a single API12 well.

        Args:
            well_api12: The 12-digit API well identifier
            completion_name: Name of the well completion
            api12_df: DataFrame containing production data for the API12

        Returns:
            Summary DataFrame with production metrics
        """
        columns = [
            "API12",
            "API10",
            "O_PROD_STATUS",
            "O_CUMMULATIVE_PROD_MMBBL",
            "DAYS_ON_PROD",
            "O_MEAN_PROD_RATE_BOPD",
            "COMPLETION_NAME",
            "START_PRODUCTION_DATE",
            "LAST_PRODUCTION_DATE",
        ]
        production_summary_df = pd.DataFrame(columns=columns)
        production_summary_df = production_summary_df.astype(
            {
                "API12": str,
                "API10": str,
                "O_PROD_STATUS": int,
                "O_CUMMULATIVE_PROD_MMBBL": float,
                "DAYS_ON_PROD": int,
                "O_MEAN_PROD_RATE_BOPD": float,
                "COMPLETION_NAME": str,
                "START_PRODUCTION_DATE": str,
                "LAST_PRODUCTION_DATE": str,
            }
        )

        well_api10 = str(well_api12)[0:10]
        values = [well_api12, well_api10, 0.0, 0.0, 0.0, 0.0, completion_name, "", ""]
        production_summary_df.loc[0] = values

        total_well_production = api12_df.MON_O_PROD_VOL.sum() / 1000 / 1000
        api12_production = api12_df[["PRODUCTION_DATETIME", "O_PROD_RATE_BOPD"]].copy()
        api12_production.rename(
            columns={"PRODUCTION_DATETIME": "date_time"}, inplace=True
        )
        api12_production = api12_production.round(decimals=3)
        api12_production["date_time"] = [
            item.strftime("%Y-%m-%d")
            for item in api12_production["date_time"].to_list()
        ]

        if len(api12_df) > 0 and total_well_production > 0:
            df_row_index = api12_df.index[0]

            current_value = production_summary_df.O_CUMMULATIVE_PROD_MMBBL.iloc[0]
            O_CUMMULATIVE_PROD_MMBBL = current_value + total_well_production
            production_summary_df.loc[df_row_index, "O_CUMMULATIVE_PROD_MMBBL"] = float(
                O_CUMMULATIVE_PROD_MMBBL
            )

            DAYS_ON_PROD = api12_df.DAYS_ON_PROD.sum()
            production_summary_df.loc[df_row_index, "DAYS_ON_PROD"] = DAYS_ON_PROD

            O_MEAN_PROD_RATE_BOPD = api12_df.MON_O_PROD_VOL.sum() / DAYS_ON_PROD
            production_summary_df.loc[df_row_index, "O_MEAN_PROD_RATE_BOPD"] = float(
                O_MEAN_PROD_RATE_BOPD
            )

            # Calculate start and last production dates
            production_dates_df = api12_df[api12_df.O_PROD_RATE_BOPD > 0]
            if len(production_dates_df) > 0:
                try:
                    start_production_date = (
                        production_dates_df.PRODUCTION_DATETIME.min().strftime(
                            "%Y-%m-%d"
                        )
                    )
                    last_production_date = (
                        production_dates_df.PRODUCTION_DATETIME.max().strftime(
                            "%Y-%m-%d"
                        )
                    )
                    production_summary_df.loc[df_row_index, "START_PRODUCTION_DATE"] = (
                        start_production_date
                    )
                    production_summary_df.loc[df_row_index, "LAST_PRODUCTION_DATE"] = (
                        last_production_date
                    )
                    logger.info(
                        f"Calculated production dates for API12 {well_api12}: "
                        f"{start_production_date} to {last_production_date}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error calculating production dates for API12 {well_api12}: {e}"
                    )
                    production_summary_df.loc[df_row_index, "START_PRODUCTION_DATE"] = (
                        ""
                    )
                    production_summary_df.loc[df_row_index, "LAST_PRODUCTION_DATE"] = ""
            else:
                logger.warning(f"No production data found for API12 {well_api12}")
                production_summary_df.loc[df_row_index, "START_PRODUCTION_DATE"] = ""
                production_summary_df.loc[df_row_index, "LAST_PRODUCTION_DATE"] = ""

            production_summary_df.loc[df_row_index, "O_PROD_STATUS"] = 1

        return production_summary_df


class ProductionRateCalculator:
    """Calculates production rates and cumulative production."""

    def add_production_rate_and_date_to_df(
        self, cfg: dict, api12_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Add production rate and datetime columns to the DataFrame.

        Args:
            cfg: Configuration dictionary
            api12_df: DataFrame with raw production data

        Returns:
            DataFrame with added PRODUCTION_DATETIME, O_PROD_RATE_BOPD,
            and O_CUMMULATIVE_PROD_MMBBL columns
        """
        production_date_time = []
        production_rate = []
        O_CUMMULATIVE_PROD_MMBBL_array = []

        for df_row in range(0, len(api12_df)):
            year = int(api12_df.PRODUCTION_DATE.iloc[df_row] / 100)
            month = api12_df.PRODUCTION_DATE.iloc[df_row] % year
            date_time = datetime.datetime(year, month, 1)
            date_time = dtu.last_day_of_month(date_time.date())

            if api12_df.DAYS_ON_PROD.iloc[df_row] != 0:
                rate = (
                    api12_df.MON_O_PROD_VOL.iloc[df_row]
                    / api12_df.DAYS_ON_PROD.iloc[df_row]
                )
            else:
                rate = 0

            production_date_time.append(date_time)
            production_rate.append(rate)

            O_CUMMULATIVE_PROD_MMBBL_previous_df_row = 0
            if len(O_CUMMULATIVE_PROD_MMBBL_array) > 0:
                O_CUMMULATIVE_PROD_MMBBL_previous_df_row = (
                    O_CUMMULATIVE_PROD_MMBBL_array[-1]
                )

            O_CUMMULATIVE_PROD_MMBBL = (
                api12_df.MON_O_PROD_VOL.iloc[df_row] / 1000 / 1000
                + O_CUMMULATIVE_PROD_MMBBL_previous_df_row
            )
            O_CUMMULATIVE_PROD_MMBBL_array.append(O_CUMMULATIVE_PROD_MMBBL)

        api12_df["PRODUCTION_DATETIME"] = production_date_time
        api12_df["O_PROD_RATE_BOPD"] = production_rate
        api12_df["O_CUMMULATIVE_PROD_MMBBL"] = O_CUMMULATIVE_PROD_MMBBL_array

        return api12_df
