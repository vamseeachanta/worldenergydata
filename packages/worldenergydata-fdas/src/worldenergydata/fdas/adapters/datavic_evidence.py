"""Validate and retain local DataVic interpretation evidence without I/O.

Citations are opaque references: metadata validation does not qualify their
contents, licence currency, field membership, depth datum or drilling activity.
"""

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from .datavic_wells import (
    DataVicInputError,
    DataVicWells,
    _collection,
    read_datavic_wells,
)
from .wells import require_text


@dataclass(frozen=True)
class DevelopmentLink:
    """Caller-supplied interpretation and its unverified evidence reference."""

    site_id: str
    development: str
    evidence: str


@dataclass(frozen=True)
class DataVicEvidence:
    """Immutable snapshot of validated metadata, original bytes and wells.

    source_vintage=None explicitly records unknown vintage. Unknown depth units
    retain null normalized depth. Neither state supplies engineering evidence.
    """

    schema_version: int
    raw_sha256: str
    query_url: str
    retrieved_at_utc: str
    source_vintage: str | None
    licence_identifier: str
    licence_source: str
    development_links: tuple[DevelopmentLink, ...]
    water_depth_unit: str | None
    water_depth_unit_evidence: str | None
    raw: bytes
    normalized: DataVicWells


def _fields(value: Mapping, expected: set[str]) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise DataVicInputError(
            "Evidence mapping requires exactly the documented fields"
        )


def read_datavic_evidence(raw: bytes, metadata: Mapping) -> DataVicEvidence:
    """Validate version 1 metadata before calling the existing wells reader.

    Link rows must cover exactly the exported site IDs, once each. No URL or
    evidence reference is fetched. No mapping or unit is inferred. The digest
    binds the raw bytes, not the truth of caller-supplied interpretation metadata.
    """
    _fields(metadata, set(DataVicEvidence.__dataclass_fields__) - {"raw", "normalized"})
    if type(raw) is not bytes:
        raise DataVicInputError("Raw export must be immutable bytes")
    if type(metadata["schema_version"]) is not int or metadata["schema_version"] != 1:
        raise DataVicInputError("Unsupported evidence schema_version")
    if metadata["raw_sha256"] != hashlib.sha256(raw).hexdigest():
        raise DataVicInputError("Raw export digest mismatch")
    for key in (
        "query_url",
        "retrieved_at_utc",
        "licence_identifier",
        "licence_source",
    ):
        require_text(metadata[key], key)
    if re.search(r"[\s\x00-\x1f\x7f-\x9f]", metadata["query_url"]):
        raise DataVicInputError("query_url must not contain whitespace or controls")
    url = urlsplit(metadata["query_url"])
    if url.scheme not in {"https", "http"} or not url.hostname:
        raise DataVicInputError("query_url must be an absolute HTTP(S) URL")
    try:
        _ = url.port  # Access validates numeric syntax and the port range.
    except ValueError as exc:
        raise DataVicInputError("query_url must have a valid port") from exc
    retrieved_text = metadata["retrieved_at_utc"]
    # Check the written offset: fromisoformat can discard fractional offsets.
    if not re.search(r"(?:Z|[+-]00(?::?00){0,2}(?:[.,]0+)?)$", retrieved_text):
        raise DataVicInputError("retrieved_at_utc must be timezone-aware UTC")
    try:
        retrieved = datetime.fromisoformat(retrieved_text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DataVicInputError("retrieved_at_utc must be timezone-aware UTC") from exc
    if retrieved.tzinfo is None or retrieved.utcoffset() != timedelta(0):
        raise DataVicInputError("retrieved_at_utc must be timezone-aware UTC")
    if metadata["source_vintage"] is not None:
        require_text(metadata["source_vintage"], "source_vintage")
    unit, evidence = metadata["water_depth_unit"], metadata["water_depth_unit_evidence"]
    if unit is not None and (not isinstance(unit, str) or unit not in {"m", "ft"}):
        raise DataVicInputError(
            "water_depth_unit must be m, ft (international), or None"
        )
    if unit is not None or evidence is not None:
        require_text(evidence, "water_depth_unit_evidence")
    rows = metadata["development_links"]
    if not isinstance(rows, list):
        raise DataVicInputError("development_links must be a list")
    links = {}
    retained = []
    for row in rows:
        _fields(row, {"site_id", "development", "evidence"})
        for key in row:
            require_text(row[key], key)
        site_id = row["site_id"]
        if not re.fullmatch(r"0|-?[1-9][0-9]*", site_id) or site_id in links:
            raise DataVicInputError("Malformed or duplicate development link site_id")
        links[site_id] = row["development"]
        retained.append(DevelopmentLink(**row))
    identifiers = set()
    for feature in _collection(raw)["features"]:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise DataVicInputError("Expected GeoJSON Feature")
        props = feature.get("properties")
        if not isinstance(props, dict) or type(props.get("siteid")) is not int:
            raise DataVicInputError("Well properties require integer siteid")
        identifiers.add(str(props["siteid"]))
    if identifiers != links.keys():
        raise DataVicInputError(
            "Explicit development links must exactly cover exported site IDs"
        )
    normalized = read_datavic_wells(
        raw, development_by_site_id=links, water_depth_unit=unit
    )
    snapshot = dict(metadata) | {"development_links": tuple(retained)}
    return DataVicEvidence(**snapshot, raw=raw, normalized=normalized)
