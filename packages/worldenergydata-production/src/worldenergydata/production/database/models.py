"""Metadata contracts; no regulator data or conversion factors are bundled."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from numbers import Real
from types import MappingProxyType
from urllib.parse import urlsplit

# Stable identities: data/data-source-catalog.yml, production-reservoir domain,
# inspected 2026-10-20. These are identifiers, not source-access qualifications.
REGULATOR_SOURCES = MappingProxyType(
    {
        "BSEE": "bsee-data-center",
        "EIA": "eia-api-v2",
        "SODIR": "sodir-factpages",
        "NSTA": "uk-nsta-opendata",
        "ANP": "brazil-anp-bdep",
        "CNH": "mexico-cnh-sih",
        "RRC": "texas-rrc",
    }
)

# Existing unified/query.py STANDARD_COLUMNS contract: monthly volumes, not
# daily rates. No standard-condition or unit conversion is implied here.
CANONICAL_UNITS = MappingProxyType(
    {"oil_bbl": "bbl", "gas_mcf": "Mcf", "water_bbl": "bbl", "condensate_bbl": "bbl"}
)


def text(value: str, name: str) -> str:
    """Reject absent identifiers without silently normalizing source identity."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


def number(value: float, name: str, *, positive: bool = False) -> float:
    """Production and decline magnitudes must be finite and nonnegative."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be finite") from error
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError(
            f"{name} must be finite and {'positive' if positive else 'nonnegative'}"
        )
    return result


@dataclass(frozen=True)
class SourceSnapshot:
    """Caller-attested raw source identity, version, digest and retrieval time.

    The digest identifies the retained original, not normalized database rows.
    This class does not verify raw bytes, rights, freshness or field suitability.
    """

    snapshot_id: str
    source_id: str
    version: str
    locator: str
    retrieved_at: str
    sha256: str
    data_kind: str

    def __post_init__(self):
        for name in ("snapshot_id", "version", "locator", "retrieved_at"):
            text(getattr(self, name), name)
        if self.source_id not in REGULATOR_SOURCES.values():
            raise ValueError("unknown regulator source_id")
        if not isinstance(self.sha256, str) or not re.fullmatch(
            "[0-9a-f]{64}", self.sha256
        ):
            raise ValueError("sha256 must contain lowercase hexadecimal digest text")
        if self.data_kind not in {"reported", "synthetic"}:
            raise ValueError("data_kind must be reported or synthetic")
        try:
            instant = datetime.fromisoformat(self.retrieved_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("retrieved_at must be an ISO timestamp") from error
        if instant.utcoffset() is None:
            raise ValueError("retrieved_at must include a timezone")
        address = urlsplit(self.locator)
        if (
            address.scheme not in {"https", "http"}
            or not address.hostname
            or address.username
        ):
            raise ValueError("locator must be an HTTP source URL without credentials")


@dataclass(frozen=True)
class DeclineHistory:
    """Explicitly qualified input for the existing monthly-volume fitter.

    Points use its one-based month index and bbl/month convention. The digest
    binds the snapshot metadata, asset identity and selected production rows.
    """

    snapshot_id: str
    asset_id: str
    points: tuple[tuple[int, float], ...]
    sha256: str
    data_kind: str
