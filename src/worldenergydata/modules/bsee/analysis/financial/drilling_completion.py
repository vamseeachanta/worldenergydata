"""
Drilling and Completion Data Processing Module
Handles D&C cost calculations and allocations
Implements logic from SME V20
"""

import logging
from typing import Dict, Optional, Set, Tuple

import pandas as pd

from .data_loader import pick_column

logger = logging.getLogger(__name__)


def calculate_drilling_costs(
    dc_data: pd.DataFrame, cost_per_day: float, fill_na: float = 0
) -> Dict[str, float]:
    """
    Calculate drilling costs based on days and daily rate

    Args:
        dc_data: DataFrame with drilling days
        cost_per_day: Cost per drilling day
        fill_na: Value to fill NaN values

    Returns:
        Dictionary mapping wells to drilling costs
    """
    costs = {}

    if dc_data.empty:
        return costs

    # Find well column
    well_col = pick_column(dc_data, ["WELL_NAME", "WELL", "API_WELL_NUMBER", "API"])
    if not well_col:
        return costs

    # Calculate costs
    for _, row in dc_data.iterrows():
        well = str(row[well_col]).strip()
        if well and "DRILL_DAYS" in row:
            days = pd.to_numeric(row["DRILL_DAYS"], errors="coerce")
            if pd.isna(days):
                days = fill_na
            costs[well] = float(days * cost_per_day)

    return costs


def calculate_completion_costs(
    dc_data: pd.DataFrame, cost_per_day: float, fill_na: float = 0
) -> Dict[str, float]:
    """
    Calculate completion costs based on days and daily rate

    Args:
        dc_data: DataFrame with completion days
        cost_per_day: Cost per completion day
        fill_na: Value to fill NaN values

    Returns:
        Dictionary mapping wells to completion costs
    """
    costs = {}

    if dc_data.empty:
        return costs

    # Find well column
    well_col = pick_column(dc_data, ["WELL_NAME", "WELL", "API_WELL_NUMBER", "API"])
    if not well_col:
        return costs

    # Calculate costs
    for _, row in dc_data.iterrows():
        well = str(row[well_col]).strip()
        if well and "COMP_DAYS" in row:
            days = pd.to_numeric(row["COMP_DAYS"], errors="coerce")
            if pd.isna(days):
                days = fill_na
            costs[well] = float(days * cost_per_day)

    return costs


def build_dc_day_maps(
    dc_totals: pd.DataFrame, dc_monthly: pd.DataFrame
) -> Tuple[Dict, Dict, Dict]:
    """
    Build drilling and completion day maps from data

    Args:
        dc_totals: Totals data
        dc_monthly: Monthly data

    Returns:
        Tuple of (drill_map, comp_map, input_totals)
    """
    drill_map = {}
    comp_map = {}
    input_totals = {}

    # Process totals first
    if not dc_totals.empty:
        well_col = pick_column(
            dc_totals, ["WELL_NAME", "WELL", "API_WELL_NUMBER", "API"]
        )

        if well_col:
            for _, row in dc_totals.iterrows():
                well = str(row.get(well_col, "")).strip()
                if not well:
                    continue

                drill_days = float(
                    pd.to_numeric(row.get("DRILL_DAYS", 0), errors="coerce") or 0
                )
                comp_days = float(
                    pd.to_numeric(row.get("COMP_DAYS", 0), errors="coerce") or 0
                )
                spud_date = pd.to_datetime(
                    row.get("WELL_SPUD_DATE", pd.NaT), errors="coerce"
                )
                td_date = pd.to_datetime(
                    row.get("TOTAL_DEPTH_DATE", pd.NaT), errors="coerce"
                )

                input_totals[well] = (drill_days, comp_days, spud_date, td_date)

    # Process monthly data (overrides totals if both exist)
    if not dc_monthly.empty:
        well_col = pick_column(
            dc_monthly, ["WELL_NAME", "WELL", "API_WELL_NUMBER", "API"]
        )

        if well_col:
            # Group by well to get totals
            grp = (
                dc_monthly.groupby(well_col, dropna=True)
                .agg({"DRILL_DAYS": "sum", "COMP_DAYS": "sum"})
                .reset_index()
            )

            for _, row in grp.iterrows():
                well = str(row[well_col]).strip()
                if not well:
                    continue

                # Override totals with monthly sum
                if well not in input_totals:
                    input_totals[well] = (
                        float(row.get("DRILL_DAYS", 0) or 0),
                        float(row.get("COMP_DAYS", 0) or 0),
                        pd.NaT,
                        pd.NaT,
                    )

            # Build monthly maps
            for _, row in dc_monthly.iterrows():
                well = str(row.get(well_col, "")).strip()
                if not well:
                    continue

                month = pd.to_datetime(row.get("YearMonth"), errors="coerce")
                if pd.isna(month):
                    continue

                month_key = month.strftime("%Y-%m")

                # Add drilling days
                drill_days = float(
                    pd.to_numeric(row.get("DRILL_DAYS", 0), errors="coerce") or 0
                )
                if drill_days > 0:
                    if month_key not in drill_map:
                        drill_map[month_key] = {}
                    drill_map[month_key][well] = drill_days

                # Add completion days
                comp_days = float(
                    pd.to_numeric(row.get("COMP_DAYS", 0), errors="coerce") or 0
                )
                if comp_days > 0:
                    if month_key not in comp_map:
                        comp_map[month_key] = {}
                    comp_map[month_key][well] = comp_days

    return drill_map, comp_map, input_totals


