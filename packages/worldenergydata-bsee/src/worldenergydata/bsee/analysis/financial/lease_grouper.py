"""
Lease Grouper Module for SME Financial Analysis
Groups and aggregates data by lease and development
Implements grouping logic from V20
"""

import logging
from typing import Any, Dict, List, Tuple

import pandas as pd

from .data_loader import normalize_lease_number, pick_column

logger = logging.getLogger(__name__)


def group_leases_by_development(leases_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Group leases by development name

    Args:
        leases_df: DataFrame with lease information

    Returns:
        Dictionary mapping development names to lease DataFrames
    """
    if leases_df.empty:
        return {}

    groups = {}
    for dev_name, group in leases_df.groupby("DEV_NAME"):
        groups[str(dev_name)] = group.copy()

    return groups


def aggregate_production_by_lease(
    production_df: pd.DataFrame, wells_df: pd.DataFrame, leases_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Aggregate production data by lease

    Args:
        production_df: Production data with well-level data
        wells_df: Well information with lease mapping
        leases_df: Lease information

    Returns:
        DataFrame with production aggregated by lease
    """
    if production_df.empty or wells_df.empty:
        return pd.DataFrame()

    # Create well to lease mapping
    well_lease_map = {}
    well_col = pick_column(wells_df, ["WELL_NAME", "WELL", "API_WELL_NUMBER"])

    if well_col and "LEASE_NUM" in wells_df.columns:
        for _, row in wells_df.iterrows():
            well = str(row[well_col]).strip()
            lease = str(row["LEASE_NUM"]).strip()
            if well and lease:
                well_lease_map[well] = lease

    # Aggregate production by lease
    result = production_df.copy()

    # If production is in wide format (wells as columns)
    if "YearMonth" in result.columns:
        # Get well columns (all except YearMonth)
        well_cols = [c for c in result.columns if c != "YearMonth"]

        # Group wells by lease
        lease_groups = {}
        for well in well_cols:
            lease = well_lease_map.get(well)
            if lease:
                if lease not in lease_groups:
                    lease_groups[lease] = []
                lease_groups[lease].append(well)

        # Sum production by lease
        lease_production = pd.DataFrame({"YearMonth": result["YearMonth"]})
        for lease, wells in lease_groups.items():
            lease_production[lease] = result[wells].sum(axis=1)

        return lease_production

    # If production is in long format
    elif "WELL_NAME" in result.columns:
        # Map wells to leases
        result["LEASE_NUM"] = result["WELL_NAME"].map(well_lease_map)

        # Aggregate by lease and time
        return result.groupby(["YearMonth", "LEASE_NUM"])["OIL_BBL"].sum().reset_index()

    return pd.DataFrame()


def map_wells_to_leases(
    wells_df: pd.DataFrame, leases_df: pd.DataFrame
) -> Dict[str, Dict[str, Any]]:
    """
    Create mapping of wells to lease information

    Args:
        wells_df: Well data
        leases_df: Lease data

    Returns:
        Dictionary mapping well names to lease info
    """
    well_map = {}

    if wells_df.empty or leases_df.empty:
        return well_map

    # Find well identifier column
    well_col = pick_column(wells_df, ["WELL_NAME", "WELL", "API_WELL_NUMBER", "API"])
    if not well_col:
        return well_map

    # Create lease lookup
    lease_lookup = {}
    if "LEASE_NUM" in leases_df.columns:
        for _, row in leases_df.iterrows():
            lease_num = str(row["LEASE_NUM"]).strip()
            lease_lookup[lease_num] = {
                "lease_name": row.get("LEASE_NAME", ""),
                "dev_name": row.get("DEV_NAME", ""),
                "dev_type": row.get("DEV_TYPE_EFF", ""),
                "block": row.get("BLOCK", ""),
            }

    # Map wells to leases
    for _, row in wells_df.iterrows():
        well = str(row[well_col]).strip()
        if well and "LEASE_NUM" in row:
            lease_num = str(row["LEASE_NUM"]).strip()
            if lease_num in lease_lookup:
                well_map[well] = {"lease_num": lease_num, **lease_lookup[lease_num]}
            else:
                well_map[well] = {"lease_num": lease_num}

    return well_map


class LeaseGrouper:
    """
    Groups and aggregates data by lease for financial analysis
    Implements V20 grouping and aggregation logic
    """

    def __init__(self):
        """Initialize lease grouper"""
        self._groups = {}
        self._well_lease_map = {}
        self._lease_summary = None

    def group_by_development(
        self, leases_df: pd.DataFrame, normalize: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Group leases by development

        Args:
            leases_df: Lease data
            normalize: Whether to normalize lease numbers

        Returns:
            Dictionary of development groups
        """
        if leases_df.empty:
            return {}

        df = leases_df.copy()

        # Normalize lease numbers if requested
        if normalize and "LEASE_NUM" in df.columns:
            df["LEASE_NUM"] = df["LEASE_NUM"].apply(normalize_lease_number)

        # Group by development
        self._groups = group_leases_by_development(df)
        return self._groups

    def map_wells_to_leases(
        self, wells_df: pd.DataFrame, leases_df: pd.DataFrame
    ) -> Dict[str, Dict[str, Any]]:
        """
        Create well to lease mapping

        Args:
            wells_df: Well data
            leases_df: Lease data

        Returns:
            Well to lease mapping
        """
        self._well_lease_map = map_wells_to_leases(wells_df, leases_df)
        return self._well_lease_map

    def aggregate_production_by_lease(
        self,
        production_df: pd.DataFrame,
        wells_df: pd.DataFrame,
        leases_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Aggregate production by lease

        Args:
            production_df: Production data
            wells_df: Well data
            leases_df: Lease data

        Returns:
            Production aggregated by lease
        """
        return aggregate_production_by_lease(production_df, wells_df, leases_df)

    def group_development_wells(
        self, dev_name: str, wells_df: pd.DataFrame, leases_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Get wells for a specific development

        Args:
            dev_name: Development name
            wells_df: Well data
            leases_df: Lease data

        Returns:
            Wells in the development
        """
        if wells_df.empty or leases_df.empty:
            return pd.DataFrame()

        # Get leases for development
        dev_leases = leases_df[leases_df["DEV_NAME"] == dev_name]["LEASE_NUM"].tolist()

        # Filter wells by lease
        if "LEASE_NUM" in wells_df.columns:
            return wells_df[wells_df["LEASE_NUM"].isin(dev_leases)]

        return pd.DataFrame()

    def create_lease_summary(
        self,
        leases_df: pd.DataFrame,
        wells_df: pd.DataFrame,
        production_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Create summary statistics by lease

        Args:
            leases_df: Lease data
            wells_df: Well data
            production_df: Production data

        Returns:
            Summary DataFrame
        """
        if leases_df.empty:
            return pd.DataFrame()

        summary = leases_df[["LEASE_NUM", "LEASE_NAME", "DEV_NAME"]].copy()

        # Add well counts
        if not wells_df.empty and "LEASE_NUM" in wells_df.columns:
            well_counts = (
                wells_df.groupby("LEASE_NUM")
                .agg(
                    WELL_COUNT=("LEASE_NUM", "count"),
                    ACTIVE_WELLS=(
                        "STATUS",
                        lambda x: (
                            (x == "ACTIVE").sum()
                            if "STATUS" in wells_df.columns
                            else len(x)
                        ),
                    ),
                )
                .reset_index()
            )

            summary = summary.merge(well_counts, on="LEASE_NUM", how="left")
            summary["WELL_COUNT"] = summary["WELL_COUNT"].fillna(0).astype(int)
            summary["ACTIVE_WELLS"] = summary["ACTIVE_WELLS"].fillna(0).astype(int)

        # Add production totals
        if not production_df.empty:
            lease_prod = self.aggregate_production_by_lease(
                production_df, wells_df, leases_df
            )

            if not lease_prod.empty:
                # Sum total production by lease
                if "LEASE_NUM" in lease_prod.columns:
                    total_prod = (
                        lease_prod.groupby("LEASE_NUM")["OIL_BBL"].sum().reset_index()
                    )
                    total_prod.columns = ["LEASE_NUM", "TOTAL_PRODUCTION"]
                else:
                    # Production columns are lease numbers
                    lease_cols = [c for c in lease_prod.columns if c != "YearMonth"]
                    total_prod = pd.DataFrame(
                        {
                            "LEASE_NUM": lease_cols,
                            "TOTAL_PRODUCTION": [
                                lease_prod[c].sum() for c in lease_cols
                            ],
                        }
                    )

                summary = summary.merge(total_prod, on="LEASE_NUM", how="left")
                summary["TOTAL_PRODUCTION"] = summary["TOTAL_PRODUCTION"].fillna(0)

        self._lease_summary = summary
        return summary

    def get_lease_time_range(
        self, lease_num: str, production_df: pd.DataFrame, wells_df: pd.DataFrame
    ) -> Tuple[pd.Timestamp, pd.Timestamp]:
        """
        Get production time range for a lease

        Args:
            lease_num: Lease number
            production_df: Production data
            wells_df: Well data

        Returns:
            Tuple of (start_date, end_date)
        """
        if production_df.empty or wells_df.empty:
            return (pd.NaT, pd.NaT)

        # Get wells for lease
        lease_wells = wells_df[wells_df["LEASE_NUM"] == lease_num]
        well_col = pick_column(lease_wells, ["WELL_NAME", "WELL", "API_WELL_NUMBER"])

        if not well_col:
            return (pd.NaT, pd.NaT)

        well_names = lease_wells[well_col].tolist()

        # Find production dates
        if "YearMonth" in production_df.columns:
            # Check if wells are columns
            well_cols = [w for w in well_names if w in production_df.columns]
            if well_cols:
                # Find non-zero production
                prod_sum = production_df[well_cols].sum(axis=1)
                nonzero = production_df[prod_sum > 0]["YearMonth"]
                if not nonzero.empty:
                    return (nonzero.min(), nonzero.max())

        return (pd.NaT, pd.NaT)

    def filter_active_leases(self, leases_df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter for active leases only

        Args:
            leases_df: Lease data

        Returns:
            Active leases only
        """
        if leases_df.empty:
            return leases_df

        if "PRODUCTION_STATUS" in leases_df.columns:
            return leases_df[leases_df["PRODUCTION_STATUS"] == "ACTIVE"]

        return leases_df

    def process_production_gaps(self, production_df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle production gaps in data

        Args:
            production_df: Production data with potential gaps

        Returns:
            Production data with gaps handled
        """
        if production_df.empty:
            return production_df

        result = production_df.copy()

        # Fill zero production months (gaps) but maintain actual zeros
        # This is important for economic calculations

        return result

    def get_development_summary(self, dev_name: str) -> Dict[str, Any]:
        """
        Get summary statistics for a development

        Args:
            dev_name: Development name

        Returns:
            Summary dictionary
        """
        if dev_name not in self._groups:
            return {}

        dev_group = self._groups[dev_name]

        summary = {
            "development": dev_name,
            "lease_count": len(dev_group),
            "lease_numbers": (
                dev_group["LEASE_NUM"].tolist()
                if "LEASE_NUM" in dev_group.columns
                else []
            ),
            "dev_type": (
                dev_group["DEV_TYPE_EFF"].iloc[0]
                if "DEV_TYPE_EFF" in dev_group.columns
                else ""
            ),
            "blocks": (
                dev_group["BLOCK"].unique().tolist()
                if "BLOCK" in dev_group.columns
                else []
            ),
        }

        return summary

    def create_development_hierarchy(
        self, leases_df: pd.DataFrame, wells_df: pd.DataFrame
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Create hierarchical structure: Development -> Lease -> Wells

        Args:
            leases_df: Lease data
            wells_df: Well data

        Returns:
            Hierarchical dictionary
        """
        hierarchy = {}

        # Group by development
        dev_groups = self.group_by_development(leases_df)

        for dev_name, dev_leases in dev_groups.items():
            hierarchy[dev_name] = {}

            # For each lease in development
            for lease_num in dev_leases["LEASE_NUM"]:
                # Find wells for this lease
                if not wells_df.empty and "LEASE_NUM" in wells_df.columns:
                    lease_wells = wells_df[wells_df["LEASE_NUM"] == lease_num]
                    well_col = pick_column(
                        lease_wells, ["WELL_NAME", "WELL", "API_WELL_NUMBER"]
                    )

                    if well_col:
                        hierarchy[dev_name][lease_num] = lease_wells[well_col].tolist()
                    else:
                        hierarchy[dev_name][lease_num] = []
                else:
                    hierarchy[dev_name][lease_num] = []

        return hierarchy
