# ABOUTME: Importer for BSEE INCs (Incidents of Non-Compliance) raw data
# ABOUTME: Reads tab-delimited INC files and maps to HSEIncident/ViolationIncident models

"""
BSEE INCs (Incidents of Non-Compliance) Importer

Reads BSEE INC raw data files from the INCSRawData directory. The primary
file is mv_incs_by_oper.txt (operator-level INC aggregates), along with
regional breakdowns for warnings, component shut-ins, and facility shut-ins.

Primary file columns (mv_incs_by_oper.txt):
    INC_DATE, REGION, BUS_ASC_CODE, BUS_ASC_NAME,
    WARNING_INCS, COMP_SHUTIN_INCS, FAC_SHUTIN_INCS

Usage:
    # As module
    from worldenergydata.hse.importers.bsee_incs_importer import BSEEINCSImporter

    importer = BSEEINCSImporter(data_dir="data/modules/hse/raw/bsee")
    records = importer.load()
    logger.info(f"Loaded {len(records)} INC records")

    # CLI
    uv run python -m worldenergydata.hse.importers.bsee_incs_importer \\
        --data-dir data/modules/hse/raw/bsee
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from worldenergydata.common import get_logger

logger = get_logger(__name__)

# File location within the extracted BSEE data directory
INCS_SUBDIR = "INCSRawData"
INCS_PRIMARY_FILE = "mv_incs_by_oper.txt"

# Regional INC files for detailed breakdowns
INCS_REGIONAL_FILES: Dict[str, str] = {
    "warnings_alaska": "mv_incs_warnings_alaska.txt",
    "warnings_gulf": "mv_incs_warnings_gulf.txt",
    "warnings_pacific": "mv_incs_warnings_pacific.txt",
    "shutins_alaska": "mv_incs_shutins_alaska.txt",
    "shutins_gulf": "mv_incs_shutins_gulf.txt",
    "shutins_pacific": "mv_incs_shutins_pacific.txt",
    "fac_shutins_alaska": "mv_incs_fac_shutins_alaska.txt",
    "fac_shutins_gulf": "mv_incs_fac_shutins_gulf.txt",
    "fac_shutins_pacific": "mv_incs_fac_shutins_pacific.txt",
    "inspections_alaska": "mv_incs_inspections_alaska.txt",
    "inspections_gulf": "mv_incs_inspections_gulf.txt",
    "inspections_pacific": "mv_incs_inspections_pacific.txt",
}

# Region code mapping
REGION_MAP: Dict[str, str] = {
    "G": "Gulf of Mexico",
    "A": "Alaska",
    "P": "Pacific",
}


class BSEEINCSImporter:
    """
    Importer for BSEE INCs (Incidents of Non-Compliance) raw data.

    Reads the tab-delimited INC files and produces normalized records
    compatible with the HSEIncident and ViolationIncident models.

    Each row in mv_incs_by_oper.txt represents a single INC event date
    for an operator, with counts of warnings, component shut-ins, and
    facility shut-ins. Each non-zero count category is emitted as a
    separate violation record.

    Attributes:
        data_dir: Root directory containing BSEE raw data subdirectories.
    """

    def __init__(self, data_dir: str):
        """
        Initialize the importer.

        Args:
            data_dir: Path to the BSEE raw data directory (parent of INCSRawData/).
        """
        self.data_dir = Path(data_dir)
        self.incs_dir = self.data_dir / INCS_SUBDIR

    def load(self) -> List[Dict[str, Any]]:
        """
        Load and normalize INC records from the primary operator file.

        Reads mv_incs_by_oper.txt, parses each row, and emits one
        normalized record per INC category (warning, component shut-in,
        facility shut-in) that has a non-zero count.

        Returns:
            List of normalized record dictionaries.

        Raises:
            FileNotFoundError: If the data file does not exist.
        """
        file_path = self.incs_dir / INCS_PRIMARY_FILE

        if not file_path.exists():
            raise FileNotFoundError(f"INCs operator file not found: {file_path}")

        logger.info("Reading INCs from %s", file_path)

        df = pd.read_csv(
            file_path,
            sep=",",
            dtype=str,
            encoding="latin-1",
            quotechar='"',
        )

        # Strip whitespace from column names and values
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].str.strip()

        logger.info("Read %d raw INC rows", len(df))

        records = []
        for idx, row in df.iterrows():
            row_records = self._normalize_row(row, idx)
            records.extend(row_records)

        logger.info(
            "Normalized %d violation records (from %d raw rows)",
            len(records),
            len(df),
        )
        return records

    def _normalize_row(
        self,
        row: pd.Series,
        row_index: int,
    ) -> List[Dict[str, Any]]:
        """
        Normalize a single INC row into one or more violation records.

        Each row can produce up to 3 records: one per non-zero INC
        category (warnings, component shut-ins, facility shut-ins).

        Args:
            row: Pandas Series containing raw column values.
            row_index: Row index for generating composite ID.

        Returns:
            List of normalized dictionaries (0-3 records per row).
        """
        # Parse date
        incident_date = self._parse_date(row.get("INC_DATE"))
        if incident_date is None:
            logger.warning(
                "Skipping row %d: cannot parse date '%s'",
                row_index,
                row.get("INC_DATE"),
            )
            return []

        # Extract common fields
        region_code = row.get("REGION", "").strip()
        region_name = REGION_MAP.get(region_code, region_code)
        bus_asc_code = row.get("BUS_ASC_CODE", "").strip()
        operator = row.get("BUS_ASC_NAME", "").strip()

        # Parse INC counts
        warning_incs = self._safe_int(row.get("WARNING_INCS"))
        comp_shutin_incs = self._safe_int(row.get("COMP_SHUTIN_INCS"))
        fac_shutin_incs = self._safe_int(row.get("FAC_SHUTIN_INCS"))

        date_str = incident_date.strftime("%Y%m%d")
        records = []

        # Emit one record per non-zero INC category
        inc_categories = [
            ("WARNING", warning_incs, "Warning INC"),
            ("COMP_SHUTIN", comp_shutin_incs, "Component Shut-in INC"),
            ("FAC_SHUTIN", fac_shutin_incs, "Facility Shut-in INC"),
        ]

        for suffix, count, label in inc_categories:
            if count > 0:
                bsee_incident_id = f"INC-{date_str}-{bus_asc_code}-{suffix}-{row_index}"
                records.append(
                    {
                        "bsee_incident_id": bsee_incident_id,
                        "incident_date": incident_date,
                        "operator": operator if operator else "Unknown",
                        "incident_type": "violation",
                        "severity": "minor",
                        "description": (
                            f"{label}: {count} incident(s); "
                            f"Region: {region_name}; "
                            f"Operator code: {bus_asc_code}"
                        ),
                        "inc_number": None,
                        "violation_type": suffix.lower(),
                        "region": region_name,
                        "inc_count": count,
                    }
                )

        return records

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse BSEE INC date string into datetime.

        Handles formats like "M/D/YYYY H:MM:SS AM/PM" from the raw data.

        Args:
            date_str: Date string from the raw data.

        Returns:
            Parsed datetime object, or None if parsing fails.
        """
        if not date_str or date_str == "nan":
            return None

        date_str = date_str.strip()

        # Try common formats in order of likelihood
        formats = [
            "%m/%d/%Y %I:%M:%S %p",  # 8/21/2020 2:12:53 PM
            "%m/%d/%Y %H:%M:%S",  # 8/21/2020 14:12:53
            "%m/%d/%Y",  # 8/21/2020
            "%Y-%m-%d",  # 2020-08-21
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.debug("Could not parse date: '%s'", date_str)
        return None

    @staticmethod
    def _safe_int(value: Optional[str]) -> int:
        """
        Safely convert string to integer, defaulting to 0.

        Args:
            value: String representation of an integer.

        Returns:
            Parsed integer, or 0 if parsing fails.
        """
        if not value or value == "nan":
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    def load_regional(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load regional breakdown files.

        Reads all available regional INC files and returns them
        grouped by region/type.

        Returns:
            Dictionary mapping regional file keys to lists of records.
        """
        results: Dict[str, List[Dict[str, Any]]] = {}

        for key, filename in INCS_REGIONAL_FILES.items():
            file_path = self.incs_dir / filename
            if not file_path.exists():
                logger.debug("Regional file not found: %s", file_path)
                continue

            try:
                df = pd.read_csv(
                    file_path,
                    sep=",",
                    dtype=str,
                    encoding="latin-1",
                    quotechar='"',
                )
                df.columns = df.columns.str.strip()
                records = df.to_dict("records")
                results[key] = records
                logger.info(
                    "Loaded %d records from %s",
                    len(records),
                    filename,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to read regional file %s: %s",
                    filename,
                    exc,
                )

        return results

    def summary(self) -> Dict[str, Any]:
        """
        Generate summary statistics for the loaded INC data.

        Returns:
            Dictionary with count, date range, operator count, and
            regional breakdown.
        """
        records = self.load()
        if not records:
            return {"count": 0}

        dates = [r["incident_date"] for r in records if r.get("incident_date")]
        operators = {r.get("operator") for r in records if r.get("operator")}
        regions = {}
        violation_types = {}

        for r in records:
            region = r.get("region", "unknown")
            regions[region] = regions.get(region, 0) + 1
            vtype = r.get("violation_type", "unknown")
            violation_types[vtype] = violation_types.get(vtype, 0) + 1

        return {
            "count": len(records),
            "date_min": min(dates).isoformat() if dates else None,
            "date_max": max(dates).isoformat() if dates else None,
            "operator_count": len(operators),
            "regions": regions,
            "violation_types": violation_types,
        }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Import BSEE INCs (Incidents of Non-Compliance) raw data",
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing BSEE raw data (parent of INCSRawData/)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        default=False,
        help="Print summary statistics instead of full records",
    )
    parser.add_argument(
        "--include-regional",
        action="store_true",
        default=False,
        help="Also load regional breakdown files",
    )
    return parser


def main(argv: Optional[list] = None) -> None:
    """CLI entry point for BSEE INCs import."""
    parser = build_parser()
    args = parser.parse_args(argv)

    importer = BSEEINCSImporter(data_dir=args.data_dir)

    if args.summary:
        stats = importer.summary()
        logger.info("INCs Summary:")
        for key, value in stats.items():
            logger.info("  %s: %s", key, value)
    else:
        records = importer.load()
        logger.info(
            "Loaded %d INC records from %s",
            len(records),
            args.data_dir,
        )

        # Print first few records as sample
        for record in records[:3]:
            logger.info("  Sample: %s", record)

    if args.include_regional:
        logger.info("Loading regional breakdown files...")
        regional = importer.load_regional()
        for key, recs in regional.items():
            logger.info("  %s: %d records", key, len(recs))

    logger.info("BSEE INCs import complete")


if __name__ == "__main__":
    main()
