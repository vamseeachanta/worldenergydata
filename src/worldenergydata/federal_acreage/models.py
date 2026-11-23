"""Validated contracts for one-section quarter-quarter acreage screening."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

QUARTERS = {"NE", "NW", "SE", "SW"}
TITLE_GAP = (
    "Federal land records are not evidence of title. "
    "County recorder / title-chain records were NOT evaluated."
)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SourceRef(Contract):
    source_id: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    kind: Literal["fixture", "live"]
    url: str | None = None
    retrieved_at: datetime
    license_note: str = Field(min_length=1)

    @field_validator("retrieved_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("retrieved_at requires a timezone")
        return value


class SourcedValue(Contract):
    value: float | None
    status: Literal["available", "unavailable", "ambiguous"]
    source_id: str | None
    note: str | None = None

    @model_validator(mode="after")
    def validate_evidence(self) -> SourcedValue:
        if self.status == "available":
            if self.value is None or not self.source_id or self.value < 0:
                raise ValueError(
                    "Available acreage requires a nonnegative value and source"
                )
        elif self.value is not None or self.source_id is not None or not self.note:
            raise ValueError(
                "Unknown acreage requires null value/source and an explanation"
            )
        return self


def valid_aliquots(values: list[str]) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError("Duplicate aliquots")
    allowed = {f"{a}-{b}" for a in QUARTERS for b in QUARTERS}
    if any(value not in allowed for value in values):
        raise ValueError("Only quarter-quarter aliquots are supported")
    return values


class TractOfInterest(Contract):
    tract_id: str = Field(min_length=1)
    label: str
    state: str
    principal_meridian: str
    township: str
    range: str
    section: int = Field(ge=1, le=36)
    aliquots: list[str] = Field(min_length=1)
    gross_area_acres: float = Field(gt=0)

    @field_validator("aliquots")
    @classmethod
    def validate_aliquots(cls, values: list[str]) -> list[str]:
        return valid_aliquots(values)

    @model_validator(mode="after")
    def validate_gross(self) -> TractOfInterest:
        if self.gross_area_acres != 40.0 * len(self.aliquots):
            raise ValueError("Gross area must equal 40 acres per quarter-quarter")
        return self


class RecordArea(Contract):
    value: float = Field(ge=0)
    unit: Literal["acres", "hectares"]


class FederalLandRecord(Contract):
    record_serial: str = Field(min_length=1)
    record_type: Literal["lease", "parcel"]
    record_status: Literal["active", "expired", "pending", "unknown"]
    effective_date: date | None = None
    expiration_date: date | None = None
    area: RecordArea
    public_lessee: str | None = None
    public_operator: str | None = None
    aliquots: list[str] | None
    source_id: str

    @field_validator("aliquots")
    @classmethod
    def validate_aliquots(cls, values: list[str] | None) -> list[str] | None:
        return None if values is None else valid_aliquots(values)

    @model_validator(mode="after")
    def validate_date_interval(self) -> FederalLandRecord:
        if (
            self.effective_date is not None
            and self.expiration_date is not None
            and self.expiration_date < self.effective_date
        ):
            raise ValueError("Expiration precedes effectiveness")
        return self


class RecordEvidence(FederalLandRecord):
    intersect_acres: SourcedValue
    area_acres: SourcedValue
    retrieved_at: datetime


class AcreageException(Contract):
    kind: Literal[
        "overlap",
        "missing_geometry",
        "non_intersecting",
        "unit_ambiguous",
        "stale_status",
    ]
    record_serials: list[str]
    acres: float | None = None
    detail: str


class AcreageRollup(Contract):
    gross_area_acres: SourcedValue
    federal_record_coverage_acres: SourcedValue
    leased_acres: SourcedValue
    expired_or_nonleased_acres: SourcedValue
    no_record_acres: SourcedValue


class TitleChainGap(Contract):
    status: Literal["not_evaluated"] = "not_evaluated"
    statement: Literal[
        "Federal land records are not evidence of title. "
        "County recorder / title-chain records were NOT evaluated."
    ] = (
        "Federal land records are not evidence of title. "
        "County recorder / title-chain records were NOT evaluated."
    )


class AcreageEvidenceResult(Contract):
    schema_version: Literal["federal-acreage-result-v1"] = "federal-acreage-result-v1"
    screening_status: Literal[
        "evidence_complete", "evidence_partial", "evidence_blocked"
    ]
    screening_reasons: list[str]
    tract: TractOfInterest
    acreage: AcreageRollup
    records: list[RecordEvidence]
    exceptions: list[AcreageException]
    title_chain_gap: TitleChainGap = Field(default_factory=TitleChainGap)
    sources: list[SourceRef]
    data_as_of: datetime
