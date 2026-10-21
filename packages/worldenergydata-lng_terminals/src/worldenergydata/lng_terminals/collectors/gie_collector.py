"""GIE ALSI collector for European LNG terminal inventory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
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


@dataclass(frozen=True)
class GIECapacityBasis:
    """Caller-supplied annual and gas-property basis; no universal defaults.

    Factors must describe the same gas and reference conditions as the source.
    ``reference`` identifies the supporting document or declared assumption.
    """

    days_per_year: float
    reference: str
    tonnes_per_mcm: float | None = None
    tonnes_per_gwh: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reference, str) or not self.reference.strip():
            raise ValueError("A conversion basis reference is required")
        for field in ("days_per_year", "tonnes_per_mcm", "tonnes_per_gwh"):
            value = getattr(self, field)
            if value is None and field != "days_per_year":
                continue
            # Positive, finite factors are the domain of mass/rate conversion.
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0
            ):
                raise ValueError(f"{field} must be finite and positive")


class GIECollector(BaseCollector):
    """Collect European LNG terminal data from GIE ALSI."""

    source_name = "gie"
    source_reliability = SourceReliability.HIGH

    def __init__(
        self,
        refresh_mode: RefreshMode | None = None,
        *,
        capacity_basis: GIECapacityBasis | None = None,
    ) -> None:
        super().__init__(source_name="gie", refresh_mode=refresh_mode)
        self.capacity_basis = capacity_basis
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

        capacity_mtpa = self._parse_capacity(record)

        # Coordinates
        lat = self._safe_float(record.get("lat", record.get("latitude")))
        lon = self._safe_float(record.get("lng", record.get("longitude")))

        region = Normalizer.get_region(country)

        fields = [
            "terminal_name",
            "country",
            "status",
            "operator",
            "latitude",
            "longitude",
        ]
        if capacity_mtpa is not None:
            fields.append("capacity_mtpa")
        citations = [self._create_citation(fields)]
        if capacity_mtpa is not None:
            citations.append(
                self._create_citation(["capacity_mtpa"]).model_copy(
                    update={"source_name": self.capacity_basis.reference}
                )
            )

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
            sources=citations,
        )

    def _parse_capacity(self, record: dict) -> float | None:
        """Convert only explicitly dimensioned throughput with a declared basis."""
        # GIE API User Manual v007 (2022), section 2.4, page 8:
        # dtrs is send-out capacity in GWh/d; dtmi is storage volume, never rate.
        # https://www.gie.eu/transparency-platform/GIE_API_documentation_v007.pdf
        # maxCapacity/maxCapacityUnit is the explicit adapter input contract.
        if "maxCapacity" in record:
            raw = record["maxCapacity"]
            unit = record.get("maxCapacityUnit")
        else:
            raw = record.get("dtrs")
            unit = "GWh/d"
        if raw is None or raw == "":
            return None
        try:
            if unit not in ("mcm/d", "GWh/d"):
                raise ValueError("unknown or missing capacity unit")
            rate = float(raw)
            if isinstance(raw, bool) or not isfinite(rate) or rate <= 0:
                raise ValueError("capacity rate must be finite and positive")
            basis = self.capacity_basis
            if basis is None:
                raise ValueError("conversion basis is required")
            factor = basis.tonnes_per_mcm if unit == "mcm/d" else basis.tonnes_per_gwh
            if factor is None:
                raise ValueError("conversion factor for capacity unit is required")
            # Dimensional cancellation: rate/day * tonnes/rate * days/year.
            # NIST SP 811 (2008), section 4, table 5: mega = 10**6.
            capacity = rate * factor * basis.days_per_year / 1_000_000
            if not isfinite(capacity):
                raise ValueError("capacity conversion is not finite")
            return capacity
        except (ValueError, TypeError, OverflowError) as exc:
            self.logger.warning("GIE capacity NOT_EVALUATED: %s", exc)
            return None

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        if val is None:
            return None
        try:
            result = float(val)
            return result if result != 0.0 else None
        except (ValueError, TypeError):
            return None
