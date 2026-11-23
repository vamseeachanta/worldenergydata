"""Persist Texas RRC field-architecture portfolio outputs."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from worldenergydata.texas_rrc.architecture_portfolio.html import (
    render_field_architecture_portfolio_html,
)
from worldenergydata.texas_rrc.architecture_portfolio.models import (
    ACTION_SPECS,
    PORTFOLIO_LIMITATIONS,
)
from worldenergydata.texas_rrc.architecture_portfolio.quality import (
    FieldArchitecturePortfolioQuality,
)
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT

FIELD_ARCHITECTURE_PORTFOLIO_DIR = (
    Path("curated") / "analysis" / "field_architecture_portfolio"
)
ACTION_QUEUE_CSV_FILENAME = "field_architecture_action_queue.csv"
ACTION_QUEUE_PARQUET_FILENAME = "field_architecture_action_queue.parquet"
CLASS_SUMMARY_CSV_FILENAME = "field_architecture_class_summary.csv"
CLASS_SUMMARY_PARQUET_FILENAME = "field_architecture_class_summary.parquet"
FOLLOWUP_SUMMARY_CSV_FILENAME = "field_architecture_followup_summary.csv"
FOLLOWUP_SUMMARY_PARQUET_FILENAME = "field_architecture_followup_summary.parquet"
HTML_FILENAME = "field_architecture_portfolio.html"
QUALITY_FILENAME = "quality.json"
COMPONENT_QUALITY_FILENAME = "field_architecture_portfolio_quality.json"
MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class FieldArchitecturePortfolioOutputManifest:
    """Paths and metadata for one field-architecture portfolio output batch."""

    generated_at: str
    output_root: Path
    output_dir: Path
    action_queue_csv_path: Path
    action_queue_parquet_path: Path
    class_summary_csv_path: Path
    class_summary_parquet_path: Path
    followup_summary_csv_path: Path
    followup_summary_parquet_path: Path
    html_path: Path
    quality_path: Path
    component_quality_path: Path
    manifest_path: Path
    row_count: int
    class_summary_row_count: int
    followup_summary_row_count: int
    input_paths: tuple[str, ...]
    dossier_input_paths: tuple[str, ...]
    upstream_manifests: tuple[str, ...]
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]
    limitations: tuple[str, ...]
    action_specs: dict[str, dict[str, object]]
    command: str | None
    code_revision: str | None


def write_field_architecture_portfolio_outputs(
    action_queue: pd.DataFrame,
    class_summary: pd.DataFrame,
    followup_summary: pd.DataFrame,
    quality: FieldArchitecturePortfolioQuality,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    generated_at: datetime | None = None,
    input_paths: Iterable[str | Path] = (),
    dossier_input_paths: Iterable[str | Path] = (),
    upstream_manifests: Iterable[str | Path] = (),
    allow_non_ace_root: bool = False,
    command: str | None = None,
    code_revision: str | None = None,
) -> FieldArchitecturePortfolioOutputManifest:
    """Write action queue, rollups, HTML, quality aliases, and manifest JSON."""
    root = Path(output_root)
    _validate_output_root(root, allow_non_ace_root)
    target_dir = root / FIELD_ARCHITECTURE_PORTFOLIO_DIR
    stamp = _timestamp(generated_at)
    limitations = _limitations(action_queue)
    manifest = _manifest(
        root,
        target_dir,
        action_queue,
        class_summary,
        followup_summary,
        quality,
        input_paths,
        dossier_input_paths,
        upstream_manifests,
        limitations,
        command,
        code_revision,
        stamp,
    )
    _write_with_staging(
        target_dir,
        action_queue,
        class_summary,
        followup_summary,
        quality,
        manifest,
        stamp,
    )
    return manifest


def _manifest(
    root: Path,
    target_dir: Path,
    action_queue: pd.DataFrame,
    class_summary: pd.DataFrame,
    followup_summary: pd.DataFrame,
    quality: FieldArchitecturePortfolioQuality,
    input_paths: Iterable[str | Path],
    dossier_input_paths: Iterable[str | Path],
    upstream_manifests: Iterable[str | Path],
    limitations: tuple[str, ...],
    command: str | None,
    code_revision: str | None,
    stamp: str,
) -> FieldArchitecturePortfolioOutputManifest:
    return FieldArchitecturePortfolioOutputManifest(
        generated_at=stamp,
        output_root=root,
        output_dir=target_dir,
        action_queue_csv_path=target_dir / ACTION_QUEUE_CSV_FILENAME,
        action_queue_parquet_path=target_dir / ACTION_QUEUE_PARQUET_FILENAME,
        class_summary_csv_path=target_dir / CLASS_SUMMARY_CSV_FILENAME,
        class_summary_parquet_path=target_dir / CLASS_SUMMARY_PARQUET_FILENAME,
        followup_summary_csv_path=target_dir / FOLLOWUP_SUMMARY_CSV_FILENAME,
        followup_summary_parquet_path=target_dir / FOLLOWUP_SUMMARY_PARQUET_FILENAME,
        html_path=target_dir / HTML_FILENAME,
        quality_path=target_dir / QUALITY_FILENAME,
        component_quality_path=target_dir / COMPONENT_QUALITY_FILENAME,
        manifest_path=target_dir / MANIFEST_FILENAME,
        row_count=len(action_queue),
        class_summary_row_count=len(class_summary),
        followup_summary_row_count=len(followup_summary),
        input_paths=tuple(str(path) for path in input_paths),
        dossier_input_paths=tuple(str(path) for path in dossier_input_paths),
        upstream_manifests=tuple(str(path) for path in upstream_manifests),
        blocking_source_gaps=tuple(quality.blocking_source_gaps),
        informational_source_gaps=tuple(quality.informational_source_gaps),
        limitations=limitations,
        action_specs=_action_specs_payload(),
        command=command,
        code_revision=code_revision or _git_revision(),
    )


def _write_with_staging(
    target_dir: Path,
    action_queue: pd.DataFrame,
    class_summary: pd.DataFrame,
    followup_summary: pd.DataFrame,
    quality: FieldArchitecturePortfolioQuality,
    manifest: FieldArchitecturePortfolioOutputManifest,
    stamp: str,
) -> None:
    staging = target_dir.parent / f".staging-field-portfolio-{_compact_stamp(stamp)}"
    backup = target_dir.parent / f".backup-field-portfolio-{_compact_stamp(stamp)}"
    shutil.rmtree(staging, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    promoted = False
    try:
        staging.mkdir(parents=True, exist_ok=False)
        action_queue.to_csv(staging / ACTION_QUEUE_CSV_FILENAME, index=False)
        action_queue.to_parquet(staging / ACTION_QUEUE_PARQUET_FILENAME, index=False)
        class_summary.to_csv(staging / CLASS_SUMMARY_CSV_FILENAME, index=False)
        class_summary.to_parquet(staging / CLASS_SUMMARY_PARQUET_FILENAME, index=False)
        followup_summary.to_csv(staging / FOLLOWUP_SUMMARY_CSV_FILENAME, index=False)
        followup_summary.to_parquet(
            staging / FOLLOWUP_SUMMARY_PARQUET_FILENAME, index=False
        )
        (staging / HTML_FILENAME).write_text(
            render_field_architecture_portfolio_html(
                action_queue,
                class_summary,
                followup_summary,
                quality,
            ),
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
    manifest: FieldArchitecturePortfolioOutputManifest,
    quality: FieldArchitecturePortfolioQuality,
) -> dict[str, object]:
    payload = asdict(manifest)
    for key, value in list(payload.items()):
        if isinstance(value, Path):
            payload[key] = str(value)
    payload["input_paths"] = list(manifest.input_paths)
    payload["dossier_input_paths"] = list(manifest.dossier_input_paths)
    payload["upstream_manifests"] = list(manifest.upstream_manifests)
    payload["blocking_source_gaps"] = list(manifest.blocking_source_gaps)
    payload["informational_source_gaps"] = list(manifest.informational_source_gaps)
    payload["limitations"] = list(manifest.limitations)
    payload["quality"] = asdict(quality)
    return payload


def _action_specs_payload() -> dict[str, dict[str, object]]:
    return {
        architecture_class: asdict(spec)
        for architecture_class, spec in ACTION_SPECS.items()
    }


def _limitations(action_queue: pd.DataFrame) -> tuple[str, ...]:
    values: list[str] = []
    if "portfolio_limitations" in action_queue:
        for value in action_queue["portfolio_limitations"]:
            values.extend(
                part.strip() for part in str(value).split(";") if part.strip()
            )
    return tuple(dict.fromkeys(values)) or PORTFOLIO_LIMITATIONS


def _validate_output_root(root: Path, allow_non_ace_root: bool) -> None:
    if allow_non_ace_root:
        return
    if not root.resolve().is_relative_to(SOURCE_CATALOG_ROOT.resolve()):
        raise ValueError(
            "field-architecture portfolio output_root must stay under "
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
    "FIELD_ARCHITECTURE_PORTFOLIO_DIR",
    "FieldArchitecturePortfolioOutputManifest",
    "write_field_architecture_portfolio_outputs",
]
