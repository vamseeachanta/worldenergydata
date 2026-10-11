"""Validated annual-statement discovery metadata; no disclosure values or reports."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SEED_OPERATORS = (
    "BP",
    "Chevron",
    "Shell",
    "Equinor",
    "Aker BP",
    "TotalEnergies",
    "ExxonMobil",
    "Murphy Oil",
    "Hess",
)
YEARS = frozenset(range(2020, 2025))
Channel = Literal["annual_report", "sec_10k", "sec_20f", "sustainability_report"]
Status = Literal["verified", "missing", "known_unavailable"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("absolute HTTP(S) URL required")
    if parsed.username or parsed.password or any(c.isspace() for c in value):
        raise ValueError("credentials and whitespace forbidden in URL")
    return value


def validate_utc(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("UTC retrieval timestamp required")
    return value


class SourceObservation(StrictModel):
    """A response observation, including refusal responses; never an access grant."""

    url: str
    retrieved_at_utc: str
    http_status: int = Field(ge=100, le=599)
    content_type: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(ge=0)
    terms_url: str
    terms_retrieved_at_utc: str
    terms_wording: str = Field(min_length=1)

    _urls = field_validator("url", "terms_url")(validate_url)
    _dates = field_validator("retrieved_at_utc", "terms_retrieved_at_utc")(validate_utc)


class DocumentEvidence(SourceObservation):
    listing_url: str
    channel: Channel
    operator_name: str = Field(min_length=1)
    fiscal_year: int = Field(ge=2020, le=2024)
    identity_quote: str = Field(min_length=1)
    identity_locator: str = Field(min_length=1)
    http_status: Literal[200]
    size_bytes: int = Field(gt=0)
    content_type: Literal["application/pdf", "application/x-pdf"]

    _listing = field_validator("listing_url")(validate_url)


class YearCoverage(StrictModel):
    status: Status
    note: str = Field(min_length=1)
    documents: list[DocumentEvidence] = Field(default_factory=list)
    refusal_url: str | None = None
    refusal_scope: str | None = None
    finding_quote: str | None = None

    @model_validator(mode="after")
    def check_evidence(self) -> YearCoverage:
        if (self.status == "verified") != bool(self.documents):
            raise ValueError("only verified years require document evidence")
        if self.status == "known_unavailable":
            if not self.refusal_url or not self.refusal_scope:
                raise ValueError("known_unavailable requires refusal URL and scope")
            validate_url(self.refusal_url)
        elif any(
            v is not None
            for v in (self.refusal_url, self.refusal_scope, self.finding_quote)
        ):
            raise ValueError("refusal fields only belong to known_unavailable")
        return self


class OperatorStatement(StrictModel):
    name: str = Field(min_length=1)
    primary_domains: list[str] = Field(min_length=1)
    market_context: str = Field(min_length=1)
    discovery_url: str | None
    filing_channels: list[Channel] = Field(min_length=1)
    discovery_notes: str = Field(min_length=1)
    observations: list[SourceObservation]
    coverage_by_year: dict[int, YearCoverage]

    @model_validator(mode="after")
    def check_coverage(self) -> OperatorStatement:
        if set(self.coverage_by_year) != YEARS:
            raise ValueError("coverage must contain exactly 2020–2024")
        if len(set(self.filing_channels)) != len(self.filing_channels):
            raise ValueError("duplicate filing channel")
        if any(not d or "/" in d or ":" in d for d in self.primary_domains):
            raise ValueError("primary_domains must contain host names only")
        if self.discovery_url is not None:
            self.check_primary_url(self.discovery_url)
        for year, coverage in self.coverage_by_year.items():
            for document in coverage.documents:
                self.check_primary_url(document.url)
                self.check_primary_url(document.listing_url)
                if not any(
                    o.url == document.listing_url and o.http_status == 200
                    for o in self.observations
                ):
                    raise ValueError("document listing requires successful observation")
                if not any(
                    o.url == document.terms_url
                    and o.http_status == 200
                    and o.retrieved_at_utc == document.terms_retrieved_at_utc
                    for o in self.observations
                ):
                    raise ValueError(
                        "document terms require dated successful observation"
                    )
                if document.operator_name != self.name or document.fiscal_year != year:
                    raise ValueError("document identity must match operator and year")
                if document.channel not in self.filing_channels:
                    raise ValueError("document channel must be declared")
            if coverage.status == "known_unavailable":
                matches = [
                    o for o in self.observations if o.url == coverage.refusal_url
                ]
                refusal = any(o.http_status in {403, 429} for o in matches)
                finding = any(o.http_status == 200 for o in matches) and bool(
                    coverage.finding_quote
                )
                if not (refusal or finding):
                    raise ValueError(
                        "refusal or explicit source finding requires response evidence"
                    )
        return self

    def check_primary_url(self, value: str) -> None:
        validate_url(value)
        host = urlsplit(value).hostname
        if not any(
            host == d or (host or "").endswith("." + d) for d in self.primary_domains
        ):
            raise ValueError("source must be operator-owned or regulator-owned")


class StatementRegistry(StrictModel):
    schema_version: Literal[1]
    operators: list[OperatorStatement] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_names(self) -> StatementRegistry:
        names = [row.name for row in self.operators]
        if len(set(names)) != len(names):
            raise ValueError("duplicate operator name")
        return self


def load_registry(path: str | Path, *, require_seed: bool = True) -> StatementRegistry:
    registry = StatementRegistry.model_validate_json(Path(path).read_bytes())
    if require_seed and {row.name for row in registry.operators} != set(SEED_OPERATORS):
        raise ValueError("registry must contain exactly the nine seed operators")
    return registry


def emit_registry(path: str | Path, *, require_seed: bool = True) -> bytes:
    """Emit the canonical metadata manifest from retained observation inputs."""
    registry = load_registry(path, require_seed=require_seed)
    return (
        json.dumps(registry.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    ).encode()


def derive_coverage(row: OperatorStatement) -> dict:
    """Bounds and channel years reflect verified evidence only, never discovery."""
    verified = sorted(
        y for y, c in row.coverage_by_year.items() if c.status == "verified"
    )
    channels = {
        channel: sorted(
            y
            for y, c in row.coverage_by_year.items()
            if any(d.channel == channel for d in c.documents)
        )
        for channel in row.filing_channels
    }
    return {
        "earliest_covered_year": min(verified) if verified else None,
        "latest_verified_year": max(verified) if verified else None,
        "coverage_by_year": {
            y: c.status for y, c in sorted(row.coverage_by_year.items())
        },
        "coverage_by_channel": channels,
    }
