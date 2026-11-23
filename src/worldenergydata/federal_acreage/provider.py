"""Provider seam for future live MLRS acquisition in issue #913."""

from pathlib import Path
from typing import Literal, Protocol

from .models import Contract, FederalLandRecord, SourceRef, TractOfInterest


class FederalLandRecordProvider(Protocol):
    def records_for_tract(
        self, tract: TractOfInterest
    ) -> tuple[list[FederalLandRecord], list[SourceRef]]:
        """Return records on the tract's single-section grid and their sources."""
        ...


class FixtureData(Contract):
    schema_version: Literal["federal-acreage-fixture-v1"]
    tract: TractOfInterest
    records: list[FederalLandRecord]
    sources: list[SourceRef]


class FixtureRecordProvider:
    """Read a synthetic fixture; the live issue #913 provider uses the same protocol."""

    def __init__(self, path: str | Path):
        self.data = FixtureData.model_validate_json(
            Path(path).read_text(encoding="utf-8")
        )
        if any(source.kind != "fixture" for source in self.data.sources):
            raise ValueError("Fixture sources must carry kind=fixture")
        self.tract = self.data.tract

    def records_for_tract(
        self, tract: TractOfInterest
    ) -> tuple[list[FederalLandRecord], list[SourceRef]]:
        grid = ("state", "principal_meridian", "township", "range", "section")
        if any(getattr(tract, key) != getattr(self.tract, key) for key in grid):
            raise ValueError("Fixture records belong to a different section grid")
        return self.data.records, self.data.sources
