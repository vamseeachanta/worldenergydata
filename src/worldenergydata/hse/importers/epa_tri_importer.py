# ABOUTME: Importer for EPA TRI (Toxics Release Inventory) data into ToxicRelease model.
# ABOUTME: Reads TRI basic data CSVs and persists facility-level chemical release records.

"""
EPA TRI Data Importer

Imports EPA Toxics Release Inventory (TRI) basic data CSV files into the
ToxicRelease database model. Handles field normalization from the TRI
reporting format to the standardized database schema.

TRI data represents annual facility-level reporting of toxic chemical
releases, not individual incident events. Each row is a facility + chemical
+ year combination.

Usage:
    uv run python -m worldenergydata.hse.importers.epa_tri_importer \
        --input data/modules/hse/raw/epa_tri/tri_basic_2023_oil_gas.csv
"""

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from worldenergydata.hse.database.models import Base, ToxicRelease

logger = logging.getLogger(__name__)

# TRI CSV column name mappings to database field names.
# TRI CSVs use various naming conventions across years.
COLUMN_MAPPINGS = {
    # Facility ID (Envirofacts uses "TRIFD")
    "TRIFD": "tri_facility_id",
    "TRIFID": "tri_facility_id",
    "TRI FACILITY ID": "tri_facility_id",
    "TRI_FACILITY_ID": "tri_facility_id",
    "FACILITY ID": "tri_facility_id",
    # Facility name
    "FACILITY NAME": "facility_name",
    "FACILITY_NAME": "facility_name",
    # Address
    "STREET ADDRESS": "street_address",
    "STREET_ADDRESS": "street_address",
    "FACILITY STREET": "street_address",
    # City
    "CITY": "city",
    "FACILITY CITY": "city",
    # State (Envirofacts uses "ST")
    "ST": "state",
    "STATE": "state",
    "FACILITY STATE": "state",
    # ZIP (Envirofacts uses "ZIP")
    "ZIP": "zip_code",
    "ZIP CODE": "zip_code",
    "ZIP_CODE": "zip_code",
    "FACILITY ZIP CODE": "zip_code",
    # County
    "COUNTY": "county",
    "FACILITY COUNTY": "county",
    # Latitude
    "LATITUDE": "latitude",
    "LAT": "latitude",
    "FACILITY LATITUDE": "latitude",
    # Longitude
    "LONGITUDE": "longitude",
    "LON": "longitude",
    "LONG": "longitude",
    "FACILITY LONGITUDE": "longitude",
    # Industry codes (Envirofacts uses "PRIMARY SIC" and "PRIMARY NAICS")
    "PRIMARY SIC": "industry_sector_code",
    "SIC CODE": "industry_sector_code",
    "SIC_CODE": "industry_sector_code",
    "PRIMARY SIC CODE": "industry_sector_code",
    "INDUSTRY SECTOR CODE": "industry_sector_code",
    "PRIMARY NAICS": "naics_code",
    "NAICS": "naics_code",
    "NAICS CODE": "naics_code",
    "NAICS_CODE": "naics_code",
    "PRIMARY NAICS CODE": "naics_code",
    # Chemical (Envirofacts uses "CHEMICAL" and "CAS#")
    "CHEMICAL": "chemical_name",
    "CHEMICAL NAME": "chemical_name",
    "CHEMICAL_NAME": "chemical_name",
    "CAS#": "cas_number",
    "CAS NUMBER": "cas_number",
    "CAS_NUMBER": "cas_number",
    "CAS #": "cas_number",
    "CAS CHEMNO": "cas_number",
    "CAS #/COMPOUND ID": "cas_number",
    # Release quantities (Envirofacts uses "5.1 - FUGITIVE AIR" format)
    "TOTAL RELEASES": "total_releases_pounds",
    "TOTAL_RELEASES": "total_releases_pounds",
    "ON-SITE RELEASE TOTAL": "total_releases_pounds",
    "TOTAL ON-SITE RELEASES": "total_releases_pounds",
    "TOTAL ON- AND OFF-SITE RELEASES": "total_releases_pounds",
    "5.1 - FUGITIVE AIR": "fugitive_air_pounds",
    "FUGITIVE AIR": "fugitive_air_pounds",
    "FUGITIVE_AIR": "fugitive_air_pounds",
    "ON-SITE - FUGITIVE AIR RELEASES": "fugitive_air_pounds",
    "5.2 - STACK AIR": "stack_air_pounds",
    "STACK AIR": "stack_air_pounds",
    "STACK_AIR": "stack_air_pounds",
    "ON-SITE - POINT SOURCE AIR RELEASES": "stack_air_pounds",
    "5.3 - WATER": "water_pounds",
    "WATER": "water_pounds",
    "ON-SITE - WATER DISCHARGES": "water_pounds",
    "5.4 - UNDERGROUND": "underground_injection_pounds",
    "UNDERGROUND INJECTION": "underground_injection_pounds",
    "UNDERGROUND_INJECTION": "underground_injection_pounds",
    "ON-SITE - UNDERGROUND INJECTION": "underground_injection_pounds",
    "5.5.2 - LAND TREATMENT": "land_treatment_pounds",
    "5.5 - LAND": "land_treatment_pounds",
    "LAND TREATMENT": "land_treatment_pounds",
    "LAND_TREATMENT": "land_treatment_pounds",
    "ON-SITE - LAND TREATMENT/APPLICATION FARMING": "land_treatment_pounds",
    # Year (Envirofacts uses "YEAR")
    "YEAR": "reporting_year",
    "REPORTING YEAR": "reporting_year",
    "REPORTING_YEAR": "reporting_year",
    "RY": "reporting_year",
}


