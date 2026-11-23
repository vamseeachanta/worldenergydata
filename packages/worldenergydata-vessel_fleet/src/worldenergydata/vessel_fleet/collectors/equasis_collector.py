"""Equasis vessel registry lookup collector.

Equasis (equasis.org) provides IMO numbers, flag states, classification
societies, and ownership data for registered vessels. Free registration
required. Rate limit: 1 request per 3 seconds (be polite).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from worldenergydata.vessel_fleet.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

_EQUASIS_SEARCH_URL = "https://www.equasis.org/EquasisWeb/restricted/Search"
_EQUASIS_DETAIL_URL = "https://www.equasis.org/EquasisWeb/restricted/ShipInfo"


class EquasisCollector(BaseCollector):
    """Look up vessel details from Equasis maritime registry.

    Requires a free Equasis account. Authentication cookies must be
    provided or obtained via login.
    """

    def __init__(
        self,
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="equasis",
            rate_limit=0.33,  # 1 request per 3 seconds
            cache_ttl=86400.0,  # 24h cache — vessel data changes rarely
        )
        self._username = username
        self._password = password
        self._authenticated = False

    def collect(self) -> list[dict[str, Any]]:
        """Not used directly — call lookup_vessel instead."""
        return []

    def authenticate(self) -> bool:
        """Log in to Equasis and store session cookies.

        Returns True on success, False on failure.
        """
        if not self._username or not self._password:
            logger.warning("Equasis credentials not provided")
            return False

        try:
            response = self.session.post(
                "https://www.equasis.org/EquasisWeb/authen/HomePage",
                data={
                    "j_username": self._username,
                    "j_password": self._password,
                },
                timeout=self.timeout,
            )
            self._authenticated = response.status_code == 200
            if self._authenticated:
                logger.info("Equasis authentication successful")
            else:
                logger.warning(
                    "Equasis authentication failed: %d", response.status_code
                )
            return self._authenticated
        except Exception as exc:
            logger.warning("Equasis authentication error: %s", exc)
            return False

    def lookup_vessel(self, vessel_name: str) -> Optional[dict[str, Any]]:
        """Search Equasis for a vessel by name.

        Returns a dict with IMO_NUMBER, FLAG_STATE, CLASSIFICATION_SOCIETY,
        OWNER, MMSI, or None if not found.
        """
        if not self._authenticated:
            logger.warning("Not authenticated with Equasis")
            return None

        cache_key = f"equasis:name:{vessel_name.upper()}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            response = self.get(
                _EQUASIS_SEARCH_URL,
                params={"ShipName": vessel_name},
            )
            result = self._parse_search_results(response.text, vessel_name)
            if result:
                self._set_cache(cache_key, result)
            return result
        except Exception as exc:
            logger.warning("Equasis lookup failed for %s: %s", vessel_name, exc)
            return None

    def lookup_by_imo(self, imo_number: str) -> Optional[dict[str, Any]]:
        """Look up vessel details by IMO number."""
        if not self._authenticated:
            logger.warning("Not authenticated with Equasis")
            return None

        cache_key = f"equasis:imo:{imo_number}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            response = self.get(
                _EQUASIS_DETAIL_URL,
                params={"IMO": imo_number},
            )
            result = self._parse_vessel_detail(response.text)
            if result:
                self._set_cache(cache_key, result)
            return result
        except Exception as exc:
            logger.warning("Equasis IMO lookup failed for %s: %s", imo_number, exc)
            return None

    def _parse_search_results(
        self,
        html: str,
        vessel_name: str,
    ) -> Optional[dict[str, Any]]:
        """Parse Equasis search results HTML."""
        try:
            from worldenergydata.vessel_fleet.parsers.html import extract_tables
        except ImportError:
            return None

        tables = extract_tables(html, "table#resultTable")
        if not tables or not tables[0]:
            return None

        name_upper = vessel_name.upper()
        for row in tables[0]:
            row_name = row.get("Ship name", row.get("Name", "")).upper()
            if name_upper in row_name or row_name in name_upper:
                return {
                    "VESSEL_NAME": row.get("Ship name", row.get("Name", "")),
                    "IMO_NUMBER": row.get("IMO number", row.get("IMO", "")),
                    "FLAG_STATE": row.get("Flag", ""),
                    "CLASSIFICATION_SOCIETY": row.get("Class", ""),
                    "GROSS_TONNAGE": row.get("Gross tonnage", ""),
                    "DATA_SOURCE": "equasis",
                }
        return None

    def _parse_vessel_detail(self, html: str) -> Optional[dict[str, Any]]:
        """Parse Equasis vessel detail page HTML."""
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
            "IMO_NUMBER": pairs.get("IMO number", ""),
            "VESSEL_NAME": pairs.get("Ship name", ""),
            "FLAG_STATE": pairs.get("Flag", ""),
            "CLASSIFICATION_SOCIETY": pairs.get("Classification society", ""),
            "MMSI": pairs.get("MMSI", ""),
            "OWNER": pairs.get("Registered owner", ""),
            "GROSS_TONNAGE": pairs.get("Gross tonnage", ""),
            "DEADWEIGHT_TONNES": pairs.get("Deadweight", ""),
            "YEAR_BUILT": pairs.get("Year of build", ""),
            "DATA_SOURCE": "equasis",
        }
