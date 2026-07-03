"""Persist Texas RRC pressure-observation outputs."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT

PRESSURE_OBSERVATION_DIR = Path("curated") / "pressure" / "well_pressure_observations"
NORMALIZED_PRESSURE_DIR = Path("normalized") / "pressure"
OBSERVATIONS_CSV_FILENAME = "texas_rrc_well_pressure_observations.csv"
OBSERVATIONS_PARQUET_FILENAME = "texas_rrc_well_pressure_observations.parquet"
CANDIDATES_CSV_FILENAME = "texas_rrc_pressure_candidates.csv"
CANDIDATES_PARQUET_FILENAME = "texas_rrc_pressure_candidates.parquet"
COVERAGE_BY_DISTRICT_DECADE_CSV_FILENAME = "coverage_by_district_decade.csv"
COVERAGE_BY_DISTRICT_DECADE_PARQUET_FILENAME = "coverage_by_district_decade.parquet"
COVERAGE_BY_FIELD_DECADE_CSV_FILENAME = "coverage_by_field_decade.csv"
COVERAGE_BY_FIELD_DECADE_PARQUET_FILENAME = "coverage_by_field_decade.parquet"
QUALITY_FILENAME = "texas_rrc_pressure_observation_quality.json"
MANIFEST_FILENAME = "manifest.json"
PRESSURE_DTYPES = {
    "api14": "string",
    "api10": "string",
    "district": "string",
    "field_no": "string",
    "field_name": "string",
    "lease_number": "string",
    "operator_number": "string",
    "source_tracking_no": "string",
    "source_packet_id": "string",
    "source_form_id": "string",
}


@dataclass(frozen=True)
class PressureObservationOutputManifest:
    """Paths and metadata for one pressure-observation output batch."""

    generated_at: str
    output_root: Path
    observations_csv_path: Path
    observations_parquet_path: Path
    candidates_csv_path: Path
    candidates_parquet_path: Path
    coverage_by_district_decade_csv_path: Path
    coverage_by_district_decade_parquet_path: Path
    coverage_by_field_decade_csv_path: Path
    coverage_by_field_decade_parquet_path: Path
    quality_path: Path
    manifest_path: Path
    row_count: int
    candidate_count: int
    input_paths: tuple[str, ...]
    input_artifacts: tuple[dict[str, object], ...]
    source_gaps: tuple[str, ...]
    source_warnings: tuple[str, ...]
    command: str | None
    code_revision: str | None


def write_pressure_observation_outputs(
    observations: pd.DataFrame,
    candidates: pd.DataFrame,
    coverage_by_district_decade: pd.DataFrame,
    coverage_by_field_decade: pd.DataFrame,
    quality: dict[str, object],
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    generated_at: datetime | None = None,
    input_paths: Iterable[str | Path] = (),
    input_artifacts: Sequence[dict[str, object]] = (),
    source_gaps: Sequence[str] = (),
    source_warnings: Sequence[str] = (),
    allow_non_ace_root: bool = False,
    command: str | None = None,
    code_revision: str | None = None,
) -> PressureObservationOutputManifest:
    """Write curated observations, normalized candidates, quality, and manifest."""
    root = Path(output_root)
    _validate_output_root(root, allow_non_ace_root)
    stamp = _timestamp(generated_at)
    manifest = _build_manifest(
        root=root,
        stamp=stamp,
        observations=observations,
        candidates=candidates,
        input_paths=input_paths,
        input_artifacts=input_artifacts,
        source_gaps=source_gaps,
        source_warnings=source_warnings,
        command=command,
        code_revision=code_revision,
    )
    _write_with_staging(
        observations,
        candidates,
        coverage_by_district_decade,
        coverage_by_field_decade,
        quality,
        manifest,
        stamp,
    )
    return manifest


def _build_manifest(
    *,
    root: Path,
    stamp: str,
    observations: pd.DataFrame,
    candidates: pd.DataFrame,
    input_paths: Iterable[str | Path],
    input_artifacts: Sequence[dict[str, object]],
    source_gaps: Sequence[str],
    source_warnings: Sequence[str],
    command: str | None,
    code_revision: str | None,
) -> PressureObservationOutputManifest:
    curated_dir = root / PRESSURE_OBSERVATION_DIR
    normalized_dir = root / NORMALIZED_PRESSURE_DIR
    return PressureObservationOutputManifest(
        generated_at=stamp,
        output_root=root,
        observations_csv_path=curated_dir / OBSERVATIONS_CSV_FILENAME,
        observations_parquet_path=curated_dir / OBSERVATIONS_PARQUET_FILENAME,
        candidates_csv_path=normalized_dir / CANDIDATES_CSV_FILENAME,
        candidates_parquet_path=normalized_dir / CANDIDATES_PARQUET_FILENAME,
        coverage_by_district_decade_csv_path=_curated_path(
            curated_dir, COVERAGE_BY_DISTRICT_DECADE_CSV_FILENAME
        ),
        coverage_by_district_decade_parquet_path=_curated_path(
            curated_dir, COVERAGE_BY_DISTRICT_DECADE_PARQUET_FILENAME
        ),
        coverage_by_field_decade_csv_path=_curated_path(
            curated_dir, COVERAGE_BY_FIELD_DECADE_CSV_FILENAME
        ),
        coverage_by_field_decade_parquet_path=_curated_path(
            curated_dir, COVERAGE_BY_FIELD_DECADE_PARQUET_FILENAME
        ),
        quality_path=curated_dir / QUALITY_FILENAME,
        manifest_path=curated_dir / MANIFEST_FILENAME,
        row_count=len(observations),
        candidate_count=len(candidates),
        input_paths=tuple(str(path) for path in input_paths),
        input_artifacts=tuple(dict(artifact) for artifact in input_artifacts),
        source_gaps=tuple(source_gaps),
        source_warnings=tuple(source_warnings),
        command=command,
        code_revision=code_revision or _git_revision(),
    )


def _curated_path(curated_dir: Path, filename: str) -> Path:
    return curated_dir / filename


def load_pressure_observations(path: Path | str) -> pd.DataFrame:
    """Load persisted pressure observations from CSV or Parquet."""
    pressure_path = Path(path)
    if pressure_path.suffix.lower() == ".parquet":
        return pd.read_parquet(pressure_path)
    return pd.read_csv(pressure_path, dtype=PRESSURE_DTYPES)


def _write_with_staging(
    observations: pd.DataFrame,
    candidates: pd.DataFrame,
    coverage_by_district_decade: pd.DataFrame,
    coverage_by_field_decade: pd.DataFrame,
    quality: dict[str, object],
    manifest: PressureObservationOutputManifest,
    stamp: str,
) -> None:
    curated_dir = manifest.observations_csv_path.parent
    normalized_dir = manifest.candidates_csv_path.parent
    curated_staging = (
        curated_dir / f".staging-pressure-observations-{_compact_stamp(stamp)}"
    )
    normalized_staging = (
        normalized_dir / f".staging-pressure-candidates-{_compact_stamp(stamp)}"
    )
    shutil.rmtree(curated_staging, ignore_errors=True)
    shutil.rmtree(normalized_staging, ignore_errors=True)
    try:
        curated_staging.mkdir(parents=True, exist_ok=False)
        normalized_staging.mkdir(parents=True, exist_ok=False)
        _write_curated_staging(
            curated_staging,
            observations,
            coverage_by_district_decade,
            coverage_by_field_decade,
            quality,
            manifest,
        )
        _write_normalized_staging(normalized_staging, candidates)
        _promote(curated_staging, curated_dir, _curated_filenames())
        _promote(normalized_staging, normalized_dir, _normalized_filenames())
    finally:
        shutil.rmtree(curated_staging, ignore_errors=True)
        shutil.rmtree(normalized_staging, ignore_errors=True)


def _write_curated_staging(
    staging: Path,
    observations: pd.DataFrame,
    coverage_by_district_decade: pd.DataFrame,
    coverage_by_field_decade: pd.DataFrame,
    quality: dict[str, object],
    manifest: PressureObservationOutputManifest,
) -> None:
    observations.to_csv(staging / OBSERVATIONS_CSV_FILENAME, index=False)
    observations.to_parquet(staging / OBSERVATIONS_PARQUET_FILENAME, index=False)
    coverage_by_district_decade.to_csv(
        staging / COVERAGE_BY_DISTRICT_DECADE_CSV_FILENAME, index=False
    )
    coverage_by_district_decade.to_parquet(
        staging / COVERAGE_BY_DISTRICT_DECADE_PARQUET_FILENAME, index=False
    )
    coverage_by_field_decade.to_csv(
        staging / COVERAGE_BY_FIELD_DECADE_CSV_FILENAME, index=False
    )
    coverage_by_field_decade.to_parquet(
        staging / COVERAGE_BY_FIELD_DECADE_PARQUET_FILENAME, index=False
    )
    _write_json(staging / QUALITY_FILENAME, _quality_payload(manifest, quality))
    _write_json(staging / MANIFEST_FILENAME, _manifest_payload(manifest, quality))


def _write_normalized_staging(staging: Path, candidates: pd.DataFrame) -> None:
    candidates.to_csv(staging / CANDIDATES_CSV_FILENAME, index=False)
    candidates.to_parquet(staging / CANDIDATES_PARQUET_FILENAME, index=False)


def _promote(staging: Path, target_dir: Path, filenames: tuple[str, ...]) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        (staging / filename).replace(target_dir / filename)


def _curated_filenames() -> tuple[str, ...]:
    return (
        OBSERVATIONS_CSV_FILENAME,
        OBSERVATIONS_PARQUET_FILENAME,
        COVERAGE_BY_DISTRICT_DECADE_CSV_FILENAME,
        COVERAGE_BY_DISTRICT_DECADE_PARQUET_FILENAME,
        COVERAGE_BY_FIELD_DECADE_CSV_FILENAME,
        COVERAGE_BY_FIELD_DECADE_PARQUET_FILENAME,
        QUALITY_FILENAME,
        MANIFEST_FILENAME,
    )


def _normalized_filenames() -> tuple[str, ...]:
    return (CANDIDATES_CSV_FILENAME, CANDIDATES_PARQUET_FILENAME)


def _validate_output_root(root: Path, allow_non_ace_root: bool) -> None:
    if allow_non_ace_root:
        return
    if not root.resolve().is_relative_to(SOURCE_CATALOG_ROOT.resolve()):
        raise ValueError(
            "Pressure-observation output_root must stay under "
            f"{SOURCE_CATALOG_ROOT}; pass allow_non_ace_root=True only for "
            "isolated tests or sandbox runs"
        )


def _quality_payload(
    manifest: PressureObservationOutputManifest,
    quality: dict[str, object],
) -> dict[str, object]:
    payload = dict(quality)
    payload.update(
        {
            "row_count": manifest.row_count,
            "candidate_count": manifest.candidate_count,
            "source_gaps": list(manifest.source_gaps),
            "source_warnings": list(manifest.source_warnings),
        }
    )
    return payload


def _manifest_payload(
    manifest: PressureObservationOutputManifest,
    quality: dict[str, object],
) -> dict[str, object]:
    return {
        "generated_at": manifest.generated_at,
        "output_root": str(manifest.output_root),
        "observations_csv_path": str(manifest.observations_csv_path),
        "observations_parquet_path": str(manifest.observations_parquet_path),
        "candidates_csv_path": str(manifest.candidates_csv_path),
        "candidates_parquet_path": str(manifest.candidates_parquet_path),
        "coverage_by_district_decade_csv_path": str(
            manifest.coverage_by_district_decade_csv_path
        ),
        "coverage_by_district_decade_parquet_path": str(
            manifest.coverage_by_district_decade_parquet_path
        ),
        "coverage_by_field_decade_csv_path": str(
            manifest.coverage_by_field_decade_csv_path
        ),
        "coverage_by_field_decade_parquet_path": str(
            manifest.coverage_by_field_decade_parquet_path
        ),
        "quality_path": str(manifest.quality_path),
        "manifest_path": str(manifest.manifest_path),
        "row_count": manifest.row_count,
        "candidate_count": manifest.candidate_count,
        "input_paths": list(manifest.input_paths),
        "input_artifacts": list(manifest.input_artifacts),
        "source_gaps": list(manifest.source_gaps),
        "source_warnings": list(manifest.source_warnings),
        "command": manifest.command,
        "code_revision": manifest.code_revision,
        "quality": _quality_payload(manifest, quality),
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
    repo_root = Path(__file__).resolve().parents[5]
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    suffix = "+dirty" if status.stdout.strip() else ""
    value = revision.stdout.strip()
    return f"{value}{suffix}" if value else None


__all__ = [
    "NORMALIZED_PRESSURE_DIR",
    "PRESSURE_OBSERVATION_DIR",
    "PressureObservationOutputManifest",
    "load_pressure_observations",
    "write_pressure_observation_outputs",
]
