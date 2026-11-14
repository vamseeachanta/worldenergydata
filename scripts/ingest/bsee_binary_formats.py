"""Streaming readers for trusted local BSEE tables; no archive extraction."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from itertools import islice
from pathlib import Path, PurePosixPath

import pandas as pd

# Published dspts layout already used by bsee.data.sources.zip.well_data.
SURVEY_COLUMNS = [
    "API_WELL_NUMBER",
    "INCL_ANG_DEG_VAL",
    "INCL_ANG_MIN_VAL",
    "SURVEY_POINT_MD",
    "WELL_N_S_CODE",
    "DIR_DEG_VAL",
    "DIR_MINS_VAL",
    "WELL_E_W_CODE",
    "SURVEY_POINT_TVD",
    "DELTA_X",
    "DELTA_Y",
    "SURF_LONGITUDE",
    "SURF_LATITUDE",
]
# The remaining directdelimit field meanings/units have not been verified.
DIRECT_COLUMNS = ["API_WELL_NUMBER"] + [f"SOURCE_COLUMN_{n:02d}" for n in range(2, 12)]
SUFFIXES = {".zip", ".bin", ".pkl", ".pickle", ".txt", ".csv", ".tsv"}


def digest(path: Path) -> str:
    """Hash source/output bytes with bounded memory."""
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def detect_format(path: Path) -> str:
    """Identify content from the first 512 bytes, independent of suffix."""
    with path.open("rb") as handle:
        head = handle.read(512)
    if head.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise ValueError("LFS pointer requires the actual payload")
    if not head:
        raise ValueError("Empty input")
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    if head[:1] == b"\x80" and head[1:2] in (b"\x02", b"\x03", b"\x04", b"\x05"):
        return "pickle"
    if b"\x00" in head:
        raise ValueError("Unsupported binary format")
    return "delimited"


def table_name(name: str) -> str:
    """Reject traversal and names that cannot be used as output identifiers."""
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError("Unsafe archive member")
    stem = path.stem
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_-]*", stem):
        raise ValueError("Invalid table identifier")
    return stem.lower()


def text_chunks(handle, name: str, chunk_size: int, encoding: str):
    """Preserve every field as text, including leading zeros and literal NA."""
    sample = handle.read(8192)
    handle.seek(0)
    codec = "utf-8-sig" if sample.startswith(b"\xef\xbb\xbf") else encoding
    text = sample.decode(codec)
    if text.startswith("version https://git-lfs.github.com/spec/v1"):
        raise ValueError("LFS pointer requires the actual payload")
    if not text:
        raise ValueError("Empty input")
    first_line = text.splitlines()[0]
    try:
        dialect = csv.Sniffer().sniff(first_line, delimiters=",\t|")
    except csv.Error as exc:
        if any(sep in first_line for sep in (",", "\t", "|")):
            raise ValueError("Unrecognized delimited table") from exc
        dialect = csv.excel  # A one-column table has no delimiter to sniff.
    with io.TextIOWrapper(handle, encoding=codec, newline="") as wrapper:
        # Header-only sniffing identifies the separator, but cannot infer
        # escaped quotes in later records. BSEE uses standard doubled quotes.
        reader = csv.reader(wrapper, delimiter=dialect.delimiter, strict=True)
        first = next(reader)
        known = {"dsptsdelimit": SURVEY_COLUMNS, "directdelimit": DIRECT_COLUMNS}.get(
            name
        )
        headerless = known is not None and first[0].strip() != "API_WELL_NUMBER"
        columns = list(known) if headerless else [v.strip() for v in first]
        if (
            not columns
            or any(not c for c in columns)
            or len(set(columns)) != len(columns)
        ):
            raise ValueError("Invalid or duplicate column names")
        pending = [first] if headerless else []
        emitted = False
        while True:
            rows = pending + list(islice(reader, chunk_size - len(pending)))
            pending = []
            if not rows:
                if not emitted:
                    yield pd.DataFrame(columns=columns, dtype=str)
                break
            if any(len(row) != len(columns) for row in rows):
                raise ValueError("Row width differs from table schema")
            emitted = True
            yield pd.DataFrame(rows, columns=columns, dtype=str)


def tables(path: Path, chunk_size: int, encoding: str, trust_pickles: bool):
    """Yield (table name, ZIP member, chunks) while each source stays open."""
    kind = detect_format(path)
    if kind == "zip":
        with zipfile.ZipFile(path) as archive:
            members = [m for m in archive.infolist() if not m.is_dir()]
            if not members:
                raise ValueError("Archive has no tables")
            for member in sorted(members, key=lambda m: m.filename):
                name = table_name(member.filename)
                if PurePosixPath(member.filename).suffix.lower() not in {
                    ".txt",
                    ".csv",
                    ".tsv",
                }:
                    raise ValueError("Unsupported archive member format")
                with archive.open(member) as handle:
                    yield name, member.filename, text_chunks(
                        handle, name, chunk_size, encoding
                    )
    elif kind == "pickle":
        if not trust_pickles:
            raise ValueError(
                "Local pickles require --trust-pickles; never use untrusted inputs"
            )
        # Same pandas DataFrame serialization as the existing BSEE loaders.
        frame = pd.read_pickle(path)  # nosec B301: explicitly trusted local input
        if not isinstance(frame, pd.DataFrame):
            raise ValueError("Pickle is not a DataFrame")
        if (
            not len(frame.columns)
            or not frame.columns.is_unique
            or not all(isinstance(c, str) and c for c in frame.columns)
        ):
            raise ValueError("Invalid DataFrame columns")
        chunks = (
            frame.iloc[i : i + chunk_size].astype("string").fillna("")
            for i in range(0, max(len(frame), 1), chunk_size)
        )
        yield table_name(path.name), None, chunks
    else:
        with path.open("rb") as handle:
            name = table_name(path.name)
            yield name, None, text_chunks(handle, name, chunk_size, encoding)


class CurrentIndex:
    """Exact full-row comparison; different schemas never imply duplicates."""

    def __init__(self, root: Path, encoding: str):
        if not root.is_dir():
            raise ValueError("Current CSV tier is unavailable")
        self.rows = {}
        self.files = {}
        self.sources = {}
        for path in sorted(root.rglob("*.csv")):
            relative = path.relative_to(root).as_posix()
            before = digest(path)
            for _, _, chunks in tables(path, 10000, encoding, False):
                for chunk in chunks:
                    columns = tuple(sorted(chunk.columns))
                    self.rows.setdefault(columns, set()).update(
                        chunk.loc[:, columns].itertuples(index=False, name=None)
                    )
                    self.files.setdefault(columns, set()).add(relative)
            if digest(path) != before:
                raise ValueError("Current source changed while being read")
            self.sources[relative] = {"path": relative, "sha256": before}

    def filter(self, frame: pd.DataFrame):
        columns = tuple(sorted(frame.columns))
        reference = self.rows.get(columns, set())
        keep = [
            row not in reference
            for row in frame.loc[:, columns].itertuples(index=False, name=None)
        ]
        return frame.loc[keep], sorted(self.files.get(columns, set()))