class EPATRIImporter:
    """
    Importer for EPA TRI basic data CSV files.

    Reads TRI CSV files (as downloaded by EPATRIAcquirer) and persists
    records to the ToxicRelease database model.

    Handles:
    - Multiple column naming conventions across TRI reporting years
    - Type conversion (strings to floats for release quantities)
    - Duplicate detection via facility_id + chemical + year
    - Batch inserts for performance

    Attributes:
        session: SQLAlchemy database session
        batch_size: Number of records per database commit
    """

    def __init__(self, session: Session, batch_size: int = 500):
        self.session = session
        self.batch_size = batch_size
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def import_file(self, file_path: Path) -> Dict[str, int]:
        """
        Import a single TRI CSV file.

        Args:
            file_path: Path to TRI CSV file

        Returns:
            Dictionary with import statistics
        """
        file_path = Path(file_path)
        logger.info(f"Importing TRI data from: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"TRI file not found: {file_path}")

        df = pd.read_csv(file_path, low_memory=False)
        logger.info(f"Read {len(df)} records from {file_path.name}")

        # Normalize columns
        df = self._normalize_columns(df)

        # Process records in batches
        records = df.to_dict("records")
        batch = []

        for raw_record in records:
            normalized = self._normalize_record(raw_record)
            if normalized is None:
                self.error_count += 1
                continue

            if self._is_duplicate(normalized):
                self.skipped_count += 1
                continue

            model = self._to_model(normalized)
            if model:
                batch.append(model)

            if len(batch) >= self.batch_size:
                self._flush_batch(batch)
                batch = []

        # Flush remaining records
        if batch:
            self._flush_batch(batch)

        stats = {
            "imported_count": self.imported_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "total_records": len(records),
        }

        logger.info(
            f"Import complete: {stats['imported_count']} imported, "
            f"{stats['skipped_count']} skipped, "
            f"{stats['error_count']} errors"
        )

        return stats

    def import_directory(self, directory: Path) -> Dict[str, int]:
        """
        Import all TRI CSV files from a directory.

        Args:
            directory: Directory containing TRI CSV files

        Returns:
            Aggregated import statistics
        """
        directory = Path(directory)
        csv_files = sorted(directory.glob("tri_basic_*.csv"))

        if not csv_files:
            logger.warning(f"No TRI CSV files found in {directory}")
            return {
                "imported_count": 0,
                "skipped_count": 0,
                "error_count": 0,
                "total_records": 0,
            }

        logger.info(f"Found {len(csv_files)} TRI CSV files in {directory}")

        total_stats = {
            "imported_count": 0,
            "skipped_count": 0,
            "error_count": 0,
            "total_records": 0,
        }

        for csv_file in csv_files:
            # Skip combined files to avoid double-counting
            if "combined" in csv_file.name:
                continue

            try:
                stats = self.import_file(csv_file)
                for key in total_stats:
                    total_stats[key] += stats[key]
            except Exception as e:
                logger.error(f"Failed to import {csv_file.name}: {e}")

        return total_stats

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize DataFrame column names using the column mapping.

        Args:
            df: Raw DataFrame

        Returns:
            DataFrame with normalized column names
        """
        # First uppercase all columns for consistent matching
        upper_cols = {c: c.upper().strip() for c in df.columns}
        df = df.rename(columns=upper_cols)

        # Apply column mapping
        rename_map = {}
        for old_col in df.columns:
            if old_col in COLUMN_MAPPINGS:
                new_name = COLUMN_MAPPINGS[old_col]
                # Only map if we haven't already mapped to this target
                if new_name not in rename_map.values():
                    rename_map[old_col] = new_name

        df = df.rename(columns=rename_map)
        return df

    def _normalize_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize a single TRI record for database insertion.

        Args:
            record: Raw record dictionary

        Returns:
            Normalized record dictionary or None if invalid
        """
        # Required fields
        tri_facility_id = record.get("tri_facility_id")
        facility_name = record.get("facility_name")
        chemical_name = record.get("chemical_name")
        reporting_year = record.get("reporting_year")

        if not tri_facility_id or not facility_name or not chemical_name:
            return None

        normalized = {
            "tri_facility_id": str(tri_facility_id).strip(),
            "facility_name": str(facility_name).strip(),
            "chemical_name": str(chemical_name).strip(),
        }

        # Reporting year
        if reporting_year is not None:
            try:
                normalized["reporting_year"] = int(float(reporting_year))
            except (ValueError, TypeError):
                return None
        else:
            return None

        # Optional string fields
        for field in [
            "street_address",
            "city",
            "state",
            "zip_code",
            "county",
            "industry_sector_code",
            "naics_code",
            "cas_number",
        ]:
            value = record.get(field)
            if (
                value is not None
                and str(value).strip()
                and str(value).strip().lower() != "nan"
            ):
                normalized[field] = str(value).strip()
            else:
                normalized[field] = None

        # Float fields (release quantities and coordinates)
        for field in [
            "latitude",
            "longitude",
            "total_releases_pounds",
            "fugitive_air_pounds",
            "stack_air_pounds",
            "water_pounds",
            "underground_injection_pounds",
            "land_treatment_pounds",
        ]:
            value = record.get(field)
            normalized[field] = self._safe_float(value)

        return normalized

    def _safe_float(self, value: Any) -> Optional[float]:
        """Convert a value to float, returning None on failure."""
        if value is None:
            return None
        try:
            val = float(value)
            if pd.isna(val):
                return None
            return val
        except (ValueError, TypeError):
            return None

    def _is_duplicate(self, record: Dict[str, Any]) -> bool:
        """
        Check if a TRI record already exists in the database.

        Deduplication key: tri_facility_id + chemical_name + reporting_year

        Args:
            record: Normalized record dictionary

        Returns:
            True if duplicate exists
        """
        existing = (
            self.session.query(ToxicRelease)
            .filter(
                ToxicRelease.tri_facility_id == record["tri_facility_id"],
                ToxicRelease.chemical_name == record["chemical_name"],
                ToxicRelease.reporting_year == record["reporting_year"],
            )
            .first()
        )
        return existing is not None

    def _to_model(self, record: Dict[str, Any]) -> Optional[ToxicRelease]:
        """
        Convert a normalized record to a ToxicRelease model instance.

        Args:
            record: Normalized record dictionary

        Returns:
            ToxicRelease instance or None on error
        """
        try:
            return ToxicRelease(
                tri_facility_id=record["tri_facility_id"],
                facility_name=record["facility_name"],
                street_address=record.get("street_address"),
                city=record.get("city"),
                state=record.get("state"),
                zip_code=record.get("zip_code"),
                county=record.get("county"),
                latitude=record.get("latitude"),
                longitude=record.get("longitude"),
                industry_sector_code=record.get("industry_sector_code"),
                naics_code=record.get("naics_code"),
                chemical_name=record["chemical_name"],
                cas_number=record.get("cas_number"),
                total_releases_pounds=record.get("total_releases_pounds"),
                fugitive_air_pounds=record.get("fugitive_air_pounds"),
                stack_air_pounds=record.get("stack_air_pounds"),
                water_pounds=record.get("water_pounds"),
                underground_injection_pounds=record.get("underground_injection_pounds"),
                land_treatment_pounds=record.get("land_treatment_pounds"),
                reporting_year=record["reporting_year"],
            )
        except Exception as e:
            logger.error(f"Error creating ToxicRelease model: {e}")
            return None

    def _flush_batch(self, batch: List[ToxicRelease]) -> None:
        """
        Persist a batch of ToxicRelease records to the database.

        Args:
            batch: List of ToxicRelease model instances
        """
        try:
            self.session.add_all(batch)
            self.session.commit()
            self.imported_count += len(batch)
            logger.debug(f"Committed batch of {len(batch)} records")
        except Exception as e:
            logger.error(f"Batch commit failed: {e}")
            self.session.rollback()
            self.error_count += len(batch)


def main():
    """CLI entry point for EPA TRI data import."""
    parser = argparse.ArgumentParser(
        description="Import EPA TRI toxic release data into database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import a single file
  uv run python -m worldenergydata.hse.importers.epa_tri_importer \\
    --input data/modules/hse/raw/epa_tri/tri_basic_2023_oil_gas.csv

  # Import all files from directory
  uv run python -m worldenergydata.hse.importers.epa_tri_importer \\
    --input-dir data/modules/hse/raw/epa_tri

  # Dry run (validate only, no database writes)
  uv run python -m worldenergydata.hse.importers.epa_tri_importer \\
    --input data/modules/hse/raw/epa_tri/tri_basic_2023_oil_gas.csv --dry-run
        """,
    )

    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to a single TRI CSV file to import",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default=None,
        help="Directory containing TRI CSV files to import",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default="sqlite:///data/modules/hse/hse_database.db",
        help="SQLAlchemy database URL (default: SQLite)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data without writing to database",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Records per database commit (default: 500)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if not args.input and not args.input_dir:
        parser.error("Either --input or --input-dir is required")

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if args.dry_run:
        logger.info("DRY RUN mode - no database writes")
        # In dry-run mode, just validate the CSV
        input_path = Path(args.input) if args.input else Path(args.input_dir)
        if input_path.is_file():
            df = pd.read_csv(input_path, low_memory=False)
            print(f"File: {input_path}")
            print(f"Records: {len(df)}")
            print(f"Columns: {list(df.columns)}")
            print("Sample (first 3 rows):")
            print(df.head(3).to_string())
        return

    # Create database engine and session
    engine = create_engine(args.database_url)
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()

    try:
        importer = EPATRIImporter(session=session, batch_size=args.batch_size)

        if args.input:
            stats = importer.import_file(Path(args.input))
        else:
            stats = importer.import_directory(Path(args.input_dir))

        print("\nImport summary:")
        print(f"  Total records: {stats['total_records']}")
        print(f"  Imported: {stats['imported_count']}")
        print(f"  Skipped (duplicates): {stats['skipped_count']}")
        print(f"  Errors: {stats['error_count']}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
