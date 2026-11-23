"""Validate caller-supplied publication assertions without fetching their URLs."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from worldenergydata.cost.timeseries.portfolio_trace import PortfolioTrace
from worldenergydata.cost.timeseries.project_trace import DateInterval


class _Locator(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    url: str
    location: str
    quoted_text: str

    @field_validator("url")
    @classmethod
    def _url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or any(char.isspace() or ord(char) < 32 for char in value)
        ):
            raise ValueError("locator requires an HTTP(S) URL without credentials")
        # Accessing port also rejects malformed and out-of-range port text.
        _ = parsed.port
        return value

    @field_validator("location", "quoted_text")
    @classmethod
    def _nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("locator requires a location and supporting quote")
        return value


class _Annotation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    event_id: str
    source_table_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_url: str
    publication_date: str | None
    date_precision: Literal["year", "month", "day", "unknown"]
    source_locator: _Locator

    def interval(self) -> DateInterval | None:
        if self.publication_date is None and self.date_precision == "unknown":
            return None
        if self.publication_date is None or not re.fullmatch(
            r"[0-9]{4}(?:-[0-9]{2}){0,2}", self.publication_date
        ):
            raise ValueError("publication date must use explicit ISO precision")
        result = DateInterval.from_text(self.publication_date)
        if result.precision != self.date_precision:
            raise ValueError("publication date precision mismatch")
        return result


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def apply_publication_evidence(trace: PortfolioTrace, payload: bytes) -> PortfolioTrace:
    """Return a new snapshot, or raise before any output on unsupported evidence.

    The input is a JSON array of explicit assertions, including null/unknown dates.
    URL syntax and snapshot bindings are checked offline; citation authenticity
    and whether its quote supports the date still require independent review.
    Only availability and retained evidence change; no cost qualification follows.
    """
    rows = json.loads(payload, object_pairs_hook=_unique_keys)
    if not isinstance(rows, list):
        raise ValueError("publication evidence must be a JSON array")
    digest = hashlib.sha256(payload).hexdigest()
    previous = trace.input_sha256.get("publication_evidence")
    if previous is not None and previous != digest:
        raise ValueError("conflicting publication evidence input digest")
    events = {event.event_id: event for event in trace.events}
    if len(events) != len(trace.events):
        raise ValueError("duplicate event identity in snapshot")
    annotations = {}
    for row in rows:
        annotation = _Annotation.model_validate(row)
        available = annotation.interval()
        event = events.get(annotation.event_id)
        if event is None:
            raise ValueError("unknown event identity")
        if trace.input_sha256.get(event.source_table) != annotation.source_table_sha256:
            raise ValueError("source table digest mismatch")
        source_url = event.source_fields.get("SOURCE_URL", "")
        _Locator._url(annotation.source_url)
        if source_url != annotation.source_url:
            raise ValueError("source URL mismatch")
        evidence = json.dumps(annotation.model_dump(), sort_keys=True)
        previous = annotations.get(event.event_id)
        retained = event.source_fields.get("PUBLICATION_EVIDENCE")
        if (previous is not None and previous != evidence) or (
            retained is not None and retained != evidence
        ):
            raise ValueError("conflicting publication evidence for event")
        if (
            event.source_available_date is not None
            and event.source_available_date != available
        ):
            raise ValueError("conflicting existing publication date")
        annotations[event.event_id] = evidence
        events[event.event_id] = replace(
            event,
            source_available_date=available,
            source_fields={**event.source_fields, "PUBLICATION_EVIDENCE": evidence},
        )
    return replace(
        trace,
        events=tuple(events[event.event_id] for event in trace.events),
        input_sha256={**trace.input_sha256, "publication_evidence": digest},
    )
