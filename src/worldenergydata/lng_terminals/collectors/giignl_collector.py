"""GIIGNL annual report collector for global LNG terminal data."""

from __future__ import annotations

import contextlib
import re
from datetime import datetime

from ..constants import (
    RefreshMode,
    SourceReliability,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from ..exceptions import LNGCollectionError
from ..models.terminal import LNGTerminal
from ..processors.normalizer import Normalizer
from .base_collector import BaseCollector


class GIIGNLCollector(BaseCollector):
    """Collect global LNG terminal data from GIIGNL annual reports.

    GIIGNL publishes annual reports with tables listing all global
    import and export terminals. This collector parses PDF tables
    via pdfplumber when available, or falls back to pre-extracted
    CSV data.
    """

    source_name = "giignl"
    source_reliability = SourceReliability.HIGH

    def __init__(self, refresh_mode: RefreshMode | None = None) -> None:
        super().__init__(source_name="giignl", refresh_mode=refresh_mode)
        source_cfg = self.config.sources.get("giignl")
        self._base_url = source_cfg.base_url if source_cfg else ""

    def fetch_data(self) -> list[dict]:
        """Fetch GIIGNL data.

        Attempts to download and parse PDF, falls back to empty list.
        """
        if not self._base_url:
            self.logger.warning("GIIGNL URL not configured, returning empty dataset")
            return []

        try:
            response = self._make_request(self._base_url)
            content_type = response.headers.get("content-type", "")

            if "pdf" in content_type.lower():
                return self._parse_pdf(response.content)
            elif "csv" in content_type.lower() or "text" in content_type.lower():
                return self._parse_csv_text(response.text)
            else:
                # Try as CSV first, then PDF
                try:
                    return self._parse_csv_text(response.text)
                except Exception:
                    return self._parse_pdf(response.content)
        except LNGCollectionError:
            self.logger.warning("GIIGNL source unavailable, returning empty dataset")
            return []
        except Exception as e:
            self.logger.warning(f"Failed to fetch GIIGNL data: {e}")
            return []

    def _parse_pdf(self, content: bytes) -> list[dict]:
        """Extract terminal data from GIIGNL PDF report."""
        try:
            import pdfplumber
        except ImportError:
            self.logger.warning("pdfplumber not installed, cannot parse GIIGNL PDF")
            return []

        records = []
        try:
            import io

            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        records.extend(self._parse_table_rows(table))
        except Exception as e:
            self.logger.warning(f"Failed to parse GIIGNL PDF: {e}")

        return records

    def _parse_csv_text(self, text: str) -> list[dict]:
        """Parse CSV text data from GIIGNL."""
        import csv
        import io

        records = []
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            record = {
                "terminal_name": row.get("Terminal", row.get("Name", "")).strip(),
                "country": row.get("Country", "").strip(),
                "capacity": row.get("Capacity (MTPA)", row.get("Capacity", "")),
                "status": row.get("Status", "operational"),
                "type": row.get("Type", ""),
                "operator": row.get("Operator", row.get("Company", "")),
                "year": row.get("Start Year", row.get("Year", "")),
            }
            if record["terminal_name"]:
                records.append(record)
        return records

    def _parse_table_rows(self, table: list[list]) -> list[dict]:
        """Parse a table extracted from PDF into record dicts."""
        if not table or len(table) < 2:
            return []

        records = []
        headers = [str(h).strip().lower() if h else "" for h in table[0]]

        for row in table[1:]:
            if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                continue

            record = {}
            for i, cell in enumerate(row):
                if i < len(headers) and headers[i]:
                    record[headers[i]] = str(cell).strip() if cell else ""

            name = record.get("terminal", record.get("name", ""))
            if name:
                records.append(
                    {
                        "terminal_name": name,
                        "country": record.get("country", ""),
                        "capacity": record.get(
                            "capacity (mtpa)", record.get("capacity", "")
                        ),
                        "status": record.get("status", "operational"),
                        "operator": record.get("operator", record.get("company", "")),
                        "year": record.get("start year", record.get("year", "")),
                    }
                )
        return records

    def parse_records(self, raw_data: list[dict]) -> list[LNGTerminal]:
        """Parse GIIGNL records into LNGTerminal models."""
        terminals = []
        for record in raw_data:
            try:
                terminal = self._parse_record(record)
                if terminal:
                    terminals.append(terminal)
            except Exception as e:
                self.logger.warning(
                    f"Failed to parse GIIGNL record '{record.get('terminal_name', '?')}': {e}"
                )
        return terminals

    def _parse_record(self, record: dict) -> LNGTerminal | None:
        """Parse a single GIIGNL record dict."""
        name = record.get("terminal_name", "").strip()
        if not name:
            return None

        country_raw = record.get("country", "").strip()
        country = Normalizer.normalize_country(country_raw) if country_raw else ""
        if not country or len(country) != 3:
            return None

        # Determine type
        type_str = record.get("type", "").lower()
        if "export" in type_str or "liquefaction" in type_str:
            terminal_type = TerminalType.ONSHORE_EXPORT
            function = TerminalFunction.EXPORT
        elif "fsru" in type_str:
            terminal_type = TerminalType.FSRU
            function = TerminalFunction.IMPORT
        elif "flng" in type_str:
            terminal_type = TerminalType.FLNG
            function = TerminalFunction.EXPORT
        else:
            terminal_type = TerminalType.ONSHORE_IMPORT
            function = TerminalFunction.IMPORT

        # Capacity
        capacity_mtpa = None
        cap_str = record.get("capacity", "")
        if cap_str:
            with contextlib.suppress(ValueError, TypeError):
                capacity_mtpa = float(re.sub(r"[^\d.]", "", str(cap_str)))

        # Year
        year = None
        year_str = record.get("year", "")
        if year_str:
            match = re.search(r"(\d{4})", str(year_str))
            if match:
                year = int(match.group(1))
                if year < 1960 or year > 2040:
                    year = None

        status = TerminalStatus.OPERATIONAL
        status_raw = record.get("status", "").lower()
        if "construction" in status_raw:
            status = TerminalStatus.UNDER_CONSTRUCTION
        elif "planned" in status_raw:
            status = TerminalStatus.PLANNED

        region = Normalizer.get_region(country)

        return LNGTerminal(
            terminal_name=name,
            country=country,
            terminal_type=terminal_type,
            function=function,
            status=status,
            capacity_mtpa=capacity_mtpa,
            operator=record.get("operator") or None,
            year_commissioned=year,
            region=region,
            last_updated=datetime.utcnow(),
            sources=[
                self._create_citation(
                    [
                        "terminal_name",
                        "country",
                        "capacity_mtpa",
                        "status",
                    ]
                )
            ],
        )
