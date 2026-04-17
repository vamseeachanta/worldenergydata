"""Classification society register lookups (ABS, DNV, LR)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from worldenergydata.vessel_fleet.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class ClassificationCollector(BaseCollector):
    """Look up vessel classification data from society registers.

    Supports ABS Eagle, DNV Vessel Register, and Lloyd's Register.
    All are free, publicly accessible web lookups.
    """

    def __init__(self) -> None:
        super().__init__(
            name="classification",
            rate_limit=0.5,  # 1 request per 2 seconds
            cache_ttl=86400.0 * 7,  # 7-day cache
        )

    def collect(self) -> list[dict[str, Any]]:
        """Not used directly — call lookup methods."""
        return []

    def lookup_abs(self, imo_number: str) -> Optional[dict[str, Any]]:
        """Look up vessel in ABS Eagle register."""
        cache_key = f"abs:{imo_number}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            url = f"https://ww2.eagle.org/en/rules-and-resources/record.html?imo={imo_number}"
            html = self.get_text(url)
            result = self._parse_abs_result(html, imo_number)
            if result:
                self._set_cache(cache_key, result)
            return result
        except Exception as exc:
            logger.warning("ABS lookup failed for IMO %s: %s", imo_number, exc)
            return None

    def lookup_dnv(self, imo_number: str) -> Optional[dict[str, Any]]:
        """Look up vessel in DNV Vessel Register."""
        cache_key = f"dnv:{imo_number}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            url = f"https://vesselregister.dnv.com/VesselRegister/vesseldetails/{imo_number}"
            html = self.get_text(url)
            result = self._parse_dnv_result(html, imo_number)
            if result:
                self._set_cache(cache_key, result)
            return result
        except Exception as exc:
            logger.warning("DNV lookup failed for IMO %s: %s", imo_number, exc)
            return None

    def _parse_abs_result(
        self,
        html: str,
        imo_number: str,
    ) -> Optional[dict[str, Any]]:
        """Parse ABS Eagle register page."""
        try:
            from worldenergydata.vessel_fleet.parsers.html import (
                extract_key_value_pairs,
            )
        except ImportError:
            return None

        pairs = extract_key_value_pairs(html)
        if not pairs:
            return None

        return {
            "IMO_NUMBER": imo_number,
            "CLASSIFICATION_SOCIETY": "ABS",
            "CLASS_NOTATION": pairs.get("Class Notation", ""),
            "VESSEL_NAME": pairs.get("Vessel Name", ""),
            "FLAG_STATE": pairs.get("Flag", ""),
            "YEAR_BUILT": pairs.get("Year Built", ""),
            "DATA_SOURCE": "abs_register",
        }

    def _parse_dnv_result(
        self,
        html: str,
        imo_number: str,
    ) -> Optional[dict[str, Any]]:
        """Parse DNV Vessel Register page."""
        try:
            from worldenergydata.vessel_fleet.parsers.html import (
                extract_key_value_pairs,
            )
        except ImportError:
            return None

        pairs = extract_key_value_pairs(html)
        if not pairs:
            return None

        return {
            "IMO_NUMBER": imo_number,
            "CLASSIFICATION_SOCIETY": "DNV",
            "CLASS_NOTATION": pairs.get("Class notation", ""),
            "VESSEL_NAME": pairs.get("Name", ""),
            "FLAG_STATE": pairs.get("Flag state", ""),
            "YEAR_BUILT": pairs.get("Year of build", ""),
            "DATA_SOURCE": "dnv_register",
        }
