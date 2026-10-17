"""Curated public offshore evidence, independent of the Gulf-only ORM.

Unknown facts remain null. Text admission is fail-closed against an exact,
human/independent-review inventory; this is deliberately not a name recognizer.
Never populate this inventory by copying report prose or contact information.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Source(str, Enum):
    UK_HSE = "uk_hse"
    OPRED = "opred"
    BSEE = "bsee"
    IOGP = "iogp"
    HAVTIL = "havtil"
    NOPSEMA = "nopsema"
    IADC = "iadc"
    CSB = "csb"
    SEC = "sec"


SOURCE_HOSTS = {
    "uk_hse": {"resources.hse.gov.uk", "notices.hse.gov.uk", "www.hse.gov.uk"},
    "opred": {"itportal.energysecurity.gov.uk"},
    "bsee": {"www.bsee.gov"},
    "iogp": {"data.iogp.org", "www.iogp.org"},
    "havtil": {"www.havtil.no"},
    "nopsema": {"www.nopsema.gov.au"},
    "iadc": {"iadc.org"},
    "csb": {"www.csb.gov"},
    "sec": {"www.sec.gov"},
}
AGENCIES = {
    "uk_hse": "UK Health and Safety Executive",
    "opred": "OPRED",
    "bsee": "BSEE",
    "iogp": "IOGP",
    "havtil": "Havtil",
    "nopsema": "NOPSEMA",
    "iadc": "IADC",
    "csb": "US CSB",
    "sec": "SEC",
}
Operation = Literal[
    "drilling",
    "well control",
    "riser or BOP handling",
    "lifting",
    "dropped object",
    "diving",
    "marine",
    "process release",
    "other",
]
FailureMode = Literal[
    "separation",
    "dropped object",
    "loss of well control",
    "equipment failure",
    "loss of containment",
    "lifting failure",
    "other",
    "not established",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, allow_inf_nan=False
    )


class Event(StrictModel):
    event_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    event_date: date | datetime
    country: str = Field(pattern=r"^[A-Z]{2}$")
    basin_or_area: str = Field(min_length=1)
    field: str | None = None
    block_or_lease: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    installation_name: str = Field(min_length=1)
    installation_aliases: list[str] = Field(default_factory=list)
    installation_type: str | None = None
    operation: Operation
    equipment: list[str] = Field(default_factory=list)
    failure_mode: FailureMode
    failure_summary: str = Field(min_length=1)
    causes_as_stated: list[str] = Field(default_factory=list)
    fatalities: int | None = Field(default=None, ge=0, strict=True)
    injuries: int | None = Field(default=None, ge=0, strict=True)
    release_substance: str | None = None
    release_quantity: float | None = Field(default=None, ge=0)
    release_unit: str | None = None
    damage: str | None = None
    official_downtime_days: float | None = Field(default=None, ge=0)
    organisations: list[str] = Field(default_factory=list)

    @field_validator("event_date", mode="before")
    @classmethod
    def utc_or_date(cls, value):
        if isinstance(value, str):
            value = (
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                if "T" in value
                else date.fromisoformat(value)
            )
        if isinstance(value, datetime):
            if value.tzinfo is None:
                raise ValueError("a published time needs an explicit timezone")
            return value.astimezone(timezone.utc)
        return value

    @field_validator("failure_summary")
    @classmethod
    def short_paraphrase(cls, value):
        if len(value.split()) > 50:
            raise ValueError("failure paraphrase exceeds 50 words")
        return value

    @model_validator(mode="after")
    def release_units(self):
        if self.release_quantity is not None and (
            not self.release_unit or not self.release_substance
        ):
            raise ValueError("a release quantity requires substance and unit")
        return self


class SourceDocument(StrictModel):
    event_id: str = Field(min_length=1)
    source: Source
    source_ref: str = Field(min_length=1)
    title: str = Field(min_length=1)
    doc_type: Literal[
        "improvement notice",
        "prohibition notice",
        "direction",
        "investigation report",
        "alert",
        "release notice",
        "filing",
    ]
    legal_provision: str | None = None
    issue_date: date | None = None
    compliance_date: date | None = None
    status: str = Field(min_length=1)
    url: str
    access_date: date
    licence: str = Field(min_length=1)
    evidence_level: Literal["regulator", "industry alert", "company"]
    access_status: Literal["public", "cached"]
    summary: str = Field(min_length=1)
    association_basis: str = "published installation, country and event date"

    @model_validator(mode="after")
    def official_public_source(self):
        url = urlsplit(self.url)
        if (
            url.scheme != "https"
            or url.hostname not in SOURCE_HOSTS[self.source.value]
            or url.username
            or url.password
        ):
            raise ValueError("source URL must identify the official public site")
        if self.issue_date and self.access_date < self.issue_date:
            raise ValueError("access precedes publication")
        level = (
            "company"
            if self.source == Source.SEC
            else "industry alert"
            if self.source in {Source.IADC, Source.IOGP}
            else "regulator"
        )
        if self.evidence_level != level:
            raise ValueError("evidence level does not match source authority")
        return self

    @property
    def citation(self):
        issued = (
            self.issue_date.isoformat()
            if self.issue_date
            else "issue date not published"
        )
        text = (
            f"{AGENCIES[self.source.value]}, {self.doc_type} {self.source_ref}, "
            f'"{self.title}", {issued}. {self.url} '
            f"(accessed {self.access_date.isoformat()}). Licence: {self.licence}."
        )
        if self.licence == "OGL-3.0":
            text += " Contains public sector information licensed under the Open Government Licence v3.0."
        return text


class ReviewReceipt(StrictModel):
    """A reviewer attestation bound to exact normalized collection bytes."""

    verdict: Literal["pass"]
    reviewer_role: Literal["independent_agent"]
    reviewed_event_ids: list[str] = Field(min_length=1)
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def text_values(value):
    """Walk every string value, including nested extension fields before parsing."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from text_values(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from text_values(item)


def check_privacy(value, reviewed_text):
    """Reject unreviewed text and contact patterns without echoing suspect data.

    The reviewed inventory is an explicit curation attestation, not an automated
    guarantee that arbitrary language contains no names. Independent source
    review must check this inventory as well as the event/source rows.
    """
    allowed = set(reviewed_text)
    check_contacts([value, reviewed_text])
    for item in [*text_values(value), *allowed]:
        if item not in allowed:
            raise ValueError(
                "privacy: unreviewed text or contact data; admission refused"
            )


def check_contacts(value):
    """Screen identity exports too; their completeness needs separate review."""
    for item in text_values(value):
        if re.search(r"[\w.+-]+@[\w.-]+|\+\d[\d ()-]{8,}", item):
            raise ValueError("privacy: contact data; admission refused")
