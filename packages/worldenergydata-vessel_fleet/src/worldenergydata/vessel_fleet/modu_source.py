"""MODU source evidence only; no host envelope or hydrodynamic model.

Contract requirements: issue #1050, with consumer boundary in issue #1618.
No engineering defaults, conversions, inferred identities or acceptance limits.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    field_validator,
)

PUBLIC_RECORD = Path(__file__).parent / "data" / "public_modu_source.json"
# Units are the contract's input vocabulary, not numerical conversion factors.
REQUIRED_UNITS = {
    "length": "m",
    "beam": "m",
    "depth": "m",
    "draft": "m",
    "displacement": "t",
    "cog_x": "m",
    "cog_y": "m",
    "cog_z": "m",
    "i_xx": "t*m^2",
    "i_yy": "t*m^2",
    "i_zz": "t*m^2",
    "i_xy": "t*m^2",
    "i_xz": "t*m^2",
    "i_yz": "t*m^2",
}


class EvidenceModel(BaseModel):
    """Reject undeclared fields instead of accepting readiness assertions."""

    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, allow_inf_nan=False
    )

    @field_validator("*", mode="after")
    @classmethod
    def nonempty_strings(cls, value):
        if isinstance(value, str) and not value:
            raise ValueError("Empty evidence text")
        return value


class Citation(EvidenceModel):
    source_id: str
    locator: str


class BoundCitation(Citation):
    physical_id: str
    condition_id: str


class Source(EvidenceModel):
    source_id: str
    url: str
    captured_at: datetime
    http_status: StrictInt
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")  # SHA-256: FIPS 180-4 (2015).
    size_bytes: StrictInt = Field(gt=0)
    origin: Literal["public", "synthetic", "private", "licensed"]
    redistribution: Literal["facts_only", "unknown", "prohibited"]
    rights_evidence: str

    @field_validator("url")
    @classmethod
    def public_url(cls, value):
        parts = urlsplit(value)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
        ):
            raise ValueError("Source must have a credential-free HTTPS URL")
        return value

    @field_validator("captured_at")
    @classmethod
    def aware_time(cls, value):
        if value.tzinfo is None or value > datetime.now(timezone.utc):
            raise ValueError("Capture must be timezone aware and not in the future")
        return value


class Fallback(EvidenceModel):
    identifier: str
    review_ref: str
    evidence: Citation


class Alias(EvidenceModel):
    alias: str
    physical_id: str
    imo: str | None
    evidence: Citation


class Condition(EvidenceModel):
    condition_id: str
    physical_id: str
    description: str
    evidence: Citation


class Frame(EvidenceModel):
    origin: str
    axes: str
    inertia_reference: Literal["centre_of_gravity"]
    inertia_convention: Literal["tensor_components"]
    evidence: BoundCitation


class Quantity(EvidenceModel):
    value: StrictFloat | StrictInt
    unit: str
    evidence: BoundCitation


class SourceRecord(EvidenceModel):
    schema_version: Literal["1"]
    record_id: str
    rig_source_id: str
    rig_class: Literal["drillship", "semi_submersible", "floater_unspecified"]
    rig_evidence: Citation
    physical_id: str | None
    imo: str | None
    fallback: Fallback | None
    aliases: list[Alias]
    identity_evidence: Citation | None
    geometry_evidence: Citation | None
    condition: Condition | None
    frame: Frame | None
    quantities: dict[str, Quantity]
    sources: list[Source] = Field(min_length=1)
    missing_evidence: dict[str, str]

    @field_validator("missing_evidence")
    @classmethod
    def missing_reasons(cls, value):
        if any(not key.strip() or not reason.strip() for key, reason in value.items()):
            raise ValueError("Missing-evidence dispositions need nonempty reasons")
        return value


@dataclass(frozen=True)
class Assessment:
    status: Literal["COMPLETE", "NOT_EVALUATED", "REJECTED"]
    promotable: bool
    reasons: tuple[str, ...]
    record_sha256: str


def canonical_bytes(record: SourceRecord) -> bytes:
    """v1: UTF-8 JSON, sorted keys, compact separators, original array order.

    This is this source contract's encoding, not a consumer identity algorithm.
    All metadata, missing-evidence reasons and capture instants are committed.
    """
    return json.dumps(
        record.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def commitment(record: SourceRecord) -> str:
    """SHA-256 of canonical source-record bytes; FIPS 180-4 (2015), section 6.2."""
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def verify_source_bytes(record: SourceRecord, payloads: dict[str, bytes]) -> None:
    """Compare retained or independently retrieved bytes; never fetch implicitly."""
    for source in record.sources:
        if source.source_id not in payloads:
            raise ValueError("SOURCE_BYTES_MISSING:" + source.source_id)
        raw = payloads[source.source_id]
        if (
            len(raw) != source.size_bytes
            or hashlib.sha256(raw).hexdigest() != source.sha256
        ):
            raise ValueError("SOURCE_BYTES_MISMATCH:" + source.source_id)


def assess(
    record: SourceRecord, *, source_bytes: dict[str, bytes] | None = None
) -> Assessment:
    """Qualify source completeness, never certify the truth of source assertions.

    A positive disposition additionally requires public rights and matching bytes.
    Review references must be authenticated by the consumer's review process.
    """
    rejected, missing, withheld = set(), set(), set()
    sources = {source.source_id: source for source in record.sources}
    if len(sources) != len(record.sources):
        rejected.add("DUPLICATE_SOURCE_ID")

    def cite(citation):
        if citation.source_id not in sources:
            rejected.add("UNKNOWN_SOURCE:" + citation.source_id)

    def bound(citation):
        cite(citation)
        if citation.physical_id != record.physical_id:
            rejected.add("PHYSICAL_UNIT_MISMATCH")
        if record.condition and citation.condition_id != record.condition.condition_id:
            rejected.add("LOADING_MISMATCH")

    cite(record.rig_evidence)
    for source in record.sources:
        if (
            source.http_status != 200
        ):  # HTTP Semantics, RFC 9110 (2022), section 15.3.1.
            missing.add("SOURCE_UNAVAILABLE:" + source.source_id)
        if source.origin != "public":
            withheld.add("NON_PUBLIC_SOURCE:" + source.source_id)
        if source.redistribution != "facts_only":
            missing.add("RIGHTS_NOT_CLEARED:" + source.source_id)

    if record.rig_class == "floater_unspecified":
        missing.add("RIG_CLASS_MISSING")
    if not record.physical_id or not (record.imo or record.fallback):
        missing.add("IDENTITY_MISSING")
    if record.imo and record.fallback:
        rejected.add("MULTIPLE_IDENTITY_BASES")
    # Deliberately no checksum-based identity inference: a format alone proves no identity.
    if record.imo and (
        len(record.imo) != 7 or not record.imo.isascii() or not record.imo.isdigit()
    ):
        # IMO, Ship Identification Number Scheme, explanatory page (2026 capture):
        # https://www.imo.org/en/OurWork/MSAS/Pages/IMO-identification-number-scheme.aspx
        rejected.add("IMO_FORMAT")
    if record.fallback:
        cite(record.fallback.evidence)
    if record.identity_evidence:
        cite(record.identity_evidence)
    else:
        missing.add("IDENTITY_EVIDENCE_MISSING")
    if record.geometry_evidence:
        cite(record.geometry_evidence)
    else:
        missing.add("GEOMETRY_MISSING")
    if not record.aliases:
        missing.add("ALIASES_MISSING")
    seen = {}
    for alias in record.aliases:
        cite(alias.evidence)
        key = alias.alias.casefold()
        target = (alias.physical_id, alias.imo)
        if key in seen and seen[key] != target:
            rejected.add("ALIAS_COLLISION")
        seen[key] = target
        if alias.physical_id != record.physical_id:
            rejected.add("PHYSICAL_UNIT_MISMATCH")
        if alias.imo and alias.imo != record.imo:
            rejected.add("IMO_CONFLICT")

    if not record.condition:
        missing.add("LOADING_MISSING")
    else:
        cite(record.condition.evidence)
        if record.condition.physical_id != record.physical_id:
            rejected.add("PHYSICAL_UNIT_MISMATCH")
    if not record.frame:
        missing.add("FRAME_MISSING")
    else:
        bound(record.frame.evidence)
    for key, unit in REQUIRED_UNITS.items():
        quantity = record.quantities.get(key)
        if quantity is None:
            missing.add("MISSING:" + key)
            if key not in record.missing_evidence:
                missing.add("MISSING_DISPOSITION:" + key)
            continue
        bound(quantity.evidence)
        if key in record.missing_evidence:
            rejected.add("CONTRADICTORY_DISPOSITION:" + key)
        if quantity.unit != unit:
            rejected.add("UNIT_MISMATCH:" + key)
        # Strict positivity expresses physical quantities, not an engineering limit.
        if (
            key
            in {
                "length",
                "beam",
                "depth",
                "draft",
                "displacement",
                "i_xx",
                "i_yy",
                "i_zz",
            }
            and quantity.value <= 0
        ):
            rejected.add("NONPOSITIVE:" + key)
    if set(record.quantities) - set(REQUIRED_UNITS):
        rejected.add("UNKNOWN_QUANTITY")
    if source_bytes is not None:
        verify_source_bytes(record, source_bytes)
    else:
        withheld.add("SOURCE_BYTES_NOT_VERIFIED")
    # Synthetic fixtures are complete evidence shapes, never public records.
    if all(source.origin == "synthetic" for source in record.sources):
        withheld.discard("SOURCE_BYTES_NOT_VERIFIED")
    status = "REJECTED" if rejected else "NOT_EVALUATED" if missing else "COMPLETE"
    reasons = tuple(sorted(rejected | missing | withheld))
    return Assessment(
        status, status == "COMPLETE" and not reasons, reasons, commitment(record)
    )


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_KEY:" + key)
        result[key] = value
    return result


def load_record(path: str | Path = PUBLIC_RECORD) -> SourceRecord:
    """Load a strict source record, rejecting duplicate JSON object keys."""
    document = json.loads(
        Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object
    )
    return SourceRecord.model_validate(document)
