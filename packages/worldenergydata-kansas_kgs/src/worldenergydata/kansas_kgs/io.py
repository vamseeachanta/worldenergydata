"""Persist Kansas KGS normalized and curated pressure artifacts."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from worldenergydata.kansas_kgs.raw_sources import DEFAULT_KANSAS_KGS_ROOT

NORMALIZED_PRESSURE = Path("normalized/pressure/kansas_proration_pressures.parquet")
NORMALIZED_WELLS = Path("normalized/wells/ks_wells.parquet")
CURATED_DIR = Path("curated/pressure/well_pressure_observations")
CSV_FILENAME = "well_pressure_observations.csv"
PARQUET_FILENAME = "well_pressure_observations.parquet"
QUALITY_FILENAME = "quality.json"
MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class PressureObservationOutputManifest:
    """Paths and summary metadata for Kansas KGS pressure outputs."""

    generated_at: str
    output_root: Path
    csv_path: Path
    parquet_path: Path
    quality_path: Path
    manifest_path: Path
    row_count: int


def write_pressure_observation_outputs(
    normalized_pressure: pd.DataFrame,
    normalized_wells: pd.DataFrame,
    observations: pd.DataFrame,
    coverage: pd.DataFrame,
    quality: dict[str, object],
    output_root: Path | str = DEFAULT_KANSAS_KGS_ROOT,
    generated_at: datetime | None = None,
    input_paths: Iterable[str | Path] = (),
    source_manifest: Mapping[str, object] | None = None,
    limitations: Iterable[str] = (),
    allow_non_ace_root: bool = False,
    command: str | None = None,
    code_revision: str | None = None,
) -> PressureObservationOutputManifest:
    """Write normalized and curated Kansas KGS pressure artifacts."""
    root = Path(output_root)
    _validate_output_root(root, allow_non_ace_root)
    stamp = _timestamp(generated_at)
    target = root / CURATED_DIR
    manifest = PressureObservationOutputManifest(
        generated_at=stamp,
        output_root=root,
        csv_path=target / CSV_FILENAME,
        parquet_path=target / PARQUET_FILENAME,
        quality_path=target / QUALITY_FILENAME,
        manifest_path=target / MANIFEST_FILENAME,
        row_count=len(observations),
    )
    staging = target / f".staging-kansas-kgs-pressure-{_compact(stamp)}"
    shutil.rmtree(staging, ignore_errors=True)
    try:
        staging.mkdir(parents=True, exist_ok=False)
        _write_normalized(staging, normalized_pressure, normalized_wells)
        observations.to_csv(staging / CSV_FILENAME, index=False)
        observations.to_parquet(staging / PARQUET_FILENAME, index=False)
        coverage.to_csv(staging / "coverage_by_county_year.csv", index=False)
        coverage.to_parquet(staging / "coverage_by_county_year.parquet", index=False)
        _write_json(staging / QUALITY_FILENAME, quality)
        _write_json(
            staging / MANIFEST_FILENAME,
            _manifest_payload(
                manifest=manifest,
                quality=quality,
                input_paths=input_paths,
                command=command,
                code_revision=code_revision,
                source_manifest=source_manifest,
                limitations=limitations,
                output_paths=_output_paths(staging),
            ),
        )
        (root / NORMALIZED_PRESSURE).parent.mkdir(parents=True, exist_ok=True)
        (root / NORMALIZED_WELLS).parent.mkdir(parents=True, exist_ok=True)
        (staging / NORMALIZED_PRESSURE).replace(root / NORMALIZED_PRESSURE)
        (staging / NORMALIZED_WELLS).replace(root / NORMALIZED_WELLS)
        target.mkdir(parents=True, exist_ok=True)
        for path in staging.iterdir():
            if path.name == "normalized":
                continue
            path.replace(target / path.name)
        return manifest
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def load_pressure_observations(path: Path | str) -> pd.DataFrame:
    """Load curated pressure observations while preserving API key strings."""
    return pd.read_csv(
        path,
        dtype={
            "api14": "string",
            "api10": "string",
            "api_state_code": "string",
            "api_county_code": "string",
        },
    )


def _write_normalized(
    root: Path,
    normalized_pressure: pd.DataFrame,
    normalized_wells: pd.DataFrame,
) -> None:
    pressure_path = root / NORMALIZED_PRESSURE
    wells_path = root / NORMALIZED_WELLS
    pressure_path.parent.mkdir(parents=True, exist_ok=True)
    wells_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_pressure.to_parquet(pressure_path, index=False)
    normalized_wells.to_parquet(wells_path, index=False)


def _validate_output_root(root: Path, allow_non_ace_root: bool) -> None:
    if allow_non_ace_root:
        return
    if not root.resolve().is_relative_to(DEFAULT_KANSAS_KGS_ROOT.resolve()):
        raise ValueError(
            f"Kansas KGS output_root must stay under {DEFAULT_KANSAS_KGS_ROOT}"
        )


def _manifest_payload(
    manifest: PressureObservationOutputManifest,
    quality: dict[str, object],
    input_paths: Iterable[str | Path],
    command: str | None,
    code_revision: str | None,
    source_manifest: Mapping[str, object] | None,
    limitations: Iterable[str],
    output_paths: Mapping[str, Path],
) -> dict[str, object]:
    return {
        "generated_at": manifest.generated_at,
        "output_root": str(manifest.output_root),
        "csv_path": str(manifest.csv_path),
        "parquet_path": str(manifest.parquet_path),
        "quality_path": str(manifest.quality_path),
        "manifest_path": str(manifest.manifest_path),
        "row_count": manifest.row_count,
        "input_paths": [str(path) for path in input_paths],
        "source_manifest": dict(source_manifest or {}),
        "output_hashes": {
            name: _file_snapshot(path) for name, path in sorted(output_paths.items())
        },
        "quality": quality,
        "limitations": list(limitations),
        "command": command,
        "code_revision": code_revision or _git_revision(),
    }


def _output_paths(staging: Path) -> dict[str, Path]:
    return {
        CSV_FILENAME: staging / CSV_FILENAME,
        PARQUET_FILENAME: staging / PARQUET_FILENAME,
        "coverage_by_county_year.csv": staging / "coverage_by_county_year.csv",
        "coverage_by_county_year.parquet": staging / "coverage_by_county_year.parquet",
        QUALITY_FILENAME: staging / QUALITY_FILENAME,
        str(NORMALIZED_PRESSURE): staging / NORMALIZED_PRESSURE,
        str(NORMALIZED_WELLS): staging / NORMALIZED_WELLS,
    }


def _file_snapshot(path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return {"size_bytes": size, "sha256": digest.hexdigest()}


def _git_revision() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    return result.stdout.strip()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _timestamp(value: datetime | None) -> str:
    stamp = value or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compact(value: str) -> str:
    return value.replace("-", "").replace(":", "")
