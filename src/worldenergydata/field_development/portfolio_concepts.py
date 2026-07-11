# ABOUTME: Map a Lower-Tertiary field id -> its authored FieldConcept (or None).
# ABOUTME: Issue #969 (epic #942) — single reviewable seam for the 3 FDP concepts.
"""
worldenergydata.field_development.portfolio_concepts
====================================================

Resolve the **authored** :class:`FieldConcept` for a Lower-Tertiary Explorer
field id. Only 3 of the 10 LT fields carry a committed FDP page with real
geometry (well count / concept type / tieback distance): ``cascade_chinook``,
``julia`` and ``stones``. The architecture-drawing panel (#969) draws a to-scale
plan-view for exactly those 3 (via
:func:`worldenergydata.field_development.layout.render_layout`) and shows a
visible placeholder for the other 7 — an honest gap over a degenerate 1-tree
drawing.

Concept provenance (kept here so a later reviewer sees one seam, not build
scripts):

* ``julia`` — the richest authored concept (5 wells, 2 manifolds, 30 km tieback),
  mirrored from ``scripts/field_development/build_julia_fdp.py``. Deliberately
  disagrees with ``_research.json`` (6 wells) — "richest" wins.
* ``stones`` / ``cascade_chinook`` — ``to_concept()`` applied to the matching
  ``reports/field_development/portfolio/_research.json`` entry ("Stones" — FPSO,
  8 wells; "Chinook" — subsea tieback, 2 wells, 24 km). ``cascade_chinook`` is
  drawn from the Chinook-only concept; the render sites caption it honestly.

A concept whose numeric inputs are non-finite (NaN/inf) is rejected → ``None``
(defence-in-depth so no ``NaN``/``Infinity`` can reach the SVG or the sidecar
JSON, which would dark-screen the Explorer).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

from worldenergydata.field_development.enums import (
    ConceptType,
    FluidType,
    MetoceanRegime,
    ReservoirDistribution,
)
from worldenergydata.field_development.models import FieldConcept

_RESEARCH_JSON = (
    Path(__file__).resolve().parents[3]
    / "reports/field_development/portfolio/_research.json"
)

_FLUID = {
    "oil": FluidType.OIL,
    "gas": FluidType.GAS,
    "condensate": FluidType.CONDENSATE,
    "gas_condensate": FluidType.GAS_CONDENSATE,
}

# field id -> the _research.json "name" for the two portfolio concepts sourced
# there. julia is authored inline below (richest committed concept).
_RESEARCH_NAME = {"stones": "Stones", "cascade_chinook": "Chinook"}

# Julia (Lower Tertiary subsea tieback to Jack/St. Malo). Mirrors the committed
# FDP concept in scripts/field_development/build_julia_fdp.py (5 wells / 2
# manifolds) — the richest authored geometry of the three.
_JULIA = FieldConcept(
    name="Julia (Lower Tertiary)",
    operator="ExxonMobil (Equinor 50%)",
    region="US Gulf of Mexico — Walker Ridge",
    water_depth_m=2160.0,
    fluid_type=FluidType.OIL,
    api_gravity=27.0,
    gor_scf_stb=1000.0,
    recoverable_reserves_mmboe=80.0,
    num_wells=5,
    num_manifolds=2,
    plateau_rate_boed=34000.0,
    field_life_years=20.0,
    concept_type=ConceptType.SUBSEA_TIEBACK,
    tieback_distance_km=30.0,
    distance_to_host_km=30.0,
    host_spare_capacity=True,
    metocean_regime=MetoceanRegime.HURRICANE_CYCLONE,
    reservoir_distribution=ReservoirDistribution.DISTRIBUTED,
    year_fid=2013,
    year_first_oil=2016,
    discount_rate=0.10,
    data_source="config/analysis/lower_tertiary/fields/julia.yml + BSEE OGOR-A",
)


def _concept_type(d: dict) -> Optional[ConceptType]:
    """Concept type from a research profile (mirrors build_fdp_portfolio)."""
    v = d.get("verify") or {}
    raw = v.get("corrected_concept_type") or d.get("concept_type")
    try:
        return ConceptType(raw) if raw else None
    except ValueError:
        return None


def _to_concept(d: dict) -> FieldConcept:
    """Map a researched profile dict to a FieldConcept.

    Port of ``scripts/field_development/build_fdp_portfolio.py::to_concept`` so
    the mapping lives in one reviewable place inside the package (no import of a
    build script from ``scripts/``).
    """
    ct = _concept_type(d)
    is_tieback = ct == ConceptType.SUBSEA_TIEBACK
    return FieldConcept(
        name=d["name"],
        operator=d.get("operator_current"),
        region="US Gulf of Mexico",
        water_depth_m=d.get("water_depth_m"),
        fluid_type=_FLUID.get((d.get("fluid") or "").lower()),
        concept_type=ct,
        tieback_distance_km=d.get("tieback_distance_km") if is_tieback else None,
        distance_to_host_km=d.get("tieback_distance_km") if is_tieback else None,
        host_spare_capacity=True if is_tieback else None,
        num_wells=d.get("num_wells") or 4,
        recoverable_reserves_mmboe=d.get("recoverable_reserves_mmboe"),
        plateau_rate_boed=d.get("plateau_boed"),
        year_first_oil=d.get("first_oil_year"),
        metocean_regime=MetoceanRegime.HURRICANE_CYCLONE,
        data_source="SubseaIQ + web research (FDP portfolio)",
    )


def _load_research_concept(name: str) -> Optional[FieldConcept]:
    """Find the ``_research.json`` entry by name and map it to a FieldConcept."""
    try:
        profiles = json.loads(_RESEARCH_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for d in profiles:
        if d.get("name") == name:
            return _to_concept(d)
    return None


def _is_finite_concept(c: FieldConcept) -> bool:
    """False if any numeric field is NaN/inf (defence-in-depth; §3.5)."""
    for value in c.model_dump().values():
        if isinstance(value, float) and not math.isfinite(value):
            return False
    return True


def concept_for(field_id: str) -> Optional[FieldConcept]:
    """Return the authored :class:`FieldConcept` for ``field_id``, else ``None``.

    Real geometry exists for exactly ``cascade_chinook`` / ``julia`` / ``stones``;
    every other id (the concept-less 7 and any unknown id) returns ``None`` so the
    caller emits a placeholder. A concept with non-finite numeric inputs is also
    rejected (→ ``None``).
    """
    if field_id == "julia":
        concept: Optional[FieldConcept] = _JULIA
    elif field_id in _RESEARCH_NAME:
        concept = _load_research_concept(_RESEARCH_NAME[field_id])
    else:
        return None
    if concept is None or not _is_finite_concept(concept):
        return None
    return concept