def allocate_dc_costs_monthly(
    dc_monthly: pd.DataFrame, cost_assumptions: Dict[str, float]
) -> pd.DataFrame:
    """
    Allocate D&C costs on a monthly basis

    Args:
        dc_monthly: Monthly D&C data
        cost_assumptions: Cost per day assumptions

    Returns:
        DataFrame with monthly cost allocations
    """
    if dc_monthly.empty:
        return pd.DataFrame()

    result = dc_monthly.copy()

    # Get cost rates
    drill_cost_per_day = cost_assumptions.get("DRILL_COST_PER_DAY", 100000)
    comp_cost_per_day = cost_assumptions.get("COMP_COST_PER_DAY", 75000)

    # Calculate monthly costs
    result["DRILL_COST"] = (
        pd.to_numeric(result.get("DRILL_DAYS", 0), errors="coerce").fillna(0)
        * drill_cost_per_day
    )
    result["COMP_COST"] = (
        pd.to_numeric(result.get("COMP_DAYS", 0), errors="coerce").fillna(0)
        * comp_cost_per_day
    )
    result["TOTAL_DC_COST"] = result["DRILL_COST"] + result["COMP_COST"]

    return result


class DrillingCompletionProcessor:
    """
    Processes drilling and completion data for financial analysis
    Implements V20 D&C cost allocation logic
    """

    def __init__(self, cost_assumptions: Optional[Dict[str, float]] = None):
        """
        Initialize processor

        Args:
            cost_assumptions: Cost assumptions dictionary
        """
        self.cost_assumptions = cost_assumptions or {}
        self.drill_cost_per_day = self.cost_assumptions.get(
            "DRILL_COST_PER_DAY", 100000
        )
        self.comp_cost_per_day = self.cost_assumptions.get("COMP_COST_PER_DAY", 75000)
        self.subsea_drill_cost = self.cost_assumptions.get(
            "SUBSEA_DRILL_COST_PER_DAY", 150000
        )
        self.subsea_comp_cost = self.cost_assumptions.get(
            "SUBSEA_COMP_COST_PER_DAY", 100000
        )
        self._cache = {}

    def calculate_drilling_costs(
        self, dc_data: pd.DataFrame, cost_per_day: float, fill_na: float = 0
    ) -> Dict[str, float]:
        """Calculate drilling costs for wells"""
        return calculate_drilling_costs(dc_data, cost_per_day, fill_na)

    def calculate_completion_costs(
        self, dc_data: pd.DataFrame, cost_per_day: float, fill_na: float = 0
    ) -> Dict[str, float]:
        """Calculate completion costs for wells"""
        return calculate_completion_costs(dc_data, cost_per_day, fill_na)

    def build_day_maps_for_development(
        self,
        dev_name: str,
        dc_totals: pd.DataFrame,
        dc_monthly: pd.DataFrame,
        leases_df: Optional[pd.DataFrame] = None,
    ) -> Tuple[Dict, Dict, Set]:
        """
        Build day maps for a specific development

        Args:
            dev_name: Development name
            dc_totals: Totals data
            dc_monthly: Monthly data
            leases_df: Optional lease data for filtering

        Returns:
            Tuple of (drill_map, comp_map, all_wells)
        """
        # Filter data for development
        totals_filtered = self._filter_by_development(dc_totals, dev_name, leases_df)
        monthly_filtered = self._filter_by_development(dc_monthly, dev_name, leases_df)

        # Build maps
        drill_map, comp_map, input_totals = build_dc_day_maps(
            totals_filtered, monthly_filtered
        )

        # Get all wells
        all_wells = set(input_totals.keys())

        return drill_map, comp_map, all_wells

    def _filter_by_development(
        self, df: pd.DataFrame, dev_name: str, leases_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Filter dataframe by development"""
        if df is None or df.empty:
            return pd.DataFrame()

        result = df.copy()
        result.columns = [c.upper() for c in result.columns]

        # If DEV_NAME column exists, use it directly
        if "DEV_NAME" in result.columns:
            return result[result["DEV_NAME"].str.upper() == dev_name.upper()]

        # Otherwise try to join with leases
        if leases_df is not None and not leases_df.empty:
            leases = leases_df.copy()
            leases.columns = [c.upper() for c in leases.columns]

            # Join on lease number or name
            if "LEASE_NUM" in result.columns and "LEASE_NUM" in leases.columns:
                result = result.merge(
                    leases[["LEASE_NUM", "DEV_NAME"]], on="LEASE_NUM", how="left"
                )
            elif "LEASE_NAME" in result.columns and "LEASE_NAME" in leases.columns:
                result = result.merge(
                    leases[["LEASE_NAME", "DEV_NAME"]], on="LEASE_NAME", how="left"
                )

            if "DEV_NAME" in result.columns:
                return result[result["DEV_NAME"].str.upper() == dev_name.upper()]

        return result

    def allocate_costs_monthly(
        self,
        dc_monthly: pd.DataFrame,
        cost_assumptions: Optional[Dict[str, float]] = None,
    ) -> pd.DataFrame:
        """
        Allocate costs monthly

        Args:
            dc_monthly: Monthly D&C data
            cost_assumptions: Optional cost overrides

        Returns:
            Monthly cost allocation
        """
        costs = cost_assumptions or self.cost_assumptions
        return allocate_dc_costs_monthly(dc_monthly, costs)

    def process_dc_totals(
        self, dc_totals: pd.DataFrame, dc_monthly: pd.DataFrame
    ) -> Tuple[Dict, Dict]:
        """
        Process D&C totals with monthly override

        Args:
            dc_totals: Totals data
            dc_monthly: Monthly data

        Returns:
            Tuple of (totals_map, has_monthly)
        """
        _, _, input_totals = build_dc_day_maps(dc_totals, dc_monthly)

        # Check which wells have monthly data
        has_monthly = {}
        if not dc_monthly.empty:
            well_col = pick_column(
                dc_monthly, ["WELL_NAME", "WELL", "API_WELL_NUMBER", "API"]
            )
            if well_col:
                monthly_wells = set(dc_monthly[well_col].unique())
                for well in input_totals:
                    has_monthly[well] = well in monthly_wells

        return input_totals, has_monthly

    def calculate_system_specific_costs(
        self, dc_data: pd.DataFrame, cost_assumptions: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate costs based on system type (subsea vs dry tree)

        Args:
            dc_data: D&C data with system type
            cost_assumptions: Cost assumptions

        Returns:
            Well costs dictionary
        """
        costs = {}
        well_col = pick_column(dc_data, ["WELL_NAME", "WELL", "API_WELL_NUMBER", "API"])

        if not well_col:
            return costs

        for _, row in dc_data.iterrows():
            well = str(row[well_col]).strip()
            if not well:
                continue

            # Determine system type
            system = str(row.get("DEV_TYPE", "dry tree")).lower()

            # Select appropriate costs
            if "subsea" in system:
                drill_cost = cost_assumptions.get("SUBSEA_DRILL_COST_PER_DAY", 150000)
                comp_cost = cost_assumptions.get("SUBSEA_COMP_COST_PER_DAY", 100000)
            else:
                drill_cost = cost_assumptions.get("DRILL_COST_PER_DAY", 100000)
                comp_cost = cost_assumptions.get("COMP_COST_PER_DAY", 75000)

            # Calculate total cost
            drill_days = float(
                pd.to_numeric(row.get("DRILL_DAYS", 0), errors="coerce") or 0
            )
            comp_days = float(
                pd.to_numeric(row.get("COMP_DAYS", 0), errors="coerce") or 0
            )

            costs[well] = (drill_days * drill_cost) + (comp_days * comp_cost)

        return costs

    def validate_dates(self, dc_data: pd.DataFrame) -> None:
        """
        Validate spud and TD dates

        Args:
            dc_data: D&C data with dates

        Raises:
            ValueError: If dates are invalid
        """
        if dc_data.empty:
            return

        if (
            "WELL_SPUD_DATE" in dc_data.columns
            and "TOTAL_DEPTH_DATE" in dc_data.columns
        ):
            for idx, row in dc_data.iterrows():
                spud = pd.to_datetime(row.get("WELL_SPUD_DATE"), errors="coerce")
                td = pd.to_datetime(row.get("TOTAL_DEPTH_DATE"), errors="coerce")

                if pd.notna(spud) and pd.notna(td) and td < spud:
                    well_col = pick_column(
                        dc_data, ["WELL_NAME", "WELL", "API_WELL_NUMBER"]
                    )
                    well = row.get(well_col, f"Row {idx}") if well_col else f"Row {idx}"
                    raise ValueError(f"Total depth date before spud date for {well}")

    def generate_capex_schedule(
        self,
        dc_monthly: pd.DataFrame,
        cost_assumptions: Dict[str, float],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        Generate monthly CAPEX schedule

        Args:
            dc_monthly: Monthly D&C data
            cost_assumptions: Cost assumptions
            start_date: Schedule start
            end_date: Schedule end

        Returns:
            Monthly CAPEX schedule
        """
        # Create date range
        dates = pd.date_range(start_date, end_date, freq="MS")
        schedule = pd.DataFrame({"YearMonth": dates})

        # Calculate monthly costs
        monthly_costs = self.allocate_costs_monthly(dc_monthly, cost_assumptions)

        if not monthly_costs.empty:
            # Aggregate by month
            capex_by_month = (
                monthly_costs.groupby("YearMonth")
                .agg({"DRILL_COST": "sum", "COMP_COST": "sum", "TOTAL_DC_COST": "sum"})
                .reset_index()
            )

            # Rename columns
            capex_by_month.columns = [
                "YearMonth",
                "DRILL_CAPEX",
                "COMP_CAPEX",
                "TOTAL_CAPEX",
            ]

            # Merge with schedule
            schedule = schedule.merge(capex_by_month, on="YearMonth", how="left")
            schedule = schedule.fillna(0)
        else:
            schedule["DRILL_CAPEX"] = 0
            schedule["COMP_CAPEX"] = 0
            schedule["TOTAL_CAPEX"] = 0

        return schedule

    def calculate_first_oil_dates(
        self, dc_totals: pd.DataFrame, production_df: pd.DataFrame
    ) -> Dict[str, pd.Timestamp]:
        """
        Calculate first oil dates for wells

        Args:
            dc_totals: D&C totals with completion dates
            production_df: Production data

        Returns:
            Dictionary of well to first oil date
        """
        first_oil = {}
        well_col = pick_column(
            dc_totals, ["WELL_NAME", "WELL", "API_WELL_NUMBER", "API"]
        )

        if not well_col or production_df.empty:
            return first_oil

        for _, row in dc_totals.iterrows():
            well = str(row[well_col]).strip()
            if not well:
                continue

            # Check if well has production
            if well in production_df.columns:
                well_prod = production_df[["YearMonth", well]].copy()
                well_prod = well_prod[well_prod[well] > 0]

                if not well_prod.empty:
                    first_oil[well] = well_prod["YearMonth"].min()

        return first_oil

    def calculate_efficiency_metrics(self, dc_totals: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate drilling efficiency metrics

        Args:
            dc_totals: D&C totals data

        Returns:
            Dictionary of metrics
        """
        metrics = {}

        if dc_totals.empty:
            return metrics

        # Calculate drilling metrics
        if "DRILL_DAYS" in dc_totals.columns:
            drill_days = pd.to_numeric(
                dc_totals["DRILL_DAYS"], errors="coerce"
            ).dropna()
            if not drill_days.empty:
                metrics["avg_drill_days"] = drill_days.mean()
                metrics["drill_days_std"] = drill_days.std()
                metrics["total_drill_days"] = drill_days.sum()
                metrics["min_drill_days"] = drill_days.min()
                metrics["max_drill_days"] = drill_days.max()

        # Calculate completion metrics
        if "COMP_DAYS" in dc_totals.columns:
            comp_days = pd.to_numeric(dc_totals["COMP_DAYS"], errors="coerce").dropna()
            if not comp_days.empty:
                metrics["avg_comp_days"] = comp_days.mean()
                metrics["comp_days_std"] = comp_days.std()
                metrics["total_comp_days"] = comp_days.sum()
                metrics["min_comp_days"] = comp_days.min()
                metrics["max_comp_days"] = comp_days.max()

        # Calculate well count
        well_col = pick_column(
            dc_totals, ["WELL_NAME", "WELL", "API_WELL_NUMBER", "API"]
        )
        if well_col:
            metrics["well_count"] = dc_totals[well_col].nunique()

        return metrics

    def build_monthly_dc_map(self, daily_data: pd.DataFrame) -> Dict[Tuple, float]:
        """
        Build monthly D&C map from daily data

        Args:
            daily_data: Daily drilling/completion data

        Returns:
            Map of (month, well, activity) to days
        """
        dc_map = {}

        if daily_data.empty:
            return dc_map

        # Convert date column
        daily_data["Date"] = pd.to_datetime(daily_data["Date"])
        daily_data["YearMonth"] = daily_data["Date"].dt.to_period("M").dt.to_timestamp()

        # Aggregate by month, well, and activity
        for activity in ["DRILL_ACTIVITY", "COMP_ACTIVITY"]:
            if activity not in daily_data.columns:
                continue

            activity_type = "DRILL" if "DRILL" in activity else "COMP"

            # Group and sum
            grouped = (
                daily_data[daily_data[activity] > 0]
                .groupby(["YearMonth", "WELL_NAME"])[activity]
                .sum()
            )

            for (month, well), days in grouped.items():
                key = (month.strftime("%Y-%m"), well, activity_type)
                dc_map[key] = float(days)

        return dc_map

    def aggregate_dc_by_lease(self, dc_by_well: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate D&C data by lease

        Args:
            dc_by_well: Well-level D&C data

        Returns:
            Lease-level aggregates
        """
        if dc_by_well.empty or "LEASE_NUM" not in dc_by_well.columns:
            return pd.DataFrame()

        # Aggregate by lease
        lease_agg = (
            dc_by_well.groupby("LEASE_NUM")
            .agg(
                {
                    "DRILL_DAYS": "sum",
                    "COMP_DAYS": "sum",
                    "DRILL_COST": "sum",
                    "COMP_COST": "sum",
                }
            )
            .reset_index()
        )

        # Rename columns
        lease_agg.columns = [
            "LEASE_NUM",
            "TOTAL_DRILL_DAYS",
            "TOTAL_COMP_DAYS",
            "TOTAL_DRILL_COST",
            "TOTAL_COMP_COST",
        ]

        # Add total cost
        lease_agg["TOTAL_DC_COST"] = (
            lease_agg["TOTAL_DRILL_COST"] + lease_agg["TOTAL_COMP_COST"]
        )

        # Add well count
        lease_agg["WELL_COUNT"] = dc_by_well.groupby("LEASE_NUM").size().values

        return lease_agg
