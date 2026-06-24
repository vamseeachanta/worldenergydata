# ABOUTME: Importer for BSEE incident investigation raw data (tab-delimited txt)
# ABOUTME: Reads mv_acc_investigations.txt and maps to HSEIncident model

"""
BSEE Incident Investigation Importer

Reads the BSEE incident investigation raw data file (mv_acc_investigations.txt),
a tab-delimited text file with columns:
    DATE_OCCURRED, MILITARY_TIME, LEASE_NUMBER, AREA_BLOCK,
    ACCIDENT_TYPE, PANEL_DISTRICT, STATUS

Maps records to the HSEIncident database model.

Usage:
    # As module — use DataResolver so the path resolves correctly whether
    # data/ is in-repo or symlinked to /mnt/ace per #359.
    from worldenergydata.common.data_resolver import get_module_data
    from worldenergydata.hse.importers.bsee_incinv_importer import BSEEIncInvImporter

    importer = BSEEIncInvImporter(data_dir=get_module_data("hse") / "raw/bsee")
    records = importer.load()
    logger.info(f"Loaded {len(records)} incident investigation records")

    # CLI
    uv run python -m worldenergydata.hse.importers.bsee_incinv_importer \\
        --data-dir "$(get_module_data hse)/raw/bsee"
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from worldenergydata.common import get_logger

logger = get_logger(__name__)

# File location within the extracted BSEE data directory
INCINV_SUBDIR = "IncInvRawData"
INCINV_FILENAME = "mv_acc_investigations.txt"

# Accident type mapping from BSEE codes to HSEIncident incident_type values
ACCIDENT_TYPE_MAP: Dict[str, str] = {
    "pollution": "spill",
    "fire": "equipment_failure",
    "explosion": "equipment_failure",
    "blowout": "equipment_failure",
    "fatality": "injury",
    "injury": "injury",
    "collision": "equipment_failure",
    "loss of well control": "equipment_failure",
    "crane": "equipment_failure",
    "falling object": "injury",
    "h2s release": "spill",
    "gas release": "spill",
    "structural damage": "equipment_failure",
    "capsize": "equipment_failure",
    "helicopter": "equipment_failure",
    "other": "equipment_failure",
}

# Severity mapping: derive from accident type when explicit severity is absent
ACCIDENT_SEVERITY_MAP: Dict[str, str] = {
    "fatality": "fatality",
    "injury": "recordable",
    "pollution": "minor",
    "fire": "recordable",
    "explosion": "recordable",
    "blowout": "lost_time",
    "collision": "recordable",
    "loss of well control": "lost_time",
    "crane": "recordable",
    "falling object": "recordable",
    "h2s release": "recordable",
    "gas release": "near_miss",
    "structural damage": "recordable",
    "capsize": "lost_time",
    "helicopter": "recordable",
    "other": "minor",
}


class BSEEIncInvImporter:
    """
    Importer for BSEE incident investigation raw data.

    Reads the tab-delimited mv_acc_investigations.txt file and produces
    normalized records compatible with the HSEIncident model.

    Attributes:
        data_dir: Root directory containing BSEE raw data subdirectories.
    """

    def __init__(self, data_dir: str):
        """
        Initialize the importer.

        Args:
            data_dir: Path to the BSEE raw data directory (parent of IncInvRawData/).
        """
        self.data_dir = Path(data_dir)
        self.file_path = self.data_dir / INCINV_SUBDIR / INCINV_FILENAME

    def load(self) -> List[Dict[str, Any]]:
        """
        Load and normalize incident investigation records.

        Reads the tab-delimited file, parses dates, maps accident types
        to HSEIncident fields, and generates composite IDs.

        Returns:
            List of normalized record dictionaries.

        Raises:
            FileNotFoundError: If the data file does not exist.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"Incident investigation file not found: {self.file_path}"
            )

        logger.info("Reading incident investigations from %s", self.file_path)

        df = pd.read_csv(
            self.file_path,
            sep=",",
            dtype=str,
            encoding="latin-1",
            quotechar='"',
        )

        # Strip whitespace from column names and values
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].str.strip()

        logger.info("Read %d raw records", len(df))

        records = []
        for idx, row in df.iterrows():
            record = self._normalize_row(row, idx)
            if record is not None:
                records.append(record)

        logger.info("Normalized %d records (from %d raw)", len(records), len(df))
        return records

    def _normalize_row(
        self,
        row: pd.Series,
        row_index: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize a single raw row to HSEIncident-compatible dictionary.

        Args:
            row: Pandas Series containing raw column values.
            row_index: Row index for generating composite ID.

        Returns:
            Normalized dictionary, or None if the row cannot be parsed.
        """
        # Parse date
        incident_date = self._parse_date(
            row.get("DATE_OCCURRED"),
            row.get("MILITARY_TIME"),
        )
        if incident_date is None:
            logger.warning(
                "Skipping row %d: cannot parse date '%s'",
                row_index,
                row.get("DATE_OCCURRED"),
            )
            return None

        # Extract fields
        lease_number = row.get("LEASE_NUMBER", "")
        area_block = row.get("AREA_BLOCK", "")
        accident_type_raw = row.get("ACCIDENT_TYPE", "").lower().strip("- ").strip()
        panel_district = row.get("PANEL_DISTRICT", "")
        status = row.get("STATUS", "")

        # Generate composite ID: INCINV-{date}-{lease}-{index}
        date_str = incident_date.strftime("%Y%m%d")
        bsee_incident_id = f"INCINV-{date_str}-{lease_number}-{row_index}"

        # Map accident type
        incident_type = self._map_accident_type(accident_type_raw)
        severity = self._map_severity(accident_type_raw)

        return {
            "bsee_incident_id": bsee_incident_id,
            "incident_date": incident_date,
            "operator": "BSEE Reported",  # Not in raw data
            "lease_number": lease_number if lease_number else None,
            "block_number": area_block if area_block else None,
            "incident_type": incident_type,
            "severity": severity,
            "description": (
                f"Accident type: {accident_type_raw}; "
                f"District: {panel_district}; "
                f"Area/Block: {area_block}"
            ),
            "investigation_status": status if status else None,
        }

    def _parse_date(
        self,
        date_str: Optional[str],
        time_str: Optional[str],
    ) -> Optional[datetime]:
        """
        Parse BSEE date and time strings into datetime.

        Handles M/D/YYYY format from the raw data.

        Args:
            date_str: Date string in M/D/YYYY format.
            time_str: Military time string in H:MM format (optional).

        Returns:
            Parsed datetime object, or None if parsing fails.
        """
        if not date_str or date_str == "nan":
            return None

        try:
            dt = datetime.strptime(date_str.strip(), "%m/%d/%Y")
        except ValueError:
            try:
                dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            except ValueError:
                return None

        # Attempt to add time component
        if time_str and time_str != "nan":
            try:
                time_str = time_str.strip().strip('"')
                parts = time_str.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                dt = dt.replace(hour=hour, minute=minute)
            except (ValueError, IndexError):
                pass  # Keep date without time

        return dt

    def _map_accident_type(self, raw_type: str) -> str:
        """
        Map raw BSEE accident type to HSEIncident incident_type enum.

        Args:
            raw_type: Lowercase, stripped accident type from raw data.

        Returns:
            One of: injury, spill, equipment_failure, violation.
        """
        for keyword, mapped_type in ACCIDENT_TYPE_MAP.items():
            if keyword in raw_type:
                return mapped_type
        return "equipment_failure"  # Default for unknown types

    def _map_severity(self, raw_type: str) -> str:
        """
        Derive severity from accident type.

        Args:
            raw_type: Lowercase, stripped accident type from raw data.

        Returns:
            One of: fatality, lost_time, recordable, near_miss, minor.
        """
        for keyword, severity in ACCIDENT_SEVERITY_MAP.items():
            if keyword in raw_type:
                return severity
        return "minor"  # Default for unknown types

    def summary(self) -> Dict[str, Any]:
        """
        Generate summary statistics for the loaded data.

        Returns:
            Dictionary with count, date range, and type breakdown.
        """
        records = self.load()
        if not records:
            return {"count": 0}

        dates = [r["incident_date"] for r in records if r.get("incident_date")]
        types = {}
        for r in records:
            t = r.get("incident_type", "unknown")
            types[t] = types.get(t, 0) + 1

        return {
            "count": len(records),
            "date_min": min(dates).isoformat() if dates else None,
            "date_max": max(dates).isoformat() if dates else None,
            "incident_types": types,
        }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Import BSEE incident investigation raw data",
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing BSEE raw data (parent of IncInvRawData/)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        default=False,
        help="Print summary statistics instead of full records",
    )
    return parser


def main(argv: Optional[list] = None) -> None:
    """CLI entry point for BSEE incident investigation import."""
    parser = build_parser()
    args = parser.parse_args(argv)

    importer = BSEEIncInvImporter(data_dir=args.data_dir)

    if args.summary:
        stats = importer.summary()
        logger.info("Incident Investigation Summary:")
        for key, value in stats.items():
            logger.info("  %s: %s", key, value)
    else:
        records = importer.load()
        logger.info(
            "Loaded %d incident investigation records from %s",
            len(records),
            args.data_dir,
        )

        # Print first few records as sample
        for record in records[:3]:
            logger.info("  Sample: %s", record)

    logger.info("BSEE incident investigation import complete")


if __name__ == "__main__":
    main()
