"""Collector for off-repo ACMA MSIV markdown vessel particulars.

Reads Multi-Service Installation Vessel (MSIV) particulars from a local
directory resolved via the ``ACMA_MSIV_DIR`` environment variable.

Confidentiality: only *vessel particulars* are extracted (name, dimensions,
crane SWL, DP class, accommodation, pipelay capability). Cost / day-rate /
mobilization / scoring / recommendation tables in the source are **never**
read or mapped. The raw client folder is never copied into the repository.

Source file:
    - ``vessel-specifications-matrix.md`` (markdown tables)
"""

from __future__ import annotations

import logging
import math
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from worldenergydata.vessel_fleet.parsers.numeric import (
    parse_int_from_label,
    parse_numeric,
)
from worldenergydata.vessel_fleet.schemas.construction_vessel import (
    ConstructionVesselSchema,
)

logger = logging.getLogger(__name__)

#: Environment variable holding the off-repo MSIV source directory.
ACMA_ENV_VAR = "ACMA_MSIV_DIR"

#: Provenance tag written to ``DATA_SOURCE`` for MSIV records.
DATA_SOURCE_MSIV = "acma_msiv_md"

_MATRIX_FILE = "vessel-specifications-matrix.md"

_VESSEL_CATEGORY = "construction"

# Header (lowercased) of the only table we extract particulars from. The
# cost/scoring/recommendation/mobilization tables are intentionally excluded.
_SPEC_TABLE_HEADERS = (
    "vessel name",
    "type",
    "loa",
    "beam",
    "draft",
    "main crane",
)

# Column units are the source-format contract, not inferred conversions.
_REQUIRED_COLUMNS = {
    "vessel name",
    "type",
    "loa (m)",
    "beam (m)",
    "draft (m)",
    "main crane (mt)",
}
_MISSING = {"", "-", "--", "n/a", "na", "unknown", "tbd"}


def _normalize_header(cell: str) -> str:
    return " ".join(cell.lower().replace("²", "2").split())


def _find_spec_table_with_header(
    lines: list[str],
) -> tuple[list[str], list[list[str]]]:
    """Find a unit-labelled particulars table with an actual separator.

    Match complete columns rather than substrings in unrelated headings.
    Duplicate columns are ambiguous and are not accepted.
    """
    for idx, line in enumerate(lines):
        if "|" not in line:
            continue
        header = [_normalize_header(cell) for cell in _split_md_row(line)]
        if not _REQUIRED_COLUMNS.issubset(header) or len(header) != len(set(header)):
            continue
        following = lines[idx + 1 :]
        if not following:
            continue
        separator = _split_md_row(following[0])
        if len(separator) != len(header) or not _is_separator_row(separator):
            continue
        body: list[list[str]] = []
        for body_line in following[1:]:
            if "|" not in body_line:
                break
            cells = _split_md_row(body_line)
            if _is_separator_row(cells) or "vessel name" in {
                _normalize_header(cell) for cell in cells
            }:
                break
            if not any(cells):
                break
            body.append(cells)
        return header, body
    return [], []


def _optional_text(value: str | None) -> str | None:
    if value is None or value.strip().lower() in _MISSING:
        return None
    return value.strip()


def _checked_numeric(
    value: str | None,
    parser: Callable[[str], float | None] = parse_numeric,
) -> float | None:
    """Keep missing values unknown; reject malformed or non-finite specs."""
    value = _optional_text(value)
    if value is None:
        return None
    parsed = parser(value)
    # Sign rule: ConstructionVesselSchema._validate_non_negative_cv_floats
    # and BaseVesselSchema._validate_non_negative_floats; no physical limit.
    if parsed is None or not math.isfinite(parsed) or parsed < 0:
        raise ValueError("Invalid numeric particulars")
    return parsed


def _source_url(value: str | None) -> str | None:
    """Keep only plain HTTP(S) references without credentials or queries."""
    value = _optional_text(value)
    if value is None:
        return None
    url = urlsplit(value)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or url.query
        or url.fragment
        or any(char.isspace() for char in value)
    ):
        raise ValueError("Invalid source reference")
    return value


