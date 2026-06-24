"""Normalizer for LNG terminal data.

Standardizes country codes, maps terminal statuses, converts capacity
units, and normalizes text fields so that downstream analysis operates
on a consistent representation.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from ..constants import Region, TerminalStatus, TerminalType
from ..models.terminal import LNGTerminal

# ---------------------------------------------------------------------------
# Conversion factors
# ---------------------------------------------------------------------------

BCFD_TO_MTPA: float = 7.6
"""1 billion cubic feet per day ~ 7.6 million tonnes per annum."""

BCM_TO_MTPA: float = 0.735
"""1 billion cubic metres per year ~ 0.735 million tonnes per annum."""

# ---------------------------------------------------------------------------
# Country code aliases  (input -> ISO 3166-1 alpha-3)
# ---------------------------------------------------------------------------

COUNTRY_ALIASES: dict[str, str] = {
    "US": "USA",
    "UK": "GBR",
    "GB": "GBR",
    "UAE": "ARE",
    "UNITED STATES": "USA",
    "UNITED KINGDOM": "GBR",
    "AUSTRALIA": "AUS",
    "QATAR": "QAT",
    "CANADA": "CAN",
    "RUSSIA": "RUS",
    "MALAYSIA": "MYS",
    "NIGERIA": "NGA",
    "INDONESIA": "IDN",
    "TRINIDAD": "TTO",
    "TRINIDAD AND TOBAGO": "TTO",
    "ALGERIA": "DZA",
    "EGYPT": "EGY",
    "OMAN": "OMN",
    "NORWAY": "NOR",
    "JAPAN": "JPN",
    "SOUTH KOREA": "KOR",
    "KOREA": "KOR",
    "CHINA": "CHN",
    "INDIA": "IND",
    "SPAIN": "ESP",
    "FRANCE": "FRA",
    "ITALY": "ITA",
    "TURKEY": "TUR",
    "BRAZIL": "BRA",
    "MEXICO": "MEX",
    "GERMANY": "DEU",
    "NETHERLANDS": "NLD",
    "BELGIUM": "BEL",
    "POLAND": "POL",
    "LITHUANIA": "LTU",
    "CROATIA": "HRV",
    "GREECE": "GRC",
    "PORTUGAL": "PRT",
    "SINGAPORE": "SGP",
    "THAILAND": "THA",
    "TAIWAN": "TWN",
    "PAKISTAN": "PAK",
    "BANGLADESH": "BGD",
    "VIETNAM": "VNM",
    "PHILIPPINES": "PHL",
    "PAPUA NEW GUINEA": "PNG",
    "EQUATORIAL GUINEA": "GNQ",
    "CAMEROON": "CMR",
    "MOZAMBIQUE": "MOZ",
    "CONGO": "COG",
    "ANGOLA": "AGO",
    "CHILE": "CHL",
    "ARGENTINA": "ARG",
    "COLOMBIA": "COL",
    "PERU": "PER",
    "PANAMA": "PAN",
    "JAMAICA": "JAM",
    "DOMINICAN REPUBLIC": "DOM",
    "PUERTO RICO": "PRI",
    "KUWAIT": "KWT",
    "BAHRAIN": "BHR",
    "JORDAN": "JOR",
    "ISRAEL": "ISR",
    "GHANA": "GHA",
}

# ---------------------------------------------------------------------------
# Country -> Region
# ---------------------------------------------------------------------------

COUNTRY_TO_REGION: dict[str, Region] = {
    "USA": Region.NORTH_AMERICA,
    "CAN": Region.NORTH_AMERICA,
    "MEX": Region.NORTH_AMERICA,
    "BRA": Region.SOUTH_AMERICA,
    "ARG": Region.SOUTH_AMERICA,
    "CHL": Region.SOUTH_AMERICA,
    "COL": Region.SOUTH_AMERICA,
    "TTO": Region.SOUTH_AMERICA,
    "PER": Region.SOUTH_AMERICA,
    "PAN": Region.SOUTH_AMERICA,
    "JAM": Region.SOUTH_AMERICA,
    "DOM": Region.SOUTH_AMERICA,
    "PRI": Region.SOUTH_AMERICA,
    "GBR": Region.EUROPE,
    "FRA": Region.EUROPE,
    "ESP": Region.EUROPE,
    "NLD": Region.EUROPE,
    "BEL": Region.EUROPE,
    "ITA": Region.EUROPE,
    "DEU": Region.EUROPE,
    "NOR": Region.EUROPE,
    "POL": Region.EUROPE,
    "LTU": Region.EUROPE,
    "HRV": Region.EUROPE,
    "GRC": Region.EUROPE,
    "PRT": Region.EUROPE,
    "TUR": Region.EUROPE,
    "RUS": Region.EUROPE,
    "QAT": Region.MIDDLE_EAST,
    "ARE": Region.MIDDLE_EAST,
    "OMN": Region.MIDDLE_EAST,
    "KWT": Region.MIDDLE_EAST,
    "BHR": Region.MIDDLE_EAST,
    "JOR": Region.MIDDLE_EAST,
    "ISR": Region.MIDDLE_EAST,
    "DZA": Region.AFRICA,
    "EGY": Region.AFRICA,
    "NGA": Region.AFRICA,
    "GNQ": Region.AFRICA,
    "CMR": Region.AFRICA,
    "MOZ": Region.AFRICA,
    "COG": Region.AFRICA,
    "AGO": Region.AFRICA,
    "GHA": Region.AFRICA,
    "JPN": Region.ASIA_PACIFIC,
    "KOR": Region.ASIA_PACIFIC,
    "CHN": Region.ASIA_PACIFIC,
    "TWN": Region.ASIA_PACIFIC,
    "IND": Region.ASIA_PACIFIC,
    "SGP": Region.ASIA_PACIFIC,
    "THA": Region.ASIA_PACIFIC,
    "MYS": Region.ASIA_PACIFIC,
    "IDN": Region.ASIA_PACIFIC,
    "VNM": Region.ASIA_PACIFIC,
    "PHL": Region.ASIA_PACIFIC,
    "BGD": Region.ASIA_PACIFIC,
    "PAK": Region.ASIA_PACIFIC,
    "MMR": Region.ASIA_PACIFIC,
    "AUS": Region.OCEANIA,
    "PNG": Region.OCEANIA,
    "NZL": Region.OCEANIA,
}

# ---------------------------------------------------------------------------
# Status aliases  (lowercase input -> TerminalStatus)
# ---------------------------------------------------------------------------

STATUS_ALIASES: dict[str, TerminalStatus] = {
    "operating": TerminalStatus.OPERATIONAL,
    "operational": TerminalStatus.OPERATIONAL,
    "active": TerminalStatus.OPERATIONAL,
    "in service": TerminalStatus.OPERATIONAL,
    "online": TerminalStatus.OPERATIONAL,
    "under construction": TerminalStatus.UNDER_CONSTRUCTION,
    "construction": TerminalStatus.UNDER_CONSTRUCTION,
    "building": TerminalStatus.UNDER_CONSTRUCTION,
    "planned": TerminalStatus.PLANNED,
    "approved": TerminalStatus.PLANNED,
    "fid": TerminalStatus.PLANNED,
    "proposed": TerminalStatus.PROPOSED,
    "pre-fid": TerminalStatus.PROPOSED,
    "concept": TerminalStatus.PROPOSED,
    "decommissioned": TerminalStatus.DECOMMISSIONED,
    "closed": TerminalStatus.DECOMMISSIONED,
    "retired": TerminalStatus.DECOMMISSIONED,
    "mothballed": TerminalStatus.MOTHBALLED,
    "idle": TerminalStatus.MOTHBALLED,
    "suspended": TerminalStatus.MOTHBALLED,
}

# ---------------------------------------------------------------------------
# Terminal type aliases  (lowercase input -> TerminalType)
# ---------------------------------------------------------------------------

TYPE_ALIASES: dict[str, TerminalType] = {
    "onshore import": TerminalType.ONSHORE_IMPORT,
    "import": TerminalType.ONSHORE_IMPORT,
    "regasification": TerminalType.ONSHORE_IMPORT,
    "regas": TerminalType.ONSHORE_IMPORT,
    "onshore export": TerminalType.ONSHORE_EXPORT,
    "export": TerminalType.ONSHORE_EXPORT,
    "fsru": TerminalType.FSRU,
    "floating storage regasification": TerminalType.FSRU,
    "flng": TerminalType.FLNG,
    "floating lng": TerminalType.FLNG,
    "floating liquefaction": TerminalType.FLNG,
    "onshore liquefaction": TerminalType.ONSHORE_LIQUEFACTION,
    "liquefaction": TerminalType.ONSHORE_LIQUEFACTION,
    "lng plant": TerminalType.ONSHORE_LIQUEFACTION,
}


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------


class Normalizer:
    """Normalizes LNG terminal data fields.

    Handles country codes, statuses, terminal types, capacity unit
    conversion, text cleaning, and region assignment.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    # -- Public API ---------------------------------------------------------

    def normalize_terminals(self, terminals: list[LNGTerminal]) -> list[LNGTerminal]:
        """Normalize a list of terminals, returning the updated list.

        Terminals that fail normalization are kept in their original form
        and a warning is logged.
        """
        normalized: list[LNGTerminal] = []
        for terminal in terminals:
            try:
                normalized.append(self.normalize_terminal(terminal))
            except Exception as exc:
                self.logger.warning(
                    "Failed to normalize '%s': %s",
                    terminal.terminal_name,
                    exc,
                )
                normalized.append(terminal)
        return normalized

    def normalize_terminal(self, terminal: LNGTerminal) -> LNGTerminal:
        """Normalize a single terminal record in place and return it."""
        terminal.country = self.normalize_country(terminal.country)

        if terminal.region is None:
            terminal.region = self.get_region(terminal.country)

        terminal.terminal_name = _clean_text(terminal.terminal_name)
        terminal.aliases = [_clean_text(a) for a in terminal.aliases if a]

        if terminal.operator:
            terminal.operator = _clean_text(terminal.operator)
        if terminal.owner:
            terminal.owner = _clean_text(terminal.owner)
        if terminal.epc_contractor:
            terminal.epc_contractor = _clean_text(terminal.epc_contractor)

        return terminal

    # -- Static helpers -----------------------------------------------------

    @staticmethod
    def normalize_country(code: str) -> str:
        """Normalize a country code or name to ISO 3166-1 alpha-3.

        Looks up the uppercased input in :data:`COUNTRY_ALIASES`.  If no
        alias is found and the input is already three uppercase letters it
        is returned as-is.

        Raises:
            ValueError: When the input cannot be resolved to a valid
                three-letter code.
        """
        cleaned = _normalize_unicode(code).strip().upper()
        if cleaned in COUNTRY_ALIASES:
            return COUNTRY_ALIASES[cleaned]
        if re.fullmatch(r"[A-Z]{3}", cleaned):
            return cleaned
        raise ValueError(f"Cannot resolve country code: '{code}'")

    @staticmethod
    def normalize_status(status_str: str) -> TerminalStatus:
        """Normalize a free-text status string to a :class:`TerminalStatus`.

        Raises:
            ValueError: When the status string is not recognised.
        """
        key = _normalize_unicode(status_str).strip().lower()
        if key in STATUS_ALIASES:
            return STATUS_ALIASES[key]
        # Try matching against enum values directly
        for member in TerminalStatus:
            if key == member.value:
                return member
        raise ValueError(f"Unknown terminal status: '{status_str}'")

    @staticmethod
    def normalize_type(type_str: str) -> TerminalType:
        """Normalize a free-text type string to a :class:`TerminalType`.

        Raises:
            ValueError: When the type string is not recognised.
        """
        key = _normalize_unicode(type_str).strip().lower()
        if key in TYPE_ALIASES:
            return TYPE_ALIASES[key]
        for member in TerminalType:
            if key == member.value:
                return member
        raise ValueError(f"Unknown terminal type: '{type_str}'")

    @staticmethod
    def get_region(country_code: str) -> Region | None:
        """Return the :class:`Region` for *country_code*, or ``None``."""
        return COUNTRY_TO_REGION.get(country_code.upper())

    @staticmethod
    def bcfd_to_mtpa(bcfd: float) -> float:
        """Convert billion cubic feet per day to MTPA."""
        return bcfd * BCFD_TO_MTPA

    @staticmethod
    def bcm_to_mtpa(bcm: float) -> float:
        """Convert billion cubic metres per year to MTPA."""
        return bcm * BCM_TO_MTPA


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _normalize_unicode(text: str) -> str:
    """NFKC-normalize *text* and strip combining marks."""
    return unicodedata.normalize("NFKC", text)


def _clean_text(text: str) -> str:
    """Strip whitespace, normalize unicode, and collapse inner whitespace."""
    normalized = _normalize_unicode(text).strip()
    return re.sub(r"\s+", " ", normalized)
