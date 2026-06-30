"""Local raw snapshot readers for Texas RRC lifecycle normalization."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from importlib.resources import files
from io import StringIO
from pathlib import Path
from typing import Sequence

import pandas as pd
import yaml


@dataclass(frozen=True)
class LifecycleInputFrames:
    """Raw lifecycle source frames loaded from local Texas RRC snapshots."""

    wellbores: pd.DataFrame
    permits: pd.DataFrame
    completions: pd.DataFrame
    source_gaps: Sequence[str]


SOURCE_DIRS = {
    "wellbore_query": Path("raw/wellbore/query"),
    "drilling_permits": Path("raw/permits/drilling"),
    "completion_data": Path("raw/completions"),
}


def load_lifecycle_inputs(raw_root: Path) -> LifecycleInputFrames:
    """Load local raw snapshots needed for the lifecycle spine."""
    root = _local_root(raw_root)
    wellbores, wellbore_gap = _load_source(root, "wellbore_query")
    permits, permit_gap = _load_source(root, "drilling_permits")
    completions, completion_gap = _load_source(root, "completion_data")
    gaps = tuple(
        source
        for source in (wellbore_gap, permit_gap, completion_gap)
        if source is not None
    )
    return LifecycleInputFrames(wellbores, permits, completions, gaps)


def _local_root(raw_root: Path) -> Path:
    value = str(raw_root)
    if "://" in value:
        raise ValueError("Lifecycle inputs must be local filesystem paths")
    return Path(raw_root)


def _load_source(root: Path, source_id: str) -> tuple[pd.DataFrame, str | None]:
    source_dir = root / SOURCE_DIRS[source_id]
    if not source_dir.exists():
        return pd.DataFrame(), source_id

    frames = [_read_table(path) for path in sorted(source_dir.rglob("*")) if path.is_file()]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(), source_id

    combined = pd.concat(frames, ignore_index=True)
    return _normalize_columns(combined, source_id), None


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        return _read_zip_tables(path)
    if path.suffix.lower() not in {".csv", ".txt", ".dat"}:
        return pd.DataFrame()
    return _read_table_text(path.read_text(encoding="utf-8", errors="replace"))


def _read_zip_tables(path: Path) -> pd.DataFrame:
    frames = []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if Path(name).suffix.lower() not in {".csv", ".txt", ".dat"}:
                continue
            text = archive.read(name).decode("utf-8", errors="replace")
            frame = _read_table_text(text)
            if not frame.empty:
                frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _read_table_text(text: str) -> pd.DataFrame:
    if not text.strip():
        return pd.DataFrame()
    first_line = text.splitlines()[0]
    separator = "|" if "|" in first_line else None
    return pd.read_csv(
        StringIO(text),
        sep=separator,
        engine="python",
        dtype=str,
        keep_default_na=False,
    )


def _normalize_columns(frame: pd.DataFrame, source_id: str) -> pd.DataFrame:
    aliases = _alias_lookup()[source_id]
    rename = {}
    for column in frame.columns:
        column_key = _column_key(column)
        rename[column] = aliases.get(column_key, column.lower().replace(" ", "_"))
    return frame.rename(columns=rename)


def _alias_lookup() -> dict[str, dict[str, str]]:
    data_path = files("worldenergydata.texas_rrc.data").joinpath(
        "lifecycle_column_aliases.yml"
    )
    config = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    lookup = {}
    for source_id, columns in config["sources"].items():
        lookup[source_id] = {}
        for canonical, aliases in columns.items():
            for alias in aliases:
                lookup[source_id][_column_key(alias)] = canonical
    return lookup


def _column_key(column: str) -> str:
    return column.strip().upper().replace(" ", "_")
