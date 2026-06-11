"""BSEE download payload classification and archive extraction.

Hardened helpers for the BSEE refresh path (issue #267, epic #423).

Knowledge re-encoded from closed threads #9 / #11 / #12:

* ``https://www.data.bsee.gov/Main/RawData.aspx`` is the authoritative
  index of all bulk "Raw Data" zip downloads (issue #9, #12).  When a
  dataset URL goes stale, BSEE serves an HTTP 200 **HTML** page (~28 KB)
  instead of a 404 -- payloads must therefore be classified by content,
  never trusted by status code alone (issue #267 runtime findings,
  live-verified 2026-06-10).
* Healthy archives are served with ``Content-Type:
  application/x-zip-compressed`` and contain a leading directory entry
  plus one or more ``mv_*.txt`` members.  Members are comma-delimited,
  double-quoted CSV with CRLF line endings despite the ``.txt``
  extension (live-verified against ``PlatStrucRawData.zip`` and
  ``PermStrucRawData.zip``, 2026-06-10).  Legacy fixtures use ``.csv``
  members; both extensions are accepted.
* Plain request/response downloading is the preferred scraping method
  -- request/POST first, Selenium only as a last resort (issue #11
  method hierarchy).

Failure classification follows issue #460: deterministic failures
(stale-URL HTML payloads, empty bodies, archives without data members)
cannot succeed on retry within the same process, while transient
failures (timeouts, connection resets, 5xx) may.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatch
from typing import Optional

import pandas as pd

#: Zip local-file-header magic. Also matches empty (``PK\x05\x06``) and
#: spanned (``PK\x07\x08``) archives via the shared ``PK`` prefix check.
_ZIP_MAGIC_PREFIXES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")

#: Leading byte sequences that identify an HTML/error payload.  BSEE
#: stale-URL responses start with a doctype or ``<html`` tag.
_HTML_MARKERS = (b"<!doctype", b"<html", b"<head", b"<?xml")

#: Member extensions that may hold tabular data.  BSEE raw-data zips
#: ship ``.txt`` (quoted CSV); legacy fixtures and other agencies ship
#: ``.csv``.
DATA_MEMBER_EXTENSIONS = (".txt", ".csv")


class PayloadKind(Enum):
    """Coarse classification of a downloaded payload body."""

    ZIP = "zip"
    HTML = "html"
    EMPTY = "empty"
    UNKNOWN = "unknown"


class FailureClass(Enum):
    """Retry semantics of a dataset failure (issue #460).

    DETERMINISTIC failures will fail identically on immediate retry
    (stale URL serving HTML, no data members in archive). TRANSIENT
    failures (network errors, timeouts) may succeed on retry.
    """

    DETERMINISTIC = "deterministic"
    TRANSIENT = "transient"


@dataclass(frozen=True)
class DatasetFailure:
    """A classified per-dataset refresh failure."""

    dataset: str
    reason: str
    failure_class: FailureClass
    detail: str = ""

    def summary(self) -> str:
        """One-line summary for job error messages and logs."""
        return f"{self.dataset}: {self.reason} ({self.failure_class.value})"


def classify_payload(data: Optional[bytes]) -> PayloadKind:
    """Classify a downloaded body before any zip parsing (issue #267).

    BSEE answers stale dataset URLs with HTTP 200 + an HTML page, which
    previously surfaced as ``zipfile.BadZipFile: File is not a zip
    file``.  Classifying the payload first lets callers fail with a
    deterministic, actionable reason instead.
    """
    if not data:
        return PayloadKind.EMPTY
    head = data[:4]
    if any(head.startswith(p) for p in _ZIP_MAGIC_PREFIXES):
        return PayloadKind.ZIP
    sniff = data[:256].lstrip().lower()
    if any(sniff.startswith(m) for m in _HTML_MARKERS):
        return PayloadKind.HTML
    return PayloadKind.UNKNOWN


def list_data_members(zf: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """Return non-directory members that can hold tabular data.

    BSEE archives lead with a zero-byte directory entry (e.g.
    ``PlatStrucRawData/``) -- naive ``namelist()[0]`` reads fail on it.
    """
    members = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename.lower()
        if name.endswith(DATA_MEMBER_EXTENSIONS):
            members.append(info)
    return members


def select_primary_member(
    members: list[zipfile.ZipInfo],
    patterns: Optional[list[str]] = None,
) -> Optional[zipfile.ZipInfo]:
    """Pick the member holding the dataset's primary table.

    Tries each glob pattern in priority order against the member
    basename (e.g. ``mv_platstruc_structures.txt``); falls back to the
    largest data member, which for BSEE archives is the main entity
    table in all observed datasets.
    """
    if not members:
        return None
    for pattern in patterns or []:
        for info in members:
            basename = info.filename.rsplit("/", 1)[-1].lower()
            if fnmatch(basename, pattern.lower()):
                return info
    return max(members, key=lambda info: info.file_size)


def read_member_table(zf: zipfile.ZipFile, member: zipfile.ZipInfo) -> pd.DataFrame:
    """Read one archive member as a DataFrame.

    Members are quoted CSV with CRLF endings regardless of extension.
    BSEE exports occasionally contain non-UTF-8 bytes (operator names),
    so decoding falls back to latin-1.
    """
    raw = zf.read(member)
    try:
        return pd.read_csv(io.BytesIO(raw), low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(io.BytesIO(raw), low_memory=False, encoding="latin-1")


def extract_primary_table(
    zip_bytes: bytes,
    member_patterns: Optional[list[str]] = None,
) -> tuple[pd.DataFrame, str]:
    """Extract the primary data table from a verified zip payload.

    Args:
        zip_bytes: Payload already classified as ``PayloadKind.ZIP``.
        member_patterns: Optional glob priority list for the primary
            member (e.g. ``["mv_platstruc_structures.txt"]``).

    Returns:
        ``(dataframe, member_name)``.

    Raises:
        zipfile.BadZipFile: If the bytes are not a readable archive.
        LookupError: If the archive holds no data members
            (deterministic failure -- the upstream contract changed).
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        members = list_data_members(zf)
        primary = select_primary_member(members, member_patterns)
        if primary is None:
            raise LookupError(
                "archive contains no .txt/.csv data members: "
                f"{[i.filename for i in zf.infolist()][:10]}"
            )
        return read_member_table(zf, primary), primary.filename
