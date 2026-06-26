"""Loader for additional off-repo ``/mnt/ace`` fleet sources (#595).

Ingests two further off-repo fleet datasets into the vessel-fleet schema by
explicit path (no environment variables -- the caller passes the directory):

1. **Heavy-lift CSVs** -- brochure-digitised heavy-lift / crane-vessel
   particulars captured in two snapshots:

   - ``heavy-lift-vessels-2010.csv``    (original 2010 snapshot)
   - ``heavy-lift-vessels-current.csv`` (current snapshot, enriched with
     IMO, current owner / status, and a ``source_url``)

   :func:`load_heavy_lift_csvs` maps both snapshots into the construction /
   heavy-lift schema, reconciles them by vessel name (current snapshot is
   authoritative; missing spec fields are filled forward from 2010), and
   stamps ``DATA_SOURCE`` + ``COLLECTION_DATE`` on every record.

2. **MSIV markdown DB** -- a Multi-Service Intervention Vessel database held
   as markdown tables. :func:`parse_msiv_markdown` extracts the vessel
   comparison matrix (name + particulars) and tags rows as
   ``intervention`` / ``msiv``.

Data policy (client-derived source): only public vessel *particulars* are
mapped. Cost / day-rate / mobilisation / scoring / recommendation tables, and
any client or project identifiers in the source text, are **never** read into
the output. The raw source folders are never copied into the repository --
both readers operate on a path supplied at call time.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from worldenergydata.vessel_fleet.collectors.acma_msiv_collector import (
    _find_spec_table,
    _parse_crane,
    _parse_draft,
    _parse_dp,
    _split_md_row,
    _SPEC_TABLE_HEADERS,
)
from worldenergydata.vessel_fleet.collectors.frontier_csv_collector import (
    _map_heavy_lift_row,
    _read_csv,
)
from worldenergydata.vessel_fleet.parsers.numeric import parse_numeric

logger = logging.getLogger(__name__)

# --- Source file names ------------------------------------------------------

HEAVY_LIFT_2010_FILE = "heavy-lift-vessels-2010.csv"
HEAVY_LIFT_CURRENT_FILE = "heavy-lift-vessels-current.csv"

# --- Provenance tags --------------------------------------------------------

DATA_SOURCE_HEAVY_LIFT_2010 = "mnt_ace_heavy_lift_csv_2010"
DATA_SOURCE_HEAVY_LIFT_CURRENT = "mnt_ace_heavy_lift_csv_current"
DATA_SOURCE_MSIV = "mnt_ace_msiv_md"

# --- Tagging ----------------------------------------------------------------

_HEAVY_LIFT_CATEGORY = "construction"
_HEAVY_LIFT_TYPE = "heavy_lift"
_MSIV_CATEGORY = "intervention"
_MSIV_TYPE = "msiv"

_COLLECTION_DATE_2010 = "2010"

# Numeric / categorical spec fields that may be filled forward from the 2010
# snapshot into a current record when the current value is missing.
_RECONCILE_SPEC_FIELDS = (
    "LOA_M",
    "BEAM_M",
    "DRAFT_M",
    "DP_CLASS",
    "MAIN_CRANE_CAPACITY_T",
    "MAIN_CRANE_REACH_M",
    "AUX_CRANE_CAPACITY_T",
    "AUX_CRANE_REACH_M",
    "DECK_LOAD_CAPACITY_T",
    "CLASSIFICATION_SOCIETY",
    "VESSEL_SUBTYPE",
)

# "> Created: 2025-08-07" provenance line in the MSIV markdown headers.
_CREATED_RE = re.compile(r"created:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)


# --- Heavy-lift CSV loader --------------------------------------------------


def _map_heavy_lift_snapshot(
    row: dict[str, str],
    *,
    data_source: str,
    collection_date: Optional[str],
) -> Optional[dict[str, Any]]:
    """Map one heavy-lift CSV row, stamping snapshot provenance.

    Reuses the shared Frontier row mapper for the spec columns, then overrides
    ``DATA_SOURCE`` and ``COLLECTION_DATE`` for this snapshot. Returns ``None``
    for rows without a vessel name.
    """
    mapped = _map_heavy_lift_row(row)
    if mapped is None:
        return None
    mapped["DATA_SOURCE"] = data_source
    mapped["COLLECTION_DATE"] = collection_date
    return mapped


def _current_collection_date(row: dict[str, str]) -> Optional[str]:
    """Derive a COLLECTION_DATE for a current-snapshot row.

    Prefers the per-row ``status_year`` (e.g. ``2024``); falls back to the
    literal ``"current"`` when absent.
    """
    year = (row.get("status_year") or "").strip()
    return year or "current"


def _reconcile(
    current: list[dict[str, Any]],
    legacy: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reconcile current and 2010 heavy-lift snapshots into one record set.

    The current snapshot is authoritative. For a vessel present in both
    snapshots, any missing spec field on the current record is filled forward
    from its 2010 counterpart. Vessels present only in 2010 are appended with
    their original provenance.
    """
    by_name: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for rec in current:
        key = rec["VESSEL_NAME"].upper()
        by_name[key] = rec
        order.append(key)

    legacy_by_name: dict[str, dict[str, Any]] = {}
    for rec in legacy:
        legacy_by_name.setdefault(rec["VESSEL_NAME"].upper(), rec)

    # Fill-forward missing specs onto matched current records.
    for key, cur in by_name.items():
        old = legacy_by_name.get(key)
        if old is None:
            continue
        for field in _RECONCILE_SPEC_FIELDS:
            if cur.get(field) is None and old.get(field) is not None:
                cur[field] = old[field]

    # Append vessels that only appear in the 2010 snapshot.
    for key, old in legacy_by_name.items():
        if key not in by_name:
            by_name[key] = old
            order.append(key)

    return [by_name[key] for key in order]


