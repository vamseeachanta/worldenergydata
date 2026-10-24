# ABOUTME: Data models for WRK-219 batch drilling economics.
# ABOUTME: Defines DrillingSite and DrillCampaign Pydantic schemas.

"""Input contracts for batch drilling economics.

Field                        Unit          Sign / domain       Finite
===========================  ============  ==================  ======
water_depth_ft               ft            >= 0                yes
planned_md_ft                ft MD         > 0                 yes
location_coords (each)       degrees       signed              yes
rig_day_rate_usd             USD/day       > 0                 yes
day_rate                     USD/day       > 0                 yes
mobilization_cost_usd        USD           >= 0                yes
mob_cost                     USD           >= 0                yes
learning_curve_factor        fraction      0 < factor <= 1     yes
lc_factor                    fraction      0 < factor <= 1     yes
base_time_days               days          > 0                 yes
base_well_days               days          > 0                 yes
base_days_per_well           days          > 0                 yes
well_position                wells         integer >= 1        yes
n_wells_batch                wells         integer >= 1        yes
n_wells_standalone           wells         integer >= 1        yes
discount_rate (if supplied)  fraction/yr   >= 0 (unused)       yes
md_ft_per_day                ft/day        > 0                 yes
water_depth_ft_per_day       ft/day        > 0                 yes
fixed_days                   days          >= 0                yes
minimum_days                 days          >= 0                yes
===========================  ============  ==================  ======

These bounds define this API's domain, not empirical acceptance limits.
Real inputs accept integers and floats, never Boolean values or numeric text.
Identifiers/categories must be nonblank strings; mpd_required is Boolean.
Coordinates have no datum or geographic-range qualification. Models reject
unknown fields. Pydantic ValidationError.errors() identifies the field/location,
error type and message for both model construction and decorated direct calls.

A campaign requires at least one well with unique well_id values. An empty
sequence explicitly selects insertion order. Any nonempty sequence must be an
exact permutation: duplicates, unknowns and omissions are rejected with IDs,
because silent exclusions would change the cost denominator. Filtering all wells
out therefore rejects the campaign. Numeric learning/duration assumptions have
no calibrated defaults; see docs/campaign-contracts.md.
"""

from __future__ import annotations

from functools import wraps
from inspect import signature
from typing import Annotated

import numpy as np
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    validate_call,
)
from pydantic_core import PydanticCustomError


def reject_boolean(value: object) -> object:
    """Reject Boolean scalars before strict float conversion accepts them."""
    if isinstance(value, (bool, np.bool_)):
        raise PydanticCustomError("float_type", "Input should be a valid number")
    return value


# Boundaries are API definitions in the table above; no field calibration.
RealInput = Annotated[float, BeforeValidator(reject_boolean)]
PositiveReal = Annotated[RealInput, Field(strict=True, gt=0, allow_inf_nan=False)]
NonnegativeReal = Annotated[RealInput, Field(strict=True, ge=0, allow_inf_nan=False)]
FiniteReal = Annotated[RealInput, Field(strict=True, allow_inf_nan=False)]
LearningFactor = Annotated[
    RealInput, Field(strict=True, gt=0, le=1, allow_inf_nan=False)
]
WellCount = Annotated[int, Field(strict=True, ge=1)]
Identifier = Annotated[str, Field(strict=True, min_length=1, pattern=r"\S")]


def validate_inputs(function):
    """Validate direct calls with named locations even for positional arguments."""
    parameters = tuple(signature(function).parameters)
    validated = validate_call(config=ConfigDict(strict=True, allow_inf_nan=False))(
        function
    )

    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return validated(*args, **kwargs)
        except ValidationError as error:
            details = error.errors(include_url=False)
            for detail in details:
                location = detail["loc"]
                if location and isinstance(location[0], int):
                    index = location[0]
                    if index < len(parameters):
                        detail["loc"] = (parameters[index], *location[1:])
            raise ValidationError.from_exception_data(error.title, details) from None

    return checked


class ContractModel(BaseModel):
    """Strict models, revalidated when consumed by the calculation API."""

    model_config = ConfigDict(
        strict=True,
        allow_inf_nan=False,
        extra="forbid",
        validate_assignment=True,
        revalidate_instances="always",
    )


class DrillingSite(ContractModel):
    """Individual well; depths are feet and coordinates are decimal degrees."""

    well_id: Identifier
    field_name: Identifier
    location_coords: tuple[FiniteReal, FiniteReal]
    water_depth_ft: NonnegativeReal
    planned_md_ft: PositiveReal
    well_type: Identifier
    bore_design: Identifier = "standard"
    mpd_required: bool = False


class DrillCampaign(ContractModel):
    """Nonempty campaign with an explicit individual-duration learning factor.

    The documented empty-sequence convention preserves insertion order. The
    learning factor is required: no drilling calibration supports a default.
    """

    campaign_id: Identifier
    rig_name: Identifier
    rig_day_rate_usd: PositiveReal
    mobilization_cost_usd: NonnegativeReal
    wells: list[DrillingSite]
    sequence: list[Identifier] = Field(default_factory=list)
    learning_curve_factor: LearningFactor

    @field_validator("wells")
    @classmethod
    def check_wells(cls, wells: list[DrillingSite]) -> list[DrillingSite]:
        """Reject empty lists and ambiguous well identifiers at the wells field."""
        if not wells:
            raise ValueError("wells must contain at least one well")
        seen = set()
        for well in wells:
            if well.well_id in seen:
                raise ValueError(f"wells duplicate identifier: {well.well_id}")
            seen.add(well.well_id)
        return wells

    @field_validator("sequence")
    @classmethod
    def check_sequence(cls, sequence: list[str], info: ValidationInfo) -> list[str]:
        """Reject incomplete permutations at the sequence field, with IDs."""
        if not sequence or "wells" not in info.data:
            return sequence
        known = {well.well_id for well in info.data["wells"]}
        seen = set()
        for well_id in sequence:
            if well_id in seen:
                raise ValueError(f"sequence duplicate identifier: {well_id}")
            if well_id not in known:
                raise ValueError(f"sequence unknown identifier: {well_id}")
            seen.add(well_id)
        missing = known - seen
        if missing:
            raise ValueError(
                f"sequence omitted identifiers: {', '.join(sorted(missing))}"
            )
        return sequence

    def ordered_wells(self) -> list[DrillingSite]:
        """Return every well exactly once, rechecking mutable list contents."""
        validated = DrillCampaign.model_validate(self)
        if not validated.sequence:
            return list(validated.wells)
        well_map = {well.well_id: well for well in validated.wells}
        return [well_map[well_id] for well_id in validated.sequence]
