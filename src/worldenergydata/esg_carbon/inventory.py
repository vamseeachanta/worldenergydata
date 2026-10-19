"""Immutable, source-qualified emissions observations and homogeneous totals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import fsum, isfinite


@dataclass(frozen=True)
class EmissionBasis:
    """Quantities can be added only when every basis attribute agrees."""

    iso3_country: str
    sector: str
    subsector: str
    start_time: datetime
    end_time: datetime
    temporal_granularity: str
    gas: str


@dataclass(frozen=True)
class EmissionRecord(EmissionBasis):
    """A reported mass; None denotes unavailable data, distinct from zero.

    Climate TRACE v5.11.0 (September 2026), emissions_sources.csv metadata:
    emissions_quantity is metric tonnes; blank/null/N-A means unavailable.
    """

    source_id: str
    source_name: str
    emissions_quantity: float | None
    units: str = "tonnes"

    @property
    def basis(self) -> EmissionBasis:
        return EmissionBasis(
            self.iso3_country,
            self.sector,
            self.subsector,
            self.start_time,
            self.end_time,
            self.temporal_granularity,
            self.gas,
        )


@dataclass(frozen=True)
class EmissionSummary:
    """Completeness applies to selected rows, never national coverage.

    COMPLETE: every selected row reports a mass. INCOMPLETE: a mass is missing.
    NOT_EVALUATED: no rows match. The known subtotal is not a complete inventory.
    """

    basis: EmissionBasis | None
    total_tonnes: float | None
    known_subtotal_tonnes: float
    record_count: int
    missing_count: int
    status: str
    edition: str
    sha256: str

    @property
    def gas(self) -> str | None:
        return self.basis.gas if self.basis else None


@dataclass(frozen=True)
class EmissionInventory:
    """One supplied CSV edition; SHA-256 identifies its original bytes.

    Edition is caller-declared, not verified against an upstream release.
    No raw source data is copied or downloaded by this object.
    """

    records: tuple[EmissionRecord, ...]
    edition: str
    sha256: str
    source_url: str = "https://climatetrace.org/data"

    def select(
        self,
        *,
        source_id: str | None = None,
        iso3_country: str | None = None,
        gas: str | None = None,
        subsector: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> tuple[EmissionRecord, ...]:
        """Return exact matches; omitted filters impose no restriction."""
        filters = {
            "source_id": source_id,
            "iso3_country": iso3_country,
            "gas": gas,
            "subsector": subsector,
            "start_time": start_time,
            "end_time": end_time,
        }
        return tuple(
            row
            for row in self.records
            if all(
                value is None or getattr(row, field) == value
                for field, value in filters.items()
            )
        )

    def summarize(self, **filters) -> EmissionSummary:
        """Sum same-basis mass, without GWP or time/unit conversion.

        Equation: total = sum of reported emissions_quantity (tonnes).
        Basis: Climate TRACE v5.11.0, emissions_sources.csv metadata; gas,
        period, country and subsector distinguish observations. Missing masses
        prevent a total. No geographic-coverage or compliance claim is made.
        """
        rows = self.select(**filters)
        bases = {row.basis for row in rows}
        if len(bases) > 1:
            raise ValueError("Cannot sum observations with a mixed emissions basis")
        missing = sum(row.emissions_quantity is None for row in rows)
        try:
            subtotal = fsum(
                row.emissions_quantity
                for row in rows
                if row.emissions_quantity is not None
            )
        except OverflowError as error:
            raise ValueError(
                "Emissions subtotal exceeds finite numeric range"
            ) from error
        if not isfinite(subtotal):
            raise ValueError("Emissions subtotal must be finite")
        status = (
            "NOT_EVALUATED" if not rows else "INCOMPLETE" if missing else "COMPLETE"
        )
        return EmissionSummary(
            rows[0].basis if rows else None,
            subtotal if rows and not missing else None,
            subtotal,
            len(rows),
            missing,
            status,
            self.edition,
            self.sha256,
        )
