"""Loader for curated LNG terminal seed data from CSV/Parquet files.

This module provides functionality to load terminal data from curated seed
datasets and convert them into validated LNGTerminal model instances.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from ..constants import (
    SourceReliability,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from ..models.data_quality import SourceCitation
from ..models.design import MarineInfrastructure, StorageSpec
from ..models.terminal import LNGTerminal

logger = logging.getLogger(__name__)


class TerminalLoader:
    """Loads LNG terminal data from CSV or Parquet files.

    This loader reads curated seed datasets and converts them into validated
    LNGTerminal model instances with proper type conversion and validation.

    Attributes:
        file_path: Path to the data file (CSV or Parquet).
        source_name: Name of the data source for citation tracking.
    """

    def __init__(
        self,
        file_path: str | Path,
        source_name: str = "curated_seed_dataset",
    ) -> None:
        """Initialize the terminal loader.

        Args:
            file_path: Path to CSV or Parquet file containing terminal data.
            source_name: Source name for citation tracking.
        """
        self.file_path = Path(file_path)
        self.source_name = source_name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        if not self.file_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.file_path}")

    def load(self) -> list[LNGTerminal]:
        """Load terminal data from file and convert to LNGTerminal instances.

        Returns:
            List of validated LNGTerminal model instances.

        Raises:
            FileNotFoundError: If the data file does not exist.
            ValueError: If file format is not supported.
        """
        self.logger.info("Loading terminal data from %s", self.file_path)

        # Load data based on file extension
        if self.file_path.suffix == ".csv":
            df = pd.read_csv(self.file_path)
        elif self.file_path.suffix in (".parquet", ".pq"):
            df = pd.read_parquet(self.file_path)
        else:
            raise ValueError(
                f"Unsupported file format: {self.file_path.suffix}. "
                "Supported formats: .csv, .parquet, .pq"
            )

        self.logger.info("Loaded %d records from %s", len(df), self.file_path)

        # Convert DataFrame rows to LNGTerminal instances
        terminals = []
        failed_count = 0

        for idx, row in df.iterrows():
            try:
                terminal = self._row_to_terminal(row)
                terminals.append(terminal)
            except (ValidationError, ValueError) as exc:
                failed_count += 1
                self.logger.warning(
                    "Failed to parse row %d (%s): %s",
                    idx,
                    row.get("terminal_name", "unknown"),
                    exc,
                )

        self.logger.info(
            "Successfully parsed %d / %d terminals (%d failed)",
            len(terminals),
            len(df),
            failed_count,
        )

        return terminals

    def _row_to_terminal(self, row: pd.Series) -> LNGTerminal:
        """Convert a DataFrame row to an LNGTerminal instance.

        Args:
            row: Pandas Series containing terminal data.

        Returns:
            Validated LNGTerminal instance.

        Raises:
            ValidationError: If terminal data fails Pydantic validation.
            ValueError: If required fields are missing or invalid.
        """
        # Build source citation
        sourced_fields = self._identify_sourced_fields(row)
        source_citation = SourceCitation(
            source_name=row.get("source", self.source_name),
            source_url=self._get_optional_str(row, "source_url"),
            access_date=date.today(),
            fields_sourced=sourced_fields,
            reliability=self._parse_reliability(row.get("data_confidence", "medium")),
        )

        # Build marine infrastructure if water depth is provided
        marine_infra = None
        if pd.notna(row.get("water_depth_m")):
            marine_infra = MarineInfrastructure(
                water_depth_m=self._get_optional_float(row, "water_depth_m"),
                jetty_count=self._get_optional_int(row, "jetty_count"),
            )

        # Build storage spec if storage volume is provided
        storage = None
        if pd.notna(row.get("storage_m3")):
            storage = StorageSpec(
                tank_type="full_containment",  # Default assumption
                total_capacity_m3=self._get_optional_float(row, "storage_m3"),
            )

        # Create LNGTerminal instance
        terminal = LNGTerminal(
            terminal_name=self._get_required_str(row, "terminal_name"),
            country=self._get_required_str(row, "country"),
            latitude=self._get_optional_float(row, "latitude"),
            longitude=self._get_optional_float(row, "longitude"),
            terminal_type=self._parse_terminal_type(
                self._get_required_str(row, "terminal_type")
            ),
            function=self._parse_function(self._get_required_str(row, "function")),
            status=self._parse_status(self._get_required_str(row, "status")),
            capacity_mtpa=self._get_optional_float(row, "capacity_mtpa"),
            year_commissioned=self._get_optional_int(row, "year_commissioned"),
            operator=self._get_optional_str(row, "operator"),
            owner=self._get_optional_str(row, "owner"),
            capex_usd_million=self._get_optional_float(row, "capex_usd_million"),
            marine_infrastructure=marine_infra,
            storage=storage,
            sources=[source_citation],
            last_updated=datetime.utcnow(),
        )

        return terminal

    def _identify_sourced_fields(self, row: pd.Series) -> list[str]:
        """Identify which fields have values in the row.

        Args:
            row: Pandas Series containing terminal data.

        Returns:
            List of field names that have non-null values.
        """
        sourced_fields = [
            "terminal_name",
            "country",
            "terminal_type",
            "function",
            "status",
        ]

        optional_fields = [
            "latitude",
            "longitude",
            "capacity_mtpa",
            "year_commissioned",
            "operator",
            "owner",
            "water_depth_m",
            "storage_m3",
            "jetty_count",
            "capex_usd_million",
        ]

        for field in optional_fields:
            if pd.notna(row.get(field)):
                sourced_fields.append(field)

        return sourced_fields

    @staticmethod
    def _get_required_str(row: pd.Series, key: str) -> str:
        """Extract a required string field from a row.

        Args:
            row: Pandas Series containing data.
            key: Field name to extract.

        Returns:
            String value.

        Raises:
            ValueError: If field is missing or null.
        """
        value = row.get(key)
        if pd.isna(value):
            raise ValueError(f"Required field '{key}' is missing or null")
        return str(value).strip()

    @staticmethod
    def _get_optional_str(row: pd.Series, key: str) -> str | None:
        """Extract an optional string field from a row.

        Args:
            row: Pandas Series containing data.
            key: Field name to extract.

        Returns:
            String value or None if field is missing/null.
        """
        value = row.get(key)
        if pd.isna(value):
            return None
        return str(value).strip()

    @staticmethod
    def _get_optional_float(row: pd.Series, key: str) -> float | None:
        """Extract an optional float field from a row.

        Args:
            row: Pandas Series containing data.
            key: Field name to extract.

        Returns:
            Float value or None if field is missing/null.
        """
        value = row.get(key)
        if pd.isna(value):
            return None
        return float(value)

    @staticmethod
    def _get_optional_int(row: pd.Series, key: str) -> int | None:
        """Extract an optional integer field from a row.

        Args:
            row: Pandas Series containing data.
            key: Field name to extract.

        Returns:
            Integer value or None if field is missing/null.
        """
        value = row.get(key)
        if pd.isna(value):
            return None
        return int(value)

    @staticmethod
    def _parse_terminal_type(value: str) -> TerminalType:
        """Parse terminal type string to enum.

        Args:
            value: Terminal type string.

        Returns:
            TerminalType enum value.

        Raises:
            ValueError: If value is not a valid terminal type.
        """
        try:
            return TerminalType(value.lower().strip())
        except ValueError:
            raise ValueError(
                f"Invalid terminal_type: '{value}'. "
                f"Must be one of: {[t.value for t in TerminalType]}"
            )

    @staticmethod
    def _parse_function(value: str) -> TerminalFunction:
        """Parse terminal function string to enum.

        Args:
            value: Terminal function string.

        Returns:
            TerminalFunction enum value.

        Raises:
            ValueError: If value is not a valid function.
        """
        try:
            return TerminalFunction(value.lower().strip())
        except ValueError:
            raise ValueError(
                f"Invalid function: '{value}'. "
                f"Must be one of: {[f.value for f in TerminalFunction]}"
            )

    @staticmethod
    def _parse_status(value: str) -> TerminalStatus:
        """Parse terminal status string to enum.

        Args:
            value: Terminal status string.

        Returns:
            TerminalStatus enum value.

        Raises:
            ValueError: If value is not a valid status.
        """
        try:
            return TerminalStatus(value.lower().strip())
        except ValueError:
            raise ValueError(
                f"Invalid status: '{value}'. "
                f"Must be one of: {[s.value for s in TerminalStatus]}"
            )

    @staticmethod
    def _parse_reliability(value: str) -> SourceReliability:
        """Parse data confidence string to source reliability enum.

        Args:
            value: Confidence string (high/medium/low).

        Returns:
            SourceReliability enum value.

        Raises:
            ValueError: If value is not a valid reliability level.
        """
        try:
            return SourceReliability(value.lower().strip())
        except ValueError:
            raise ValueError(
                f"Invalid data_confidence: '{value}'. "
                f"Must be one of: {[r.value for r in SourceReliability]}"
            )
