"""
FDAS Production Data Processing Module

Handles monthly production aggregation, first oil detection, and production
summary generation for field development analysis.

Author: WorldEnergyData Team
Date: 2025-10-03
Source: Ported from FDAS build_multi_year_lease_matrix1.py
"""

import numpy as np
import pandas as pd


class ProductionProcessingError(Exception):
    """Raised when production processing fails"""

    pass


class ProductionProcessor:
    """
    Processes production data for FDAS financial analysis.

    Aggregates monthly production volumes, identifies first oil dates,
    and generates production summaries by development/lease/well.
    """

    def __init__(self, production_df: pd.DataFrame):
        """
        Initialize production processor.

        Args:
            production_df: DataFrame with production data including:
                          - API_WELL_NUMBER or well identifier
                          - PROD_DATE or date field
                          - OIL_VOLUME (barrels)
                          - WATER_VOLUME (barrels)
                          - GAS_VOLUME (MCF) optional
        """
        self.production_df = production_df.copy()
        self._validate_input()

    def _validate_input(self) -> None:
        """
        Validate required columns exist.

        Raises:
            ProductionProcessingError: If required columns missing
        """
        required = ["PROD_DATE", "OIL_VOLUME"]
        missing = [col for col in required if col not in self.production_df.columns]

        if missing:
            raise ProductionProcessingError(f"Missing required columns: {missing}")

    def aggregate_monthly(
        self, by: str = "API_WELL_NUMBER", date_col: str = "PROD_DATE"
    ) -> pd.DataFrame:
        """
        Aggregate production to monthly totals.

        Args:
            by: Grouping column (e.g., 'API_WELL_NUMBER', 'DEV_NAME', 'LEASE_NUMBER')
            date_col: Date column name

        Returns:
            DataFrame with monthly aggregated production

        Examples:
            >>> proc = ProductionProcessor(production_df)
            >>> monthly = proc.aggregate_monthly(by='DEV_NAME')
        """
        df = self.production_df.copy()

        # Convert to datetime and extract year-month
        df[date_col] = pd.to_datetime(df[date_col])
        df["YEAR_MONTH"] = df[date_col].dt.to_period("M")

        # Aggregate by grouping column and month
        agg_dict = {
            "OIL_VOLUME": "sum",
            "WATER_VOLUME": "sum" if "WATER_VOLUME" in df.columns else lambda x: 0,
            "GAS_VOLUME": "sum" if "GAS_VOLUME" in df.columns else lambda x: 0,
        }

        monthly = df.groupby([by, "YEAR_MONTH"]).agg(agg_dict).reset_index()

        # Rename to FDAS convention
        monthly = monthly.rename(
            columns={
                "OIL_VOLUME": "MONTHLY_OIL_BBL",
                "WATER_VOLUME": "MONTHLY_WATER_BBL",
                "GAS_VOLUME": "MONTHLY_GAS_MCF",
            }
        )

        # Sort by date
        monthly = monthly.sort_values([by, "YEAR_MONTH"])

        return monthly

    def identify_first_oil(
        self, by: str = "API_WELL_NUMBER", threshold_bbl: float = 10.0
    ) -> pd.DataFrame:
        """
        Identify first oil date for wells/developments.

        Args:
            by: Grouping column
            threshold_bbl: Minimum oil volume to count as first production

        Returns:
            DataFrame with first oil dates

        Examples:
            >>> proc = ProductionProcessor(production_df)
            >>> first_oil = proc.identify_first_oil(by='API_WELL_NUMBER')
        """
        df = self.production_df.copy()

        # Convert date
        df["PROD_DATE"] = pd.to_datetime(df["PROD_DATE"])

        # Filter to significant production
        df = df[df["OIL_VOLUME"] >= threshold_bbl]

        # Get first production date for each entity
        first_oil = (
            df.groupby(by).agg({"PROD_DATE": "min", "OIL_VOLUME": "sum"}).reset_index()
        )

        first_oil = first_oil.rename(
            columns={"PROD_DATE": "FIRST_OIL_DATE", "OIL_VOLUME": "CUMULATIVE_OIL_BBL"}
        )

        return first_oil

    def calculate_cumulative_production(
        self, by: str = "API_WELL_NUMBER"
    ) -> pd.DataFrame:
        """
        Calculate cumulative production over time.

        Args:
            by: Grouping column

        Returns:
            DataFrame with cumulative production columns
        """
        monthly = self.aggregate_monthly(by=by)

        # Calculate cumulative sums
        monthly["CUMULATIVE_OIL_BBL"] = monthly.groupby(by)["MONTHLY_OIL_BBL"].cumsum()
        monthly["CUMULATIVE_WATER_BBL"] = monthly.groupby(by)[
            "MONTHLY_WATER_BBL"
        ].cumsum()
        monthly["CUMULATIVE_GAS_MCF"] = monthly.groupby(by)["MONTHLY_GAS_MCF"].cumsum()

        # Calculate water cut
        total_liquid = monthly["MONTHLY_OIL_BBL"] + monthly["MONTHLY_WATER_BBL"]
        monthly["WATER_CUT"] = np.where(
            total_liquid > 0, monthly["MONTHLY_WATER_BBL"] / total_liquid, 0.0
        )

        return monthly

    def generate_production_summary(self, by: str = "API_WELL_NUMBER") -> pd.DataFrame:
        """
        Generate comprehensive production summary.

        Args:
            by: Grouping column

        Returns:
            DataFrame with production statistics

        Examples:
            >>> proc = ProductionProcessor(production_df)
            >>> summary = proc.generate_production_summary(by='DEV_NAME')
        """
        df = self.production_df.copy()
        df["PROD_DATE"] = pd.to_datetime(df["PROD_DATE"])

        summary = (
            df.groupby(by)
            .agg(
                {
                    "OIL_VOLUME": ["sum", "mean", "max"],
                    "WATER_VOLUME": (
                        ["sum", "mean"] if "WATER_VOLUME" in df.columns else lambda x: 0
                    ),
                    "PROD_DATE": ["min", "max", "count"],
                }
            )
            .reset_index()
        )

        # Flatten column names
        summary.columns = [
            f"{col[0]}_{col[1]}" if col[1] else col[0] for col in summary.columns
        ]

        # Rename for clarity
        summary = summary.rename(
            columns={
                "OIL_VOLUME_sum": "TOTAL_OIL_BBL",
                "OIL_VOLUME_mean": "AVG_MONTHLY_OIL_BBL",
                "OIL_VOLUME_max": "PEAK_MONTHLY_OIL_BBL",
                "WATER_VOLUME_sum": "TOTAL_WATER_BBL",
                "PROD_DATE_min": "FIRST_PRODUCTION_DATE",
                "PROD_DATE_max": "LAST_PRODUCTION_DATE",
                "PROD_DATE_count": "PRODUCTION_MONTHS",
            }
        )

        return summary

    def create_pivot_table(
        self, by: str = "API_WELL_NUMBER", value: str = "MONTHLY_OIL_BBL"
    ) -> pd.DataFrame:
        """
        Create pivot table with months as columns.

        Args:
            by: Row grouping
            value: Value to pivot

        Returns:
            Pivot table DataFrame
        """
        monthly = self.aggregate_monthly(by=by)

        pivot = monthly.pivot(index=by, columns="YEAR_MONTH", values=value).fillna(0)

        return pivot


