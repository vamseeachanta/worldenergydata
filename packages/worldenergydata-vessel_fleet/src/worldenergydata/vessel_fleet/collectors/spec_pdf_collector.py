"""PDF spec sheet collector for contractor fleet data.

Downloads and parses spec sheet PDFs from contractor websites using the
rig-summary parser and optional key-value mappings.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Optional

from worldenergydata.vessel_fleet.collectors.base import BaseCollector
from worldenergydata.vessel_fleet.parsers.pdf import (
    extract_key_value_from_text,
    extract_text_from_pdf,
)
from worldenergydata.vessel_fleet.parsers.rig_summary import parse_rig_summary_text

logger = logging.getLogger(__name__)


class SpecPdfCollector(BaseCollector):
    """Collect vessel specs from PDF spec sheets.

    Downloads PDFs from URLs and parses drilling-rig specifications into
    typed fields with the existing rig-summary parser. Optional mappings
    add fields without replacing normalized values or source identity.
    Non-rig categories use only the explicit mappings.
    """

    def __init__(
        self,
        *,
        name: str,
        owner: str,
        vessel_category: str = "drilling_rig",
        field_mapping: Optional[dict[str, str]] = None,
        rate_limit: float = 0.5,
    ) -> None:
        super().__init__(name=name, rate_limit=rate_limit)
        self.owner = owner
        self.vessel_category = vessel_category
        self.field_mapping = field_mapping or {}

    def collect(self) -> list[dict[str, Any]]:
        """Override in subclass or call collect_from_urls."""
        return []

    def collect_from_urls(
        self,
        pdf_urls: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Collect specs from a dict of {vessel_name: pdf_url}.

        Returns only records with extracted specifications. Empty, image-only,
        unrecognized and failed PDFs are warned about and omitted, leaving
        any separately collected source-table records available to the caller.
        """
        records: list[dict[str, Any]] = []
        for vessel_name, url in pdf_urls.items():
            try:
                record = self._collect_single(vessel_name, url)
                if record:
                    records.append(record)
            except Exception as exc:
                logger.warning(
                    "Failed to collect %s from %s: %s",
                    vessel_name,
                    url,
                    exc,
                )
        return records

    def _collect_single(
        self,
        vessel_name: str,
        url: str,
    ) -> Optional[dict[str, Any]]:
        """Download and parse a single spec PDF."""
        logger.info("Downloading spec PDF for %s", vessel_name)
        pdf_bytes = self.get_bytes(url)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            text = extract_text_from_pdf(
                tmp_path, layout=self.vessel_category == "drilling_rig"
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        if not text.strip():
            logger.warning("Empty PDF text for %s", vessel_name)
            return None

        pairs = {
            " ".join(key.split()): value
            for key, value in extract_key_value_from_text(text).items()
        }

        record: dict[str, Any] = {
            "VESSEL_NAME": vessel_name,
            "VESSEL_CATEGORY": self.vessel_category,
            "OWNER": self.owner,
            "DATA_SOURCE": "contractor_spec_pdf",
            "DATA_SOURCE_URL": url,
        }
        specs = (
            parse_rig_summary_text(text)
            if self.vessel_category == "drilling_rig"
            else {}
        )

        for pdf_key, schema_field in self.field_mapping.items():
            value = pairs.get(" ".join(pdf_key.split()))
            if value and value.strip() and schema_field not in record:
                specs.setdefault(schema_field, value.strip())

        if not specs:
            logger.warning("No recognized PDF specifications for %s", vessel_name)
            return None

        record.update(specs)
        return record
