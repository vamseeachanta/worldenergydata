"""Base vessel entry dataclass with shared domain logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from worldenergydata.vessel_fleet.constants import (
    FT_TO_M,
    INACTIVE_STATUSES,
    M_TO_FT,
)

_VESSEL_NAME_PREFIXES: tuple[str, ...] = (
    "M/V ",
    "MV ",
    "S/V ",
    "SV ",
    "T.O. ",
    "SS ",
)


@dataclass
class BaseVesselEntry:
    """Domain model for shared vessel fields.

    Attributes use snake_case following Python conventions.
    """

    vessel_name: str
    vessel_category: Optional[str] = None
    vessel_type: Optional[str] = None
    vessel_subtype: Optional[str] = None
    owner: Optional[str] = None
    operator: Optional[str] = None
    imo_number: Optional[str] = None
    mmsi: Optional[str] = None
    flag_state: Optional[str] = None
    classification_society: Optional[str] = None
    class_notation: Optional[str] = None
    status: Optional[str] = None
    data_source: Optional[str] = None
    data_source_url: Optional[str] = None
    collection_date: Optional[str] = None
    loa_m: Optional[float] = None
    beam_m: Optional[float] = None
    depth_m: Optional[float] = None
    draft_m: Optional[float] = None
    displacement_tonnes: Optional[float] = None
    gross_tonnage: Optional[float] = None
    deadweight_tonnes: Optional[float] = None
    transit_speed_knots: Optional[float] = None
    dp_class: Optional[int] = None
    year_built: Optional[int] = None
    quarters_capacity: Optional[int] = None
    helideck: Optional[bool] = None

    @property
    def is_active(self) -> bool:
        """Vessel is active when status is not in the inactive set."""
        if self.status is None:
            return True
        return self.status not in INACTIVE_STATUSES

    @property
    def vessel_key(self) -> str:
        """Normalised key: lowered, stripped, spaces to underscores."""
        return self.vessel_name.strip().lower().replace(" ", "_")

    @property
    def normalised_name(self) -> str:
        """Vessel name with common prefixes stripped."""
        name = self.vessel_name.strip().upper()
        for prefix in _VESSEL_NAME_PREFIXES:
            if name.startswith(prefix):
                name = name[len(prefix) :]
                break
        return name.strip()

    @property
    def loa_ft(self) -> Optional[float]:
        """LOA in feet, converted from metres."""
        if self.loa_m is None:
            return None
        return self.loa_m * M_TO_FT

    @property
    def beam_ft(self) -> Optional[float]:
        """Beam in feet, converted from metres."""
        if self.beam_m is None:
            return None
        return self.beam_m * M_TO_FT