def load_heavy_lift_csvs(source_dir: str | Path) -> list[dict[str, Any]]:
    """Load and reconcile the 2010 + current heavy-lift CSV snapshots.

    Args:
        source_dir: Directory containing ``heavy-lift-vessels-2010.csv`` and
            ``heavy-lift-vessels-current.csv``.

    Returns:
        Reconciled construction / heavy-lift records (one per vessel). Each
        record carries ``DATA_SOURCE`` and ``COLLECTION_DATE``. Returns an
        empty list (with a warning) when the directory is missing, so callers
        and CI degrade gracefully without the off-repo share mounted.
    """
    base = Path(source_dir)
    if not base.is_dir():
        logger.warning("Heavy-lift source dir not found: %s; skipping", base)
        return []

    current: list[dict[str, Any]] = []
    cur_path = base / HEAVY_LIFT_CURRENT_FILE
    if cur_path.is_file():
        for row in _read_csv(cur_path):
            mapped = _map_heavy_lift_snapshot(
                row,
                data_source=DATA_SOURCE_HEAVY_LIFT_CURRENT,
                collection_date=_current_collection_date(row),
            )
            if mapped is not None:
                current.append(mapped)
    else:
        logger.warning("Current heavy-lift file missing: %s", cur_path)

    legacy: list[dict[str, Any]] = []
    legacy_path = base / HEAVY_LIFT_2010_FILE
    if legacy_path.is_file():
        for row in _read_csv(legacy_path):
            mapped = _map_heavy_lift_snapshot(
                row,
                data_source=DATA_SOURCE_HEAVY_LIFT_2010,
                collection_date=_COLLECTION_DATE_2010,
            )
            if mapped is not None:
                legacy.append(mapped)
    else:
        logger.warning("2010 heavy-lift file missing: %s", legacy_path)

    records = _reconcile(current, legacy)
    logger.info(
        "Loaded %d reconciled heavy-lift vessels (%d current, %d legacy-2010)",
        len(records),
        len(current),
        len(legacy),
    )
    return records


# --- MSIV markdown parser ---------------------------------------------------


def _extract_created_date(text: str) -> Optional[str]:
    """Return the ``Created:`` ISO date from the markdown header, if present."""
    match = _CREATED_RE.search(text)
    return match.group(1) if match else None


