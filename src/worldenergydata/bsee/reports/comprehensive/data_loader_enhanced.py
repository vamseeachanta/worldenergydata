"""
Hierarchical data loader for BSEE integration
Loads and organizes data from BSEE sources into hierarchical structure
"""

import logging
import pickle
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import pandas as pd

from worldenergydata.common.data_resolver import get_data_root

# Import enhanced data refresh components
from ...data.enhanced.data_refresh_chunked import DataRefreshChunked
from ...data.loaders.block.local_files import DataFromLocalFiles as BlockDataFromFiles
from ...data.loaders.lease.local_files import DataFromLocalFiles as LeaseDataFromFiles
from ...data.refresh.data_refresh_enhanced import DataRefreshEnhanced
from ...data.sources.bin.api_data import APIData
from ...data.sources.bin.block_data import BlockData
from ...data.sources.bin.lease_data import LeaseData
from .models import Block, Field, Lease, Well

# Import BSEE analysis modules


logger = logging.getLogger(__name__)


class HierarchicalDataLoader:
    """Enhanced data loader with BSEE data refresh and fetching integration

    Features:
    - Direct integration with enhanced data refresh for fresh data
    - Block and lease data fetching from binary files
    - Production data aggregation at all levels
    - Chunk-based optimization for large datasets
    - Caching for improved performance
    """

    def __init__(
        self, data_path: Optional[Path] = None, use_enhanced_refresh: bool = True
    ):
        """
        Initialize enhanced data loader

        Args:
            data_path: Path to BSEE data directory
            use_enhanced_refresh: Use enhanced data refresh for fresh data
        """
        self.data_path = data_path or get_data_root() / "bsee"
        self.use_enhanced_refresh = use_enhanced_refresh

        # Initialize data fetchers
        self.block_data_fetcher = BlockData()
        self.lease_data_fetcher = LeaseData()
        self.well_data_fetcher = APIData()
        self.block_files_loader = BlockDataFromFiles()
        self.lease_files_loader = LeaseDataFromFiles()

        # Initialize enhanced refresh if enabled
        if use_enhanced_refresh:
            self.data_refresh_chunked = DataRefreshChunked()
            self.data_refresh_enhanced = DataRefreshEnhanced(
                use_chunked_downloads=True, use_optimized_processing=True
            )

        self.blocks = {}
        self.fields = {}
        self.leases = {}
        self.wells = {}
        self._cache = {}

    def refresh_data_if_needed(
        self, cfg: Dict[str, Any], force_refresh: bool = False
    ) -> None:
        """
        Refresh BSEE data if needed using enhanced refresh

        Args:
            cfg: Configuration dictionary
            force_refresh: Force data refresh even if cache exists
        """
        if not self.use_enhanced_refresh:
            logger.info("Enhanced refresh disabled, using existing data")
            return

        logger.info("Checking if data refresh is needed...")

        # Check if binary files exist
        binary_path = self.data_path / "binary"
        needs_refresh = force_refresh or not binary_path.exists()

        if needs_refresh:
            logger.info("Starting enhanced data refresh...")

            # Configure refresh parameters
            refresh_cfg = cfg.copy()
            refresh_cfg["enhanced_mode"] = True
            refresh_cfg["chunked_refresh"] = True
            refresh_cfg["data"] = {
                "well": True,
                "production": True,
                "war": False,  # WAR data if needed
            }

            # Run enhanced refresh
            if hasattr(self, "data_refresh_chunked"):
                self.data_refresh_chunked.router(refresh_cfg)
            else:
                self.data_refresh_enhanced.router(refresh_cfg)

            logger.info("Data refresh completed")
        else:
            logger.info("Using existing data (no refresh needed)")

    def load_hierarchy(
        self,
        block_number: Optional[str] = None,
        field_name: Optional[str] = None,
        lease_number: Optional[str] = None,
        cfg: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Load complete hierarchy with enhanced data fetching

        Args:
            block_number: Optional block number to filter
            field_name: Optional field name to filter
            lease_number: Optional lease number to filter
            cfg: Configuration dictionary for data refresh

        Returns:
            Dictionary with hierarchical data structure
        """
        logger.info(
            f"Loading hierarchy: block={block_number}, field={field_name}, lease={lease_number}"
        )

        # Refresh data if configuration provided
        if cfg:
            self.refresh_data_if_needed(cfg)

        # Load block data if specified
        if block_number:
            block_data = self._load_block_data(block_number, cfg)
        else:
            block_data = None

        # Load lease data if specified
        if lease_number:
            lease_data = self._load_lease_data(lease_number, cfg)
        else:
            lease_data = None

        # Load raw data from all sources
        raw_data = self._load_comprehensive_data(
            block_number, field_name, lease_number, block_data, lease_data
        )

        # Build hierarchy
        hierarchy = self._build_hierarchy(raw_data)

        # Add production data
        self._add_production_data(hierarchy)

        # Add economic data
        self._add_economic_data(hierarchy)

        return hierarchy

    def _load_raw_data(
        self, block_number: Optional[str] = None, field_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load raw data from BSEE sources

        Args:
            block_number: Optional block filter
            field_name: Optional field filter

        Returns:
            Raw data dictionary
        """
        raw_data = {
            "blocks": [],
            "fields": [],
            "leases": [],
            "wells": [],
            "production": [],
        }

        # Try to load from binary files first (faster)
        binary_path = self.data_path / "binary"
        if binary_path.exists():
            raw_data = self._load_from_binary(binary_path, block_number, field_name)
        else:
            # Fall back to CSV/API loading
            raw_data = self._load_from_csv(block_number, field_name)

        return raw_data

    def _load_from_binary(
        self,
        binary_path: Path,
        block_number: Optional[str] = None,
        field_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load data from binary files (pickle format)

        Args:
            binary_path: Path to binary files
            block_number: Optional block filter
            field_name: Optional field filter

        Returns:
            Data dictionary
        """
        data = {"blocks": [], "fields": [], "leases": [], "wells": [], "production": []}

        # Load well data
        well_file = binary_path / "wells.bin"
        if well_file.exists():
            with open(well_file, "rb") as f:
                wells_data = pickle.load(f)

                for well_record in wells_data:
                    # Filter by field if specified
                    if field_name and well_record.get("field_name") != field_name:
                        continue

                    # Extract block from area/block designation
                    area_block = well_record.get("area_block", "")
                    if block_number and block_number not in area_block:
                        continue

                    # Parse block, field, lease from well data
                    block_info = self._parse_block_info(area_block)
                    if block_info and block_info not in data["blocks"]:
                        data["blocks"].append(block_info)

                    field_info = {
                        "id": well_record.get("field_name", "Unknown"),
                        "name": well_record.get("field_name", "Unknown"),
                        "block_id": block_info["id"] if block_info else None,
                    }
                    if field_info not in data["fields"]:
                        data["fields"].append(field_info)

                    lease_info = {
                        "id": well_record.get("lease_number", "Unknown"),
                        "number": well_record.get("lease_number", "Unknown"),
                        "field_id": field_info["id"],
                    }
                    if lease_info not in data["leases"]:
                        data["leases"].append(lease_info)

                    well_info = {
                        "id": well_record.get("api_well_number", "Unknown"),
                        "name": well_record.get("well_name", "Unknown"),
                        "api_number": well_record.get("api_well_number"),
                        "lease_id": lease_info["id"],
                        "water_depth": well_record.get("water_depth"),
                        "total_depth": well_record.get("total_borehole_length"),
                        "spud_date": well_record.get("spud_date"),
                        "status": well_record.get("well_status", "ACTIVE"),
                    }
                    data["wells"].append(well_info)

        # Load production data
        prod_file = binary_path / "production.bin"
        if prod_file.exists():
            with open(prod_file, "rb") as f:
                prod_data = pickle.load(f)
                data["production"] = prod_data

        return data

    def _load_from_csv(
        self, block_number: Optional[str] = None, field_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load data from CSV files

        Args:
            block_number: Optional block filter
            field_name: Optional field filter

        Returns:
            Data dictionary
        """
        # This would integrate with existing BSEE CSV loaders
        # For now, return sample data for testing
        return self._create_sample_data(block_number, field_name)

    def _parse_block_info(self, area_block: str) -> Optional[Dict[str, str]]:
        """
        Parse block information from area/block string

        Args:
            area_block: Area block designation (e.g., "WR 759")

        Returns:
            Block info dictionary or None
        """
        if not area_block:
            return None

        parts = area_block.strip().split()
        if len(parts) >= 2:
            area = parts[0]
            number = parts[1]
            return {"id": f"{area}_{number}", "area": area, "number": number}
        return None

    def _build_hierarchy(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build hierarchical structure from raw data

        Args:
            raw_data: Raw data dictionary

        Returns:
            Hierarchical structure
        """
        hierarchy = {"blocks": {}, "fields": {}, "leases": {}, "wells": {}}

        # Create blocks
        for block_data in raw_data.get("blocks", []):
            block = Block(
                id=block_data["id"],
                number=block_data["number"],
                area=block_data.get("area", ""),
            )
            hierarchy["blocks"][block.id] = block
            self.blocks[block.id] = block

        # Create fields and link to blocks
        for field_data in raw_data.get("fields", []):
            field = Field(
                id=field_data["id"],
                name=field_data["name"],
                block_id=field_data.get("block_id"),
            )
            hierarchy["fields"][field.id] = field
            self.fields[field.id] = field

            # Link to parent block
            if field_data.get("block_id") in hierarchy["blocks"]:
                parent_block = hierarchy["blocks"][field_data["block_id"]]
                parent_block.add_child(field)

        # Create leases and link to fields
        for lease_data in raw_data.get("leases", []):
            lease = Lease(
                id=lease_data["id"],
                number=lease_data["number"],
                field_id=lease_data.get("field_id"),
            )
            hierarchy["leases"][lease.id] = lease
            self.leases[lease.id] = lease

            # Link to parent field
            if lease_data.get("field_id") in hierarchy["fields"]:
                parent_field = hierarchy["fields"][lease_data["field_id"]]
                parent_field.add_child(lease)

        # Create wells and link to leases
        for well_data in raw_data.get("wells", []):
            well = Well(
                id=well_data["id"],
                name=well_data["name"],
                api_number=well_data.get("api_number"),
                lease_id=well_data.get("lease_id"),
                water_depth_ft=well_data.get("water_depth"),
                total_depth_ft=well_data.get("total_depth"),
                spud_date=well_data.get("spud_date"),
                status=well_data.get("status", "active"),
            )
            hierarchy["wells"][well.id] = well
            self.wells[well.id] = well

            # Link to parent lease
            if well_data.get("lease_id") in hierarchy["leases"]:
                parent_lease = hierarchy["leases"][well_data["lease_id"]]
                parent_lease.add_child(well)

        return hierarchy

    def _add_production_data(self, hierarchy: Dict[str, Any]):
        """
        Add production data to wells

        Args:
            hierarchy: Hierarchical structure
        """
        # This would load actual production data
        # For now, add sample production data
        for well_id, well in hierarchy["wells"].items():
            # Sample production data
            production = {
                "oil_bbls": 50000 + (hash(well_id) % 100000),
                "gas_mcf": 25000 + (hash(well_id) % 50000),
                "water_bbls": 10000 + (hash(well_id) % 20000),
                "days_on": 365,
            }
            well.set_production_data(production)

    def stream_large_dataset(self, chunk_size: int = 1000) -> Iterator[Dict[str, Any]]:
        """
        Stream large datasets in chunks

        Args:
            chunk_size: Number of wells per chunk

        Yields:
            Chunks of hierarchical data
        """
        # Load well list
        well_files = list(self.data_path.glob("wells_*.bin"))

        for well_file in well_files:
            with open(well_file, "rb") as f:
                wells_chunk = pickle.load(f)

                # Process in chunks
                for i in range(0, len(wells_chunk), chunk_size):
                    chunk = wells_chunk[i : i + chunk_size]

                    # Build hierarchy for this chunk
                    raw_data = self._process_chunk(chunk)
                    hierarchy = self._build_hierarchy(raw_data)
                    self._add_production_data(hierarchy)

                    yield hierarchy

    def _process_chunk(self, wells_chunk: List[Dict]) -> Dict[str, Any]:
        """
        Process a chunk of wells into raw data format

        Args:
            wells_chunk: List of well records

        Returns:
            Raw data dictionary
        """
        data = {"blocks": [], "fields": [], "leases": [], "wells": [], "production": []}

        seen_blocks = set()
        seen_fields = set()
        seen_leases = set()

        for well_record in wells_chunk:
            # Extract unique blocks, fields, leases
            area_block = well_record.get("area_block", "")
            block_info = self._parse_block_info(area_block)

            if block_info and block_info["id"] not in seen_blocks:
                data["blocks"].append(block_info)
                seen_blocks.add(block_info["id"])

            field_name = well_record.get("field_name", "Unknown")
            if field_name not in seen_fields:
                data["fields"].append(
                    {
                        "id": field_name,
                        "name": field_name,
                        "block_id": block_info["id"] if block_info else None,
                    }
                )
                seen_fields.add(field_name)

            lease_number = well_record.get("lease_number", "Unknown")
            if lease_number not in seen_leases:
                data["leases"].append(
                    {"id": lease_number, "number": lease_number, "field_id": field_name}
                )
                seen_leases.add(lease_number)

            # Add well
            data["wells"].append(
                {
                    "id": well_record.get("api_well_number", "Unknown"),
                    "name": well_record.get("well_name", "Unknown"),
                    "api_number": well_record.get("api_well_number"),
                    "lease_id": lease_number,
                    "water_depth": well_record.get("water_depth"),
                    "total_depth": well_record.get("total_borehole_length"),
                    "spud_date": well_record.get("spud_date"),
                    "status": well_record.get("well_status", "ACTIVE"),
                }
            )

        return data

    def _create_sample_data(
        self, block_number: Optional[str] = None, field_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create sample data for testing

        Args:
            block_number: Optional block filter
            field_name: Optional field filter

        Returns:
            Sample data dictionary
        """
        # Sample data matching go-by reports structure
        data = {
            "blocks": [{"id": "WR_759", "area": "WR", "number": "759"}],
            "fields": [
                {"id": "Jack", "name": "Jack", "block_id": "WR_759"},
                {"id": "St_Malo", "name": "St. Malo", "block_id": "WR_759"},
            ],
            "leases": [
                {"id": "OCS-G-12345", "number": "OCS-G-12345", "field_id": "Jack"},
                {"id": "OCS-G-12346", "number": "OCS-G-12346", "field_id": "Jack"},
                {"id": "OCS-G-12347", "number": "OCS-G-12347", "field_id": "St_Malo"},
            ],
            "wells": [
                {
                    "id": "API001",
                    "name": "PS001",
                    "api_number": "API001",
                    "lease_id": "OCS-G-12345",
                    "water_depth": 7000,
                    "total_depth": 25000,
                    "spud_date": date(2020, 1, 15),
                    "status": "active",
                },
                {
                    "id": "API002",
                    "name": "PS002",
                    "api_number": "API002",
                    "lease_id": "OCS-G-12345",
                    "water_depth": 7000,
                    "total_depth": 26000,
                    "spud_date": date(2020, 3, 20),
                    "status": "active",
                },
                {
                    "id": "API003",
                    "name": "PS003",
                    "api_number": "API003",
                    "lease_id": "OCS-G-12346",
                    "water_depth": 7100,
                    "total_depth": 24500,
                    "spud_date": date(2020, 6, 10),
                    "status": "active",
                },
            ],
            "production": [],
        }

        # Apply filters
        if block_number and block_number != "759":
            return {
                "blocks": [],
                "fields": [],
                "leases": [],
                "wells": [],
                "production": [],
            }

        if field_name:
            data["fields"] = [f for f in data["fields"] if f["name"] == field_name]
            field_ids = {f["id"] for f in data["fields"]}
            data["leases"] = [l for l in data["leases"] if l["field_id"] in field_ids]
            lease_ids = {l["id"] for l in data["leases"]}
            data["wells"] = [w for w in data["wells"] if w["lease_id"] in lease_ids]

        return data

    def get_hierarchy_stats(self) -> Dict[str, int]:
        """
        Get statistics about loaded hierarchy

        Returns:
            Dictionary with counts
        """
        return {
            "blocks": len(self.blocks),
            "fields": len(self.fields),
            "leases": len(self.leases),
            "wells": len(self.wells),
        }

    def _load_block_data(
        self, block_number: str, cfg: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Load block-specific data using block data fetcher

        Args:
            block_number: Block number to load
            cfg: Configuration dictionary

        Returns:
            DataFrame with block data
        """
        logger.info(f"Loading block data for {block_number}")

        # Prepare configuration for block data fetcher
        block_cfg = cfg or {}
        if "parameters" not in block_cfg:
            block_cfg["parameters"] = {
                "filepath": {"Well_APD_Default": str(self.data_path / "binary")}
            }

        # Create input group for block fetcher
        input_group = {
            "bottom_block": {
                "number": block_number,
                "area": "GOM",  # Default to Gulf of Mexico
            }
        }

        # Fetch block data
        try:
            self.block_data_fetcher.router(block_cfg, input_group)

            # Load the generated CSV file
            output_path = (
                Path(block_cfg.get("Analysis", {}).get("result_folder", "results"))
                / "Data"
            )
            block_file = output_path / f"GOM_{block_number}.csv"

            if block_file.exists():
                import pandas as pd

                return pd.read_csv(block_file)
            else:
                logger.warning(f"Block data file not found: {block_file}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading block data: {e}")
            import pandas as pd

            return pd.DataFrame()

    def _load_lease_data(
        self, lease_number: str, cfg: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Load lease-specific data using lease data fetcher

        Args:
            lease_number: Lease number to load
            cfg: Configuration dictionary

        Returns:
            DataFrame with lease data
        """
        logger.info(f"Loading lease data for {lease_number}")

        # Prepare configuration for lease data fetcher
        lease_cfg = cfg or {}
        if "parameters" not in lease_cfg:
            lease_cfg["parameters"] = {
                "filepath": {"Well_APD_Default": str(self.data_path / "binary")}
            }

        # Create input group for lease fetcher
        input_group = {"bottom_lease": {"number": lease_number}}

        # Fetch lease data
        try:
            self.lease_data_fetcher.router(lease_cfg, input_group)

            # Load the generated CSV file
            output_path = (
                Path(lease_cfg.get("Analysis", {}).get("result_folder", "results"))
                / "Data"
            )
            lease_file = output_path / f"lease_{lease_number}.csv"

            if lease_file.exists():
                import pandas as pd

                return pd.read_csv(lease_file, low_memory=False)
            else:
                logger.warning(f"Lease data file not found: {lease_file}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading lease data: {e}")
            import pandas as pd

            return pd.DataFrame()

    def _load_comprehensive_data(
        self,
        block_number: Optional[str] = None,
        field_name: Optional[str] = None,
        lease_number: Optional[str] = None,
        block_df: Optional[pd.DataFrame] = None,
        lease_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Load comprehensive data from all sources

        Args:
            block_number: Optional block filter
            field_name: Optional field filter
            lease_number: Optional lease filter
            block_df: Pre-loaded block DataFrame
            lease_df: Pre-loaded lease DataFrame

        Returns:
            Raw data dictionary with all components
        """

        raw_data = {
            "blocks": [],
            "fields": [],
            "leases": [],
            "wells": [],
            "production": [],
            "block_df": block_df,
            "lease_df": lease_df,
        }

        # Process block data if available
        if block_df is not None and not block_df.empty:
            # Extract unique blocks
            if "Bottom Block Number" in block_df.columns:
                blocks = block_df["Bottom Block Number"].unique()
                for block in blocks:
                    raw_data["blocks"].append(
                        {"id": str(block), "number": str(block), "area": "GOM"}
                    )

            # Extract wells from block data
            if "API Well Number" in block_df.columns:
                for _, well_row in block_df.iterrows():
                    raw_data["wells"].append(
                        {
                            "api": well_row.get("API Well Number"),
                            "name": well_row.get("Well Name", "Unknown"),
                            "lease_number": well_row.get("Lease Number"),
                            "field_name": well_row.get("Field Name"),
                            "block_number": well_row.get("Bottom Block Number"),
                            "water_depth": well_row.get("Water Depth", 0),
                            "total_depth": well_row.get("Total Depth", 0),
                            "spud_date": well_row.get("Spud Date"),
                            "status": well_row.get("Status", "Unknown"),
                        }
                    )

        # Process lease data if available
        if lease_df is not None and not lease_df.empty:
            # Extract unique leases
            if "Lease Number" in lease_df.columns or "LEASE_NUMBER" in lease_df.columns:
                lease_col = (
                    "Lease Number"
                    if "Lease Number" in lease_df.columns
                    else "LEASE_NUMBER"
                )
                leases = lease_df[lease_col].unique()
                for lease in leases:
                    raw_data["leases"].append(
                        {
                            "id": str(lease),
                            "number": str(lease),
                            "field_id": lease_df[lease_df[lease_col] == lease]
                            .iloc[0]
                            .get("Field Name", "Unknown"),
                        }
                    )

            # Add well data from lease DataFrame if not already added
            if "API_WELL_NUMBER" in lease_df.columns and not raw_data["wells"]:
                for _, well_row in lease_df.iterrows():
                    raw_data["wells"].append(
                        {
                            "api": well_row.get("API_WELL_NUMBER"),
                            "name": well_row.get("WELL_NAME", "Unknown"),
                            "lease_number": well_row.get("LEASE_NUMBER"),
                            "field_name": well_row.get("FIELD_NAME"),
                            "block_number": well_row.get("BLOCK_NUMBER"),
                            "water_depth": well_row.get("WATER_DEPTH", 0),
                            "total_depth": well_row.get("TOTAL_DEPTH", 0),
                            "spud_date": well_row.get("SPUD_DATE"),
                            "status": well_row.get("STATUS", "Unknown"),
                        }
                    )

        # Load from binary files as fallback
        if not raw_data["wells"]:
            raw_data.update(
                self._load_from_binary(
                    self.data_path / "binary", block_number, field_name
                )
            )

        # Load production data
        raw_data["production"] = self._load_production_data(
            block_number, field_name, lease_number
        )

        return raw_data

    def _load_production_data(
        self,
        block_number: Optional[str] = None,
        field_name: Optional[str] = None,
        lease_number: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Load production data from binary files

        Args:
            block_number: Optional block filter
            field_name: Optional field filter
            lease_number: Optional lease filter

        Returns:
            List of production records
        """
        production_data = []

        binary_path = self.data_path / "binary"
        prod_file = binary_path / "production.bin"

        if prod_file.exists():
            try:
                with open(prod_file, "rb") as f:
                    all_production = pickle.load(f)

                    for prod_record in all_production:
                        # Apply filters
                        if (
                            lease_number
                            and prod_record.get("lease_number") != lease_number
                        ):
                            continue
                        if field_name and prod_record.get("field_name") != field_name:
                            continue
                        if block_number and block_number not in prod_record.get(
                            "area_block", ""
                        ):
                            continue

                        production_data.append(prod_record)

            except Exception as e:
                logger.error(f"Error loading production binary data: {e}")

        return production_data

    def _add_economic_data(self, hierarchy: Dict[str, Any]) -> None:
        """
        Add economic data to hierarchy

        Args:
            hierarchy: Hierarchical data structure
        """
        logger.info("Adding economic data to hierarchy")

        # Add economic calculations based on production
        # This would integrate with economic analysis modules
        pass

    def _load_well_data(
        self, api_number: str, cfg: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Load well-specific data using API data fetcher

        Args:
            api_number: API well number to load
            cfg: Configuration dictionary

        Returns:
            DataFrame with well data
        """
        logger.info(f"Loading well data for API {api_number}")

        # Prepare configuration for well data fetcher
        well_cfg = cfg or {}
        if "parameters" not in well_cfg:
            well_cfg["parameters"] = {
                "filepath": {"Well_APD_Default": str(self.data_path / "binary")}
            }

        # Create input for API fetcher
        input_api = {"api": api_number}

        # Fetch well data
        try:
            # The APIData class has a method to search by API number
            results = self.well_data_fetcher.get_api_data_from_input_bin_files(
                [api_number]
            )

            if results:
                # Convert results to DataFrame
                import pandas as pd

                well_df = pd.DataFrame()
                for file_path, df in results.items():
                    if not df.empty:
                        well_df = pd.concat([well_df, df], ignore_index=True)

                return well_df
            else:
                logger.warning(f"No data found for API {api_number}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading well data: {e}")
            import pandas as pd

            return pd.DataFrame()

    def fetch_wells_by_api_list(
        self, api_numbers: List[str], cfg: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Fetch data for multiple wells by API numbers

        Args:
            api_numbers: List of API well numbers
            cfg: Configuration dictionary

        Returns:
            DataFrame with combined well data
        """
        logger.info(f"Fetching data for {len(api_numbers)} wells")

        # Prepare configuration
        well_cfg = cfg or {}
        if "parameters" not in well_cfg:
            well_cfg["parameters"] = {
                "filepath": {"Well_APD_Default": str(self.data_path / "binary")}
            }

        # Initialize the API data fetcher with config if needed
        if well_cfg and not self.well_data_fetcher.bin_folder_path:
            self.well_data_fetcher._initialize_bin_path(well_cfg)

        try:
            # Fetch data for all API numbers
            results = self.well_data_fetcher.get_api_data_from_input_bin_files(
                api_numbers
            )

            if results:
                # Combine all results into single DataFrame
                import pandas as pd

                combined_df = pd.DataFrame()

                for file_path, df in results.items():
                    if not df.empty:
                        combined_df = pd.concat([combined_df, df], ignore_index=True)

                # Remove duplicates based on API number if present
                if "API Well Number" in combined_df.columns:
                    combined_df = combined_df.drop_duplicates(
                        subset=["API Well Number"]
                    )

                logger.info(
                    f"Successfully fetched data for {len(combined_df)} unique wells"
                )
                return combined_df
            else:
                logger.warning("No well data found for provided API numbers")
                return pd.DataFrame()

        except AttributeError:
            # If the method doesn't exist, fall back to individual fetching
            import pandas as pd

            combined_df = pd.DataFrame()

            for api_num in api_numbers:
                well_df = self._load_well_data(api_num, cfg)
                if not well_df.empty:
                    combined_df = pd.concat([combined_df, well_df], ignore_index=True)

            return combined_df
        except Exception as e:
            logger.error(f"Error fetching wells by API list: {e}")
            import pandas as pd

            return pd.DataFrame()