def aggregate_monthly_production(
    production_df: pd.DataFrame, by: str = "DEV_NAME", date_col: str = "PROD_DATE"
) -> pd.DataFrame:
    """
    Convenience function to aggregate production monthly.

    Args:
        production_df: Production data
        by: Grouping column
        date_col: Date column name

    Returns:
        Monthly aggregated DataFrame

    Examples:
        >>> monthly = aggregate_monthly_production(df, by='LEASE_NUMBER')
    """
    processor = ProductionProcessor(production_df)
    return processor.aggregate_monthly(by=by, date_col=date_col)


def identify_first_oil_date(
    production_df: pd.DataFrame,
    by: str = "API_WELL_NUMBER",
    threshold_bbl: float = 10.0,
) -> pd.DataFrame:
    """
    Convenience function to identify first oil dates.

    Args:
        production_df: Production data
        by: Grouping column
        threshold_bbl: Minimum volume threshold

    Returns:
        DataFrame with first oil information

    Examples:
        >>> first_oil = identify_first_oil_date(df, by='DEV_NAME')
    """
    processor = ProductionProcessor(production_df)
    return processor.identify_first_oil(by=by, threshold_bbl=threshold_bbl)


class ProductionForecaster:
    """
    Generates production forecasts for economic analysis.

    Uses decline curve analysis or simple extrapolation for future
    production estimates.
    """

    def __init__(self, historical_production: pd.DataFrame):
        """
        Initialize forecaster with historical data.

        Args:
            historical_production: Monthly production history
        """
        self.historical = historical_production

    def exponential_decline(
        self, initial_rate: float, decline_rate: float, months: int
    ) -> np.ndarray:
        """
        Generate exponential decline forecast.

        Args:
            initial_rate: Initial production rate (BBL/month)
            decline_rate: Annual decline rate (decimal, e.g., 0.15 for 15%)
            months: Number of months to forecast

        Returns:
            Array of monthly production volumes

        Examples:
            >>> forecaster = ProductionForecaster(historical_df)
            >>> forecast = forecaster.exponential_decline(10000, 0.15, 60)
        """
        # Convert annual decline to monthly
        monthly_decline = 1 - (1 - decline_rate) ** (1 / 12)

        # Generate forecast
        time_periods = np.arange(months)
        forecast = initial_rate * (1 - monthly_decline) ** time_periods

        return forecast

    def hyperbolic_decline(
        self, initial_rate: float, initial_decline: float, b_factor: float, months: int
    ) -> np.ndarray:
        """
        Generate hyperbolic decline forecast.

        Args:
            initial_rate: Initial production rate
            initial_decline: Initial decline rate
            b_factor: Hyperbolic exponent (0 = exponential, 1 = harmonic)
            months: Number of months

        Returns:
            Array of monthly production volumes
        """
        time_periods = np.arange(months) / 12.0  # Convert to years

        if b_factor == 0:
            # Exponential decline
            forecast = initial_rate * np.exp(-initial_decline * time_periods)
        else:
            # Hyperbolic decline
            forecast = initial_rate / (
                1 + b_factor * initial_decline * time_periods
            ) ** (1 / b_factor)

        return forecast
