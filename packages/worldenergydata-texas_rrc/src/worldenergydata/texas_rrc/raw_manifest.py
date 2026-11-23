"""Manifest models for Texas RRC raw refresh."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from worldenergydata.texas_rrc.raw_directory import SnapshotArtifactManifest


@dataclass(frozen=True)
class RefreshPlan:
    """Planned refresh action for one source catalog entry."""

    source_id: str
    refreshable: bool
    download_strategy: str
    source_url: str
    download_url: str | None
    target_path: Path
    refresh_cadence: str
    skip_reason: str | None = None


@dataclass(frozen=True)
class SnapshotManifest:
    """Manifest record for one attempted raw snapshot refresh."""

    source_id: str
    source_url: str
    download_url: str | None
    effective_url: str | None
    retrieved_at: str
    refresh_cadence: str
    raw_path: str
    checksum_sha256: str | None
    byte_size: int
    status: str
    error: str | None = None
    artifacts: tuple[SnapshotArtifactManifest, ...] = ()
