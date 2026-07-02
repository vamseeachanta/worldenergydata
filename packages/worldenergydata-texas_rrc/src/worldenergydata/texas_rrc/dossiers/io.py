"""Persist Texas RRC field-architecture dossier outputs."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from worldenergydata.texas_rrc.dossiers.html import (
    render_field_architecture_dossier_html,
    render_field_architecture_dossier_summary_html,
)
from worldenergydata.texas_rrc.dossiers.models import (
    DOSSIER_LIMITATIONS,
    FieldArchitectureDossierPage,
)
from worldenergydata.texas_rrc.dossiers.quality import FieldArchitectureDossierQuality
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT

FIELD_ARCHITECTURE_DOSSIER_DIR = (
    Path("curated") / "analysis" / "field_architecture_dossiers"
)
INDEX_CSV_FILENAME = "field_architecture_dossier_index.csv"
INDEX_PARQUET_FILENAME = "field_architecture_dossier_index.parquet"
SUMMARY_HTML_FILENAME = "field_architecture_dossier_summary.html"
QUALITY_FILENAME = "quality.json"
COMPONENT_QUALITY_FILENAME = "field_architecture_dossier_quality.json"
MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class FieldArchitectureDossierOutputManifest:
    """Paths and metadata for one field-architecture dossier output batch."""

    generated_at: str
    output_root: Path
    output_dir: Path
    index_csv_path: Path
    index_parquet_path: Path
    summary_html_path: Path
    field_dir: Path
    quality_path: Path
    component_quality_path: Path
    manifest_path: Path
    row_count: int
    input_paths: tuple[str, ...]
    upstream_manifests: tuple[str, ...]
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]
    selection_policy: dict[str, int]
    limitations: tuple[str, ...]
    command: str | None
    code_revision: str | None


def write_field_architecture_dossier_outputs(
    pages: tuple[FieldArchitectureDossierPage, ...],
    index: pd.DataFrame,
    quality: FieldArchitectureDossierQuality,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    generated_at: datetime | None = None,
    input_paths: Iterable[str | Path] = (),
    upstream_manifests: Iterable[str | Path] = (),
    selection_policy: dict[str, int] | None = None,
    allow_non_ace_root: bool = False,
    command: str | None = None,
    code_revision: str | None = None,
) -> FieldArchitectureDossierOutputManifest:
    """Write index, HTML pages, quality aliases, and manifest JSON."""
    root = Path(output_root)
    _validate_output_root(root, allow_non_ace_root)
    target_dir = root / FIELD_ARCHITECTURE_DOSSIER_DIR
    stamp = _timestamp(generated_at)
    manifest = _manifest(
        root,
        target_dir,
        index,
        quality,
        input_paths,
        upstream_manifests,
        selection_policy or {"max_fields": 25, "class_coverage_limit": 3},
        tuple(pages[0].limitations if pages else DOSSIER_LIMITATIONS),
        command,
        code_revision,
        stamp,
    )
    _write_with_staging(target_dir, pages, index, quality, manifest, stamp)
    return manifest


def _manifest(
    root: Path,
    target_dir: Path,
    index: pd.DataFrame,
    quality: FieldArchitectureDossierQuality,
    input_paths: Iterable[str | Path],
    upstream_manifests: Iterable[str | Path],
    selection_policy: dict[str, int],
    limitations: tuple[str, ...],
    command: str | None,
    code_revision: str | None,
    stamp: str,
) -> FieldArchitectureDossierOutputManifest:
    return FieldArchitectureDossierOutputManifest(
        generated_at=stamp,
        output_root=root,
        output_dir=target_dir,
        index_csv_path=target_dir / INDEX_CSV_FILENAME,
        index_parquet_path=target_dir / INDEX_PARQUET_FILENAME,
        summary_html_path=target_dir / SUMMARY_HTML_FILENAME,
        field_dir=target_dir / "fields",
        quality_path=target_dir / QUALITY_FILENAME,
        component_quality_path=target_dir / COMPONENT_QUALITY_FILENAME,
        manifest_path=target_dir / MANIFEST_FILENAME,
        row_count=len(index),
        input_paths=tuple(str(path) for path in input_paths),
        upstream_manifests=tuple(str(path) for path in upstream_manifests),
        blocking_source_gaps=tuple(quality.blocking_source_gaps),
        informational_source_gaps=tuple(quality.informational_source_gaps),
        selection_policy=dict(selection_policy),
        limitations=tuple(limitations),
        command=command,
        code_revision=code_revision or _git_revision(),
    )


def _write_with_staging(
    target_dir: Path,
    pages: tuple[FieldArchitectureDossierPage, ...],
    index: pd.DataFrame,
    quality: FieldArchitectureDossierQuality,
    manifest: FieldArchitectureDossierOutputManifest,
    stamp: str,
) -> None:
    staging = target_dir.parent / f".staging-field-dossiers-{_compact_stamp(stamp)}"
    backup = target_dir.parent / f".backup-field-dossiers-{_compact_stamp(stamp)}"
    shutil.rmtree(staging, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    promoted = False
    try:
        (staging / "fields").mkdir(parents=True, exist_ok=False)
        index.to_csv(staging / INDEX_CSV_FILENAME, index=False)
        index.to_parquet(staging / INDEX_PARQUET_FILENAME, index=False)
        (staging / SUMMARY_HTML_FILENAME).write_text(
            render_field_architecture_dossier_summary_html(index, quality),
            encoding="utf-8",
        )
        for page in pages:
            (staging / "fields" / page.dossier_filename).write_text(
                render_field_architecture_dossier_html(page),
                encoding="utf-8",
            )
        quality_payload = asdict(quality)
        _write_json(staging / QUALITY_FILENAME, quality_payload)
        _write_json(staging / COMPONENT_QUALITY_FILENAME, quality_payload)
        _write_json(staging / MANIFEST_FILENAME, _manifest_payload(manifest, quality))
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if target_dir.exists():
            target_dir.rename(backup)
        staging.rename(target_dir)
        promoted = True
        shutil.rmtree(backup, ignore_errors=True)
    except Exception:
        if backup.exists() and not target_dir.exists():
            backup.rename(target_dir)
        raise
    finally:
        if not promoted:
            shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)


def _manifest_payload(
    manifest: FieldArchitectureDossierOutputManifest,
    quality: FieldArchitectureDossierQuality,
) -> dict[str, object]:
    payload = asdict(manifest)
    for key, value in list(payload.items()):
        if isinstance(value, Path):
            payload[key] = str(value)
    payload["input_paths"] = list(manifest.input_paths)
    payload["upstream_manifests"] = list(manifest.upstream_manifests)
    payload["blocking_source_gaps"] = list(manifest.blocking_source_gaps)
    payload["informational_source_gaps"] = list(manifest.informational_source_gaps)
    payload["selection_policy"] = dict(manifest.selection_policy)
    payload["limitations"] = list(manifest.limitations)
    payload["quality"] = asdict(quality)
    return payload


def _validate_output_root(root: Path, allow_non_ace_root: bool) -> None:
    if allow_non_ace_root:
        return
    if not root.resolve().is_relative_to(SOURCE_CATALOG_ROOT.resolve()):
        raise ValueError(
            "field-architecture dossier output_root must stay under "
            f"{SOURCE_CATALOG_ROOT}; pass allow_non_ace_root=True only for tests"
        )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _timestamp(value: datetime | None) -> str:
    timestamp = value or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compact_stamp(stamp: str) -> str:
    return stamp.replace("-", "").replace(":", "")


def _git_revision() -> str | None:
    repo_root = _repo_root()
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return revision or None


def _repo_root() -> Path:
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / ".git").exists():
            return parent
    return path.parents[6]


__all__ = [
    "FIELD_ARCHITECTURE_DOSSIER_DIR",
    "FieldArchitectureDossierOutputManifest",
    "write_field_architecture_dossier_outputs",
]
