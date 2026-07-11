# ABOUTME: Past-projects registry loader + query API (selectable historical developments).
# ABOUTME: Issue #931 (epic #929, A2) — GoM first, derived ONLY from in-repo data sources.
"""
worldenergydata.field_development.past_projects
===============================================

Historical field-development projects as machine-readable, selectable lists —
filterable by region, operator, and water-depth class. Gulf of Mexico first;
the ``worldwide`` region is structured but deliberately empty (later slice of
epic #929).

All entries live in :data:`PAST_PROJECTS_PATH` (``past_projects.yml``, shipped
next to this module) — **no project data is hardcoded here**.

Derivation & provenance
-----------------------
Every catalog entry is derived from data already in this repo and lists its
sources (repo-relative paths) under ``sources``:

* ``config/fields.yml`` — the CANONICAL field-identity registry (epic #754):
  ``project_id`` == ``canonical_id``, display name, play, BSEE area/blocks.
  This module adds **no parallel identity mappings**.
* ``config/ong_field_development/fields_registry.yml`` — auto-generated
  BOEM/BSEE-backed attribute registry: operator, water depth, status,
  first oil, development system, facility.
* ``packages/worldenergydata-bsee/.../buckskin/buckskin_config.py`` — BSEE
  WAR/LAB-derived Buckskin field config (the one canonical field absent from
  the auto-generated registry).

No fabrication: where a source does not state an attribute it is ``null`` in
the catalog (with a ``notes`` explanation) and ``None`` on the record. The
contract tests assert both provenance completeness (every entry has sources
that exist in the repo) and coherence with the upstream registries.

Water-depth classes follow the BOEM convention: ``shallow`` < 1,000 ft,
``deepwater`` 1,000–4,999 ft, ``ultra_deepwater`` >= 5,000 ft.

Usage::

    from worldenergydata.field_development.past_projects import past_projects

    past_projects(region="gulf_of_mexico")
    past_projects(operator="Chevron")
    past_projects(water_depth_class="ultra_deepwater", status="producing")

This module is intentionally NOT exported from the package ``__init__`` (same
as ``terrain``): import it directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

__all__ = [
    "PAST_PROJECTS_PATH",
    "REQUIRED_PROJECT_FIELDS",
    "VALID_STATUSES",
    "WATER_DEPTH_CLASSES",
    "PastProject",
    "classify_water_depth",
    "load_past_projects",
    "past_projects",
    "past_project_operators",
    "past_project_regions",
]

PAST_PROJECTS_PATH = Path(__file__).parent / "past_projects.yml"

#: Keys every catalog entry must carry (nullable ones may be ``null``, but the
#: key itself must be present so gaps are explicit, never silent).
REQUIRED_PROJECT_FIELDS = {
    "project_id",
    "display_name",
    "operator",
    "water_depth_ft",
    "development_system",
    "facility",
    "status",
    "first_oil_year",
    "play",
    "bsee_area_blocks",
    "sources",
}

#: Status vocabulary, exactly as used by the upstream attribute registry
#: (``config/ong_field_development/fields_registry.yml``). ``None`` = unknown.
VALID_STATUSES = {"producing", "non_producing", "pre-FID", "decommissioned"}

#: BOEM water-depth convention (feet): deepwater >= 1,000 ft,
#: ultra-deepwater >= 5,000 ft.
WATER_DEPTH_CLASSES = ("shallow", "deepwater", "ultra_deepwater")
_DEEPWATER_MIN_FT = 1_000
_ULTRA_DEEPWATER_MIN_FT = 5_000


def classify_water_depth(water_depth_ft: Optional[float]) -> Optional[str]:
    """Classify a water depth (ft) per the BOEM convention.

    Returns ``"shallow"`` (< 1,000 ft), ``"deepwater"`` (1,000–4,999 ft) or
    ``"ultra_deepwater"`` (>= 5,000 ft); ``None`` in -> ``None`` out (unknown
    depth is never classified).
    """
    if water_depth_ft is None:
        return None
    if water_depth_ft >= _ULTRA_DEEPWATER_MIN_FT:
        return "ultra_deepwater"
    if water_depth_ft >= _DEEPWATER_MIN_FT:
        return "deepwater"
    return "shallow"


@dataclass(frozen=True)
class PastProject:
    """One historical field-development project (identity per fields.yml)."""

    project_id: str
    display_name: str
    region: str
    region_display_name: str
    operator: Optional[str]
    water_depth_ft: Optional[float]
    development_system: Optional[str]
    facility: Optional[str]
    status: Optional[str]
    first_oil_year: Optional[int]
    play: Optional[str]
    bsee_area_blocks: tuple[str, ...]
    sources: tuple[str, ...]
    notes: Optional[str] = None

    @property
    def water_depth_class(self) -> Optional[str]:
        """BOEM water-depth class derived from ``water_depth_ft`` (or None)."""
        return classify_water_depth(self.water_depth_ft)


def _validate_entry(region_key: str, raw: dict[str, Any]) -> None:
    missing = REQUIRED_PROJECT_FIELDS - raw.keys()
    if missing:
        raise ValueError(
            f"past_projects.yml entry {raw.get('project_id')!r} in region "
            f"{region_key!r} is missing required fields: {sorted(missing)}"
        )
    if not raw["project_id"] or not raw["display_name"]:
        raise ValueError(
            f"past_projects.yml entry in region {region_key!r} has an empty "
            "project_id/display_name"
        )
    sources = raw["sources"]
    if not isinstance(sources, list) or not sources:
        raise ValueError(
            f"past_projects.yml entry {raw['project_id']!r} has no sources — "
            "every entry must trace to at least one in-repo data source"
        )
    status = raw["status"]
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(
            f"past_projects.yml entry {raw['project_id']!r} carries invalid "
            f"status {status!r} (expected one of {sorted(VALID_STATUSES)} or null)"
        )
    depth = raw["water_depth_ft"]
    if depth is not None and (not isinstance(depth, (int, float)) or depth <= 0):
        raise ValueError(
            f"past_projects.yml entry {raw['project_id']!r} carries invalid "
            f"water_depth_ft {depth!r} (expected positive number or null)"
        )


def load_past_projects(path: Optional[Path] = None) -> list[PastProject]:
    """Load and validate the past-projects catalog (all regions).

    Returns records in file order. Raises :class:`ValueError` on a malformed
    catalog: missing required keys, empty/missing ``sources``, an unknown
    ``status``, a non-positive water depth, or a duplicate ``project_id``.
    """
    catalog_path = Path(path) if path is not None else PAST_PROJECTS_PATH
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    regions = data.get("regions")
    if not isinstance(regions, dict):
        raise ValueError(
            f"past-projects catalog {catalog_path} has no 'regions' mapping"
        )

    projects: list[PastProject] = []
    seen: set[str] = set()
    for region_key, region in regions.items():
        region = region or {}
        region_display = str(region.get("display_name") or region_key)
        for raw in region.get("projects") or []:
            _validate_entry(region_key, raw)
            project_id = raw["project_id"]
            if project_id in seen:
                raise ValueError(
                    f"Duplicate project_id in past_projects.yml: {project_id!r}"
                )
            seen.add(project_id)
            projects.append(
                PastProject(
                    project_id=project_id,
                    display_name=raw["display_name"],
                    region=region_key,
                    region_display_name=region_display,
                    operator=raw["operator"],
                    water_depth_ft=raw["water_depth_ft"],
                    development_system=raw["development_system"],
                    facility=raw["facility"],
                    status=raw["status"],
                    first_oil_year=raw["first_oil_year"],
                    play=raw["play"],
                    bsee_area_blocks=tuple(raw["bsee_area_blocks"] or ()),
                    sources=tuple(raw["sources"]),
                    notes=raw.get("notes"),
                )
            )
    return projects


def _norm(value: str) -> str:
    return " ".join(value.split()).lower()


def past_projects(
    region: Optional[str] = None,
    operator: Optional[str] = None,
    water_depth_class: Optional[str] = None,
    status: Optional[str] = None,
    path: Optional[Path] = None,
) -> list[PastProject]:
    """Selectable list of past projects, optionally filtered.

    Args:
        region: Region key (``"gulf_of_mexico"``) or region display name
            (``"US Gulf of Mexico"``); case-insensitive.
        operator: Operator name, case-insensitive exact match. Entries whose
            operator is unknown (``None``) never match an operator filter.
        water_depth_class: One of :data:`WATER_DEPTH_CLASSES`; raises
            :class:`ValueError` on anything else (fail loud on typos).
            Entries with unknown water depth never match a class filter.
        status: One of :data:`VALID_STATUSES` (case-insensitive); raises
            :class:`ValueError` on anything else. Unknown status (``None``)
            never matches.
        path: Optional alternate catalog path (tests).

    Returns:
        Matching records in catalog order. Unknown region/operator values
        return an empty list (fail-closed — nothing is invented).
    """
    if water_depth_class is not None and water_depth_class not in WATER_DEPTH_CLASSES:
        raise ValueError(
            f"Unknown water_depth_class {water_depth_class!r} "
            f"(expected one of {list(WATER_DEPTH_CLASSES)})"
        )
    status_key: Optional[str] = None
    if status is not None:
        by_norm = {_norm(s): s for s in VALID_STATUSES}
        status_key = by_norm.get(_norm(status))
        if status_key is None:
            raise ValueError(
                f"Unknown status {status!r} (expected one of {sorted(VALID_STATUSES)})"
            )

    selected = []
    for project in load_past_projects(path=path):
        if region is not None and _norm(region) not in (
            _norm(project.region),
            _norm(project.region_display_name),
        ):
            continue
        if operator is not None and (
            project.operator is None or _norm(project.operator) != _norm(operator)
        ):
            continue
        if (
            water_depth_class is not None
            and project.water_depth_class != water_depth_class
        ):
            continue
        if status_key is not None and project.status != status_key:
            continue
        selected.append(project)
    return selected


def past_project_operators(
    region: Optional[str] = None, path: Optional[Path] = None
) -> list[str]:
    """Sorted unique operator names (for selection UIs). Nulls are omitted."""
    return sorted(
        {
            p.operator
            for p in past_projects(region=region, path=path)
            if p.operator is not None
        }
    )


def past_project_regions(path: Optional[Path] = None) -> dict[str, str]:
    """Region key -> display name for every region in the catalog (incl. empty)."""
    catalog_path = Path(path) if path is not None else PAST_PROJECTS_PATH
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    regions = data.get("regions") or {}
    return {
        key: str((region or {}).get("display_name") or key)
        for key, region in regions.items()
    }
