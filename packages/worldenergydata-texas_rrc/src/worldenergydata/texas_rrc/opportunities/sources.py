"""Load direct curated inputs for Texas RRC field-opportunity rankings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from worldenergydata.texas_rrc.field_development.io import (
    FIELD_DEVELOPMENT_METRICS_DIR,
)
from worldenergydata.texas_rrc.infrastructure.io import INFRASTRUCTURE_ACCESS_DIR
from worldenergydata.texas_rrc.production_atlas.io import PRODUCTION_ATLAS_DIR
from worldenergydata.texas_rrc.reports.io import (
    FIELD_ATLAS_REPORT_DIR,
    MANIFEST_FILENAME,
    SUMMARY_CSV_FILENAME,
    SUMMARY_PARQUET_FILENAME,
)


@dataclass(frozen=True)
class FieldOpportunityInputs:
    """Direct curated inputs used to rank Texas RRC field opportunities."""

    field_atlas_summary: pd.DataFrame
    input_paths: tuple[Path, ...]
    source_gaps: tuple[str, ...]
    upstream_manifests: tuple[Path, ...]


def load_field_opportunity_inputs(root: Path | str) -> FieldOpportunityInputs:
    """Load the #666 field-atlas summary and upstream manifests."""
    catalog_root = Path(root)
    report_dir = catalog_root / FIELD_ATLAS_REPORT_DIR
    data_path = _existing_data_path(report_dir)
    manifests = _upstream_manifest_paths(catalog_root)
    paths = ((data_path,) if data_path else ()) + manifests
    gaps = []
    for manifest in manifests:
        gaps.extend(_manifest_source_gaps(manifest))
    if data_path is None:
        gaps.insert(0, "missing_field_atlas_summary")
        summary = pd.DataFrame()
    else:
        summary = _load_frame(data_path)
    return FieldOpportunityInputs(
        field_atlas_summary=summary,
        input_paths=paths,
        source_gaps=_dedupe(gaps),
        upstream_manifests=manifests,
    )


def _existing_data_path(directory: Path) -> Path | None:
    parquet_path = directory / SUMMARY_PARQUET_FILENAME
    if parquet_path.exists():
        return parquet_path
    csv_path = directory / SUMMARY_CSV_FILENAME
    return csv_path if csv_path.exists() else None


def _load_frame(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
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


def _upstream_manifest_paths(root: Path) -> tuple[Path, ...]:
    candidates = (
        root / FIELD_ATLAS_REPORT_DIR / MANIFEST_FILENAME,
        root / FIELD_DEVELOPMENT_METRICS_DIR / MANIFEST_FILENAME,
        root / INFRASTRUCTURE_ACCESS_DIR / MANIFEST_FILENAME,
        root / PRODUCTION_ATLAS_DIR / MANIFEST_FILENAME,
    )
    return tuple(path for path in candidates if path.exists())


def _manifest_source_gaps(manifest_path: Path) -> list[str]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["unreadable_manifest"]
    gaps = _string_sequence(payload.get("source_gaps"))
    if not gaps and isinstance(payload.get("quality"), dict):
        gaps = _string_sequence(payload["quality"].get("source_gaps"))
    return gaps


def _string_sequence(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)


__all__ = [
    "FieldOpportunityInputs",
    "load_field_opportunity_inputs",
]
