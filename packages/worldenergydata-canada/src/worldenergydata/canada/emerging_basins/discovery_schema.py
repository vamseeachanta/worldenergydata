"""Pydantic schema for frontier-basin deepwater discovery records.

Mirrors the conventions of :mod:`worldenergydata.subsea.schemas` and
:mod:`worldenergydata.vessel_fleet.schemas`: field names are UPPERCASE so a
row can be loaded directly from a CSV ``DictReader`` row via
``DiscoverySchema(**row)``.

The curated CSV (``data/modules/frontier_basins/curated/frontier_discoveries.csv``)
is the human-readable source of truth.  Every figure is source-attributed via
``DATA_SOURCE_URL`` and graded with a ``CONFIDENCE_TIER``:

* ``high``   — operator-confirmed (company press release / FID statement)
* ``medium`` — reputable secondary (Reuters / Offshore Magazine / OGJ / trade press)
* ``low``    — analyst estimate only, in-place-only figure, or commerciality unconfirmed
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

#: Countries currently catalogued in the frontier-basins dataset.
COUNTRIES = {"Guyana", "Suriname", "Namibia"}

#: Allowed confidence gradings.
CONFIDENCE_TIERS = {"high", "medium", "low"}

#: How the reported resource figure should be interpreted.
RESOURCE_BASES = {
    "recoverable",  # recoverable / EUR volume
    "in_place",  # oil/gas in place (NOT recoverable)
    "net_pay",  # only net hydrocarbon pay thickness disclosed
    "not_disclosed",  # no public volume figure
}

#: Allowed development / appraisal status values.
STATUSES = {
    "discovery",  # confirmed discovery, not yet appraised/sanctioned
    "appraisal",  # under appraisal drilling
    "pre_fid",  # development concept defined, FID pending
    "sanctioned",  # FID taken, under development
    "producing",  # on production (typically via an FPSO phase)
    "non_commercial",  # hydrocarbons found but sub-commercial as drilled
}


class DiscoverySchema(BaseModel):
    """Schema for a single frontier-basin deepwater discovery record."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Required identity
    DISCOVERY_NAME: str
    BLOCK: str
    COUNTRY: str
    BASIN: str

    # Operatorship
    OPERATOR: str
    PARTNERS: Optional[str] = None

    # Facts
    DISCOVERY_YEAR: Optional[int] = None
    WATER_DEPTH_M: Optional[int] = None
    RESOURCE_ESTIMATE: Optional[str] = None
    RESOURCE_BASIS: str = "not_disclosed"
    STATUS: str = "discovery"

    # Provenance / grading
    CONFIDENCE_TIER: str = "medium"
    DATA_SOURCE_URL: Optional[str] = None
    NOTES: Optional[str] = None

    # --- Validators ---

    @field_validator("DISCOVERY_NAME", "BLOCK", "COUNTRY", "BASIN", "OPERATOR")
    @classmethod
    def _require_non_empty(cls, v: str) -> str:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            raise ValueError("required field must not be empty")
        return v

    @field_validator(
        "PARTNERS",
        "RESOURCE_ESTIMATE",
        "DATA_SOURCE_URL",
        "NOTES",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("DISCOVERY_YEAR", "WATER_DEPTH_M", mode="before")
    @classmethod
    def _coerce_int(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == "" or v.lower() in {"unknown", "n/a", "na", "tbd"}:
                return None
            return int(float(v))
        if isinstance(v, float):
            return int(v)
        return v

    @field_validator("COUNTRY")
    @classmethod
    def _validate_country(cls, v: str) -> str:
        if v not in COUNTRIES:
            raise ValueError(f"COUNTRY must be one of {sorted(COUNTRIES)}")
        return v

    @field_validator("CONFIDENCE_TIER")
    @classmethod
    def _validate_tier(cls, v: str) -> str:
        if v not in CONFIDENCE_TIERS:
            raise ValueError(
                f"CONFIDENCE_TIER must be one of {sorted(CONFIDENCE_TIERS)}"
            )
        return v

    @field_validator("RESOURCE_BASIS", mode="before")
    @classmethod
    def _default_basis(cls, v: object) -> object:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return "not_disclosed"
        return v

    @field_validator("RESOURCE_BASIS")
    @classmethod
    def _validate_basis(cls, v: str) -> str:
        if v not in RESOURCE_BASES:
            raise ValueError(f"RESOURCE_BASIS must be one of {sorted(RESOURCE_BASES)}")
        return v

    @field_validator("STATUS", mode="before")
    @classmethod
    def _default_status(cls, v: object) -> object:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return "discovery"
        return v

    @field_validator("STATUS")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        if v not in STATUSES:
            raise ValueError(f"STATUS must be one of {sorted(STATUSES)}")
        return v

    @field_validator("DISCOVERY_YEAR")
    @classmethod
    def _validate_year(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1990 <= v <= 2035):
            raise ValueError("DISCOVERY_YEAR must be between 1990 and 2035")
        return v

    @field_validator("WATER_DEPTH_M")
    @classmethod
    def _validate_depth(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 < v <= 4000):
            raise ValueError("WATER_DEPTH_M must be between 0 and 4000 m")
        return v
