"""Local raw snapshot readers for Texas RRC lifecycle normalization."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from datetime import date
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

    frames = [
        _read_table(path, source_id)
        for path in sorted(source_dir.rglob("*"))
        if path.is_file()
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(), source_id

    combined = pd.concat(frames, ignore_index=True)
    return _normalize_columns(combined, source_id), None


def _read_table(path: Path, source_id: str) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        return _read_zip_tables(path, source_id)
    if path.suffix.lower() not in {".csv", ".txt", ".dat"}:
        return pd.DataFrame()
    text = path.read_text(encoding="utf-8", errors="replace")
    if source_id == "drilling_permits" and path.name.lower() == "daf420.dat":
        frame = _read_daf420_text(text)
        if not frame.empty:
            return frame
    return _read_table_text(text)


def _read_zip_tables(path: Path, source_id: str) -> pd.DataFrame:
    frames = []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if Path(name).suffix.lower() not in {".csv", ".txt", ".dat"}:
                continue
            text = archive.read(name).decode("utf-8", errors="replace")
            if (
                source_id == "drilling_permits"
                and Path(name).name.lower() == "daf420.dat"
            ):
                frame = _read_daf420_text(text)
                if not frame.empty:
                    frames.append(frame)
                    continue
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


def _read_daf420_text(text: str) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r\n")
        segment = _rrc_segment(line)
        if segment is None:
            continue
        segment_type, segment_start = segment
        if segment_type == "02":
            row = _parse_daf420_master(line, segment_start)
            if row:
                rows.append(row)
        elif segment_type == "14" and rows:
            rows[-1].update(_parse_daf420_surface_location(line, segment_start))
    return pd.DataFrame(rows)


def _rrc_segment(line: str) -> tuple[str, int] | None:
    for start in (0, 2):
        segment_type = line[start : start + 2]
        if segment_type in {"02", "14"}:
            return segment_type, start + 1
    return None


def _parse_daf420_master(line: str, segment_start: int) -> dict[str, str]:
    offset = segment_start - 3
    api_number = _fixed_value(line, 505 + offset, 8)
    if len(api_number) != 8 or not api_number.isdigit():
        return {}

    row = {
        "api_number": api_number,
        "permit_number": _fixed_value(line, 5 + offset, 7),
        "permit_type": _fixed_value(line, 68 + offset, 2),
        "district": _fixed_value(line, 49 + offset, 2),
        "lease_name": _fixed_value(line, 17 + offset, 32),
        "operator_number": _fixed_value(line, 62 + offset, 6),
        "permit_issued_date": _fixed_date(line, 132 + offset),
        "permit_amended_date": _fixed_date(line, 140 + offset),
        "permit_extended_date": _fixed_date(line, 148 + offset),
        "spud_date": _fixed_date(line, 156 + offset),
        "total_depth": _fixed_value(line, 57 + offset, 5),
    }
    return {key: value for key, value in row.items() if value}


def _parse_daf420_surface_location(line: str, segment_start: int) -> dict[str, str]:
    offset = segment_start - 3
    longitude = _fixed_coordinate(line, 5 + offset, west_longitude=True)
    latitude = _fixed_coordinate(line, 17 + offset, west_longitude=False)
    result = {}
    if latitude:
        result["latitude"] = latitude
    if longitude:
        result["longitude"] = longitude
    return result


def _fixed_value(line: str, start: int, width: int) -> str:
    if start < 1:
        return ""
    return line[start - 1 : start - 1 + width].strip()


def _fixed_date(line: str, start: int) -> str:
    value = _fixed_value(line, start, 8)
    if len(value) != 8 or not value.isdigit() or value == "00000000":
        return ""
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:8])).isoformat()
    except ValueError:
        return ""


def _fixed_coordinate(line: str, start: int, west_longitude: bool) -> str:
    value = _fixed_value(line, start, 12)
    if len(value) != 12 or not value.isdigit() or value == "000000000000":
        return ""
    coordinate = int(value[:5]) + int(value[5:]) / 10_000_000
    if west_longitude:
        coordinate = -coordinate
    return f"{coordinate:g}"


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
