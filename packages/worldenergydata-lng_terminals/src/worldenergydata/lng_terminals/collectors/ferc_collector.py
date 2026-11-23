"""Collector for US LNG terminal data from FERC.

FERC (Federal Energy Regulatory Commission) publishes data about approved
and operating LNG terminals in the United States.  This collector fetches
CSV/tabular data from a configurable FERC endpoint and parses it into
LNGTerminal records.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime

from ..constants import (
    RefreshMode,
    Region,
    SourceReliability,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from ..exceptions import LNGCollectionError
from ..models.terminal import LNGTerminal
from .base_collector import BaseCollector

# ---------------------------------------------------------------------------
# Column and status mappings
# ---------------------------------------------------------------------------

_FERC_COLUMN_MAP: dict[str, str] = {
    "Project Name": "terminal_name",
    "Docket Number": "docket_number",
    "Status": "status",
    "Capacity (Bcf/d)": "capacity_bcfd",
    "Location": "location",
    "Operator": "operator",
    "Type": "terminal_type",
    "Date Approved": "date_approved",
    "Date Operational": "date_operational",
}

_FERC_STATUS_MAP: dict[str, TerminalStatus] = {
    "Approved": TerminalStatus.PLANNED,
    "Operating": TerminalStatus.OPERATIONAL,
    "Under Construction": TerminalStatus.UNDER_CONSTRUCTION,
    "Proposed": TerminalStatus.PROPOSED,
    "Approved - Not Yet Built": TerminalStatus.PLANNED,
}

# Approximate conversion factor: 1 Bcf/d ~ 7.6 MTPA
_BCFD_TO_MTPA = 7.6


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------


class FERCCollector(BaseCollector):
    """Collect US LNG terminal data from FERC."""

    source_name = "ferc"
    source_reliability = SourceReliability.HIGH

    def __init__(self, refresh_mode: RefreshMode | None = None) -> None:
        super().__init__(source_name="ferc", refresh_mode=refresh_mode)
        source_cfg = self.config.sources.get("ferc")
        self._base_url: str = source_cfg.base_url if source_cfg else ""

    # -- Lifecycle hooks -----------------------------------------------------

    def fetch_data(self) -> str:
        """Fetch CSV data from FERC.

        Returns:
            CSV content as a string, or an empty string when the source
            is not configured or unavailable.
        """
        if not self._base_url:
            self.logger.warning("FERC base_url not configured, returning empty dataset")
            return ""

        try:
            response = self._make_request(self._base_url)
            return response.text
        except LNGCollectionError:
            self.logger.warning("FERC source unavailable, returning empty dataset")
            return ""

    def parse_records(self, raw_data: str) -> list[LNGTerminal]:
        """Parse FERC CSV data into LNGTerminal records."""
        if not raw_data:
            return []

        terminals: list[LNGTerminal] = []
        reader = csv.DictReader(io.StringIO(raw_data))

        for row in reader:
            try:
                terminal = self._parse_row(row)
                if terminal is not None:
                    terminals.append(terminal)
            except Exception as exc:
                self.logger.warning("Failed to parse FERC row: %s", exc)

        return terminals

    # -- Row parsing ---------------------------------------------------------

    def _parse_row(self, row: dict[str, str]) -> LNGTerminal | None:
        """Parse a single FERC CSV row into an LNGTerminal.

        Returns ``None`` when the row lacks a project name.
        """
        name = row.get("Project Name", "").strip()
        if not name:
            return None

        terminal_type, function = self._determine_type_and_function(row)
        status = self._parse_status(row)
        capacity_mtpa = self._parse_capacity(row)
        year = self._parse_year(row)

        return LNGTerminal(
            terminal_name=name,
            country="USA",
            terminal_type=terminal_type,
            function=function,
            status=status,
            capacity_mtpa=capacity_mtpa,
            operator=row.get("Operator", "").strip() or None,
            year_commissioned=year,
            region=Region.NORTH_AMERICA,
            last_updated=datetime.utcnow(),
            sources=[
                self._create_citation(
                    [
                        "terminal_name",
                        "status",
                        "capacity_mtpa",
                        "operator",
                    ]
                )
            ],
        )

    # -- Field helpers -------------------------------------------------------

    @staticmethod
    def _determine_type_and_function(
        row: dict[str, str],
    ) -> tuple[TerminalType, TerminalFunction]:
        """Derive terminal type and function from the FERC 'Type' column."""
        raw_type = row.get("Type", "").strip().lower()

        if "import" in raw_type:
            return TerminalType.ONSHORE_IMPORT, TerminalFunction.IMPORT

        # Default to export -- most FERC-tracked projects are liquefaction
        return TerminalType.ONSHORE_EXPORT, TerminalFunction.EXPORT

    @staticmethod
    def _parse_status(row: dict[str, str]) -> TerminalStatus:
        """Map a FERC status string to a ``TerminalStatus``."""
        raw_status = row.get("Status", "").strip()
        return _FERC_STATUS_MAP.get(raw_status, TerminalStatus.OPERATIONAL)

    @staticmethod
    def _parse_capacity(row: dict[str, str]) -> float | None:
        """Convert Bcf/d capacity to MTPA."""
        capacity_str = row.get("Capacity (Bcf/d)", "").strip()
        if not capacity_str:
            return None
        try:
            return float(capacity_str) * _BCFD_TO_MTPA
        except ValueError:
            return None

    @staticmethod
    def _parse_year(row: dict[str, str]) -> int | None:
        """Extract a four-digit year from date columns."""
        for field in ("Date Operational", "Date Approved"):
            date_str = row.get(field, "").strip()
            if date_str and len(date_str) >= 4:
                try:
                    return int(date_str[:4])
                except ValueError:
                    continue
        return None
