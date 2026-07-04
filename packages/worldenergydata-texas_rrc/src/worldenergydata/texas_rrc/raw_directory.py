"""Directory selection helpers for Texas RRC GoDrive raw refresh."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from worldenergydata.texas_rrc.godrive import (
    GoDriveDirectoryEntry,
    GoDriveDirectoryPage,
)
from worldenergydata.texas_rrc.raw_transport import (
    DownloadedArtifact,
    RetryableDownloadError,
)
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT


@dataclass(frozen=True)
class DirectorySelection:
    """User selection options for a GoDrive directory refresh."""

    since_date: date | None = None
    through_date: date | None = None
    mode: str = "catalog_default"


@dataclass(frozen=True)
class DirectoryRefreshFile:
    """One selected file in a GoDrive directory refresh plan."""

    filename: str
    command_id: str
    modified_label: str
    size_label: str
    page_first: int
    target_path: Path


@dataclass(frozen=True)
class DirectoryRefreshPlan:
    """Planned refresh action for one GoDrive directory source."""

    source_id: str
    refreshable: bool
    download_strategy: str
    source_url: str
    download_url: str | None
    target_path: Path
    refresh_cadence: str
    row_count: int
    selected_files: tuple[DirectoryRefreshFile, ...]
    skip_reason: str | None = None


@dataclass(frozen=True)
class SnapshotArtifactManifest:
    """Manifest record for one file in a multi-file raw snapshot."""

    filename: str
    raw_path: str
    effective_url: str | None
    retrieved_at: str
    source_modified_label: str | None
    source_size_label: str | None
    checksum_sha256: str | None
    byte_size: int
    status: str
    error: str | None = None


def build_directory_refresh_plan(
    source_id: str,
    entry: dict[str, Any],
    output_root: Path,
    pages: Iterable[GoDriveDirectoryPage],
    selection: DirectorySelection,
) -> DirectoryRefreshPlan:
    """Return selected GoDrive files for one directory catalog entry."""
    all_pages = tuple(pages)
    entries = tuple(file_entry for page in all_pages for file_entry in page.entries)
    row_count = all_pages[0].row_count if all_pages else 0
    target_dir = _target_dir(entry, output_root)
    selected = _select_entries(source_id, entry, entries, selection)
    selected_files = tuple(_to_refresh_file(item, target_dir) for item in selected)
    return DirectoryRefreshPlan(
        source_id=source_id,
        refreshable=True,
        download_strategy=entry["download_strategy"],
        source_url=entry["source_url"],
        download_url=entry.get("download_url"),
        target_path=target_dir,
        refresh_cadence=entry["refresh_cadence"],
        row_count=row_count,
        selected_files=_deduplicate_refresh_files(selected_files),
    )


def _target_dir(entry: dict[str, Any], output_root: Path) -> Path:
    relative_raw = Path(entry["raw_path"]).relative_to(SOURCE_CATALOG_ROOT)
    return output_root / relative_raw


def download_directory_files(
    plan: DirectoryRefreshPlan,
    transport,
    staging: Path,
    rows_per_page: int,
    validate_artifact,
    retrieved_at: str,
    max_attempts: int = 1,
) -> tuple[SnapshotArtifactManifest, ...]:
    """Download selected directory files into a staging directory."""
    download_file = getattr(transport, "download_godrive_directory_file_to")
    artifacts = []
    for item in plan.selected_files:
        part_path = staging / f"{item.filename}.part"
        artifact = _download_directory_file_with_retries(
            download_file,
            plan.download_url,
            item,
            part_path,
            rows_per_page,
            validate_artifact,
            max_attempts,
        )
        final_staged = staging / item.filename
        part_path.replace(final_staged)
        artifacts.append(
            _artifact_manifest(item, artifact, item.target_path, retrieved_at)
        )
    return tuple(artifacts)


def _download_directory_file_with_retries(
    download_file,
    download_url: str | None,
    item: DirectoryRefreshFile,
    part_path: Path,
    rows_per_page: int,
    validate_artifact,
    max_attempts: int,
) -> DownloadedArtifact:
    for attempt in range(1, max_attempts + 1):
        part_path.unlink(missing_ok=True)
        try:
            artifact = download_file(download_url, item, part_path, rows_per_page)
            validate_artifact(artifact)
            return artifact
        except RetryableDownloadError:
            if attempt == max_attempts:
                raise
        except ValueError:
            raise
        except Exception:
            if attempt == max_attempts:
                raise
    raise RuntimeError("directory download retry loop exited without a result")


def promote_directory_files(plan: DirectoryRefreshPlan, staging: Path) -> None:
    """Promote a complete staged directory batch into its final raw path."""
    plan.target_path.mkdir(parents=True, exist_ok=True)
    for item in plan.selected_files:
        (staging / item.filename).replace(item.target_path)
    cleanup_directory_staging(staging)


def cleanup_directory_staging(staging: Path) -> None:
    """Remove a directory refresh staging path if present."""
    shutil.rmtree(staging, ignore_errors=True)


def _artifact_manifest(
    item: DirectoryRefreshFile,
    artifact: DownloadedArtifact,
    raw_path: Path,
    retrieved_at: str,
) -> SnapshotArtifactManifest:
    return SnapshotArtifactManifest(
        filename=item.filename,
        raw_path=str(raw_path),
        effective_url=artifact.effective_url,
        retrieved_at=retrieved_at,
        source_modified_label=item.modified_label,
        source_size_label=item.size_label,
        checksum_sha256=artifact.checksum_sha256,
        byte_size=artifact.byte_size,
        status="downloaded",
    )


def _select_entries(
    source_id: str,
    entry: dict[str, Any],
    entries: tuple[GoDriveDirectoryEntry, ...],
    selection: DirectorySelection,
) -> tuple[GoDriveDirectoryEntry, ...]:
    mode = _effective_mode(entry, selection)
    if selection.since_date or selection.through_date:
        return _select_by_filename_date(entries, selection, mode)
    if mode == "all" and entry.get("directory_refresh_policy") == "all_files":
        return _select_all(source_id, entries)
    return _select_by_filename_date(entries, selection, mode)


def _effective_mode(entry: dict[str, Any], selection: DirectorySelection) -> str:
    if selection.mode == "all":
        return "all"
    if selection.mode == "latest":
        return "latest"
    policy = entry.get("directory_refresh_policy", "latest_by_filename_date")
    return "all" if policy == "all_files" else "latest"


def _select_all(
    source_id: str,
    entries: tuple[GoDriveDirectoryEntry, ...],
) -> tuple[GoDriveDirectoryEntry, ...]:
    prefix = "pipeline" if source_id == "pipeline_gis_layers" else "well"
    selected = [entry for entry in entries if entry.filename.startswith(prefix)]
    if not selected:
        raise ValueError("GoDrive directory selection did not match any files")
    return tuple(sorted(selected, key=lambda item: item.filename))


def _select_by_filename_date(
    entries: tuple[GoDriveDirectoryEntry, ...],
    selection: DirectorySelection,
    mode: str,
) -> tuple[GoDriveDirectoryEntry, ...]:
    dated = [(item, parsed) for item in entries if (parsed := _filename_date(item))]
    if not dated:
        raise ValueError("GoDrive directory did not contain dated zip filenames")
    if selection.since_date or selection.through_date:
        dated = [
            (item, parsed)
            for item, parsed in dated
            if _date_selected(parsed, selection)
        ]
    elif mode == "latest":
        latest = max(parsed for _, parsed in dated)
        dated = [(item, parsed) for item, parsed in dated if parsed == latest]
    if not dated:
        raise ValueError("GoDrive directory selection did not match any files")
    return tuple(item for item, _ in sorted(dated, key=lambda pair: pair[0].filename))


def _filename_date(entry: GoDriveDirectoryEntry) -> date | None:
    match = re.fullmatch(r"(\d{2})-(\d{2})-(\d{4})\.zip", entry.filename)
    if not match:
        return None
    month, day, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _date_selected(value: date, selection: DirectorySelection) -> bool:
    if selection.since_date and value < selection.since_date:
        return False
    if selection.through_date and value > selection.through_date:
        return False
    return True


def _to_refresh_file(
    entry: GoDriveDirectoryEntry,
    target_dir: Path,
) -> DirectoryRefreshFile:
    return DirectoryRefreshFile(
        filename=entry.filename,
        command_id=entry.command_id,
        modified_label=entry.modified_label,
        size_label=entry.size_label,
        page_first=entry.page_first,
        target_path=target_dir / entry.filename,
    )


def _deduplicate_refresh_files(
    selected_files: tuple[DirectoryRefreshFile, ...],
) -> tuple[DirectoryRefreshFile, ...]:
    seen = set()
    result = []
    for item in selected_files:
        key = (item.filename, item.target_path)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return tuple(result)
