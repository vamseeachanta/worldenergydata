"""Persist Texas RRC field-atlas report outputs."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from worldenergydata.texas_rrc.reports.field_atlas import FieldAtlasPage
from worldenergydata.texas_rrc.reports.html import render_field_html, render_index_html
from worldenergydata.texas_rrc.reports.quality import FieldAtlasReportQuality
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT

FIELD_ATLAS_REPORT_DIR = Path("curated") / "reports" / "field_atlas"
SUMMARY_CSV_FILENAME = "field_atlas_summary.csv"
SUMMARY_PARQUET_FILENAME = "field_atlas_summary.parquet"
QUALITY_FILENAME = "field_atlas_report_quality.json"
MANIFEST_FILENAME = "manifest.json"
INDEX_FILENAME = "index.html"


@dataclass(frozen=True)
class FieldAtlasReportOutputManifest:
    """Paths and metadata for one field-atlas report output batch."""

    generated_at: str
    output_root: Path
    output_dir: Path
    index_path: Path
    summary_csv_path: Path
    summary_parquet_path: Path
    quality_path: Path
    manifest_path: Path
    row_count: int
    page_count: int
    input_paths: tuple[str, ...]
    source_gaps: tuple[str, ...]
    command: str | None
    code_revision: str | None


def write_field_atlas_report_outputs(
    pages: tuple[FieldAtlasPage, ...],
    summary: pd.DataFrame,
    quality: FieldAtlasReportQuality,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    generated_at: datetime | None = None,
    input_paths: Iterable[str | Path] = (),
    allow_non_ace_root: bool = False,
    command: str | None = None,
    code_revision: str | None = None,
) -> FieldAtlasReportOutputManifest:
    """Write HTML, summary, quality, and manifest report outputs."""
    root = Path(output_root)
    _validate_output_root(root, allow_non_ace_root)
    target_dir = root / FIELD_ATLAS_REPORT_DIR
    stamp = _timestamp(generated_at)
    manifest = _manifest(
        root,
        target_dir,
        summary,
        pages,
        quality,
        input_paths,
        command,
        code_revision,
        stamp,
    )
    _write_with_staging(target_dir, pages, summary, quality, manifest, stamp)
    return manifest


def _manifest(
    root: Path,
    target_dir: Path,
    summary: pd.DataFrame,
    pages: tuple[FieldAtlasPage, ...],
    quality: FieldAtlasReportQuality,
    input_paths: Iterable[str | Path],
    command: str | None,
    code_revision: str | None,
    stamp: str,
) -> FieldAtlasReportOutputManifest:
    return FieldAtlasReportOutputManifest(
        generated_at=stamp,
        output_root=root,
        output_dir=target_dir,
        index_path=target_dir / INDEX_FILENAME,
        summary_csv_path=target_dir / SUMMARY_CSV_FILENAME,
        summary_parquet_path=target_dir / SUMMARY_PARQUET_FILENAME,
        quality_path=target_dir / QUALITY_FILENAME,
        manifest_path=target_dir / MANIFEST_FILENAME,
        row_count=len(summary),
        page_count=len(pages),
        input_paths=tuple(str(path) for path in input_paths),
        source_gaps=tuple(quality.source_gaps),
        command=command,
        code_revision=code_revision or _git_revision(),
    )


def _write_with_staging(
    target_dir: Path,
    pages: tuple[FieldAtlasPage, ...],
    summary: pd.DataFrame,
    quality: FieldAtlasReportQuality,
    manifest: FieldAtlasReportOutputManifest,
    stamp: str,
) -> None:
    staging = (
        target_dir.parent / f".staging-field-atlas-reports-{_compact_stamp(stamp)}"
    )
    backup = target_dir.parent / f".backup-field-atlas-reports-{_compact_stamp(stamp)}"
    shutil.rmtree(staging, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    promoted = False
    try:
        (staging / "fields").mkdir(parents=True, exist_ok=False)
        _write_html_outputs(staging, pages, summary)
        summary.to_csv(staging / SUMMARY_CSV_FILENAME, index=False)
        summary.to_parquet(staging / SUMMARY_PARQUET_FILENAME, index=False)
        _write_json(staging / QUALITY_FILENAME, _quality_payload(quality))
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


def _write_html_outputs(
    staging: Path, pages: tuple[FieldAtlasPage, ...], summary: pd.DataFrame
) -> None:
    (staging / INDEX_FILENAME).write_text(
        render_index_html(summary, pages),
        encoding="utf-8",
    )
    for page in pages:
        (staging / "fields" / page.field_page_filename).write_text(
            render_field_html(page),
            encoding="utf-8",
        )


def _validate_output_root(root: Path, allow_non_ace_root: bool) -> None:
    if allow_non_ace_root:
        return
    if not root.resolve().is_relative_to(SOURCE_CATALOG_ROOT.resolve()):
        raise ValueError(
            "Field-atlas report output_root must stay under "
            f"{SOURCE_CATALOG_ROOT}; pass allow_non_ace_root=True only for "
            "isolated tests or sandbox runs"
        )


def _quality_payload(quality: FieldAtlasReportQuality) -> dict[str, object]:
    return asdict(quality)


def _manifest_payload(
    manifest: FieldAtlasReportOutputManifest,
    quality: FieldAtlasReportQuality,
) -> dict[str, object]:
    return {
        "generated_at": manifest.generated_at,
        "output_root": str(manifest.output_root),
        "output_dir": str(manifest.output_dir),
        "index_path": str(manifest.index_path),
        "summary_csv_path": str(manifest.summary_csv_path),
        "summary_parquet_path": str(manifest.summary_parquet_path),
        "quality_path": str(manifest.quality_path),
        "manifest_path": str(manifest.manifest_path),
        "row_count": manifest.row_count,
        "page_count": manifest.page_count,
        "input_paths": list(manifest.input_paths),
        "source_gaps": list(manifest.source_gaps),
        "command": manifest.command,
        "code_revision": manifest.code_revision,
        "quality": _quality_payload(quality),
    }


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
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=5,
        )
        value = revision.stdout.strip()
        if not value:
            return None
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    except subprocess.TimeoutExpired:
        return value
    suffix = "+dirty" if status.stdout.strip() else ""
    return f"{value}{suffix}"


def _repo_root() -> Path:
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / ".git").exists():
            return parent
    return path.parents[6]


__all__ = [
    "FIELD_ATLAS_REPORT_DIR",
    "FieldAtlasReportOutputManifest",
    "write_field_atlas_report_outputs",
]
