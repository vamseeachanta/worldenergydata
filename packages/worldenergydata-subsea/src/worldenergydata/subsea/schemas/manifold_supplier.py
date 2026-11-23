"""Pydantic schema for subsea-manifold supplier (key-player) records.

Mirrors the conventions of :mod:`worldenergydata.vessel_fleet.schemas`:
field names are UPPERCASE so a row can be loaded directly from a
DataFrame / CSV via ``ManifoldSupplierSchema(**row)``.

Multi-value fields (product lines, projects, developments, source URLs)
are stored in the curated CSV as ``" | "``-delimited strings and parsed
into lists here. ``" | "`` is used as the delimiter rather than ``,`` or
``;`` because those characters appear inside the free-text values.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

#: Delimiter used to pack list-valued fields into single CSV cells.
LIST_DELIMITER = " | "

#: Allowed values for how a company participates in the manifold market.
MANIFOLD_ROLES = {
    "OEM",  # designs/manufactures manifold hardware
    "EPC",  # engineers / procures / constructs (incl. EPCI/iEPCI)
    "fabricator",  # structural fabrication / integration of manifolds
    "subsystem_supplier",  # supplies adjacent subsea systems (power, controls)
    "limited",  # not a direct manifold supplier (completions/intervention)
}

#: Allowed competitive-tier classifications.
ROLE_TIERS = {"tier_1", "tier_2", "niche", "adjacency"}


class ManifoldSupplierSchema(BaseModel):
    """Schema for a single subsea-manifold key-player record."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Required
    COMPANY: str

    # Identity / corporate
    TICKER: Optional[str] = None
    HQ_COUNTRY: Optional[str] = None
    HQ_CITY: Optional[str] = None
    PARENT_OR_JV: Optional[str] = None

    # Market role
    MANIFOLD_ROLE: Optional[str] = None
    ROLE_TIER: Optional[str] = None
    MARKET_POSITION: Optional[str] = None

    # Capability
    MAX_WATER_DEPTH_M: Optional[int] = None

    # Multi-value (delimited in CSV, lists in-model)
    PRODUCT_LINES: List[str] = []
    NOTABLE_PROJECTS: List[str] = []
    RECENT_DEVELOPMENTS: List[str] = []
    DATA_SOURCE_URLS: List[str] = []

    # Provenance
    DATA_SOURCE_URL: Optional[str] = None
    COLLECTION_DATE: Optional[str] = None
    NOTES: Optional[str] = None

    # --- Validators ---

    @field_validator("COMPANY", mode="before")
    @classmethod
    def _require_company(cls, v: object) -> object:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            raise ValueError("COMPANY is required")
        return v

    @field_validator(
        "TICKER",
        "HQ_COUNTRY",
        "HQ_CITY",
        "PARENT_OR_JV",
        "MANIFOLD_ROLE",
        "ROLE_TIER",
        "MARKET_POSITION",
        "DATA_SOURCE_URL",
        "COLLECTION_DATE",
        "NOTES",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "PRODUCT_LINES",
        "NOTABLE_PROJECTS",
        "RECENT_DEVELOPMENTS",
        "DATA_SOURCE_URLS",
        mode="before",
    )
    @classmethod
    def _split_list_fields(cls, v: object) -> object:
        """Accept a delimited string (from CSV) or an existing list."""
        if v is None:
            return []
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return []
            return [part.strip() for part in v.split(LIST_DELIMITER) if part.strip()]
        if isinstance(v, (list, tuple)):
            return [str(item).strip() for item in v if str(item).strip()]
        return v

    @field_validator("MAX_WATER_DEPTH_M", mode="before")
    @classmethod
    def _coerce_depth(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == "" or v.lower() == "unknown":
                return None
            return int(float(v))
        if isinstance(v, float):
            return int(v)
        return v

    @field_validator("MAX_WATER_DEPTH_M")
    @classmethod
    def _validate_depth(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 6000):
            raise ValueError("MAX_WATER_DEPTH_M must be between 0 and 6000 m")
        return v

    @field_validator("MANIFOLD_ROLE")
    @classmethod
    def _validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in MANIFOLD_ROLES:
            raise ValueError(
                f"MANIFOLD_ROLE must be one of {sorted(MANIFOLD_ROLES)}",
            )
        return v

    @field_validator("ROLE_TIER")
    @classmethod
    def _validate_tier(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ROLE_TIERS:
            raise ValueError(f"ROLE_TIER must be one of {sorted(ROLE_TIERS)}")
        return v
