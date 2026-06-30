"""Load local official Texas RRC PDQ production snapshots."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from io import StringIO, TextIOWrapper
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from worldenergydata.texas_rrc.production_atlas.atlas import (
    is_usable_production_frame,
    normalize_production_frame,
)

PRODUCTION_PDQ_RELATIVE_DIR = Path("raw") / "production" / "pdq"
SUPPORTED_MEMBER_SUFFIXES = (".csv", ".txt", ".dsv")
PREFERRED_PRODUCTION_MEMBERS = ("OG_LEASE_CYCLE_DATA_TABLE",)
PRODUCTION_USE_COLUMNS = {
    "CYCLE_MONTH",
    "CYCLE_YEAR",
    "CYCLE_YEAR_MONTH",
    "DISTRICT_NO",
    "DIST_OIL_PROD_VOL",
    "DIST_GAS_PROD_VOL",
    "DIST_COND_PROD_VOL",
    "DIST_CSGD_PROD_VOL",
    "FIELD_NO",
    "FIELD_NAME",
    "FIELD_OIL_PROD_VOL",
    "FIELD_GAS_PROD_VOL",
    "FIELD_COND_PROD_VOL",
    "FIELD_CSGD_PROD_VOL",
    "LEASE_NO",
    "LEASE_NAME",
    "LEASE_OIL_PROD_VOL",
    "LEASE_GAS_PROD_VOL",
    "LEASE_COND_PROD_VOL",
    "LEASE_CSGD_PROD_VOL",
    "OPERATOR_NO",
    "OPERATOR_NAME",
    "OPER_OIL_PROD_VOL",
    "OPER_GAS_PROD_VOL",
    "OPER_COND_PROD_VOL",
    "OPER_CSGD_PROD_VOL",
}


@dataclass(frozen=True)
class ProductionInputFrame:
    """Normalized production rows and source provenance for one atlas run."""

    production: pd.DataFrame
    input_paths: tuple[Path, ...]
    source_gaps: Sequence[str]


@dataclass(frozen=True)
class ProductionInputChunks:
    """Chunked raw production rows and source provenance for one atlas run."""

    chunks: Iterable[pd.DataFrame]
    input_paths: tuple[Path, ...]
    source_gaps: Sequence[str]


def load_production_inputs(raw_root: Path | str) -> ProductionInputFrame:
    """Load local official PDQ snapshots from a Texas RRC raw root."""
    root = _local_path(raw_root)
    zip_paths = _pdq_zip_paths(root)
    if not zip_paths:
        return ProductionInputFrame(
            production=normalize_production_frame(pd.DataFrame()),
            input_paths=(),
            source_gaps=("production_pdq",),
        )
    frames = [_read_pdq_zip(path) for path in zip_paths]
    raw = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if raw.empty or not is_usable_production_frame(raw):
        return ProductionInputFrame(
            production=normalize_production_frame(pd.DataFrame()),
            input_paths=tuple(zip_paths),
            source_gaps=("production_pdq",),
        )
    return ProductionInputFrame(
        production=normalize_production_frame(raw),
        input_paths=tuple(zip_paths),
        source_gaps=(),
    )


def iter_production_input_chunks(
    raw_root: Path | str,
    chunksize: int = 250_000,
) -> ProductionInputChunks:
    """Yield official PDQ production snapshots without loading a full member."""
    if chunksize < 1:
        raise ValueError("chunksize must be greater than zero")
    root = _local_path(raw_root)
    zip_paths = tuple(_pdq_zip_paths(root))
    if not zip_paths:
        return ProductionInputChunks(
            chunks=(),
            input_paths=(),
            source_gaps=("production_pdq",),
        )
    return ProductionInputChunks(
        chunks=_iter_pdq_chunks(zip_paths, chunksize),
        input_paths=zip_paths,
        source_gaps=(),
    )


def _local_path(value: Path | str) -> Path:
    text = str(value)
    if "://" in text:
        raise ValueError("production raw_root must be a local filesystem path")
    return Path(value)


def _pdq_zip_paths(root: Path) -> list[Path]:
    if root.is_file() and root.suffix.lower() == ".zip":
        return [root]
    if root.is_dir():
        direct_zips = sorted(root.glob("*.zip"))
        if direct_zips:
            return direct_zips
    source_dir = root / PRODUCTION_PDQ_RELATIVE_DIR
    return sorted(source_dir.glob("*.zip")) if source_dir.exists() else []


def _read_pdq_zip(path: Path) -> pd.DataFrame:
    frames = []
    with zipfile.ZipFile(path) as archive:
        for name in _production_member_names(archive):
            if not name.lower().endswith(SUPPORTED_MEMBER_SUFFIXES):
                continue
            frame = _read_pdq_member(archive, name)
            if not frame.empty:
                frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _iter_pdq_chunks(
    zip_paths: Sequence[Path],
    chunksize: int,
) -> Iterable[pd.DataFrame]:
    for path in zip_paths:
        with zipfile.ZipFile(path) as archive:
            for name in _production_member_names(archive):
                if not name.lower().endswith(SUPPORTED_MEMBER_SUFFIXES):
                    continue
                for frame in _read_pdq_member_chunks(archive, name, chunksize):
                    if not frame.empty and is_usable_production_frame(frame):
                        yield frame


def _production_member_names(archive: zipfile.ZipFile) -> list[str]:
    names = sorted(archive.namelist())
    preferred = [
        name
        for name in names
        if Path(name).stem.upper() in PREFERRED_PRODUCTION_MEMBERS
    ]
    if preferred:
        return preferred
    return names


def _read_pdq_text(text: str) -> pd.DataFrame:
    if not text.strip():
        return pd.DataFrame()
    first_line = text.splitlines()[0]
    separator = _separator(first_line)
    return pd.read_csv(
        StringIO(text),
        sep=separator,
        **_csv_reader_kwargs(first_line, separator),
    )


def _read_pdq_member(archive: zipfile.ZipFile, name: str) -> pd.DataFrame:
    first_line = _member_first_line(archive, name)
    if not first_line.strip():
        return pd.DataFrame()
    separator = _separator(first_line)
    with archive.open(name) as raw_file:
        text_file = TextIOWrapper(
            raw_file,
            encoding="utf-8",
            errors="replace",
            newline="",
        )
        return pd.read_csv(
            text_file,
            sep=separator,
            **_csv_reader_kwargs(first_line, separator),
        )


def _read_pdq_member_chunks(
    archive: zipfile.ZipFile,
    name: str,
    chunksize: int,
) -> Iterable[pd.DataFrame]:
    first_line = _member_first_line(archive, name)
    if not first_line.strip():
        return
    separator = _separator(first_line)
    with archive.open(name) as raw_file:
        text_file = TextIOWrapper(
            raw_file,
            encoding="utf-8",
            errors="replace",
            newline="",
        )
        reader = pd.read_csv(
            text_file,
            sep=separator,
            chunksize=chunksize,
            **_csv_reader_kwargs(first_line, separator),
        )
        yield from reader


def _member_first_line(archive: zipfile.ZipFile, name: str) -> str:
    with archive.open(name) as raw_file:
        text_file = TextIOWrapper(raw_file, encoding="utf-8", errors="replace")
        return text_file.readline()


def _csv_reader_kwargs(first_line: str, separator: str | None) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "dtype": str,
        "keep_default_na": False,
    }
    if separator is None:
        kwargs["engine"] = "python"
    usecols = _preferred_usecols(first_line, separator)
    if usecols:
        kwargs["usecols"] = usecols
    return kwargs


def _preferred_usecols(first_line: str, separator: str | None) -> list[str]:
    if separator is None:
        return []
    columns = [column.strip() for column in first_line.rstrip("\r\n").split(separator)]
    return [column for column in columns if column.upper() in PRODUCTION_USE_COLUMNS]


def _separator(first_line: str) -> str | None:
    if "}" in first_line:
        return "}"
    if "|" in first_line:
        return "|"
    return None
