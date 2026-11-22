# ABOUTME: Data models for WRK-219 batch drilling economics.
# ABOUTME: Defines DrillingSite and DrillCampaign Pydantic schemas.

"""Data models for batch drilling campaign scheduling and cost optimization.

DrillingSite — individual well definition for campaign planning.
DrillCampaign — rig campaign grouping multiple wells with economics parameters.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from numbers import Integral, Real
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _finite_real(value: object) -> float:
    """Accept real scalars, excluding Booleans, text and nonfinite values."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("must be a finite real number, not Boolean or text")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError("must be representable as a finite float") from exc
    if not math.isfinite(result):
        raise ValueError("must be a finite real number")
    if result == 0 and value != 0:
        raise ValueError("nonzero input underflows float representation")
    return result


def _positive_integer(value: object) -> int:
    """Accept Python/NumPy integers within finite float representability."""
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError("must be a positive integer, not Boolean or float")
    _finite_real(value)
    if value <= 0:
        raise ValueError("must be > 0")
    return int(value)


FiniteReal = Annotated[float, BeforeValidator(_finite_real)]
PositiveReal = Annotated[FiniteReal, Field(gt=0)]
NonnegativeReal = Annotated[FiniteReal, Field(ge=0)]
LearningFactor = Annotated[FiniteReal, Field(gt=0, le=1)]
PositiveInteger = Annotated[int, BeforeValidator(_positive_integer)]
Latitude = Annotated[FiniteReal, Field(ge=-90, le=90)]
Longitude = Annotated[FiniteReal, Field(ge=-180, le=180)]


def _same_typed_value(original: object, validated: object) -> bool:
    """Require canonical field types as well as values before retaining identity."""
    if type(original) is not type(validated):
        return False
    if isinstance(original, dict):
        return original.keys() == validated.keys() and all(
            _same_typed_value(value, validated[key]) for key, value in original.items()
        )
    if isinstance(original, (tuple, list)):
        return len(original) == len(validated) and all(
            _same_typed_value(value, checked)
            for value, checked in zip(original, validated)
        )
    return original == validated


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

    model_config = ConfigDict(revalidate_instances="always")

    well_id: str = Field(min_length=1, pattern=r"\S")
    field_name: str
    location_coords: tuple[Latitude, Longitude]
    water_depth_ft: NonnegativeReal
    planned_md_ft: PositiveReal
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

    model_config = ConfigDict(revalidate_instances="always")

    campaign_id: str
    rig_name: str
    rig_day_rate_usd: PositiveReal
    mobilization_cost_usd: NonnegativeReal
    wells: list[DrillingSite] = Field(min_length=1)
    sequence: list[str] = Field(default_factory=list)
    learning_curve_factor: LearningFactor = 0.85

    @model_validator(mode="after")
    def _validate_sequence(self) -> DrillCampaign:
        """Require unique site IDs and a complete permutation when supplied."""
        well_ids = [well.well_id for well in self.wells]
        if len(set(well_ids)) != len(well_ids):
            raise ValueError("well_id values must be unique within a campaign")
        if self.sequence and (
            len(self.sequence) != len(well_ids) or set(self.sequence) != set(well_ids)
        ):
            raise ValueError("sequence must contain each well_id exactly once")
        return self

    def ordered_wells(self) -> list[DrillingSite]:
        """Return wells in sequence order.

        Revalidates one materialized snapshot of current state. Canonical sites
        retain identity; entries requiring normalization use validated replacements.
        A one-shot iterable assigned to wells is consumed once for this call.
        An empty sequence uses insertion order; invalid sequences raise ValueError.

        Returns:
            List of DrillingSite in campaign drill order.
        """
        originals = self.wells
        if isinstance(originals, Iterable):
            originals = list(originals)
        checked = DrillCampaign.model_validate(
            self.model_copy(update={"wells": originals})
        )
        wells = [
            (
                original
                if type(original) is DrillingSite
                and _same_typed_value(original.__dict__, validated.__dict__)
                else validated
            )
            for original, validated in zip(originals, checked.wells)
        ]
        if not checked.sequence:
            return wells
        well_map = {w.well_id: w for w in wells}
        return [well_map[wid] for wid in checked.sequence]


def _campaign_instance(value: object) -> DrillCampaign:
    """Keep the calculator's campaign boundary model-only, not a mapping parser."""
    if not isinstance(value, DrillCampaign):
        raise ValueError("campaign must be a DrillCampaign instance")
    return value


CampaignInput = Annotated[DrillCampaign, BeforeValidator(_campaign_instance)]