def _split_md_row(line: str) -> list[str]:
    """Split a markdown table row into trimmed cells."""
    line = line.strip()
    line = line.removeprefix("|")
    line = line.removesuffix("|")
    return [c.strip() for c in line.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    """A markdown header/body separator row (e.g. ``---|---``)."""
    return bool(cells) and all(set(c) <= set("-: ") and c for c in cells)


def _parse_crane(value: str) -> float | None:
    """Parse a crane SWL cell like ``2×7,000`` or ``1,200`` -> per-crane tonnes."""
    if not value or value.strip() in {"-", "--"}:
        return None
    # Drop a leading "N×" multiplier; we record the per-crane SWL.
    cleaned = re.sub(r"^\s*\d+\s*[x×X]\s*", "", value.strip())
    return parse_numeric(cleaned)


def _parse_draft(value: str) -> float | None:
    """Parse a draft cell.

    Values like ``12/26`` mean transit/operating -> take transit (first).
    """
    if not value:
        return None
    first = value.split("/")[0]
    return parse_numeric(first)


def _parse_dp(value: str) -> int | None:
    """Parse a DP-class cell. ``Anchored`` / non-DP -> ``None``."""
    if not value:
        return None
    if "dp" not in value.lower():
        return None
    return parse_int_from_label(value)


def _find_spec_table(lines: list[str]) -> list[list[str]]:
    """Return the body rows (as cell-lists) of the vessel comparison matrix.

    Locates the markdown table whose header contains the spec columns and
    returns its data rows. Returns an empty list if not found.
    """
    return _find_spec_table_with_header(lines)[1]


def _map_spec_row(header: list[str], cells: list[str]) -> dict[str, Any] | None:
    """Map a comparison-matrix row to the construction-vessel schema."""
    row = dict(zip(header, cells))
    name = (row.get("vessel name") or "").strip()
    if not name:
        return None

    accommodation = _checked_numeric(row.get("accommodation"))
    if accommodation is not None and not accommodation.is_integer():
        raise ValueError("Accommodation must be an integer headcount")
    dp_text = _optional_text(row.get("dp class"))
    if (
        dp_text is not None
        and "dp" in dp_text.lower()
        and re.fullmatch(r"dp\s*\d+", dp_text, re.IGNORECASE) is None
    ):
        raise ValueError("Malformed DP label")

    mapped = {
        "VESSEL_NAME": name,
        "VESSEL_CATEGORY": _VESSEL_CATEGORY,
        "VESSEL_SUBTYPE": (row.get("type") or "").strip() or None,
        "DATA_SOURCE": DATA_SOURCE_MSIV,
        "DATA_SOURCE_URL": _source_url(row.get("source url")),
        "IMO_NUMBER": _optional_text(row.get("imo number") or row.get("imo")),
        "LOA_M": _checked_numeric(row.get("loa (m)")),
        "BEAM_M": _checked_numeric(row.get("beam (m)")),
        "DRAFT_M": _checked_numeric(row.get("draft (m)"), _parse_draft),
        "MAIN_CRANE_CAPACITY_T": _checked_numeric(
            row.get("main crane (mt)"), _parse_crane
        ),
        "AUX_CRANE_CAPACITY_T": _checked_numeric(
            row.get("aux crane (mt)"), _parse_crane
        ),
        "DP_CLASS": _parse_dp(dp_text or ""),
        "QUARTERS_CAPACITY": int(accommodation) if accommodation is not None else None,
        "DECK_AREA_M2": _checked_numeric(row.get("deck area (m2)")),
        "DECK_LOAD_CAPACITY_T": _checked_numeric(row.get("deck load capacity (mt)")),
    }
    # Format checks come from the existing schema, including the IMO format;
    # schema validation does not establish registry identity or brochure truth.
    validated = ConstructionVesselSchema(**mapped).model_dump(include=set(mapped))
    if not validated["VESSEL_NAME"]:
        raise ValueError("Missing normalized name")
    return validated


def collect_msiv_vessels(
    source_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Collect ACMA MSIV vessels as schema-mapped dicts.

    Args:
        source_dir: Override for the source directory. When ``None`` the
            ``ACMA_MSIV_DIR`` environment variable is used.

    Returns:
        A list of construction-vessel record dicts (vessel particulars only).
        Returns an empty list and logs a warning if the directory/file is
        unset or missing (graceful degradation without the off-repo share).
    """
    resolved = source_dir or os.environ.get(ACMA_ENV_VAR)
    if not resolved:
        logger.warning("%s not set; skipping MSIV vessel collection", ACMA_ENV_VAR)
        return []

    base = Path(resolved)
    if not base.is_dir():
        logger.warning("MSIV source dir not found: %s; skipping", base)
        return []

    matrix_path = base / _MATRIX_FILE
    if not matrix_path.is_file():
        logger.warning("MSIV matrix file missing: %s", matrix_path)
        return []

    records = parse_msiv_matrix(matrix_path.read_text(encoding="utf-8"))
    logger.info("Collected %d MSIV vessel records", len(records))
    return records


def parse_msiv_matrix(text: str) -> list[dict[str, Any]]:
    """Parse the MSIV specifications-matrix markdown text into records.

    Exposed separately from :func:`collect_msiv_vessels` so tests can drive it
    with inline markdown (no off-repo dependency).
    """
    lines = text.splitlines()

    header, body = _find_spec_table_with_header(lines)
    if not header:
        logger.warning("MSIV spec table header not found")
        return []

    records: list[dict[str, Any]] = []
    for row_number, cells in enumerate(body, start=1):
        if len(cells) != len(header):
            logger.warning(
                "Skipping MSIV particulars row %d: column count mismatch", row_number
            )
            continue
        try:
            mapped = _map_spec_row(header, cells)
        except ValueError:
            mapped = None
        if mapped is None:
            # Log structure only: source values may contain private content.
            logger.warning("Skipping invalid MSIV particulars row %d", row_number)
        if mapped is not None:
            records.append(mapped)
    return records
