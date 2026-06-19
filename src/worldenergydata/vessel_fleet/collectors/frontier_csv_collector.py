"""Collector for off-repo Frontier heavy-lift & pipelay vessel CSVs.

Reads brochure-digitized vessel particulars from a local directory resolved
via the ``FRONTIER_VESSEL_FLEET_DIR`` environment variable. Only public
vessel-spec columns are mapped into the construction-vessel schema; no cost,
day-rate, or recommendation content is read.

Source files (columns in feet):
    - ``heavy-lift-vessels-current.csv``
    - ``pipelay-contractors-current.csv``

The raw client folder is *never* copied into the repository -- this collector
reads it in place at runtime via the env-var path.
"""

from __future__ import annotations

import csv
import logging
import os
from pathlib import Path
from typing import Any, Optional

from worldenergydata.vessel_fleet.constants import FT_TO_M
from worldenergydata.vessel_fleet.parsers.numeric import (
    parse_bool,
    parse_int_from_label,
    parse_numeric,
)

logger = logging.getLogger(__name__)

#: Environment variable holding the off-repo Frontier source directory.
FRONTIER_ENV_VAR = "FRONTIER_VESSEL_FLEET_DIR"

#: Provenance tag written to ``DATA_SOURCE`` for Frontier records.
DATA_SOURCE_HEAVY_LIFT = "frontier_heavy_lift_csv"
DATA_SOURCE_PIPELAY = "frontier_pipelay_csv"

_HEAVY_LIFT_FILE = "heavy-lift-vessels-current.csv"
_PIPELAY_FILE = "pipelay-contractors-current.csv"

_VESSEL_CATEGORY = "construction"


def _ft_to_m(value: Optional[str]) -> Optional[float]:
    """Convert a feet value (possibly messy string) to metres, rounded to 1dp."""
    feet = parse_numeric(value)
    if feet is None:
        return None
    return round(feet * FT_TO_M, 1)


def _clean_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = value.strip()
    return s or None


def _map_heavy_lift_row(row: dict[str, str]) -> Optional[dict[str, Any]]:
    """Map one heavy-lift CSV row to the construction-vessel schema.

    Returns ``None`` for rows without a vessel name.
    """
    name = _clean_str(row.get("vessel_name"))
    if not name:
        return None

    return {
        "VESSEL_NAME": name,
        "VESSEL_CATEGORY": _VESSEL_CATEGORY,
        "VESSEL_TYPE": "heavy_lift",
        "VESSEL_SUBTYPE": _clean_str(row.get("vessel_type")),
        "OWNER": _clean_str(row.get("current_owner")) or _clean_str(row.get("contractor")),
        "OPERATOR": _clean_str(row.get("contractor")),
        "IMO_NUMBER": _clean_str(row.get("imo_number")),
        "CLASSIFICATION_SOCIETY": _clean_str(row.get("classification")),
        "STATUS": _clean_str(row.get("current_status")),
        "DATA_SOURCE": DATA_SOURCE_HEAVY_LIFT,
        "DATA_SOURCE_URL": _clean_str(row.get("source_url")),
        "LOA_M": _ft_to_m(row.get("loa_ft")),
        "BEAM_M": _ft_to_m(row.get("beam_ft")),
        "DRAFT_M": _ft_to_m(row.get("draft_ft")),
        "DP_CLASS": parse_int_from_label(row.get("dp_class")),
        "MAIN_CRANE_CAPACITY_T": parse_numeric(row.get("primary_lift_capacity_t")),
        "MAIN_CRANE_REACH_M": _ft_to_m(row.get("primary_lift_radius_ft")),
        "AUX_CRANE_CAPACITY_T": parse_numeric(row.get("secondary_lift_capacity_t")),
        "AUX_CRANE_REACH_M": _ft_to_m(row.get("secondary_lift_radius_ft")),
        "DECK_LOAD_CAPACITY_T": parse_numeric(row.get("deck_capacity_t")),
    }


def _map_pipelay_row(row: dict[str, str]) -> Optional[dict[str, Any]]:
    """Map one pipelay CSV row to the construction-vessel schema.

    Returns ``None`` for rows without a vessel name.
    """
    name = _clean_str(row.get("vessel_name"))
    if not name:
        return None

    # Prefer loaded draft (the deeper operating value); fall back to light.
    draft = _ft_to_m(row.get("draft_load_ft")) or _ft_to_m(row.get("draft_light_ft"))

    accommodation = parse_numeric(row.get("accommodation_persons"))

    return {
        "VESSEL_NAME": name,
        "VESSEL_CATEGORY": _VESSEL_CATEGORY,
        "VESSEL_TYPE": "pipelay_vessel",
        "VESSEL_SUBTYPE": _clean_str(row.get("vessel_type")),
        "OWNER": _clean_str(row.get("current_owner")) or _clean_str(row.get("contractor")),
        "OPERATOR": _clean_str(row.get("contractor")),
        "IMO_NUMBER": _clean_str(row.get("imo_number")),
        "STATUS": _clean_str(row.get("current_status")),
        "DATA_SOURCE": DATA_SOURCE_PIPELAY,
        "DATA_SOURCE_URL": _clean_str(row.get("source_url")),
        "LOA_M": _ft_to_m(row.get("loa_ft")),
        "BEAM_M": _ft_to_m(row.get("beam_ft")),
        "DRAFT_M": draft,
        "DP_CLASS": parse_int_from_label(row.get("dp_class")),
        "QUARTERS_CAPACITY": int(accommodation) if accommodation is not None else None,
        "PIPELAY_METHOD": _clean_str(row.get("lay_method")),
        "PIPELAY_CAPACITY_IN": parse_numeric(row.get("max_pipe_dia_in")),
        "WATER_DEPTH_RATING_M": _ft_to_m(row.get("max_water_depth_ft")),
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def collect_frontier_vessels(
    source_dir: Optional[str | Path] = None,
) -> list[dict[str, Any]]:
    """Collect Frontier heavy-lift + pipelay vessels as schema-mapped dicts.

    Args:
        source_dir: Override for the source directory. When ``None`` the
            ``FRONTIER_VESSEL_FLEET_DIR`` environment variable is used.

    Returns:
        A list of construction-vessel record dicts. Returns an empty list and
        logs a warning if the directory is unset or missing (so the pipeline
        and CI degrade gracefully without the off-repo share mounted).
    """
    resolved = source_dir or os.environ.get(FRONTIER_ENV_VAR)
    if not resolved:
        logger.warning(
            "%s not set; skipping Frontier vessel collection", FRONTIER_ENV_VAR
        )
        return []

    base = Path(resolved)
    if not base.is_dir():
        logger.warning("Frontier source dir not found: %s; skipping", base)
        return []

    records: list[dict[str, Any]] = []

    hl_path = base / _HEAVY_LIFT_FILE
    if hl_path.is_file():
        for row in _read_csv(hl_path):
            mapped = _map_heavy_lift_row(row)
            if mapped is not None:
                records.append(mapped)
    else:
        logger.warning("Heavy-lift file missing: %s", hl_path)

    pl_path = base / _PIPELAY_FILE
    if pl_path.is_file():
        for row in _read_csv(pl_path):
            mapped = _map_pipelay_row(row)
            if mapped is not None:
                records.append(mapped)
    else:
        logger.warning("Pipelay file missing: %s", pl_path)

    logger.info("Collected %d Frontier vessel records", len(records))
    return records
