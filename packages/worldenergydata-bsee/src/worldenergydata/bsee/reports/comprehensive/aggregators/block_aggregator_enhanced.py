"""
Enhanced Block-level data aggregator with integrated data fetching
Aggregates field-level data up to block level with direct BSEE data integration
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from worldenergydata.common.data_resolver import get_data_root

from ....data.loaders.block.local_files import DataFromLocalFiles as BlockDataFromFiles
from ....data.sources.bin.block_data import BlockData

# Import enhanced data loader and BSEE data modules
from ..data_loader_enhanced import HierarchicalDataLoader
from ..models import Block, Field, HierarchyLevel, ProductionMetrics
from .base import DataAggregator

logger = logging.getLogger(__name__)


class BlockAggregator(DataAggregator):
    """Enhanced aggregator for block-level data with integrated data fetching

    Features:
    - Direct block data fetching from BSEE binary files
    - Enhanced data refresh integration
    - Multi-source data aggregation
    """

    def __init__(self, data_path: Optional[str] = None):
        """Initialize enhanced BlockAggregator

        Args:
            data_path: Path to BSEE data directory
        """
        super().__init__()
        self.hierarchy_level = HierarchyLevel.BLOCK
        self.data_path = data_path or get_data_root() / "bsee"

        # Initialize data fetchers
        self.block_data_fetcher = BlockData()
        self.block_files_loader = BlockDataFromFiles()
        self.enhanced_loader = HierarchicalDataLoader(
            data_path, use_enhanced_refresh=True
        )

        # Cache for block data
        self._block_data_cache = {}

    def get_hierarchy_level(self) -> HierarchyLevel:
        """Get hierarchy level"""
        return self.hierarchy_level

    def aggregate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate field data to block level

        Args:
            data: Dictionary containing 'block' key with Block object

        Returns:
            Aggregated metrics for the block
        """
        if not self.validate(data):
            logger.error("Invalid data provided to BlockAggregator")
            return {}

        block = data.get("block")
        if not isinstance(block, Block):
            logger.error(f"Expected Block object, got {type(block)}")
            return {}

        # Initialize aggregation results
        result = {
            "oil_bbls": 0,
            "gas_mcf": 0,
            "water_bbls": 0,
            "field_count": 0,
            "total_lease_count": 0,
            "total_well_count": 0,
            "active_well_count": 0,
            "revenue": 0,
            "operating_cost": 0,
            "fields": [],
        }

        # Aggregate from fields
        for field in block.children:
            if isinstance(field, Field):
                result["field_count"] += 1

                # Get field production (either from total_production or by aggregating)
                if hasattr(field, "total_production") and field.total_production:
                    prod_data = field.total_production
                else:
                    # Trigger field aggregation if needed
                    prod_data = field.aggregate_production()

                # Sum production
                result["oil_bbls"] += prod_data.get("oil_bbls", 0)
                result["gas_mcf"] += prod_data.get("gas_mcf", 0)
                result["water_bbls"] += prod_data.get("water_bbls", 0)

                # Count leases and wells
                result["total_lease_count"] += field.get_lease_count()

                # Count wells in field
                well_count = 0
                active_well_count = 0
                for lease in field.children:
                    if hasattr(lease, "children"):
                        for well in lease.children:
                            well_count += 1
                            if hasattr(well, "status") and well.status == "active":
                                active_well_count += 1

                result["total_well_count"] += well_count
                result["active_well_count"] += active_well_count

                # Store field info
                field_info = {
                    "id": field.id,
                    "name": field.name,
                    "oil_bbls": prod_data.get("oil_bbls", 0),
                    "gas_mcf": prod_data.get("gas_mcf", 0),
                    "lease_count": field.get_lease_count(),
                }
                result["fields"].append(field_info)

        # Calculate revenue if price deck provided
        if "price_deck" in data:
            revenue_costs = self.aggregate_revenue_costs(block, data["price_deck"])
            result.update(revenue_costs)

        # Store in block
        block.total_production = {
            "oil_bbls": result["oil_bbls"],
            "gas_mcf": result["gas_mcf"],
            "water_bbls": result["water_bbls"],
        }

        # Cache results
        cache_key = f"block_{block.id}"
        self.cached_results[cache_key] = result

        return result

    def fetch_block_data(
        self, block_numbers: List[str], cfg: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """Fetch block data directly from BSEE binary files

        Args:
            block_numbers: List of block numbers to fetch
            cfg: Optional configuration dictionary

        Returns:
            DataFrame with block data
        """
        cache_key = f"blocks_{','.join(sorted(block_numbers))}"

        if cache_key in self._block_data_cache:
            logger.info(f"Using cached data for blocks: {block_numbers}")
            return self._block_data_cache[cache_key]

        try:
            # Fetch from binary files
            results = self.block_data_fetcher.get_block_data_from_input_bin_files(
                block_numbers
            )

            # Combine results
            if results:
                combined_df = pd.concat(results.values(), ignore_index=True)
                self._block_data_cache[cache_key] = combined_df
                return combined_df
            else:
                logger.warning(f"No data found for blocks: {block_numbers}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching block data: {e}")
            return pd.DataFrame()

    def aggregate_with_fresh_data(
        self, block_numbers: List[str], cfg: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Aggregate data with fresh fetch from BSEE sources

        Args:
            block_numbers: List of block numbers to aggregate
            cfg: Optional configuration dictionary

        Returns:
            Aggregated block-level metrics
        """
        # Refresh data if needed
        if cfg:
            self.enhanced_loader.refresh_data_if_needed(cfg)

        # Fetch fresh block data
        block_df = self.fetch_block_data(block_numbers, cfg)

        if block_df.empty:
            logger.warning("No block data available for aggregation")
            return {}

        # Aggregate metrics
        aggregated = {
            "total_blocks": (
                len(block_df["Block Number"].unique())
                if "Block Number" in block_df
                else 0
            ),
            "total_fields": (
                len(block_df["Field Name"].unique()) if "Field Name" in block_df else 0
            ),
            "area_codes": (
                block_df["Area Code"].unique().tolist()
                if "Area Code" in block_df
                else []
            ),
            "block_numbers": block_numbers,
            "data_source": "BSEE Binary Files",
            "fetch_timestamp": datetime.now().isoformat(),
        }

        # Add production metrics if available
        if self.enhanced_loader:
            production_data = self.enhanced_loader._load_production_data()
            if production_data:
                aggregated["has_production_data"] = True
                aggregated["production_record_count"] = len(production_data)

        return aggregated

    def get_regional_summary(self, area_code: str) -> Dict[str, Any]:
        """Get summary for all blocks in a region

        Args:
            area_code: Area code (e.g., 'GC' for Green Canyon)

        Returns:
            Regional summary metrics
        """
        try:
            # Use the files loader for regional data
            regional_data = self.block_files_loader.get_block_data_by_area_code(
                area_code
            )

            if regional_data.empty:
                return {"area_code": area_code, "blocks": [], "error": "No data found"}

            summary = {
                "area_code": area_code,
                "total_blocks": len(regional_data["Block Number"].unique()),
                "total_fields": (
                    len(regional_data["Field Name"].unique())
                    if "Field Name" in regional_data
                    else 0
                ),
                "blocks": regional_data["Block Number"].unique().tolist(),
                "data_points": len(regional_data),
            }

            return summary

        except Exception as e:
            logger.error(f"Error getting regional summary: {e}")
            return {"area_code": area_code, "error": str(e)}

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

        if "block" not in data:
            self.add_validation_error("Missing 'block' key in data")
            return False

        block = data.get("block")
        if not isinstance(block, Block):
            self.add_validation_error(f"Invalid block type: {type(block)}")
            return False

        return True

    def calculate_metrics(self, data: Dict[str, Any]) -> ProductionMetrics:
        """
        Calculate production metrics for block

        Args:
            data: Block data

        Returns:
            ProductionMetrics object
        """
        block = data.get("block")
        if not block:
            return ProductionMetrics()

        # Get cached results or aggregate
        cache_key = f"block_{block.id}"
        if cache_key in self.cached_results:
            agg_data = self.cached_results[cache_key]
        else:
            agg_data = self.aggregate(data)

        metrics = ProductionMetrics(
            entity_id=block.id,
            entity_type="block",
            oil_production_bbls=agg_data.get("oil_bbls", 0),
            gas_production_mcf=agg_data.get("gas_mcf", 0),
            water_production_bbls=agg_data.get("water_bbls", 0),
            active_well_count=agg_data.get("active_well_count", 0),
        )

        # Sync volume aliases
        metrics.oil_volume_bbl = metrics.oil_production_bbls
        metrics.gas_volume_mcf = metrics.gas_production_mcf

        return metrics

    def aggregate_fields_with_rollup(
        self, block: Block, include_economics: bool = True
    ) -> Dict[str, Any]:
        """
        Aggregate fields with detailed rollup information

        Args:
            block: Block to aggregate
            include_economics: Whether to include economic calculations

        Returns:
            Detailed aggregation with rollup info
        """
        rollup = {
            "block_id": block.id,
            "block_name": block.name,
            "fields": [],
            "totals": {
                "oil_bbls": 0,
                "gas_mcf": 0,
                "water_bbls": 0,
                "revenue": 0,
                "operating_cost": 0,
                "net_income": 0,
            },
        }

        for field in block.children:
            if isinstance(field, Field):
                field_data = {
                    "field_id": field.id,
                    "field_name": field.name,
                    "production": field.aggregate_production(),
                    "lease_count": field.get_lease_count(),
                }

                # Add to totals
                for key in ["oil_bbls", "gas_mcf", "water_bbls"]:
                    rollup["totals"][key] += field_data["production"].get(key, 0)

                # Calculate field economics if requested
                if include_economics:
                    oil_revenue = field_data["production"].get("oil_bbls", 0) * 75.0
                    gas_revenue = field_data["production"].get("gas_mcf", 0) * 3.5
                    field_data["revenue"] = oil_revenue + gas_revenue
                    field_data["operating_cost"] = (
                        field_data["production"].get("oil_bbls", 0) * 12.5
                    )
                    field_data["net_income"] = (
                        field_data["revenue"] - field_data["operating_cost"]
                    )

                    rollup["totals"]["revenue"] += field_data["revenue"]
                    rollup["totals"]["operating_cost"] += field_data["operating_cost"]
                    rollup["totals"]["net_income"] += field_data["net_income"]

                rollup["fields"].append(field_data)

        return rollup
