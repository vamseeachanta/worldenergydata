"""Dataclass model for BSEE deepwater (permitted) structure records.

Provides domain logic on top of validated data from DeepwaterStructureSchema.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

_STRUCTURE_TYPE_MAP: dict[str, str] = {
    "FP": "Fixed Platform",
    "CT": "Caisson",
    "TLP": "Tension Leg Platform",
    "SPAR": "Spar",
    "FPS": "Floating Production System",
    "FPSO": "FPSO",
    "SS": "Subsea Structure",
}


@dataclass
class DeepwaterStructure:
    """Domain model for a BSEE deepwater / permitted structure.

    Extends the platform structure concept with permit-specific fields.
    """

    area_code: str
    block_number: str
    structure_number: str
    complex_id_num: Optional[str] = None
    structure_name: Optional[str] = None
    struc_type_code: Optional[str] = None
    maj_struc_flag: Optional[str] = None
    field_name_code: Optional[str] = None
    water_depth: Optional[float] = None
    install_date: Optional[str] = None
    removal_date: Optional[str] = None
    deck_count: Optional[int] = None
    slot_count: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    lease_number: Optional[str] = None
    district_code: Optional[str] = None
    permit_number: Optional[str] = None
    bus_asc_name: Optional[str] = None

    @property
    def is_active(self) -> bool:
        """Structure is active when it has not been removed."""
        return self.removal_date is None

    @property
    def structure_key(self) -> str:
        """Unique key: ``{area_code}_{block_number}_{structure_number}``."""
        return f"{self.area_code}_{self.block_number}_{self.structure_number}"

    @property
    def structure_type(self) -> str:
        """Human-readable structure type derived from STRUC_TYPE_CODE."""
        return _STRUCTURE_TYPE_MAP.get(self.struc_type_code, "Unknown")
