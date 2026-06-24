"""Dataclass model for rig fleet records.

Provides domain logic (computed properties) on top of validated data
from RigFleetSchema.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

_RIG_TYPE_DISPLAY_MAP: dict[str, str] = {
    "drillship": "Drillship",
    "semi_submersible": "Semi-Submersible",
    "jack_up": "Jack-Up",
    "platform_rig": "Platform Rig",
    "tender_assisted": "Tender Assisted",
    "inland_barge": "Inland Barge",
    "submersible": "Submersible",
    "land_rig": "Land Rig",
    "wireline_unit": "Wireline Unit",
    "coil_tubing_unit": "Coil Tubing Unit",
    "lift_boat": "Lift Boat",
    "snubbing_unit": "Snubbing Unit",
    "workover_rig": "Workover Rig",
    "support_vessel": "Support Vessel",
    "pumping_unit": "Pumping Unit",
}

_INACTIVE_STATUSES: frozenset[str] = frozenset(
    {
        "stacked_cold",
        "stacked_warm",
        "scrapped",
    }
)

_DEEPWATER_THRESHOLD_FT: float = 4000.0


@dataclass
class RigFleetEntry:
    """Domain model for a rig fleet record.

    Attributes use snake_case following Python conventions. Instantiate
    from a validated ``RigFleetSchema`` or directly with keyword
    arguments.
    """

    rig_name: str
    rig_type: Optional[str] = None
    rig_status: Optional[str] = None
    owner: Optional[str] = None
    operator: Optional[str] = None
    water_depth_rating_ft: Optional[float] = None
    drilling_depth_rating_ft: Optional[float] = None
    loa_m: Optional[float] = None
    beam_m: Optional[float] = None
    displacement_tonnes: Optional[float] = None
    dp_class: Optional[int] = None
    year_built: Optional[int] = None
    imo_number: Optional[str] = None
    flag_state: Optional[str] = None
    moonpool_diameter_m: Optional[float] = None
    wells_drilled_count: Optional[int] = None
    last_war_date: Optional[str] = None
    last_area_code: Optional[str] = None
    data_source: Optional[str] = None
    is_offshore: Optional[bool] = None
    first_war_date: Optional[str] = None
    last_block_number: Optional[str] = None
    max_water_depth_ft: Optional[float] = None

    @property
    def is_active(self) -> bool:
        """Rig is active when its status is not in the inactive set.

        A rig with an unknown (None) status is assumed active.
        """
        if self.rig_status is None:
            return True
        return self.rig_status not in _INACTIVE_STATUSES

    @property
    def is_deepwater_capable(self) -> bool:
        """Rig is deepwater capable when rated >= 4000 ft water depth."""
        if self.water_depth_rating_ft is None:
            return False
        return self.water_depth_rating_ft >= _DEEPWATER_THRESHOLD_FT

    @property
    def rig_key(self) -> str:
        """Normalised key: lowered, stripped, spaces to underscores."""
        return self.rig_name.strip().lower().replace(" ", "_")

    @property
    def rig_type_display(self) -> str:
        """Human-readable rig type derived from rig_type string."""
        return _RIG_TYPE_DISPLAY_MAP.get(self.rig_type, "Unknown")

    @property
    def is_offshore_derived(self) -> bool:
        """Whether the rig operates offshore.

        Uses the explicit ``is_offshore`` flag when set, otherwise
        infers from rig type (land_rig -> False, everything else -> True).
        """
        if self.is_offshore is not None:
            return self.is_offshore
        if self.rig_type == "land_rig":
            return False
        return True
