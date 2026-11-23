"""Load local official Texas RRC inputs for pressure observations."""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd

from worldenergydata.texas_rrc.lifecycle.keys import derive_api10, normalize_api14
from worldenergydata.texas_rrc.pressure_observations.packets import (
    read_packet_pressure_candidates,
)

COMPLETION_DIR = Path("raw") / "completions"
WELLBORE_DIR = Path("raw") / "wellbore" / "query"
MANIFEST_DIR = Path("manifests")
TABLE_SUFFIXES = {".csv", ".dat", ".txt"}


@dataclass(frozen=True)
class PressureObservationInputs:
    """Local pressure-observation source frames and source evidence."""

    candidates: pd.DataFrame
    wellbore: pd.DataFrame
    input_paths: tuple[str, ...]
    input_artifacts: tuple[dict[str, object], ...]
    source_gaps: tuple[str, ...]
    source_warnings: tuple[str, ...]
    parser_quality: dict[str, int]


def load_pressure_observation_inputs(raw_root: Path | str) -> PressureObservationInputs:
    """Load pressure candidates and wellbore reference from local RRC snapshots."""
    root = _local_root(raw_root)
    candidate_frames, completion_paths, parser_quality = _completion_candidates(root)
    wellbore, wellbore_paths = _wellbore_reference(root)

    source_gaps = []
    if not completion_paths:
        source_gaps.append("completion_data")
    if not wellbore_paths:
        source_gaps.append("wellbore_query")

    candidates = _candidate_frame(candidate_frames)
    input_paths = tuple(str(path) for path in (*completion_paths, *wellbore_paths))
    input_artifacts = tuple(
        _artifact_payload(path) for path in (*completion_paths, *wellbore_paths)
    )

    return PressureObservationInputs(
        candidates=candidates,
        wellbore=wellbore,
        input_paths=input_paths,
        input_artifacts=input_artifacts,
        source_gaps=tuple(source_gaps),
        source_warnings=_raw_manifest_warnings(root),
        parser_quality=parser_quality,
    )


def _candidate_frame(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for frame in frames:
        rows.extend(frame.to_dict("records"))
    return pd.DataFrame.from_records(rows, columns=frames[0].columns)


def _local_root(raw_root: Path | str) -> Path:
    value = str(raw_root)
    if "://" in value:
        raise ValueError("Pressure-observation inputs must be local filesystem paths")
    return Path(raw_root)


def _completion_candidates(
    root: Path,
) -> tuple[list[pd.DataFrame], list[Path], dict[str, int]]:
    source_dir = root / COMPLETION_DIR
    quality = {
        "candidate_count": 0,
        "malformed_row_count": 0,
        "unlinked_row_count": 0,
    }
    if not source_dir.exists():
        return [], [], quality

    frames = []
    paths = [path for path in sorted(source_dir.glob("*.zip")) if path.is_file()]
    for path in paths:
        with zipfile.ZipFile(path) as archive:
            for member in sorted(archive.namelist()):
                if Path(member).suffix.lower() not in TABLE_SUFFIXES:
                    continue
                text = archive.read(member).decode("utf-8", errors="replace")
                parsed = read_packet_pressure_candidates(
                    text,
                    source_file=f"{path}!{member}",
                )
                quality["candidate_count"] += len(parsed.candidates)
                quality["malformed_row_count"] += parsed.malformed_row_count
                quality["unlinked_row_count"] += parsed.unlinked_row_count
                if not parsed.candidates.empty:
                    frames.append(parsed.candidates)
    return frames, paths, quality


def _wellbore_reference(root: Path) -> tuple[pd.DataFrame, list[Path]]:
    source_dir = root / WELLBORE_DIR
    if not source_dir.exists():
        return pd.DataFrame(), []

    frames = []
    paths = [
        path
        for path in sorted(source_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in TABLE_SUFFIXES.union({".zip"})
    ]
    for path in paths:
        frame = _read_wellbore_path(path)
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame(), paths
    combined = pd.concat(frames, ignore_index=True)
    return _normalize_wellbore_reference(combined), paths


def _read_wellbore_path(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        frames = []
        with zipfile.ZipFile(path) as archive:
            for member in sorted(archive.namelist()):
                if Path(member).suffix.lower() not in TABLE_SUFFIXES:
                    continue
                text = archive.read(member).decode("utf-8", errors="replace")
                frame = _read_wellbore_text(text)
                if not frame.empty:
                    frames.append(frame)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    first_line = _first_line(path)
    if _looks_like_header(first_line):
        return pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
            low_memory=False,
        )
    return pd.read_csv(
        path,
        header=None,
        names=["api_number", "total_depth"],
        usecols=[2, 15],
        dtype=str,
        keep_default_na=False,
        on_bad_lines="skip",
    )


def _read_wellbore_text(text: str) -> pd.DataFrame:
    if not text.strip():
        return pd.DataFrame()
    first_line = text.splitlines()[0]
    if _looks_like_header(first_line):
        return pd.read_csv(
            StringIO(text),
            dtype=str,
            keep_default_na=False,
            low_memory=False,
        )
    return pd.read_csv(
        StringIO(text),
        header=None,
        names=["api_number", "total_depth"],
        usecols=[2, 15],
        engine="python",
        dtype=str,
        keep_default_na=False,
        on_bad_lines="skip",
    )


def _looks_like_header(first_line: str) -> bool:
    keys = {_column_key(part) for part in first_line.split(",")}
    return bool(keys.intersection({"API_NO", "API_NUMBER", "TOTAL_DEPTH"}))


def _first_line(path: Path) -> str:
    with path.open(encoding="utf-8", errors="replace") as handle:
        return handle.readline()


def _normalize_wellbore_reference(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.rename(
        columns={column: _wellbore_alias(column) for column in frame}
    )
    if "api_number" not in renamed or "total_depth" not in renamed:
        return pd.DataFrame()
    result = renamed.loc[:, ["api_number", "total_depth"]].copy()
    result["api14"] = result["api_number"].map(normalize_api14)
    result = result[result["api14"].notna()].copy()
    result["api10"] = result["api14"].map(derive_api10)
    result["total_depth"] = result["total_depth"].astype(str).str.strip()
    return result.loc[:, ["api14", "api10", "total_depth"]].reset_index(drop=True)


def _wellbore_alias(column: str) -> str:
    aliases = {
        "API_NO": "api_number",
        "API_NUMBER": "api_number",
        "API": "api_number",
        "TOTAL_DEPTH": "total_depth",
        "TOTAL_DEPTH_FT": "total_depth",
    }
    return aliases.get(_column_key(column), str(column).lower())


def _raw_manifest_warnings(root: Path) -> tuple[str, ...]:
    warnings = []
    manifest_dir = root / MANIFEST_DIR
    if not manifest_dir.exists():
        return ()
    for source_id in ("completion_data", "wellbore_query"):
        manifest = _latest_manifest(manifest_dir, source_id)
        if not manifest:
            continue
        status = str(manifest.get("status", ""))
        if status and status != "downloaded":
            retrieved_at = str(manifest.get("retrieved_at", ""))
            warnings.append(f"raw_manifest_warning:{source_id}:{status}:{retrieved_at}")
    return tuple(warnings)


def _latest_manifest(manifest_dir: Path, source_id: str) -> dict[str, Any]:
    paths = sorted(manifest_dir.glob(f"{source_id}-*.json"))
    for path in reversed(paths):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _artifact_payload(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "byte_size": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _column_key(column: object) -> str:
    return str(column).strip().upper().replace(" ", "_")


__all__ = [
    "PressureObservationInputs",
    "load_pressure_observation_inputs",
]
