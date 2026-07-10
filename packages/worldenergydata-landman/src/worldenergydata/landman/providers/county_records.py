# ABOUTME: Offline county-record ownership provider backed only by validated fixtures.
# ABOUTME: Applies stable normalization/filtering without network or shared caches.

"""Fixture-only county records provider."""

import json
from dataclasses import replace
from datetime import datetime
from typing import Any, Mapping

from ..fixture_schema import (
    FixtureDataset,
    parse_fixture_bytes,
    read_custom_fixture,
    read_packaged_fixture,
)
from ..routing import SourceConfig


def _collapse(value: str) -> str:
    return " ".join(value.split())


def _state(value: str) -> str:
    return _collapse(value).upper()


def _county(value: str) -> str:
    normalized = _state(value)
    if normalized.endswith(" COUNTY"):
        normalized = normalized[: -len(" COUNTY")].rstrip()
    return normalized


def _substring(value: str) -> str:
    return _collapse(value).casefold()


class CountyRecordsProvider:
    """Search a per-request packaged or custom public fixture."""

    PROVIDER_NAME = "county_records"

    def __init__(
        self, source: SourceConfig, fixture: FixtureDataset | None = None
    ) -> None:
        if not source.is_selected:
            from ..landman import LandmanValidationError

            raise LandmanValidationError(
                message="Choose exactly one fixture source",
                error_code="LANDMAN_INVALID_SOURCE",
            )
        self.source = source
        self.fixture = fixture or self._load(source)

    @staticmethod
    def _load(source: SourceConfig) -> FixtureDataset:
        if source.sample:
            return read_packaged_fixture()
        return read_custom_fixture(source.records_file or "")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "CountyRecordsProvider":
        data = json.dumps(payload, allow_nan=True).encode("utf-8")
        fixture = parse_fixture_bytes(data, "in-memory.json")
        return cls(SourceConfig(sample=True), fixture=fixture)

    def search_ownership(self, criteria: Mapping[str, Any]):
        """Return fresh records matching normalized exact/substring predicates."""
        state = _state(str(criteria.get("state", "")))
        county = _county(str(criteria.get("county", "")))
        owner = _substring(str(criteria.get("owner_name", "")))
        legal = _substring(str(criteria.get("legal_description", "")))
        matches = []
        retrieved_at = datetime.utcnow()
        for record in self.fixture.records:
            if _state(record.state) != state or _county(record.county) != county:
                continue
            if owner and owner not in _substring(record.owner_name):
                continue
            if legal and legal not in _substring(record.legal_description):
                continue
            matches.append(
                replace(record, provider=self.PROVIDER_NAME, retrieved_at=retrieved_at)
            )
        return sorted(matches, key=lambda record: record.record_id)

    def health_check(self) -> bool:
        """The local validated fixture is ready once construction succeeds."""
        return True
