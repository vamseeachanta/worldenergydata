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
import os
import re
from pathlib import Path
from typing import Any, Optional

from worldenergydata.vessel_fleet.parsers.numeric import (
    parse_int_from_label,
    parse_numeric,
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


def _split_md_row(line: str) -> list[str]:
    """Split a markdown table row into trimmed cells."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    """A markdown header/body separator row (e.g. ``---|---``)."""
    return bool(cells) and all(set(c) <= set("-: ") and c for c in cells)


def _parse_crane(value: str) -> Optional[float]:
    """Parse a crane SWL cell like ``2×7,000`` or ``1,200`` -> per-crane tonnes."""
    if not value or value.strip() in {"-", "--"}:
        return None
    # Drop a leading "N×" multiplier; we record the per-crane SWL.
    cleaned = re.sub(r"^\s*\d+\s*[x×X]\s*", "", value.strip())
    return parse_numeric(cleaned)


def _parse_draft(value: str) -> Optional[float]:
    """Parse a draft cell.

    Values like ``12/26`` mean transit/operating -> take transit (first).
    """
    if not value:
        return None
    first = value.split("/")[0]
    return parse_numeric(first)


def _parse_dp(value: str) -> Optional[int]:
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
    for idx, line in enumerate(lines):
        if "|" not in line:
            continue
        header = [c.lower() for c in _split_md_row(line)]
        header_joined = " ".join(header)
        if all(h in header_joined for h in _SPEC_TABLE_HEADERS):
            # Header found; the next line should be a separator.
            body: list[list[str]] = []
            for body_line in lines[idx + 1 :]:
                if "|" not in body_line:
                    break
                cells = _split_md_row(body_line)
                if _is_separator_row(cells):
                    continue
                if not any(cells):
                    break
                body.append(cells)
            return body
    return []


def _map_spec_row(header: list[str], cells: list[str]) -> Optional[dict[str, Any]]:
    """Map a comparison-matrix row to the construction-vessel schema."""
    row = dict(zip(header, cells))
    name = (row.get("vessel name") or "").strip()
    if not name:
        return None

    accommodation = parse_numeric(row.get("accommodation"))

    return {
        "VESSEL_NAME": name,
        "VESSEL_CATEGORY": _VESSEL_CATEGORY,
        "VESSEL_SUBTYPE": (row.get("type") or "").strip() or None,
        "DATA_SOURCE": DATA_SOURCE_MSIV,
        "DATA_SOURCE_URL": None,
        "LOA_M": parse_numeric(row.get("loa (m)")),
        "BEAM_M": parse_numeric(row.get("beam (m)")),
        "DRAFT_M": _parse_draft(row.get("draft (m)", "")),
        "MAIN_CRANE_CAPACITY_T": _parse_crane(row.get("main crane (mt)", "")),
        "AUX_CRANE_CAPACITY_T": _parse_crane(row.get("aux crane (mt)", "")),
        "DP_CLASS": _parse_dp(row.get("dp class", "")),
        "QUARTERS_CAPACITY": int(accommodation) if accommodation is not None else None,
    }


def collect_msiv_vessels(
    source_dir: Optional[str | Path] = None,
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

    # Re-locate the header to zip column names against body rows.
    header: list[str] = []
    for idx, line in enumerate(lines):
        if "|" not in line:
            continue
        candidate = [c.lower() for c in _split_md_row(line)]
        if all(h in " ".join(candidate) for h in _SPEC_TABLE_HEADERS):
            header = candidate
            break

    if not header:
        logger.warning("MSIV spec table header not found")
        return []

    body = _find_spec_table(lines)
    records: list[dict[str, Any]] = []
    for cells in body:
        if len(cells) != len(header):
            continue
        mapped = _map_spec_row(header, cells)
        if mapped is not None:
            records.append(mapped)
    return records
