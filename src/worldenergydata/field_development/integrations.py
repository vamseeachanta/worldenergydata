# ABOUTME: Enrichment layer wiring the playbook to FDAS/vessel/subsea catalogs.
# ABOUTME: Issue #575 (epic #567) — lazy, graceful cross-module integration.
"""
worldenergydata.field_development.integrations
==============================================

Turns a recommended concept into an *economics + execution* view by reusing
existing repo modules rather than rebuilding them:

* **FDAS** (`worldenergydata.fdas`) — depth → dev-system classification and a
  rough NPV via the cashflow/economics API.
* **Vessel fleet** (`worldenergydata.vessel_fleet`) — installation feasibility
  (which construction vessels can reach the water depth and lift/lay).
* **Subsea catalogs** (`worldenergydata.subsea`) — pick representative rigid
  jumper and mooring components from the curated specs.

All cross-module imports are **lazy** (inside functions) and every integration
**degrades gracefully** — if a sibling package or its data is unavailable, the
function returns ``None``/empty instead of raising, so the core engine and
``import field_development`` stay usable in a minimal environment.

Note on FDAS: dev-system classification is *depth-driven* (dry / subsea15 /
subsea20), not concept-driven, so economics attach at the **field** level; vessel
feasibility and hardware picks vary per **candidate concept**.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from worldenergydata.field_development.enums import ConceptType, TreeType
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.recommendation import ScoredConcept

M_TO_FT = 3.280839895

# Floating hosts that need a mooring system.
_MOORED_HOSTS = {
    ConceptType.SPAR,
    ConceptType.SEMISUB_FPS,
    ConceptType.FPSO,
    ConceptType.FLNG,
    ConceptType.TLP,
}


def _subsea_data_dir() -> Path:
    """Repo curated-subsea dir, resolved relative to this file (worktree/install)."""
    return Path(__file__).parents[3] / "data" / "modules" / "subsea" / "curated"


@dataclass
class Economics:
    """Field-level (depth-driven) economics estimate."""

    dev_system: Optional[str] = None
    capex_mm: Optional[float] = None
    npv_mm: Optional[float] = None
    discount_rate: Optional[float] = None
    note: str = ""


@dataclass
class VesselFeasibility:
    """Installation feasibility for a candidate concept."""

    water_depth_reachable: Optional[bool] = None
    capable_vessel_count: int = 0
    example_vessels: list[str] = field(default_factory=list)
    max_crane_capacity_t: Optional[float] = None
    needs_pipelay: bool = False
    note: str = ""


@dataclass
class HardwarePicks:
    """Representative subsea hardware selected from the curated catalogs."""

    rigid_jumper_id: Optional[str] = None
    mooring_component_id: Optional[str] = None
    note: str = ""


@dataclass
class EnrichedConcept:
    """A scored concept plus its execution/economics enrichment."""

    scored: ScoredConcept
    vessel: VesselFeasibility
    hardware: HardwarePicks


# --------------------------------------------------------------------------- #
# FDAS economics (field-level)
# --------------------------------------------------------------------------- #
def dev_system_for(concept: FieldConcept) -> Optional[str]:
    """Classify the FDAS dev system from water depth (converted m → ft)."""
    if concept.water_depth_m is None:
        return None
    try:
        from worldenergydata.fdas.core.config import classify_dev_system_by_depth
    except Exception:
        return None
    return classify_dev_system_by_depth(concept.water_depth_m * M_TO_FT)


def estimate_economics(concept: FieldConcept) -> Economics:
    """Rough, field-level economics using FDAS assumptions + the NPV API.

    Best-effort: CAPEX from dev-system assumptions; NPV only when enough inputs
    (plateau rate, price, field life) are present to build a simple cashflow.
    """
    eco = Economics()
    sysname = dev_system_for(concept)
    eco.dev_system = sysname
    if sysname in (None, "unknown"):
        eco.note = "water depth unknown — cannot classify dev system"
        return eco
    try:
        from worldenergydata.fdas.core.config import AssumptionsManager
    except Exception:
        eco.note = "FDAS unavailable"
        return eco

    mgr = AssumptionsManager()
    host_capex = mgr.get(sysname, "HOST_CAPEX_MM", 0.0)
    per_well = mgr.get(sysname, "SURF_PER_WELL_MM", 0.0)
    wells = concept.num_wells or 0
    eco.capex_mm = round(host_capex + per_well * wells, 1)
    eco.discount_rate = concept.discount_rate or mgr.get(
        sysname, "DISCOUNT_RATE_ANNUAL", 0.10
    )
    eco.npv_mm = _rough_npv(concept, eco.capex_mm, eco.discount_rate, mgr, sysname)
    if eco.npv_mm is None:
        eco.note = "CAPEX estimated; NPV needs plateau rate, price deck, field life"
    return eco


def _rough_npv(concept, capex_mm, discount_rate, mgr, sysname) -> Optional[float]:
    """A coarse annual-cashflow NPV; None if inputs are insufficient."""
    if not (concept.plateau_rate_boed and concept.oil_price_usd_bbl
            and concept.field_life_years):
        return None
    try:
        from worldenergydata.fdas.api import EconomicsQuery
    except Exception:
        return None
    annual_rev = concept.plateau_rate_boed * 365.0 * concept.oil_price_usd_bbl / 1e6
    fixed_opex = mgr.get(sysname, "FIXED_OPEX_MM_PER_YEAR", 0.0)
    var_opex = mgr.get(sysname, "VARIABLE_OPEX_$/BBL", 0.0)
    annual_opex = fixed_opex + var_opex * concept.plateau_rate_boed * 365.0 / 1e6
    royalty = mgr.get(sysname, "ROYALTY_RATE", 0.0)
    net_annual = annual_rev * (1 - royalty) - annual_opex
    cashflows = [-capex_mm] + [net_annual] * int(concept.field_life_years)
    try:
        return round(EconomicsQuery.npv(cashflows, discount_rate, period="annual"), 1)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Vessel feasibility (per candidate concept)
# --------------------------------------------------------------------------- #
def vessel_feasibility(concept: FieldConcept, scored: ScoredConcept) -> VesselFeasibility:
    """Which construction vessels can install this concept at this water depth."""
    vf = VesselFeasibility(needs_pipelay=scored.tree_type == TreeType.WET)
    if concept.water_depth_m is None:
        vf.note = "water depth unknown"
        return vf
    try:
        from worldenergydata.vessel_fleet.loaders.construction_vessel_loader import (
            ConstructionVesselLoader,
        )
    except Exception:
        vf.note = "vessel_fleet unavailable"
        return vf
    try:
        df = ConstructionVesselLoader().load()
        capable = df[df["WATER_DEPTH_RATING_M"] >= concept.water_depth_m]
        if vf.needs_pipelay and "PIPELAY_TENSION_T" in capable.columns:
            capable = capable[capable["PIPELAY_TENSION_T"].fillna(0) > 0]
        vf.water_depth_reachable = len(capable) > 0
        vf.capable_vessel_count = int(len(capable))
        vf.example_vessels = capable["VESSEL_NAME"].head(3).tolist()
        if "MAIN_CRANE_CAPACITY_T" in capable.columns and len(capable):
            vf.max_crane_capacity_t = float(capable["MAIN_CRANE_CAPACITY_T"].max())
    except Exception as exc:  # pragma: no cover - defensive
        vf.note = f"vessel query failed: {type(exc).__name__}"
    return vf


# --------------------------------------------------------------------------- #
# Subsea hardware picks (per candidate concept)
# --------------------------------------------------------------------------- #
def hardware_picks(concept: FieldConcept, scored: ScoredConcept,
                   data_dir: Optional[Path] = None) -> HardwarePicks:
    """Representative rigid-jumper (wet trees) + mooring (floating host) picks."""
    hp = HardwarePicks()
    base = data_dir or _subsea_data_dir()
    if scored.tree_type == TreeType.WET:
        hp.rigid_jumper_id = _pick_jumper(base / "rigid_jumper_specs.csv")
    if scored.concept_type in _MOORED_HOSTS:
        hp.mooring_component_id = _pick_mooring(base / "mooring_components.csv")
    if hp.rigid_jumper_id is None and hp.mooring_component_id is None:
        hp.note = "no catalog match (dry-tree fixed host, or catalogs unavailable)"
    return hp


def _pick_jumper(csv_path: Path) -> Optional[str]:
    """Highest pressure-rated rigid jumper as a representative pick."""
    try:
        from worldenergydata.subsea.models.rigid_jumper import load_rigid_jumpers
        specs = load_rigid_jumpers(csv_path)
    except Exception:
        return None
    if not specs:
        return None
    return max(specs, key=lambda s: s.pressure_rating_psi).component_id


def _pick_mooring(csv_path: Path) -> Optional[str]:
    """Highest-MBL chain component as a representative mooring pick."""
    try:
        from worldenergydata.subsea.models.mooring import load_mooring_components
        comps = load_mooring_components(csv_path)
    except Exception:
        return None
    chains = [c for c in comps if c.component_type == "chain"] or comps
    if not chains:
        return None
    return max(chains, key=lambda c: c.mbl_kn).component_id


# --------------------------------------------------------------------------- #
# Top-level enrichment
# --------------------------------------------------------------------------- #
def enrich(
    concept: FieldConcept, scored_concepts: list[ScoredConcept]
) -> tuple[Economics, list[EnrichedConcept]]:
    """Attach economics (field-level) + vessel/hardware (per concept).

    Args:
        concept: The field concept (input parameters).
        scored_concepts: Output of :func:`recommend`.

    Returns:
        ``(economics, enriched)`` — field-level economics and a per-concept
        enrichment list aligned with ``scored_concepts``.
    """
    economics = estimate_economics(concept)
    enriched = [
        EnrichedConcept(
            scored=sc,
            vessel=vessel_feasibility(concept, sc),
            hardware=hardware_picks(concept, sc),
        )
        for sc in scored_concepts
    ]
    return economics, enriched
