# ABOUTME: Offline county recorder access and title-chain feasibility catalog.
# ABOUTME: Separates public access, automation terms, and unevaluated title evidence.
"""Human-reviewed source metadata only; never connects to a recorder portal.

Classification policy: issue #914, acceptance criteria (2026). These are
categorical decisions, without fee assumptions or numerical scoring equations.
"""

import argparse
import json
from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    computed_field,
    field_validator,
    model_validator,
)

# Issue #914 requires substantive evidence for each county: empty text is invalid.
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
AccessClass = Literal[
    "public-online",
    "manual-download",
    "paid-gated",
    "in-person-only",
    "do-not-automate",
]


class Evidence(BaseModel):
    """Dated observation; an opened page does not establish reuse permission."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    url: HttpUrl
    title: Text
    observed_on: date
    status: Literal["opened", "unavailable"]
    finding: Text


class RecorderCoverage(BaseModel):
    """Unknown facts use null or NOT_EVALUATED, never guessed access rights."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    state: Text
    county: Text
    source_family: Literal["county-recorder"] = "county-recorder"
    recorder_url: HttpUrl
    search_url: HttpUrl | None = None
    priority_basis: Text
    readiness_evidence: tuple[Text, ...] = Field(min_length=1)
    regulator_readiness: Literal["downloaded", "partial", "configured-only", "missing"]
    search_capabilities: Text
    document_types: tuple[Text, ...] = Field(min_length=1)
    cost_constraints: Text
    coverage_limits: Text
    legal_caveats: Text
    next_action: Text
    sources: tuple[Evidence, ...] = Field(min_length=1)
    online_search: bool | None = None
    free_images: bool | None = None
    account_required: bool | None = None
    payment_required: bool | None = None
    in_person_required: bool | None = None
    bulk_available: bool | None = None
    automation_terms: Literal["allowed", "prohibited", "NOT_EVALUATED"] = (
        "NOT_EVALUATED"
    )
    title_chain_status: Literal["NOT_EVALUATED"] = "NOT_EVALUATED"

    @field_validator("state", "county")
    @classmethod
    def normalize_identity(cls, value: str, info) -> str:
        value = value.strip().upper()
        if info.field_name == "county":
            for suffix in (" COUNTY", " PARISH"):
                value = value.removesuffix(suffix)
        if not value:
            raise ValueError("County identity must not be empty")
        return value

    @field_validator("readiness_evidence", "document_types", "sources", mode="before")
    @classmethod
    def freeze_sequences(cls, value):
        return tuple(value) if isinstance(value, list) else value

    @computed_field
    @property
    def classification(self) -> AccessClass:
        """Conservative truth table; an unknown is not a finding of absence."""
        if self.automation_terms == "prohibited" or not any(
            source.status == "opened" for source in self.sources
        ):
            return "do-not-automate"
        if self.in_person_required is True:
            return "in-person-only"
        if self.online_search is not True:
            return "do-not-automate"
        if self.payment_required is True or self.account_required is True:
            return "paid-gated"
        if self.payment_required is None or self.account_required is None:
            return "do-not-automate"
        if self.free_images is True:
            return "public-online"
        return "manual-download"

    @computed_field
    @property
    def automation_feasibility(
        self,
    ) -> Literal["blocked", "NOT_EVALUATED", "candidate-for-review"]:
        """A candidate still requires explicit approval before any acquisition."""
        if self.classification in {"do-not-automate", "in-person-only", "paid-gated"}:
            return "blocked"
        if self.automation_terms == "allowed" and self.bulk_available is True:
            return "candidate-for-review"
        return "NOT_EVALUATED"


class CoverageCatalog(BaseModel):
    """Bounded county selection; not a national source-readiness inventory."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    counties: tuple[RecorderCoverage, ...]

    @model_validator(mode="after")
    def unique_counties(self):
        keys = [(record.state, record.county) for record in self.counties]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate county identity")
        return self

    def get(self, state: str, county: str) -> RecorderCoverage:
        """Exact normalized lookup; a substring cannot select a different county."""
        state = state.strip().upper()
        county = county.strip().upper().removesuffix(" COUNTY").removesuffix(" PARISH")
        for record in self.counties:
            if (record.state, record.county) == (state, county):
                return record
        raise KeyError((state, county))

    def priority_counties(
        self, states: list[str] | None = None
    ) -> list[RecorderCoverage]:
        """Readiness tiers from issue #911; alphabetical tie-break, no volume proxy."""
        tiers = ("downloaded", "partial", "configured-only", "missing")
        selected = (
            None if states is None else {state.strip().upper() for state in states}
        )
        return sorted(
            (r for r in self.counties if selected is None or r.state in selected),
            key=lambda r: (tiers.index(r.regulator_readiness), r.state, r.county),
        )


def load_catalog(path: Path | str | None = None) -> CoverageCatalog:
    """Load bundled metadata or an explicit local file, with no network fallback."""
    resource = (
        files(__package__).joinpath("data", "recorder_coverage.json")
        if path is None
        else Path(path)
    )
    # Computed answers are exported for consumers but recomputed on input.
    payload = json.loads(resource.read_text(encoding="utf-8"))
    for record in payload.get("counties", []):
        record.pop("classification", None)
        record.pop("automation_feasibility", None)
    return CoverageCatalog.model_validate(payload)


def main(argv: list[str] | None = None) -> None:
    """Export a priority-ordered catalog for human review, without acquiring data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, help="Explicit local catalog JSON")
    parser.add_argument("--state", action="append", help="Filter by state; repeatable")
    args = parser.parse_args(argv)
    catalog = load_catalog(args.catalog)
    selected = CoverageCatalog(counties=catalog.priority_counties(args.state))
    print(selected.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
