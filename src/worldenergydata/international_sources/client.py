"""Caller-bounded, credential-free catalogue and sample collection.

A response includes its raw bytes and their digest so a caller can retain the
original separately from normalized records. Collection is sequential, with no
retry, credential handling, bulk CSV download or implicit pagination.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .argentina import Discovery, discover_resources
from .colombia import (
    Observation,
    describe_dataset,
    metadata_url,
    normalize_rows,
    rows_url,
)


@dataclass(frozen=True)
class Evidence:
    """A retrieval observation, distinct from source vintage and readiness."""

    url: str
    observed_at: datetime
    sha256: str
    size_bytes: int
    raw_bytes: bytes


@dataclass(frozen=True)
class ColombiaPage:
    """One page is a sample, regardless of whether it fills the requested limit."""

    metadata: Discovery
    observations: tuple[Observation, ...]
    metadata_evidence: Evidence
    rows_evidence: Evidence
    complete: bool = False


def _object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON object key")
        obj[key] = value
    return obj


def _reject_constant(value):
    raise ValueError("non-finite JSON number")


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite JSON number")
    return number


class SourceClient:
    """Limits are required caller inputs, not engineering acceptance criteria."""

    def __init__(self, *, timeout_seconds: float, max_bytes: int, opener=urlopen):
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self._open = opener

    def _json(self, url: str) -> tuple[dict | list, Evidence]:
        request = Request(url, headers={"Accept": "application/json"})
        with self._open(request, timeout=self.timeout_seconds) as response:
            final_url = urlsplit(response.geturl())
            if final_url.scheme != "https" or final_url.netloc != urlsplit(url).netloc:
                raise ValueError("source redirect is unverified")
            media_type = response.headers.get_content_type()
            if media_type != "application/json" and not media_type.endswith("+json"):
                raise ValueError("source returned non-JSON content")
            raw = response.read(self.max_bytes + 1)
        if len(raw) > self.max_bytes:
            raise ValueError("source response exceeds byte limit")
        try:
            payload = json.loads(
                raw,
                object_pairs_hook=_object,
                parse_constant=_reject_constant,
                parse_float=_finite_float,
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("source returned invalid JSON") from exc
        if not isinstance(payload, (dict, list)):
            raise TypeError("source JSON must be an object or array")
        evidence = Evidence(
            url,
            datetime.now(timezone.utc),
            hashlib.sha256(raw).hexdigest(),
            len(raw),
            raw,
        )
        return payload, evidence

    def argentina_package(self, dataset_id: str) -> tuple[Discovery, Evidence]:
        """Discover resources for an explicit CKAN package id, without fetching CSVs."""
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            raise ValueError("dataset_id is required")
        query = urlencode({"id": dataset_id})
        url = f"https://datos.energia.gob.ar/api/3/action/package_show?{query}"
        payload, evidence = self._json(url)
        if not isinstance(payload, dict):
            raise TypeError("CKAN response must be an object")
        discovery = discover_resources(payload)
        if discovery.dataset_id != dataset_id:
            raise ValueError("CKAN response dataset differs from requested dataset")
        return discovery, evidence

    def colombia_metadata(self, commodity: str) -> tuple[Discovery, Evidence]:
        """Collect source reuse terms and vintage without fetching production rows."""
        url = metadata_url(commodity)
        payload, evidence = self._json(url)
        if not isinstance(payload, dict):
            raise TypeError("Socrata metadata must be an object")
        discovery = describe_dataset(payload)
        if url != f"https://www.datos.gov.co/api/views/{discovery.dataset_id}.json":
            raise ValueError("response dataset differs from requested dataset")
        return discovery, evidence

    def colombia_page(self, commodity: str, *, limit: int, offset: int) -> ColombiaPage:
        """Collect metadata plus one explicit page of native monthly observations."""
        url = rows_url(commodity, limit=limit, offset=offset)
        metadata, metadata_evidence = self.colombia_metadata(commodity)
        payload, rows_evidence = self._json(url)
        observations = normalize_rows(payload, commodity=commodity)
        if len(observations) > limit:
            raise ValueError("source returned more rows than requested")
        return ColombiaPage(metadata, observations, metadata_evidence, rows_evidence)
