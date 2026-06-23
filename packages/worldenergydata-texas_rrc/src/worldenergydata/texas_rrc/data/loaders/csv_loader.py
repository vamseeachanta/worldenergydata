# ABOUTME: CSV file loader for Texas RRC data files
# ABOUTME: Handles reading, parsing, and validating CSV data with type inference

"""
CSV Loader for Texas RRC Data Files.

Provides efficient loading and parsing of Texas RRC CSV files
with automatic type inference and validation.
"""

import csv
import logging
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

logger = logging.getLogger(__name__)


class CSVLoader:
    """
    Efficient CSV file loader for Texas RRC data.

    Features:
    - Streaming support for large files
    - Automatic type inference
    - Field mapping and renaming
    - Data validation hooks
    """

    # Default field type mappings
    NUMERIC_FIELDS = {
        "oil_production",
        "gas_production",
        "water_production",
        "condensate",
        "total_depth",
        "latitude",
        "longitude",
        "well_count",
    }

    INTEGER_FIELDS = {
        "district",
        "county_code",
        "lease_number",
        "operator_number",
        "permit_number",
        "field_number",
    }

    def __init__(
        self,
        encoding: str = "utf-8",
        delimiter: str = ",",
        quotechar: str = '"',
        skip_header: bool = False,
    ):
        """
        Initialize CSV loader.

        Args:
            encoding: File encoding (default utf-8)
            delimiter: Field delimiter (default comma)
            quotechar: Quote character for fields
            skip_header: Whether to skip the header row
        """
        self.encoding = encoding
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.skip_header = skip_header
        self._rows_processed = 0
        self._errors = []

    def load(
        self,
        file_path: Union[str, Path],
        field_mapping: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Load entire CSV file into memory.

        Args:
            file_path: Path to CSV file
            field_mapping: Optional field name mapping

        Returns:
            List of dictionaries, one per row
        """
        file_path = Path(file_path)
        self._rows_processed = 0
        self._errors = []

        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        records = []
        for record in self.iter_records(file_path, field_mapping):
            records.append(record)

        logger.info(f"Loaded {len(records)} records from {file_path}")
        return records

    def iter_records(
        self,
        file_path: Union[str, Path],
        field_mapping: Optional[Dict[str, str]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate over CSV records with streaming.

        Args:
            file_path: Path to CSV file
            field_mapping: Optional field name mapping

        Yields:
            Dictionary for each row
        """
        file_path = Path(file_path)

        with open(file_path, "r", encoding=self.encoding, errors="replace") as f:
            reader = csv.DictReader(
                f,
                delimiter=self.delimiter,
                quotechar=self.quotechar,
            )

            for row_num, row in enumerate(reader, start=1):
                try:
                    record = self._process_row(row, field_mapping)
                    self._rows_processed += 1
                    yield record
                except Exception as e:
                    self._errors.append(
                        {
                            "row": row_num,
                            "error": str(e),
                            "data": row,
                        }
                    )
                    logger.warning(f"Error processing row {row_num}: {e}")

    def _process_row(
        self,
        row: Dict[str, str],
        field_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Process a single CSV row.

        Args:
            row: Raw row dictionary
            field_mapping: Optional field name mapping

        Returns:
            Processed record dictionary
        """
        record: Dict[str, Any] = {}

        for field_name, value in row.items():
            # Apply field mapping
            if field_mapping and field_name in field_mapping:
                field_name = field_mapping[field_name]

            # Normalize field name
            normalized_name = self._normalize_field_name(field_name)

            # Convert value type
            record[normalized_name] = self._convert_value(normalized_name, value)

        return record

    def _normalize_field_name(self, field_name: str) -> str:
        """
        Normalize field name to snake_case.

        Args:
            field_name: Original field name

        Returns:
            Normalized field name
        """
        if not field_name:
            return "unknown"

        # Replace spaces and special characters
        normalized = field_name.strip().lower()
        normalized = normalized.replace(" ", "_")
        normalized = normalized.replace("-", "_")
        normalized = "".join(c if c.isalnum() or c == "_" else "" for c in normalized)

        # Remove consecutive underscores
        while "__" in normalized:
            normalized = normalized.replace("__", "_")

        return normalized.strip("_")

    def _convert_value(self, field_name: str, value: str) -> Any:
        """
        Convert string value to appropriate type.

        Args:
            field_name: Field name for type inference
            value: String value to convert

        Returns:
            Converted value
        """
        if value is None or value.strip() == "":
            return None

        value = value.strip()

        # Check for integer fields
        if field_name in self.INTEGER_FIELDS:
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return None

        # Check for numeric fields
        if field_name in self.NUMERIC_FIELDS:
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        return value

    def load_from_string(
        self,
        csv_content: str,
        field_mapping: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Load CSV from string content.

        Args:
            csv_content: CSV content as string
            field_mapping: Optional field name mapping

        Returns:
            List of record dictionaries
        """
        self._rows_processed = 0
        self._errors = []

        records = []
        f = StringIO(csv_content)
        reader = csv.DictReader(
            f,
            delimiter=self.delimiter,
            quotechar=self.quotechar,
        )

        for row_num, row in enumerate(reader, start=1):
            try:
                record = self._process_row(row, field_mapping)
                self._rows_processed += 1
                records.append(record)
            except Exception as e:
                self._errors.append(
                    {
                        "row": row_num,
                        "error": str(e),
                    }
                )
                logger.warning(f"Error processing row {row_num}: {e}")

        return records

    @property
    def stats(self) -> Dict[str, Any]:
        """Get loader statistics."""
        return {
            "rows_processed": self._rows_processed,
            "errors": len(self._errors),
            "error_details": self._errors[:10],  # First 10 errors
        }


__all__ = ["CSVLoader"]
