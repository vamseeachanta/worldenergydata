"""Load direct curated inputs for Texas RRC field-architecture dossiers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from worldenergydata.texas_rrc.field_development.io import (
    CSV_FILENAME as FIELD_DEVELOPMENT_CSV_FILENAME,
)
from worldenergydata.texas_rrc.field_development.io import (
    FIELD_DEVELOPMENT_METRICS_DIR,
    PARQUET_FILENAME as FIELD_DEVELOPMENT_PARQUET_FILENAME,
)
from worldenergydata.texas_rrc.opportunities.io import (
    FIELD_OPPORTUNITY_DIR,
    MANIFEST_FILENAME,
    RANKINGS_CSV_FILENAME,
    RANKINGS_PARQUET_FILENAME,
)
from worldenergydata.texas_rrc.reports.io import (
    FIELD_ATLAS_REPORT_DIR,
    SUMMARY_CSV_FILENAME,
    SUMMARY_PARQUET_FILENAME,
)


@dataclass(frozen=True)
class FieldArchitectureDossierInputs:
    """Curated inputs used to publish field-architecture dossiers."""

    rankings: pd.DataFrame
    field_atlas_summary: pd.DataFrame
    field_development_metrics: pd.DataFrame
    input_paths: tuple[Path, ...]
    upstream_manifests: tuple[Path, ...]
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]


def load_field_architecture_dossier_inputs(
    root: Path | str,
) -> FieldArchitectureDossierInputs:
    """Load ranking, manifest, and context artifacts for dossier publication."""
    catalog_root = Path(root)
    opportunity_dir = catalog_root / FIELD_OPPORTUNITY_DIR
    atlas_dir = catalog_root / FIELD_ATLAS_REPORT_DIR
    development_dir = catalog_root / FIELD_DEVELOPMENT_METRICS_DIR

    blocking_gaps: list[str] = []
    informational_gaps: list[str] = []
    input_paths: list[Path] = []

    ranking_path = _existing_data_path(
        opportunity_dir,
        RANKINGS_PARQUET_FILENAME,
        RANKINGS_CSV_FILENAME,
    )
    rankings = _load_required_frame(
        ranking_path,
        "missing_field_opportunity_rankings",
        blocking_gaps,
        input_paths,
    )

    opportunity_manifest = opportunity_dir / MANIFEST_FILENAME
    manifest_payload = _load_manifest(
        opportunity_manifest,
        "missing_field_opportunity_manifest",
        blocking_gaps,
        input_paths,
    )
    upstream_manifests = _upstream_manifest_paths(catalog_root, manifest_payload)
    input_paths.extend(upstream_manifests)
    informational_gaps.extend(_manifest_gaps(manifest_payload))
    for manifest in upstream_manifests:
        if not manifest.exists():
            blocking_gaps.append(f"missing_upstream_manifest:{manifest.name}")
            continue
        payload = _load_optional_manifest(manifest, blocking_gaps)
        informational_gaps.extend(_manifest_gaps(payload))

    atlas_path = _existing_data_path(
        atlas_dir,
        SUMMARY_PARQUET_FILENAME,
        SUMMARY_CSV_FILENAME,
    )
    field_atlas_summary = _load_required_frame(
        atlas_path,
        "missing_field_atlas_summary",
        blocking_gaps,
        input_paths,
    )

    development_path = _existing_data_path(
        development_dir,
        FIELD_DEVELOPMENT_PARQUET_FILENAME,
        FIELD_DEVELOPMENT_CSV_FILENAME,
    )
    field_development_metrics = _load_required_frame(
        development_path,
        "missing_field_development_metrics",
        blocking_gaps,
        input_paths,
    )

    return FieldArchitectureDossierInputs(
        rankings=rankings,
        field_atlas_summary=field_atlas_summary,
        field_development_metrics=field_development_metrics,
        input_paths=tuple(input_paths),
        upstream_manifests=tuple(upstream_manifests),
        blocking_source_gaps=_dedupe(blocking_gaps),
        informational_source_gaps=_dedupe(informational_gaps),
    )


def _existing_data_path(
    directory: Path,
    parquet_filename: str,
    csv_filename: str,
) -> Path | None:
    parquet_path = directory / parquet_filename
    if parquet_path.exists():
        return parquet_path
    csv_path = directory / csv_filename
    return csv_path if csv_path.exists() else None


def _load_required_frame(
    path: Path | None,
    missing_gap: str,
    blocking_gaps: list[str],
    input_paths: list[Path],
) -> pd.DataFrame:
    if path is None:
        blocking_gaps.append(missing_gap)
        return pd.DataFrame()
    input_paths.append(path)
    return _load_frame(path)


def _load_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(path)
    else:
        frame = pd.read_csv(path, dtype={"district": "string", "field_number": "string"})
    return _normalize_key_columns(frame)


def _normalize_key_columns(frame: pd.DataFrame) -> pd.DataFrame:
    for column in ("district", "field_number"):
        if column in frame:
            frame[column] = frame[column].astype("string")
    return frame


def _load_manifest(
    path: Path,
    missing_gap: str,
    blocking_gaps: list[str],
    input_paths: list[Path],
) -> dict[str, object]:
    if not path.exists():
        blocking_gaps.append(missing_gap)
        return {}
    input_paths.append(path)
    return _load_optional_manifest(path, blocking_gaps)


def _load_optional_manifest(
    path: Path,
    blocking_gaps: list[str],
) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        blocking_gaps.append("unreadable_manifest")
        return {}


def _upstream_manifest_paths(
    root: Path,
    manifest_payload: dict[str, object],
) -> tuple[Path, ...]:
    values = manifest_payload.get("upstream_manifests")
    if not isinstance(values, list):
        return ()
    paths = []
    for value in values:
        path = Path(str(value))
        paths.append(path if path.is_absolute() else root / path)
    return tuple(paths)


def _manifest_gaps(payload: dict[str, object]) -> list[str]:
    gaps = _string_sequence(payload.get("source_gaps"))
    gaps.extend(_string_sequence(payload.get("metric_gaps")))
    quality = payload.get("quality")
    if isinstance(quality, dict):
        gaps.extend(_string_sequence(quality.get("source_gaps")))
        gaps.extend(_string_sequence(quality.get("metric_gaps")))
    return gaps


def _string_sequence(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)


__all__ = [
    "FieldArchitectureDossierInputs",
    "load_field_architecture_dossier_inputs",
]
