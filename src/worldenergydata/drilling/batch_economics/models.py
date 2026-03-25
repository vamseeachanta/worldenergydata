# ABOUTME: Data models for WRK-219 batch drilling economics.
# ABOUTME: Defines DrillingSite and DrillCampaign Pydantic schemas.

"""Data models for batch drilling campaign scheduling and cost optimization.

DrillingSite — individual well definition for campaign planning.
DrillCampaign — rig campaign grouping multiple wells with economics parameters.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DrillingSite(BaseModel):
    """Individual well definition for batch campaign planning.

    Attributes:
        well_id: Unique well identifier (API or internal).
        field_name: Field / development area name.
        location_coords: (latitude, longitude) decimal degrees.
        water_depth_ft: Water depth at well location in feet.
        planned_md_ft: Planned measured depth of well in feet.
        well_type: Activity category — exploration, development, appraisal.
        bore_design: Wellbore design type — slim, standard. Default standard.
        mpd_required: Whether managed pressure drilling is required.
    """

    well_id: str
    field_name: str
    location_coords: tuple[float, float]
    water_depth_ft: float
    planned_md_ft: float
    well_type: str
    bore_design: str = "standard"
    mpd_required: bool = False


class DrillCampaign(BaseModel):
    """Rig campaign grouping multiple DrillingSite wells.

    Attributes:
        campaign_id: Unique campaign identifier.
        rig_name: Name of the drilling rig.
        rig_day_rate_usd: Rig day rate in USD per day.
        mobilization_cost_usd: One-time rig mobilization cost in USD.
        wells: List of DrillingSite objects in this campaign.
        sequence: Ordered list of well_ids defining drill sequence.
            If empty, defaults to insertion order of wells.
        learning_curve_factor: Wright learning curve factor (0 < LC <= 1).
            0.85 means 15% time reduction per doubling of cumulative wells.
    """

    campaign_id: str
    rig_name: str
    rig_day_rate_usd: float = Field(gt=0)
    mobilization_cost_usd: float = Field(ge=0)
    wells: list[DrillingSite]
    sequence: list[str] = Field(default_factory=list)
    learning_curve_factor: float = Field(default=0.85, gt=0.0, le=1.0)

    def ordered_wells(self) -> list[DrillingSite]:
        """Return wells in sequence order.

        Falls back to insertion order when sequence is empty.

        Returns:
            List of DrillingSite in campaign drill order.
        """
        if not self.sequence:
            return list(self.wells)
        well_map = {w.well_id: w for w in self.wells}
        return [well_map[wid] for wid in self.sequence if wid in well_map]
