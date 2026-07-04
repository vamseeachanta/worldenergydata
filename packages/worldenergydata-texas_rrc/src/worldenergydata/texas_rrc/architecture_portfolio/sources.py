"""Load #702 dossier outputs for Texas RRC portfolio publication."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from worldenergydata.texas_rrc.dossiers.io import (
    FIELD_ARCHITECTURE_DOSSIER_DIR,
    INDEX_CSV_FILENAME,
    INDEX_PARQUET_FILENAME,
    MANIFEST_FILENAME,
    QUALITY_FILENAME,
)


@dataclass(frozen=True)
class FieldArchitecturePortfolioInputs:
    """Curated #702 dossier packet used to build the portfolio report."""

    dossier_index: pd.DataFrame
    input_dossier_dir: Path
    index_path: Path | None
    manifest_path: Path
    quality_path: Path
    dossier_manifest: dict[str, object]
    dossier_quality: dict[str, object]
    input_paths: tuple[Path, ...]
    dossier_input_paths: tuple[Path, ...]
    upstream_manifest_paths: tuple[Path, ...]
    dossier_page_paths: tuple[Path, ...]
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]


def load_field_architecture_portfolio_inputs(
    root: Path | str,
) -> FieldArchitecturePortfolioInputs:
    """Load the direct #702 dossier packet from a Texas RRC module root."""
    catalog_root = Path(root)
    dossier_dir = catalog_root / FIELD_ARCHITECTURE_DOSSIER_DIR
    blocking_gaps: list[str] = []
    input_paths: list[Path] = []

    index_path = _existing_index_path(dossier_dir)
    dossier_index = _load_index(index_path, blocking_gaps, input_paths)

    manifest_path = dossier_dir / MANIFEST_FILENAME
    manifest = _load_json(
        manifest_path,
        "missing_field_architecture_dossier_manifest",
        blocking_gaps,
        input_paths,
    )

    quality_path = dossier_dir / QUALITY_FILENAME
    quality = _load_json(
        quality_path,
        "missing_field_architecture_dossier_quality",
        blocking_gaps,
        input_paths,
    )

    return FieldArchitecturePortfolioInputs(
        dossier_index=dossier_index,
        input_dossier_dir=dossier_dir,
        index_path=index_path,
        manifest_path=manifest_path,
        quality_path=quality_path,
        dossier_manifest=manifest,
        dossier_quality=quality,
        input_paths=tuple(input_paths),
        dossier_input_paths=_path_sequence(manifest.get("input_paths")),
        upstream_manifest_paths=_upstream_manifest_paths(manifest),
        dossier_page_paths=_dossier_page_paths(dossier_dir, dossier_index),
        blocking_source_gaps=_dedupe(
            [
                *blocking_gaps,
                *_gap_sequence(manifest, quality, "blocking_source_gaps"),
            ]
        ),
        informational_source_gaps=_dedupe(
            _gap_sequence(manifest, quality, "informational_source_gaps")
        ),
    )


def _existing_index_path(dossier_dir: Path) -> Path | None:
    parquet_path = dossier_dir / INDEX_PARQUET_FILENAME
    if parquet_path.exists():
        return parquet_path
    csv_path = dossier_dir / INDEX_CSV_FILENAME
    return csv_path if csv_path.exists() else None


def _load_index(
    path: Path | None,
    blocking_gaps: list[str],
    input_paths: list[Path],
) -> pd.DataFrame:
    if path is None:
        blocking_gaps.append("missing_field_architecture_dossier_index")
        return pd.DataFrame()
    input_paths.append(path)
    if path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(path)
    else:
        frame = pd.read_csv(
            path, dtype={"district": "string", "field_number": "string"}
        )
    return _normalize_key_columns(frame)


def _normalize_key_columns(frame: pd.DataFrame) -> pd.DataFrame:
    for column in ("district", "field_number"):
        if column in frame:
            frame[column] = frame[column].astype("string")
    return frame


def _load_json(
    path: Path,
    missing_gap: str,
    blocking_gaps: list[str],
    input_paths: list[Path],
) -> dict[str, object]:
    if not path.exists():
        blocking_gaps.append(missing_gap)
        return {}
    input_paths.append(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        blocking_gaps.append(f"unreadable_{path.stem}")
        return {}


def _upstream_manifest_paths(manifest: dict[str, object]) -> tuple[Path, ...]:
    paths = []
    for values in (manifest.get("input_paths"), manifest.get("upstream_manifests")):
        if not isinstance(values, list):
            continue
        paths.extend(
            Path(str(value))
            for value in values
            if Path(str(value)).name == "manifest.json"
        )
    return _dedupe_paths(paths)


def _path_sequence(value: object) -> tuple[Path, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(Path(str(item)) for item in value if str(item))


def _dossier_page_paths(dossier_dir: Path, index: pd.DataFrame) -> tuple[Path, ...]:
    if "dossier_path" not in index:
        return tuple(sorted((dossier_dir / "fields").glob("*.html")))
    paths = []
    for value in index["dossier_path"]:
        if pd.isna(value):
            continue
        path = Path(str(value))
        candidate = path if path.is_absolute() else dossier_dir / path
        if candidate.exists() and candidate.suffix.lower() == ".html":
            paths.append(candidate)
    return tuple(paths)


def _gap_sequence(
    manifest: dict[str, object],
    quality: dict[str, object],
    key: str,
) -> list[str]:
    values: list[str] = []
    values.extend(_string_sequence(manifest.get(key)))
    manifest_quality = manifest.get("quality")
    if isinstance(manifest_quality, dict):
        values.extend(_string_sequence(manifest_quality.get(key)))
    values.extend(_string_sequence(quality.get(key)))
    return values


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


def _dedupe_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    seen = set()
    result = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return tuple(result)


__all__ = [
    "FieldArchitecturePortfolioInputs",
    "load_field_architecture_portfolio_inputs",
]
