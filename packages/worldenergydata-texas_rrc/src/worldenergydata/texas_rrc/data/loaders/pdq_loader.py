# ABOUTME: PDQ (Production Data Query) loader for Texas RRC production data
# ABOUTME: Handles ZIP archive extraction and specialized production data parsing

"""
PDQ Loader for Texas RRC Production Data.

Specialized loader for Production Data Query (PDQ) dump files from
Texas RRC, handling ZIP extraction and production-specific parsing.
"""

import logging
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

from .csv_loader import CSVLoader

logger = logging.getLogger(__name__)


class PDQLoader:
    """
    Loader for Texas RRC PDQ (Production Data Query) data.

    Handles:
    - ZIP file extraction
    - Multi-file archive processing
    - Production data normalization
    - District and county mapping
    """

    # Field mappings for PDQ production files
    PRODUCTION_FIELD_MAPPING = {
        "OG_LEASE_NO": "lease_number",
        "OG_OPER_NO": "operator_number",
        "OG_OPER_NAME": "operator_name",
        "OG_LEASE_NAME": "lease_name",
        "OG_FIELD_NO": "field_number",
        "OG_FIELD_NAME": "field_name",
        "OG_DIST_NO": "district",
        "OG_COUNTY_NO": "county_code",
        "OG_OIL_PROD": "oil_production",
        "OG_GAS_PROD": "gas_production",
        "OG_COND_PROD": "condensate",
        "OG_WATER_PROD": "water_production",
        "OG_CYCLE": "production_date",
        "OG_WELL_CNT": "well_count",
    }

    # Field mappings for PDQ well files
    WELL_FIELD_MAPPING = {
        "API_NO": "api_number",
        "WELL_NO": "well_number",
        "LEASE_NAME": "lease_name",
        "OPER_NO": "operator_number",
        "OPER_NAME": "operator_name",
        "FIELD_NAME": "field_name",
        "DIST_NO": "district",
        "COUNTY_NO": "county_code",
        "WELL_TYPE": "well_type",
        "WELL_STATUS": "well_status",
        "LATITUDE": "latitude",
        "LONGITUDE": "longitude",
        "TOTAL_DEPTH": "total_depth",
        "COMPL_DATE": "completion_date",
        "PLUG_DATE": "plug_date",
    }

    def __init__(self, csv_loader: Optional[CSVLoader] = None):
        """
        Initialize PDQ loader.

        Args:
            csv_loader: Optional pre-configured CSV loader
        """
        self.csv_loader = csv_loader or CSVLoader()
        self._files_processed = 0
        self._total_records = 0

    def load_zip(
        self,
        zip_path: Union[str, Path],
        data_type: str = "production",
    ) -> List[Dict[str, Any]]:
        """
        Load data from PDQ ZIP archive.

        Args:
            zip_path: Path to ZIP file
            data_type: Type of data (production, wells, permits)

        Returns:
            List of record dictionaries
        """
        zip_path = Path(zip_path)
        self._files_processed = 0
        self._total_records = 0

        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        field_mapping = self._get_field_mapping(data_type)
        records = []

        with zipfile.ZipFile(zip_path, "r") as zf:
            csv_files = [
                name
                for name in zf.namelist()
                if name.lower().endswith(".csv") or name.lower().endswith(".txt")
            ]

            if not csv_files:
                logger.warning(f"No CSV/TXT files found in {zip_path}")
                return records

            for csv_file in csv_files:
                try:
                    logger.info(f"Processing {csv_file} from archive")
                    with zf.open(csv_file) as f:
                        content = f.read().decode("utf-8", errors="replace")
                        file_records = self.csv_loader.load_from_string(
                            content, field_mapping
                        )
                        records.extend(file_records)
                        self._files_processed += 1
                        self._total_records += len(file_records)
                except Exception as e:
                    logger.error(f"Error processing {csv_file}: {e}")

        logger.info(
            f"Loaded {self._total_records} records from "
            f"{self._files_processed} files in {zip_path}"
        )
        return records

    def iter_zip_records(
        self,
        zip_path: Union[str, Path],
        data_type: str = "production",
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate over records from ZIP archive with streaming.

        Args:
            zip_path: Path to ZIP file
            data_type: Type of data

        Yields:
            Record dictionaries
        """
        zip_path = Path(zip_path)
        field_mapping = self._get_field_mapping(data_type)

        with zipfile.ZipFile(zip_path, "r") as zf:
            csv_files = [
                name
                for name in zf.namelist()
                if name.lower().endswith(".csv") or name.lower().endswith(".txt")
            ]

            for csv_file in csv_files:
                try:
                    with zf.open(csv_file) as f:
                        content = f.read().decode("utf-8", errors="replace")
                        for record in self._parse_csv_content(content, field_mapping):
                            yield record
                except Exception as e:
                    logger.error(f"Error processing {csv_file}: {e}")

    def _parse_csv_content(
        self,
        content: str,
        field_mapping: Dict[str, str],
    ) -> Iterator[Dict[str, Any]]:
        """
        Parse CSV content and yield records.

        Args:
            content: CSV content string
            field_mapping: Field name mapping

        Yields:
            Record dictionaries
        """
        import csv
        from io import StringIO

        f = StringIO(content)
        reader = csv.DictReader(f)

        for row in reader:
            record = {}
            for orig_name, value in row.items():
                if orig_name is None:
                    continue
                mapped_name = field_mapping.get(orig_name.upper(), orig_name.lower())
                record[mapped_name] = self._convert_value(mapped_name, value)
            yield record

    def _convert_value(self, field_name: str, value: str) -> Any:
        """
        Convert string value to appropriate type.

        Args:
            field_name: Field name
            value: String value

        Returns:
            Converted value
        """
        if value is None or value.strip() == "":
            return None

        value = value.strip()

        # Numeric fields
        numeric_fields = {
            "oil_production",
            "gas_production",
            "water_production",
            "condensate",
            "latitude",
            "longitude",
            "total_depth",
        }
        if field_name in numeric_fields:
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        # Integer fields
        integer_fields = {
            "district",
            "county_code",
            "lease_number",
            "operator_number",
            "field_number",
            "well_count",
        }
        if field_name in integer_fields:
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return None

        return value

    def _get_field_mapping(self, data_type: str) -> Dict[str, str]:
        """
        Get field mapping for data type.

        Args:
            data_type: Type of data

        Returns:
            Field mapping dictionary
        """
        mappings = {
            "production": self.PRODUCTION_FIELD_MAPPING,
            "wells": self.WELL_FIELD_MAPPING,
            "permits": self.WELL_FIELD_MAPPING,  # Similar to wells
        }
        return mappings.get(data_type, {})

    def load_from_bytes(
        self,
        zip_content: bytes,
        data_type: str = "production",
    ) -> List[Dict[str, Any]]:
        """
        Load data from ZIP content in memory.

        Args:
            zip_content: ZIP file content as bytes
            data_type: Type of data

        Returns:
            List of record dictionaries
        """
        field_mapping = self._get_field_mapping(data_type)
        records = []

        with zipfile.ZipFile(BytesIO(zip_content), "r") as zf:
            csv_files = [
                name
                for name in zf.namelist()
                if name.lower().endswith(".csv") or name.lower().endswith(".txt")
            ]

            for csv_file in csv_files:
                try:
                    with zf.open(csv_file) as f:
                        content = f.read().decode("utf-8", errors="replace")
                        file_records = self.csv_loader.load_from_string(
                            content, field_mapping
                        )
                        records.extend(file_records)
                except Exception as e:
                    logger.error(f"Error processing {csv_file}: {e}")

        return records

    @property
    def stats(self) -> Dict[str, Any]:
        """Get loader statistics."""
        return {
            "files_processed": self._files_processed,
            "total_records": self._total_records,
            "csv_loader_stats": self.csv_loader.stats,
        }


__all__ = ["PDQLoader"]
