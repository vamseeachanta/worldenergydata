"""
BSEE Data Adapter for FDAS Integration

Translates BSEE data structures to FDAS-compatible formats, handling lease
mapping, development system classification, and production aggregation.

Author: WorldEnergyData Team
Date: 2025-10-03
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from ..core.config import classify_dev_system_by_depth


class AdapterError(Exception):
    """Raised when data adaptation fails"""

    pass


@dataclass
class LeaseMapping:
    """
    Represents a lease mapping from BSEE to FDAS structure.

    Attributes:
        lease_number: BSEE lease number (e.g., 'G09868')
        lease_name: Block name (e.g., 'Mississippi Canyon 941')
        dev_name: Development/complex name (e.g., 'Anchor')
        dev_system: Development system (dry, subsea15, subsea20)
        water_depth: Representative water depth in feet
    """

    lease_number: str
    lease_name: str
    dev_name: str
    dev_system: str
    water_depth: float

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            "LEASE_NUMBER": self.lease_number,
            "LEASE_NAME": self.lease_name,
            "DEV_NAME": self.dev_name,
            "DEV_SYSTEM": self.dev_system,
            "WATER_DEPTH": self.water_depth,
        }


class WellDataAdapter:
    """
    Adapts BSEE well_data.csv to FDAS requirements.

    Adds development system classification based on water depth and
    creates lease-to-development mapping.
    """

    def __init__(self, well_data_path: str):
        """
        Initialize well data adapter.

        Args:
            well_data_path: Path to BSEE well_data.csv
        """
        self.well_data_path = Path(well_data_path)
        self.well_data = None

    def load(self) -> pd.DataFrame:
        """
        Load well data from CSV.

        Returns:
            DataFrame with well data

        Raises:
            AdapterError: If file cannot be loaded
        """
        try:
            self.well_data = pd.read_csv(self.well_data_path)
            return self.well_data
        except Exception as e:
            raise AdapterError(f"Failed to load well data: {e}")

    def add_dev_system_classification(self) -> pd.DataFrame:
        """
        Add DEV_SYSTEM column based on water depth.

        Returns:
            DataFrame with DEV_SYSTEM column added

        Raises:
            AdapterError: If well data not loaded
        """
        if self.well_data is None:
            raise AdapterError("Well data not loaded. Call load() first.")

        # Add classification
        self.well_data["DEV_SYSTEM"] = self.well_data["WATER_DEPTH"].apply(
            classify_dev_system_by_depth
        )

        return self.well_data

    def create_lease_mapping(self) -> List[LeaseMapping]:
        """
        Create lease mapping from well data.

        Returns:
            List of LeaseMapping objects

        Raises:
            AdapterError: If required columns missing
        """
        if self.well_data is None:
            raise AdapterError("Well data not loaded. Call load() first.")

        required_cols = ["LEASE_NUMBER", "COMPLEX_ID_NUMBER", "WATER_DEPTH"]
        missing = [col for col in required_cols if col not in self.well_data.columns]
        if missing:
            raise AdapterError(f"Missing required columns: {missing}")

        # Group by lease and get representative values
        grouped = (
            self.well_data.groupby("LEASE_NUMBER")
            .agg(
                {
                    "COMPLEX_ID_NUMBER": "first",
                    "WATER_DEPTH": "mean",
                    "DEV_SYSTEM": lambda x: (
                        x.mode()[0] if len(x.mode()) > 0 else "unknown"
                    ),
                }
            )
            .reset_index()
        )

        mappings = []
        for _, row in grouped.iterrows():
            mapping = LeaseMapping(
                lease_number=row["LEASE_NUMBER"],
                lease_name=f"Lease {row['LEASE_NUMBER']}",  # Placeholder
                dev_name=str(row["COMPLEX_ID_NUMBER"]),
                dev_system=row["DEV_SYSTEM"],
                water_depth=float(row["WATER_DEPTH"]),
            )
            mappings.append(mapping)

        return mappings

    def save_enhanced_well_data(self, output_path: str) -> None:
        """
        Save enhanced well data with DEV_SYSTEM column.

        Args:
            output_path: Path for output CSV

        Raises:
            AdapterError: If well data not enhanced
        """
        if self.well_data is None or "DEV_SYSTEM" not in self.well_data.columns:
            raise AdapterError(
                "Well data not enhanced. Call add_dev_system_classification() first."
            )

        try:
            self.well_data.to_csv(output_path, index=False)
        except Exception as e:
            raise AdapterError(f"Failed to save enhanced well data: {e}")


class ProductionAdapter:
    """
    Adapts BSEE production.csv to FDAS chronological format.

    Aggregates monthly production by lease/development and adds
    required metadata columns.
    """

    def __init__(
        self, production_path: str, lease_mappings: Optional[List[LeaseMapping]] = None
    ):
        """
        Initialize production adapter.

        Args:
            production_path: Path to BSEE production.csv
            lease_mappings: Optional list of LeaseMapping objects
        """
        self.production_path = Path(production_path)
        self.production_data = None
        self.lease_mappings = lease_mappings or []
        self._lease_lookup = {m.lease_number: m for m in self.lease_mappings}

    def load(self) -> pd.DataFrame:
        """
        Load production data from CSV.

        Returns:
            DataFrame with production data

        Raises:
            AdapterError: If file cannot be loaded
        """
        try:
            self.production_data = pd.read_csv(self.production_path)
            return self.production_data
        except Exception as e:
            raise AdapterError(f"Failed to load production data: {e}")

    def enhance_with_lease_info(self) -> pd.DataFrame:
        """
        Add DEV_NAME and LEASE_NAME columns from mappings.

        Returns:
            Enhanced DataFrame

        Raises:
            AdapterError: If production data not loaded
        """
        if self.production_data is None:
            raise AdapterError("Production data not loaded. Call load() first.")

        # Add columns from lease mapping
        def add_lease_info(row):
            lease_num = row.get("LEASE_NUMBER")
            if lease_num in self._lease_lookup:
                mapping = self._lease_lookup[lease_num]
                return pd.Series(
                    {
                        "DEV_NAME": mapping.dev_name,
                        "LEASE_NAME": mapping.lease_name,
                        "DEV_SYSTEM": mapping.dev_system,
                    }
                )
            return pd.Series(
                {
                    "DEV_NAME": None,
                    "LEASE_NAME": None,
                    "DEV_SYSTEM": "unknown",
                }
            )

        enhanced = self.production_data.join(
            self.production_data.apply(add_lease_info, axis=1)
        )

        self.production_data = enhanced
        return enhanced

    def aggregate_monthly(self, by: str = "DEV_NAME") -> pd.DataFrame:
        """
        Aggregate production to monthly totals.

        Args:
            by: Grouping level ('DEV_NAME', 'LEASE_NUMBER', or 'API_WELL_NUMBER')

        Returns:
            Monthly aggregated DataFrame

        Raises:
            AdapterError: If production data not loaded or missing columns
        """
        if self.production_data is None:
            raise AdapterError("Production data not loaded. Call load() first.")

        required_cols = [by, "PROD_DATE", "OIL_VOLUME", "WATER_VOLUME"]
        missing = [
            col for col in required_cols if col not in self.production_data.columns
        ]
        if missing:
            raise AdapterError(f"Missing required columns: {missing}")

        # Convert date to year-month
        self.production_data["YEAR_MONTH"] = pd.to_datetime(
            self.production_data["PROD_DATE"]
        ).dt.to_period("M")

        # Aggregate
        aggregated = (
            self.production_data.groupby([by, "YEAR_MONTH"])
            .agg(
                {
                    "OIL_VOLUME": "sum",
                    "WATER_VOLUME": "sum",
                    "GAS_VOLUME": (
                        "sum"
                        if "GAS_VOLUME" in self.production_data.columns
                        else lambda x: 0
                    ),
                }
            )
            .reset_index()
        )

        # Rename to FDAS convention
        aggregated = aggregated.rename(
            columns={
                "OIL_VOLUME": "MONTHLY_OIL_VOLUME",
                "WATER_VOLUME": "MONTHLY_WATER_VOLUME",
                "GAS_VOLUME": "MONTHLY_GAS_VOLUME",
            }
        )

        return aggregated

    def create_chronological_analysis(self, dev_name: str) -> pd.DataFrame:
        """
        Create FDAS-compatible chronological lease analysis.

        Args:
            dev_name: Development name to filter

        Returns:
            DataFrame in chronological format

        Raises:
            AdapterError: If production data not prepared
        """
        if (
            self.production_data is None
            or "DEV_NAME" not in self.production_data.columns
        ):
            raise AdapterError(
                "Production data not enhanced. Call enhance_with_lease_info() first."
            )

        # Filter to development
        dev_data = self.production_data[
            self.production_data["DEV_NAME"] == dev_name
        ].copy()

        if len(dev_data) == 0:
            raise AdapterError(f"No production data found for development: {dev_name}")

        # Aggregate monthly
        monthly = self.aggregate_monthly(by="DEV_NAME")
        monthly = monthly[monthly["DEV_NAME"] == dev_name]

        return monthly


class BseeAdapter:
    """
    Main BSEE to FDAS adapter that orchestrates all conversions.

    Provides a unified interface for loading BSEE data and transforming
    it to FDAS-compatible formats.
    """

    def __init__(self, bsee_data_dir: str):
        """
        Initialize BSEE adapter.

        Args:
            bsee_data_dir: Root directory of BSEE data files
        """
        self.data_dir = Path(bsee_data_dir)
        self.well_adapter = None
        self.production_adapter = None
        self.lease_mappings = []

    def load_all(self) -> Dict[str, pd.DataFrame]:
        """
        Load all BSEE data files.

        Returns:
            Dictionary of DataFrames by data type

        Raises:
            AdapterError: If any file fails to load
        """
        data = {}

        # Load well data
        well_path = self.data_dir / "wells" / "well_data.csv"
        if well_path.exists():
            self.well_adapter = WellDataAdapter(str(well_path))
            data["wells"] = self.well_adapter.load()
            self.well_adapter.add_dev_system_classification()
            self.lease_mappings = self.well_adapter.create_lease_mapping()
        else:
            raise AdapterError(f"Well data not found: {well_path}")

        # Load production data
        prod_path = self.data_dir / "production" / "production.csv"
        if prod_path.exists():
            self.production_adapter = ProductionAdapter(
                str(prod_path), self.lease_mappings
            )
            data["production"] = self.production_adapter.load()
            self.production_adapter.enhance_with_lease_info()
        else:
            raise AdapterError(f"Production data not found: {prod_path}")

        return data

    def get_lease_mappings_df(self) -> pd.DataFrame:
        """
        Get lease mappings as DataFrame.

        Returns:
            DataFrame with lease mapping information
        """
        if not self.lease_mappings:
            raise AdapterError("Lease mappings not created. Call load_all() first.")

        return pd.DataFrame([m.to_dict() for m in self.lease_mappings])

    def export_lease_mapping_csv(self, output_path: str) -> None:
        """
        Export lease mapping to CSV file.

        Args:
            output_path: Path for output CSV
        """
        mapping_df = self.get_lease_mappings_df()
        mapping_df.to_csv(output_path, index=False)

    def get_development_production(self, dev_name: str) -> pd.DataFrame:
        """
        Get monthly production for a development.

        Args:
            dev_name: Development name

        Returns:
            Monthly production DataFrame
        """
        if self.production_adapter is None:
            raise AdapterError(
                "Production adapter not initialized. Call load_all() first."
            )

        return self.production_adapter.create_chronological_analysis(dev_name)
