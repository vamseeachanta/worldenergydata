"""Persist Texas RRC field-opportunity ranking outputs."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from worldenergydata.texas_rrc.opportunities.html import (
    render_field_opportunity_summary_html,
)
from worldenergydata.texas_rrc.opportunities.quality import FieldOpportunityQuality
from worldenergydata.texas_rrc.opportunities.scoring import (
    OUTPUT_COLUMNS,
    SCORING_VERSION,
    SCORING_WEIGHTS,
)
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT

FIELD_OPPORTUNITY_DIR = Path("curated") / "analysis" / "field_opportunities"
RANKINGS_CSV_FILENAME = "field_opportunity_rankings.csv"
RANKINGS_PARQUET_FILENAME = "field_opportunity_rankings.parquet"
HTML_FILENAME = "field_opportunity_summary.html"
QUALITY_FILENAME = "field_opportunity_quality.json"
MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class FieldOpportunityOutputManifest:
    """Paths and metadata for one field-opportunity output batch."""

    generated_at: str
    output_root: Path
    output_dir: Path
    rankings_csv_path: Path
    rankings_parquet_path: Path
    html_path: Path
    quality_path: Path
    manifest_path: Path
    row_count: int
    input_paths: tuple[str, ...]
    upstream_manifests: tuple[str, ...]
    source_gaps: tuple[str, ...]
    command: str | None
    code_revision: str | None


def write_field_opportunity_outputs(
    rankings: pd.DataFrame,
    quality: FieldOpportunityQuality,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    generated_at: datetime | None = None,
    input_paths: Iterable[str | Path] = (),
    upstream_manifests: Iterable[str | Path] = (),
    allow_non_ace_root: bool = False,
    command: str | None = None,
    code_revision: str | None = None,
) -> FieldOpportunityOutputManifest:
    """Write rankings, summary HTML, quality JSON, and manifest JSON."""
    root = Path(output_root)
    _validate_output_root(root, allow_non_ace_root)
    target_dir = root / FIELD_OPPORTUNITY_DIR
    stamp = _timestamp(generated_at)
    manifest = _manifest(
        root,
        target_dir,
        rankings,
        quality,
        input_paths,
        upstream_manifests,
        command,
        code_revision,
        stamp,
    )
    _write_with_staging(target_dir, rankings, quality, manifest, stamp)
    return manifest


def _manifest(
    root: Path,
    target_dir: Path,
    rankings: pd.DataFrame,
    quality: FieldOpportunityQuality,
    input_paths: Iterable[str | Path],
    upstream_manifests: Iterable[str | Path],
    command: str | None,
    code_revision: str | None,
    stamp: str,
) -> FieldOpportunityOutputManifest:
    return FieldOpportunityOutputManifest(
        generated_at=stamp,
        output_root=root,
        output_dir=target_dir,
        rankings_csv_path=target_dir / RANKINGS_CSV_FILENAME,
        rankings_parquet_path=target_dir / RANKINGS_PARQUET_FILENAME,
        html_path=target_dir / HTML_FILENAME,
        quality_path=target_dir / QUALITY_FILENAME,
        manifest_path=target_dir / MANIFEST_FILENAME,
        row_count=len(rankings),
        input_paths=tuple(str(path) for path in input_paths),
        upstream_manifests=tuple(str(path) for path in upstream_manifests),
        source_gaps=tuple(quality.source_gaps),
        command=command,
        code_revision=code_revision or _git_revision(),
    )


def _write_with_staging(
    target_dir: Path,
    rankings: pd.DataFrame,
    quality: FieldOpportunityQuality,
    manifest: FieldOpportunityOutputManifest,
    stamp: str,
) -> None:
    staging = (
        target_dir.parent / f".staging-field-opportunities-{_compact_stamp(stamp)}"
    )
    backup = target_dir.parent / f".backup-field-opportunities-{_compact_stamp(stamp)}"
    shutil.rmtree(staging, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    promoted = False
    try:
        staging.mkdir(parents=True, exist_ok=False)
        rankings.to_csv(staging / RANKINGS_CSV_FILENAME, index=False)
        rankings.to_parquet(staging / RANKINGS_PARQUET_FILENAME, index=False)
        (staging / HTML_FILENAME).write_text(
            render_field_opportunity_summary_html(rankings, quality),
            encoding="utf-8",
        )
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


def _validate_output_root(root: Path, allow_non_ace_root: bool) -> None:
    if allow_non_ace_root:
        return
    if not root.resolve().is_relative_to(SOURCE_CATALOG_ROOT.resolve()):
        raise ValueError(
            "field-opportunity output_root must stay under "
            f"{SOURCE_CATALOG_ROOT}; pass allow_non_ace_root=True only for tests"
        )


def _quality_payload(quality: FieldOpportunityQuality) -> dict[str, object]:
    return asdict(quality)


def _manifest_payload(
    manifest: FieldOpportunityOutputManifest,
    quality: FieldOpportunityQuality,
) -> dict[str, object]:
    return {
        "generated_at": manifest.generated_at,
        "output_root": str(manifest.output_root),
        "output_dir": str(manifest.output_dir),
        "rankings_csv_path": str(manifest.rankings_csv_path),
        "rankings_parquet_path": str(manifest.rankings_parquet_path),
        "html_path": str(manifest.html_path),
        "quality_path": str(manifest.quality_path),
        "manifest_path": str(manifest.manifest_path),
        "row_count": manifest.row_count,
        "input_paths": list(manifest.input_paths),
        "upstream_manifests": list(manifest.upstream_manifests),
        "source_gaps": list(manifest.source_gaps),
        "command": manifest.command,
        "code_revision": manifest.code_revision,
        "scoring_version": SCORING_VERSION,
        "scoring_weights": SCORING_WEIGHTS,
        "score_column_contract": OUTPUT_COLUMNS,
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
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return revision or None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


__all__ = [
    "FIELD_OPPORTUNITY_DIR",
    "FieldOpportunityOutputManifest",
    "write_field_opportunity_outputs",
]