def _map_msiv_row(
    header: list[str],
    cells: list[str],
    collection_date: Optional[str],
) -> Optional[dict[str, Any]]:
    """Map one vessel-comparison-matrix row to an intervention/MSIV record.

    Only vessel particulars are mapped; no cost / scoring / mobilisation or
    project-identifier content is read.
    """
    row = dict(zip(header, cells))
    name = (row.get("vessel name") or "").strip()
    if not name:
        return None

    accommodation = parse_numeric(row.get("accommodation"))

    return {
        "VESSEL_NAME": name,
        "VESSEL_CATEGORY": _MSIV_CATEGORY,
        "VESSEL_TYPE": _MSIV_TYPE,
        "VESSEL_SUBTYPE": (row.get("type") or "").strip() or None,
        "DATA_SOURCE": DATA_SOURCE_MSIV,
        "DATA_SOURCE_URL": None,
        "COLLECTION_DATE": collection_date,
        "LOA_M": parse_numeric(row.get("loa (m)")),
        "BEAM_M": parse_numeric(row.get("beam (m)")),
        "DRAFT_M": _parse_draft(row.get("draft (m)", "")),
        "MAIN_CRANE_CAPACITY_T": _parse_crane(row.get("main crane (mt)", "")),
        "AUX_CRANE_CAPACITY_T": _parse_crane(row.get("aux crane (mt)", "")),
        "DP_CLASS": _parse_dp(row.get("dp class", "")),
        "QUARTERS_CAPACITY": (
            int(accommodation) if accommodation is not None else None
        ),
    }


def parse_msiv_markdown(path: str | Path) -> list[dict[str, Any]]:
    """Parse a single MSIV markdown file into intervention/MSIV records.

    Locates the vessel comparison matrix (the only particulars table) and maps
    each data row. Files without that table (e.g. prose-only documents or the
    cost/recommendation reports) yield an empty list.

    Args:
        path: Path to a ``.md`` file from the MSIV database.

    Returns:
        A list of intervention/MSIV record dicts (vessel particulars only).
    """
    md_path = Path(path)
    if not md_path.is_file():
        logger.warning("MSIV markdown file not found: %s; skipping", md_path)
        return []

    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    collection_date = _extract_created_date(text)

    header: list[str] = []
    for line in lines:
        if "|" not in line:
            continue
        candidate = [c.lower() for c in _split_md_row(line)]
        if all(h in " ".join(candidate) for h in _SPEC_TABLE_HEADERS):
            header = candidate
            break

    if not header:
        return []

    records: list[dict[str, Any]] = []
    for cells in _find_spec_table(lines):
        if len(cells) != len(header):
            continue
        mapped = _map_msiv_row(header, cells, collection_date)
        if mapped is not None:
            records.append(mapped)
    return records


def parse_msiv_dir(source_dir: str | Path) -> list[dict[str, Any]]:
    """Parse every ``*.md`` file in an MSIV directory into vessel records.

    De-duplicates by vessel name across files (first occurrence wins), so the
    comparison matrix and any spec-sheet tables collapse to one record each.

    Args:
        source_dir: Directory holding the MSIV markdown database files.

    Returns:
        Combined, de-duplicated intervention/MSIV records.
    """
    base = Path(source_dir)
    if not base.is_dir():
        logger.warning("MSIV source dir not found: %s; skipping", base)
        return []

    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    for md_path in sorted(base.glob("*.md")):
        for rec in parse_msiv_markdown(md_path):
            key = rec["VESSEL_NAME"].upper()
            if key in seen:
                continue
            seen.add(key)
            records.append(rec)
    logger.info("Parsed %d MSIV vessels from %s", len(records), base)
    return records


# --- Combine ----------------------------------------------------------------


def combine(
    heavy_lift_dir: Optional[str | Path] = None,
    msiv_dir: Optional[str | Path] = None,
) -> list[dict[str, Any]]:
    """Combine heavy-lift CSV and MSIV markdown records into one record set.

    Args:
        heavy_lift_dir: Directory with the heavy-lift CSV snapshots. Skipped
            when ``None``.
        msiv_dir: Directory with the MSIV markdown database. Skipped when
            ``None``.

    Returns:
        A single list of schema-mapped vessel records from both sources.
        Heavy-lift records come first, followed by MSIV records.
    """
    records: list[dict[str, Any]] = []
    if heavy_lift_dir is not None:
        records.extend(load_heavy_lift_csvs(heavy_lift_dir))
    if msiv_dir is not None:
        records.extend(parse_msiv_dir(msiv_dir))
    logger.info("Combined %d /mnt/ace fleet records", len(records))
    return records
