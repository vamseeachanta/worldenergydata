"""Load the OSV/MPSV + subsea-intervention vendor fleet roster (#593).

The curated roster ships as package data at
``worldenergydata/vessel_fleet/data/intervention_osv_roster.yml`` -- named
units confirmed from public vendor asset pages, shipyard reference pages,
class registers and contract news across the six requested vendors (Helix,
Island Offshore/TIOS, C-Innovation/Edison Chouest, Oceaneering, AKOFS, DOF).

This module exposes ``load_intervention_osv_roster`` returning the list of
vessel dicts, plus ``summarize_intervention_osv_roster`` producing counts by
vessel_type and by gom_resident.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# Roster lives one level up from this ``loaders/`` subpackage, alongside the
# other curated catalogs in ``vessel_fleet/data/`` -- resolves identically
# whether installed editable or unpacked from the built wheel.
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_FILE = "intervention_osv_roster.yml"


def load_intervention_osv_roster(
    path: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Load the intervention/OSV vendor fleet roster.

    Args:
        path: Optional path to a roster YAML file. Defaults to the curated
            ``intervention_osv_roster.yml`` shipped as package data.

    Returns:
        List of vessel records (one dict per named unit). Empty list if the
        file is missing or contains no ``vessels`` block.
    """
    roster_path = Path(path) if path is not None else _DATA_DIR / _DEFAULT_FILE

    if not roster_path.exists():
        logger.warning("Intervention OSV roster not found: %s", roster_path)
        return []

    with roster_path.open("r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh) or {}

    vessels = doc.get("vessels", [])
    if not isinstance(vessels, list):
        logger.warning("Roster 'vessels' is not a list: %s", roster_path)
        return []

    logger.info("Loaded %d intervention/OSV vessels", len(vessels))
    return vessels


def summarize_intervention_osv_roster(
    vessels: Optional[list[dict[str, Any]]] = None,
    path: Optional[Path] = None,
) -> dict[str, Any]:
    """Summarize the roster by vessel_type and by gom_resident.

    Args:
        vessels: Optional pre-loaded list of vessel records. If omitted, the
            roster is loaded from ``path`` (or the default package data).
        path: Optional roster path forwarded to ``load_intervention_osv_roster``
            when ``vessels`` is not supplied.

    Returns:
        Dictionary with:
            - ``total``: total vessel count
            - ``by_vessel_type``: {vessel_type: count}
            - ``by_gom_resident``: {"true"|"false"|"unknown": count}
    """
    if vessels is None:
        vessels = load_intervention_osv_roster(path=path)

    by_vessel_type: dict[str, int] = {}
    by_gom_resident: dict[str, int] = {"true": 0, "false": 0, "unknown": 0}

    for vessel in vessels:
        vtype = vessel.get("vessel_type") or "unknown"
        by_vessel_type[vtype] = by_vessel_type.get(vtype, 0) + 1

        gom = vessel.get("gom_resident")
        if gom is True:
            by_gom_resident["true"] += 1
        elif gom is False:
            by_gom_resident["false"] += 1
        else:
            by_gom_resident["unknown"] += 1

    return {
        "total": len(vessels),
        "by_vessel_type": by_vessel_type,
        "by_gom_resident": by_gom_resident,
    }
