"""
Enhanced Lease-level data aggregator with integrated data fetching
Aggregates well-level data up to lease level with direct BSEE data integration
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ....data.loaders.lease.local_files import DataFromLocalFiles as LeaseDataFromFiles
from ....data.production.production_data_sources import ProductionDataFromSources
from ....data.sources.bin.lease_data import LeaseData

# Import enhanced data loader and BSEE data modules
from ..data_loader_enhanced import HierarchicalDataLoader
from ..models import (
    EconomicMetrics,
    HierarchyLevel,
    Lease,
    ProductionMetrics,
    Well,
    WellSummary,
)
from .base import DataAggregator

logger = logging.getLogger(__name__)


class LeaseAggregator(DataAggregator):
    """Enhanced aggregator for lease-level data with integrated data fetching

    Features:
    - Direct integration with BSEE lease data modules
    - Real-time data fetching from binary files
    - Production data aggregation from multiple sources
    - Support for both block and lease-level queries
    """

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize Enhanced LeaseAggregator

        Args:
            data_path: Path to BSEE data directory
        """
        super().__init__()
        self.hierarchy_level = HierarchyLevel.LEASE
        self.data_path = data_path or Path("data/bsee")

        # Initialize data fetchers
        self.lease_data_fetcher = LeaseData()
        self.lease_files_loader = LeaseDataFromFiles()
        self.production_sources = ProductionDataFromSources()
        self.enhanced_loader = HierarchicalDataLoader(
            data_path, use_enhanced_refresh=True
        )

        # Cache for lease data
        self._lease_data_cache = {}
        self._production_cache = {}

    def get_hierarchy_level(self) -> HierarchyLevel:
        """Get hierarchy level"""
        return self.hierarchy_level

    def aggregate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate well data to lease level

        Args:
            data: Dictionary containing 'lease' key with Lease object

        Returns:
            Aggregated metrics for the lease
        """
        if not self.validate(data):
            logger.error("Invalid data provided to LeaseAggregator")
            return {}

        lease = data.get("lease")
        if not isinstance(lease, Lease):
            logger.error(f"Expected Lease object, got {type(lease)}")
            return {}

        # Initialize aggregation results
        result = {
            "oil_bbls": 0,
            "gas_mcf": 0,
            "water_bbls": 0,
            "well_count": 0,
            "active_well_count": 0,
            "oil_per_well": 0,
            "gas_per_well": 0,
            "wells": [],
            "first_production_date": None,
            "last_production_date": None,
            "cumulative_oil": 0,
            "cumulative_gas": 0,
            "peak_oil_rate": 0,
            "peak_gas_rate": 0,
            "average_water_depth": 0,
            "total_depth_sum": 0,
        }

        water_depths = []
        total_depths = []
        production_dates = []

        # Aggregate from wells
        for well in lease.children:
            if isinstance(well, Well):
                result["well_count"] += 1

                # Get well production data
                prod_data = well.get_production_data()

                # Sum production
                oil = prod_data.get("oil_bbls", 0)
                gas = prod_data.get("gas_mcf", 0)
                water = prod_data.get("water_bbls", 0)

                result["oil_bbls"] += oil
                result["gas_mcf"] += gas
                result["water_bbls"] += water

                # Track cumulative (same as total for now)
                result["cumulative_oil"] += oil
                result["cumulative_gas"] += gas

                # Check if well is active
                if hasattr(well, "status") and well.status == "active":
                    result["active_well_count"] += 1

                # Track well depths
                if hasattr(well, "water_depth_ft") and well.water_depth_ft:
                    water_depths.append(well.water_depth_ft)

                if hasattr(well, "total_depth_ft") and well.total_depth_ft:
                    total_depths.append(well.total_depth_ft)
                    result["total_depth_sum"] += well.total_depth_ft

                # Track production dates
                if hasattr(well, "spud_date") and well.spud_date:
                    production_dates.append(well.spud_date)

                if hasattr(well, "last_activity_date") and well.last_activity_date:
                    production_dates.append(well.last_activity_date)

                # Track peak rates (simplified)
                days_on = prod_data.get("days_on", 365)
                if days_on > 0:
                    oil_rate = oil / days_on
                    gas_rate = gas / days_on
                    result["peak_oil_rate"] = max(result["peak_oil_rate"], oil_rate)
                    result["peak_gas_rate"] = max(result["peak_gas_rate"], gas_rate)

                # Store well info
                well_info = {
                    "id": well.id,
                    "name": well.name,
                    "api_number": getattr(well, "api_number", None),
                    "oil_bbls": oil,
                    "gas_mcf": gas,
                    "water_bbls": water,
                    "status": getattr(well, "status", "unknown"),
                    "water_depth": getattr(well, "water_depth_ft", None),
                    "total_depth": getattr(well, "total_depth_ft", None),
                }
                result["wells"].append(well_info)

        # Calculate per-well averages
        if result["well_count"] > 0:
            result["oil_per_well"] = result["oil_bbls"] / result["well_count"]
            result["gas_per_well"] = result["gas_mcf"] / result["well_count"]

        # Calculate average water depth
        if water_depths:
            result["average_water_depth"] = sum(water_depths) / len(water_depths)

        # Determine production date range
        if production_dates:
            result["first_production_date"] = min(production_dates)
            result["last_production_date"] = max(production_dates)

        # Store in lease
        lease.total_production = {
            "oil_bbls": result["oil_bbls"],
            "gas_mcf": result["gas_mcf"],
            "water_bbls": result["water_bbls"],
        }

        # Cache results
        cache_key = f"lease_{lease.id}"
        self.cached_results[cache_key] = result

        return result

    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate input data

        Args:
            data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        self.clear_validation_errors()

        if not data:
            self.add_validation_error("Empty data provided")
            return False

        if "lease" not in data:
            self.add_validation_error("Missing 'lease' key in data")
            return False

        lease = data.get("lease")
        if not isinstance(lease, Lease):
            self.add_validation_error(f"Invalid lease type: {type(lease)}")
            return False

        return True

    def calculate_metrics(self, data: Dict[str, Any]) -> ProductionMetrics:
        """
        Calculate production metrics for lease

        Args:
            data: Lease data

        Returns:
            ProductionMetrics object
        """
        lease = data.get("lease")
        if not lease:
            return ProductionMetrics()

        # Get cached results or aggregate
        cache_key = f"lease_{lease.id}"
        if cache_key in self.cached_results:
            agg_data = self.cached_results[cache_key]
        else:
            agg_data = self.aggregate(data)

        # Calculate days in period
        days_in_period = 365
        if agg_data.get("first_production_date") and agg_data.get(
            "last_production_date"
        ):
            delta = agg_data["last_production_date"] - agg_data["first_production_date"]
            days_in_period = max(1, delta.days)

        metrics = ProductionMetrics(
            entity_id=lease.id,
            entity_type="lease",
            oil_production_bbls=agg_data.get("oil_bbls", 0),
            gas_production_mcf=agg_data.get("gas_mcf", 0),
            water_production_bbls=agg_data.get("water_bbls", 0),
            active_well_count=agg_data.get("active_well_count", 0),
            days_in_period=days_in_period,
        )

        # Sync volume aliases
        metrics.oil_volume_bbl = metrics.oil_production_bbls
        metrics.gas_volume_mcf = metrics.gas_production_mcf

        return metrics

    def analyze_individual_wells(self, lease: Lease) -> List[WellSummary]:
        """
        Analyze individual wells in lease

        Args:
            lease: Lease object

        Returns:
            List of WellSummary objects
        """
        well_summaries = []

        for well in lease.children:
            if isinstance(well, Well):
                summary = WellSummary(
                    well_id=well.id,
                    well_name=well.name,
                    api_number=getattr(well, "api_number", None),
                    lease_number=lease.number,
                    water_depth_ft=getattr(well, "water_depth_ft", None),
                    total_depth_ft=getattr(well, "total_depth_ft", None),
                    spud_date=getattr(well, "spud_date", None),
                    status=getattr(well, "status", "unknown"),
                    wellbore_status=getattr(well, "wellbore_status", "UNKNOWN"),
                )

                # Add production data
                prod_data = well.get_production_data()
                summary.total_oil_bbls = prod_data.get("oil_bbls", 0)
                summary.total_gas_mcf = prod_data.get("gas_mcf", 0)
                summary.total_water_bbls = prod_data.get("water_bbls", 0)
                summary.days_on_production = prod_data.get("days_on", 0)

                # Calculate derived metrics
                summary.cumulative_oil_bbl = summary.total_oil_bbls
                summary.cumulative_gas_mcf = summary.total_gas_mcf

                if summary.days_on_production > 0:
                    summary.peak_oil_rate_bopd = (
                        summary.total_oil_bbls / summary.days_on_production
                    )
                    summary.peak_gas_rate_mcfd = (
                        summary.total_gas_mcf / summary.days_on_production
                    )

                well_summaries.append(summary)

        return well_summaries

    def calculate_lease_economics(
        self, lease: Lease, price_deck: Dict[str, float]
    ) -> EconomicMetrics:
        """
        Calculate economic metrics for lease

        Args:
            lease: Lease object
            price_deck: Pricing information

        Returns:
            EconomicMetrics object
        """
        # Get production data
        if hasattr(lease, "total_production") and lease.total_production:
            prod_data = lease.total_production
        else:
            agg_result = self.aggregate({"lease": lease})
            prod_data = {
                "oil_bbls": agg_result.get("oil_bbls", 0),
                "gas_mcf": agg_result.get("gas_mcf", 0),
            }

        # Calculate economics
        oil_revenue = prod_data["oil_bbls"] * price_deck.get("oil", 75.0)
        gas_revenue = prod_data["gas_mcf"] * price_deck.get("gas", 3.5)
        total_revenue = oil_revenue + gas_revenue

        operating_costs = prod_data["oil_bbls"] * price_deck.get(
            "operating_cost_per_bbl", 12.5
        )
        royalties = total_revenue * price_deck.get("royalty_rate", 0.1875)

        # Estimate capital costs based on well count
        well_count = lease.get_well_count()
        capital_costs = well_count * price_deck.get(
            "well_capital_cost", 10000000
        )  # $10MM per well

        metrics = EconomicMetrics(
            entity_id=lease.id,
            entity_type="lease",
            revenue=total_revenue,
            operating_costs=operating_costs,
            capital_costs=capital_costs,
            royalties=royalties,
            production_bbls=prod_data["oil_bbls"],
        )
        metrics.calculate_net_income()

        return metrics

    def fetch_lease_data(
        self, lease_number: str, cfg: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Fetch lease data directly from BSEE sources

        Args:
            lease_number: Lease number to fetch
            cfg: Configuration dictionary

        Returns:
            DataFrame with lease data
        """
        # Check cache first
        if lease_number in self._lease_data_cache:
            logger.info(f"Using cached data for lease {lease_number}")
            return self._lease_data_cache[lease_number]

        logger.info(f"Fetching fresh data for lease {lease_number}")

        # Use enhanced loader to fetch lease data
        lease_df = self.enhanced_loader._load_lease_data(lease_number, cfg)

        if not lease_df.empty:
            # Cache the result
            self._lease_data_cache[lease_number] = lease_df
            logger.info(
                f"Successfully fetched {len(lease_df)} records for lease {lease_number}"
            )
        else:
            logger.warning(f"No data found for lease {lease_number}")

        return lease_df

    def fetch_production_data(self, lease_number: str) -> pd.DataFrame:
        """
        Fetch production data for a specific lease

        Args:
            lease_number: Lease number to fetch production for

        Returns:
            DataFrame with production data
        """
        # Check cache first
        if lease_number in self._production_cache:
            return self._production_cache[lease_number]

        logger.info(f"Fetching production data for lease {lease_number}")

        # Try to load from binary
        binary_path = self.data_path / "binary" / "production.bin"
        production_df = pd.DataFrame()

        if binary_path.exists():
            try:
                import pickle

                with open(binary_path, "rb") as f:
                    all_production = pickle.load(f)

                    # Filter for specific lease
                    lease_production = [
                        rec
                        for rec in all_production
                        if rec.get("lease_number") == lease_number
                    ]

                    if lease_production:
                        production_df = pd.DataFrame(lease_production)
                        self._production_cache[lease_number] = production_df

            except Exception as e:
                logger.error(f"Error loading production data: {e}")

        return production_df

    def aggregate_with_fresh_data(
        self, lease_number: str, cfg: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate lease data with fresh data fetching

        Args:
            lease_number: Lease number to aggregate
            cfg: Configuration dictionary

        Returns:
            Aggregated metrics with fresh data
        """
        # Fetch fresh lease data
        lease_df = self.fetch_lease_data(lease_number, cfg)

        # Fetch production data
        production_df = self.fetch_production_data(lease_number)

        # Initialize aggregation results
        result = {
            "lease_number": lease_number,
            "oil_bbls": 0,
            "gas_mcf": 0,
            "water_bbls": 0,
            "well_count": 0,
            "active_well_count": 0,
            "oil_per_well": 0,
            "gas_per_well": 0,
            "wells": [],
            "first_production_date": None,
            "last_production_date": None,
            "cumulative_oil": 0,
            "cumulative_gas": 0,
            "peak_oil_rate": 0,
            "peak_gas_rate": 0,
            "average_water_depth": 0,
            "total_depth_sum": 0,
            "field_names": set(),
            "block_numbers": set(),
        }

        # Process lease DataFrame
        if not lease_df.empty:
            # Count wells
            if "API_WELL_NUMBER" in lease_df.columns:
                result["well_count"] = lease_df["API_WELL_NUMBER"].nunique()

                # Get well details
                for _, well_row in lease_df.iterrows():
                    well_info = {
                        "api": well_row.get("API_WELL_NUMBER"),
                        "name": well_row.get("WELL_NAME", "Unknown"),
                        "water_depth": well_row.get("WATER_DEPTH", 0),
                        "total_depth": well_row.get("TOTAL_DEPTH", 0),
                        "status": well_row.get("STATUS", "Unknown"),
                        "spud_date": well_row.get("SPUD_DATE"),
                    }
                    result["wells"].append(well_info)

                    # Track fields and blocks
                    if "FIELD_NAME" in well_row:
                        result["field_names"].add(well_row["FIELD_NAME"])
                    if "BLOCK_NUMBER" in well_row:
                        result["block_numbers"].add(well_row["BLOCK_NUMBER"])

                    # Sum depths
                    result["total_depth_sum"] += well_info["total_depth"]

                    # Check if active
                    if well_info["status"].upper() in ["ACTIVE", "PRODUCING", "ONLINE"]:
                        result["active_well_count"] += 1

            # Calculate average water depth
            if "WATER_DEPTH" in lease_df.columns:
                water_depths = lease_df["WATER_DEPTH"].dropna()
                if len(water_depths) > 0:
                    result["average_water_depth"] = water_depths.mean()

        # Process production DataFrame
        if not production_df.empty:
            # Sum production volumes
            if "oil_bbls" in production_df.columns:
                result["oil_bbls"] = production_df["oil_bbls"].sum()
                result["cumulative_oil"] = result["oil_bbls"]

            if "gas_mcf" in production_df.columns:
                result["gas_mcf"] = production_df["gas_mcf"].sum()
                result["cumulative_gas"] = result["gas_mcf"]

            if "water_bbls" in production_df.columns:
                result["water_bbls"] = production_df["water_bbls"].sum()

            # Get production dates
            if "production_date" in production_df.columns:
                prod_dates = pd.to_datetime(production_df["production_date"])
                result["first_production_date"] = prod_dates.min()
                result["last_production_date"] = prod_dates.max()

            # Calculate peak rates
            if "oil_rate_bopd" in production_df.columns:
                result["peak_oil_rate"] = production_df["oil_rate_bopd"].max()
            if "gas_rate_mcfd" in production_df.columns:
                result["peak_gas_rate"] = production_df["gas_rate_mcfd"].max()

        # Calculate per-well metrics
        if result["well_count"] > 0:
            result["oil_per_well"] = result["oil_bbls"] / result["well_count"]
            result["gas_per_well"] = result["gas_mcf"] / result["well_count"]

        # Convert sets to lists for serialization
        result["field_names"] = list(result["field_names"])
        result["block_numbers"] = list(result["block_numbers"])

        return result

    def get_block_level_summary(
        self, block_number: str, cfg: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get summary for all leases in a block

        Args:
            block_number: Block number to summarize
            cfg: Configuration dictionary

        Returns:
            Block-level summary dictionary
        """
        logger.info(f"Getting block-level summary for block {block_number}")

        # Use enhanced loader to get block data
        block_df = self.enhanced_loader._load_block_data(block_number, cfg)

        if block_df.empty:
            logger.warning(f"No data found for block {block_number}")
            return {}

        # Extract unique leases in the block
        lease_numbers = []
        if "Lease Number" in block_df.columns:
            lease_numbers = block_df["Lease Number"].dropna().unique().tolist()
        elif "LEASE_NUMBER" in block_df.columns:
            lease_numbers = block_df["LEASE_NUMBER"].dropna().unique().tolist()

        # Aggregate data for each lease
        block_summary = {
            "block_number": block_number,
            "lease_count": len(lease_numbers),
            "total_oil_bbls": 0,
            "total_gas_mcf": 0,
            "total_water_bbls": 0,
            "total_well_count": 0,
            "active_well_count": 0,
            "leases": [],
        }

        for lease_num in lease_numbers:
            lease_data = self.aggregate_with_fresh_data(lease_num, cfg)

            block_summary["total_oil_bbls"] += lease_data.get("oil_bbls", 0)
            block_summary["total_gas_mcf"] += lease_data.get("gas_mcf", 0)
            block_summary["total_water_bbls"] += lease_data.get("water_bbls", 0)
            block_summary["total_well_count"] += lease_data.get("well_count", 0)
            block_summary["active_well_count"] += lease_data.get("active_well_count", 0)

            block_summary["leases"].append(
                {
                    "lease_number": lease_num,
                    "oil_bbls": lease_data.get("oil_bbls", 0),
                    "gas_mcf": lease_data.get("gas_mcf", 0),
                    "well_count": lease_data.get("well_count", 0),
                }
            )

        return block_summary
