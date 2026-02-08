"""GIE ALSI collector for European LNG terminal inventory."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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

# GIE country code mapping (GIE uses 2-letter codes)
_GIE_COUNTRY_MAP = {
    "BE": "BEL",
    "ES": "ESP",
    "FR": "FRA",
    "GB": "GBR",
    "GR": "GRC",
    "HR": "HRV",
    "IT": "ITA",
    "LT": "LTU",
    "NL": "NLD",
    "PL": "POL",
    "PT": "PRT",
    "TR": "TUR",
    "DE": "DEU",
    "MT": "MLT",
    "SE": "SWE",
    "FI": "FIN",
}

# GIE status mapping
_GIE_STATUS_MAP = {
    "E": TerminalStatus.OPERATIONAL,  # Existing
    "C": TerminalStatus.UNDER_CONSTRUCTION,  # Under construction
    "P": TerminalStatus.PLANNED,  # Planned
}


class GIECollector(BaseCollector):
    """Collect European LNG terminal data from GIE ALSI."""

    source_name = "gie"
    source_reliability = SourceReliability.HIGH

    def __init__(self, refresh_mode: RefreshMode | None = None) -> None:
        super().__init__(source_name="gie", refresh_mode=refresh_mode)
        source_cfg = self.config.sources.get("gie")
        self._api_url = source_cfg.api_url if source_cfg else ""

    def fetch_data(self) -> list[dict]:
        """Fetch terminal data from GIE API.

        Returns list of terminal dicts, or empty list if unavailable.
        """
        if not self._api_url:
            self.logger.warning("GIE API URL not configured, returning empty dataset")
            return []

        try:
            response = self._make_request(self._api_url)
            data = response.json()
            # GIE API returns various formats; handle both list and nested
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return []
        except LNGCollectionError:
            self.logger.warning("GIE source unavailable, returning empty dataset")
            return []
        except Exception as e:
            self.logger.warning(f"Failed to parse GIE response: {e}")
            return []

    def parse_records(self, raw_data: list[dict]) -> list[LNGTerminal]:
        """Parse GIE JSON data into LNGTerminal records."""
        terminals = []
        for record in raw_data:
            try:
                terminal = self._parse_record(record)
                if terminal:
                    terminals.append(terminal)
            except Exception as e:
                name = record.get("name", record.get("facilityName", "unknown"))
                self.logger.warning(f"Failed to parse GIE record '{name}': {e}")
        return terminals

    def _parse_record(self, record: dict) -> LNGTerminal | None:
        """Parse a single GIE record."""
        name = record.get("name", record.get("facilityName", "")).strip()
        if not name:
            return None

        # Country code
        country_2 = record.get("country", record.get("countryCode", "")).strip()
        country = _GIE_COUNTRY_MAP.get(
            country_2, Normalizer.normalize_country(country_2)
        )

        # Status
        status_code = record.get("status", "E").strip()
        status = _GIE_STATUS_MAP.get(status_code, TerminalStatus.OPERATIONAL)

        # Capacity (GIE typically reports in mcm/d or GWh/d)
        capacity_mtpa = None
        cap_str = record.get("maxCapacity", record.get("dtmi", ""))
        if cap_str:
            try:
                mcm_d = float(cap_str)
                # mcm/d to bcm/yr (365 * mcm/d / 1000), then to MTPA
                bcm_yr = mcm_d * 365 / 1000
                capacity_mtpa = round(bcm_yr * 0.735, 2)
            except (ValueError, TypeError):
                pass

        # Coordinates
        lat = self._safe_float(record.get("lat", record.get("latitude")))
        lon = self._safe_float(record.get("lng", record.get("longitude")))

        region = Normalizer.get_region(country)

        return LNGTerminal(
            terminal_name=name,
            country=country,
            terminal_type=TerminalType.ONSHORE_IMPORT,
            function=TerminalFunction.IMPORT,
            status=status,
            capacity_mtpa=capacity_mtpa,
            operator=record.get("operator", record.get("company")),
            latitude=lat,
            longitude=lon,
            region=region,
            last_updated=datetime.utcnow(),
            sources=[
                self._create_citation(
                    [
                        "terminal_name",
                        "country",
                        "status",
                        "capacity_mtpa",
                        "operator",
                        "latitude",
                        "longitude",
                    ]
                )
            ],
        )

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        if val is None:
            return None
        try:
            result = float(val)
            return result if result != 0.0 else None
        except (ValueError, TypeError):
            return None
