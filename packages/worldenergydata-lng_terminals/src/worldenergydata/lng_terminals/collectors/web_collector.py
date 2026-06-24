"""Collector for LNG terminal engineering design data from web sources.

Targets HTML pages from trade publications, operator project pages,
Marine Insight, and similar sources to extract hull, pipeline, process,
and storage specifications.  Because web sources vary greatly, this
collector returns partial LNGTerminal records that the enricher merges
into the canonical dataset.
"""

from __future__ import annotations

import contextlib
import logging
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from ..constants import (
    RefreshMode,
    SourceReliability,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from ..exceptions import LNGCollectionError
from ..models.design import (
    HullDesign,
    MarineInfrastructure,
    ProcessEquipment,
    StorageSpec,
)
from ..models.terminal import LNGTerminal
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns for extracting engineering data from free-form text
# ---------------------------------------------------------------------------

_CAPACITY_PATTERN = re.compile(
    r"(\d+\.?\d*)\s*(?:MTPA|mtpa|million\s+tonn)",
    re.IGNORECASE,
)
_LOA_PATTERN = re.compile(
    r"(?:LOA|length\s+overall)[:\s]*(\d+\.?\d*)\s*m",
    re.IGNORECASE,
)
_BEAM_PATTERN = re.compile(
    r"(?:beam|breadth|width)[:\s]*(\d+\.?\d*)\s*m",
    re.IGNORECASE,
)
_DRAFT_PATTERN = re.compile(
    r"(?:draft|draught)[:\s]*(\d+\.?\d*)\s*m",
    re.IGNORECASE,
)
_DEPTH_PATTERN = re.compile(
    r"(?:depth|moulded\s+depth)[:\s]*(\d+\.?\d*)\s*m",
    re.IGNORECASE,
)
_STORAGE_PATTERN = re.compile(
    r"(?:storage|tank)\s+(?:capacity)?[:\s]*(\d[\d,]*)\s*(?:m3|m\u00b3|cubic)",
    re.IGNORECASE,
)
_TRAINS_PATTERN = re.compile(
    r"(\d+)\s+(?:liquefaction\s+)?trains?",
    re.IGNORECASE,
)
_WATER_DEPTH_PATTERN = re.compile(
    r"water\s+depth[:\s]*(\d+\.?\d*)\s*m",
    re.IGNORECASE,
)


class WebCollector(BaseCollector):
    """Collect engineering design data from web sources.

    Accepts a list of URLs, fetches each page, and extracts whatever
    engineering parameters can be identified via keyword/regex patterns.
    The resulting :class:`LNGTerminal` records are intentionally partial
    -- missing fields are expected to be filled by the enrichment layer.
    """

    source_name = "web"
    source_reliability = SourceReliability.LOW

    def __init__(
        self, urls: list[str] | None = None, refresh_mode: RefreshMode | None = None
    ) -> None:
        super().__init__(source_name="web", refresh_mode=refresh_mode)
        self._urls = urls or []

    # -- Public lifecycle hooks ---------------------------------------------

    def fetch_data(self) -> list[dict[str, Any]]:
        """Fetch HTML content from configured URLs.

        Returns:
            List of dicts with ``url`` and ``html`` keys.
        """
        results: list[dict[str, Any]] = []
        for url in self._urls:
            try:
                response = self._make_request(url)
                results.append({"url": url, "html": response.text})
            except LNGCollectionError as exc:
                self.logger.warning("Failed to fetch %s: %s", url, exc)
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("Error fetching %s: %s", url, exc)
        return results

    def parse_records(self, raw_data: list[dict[str, Any]]) -> list[LNGTerminal]:
        """Parse HTML pages into partial :class:`LNGTerminal` records."""
        terminals: list[LNGTerminal] = []
        for page in raw_data:
            try:
                extracted = self._extract_from_html(page["html"], page["url"])
                if extracted:
                    terminals.extend(extracted)
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(
                    "Failed to parse %s: %s",
                    page.get("url", "?"),
                    exc,
                )
        return terminals

    # -- HTML extraction ----------------------------------------------------

    def _extract_from_html(
        self,
        html: str,
        url: str,
    ) -> list[LNGTerminal]:
        """Extract terminal data from a single HTML page.

        Returns a list containing zero or one :class:`LNGTerminal` records.
        An empty list is returned when no usable terminal name can be
        determined from the page.
        """
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        # Try to find terminal name from page title or heading
        name = self._extract_name(soup)
        if not name or len(name) < 3:
            return []

        # Extract engineering parameters
        hull = self._extract_hull(text)
        process = self._extract_process(text)
        storage = self._extract_storage(text)
        marine = self._extract_marine(text)
        capacity = self._extract_float(_CAPACITY_PATTERN, text)

        # Determine terminal type from content
        terminal_type, function = self._infer_type_and_function(text)

        # Build source-field tracking
        sourced_fields = self._build_sourced_fields(
            hull=hull,
            process=process,
            storage=storage,
            marine=marine,
            capacity=capacity,
        )

        # Web collector primarily provides engineering enrichment, so a
        # missing country is expected -- use a sentinel that the enricher
        # will resolve.
        terminal = LNGTerminal(
            terminal_name=name,
            country="UNK",
            terminal_type=terminal_type,
            function=function,
            status=TerminalStatus.OPERATIONAL,
            capacity_mtpa=capacity,
            hull_design=hull,
            process_equipment=process,
            storage=storage,
            marine_infrastructure=marine,
            last_updated=datetime.utcnow(),
            sources=[self._create_citation(sourced_fields)],
        )
        return [terminal]

    # -- Name extraction ----------------------------------------------------

    @staticmethod
    def _extract_name(soup: BeautifulSoup) -> str:
        """Derive a terminal name from ``<h1>`` or ``<title>``."""
        h1 = soup.find("h1")
        title = soup.find("title")

        name = ""
        if h1:
            name = h1.get_text(strip=True)
        elif title:
            name = title.get_text(strip=True)

        # Strip common website suffixes
        for suffix in [" - Wikipedia", " | ", " \u2013 "]:
            if suffix in name:
                name = name.split(suffix)[0].strip()

        return name

    # -- Type inference -----------------------------------------------------

    @staticmethod
    def _infer_type_and_function(
        text: str,
    ) -> tuple[TerminalType, TerminalFunction]:
        """Guess terminal type and function from page text."""
        text_lower = text.lower()

        if "fsru" in text_lower:
            return TerminalType.FSRU, TerminalFunction.IMPORT
        if "flng" in text_lower:
            return TerminalType.FLNG, TerminalFunction.EXPORT
        if "liquefaction" in text_lower or "export" in text_lower:
            return TerminalType.ONSHORE_EXPORT, TerminalFunction.EXPORT

        return TerminalType.ONSHORE_IMPORT, TerminalFunction.IMPORT

    # -- Sub-model extraction -----------------------------------------------

    def _extract_hull(self, text: str) -> HullDesign | None:
        """Try to extract hull design parameters from text."""
        loa = self._extract_float(_LOA_PATTERN, text)
        beam = self._extract_float(_BEAM_PATTERN, text)
        draft = self._extract_float(_DRAFT_PATTERN, text)
        depth = self._extract_float(_DEPTH_PATTERN, text)

        if not any([loa, beam, draft, depth]):
            return None

        text_lower = text.lower()
        hull_type = "ship-shaped"
        if "barge" in text_lower:
            hull_type = "barge"
        elif "semi-submersible" in text_lower or "semi submersible" in text_lower:
            hull_type = "semi-submersible"
        elif "spar" in text_lower:
            hull_type = "spar"

        return HullDesign(
            hull_type=hull_type,
            loa_m=loa,
            beam_m=beam,
            draft_m=draft,
            depth_m=depth,
        )

    def _extract_process(self, text: str) -> ProcessEquipment | None:
        """Try to extract process equipment parameters."""
        trains = self._extract_int(_TRAINS_PATTERN, text)
        if trains is None:
            return None

        process = None
        text_lower = text.lower()
        for tech in ["c3mr", "ap-x", "dmr", "cascade", "prico"]:
            if tech in text_lower:
                process = tech.upper()
                break

        return ProcessEquipment(
            number_of_trains=trains,
            liquefaction_process=process,
        )

    def _extract_storage(self, text: str) -> StorageSpec | None:
        """Try to extract storage parameters."""
        match = _STORAGE_PATTERN.search(text)
        if not match:
            return None

        capacity_str = match.group(1).replace(",", "")
        try:
            total_capacity = float(capacity_str)
        except ValueError:
            return None

        return StorageSpec(
            tank_type="full_containment",
            total_capacity_m3=total_capacity,
        )

    def _extract_marine(self, text: str) -> MarineInfrastructure | None:
        """Try to extract marine infrastructure parameters."""
        water_depth = self._extract_float(_WATER_DEPTH_PATTERN, text)
        if water_depth is None:
            return None

        return MarineInfrastructure(water_depth_m=water_depth)

    # -- Sourced-field tracking ---------------------------------------------

    @staticmethod
    def _build_sourced_fields(
        *,
        hull: HullDesign | None,
        process: ProcessEquipment | None,
        storage: StorageSpec | None,
        marine: MarineInfrastructure | None,
        capacity: float | None,
    ) -> list[str]:
        """Build the list of field names provided by this extraction."""
        sourced: list[str] = ["terminal_name"]
        if hull:
            sourced.append("hull_design")
        if process:
            sourced.append("process_equipment")
        if storage:
            sourced.append("storage")
        if marine:
            sourced.append("marine_infrastructure")
        if capacity:
            sourced.append("capacity_mtpa")
        return sourced

    # -- Primitive extraction helpers ----------------------------------------

    @staticmethod
    def _extract_float(pattern: re.Pattern, text: str) -> float | None:
        """Return the first float captured by *pattern*, or ``None``."""
        match = pattern.search(text)
        if match:
            with contextlib.suppress(ValueError):
                return float(match.group(1).replace(",", ""))
        return None

    @staticmethod
    def _extract_int(pattern: re.Pattern, text: str) -> int | None:
        """Return the first int captured by *pattern*, or ``None``."""
        match = pattern.search(text)
        if match:
            with contextlib.suppress(ValueError):
                return int(match.group(1))
        return None
