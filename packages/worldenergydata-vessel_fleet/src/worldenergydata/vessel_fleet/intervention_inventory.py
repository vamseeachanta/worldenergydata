"""Queryable intervention inventory with source conflicts and observed bounds.

This view reuses the packaged rosters and existing identity resolver. It does
not edit source data, infer well-control capability from a hull type, or turn
historical residency into present availability. Issue #585 defines the classes;
the source YAML files remain the authority for individual observations.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

from worldenergydata.vessel_fleet.fleet_catalog import classify_asset_class
from worldenergydata.vessel_fleet.identity_resolver import resolve_identities
from worldenergydata.vessel_fleet.schemas.intervention_vessel import (
    InterventionVesselSchema,
)

_DATA = Path(__file__).resolve().parent / "data"
DEFAULT_ROSTERS = (
    _DATA / "intervention_vessels_seed.yml",
    _DATA / "intervention_osv_roster.yml",
)
_DEDICATED = frozenset({"rlwi_monohull", "heavy_intervention_semi"})
# These are source field names, not inferred capabilities or default ratings.
_FIELDS = (
    "VESSEL_TYPE",
    "INTERVENTION_CLASS",
    "RISER_CAPABLE",
    "SUBSEA_LUBRICATOR",
    "IRS_SYSTEM",
    "WELL_CONTROL_PACKAGE",
    "CT_CAPABLE",
    "GOM_RESIDENT",
    "WATER_DEPTH_RATING_M",
)


@dataclass(frozen=True)
class InventoryObservation:
    """One source listing, with a portable locator and unchanged capabilities.

    A missing or unclassified type has no asset class. An explicit ``other``
    type remains positive evidence and can disagree with a dedicated class.
    """

    vessel: InterventionVesselSchema
    asset_class: str | None
    locator: str
    source: str | None
    confidence: str | None


@dataclass(frozen=True)
class InventoryAsset:
    """One resolved hull; conflicting values are unknown in ``vessel``.

    Observations retain the original values, citations and confidence labels.
    ``asset_class='other'`` includes unresolved class conflicts; observations
    retain the candidate classes for the observed upper bound.
    """

    vessel: InterventionVesselSchema
    asset_class: str
    observations: tuple[InventoryObservation, ...]
    conflicts: tuple[str, ...]


def _consensus(values: Iterable[Any]) -> tuple[Any, bool]:
    known = {value for value in values if value is not None}
    return (next(iter(known)) if len(known) == 1 else None, len(known) > 1)


def load_intervention_inventory(
    paths: Iterable[Path] | None = None,
) -> list[InventoryAsset]:
    """Load seed/roster-format YAML and merge listings of the same hull.

    Missing or invalid requested inputs raise rather than produce a misleading
    empty inventory. No arguments loads both packaged rosters; an empty iterable
    explicitly represents an empty input. Source numbers remain in metres.
    """
    records: list[dict[str, Any]] = []
    for path in DEFAULT_ROSTERS if paths is None else paths:
        path = Path(path)
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or not isinstance(doc.get("vessels"), list):
            raise TypeError(f"{path.name}: vessels must be a list")
        for index, row in enumerate(doc["vessels"]):
            if not isinstance(row, dict):
                raise TypeError(f"{path.name}: vessels entries must be mappings")
            fields = {key: row[key.lower()] for key in _FIELDS if key.lower() in row}
            name = row.get("vessel_name") or row.get("name")
            if not isinstance(name, str):
                raise TypeError(f"{path.name}: VESSEL_NAME must be a string")
            if not name.strip():
                raise ValueError(f"{path.name}: VESSEL_NAME must be nonempty")
            vessel = InterventionVesselSchema(
                VESSEL_NAME=name,
                OPERATOR=row.get("operator"),
                **fields,
            )
            asset_class = classify_asset_class(
                rig_type=row.get("rig_type"),
                vessel_type=vessel.VESSEL_TYPE,
            )
            # The classifier's fallback is not positive evidence of a class.
            if asset_class == "other" and not any(
                (value or "").strip().lower() == "other"
                for value in (row.get("rig_type"), vessel.VESSEL_TYPE)
            ):
                asset_class = None
            observation = InventoryObservation(
                vessel=vessel,
                asset_class=asset_class,
                locator=f"{path.name}:vessels[{index}]",
                source=row.get("source_url") or row.get("source"),
                confidence=row.get("confidence"),
            )
            records.append(
                {
                    "name": name,
                    "operator": row.get("operator"),
                    "owner": row.get("owner"),
                    "imo": row.get("imo"),
                    "aka": row.get("aka") or [],
                    "observation": observation,
                }
            )

    assets = []
    for cluster in resolve_identities(records):
        observations = tuple(member["observation"] for member in cluster["members"])
        merged: dict[str, Any] = {}
        conflicts = []
        for field in _FIELDS:
            value, conflict = _consensus(getattr(o.vessel, field) for o in observations)
            merged[field] = value
            if conflict:
                conflicts.append(field)
        asset_class, conflict = _consensus(o.asset_class for o in observations)
        if conflict:
            conflicts.append("ASSET_CLASS")
        assets.append(
            InventoryAsset(
                vessel=InterventionVesselSchema(
                    VESSEL_NAME=observations[0].vessel.VESSEL_NAME,
                    CANONICAL_NAME=cluster["canonical_name"],
                    **merged,
                ),
                asset_class=asset_class or "other",
                observations=observations,
                conflicts=tuple(sorted(conflicts)),
            )
        )
    return assets


def query_intervention_inventory(
    assets: Iterable[InventoryAsset],
    *,
    asset_class: str | None = None,
    minimum_depth_m: float | None = None,
    gom_resident: bool | None = None,
    riser_capable: bool | None = None,
) -> list[InventoryAsset]:
    """Select agreed attributes, with an inclusive minimum nameplate depth.

    Unknown or conflicting attributes do not satisfy a specified filter.
    Depth/residency matching is inventory screening, not well-serviceability
    approval or a claim of current commercial availability.
    """
    if minimum_depth_m is not None and (
        not isfinite(minimum_depth_m) or minimum_depth_m < 0
    ):
        raise ValueError("Minimum depth must be finite and nonnegative")
    selected = []
    for asset in assets:
        vessel = asset.vessel
        if asset_class is not None and asset.asset_class != asset_class:
            continue
        if minimum_depth_m is not None and (
            vessel.WATER_DEPTH_RATING_M is None
            or vessel.WATER_DEPTH_RATING_M < minimum_depth_m
        ):
            continue
        if gom_resident is not None and vessel.GOM_RESIDENT is not gom_resident:
            continue
        if riser_capable is not None and vessel.RISER_CAPABLE is not riser_capable:
            continue
        selected.append(asset)
    return selected


def summarize_intervention_inventory(
    assets: Iterable[InventoryAsset],
) -> dict[str, Any]:
    """Count resolved hulls and bound residency uncertainty in this input only.

    Hand-count identities: lower = agreed dedicated and resident; upper = all
    possibly dedicated hulls not confirmed non-resident. This is a set-count
    interval, not a population forecast or a statistical confidence interval.
    Research estimates are quoted from the committed catalog with their source
    locators and explicitly remain NOT_EVALUATED; that file has no auditable
    primary-source/date basis for validating those population claims.
    """
    assets = list(assets)
    lower = upper = 0
    for asset in assets:
        if asset.asset_class in _DEDICATED and asset.vessel.GOM_RESIDENT is True:
            lower += 1
        possibly_dedicated = any(
            o.asset_class in _DEDICATED for o in asset.observations
        )
        if possibly_dedicated and asset.vessel.GOM_RESIDENT is not False:
            upper += 1
    path = _DATA / "intervention_fleet_catalog.yml"
    research = yaml.safe_load(path.read_text(encoding="utf-8"))[
        "reconciliation_to_research"
    ]
    estimates = {
        key: {
            **item,
            "status": "NOT_EVALUATED",
            "source": f"{path.name}:reconciliation_to_research.{key}",
            "reason": "Primary-source basis and applicable date are not recorded.",
        }
        for key, item in research.items()
    }
    return {
        "scope": "observed input rosters; historical residency, not live availability",
        "distinct_assets": len(assets),
        "by_asset_class": dict(sorted(Counter(a.asset_class for a in assets).items())),
        "gom_dedicated_observed": {"lower": lower, "upper": upper},
        "unknown_depth_assets": sum(
            a.vessel.WATER_DEPTH_RATING_M is None for a in assets
        ),
        "conflicted_assets": sum(bool(a.conflicts) for a in assets),
        "research_estimates": estimates,
    }
