"""Immutable schema primitives for auditable project cost maps."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _has_opaque_prefix(value: str, prefix: str) -> bool:
    return value.startswith(prefix) and len(value) > len(prefix)


_ALL_BOUND_TYPES = {"point", "floor", "ceiling", "closed_range", "open_range"}
_ALLOWED_BOUNDS_BY_VALUE_BASIS = {
    "point": {"point"},
    "range": {"floor", "ceiling", "closed_range", "open_range"},
    "band": {"floor", "ceiling", "closed_range", "open_range"},
    "not_public": {"open_range"},
    "backlog": _ALL_BOUND_TYPES,
    "lease_contract": _ALL_BOUND_TYPES,
    "combined": _ALL_BOUND_TYPES,
    "midstream": _ALL_BOUND_TYPES,
}


class PriceBasis(str, Enum):
    NOMINAL = "nominal"
    REAL = "real"


class Evidence(BaseModel):
    """Evidence method plus independent provenance and confidence fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    derivation: Literal[
        "disclosed", "award_derived", "allocated", "modeled", "assumed", "todo"
    ]
    source_provenance: str
    source_url: str
    source_locator: str
    confidence: Literal["high", "medium", "low"]


class RequiredAsset(BaseModel):
    """An asset and quantity required by a work package."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_type: str = Field(min_length=1)
    quantity: Annotated[int, Field(strict=True, gt=0)] | Literal["unknown"]


class WorkPackageRequirement(BaseModel):
    """A stable requirement identity with its required assets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    requirement_id: str
    project_id: str
    work_package: str = Field(min_length=1)
    required_assets: tuple[RequiredAsset, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_ids(self) -> "WorkPackageRequirement":
        if not _has_opaque_prefix(self.requirement_id, "req-"):
            raise ValueError("requirement_id must use prefix req-")
        if not _has_opaque_prefix(self.project_id, "prj-"):
            raise ValueError("project_id must use prefix prj-")
        return self


class CostMapStatus(BaseModel):
    """Independent linkage, coverage, bundle, and counting decisions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    link_resolution: Literal["linked", "unlinked", "ambiguous"]
    scope_coverage: Literal["unknown", "none", "partial", "full"]
    bundle_group_id: str | None = None
    counting_disposition: Literal["included", "excluded", "overlap"]
    counting_reason: (
        Literal[
            "out_of_scope",
            "duplicate",
            "superseded",
            "non_capex",
            "overlap_avoidance",
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def _validate_counting_reason(self) -> "CostMapStatus":
        if self.counting_disposition == "included" and self.counting_reason is not None:
            raise ValueError("included rows must not carry a counting reason")
        if self.counting_disposition != "included" and self.counting_reason is None:
            raise ValueError("excluded and overlap rows require a counting reason")
        if self.counting_disposition == "excluded" and self.counting_reason not in {
            "out_of_scope",
            "duplicate",
            "superseded",
            "non_capex",
        }:
            raise ValueError("invalid reason for excluded disposition")
        if (
            self.counting_disposition == "overlap"
            and self.counting_reason != "overlap_avoidance"
        ):
            raise ValueError("invalid reason for overlap disposition")
        return self


class AwardRequirementLink(BaseModel):
    """A money-free mapping from one commercial award to requirements.

    No separate commercial-amount registry exists in this slice. Therefore
    ``commercial_amount_id`` reuses, and must equal, the single ``awd-``
    identity whose amount the link describes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    award_id: str
    requirement_ids: tuple[str, ...] = Field(min_length=1)
    commercial_amount_id: str
    bundle_group_id: str | None = None

    @model_validator(mode="after")
    def _validate_ids(self) -> "AwardRequirementLink":
        if not _has_opaque_prefix(self.award_id, "awd-"):
            raise ValueError("award_id must use prefix awd-")
        if not all(_has_opaque_prefix(value, "req-") for value in self.requirement_ids):
            raise ValueError("requirement_ids must use prefix req-")
        if self.commercial_amount_id != self.award_id:
            raise ValueError("commercial_amount_id must equal award_id")
        return self


class IdentityRegistryEntry(BaseModel):
    """A supplied stable identity; allocation is intentionally out of scope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    opaque_id: str
    entity_kind: Literal["project", "award", "requirement", "event"]
    display_label: str
    state: Literal["active", "tombstoned"]
    active: bool
    aliases: tuple[str, ...] = ()
    validation_group_id: str

    @model_validator(mode="after")
    def _validate_identity(self) -> "IdentityRegistryEntry":
        prefixes = {
            "project": "prj-",
            "award": "awd-",
            "requirement": "req-",
            "event": "evt-",
        }
        required_prefix = prefixes[self.entity_kind]
        if (
            not self.opaque_id.startswith(required_prefix)
            or not self.opaque_id[len(required_prefix) :]
        ):
            raise ValueError(f"opaque_id must use prefix {required_prefix}")
        if self.state == "tombstoned" and self.active:
            raise ValueError("tombstoned identity cannot be active")
        if self.state == "active" and not self.active:
            raise ValueError("active identity must be active")
        return self


class MoneyInterval(BaseModel):
    """A monetary value or interval expressed in its disclosed currency."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    currency: str
    price_basis: PriceBasis
    basis_year: int | None
    ownership_basis: str
    scope_basis: str
    capex_basis: str
    value_basis: Literal[
        "point",
        "range",
        "band",
        "backlog",
        "not_public",
        "lease_contract",
        "combined",
        "midstream",
    ]
    bound_type: Literal["point", "floor", "ceiling", "closed_range", "open_range"]
    low_value: Decimal | None = Field(default=None, allow_inf_nan=True)
    high_value: Decimal | None = Field(default=None, allow_inf_nan=True)
    source_precision: str

    @model_validator(mode="after")
    def _validate_bounds(self) -> "MoneyInterval":
        if self.bound_type not in _ALLOWED_BOUNDS_BY_VALUE_BASIS[self.value_basis]:
            raise ValueError(
                f"bound_type {self.bound_type} is incompatible with "
                f"value_basis {self.value_basis}"
            )
        if self.value_basis == "not_public" and (
            self.low_value is not None or self.high_value is not None
        ):
            raise ValueError("not_public must not carry an amount")
        if self.bound_type == "point" and (
            self.low_value is None
            or self.high_value is None
            or not self.low_value.is_finite()
            or not self.high_value.is_finite()
            or self.low_value != self.high_value
        ):
            raise ValueError("point bounds must be equal and finite")
        if self.bound_type != "point" and any(
            value is not None and not value.is_finite()
            for value in (self.low_value, self.high_value)
        ):
            raise ValueError("money bounds must be finite")
        if self.bound_type == "floor" and (
            self.low_value is None or self.high_value is not None
        ):
            raise ValueError("floor requires a low value and an open high side")
        if self.bound_type == "ceiling" and (
            self.low_value is not None or self.high_value is None
        ):
            raise ValueError("ceiling requires an open low side and a high value")
        if self.bound_type == "closed_range" and (
            self.low_value is None or self.high_value is None
        ):
            raise ValueError("closed_range requires both bounds")
        if (
            self.bound_type == "open_range"
            and self.value_basis != "not_public"
            and ((self.low_value is None) == (self.high_value is None))
        ):
            raise ValueError("open_range must retain an open side")
        if (
            self.low_value is not None
            and self.high_value is not None
            and self.low_value > self.high_value
        ):
            raise ValueError("low_value must not exceed high_value")
        return self
