"""Observation normalization for the under-pressured screen."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REQUIRED_SCREEN_COLUMNS = (
    "well_key",
    "state",
    "field",
    "test_year",
    "pressure_kind",
    "pressure_psia",
    "reference_depth_ft",
)

TEXAS_COLUMN_MAP = {
    "api14": "well_key",
    "field_name": "field",
}

OKLAHOMA_COLUMN_MAP = {
    "formation_name": "field",
}


def normalize_observations(frame: pd.DataFrame, input_config: dict) -> pd.DataFrame:
    """Normalize one source-specific pressure table to the screen contract."""
    schema = input_config.get("schema", "screen_v1")
    if schema == "screen_v1":
        normalized = frame.copy()
    elif schema == "texas_rrc_pressure_v1":
        normalized = _normalize_texas_pressure(frame, input_config)
    elif schema == "oklahoma_occ_completion_v1":
        normalized = _normalize_oklahoma_occ_completion(frame, input_config)
    else:
        raise ValueError(f"Unsupported pressure screen input schema: {schema}")

    normalized["source_name"] = input_config["name"]
    normalized["era"] = input_config["era"]
    if "state" in input_config:
        if "state" not in normalized:
            normalized["state"] = input_config["state"]
        else:
            normalized["state"] = normalized["state"].fillna(input_config["state"])
    if "screen_observation_priority" not in normalized:
        normalized["screen_observation_priority"] = 0
    _validate_required_columns(normalized, input_config["name"])
    return normalized


def load_observations(inputs: list[dict]) -> tuple[pd.DataFrame, dict]:
    """Load and normalize all configured pressure-observation inputs."""
    frames = []
    summary = {
        "input_row_counts": {},
        "loaded_row_counts": {},
        "source_warnings": {},
    }
    for entry in inputs:
        frame = pd.read_parquet(entry["path"])
        summary["input_row_counts"][entry["name"]] = int(len(frame))
        normalized = normalize_observations(frame, entry)
        summary["loaded_row_counts"][entry["name"]] = int(len(normalized))
        warnings = _read_source_warnings(entry.get("quality_path"))
        if warnings:
            summary["source_warnings"][entry["name"]] = warnings
        frames.append(normalized)
    return pd.concat(frames, ignore_index=True), summary


def _normalize_texas_pressure(frame: pd.DataFrame, input_config: dict) -> pd.DataFrame:
    required = set(TEXAS_COLUMN_MAP) | {
        "test_year",
        "pressure_kind",
        "pressure_psia",
        "reference_depth_ft",
    }
    _validate_columns(frame, required, input_config["name"])
    normalized = frame.rename(columns=TEXAS_COLUMN_MAP).copy()
    normalized["well_key"] = normalized["well_key"].astype("string")
    if "is_earliest_observation_for_well" in normalized:
        earliest = _truthy(normalized["is_earliest_observation_for_well"])
        normalized["screen_observation_priority"] = (~earliest).astype(int)
    if input_config.get("require_usable_proxy"):
        _validate_columns(
            normalized, {"usable_for_virgin_pressure_proxy"}, input_config["name"]
        )
        usable = _truthy(normalized["usable_for_virgin_pressure_proxy"])
        normalized = normalized[usable].copy()
    return normalized


def _normalize_oklahoma_occ_completion(
    frame: pd.DataFrame, input_config: dict
) -> pd.DataFrame:
    required = {
        "well_key",
        "test_year",
        "pressure_kind",
        "pressure_psia",
        "reference_depth_ft",
    }
    if "field" not in frame:
        required.add("formation_name")
    _validate_columns(frame, required, input_config["name"])
    normalized = frame.copy()
    if "field" not in normalized:
        normalized = normalized.rename(columns=OKLAHOMA_COLUMN_MAP)
    normalized["well_key"] = normalized["well_key"].astype("string")
    if "is_earliest_observation" in normalized:
        earliest = _truthy(normalized["is_earliest_observation"])
        normalized["screen_observation_priority"] = (~earliest).astype(int)
    return normalized


def _validate_required_columns(frame: pd.DataFrame, source_name: str) -> None:
    _validate_columns(frame, set(REQUIRED_SCREEN_COLUMNS), source_name)


def _validate_columns(
    frame: pd.DataFrame, required: set[str], source_name: str
) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"{source_name} missing required columns: {missing_text}")


def _read_source_warnings(quality_path: str | None) -> list[str]:
    if not quality_path:
        return []
    path = Path(quality_path)
    if not path.exists():
        return [f"missing_quality_path:{path}"]
    quality = json.loads(path.read_text(encoding="utf-8"))
    return [str(item) for item in quality.get("source_warnings", [])]


def _truthy(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.fillna("").astype(str).str.lower().isin({"1", "true", "yes"})
