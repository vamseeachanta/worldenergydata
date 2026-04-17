"""Common schema and adapter interface for multi-source field pipelines.

All adapters normalise their regulatory data source into the FieldContext
contract (from bsee.pipeline.field_query) so that PipelineRunner and
downstream analysis stages work identically regardless of source.

Canonical units are SI — each adapter's ``adapt()`` converts source units
on ingestion.  See ``units.py`` for conversion helpers.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Domain status — used by the data-availability matrix
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DomainStatus:
    """Availability of one analysis domain for a given regulatory source.

    Attributes:
        status: One of ``"available"``, ``"partial"``, ``"unavailable"``.
        notes: Free-text description of coverage, gaps, or caveats.
    """

    status: str  # "available" | "partial" | "unavailable"
    notes: str = ""


@dataclass(frozen=True)
class DataAvailability:
    """Per-source availability across all six analysis domains."""

    source_id: str
    source_name: str
    jurisdiction: str

    wellbore: DomainStatus = field(default_factory=lambda: DomainStatus("unavailable"))
    well_path: DomainStatus = field(default_factory=lambda: DomainStatus("unavailable"))
    casing: DomainStatus = field(default_factory=lambda: DomainStatus("unavailable"))
    drilling_completion: DomainStatus = field(
        default_factory=lambda: DomainStatus("unavailable")
    )
    intervention: DomainStatus = field(
        default_factory=lambda: DomainStatus("unavailable")
    )
    production: DomainStatus = field(
        default_factory=lambda: DomainStatus("unavailable")
    )


@dataclass(frozen=True)
class SourceMetadata:
    """Metadata describing a regulatory data source.

    Attached to every adapter result so downstream consumers know
    which source produced the data.
    """

    source_id: str
    source_name: str
    jurisdiction: str
    api_base_url: str = ""
    update_cadence: str = ""  # e.g. "monthly", "weekly", "daily"


# ---------------------------------------------------------------------------
# Adapter result — what adapt() returns
# ---------------------------------------------------------------------------


@dataclass
class AdapterResult:
    """Normalised output from an adapter's ``adapt()`` call.

    All DataFrames use SI units (metres, cubic metres, kilograms).
    Domains the source cannot supply are empty DataFrames with the
    expected columns still present (schema-correct empties).
    """

    source: SourceMetadata

    # Core identification (maps to FieldContext fields)
    field_code: str
    field_name: str
    leases: tuple[str, ...]
    area_code: str = ""
    geological_era: str = "Unknown"
    well_count: int = 0
    query_type: str = "field_name"

    # Domain DataFrames (empty if unavailable)
    wellbore_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    well_paths: pd.DataFrame = field(default_factory=pd.DataFrame)
    casing_strings: pd.DataFrame = field(default_factory=pd.DataFrame)
    drilling_activities: pd.DataFrame = field(default_factory=pd.DataFrame)
    completion_activities: pd.DataFrame = field(default_factory=pd.DataFrame)
    intervention_activities: pd.DataFrame = field(default_factory=pd.DataFrame)
    production: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Soft-failure log
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Adapter interface (abstract base)
# ---------------------------------------------------------------------------


class AdapterInterface(abc.ABC):
    """Base class for all regulatory-source adapters.

    Subclasses implement ``adapt()`` to transform source-specific data
    into a normalised :class:`AdapterResult`.
    """

    @abc.abstractmethod
    def adapt(self, query: str, **kwargs: Any) -> AdapterResult:
        """Resolve *query* against this source and return normalised data.

        Args:
            query: Field name, well identifier, lease/block, or region.
            **kwargs: Source-specific options (e.g. ``district`` for RRC).

        Returns:
            An :class:`AdapterResult` with SI-unit DataFrames.
        """

    @abc.abstractmethod
    def get_metadata(self) -> SourceMetadata:
        """Return static metadata for this source."""

    @abc.abstractmethod
    def get_availability(self) -> DataAvailability:
        """Return domain-level availability for this source."""

    def available_domains(self) -> list[str]:
        """List domains with status != 'unavailable'."""
        avail = self.get_availability()
        domains = []
        for name in (
            "wellbore",
            "well_path",
            "casing",
            "drilling_completion",
            "intervention",
            "production",
        ):
            ds: DomainStatus = getattr(avail, name)
            if ds.status != "unavailable":
                domains.append(name)
        return domains
