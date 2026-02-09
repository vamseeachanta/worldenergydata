"""HTML fleet page collector for contractor websites.

Uses per-contractor configs to scrape fleet pages and extract
vessel data from HTML tables and key-value pairs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from worldenergydata.vessel_fleet.collectors.base import BaseCollector
from worldenergydata.vessel_fleet.parsers.html import (
    extract_key_value_pairs,
    extract_tables,
)
from worldenergydata.vessel_fleet.parsers.numeric import parse_numeric

logger = logging.getLogger(__name__)


@dataclass
class ContractorConfig:
    """Configuration for a single contractor's fleet page collection."""

    name: str
    fleet_url: str
    vessel_category: str
    vessel_type: str
    owner: str
    table_selector: Optional[str] = None
    detail_selector: Optional[str] = None
    field_mapping: dict[str, str] = field(default_factory=dict)
    vessel_links_selector: Optional[str] = None
    rate_limit: float = 1.0


class FleetPageCollector(BaseCollector):
    """Collect vessel data from contractor fleet web pages."""

    def __init__(self, config: ContractorConfig) -> None:
        super().__init__(
            name=config.name,
            rate_limit=config.rate_limit,
        )
        self.config = config

    def collect(self) -> list[dict[str, Any]]:
        """Collect all vessels from the configured fleet page."""
        logger.info("Collecting fleet data from %s", self.config.fleet_url)
        html = self.get_text(self.config.fleet_url)

        vessels: list[dict[str, Any]] = []

        # Try table extraction first
        if self.config.table_selector:
            tables = extract_tables(html, self.config.table_selector)
            for table in tables:
                for row in table:
                    vessel = self._map_table_row(row)
                    if vessel:
                        vessels.append(vessel)

        # Try key-value extraction for detail pages
        if self.config.detail_selector and not vessels:
            pairs = extract_key_value_pairs(html, self.config.detail_selector)
            if pairs:
                vessel = self._map_kv_pairs(pairs)
                if vessel:
                    vessels.append(vessel)

        logger.info("Collected %d vessels from %s", len(vessels), self.config.name)
        return vessels

    def _map_table_row(self, row: dict[str, str]) -> Optional[dict[str, Any]]:
        """Map an HTML table row to a vessel record using field mapping."""
        record: dict[str, Any] = {
            "VESSEL_CATEGORY": self.config.vessel_category,
            "VESSEL_TYPE": self.config.vessel_type,
            "OWNER": self.config.owner,
            "DATA_SOURCE": "contractor_fleet_page",
            "DATA_SOURCE_URL": self.config.fleet_url,
        }

        has_name = False
        for html_col, schema_field in self.config.field_mapping.items():
            value = row.get(html_col)
            if value and value.strip():
                record[schema_field] = value.strip()
                if schema_field == "VESSEL_NAME":
                    has_name = True

        if not has_name:
            return None
        return record

    def _map_kv_pairs(self, pairs: dict[str, str]) -> Optional[dict[str, Any]]:
        """Map key-value pairs to a vessel record."""
        record: dict[str, Any] = {
            "VESSEL_CATEGORY": self.config.vessel_category,
            "VESSEL_TYPE": self.config.vessel_type,
            "OWNER": self.config.owner,
            "DATA_SOURCE": "contractor_fleet_page",
            "DATA_SOURCE_URL": self.config.fleet_url,
        }

        for html_key, schema_field in self.config.field_mapping.items():
            value = pairs.get(html_key)
            if value and value.strip():
                record[schema_field] = value.strip()

        if "VESSEL_NAME" not in record:
            return None
        return record
