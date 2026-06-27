# ABOUTME: Concept recommendation engine — FieldConcept params -> ranked shortlist.
# ABOUTME: Issue #570 (epic #567) — deterministic heuristics + MCDA scoring.
"""
worldenergydata.field_development.recommendation
================================================

Given a :class:`FieldConcept` of *input parameters*, produce a **ranked, scored
shortlist** of candidate development concepts — matching how operators gate at
Concept Select (FEL-1 / AACE Class 4): compare many options at low fidelity,
rank, and carry a shortlist forward (not a single answer).

Pipeline (briefing §A6):
1. Enumerate *feasible* concepts (water-depth envelope + host-vs-tieback logic).
2. For each, derive tree type / topology / processing / flow-assurance overlay.
3. Score each on weighted criteria (CAPEX, OPEX, schedule, recovery,
   flexibility, risk) via simple additive weighting (SAW), adjusted by the
   field's parameters.
4. Rank by total score; attach human-readable rationale.

All thresholds live in :class:`Thresholds` and all weights in
:class:`CriteriaWeights` — both overridable per call, so regional signatures and
operator preferences are *data*, not code branches. Scores are deterministic:
the same input yields the same ranking.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from worldenergydata.field_development.basin import region_fit as _region_fit
from worldenergydata.field_development.basin import region_to_basin as _region_to_basin
from worldenergydata.field_development.enums import (
    ConceptType,
    MetoceanRegime,
    ReservoirDistribution,
    Topology,
    TreeType,
)
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.sanity import HOST_DEPTH_ENVELOPES_M

CRITERIA = (
    "capex",
    "opex",
    "schedule",
    "recovery",
    "flexibility",
    "risk",
    "depth_fit",
    "region_fit",
)


@dataclass(frozen=True)
class CriteriaWeights:
    """Weights for simple additive weighting. Need not sum to 1 (normalized).

    ``depth_fit`` and ``region_fit`` carry the most weight: water depth is the
    dominant feasibility gate (briefing §A2) and regional development culture is
    the dominant tie-breaker *within* a depth band (e.g. FPSO in Brazil vs a spar
    in the GoM at the same depth; see :mod:`basin`). Both are calibrated against
    real field concepts (see :mod:`calibration`).
    """

    capex: float = 0.16
    opex: float = 0.08
    schedule: float = 0.08
    recovery: float = 0.12
    flexibility: float = 0.06
    risk: float = 0.08
    depth_fit: float = 0.24
    region_fit: float = 0.18

    def as_dict(self) -> dict[str, float]:
        return {c: getattr(self, c) for c in CRITERIA}


# Per-concept preferred (sweet-spot) water-depth band in m — tighter than the
# feasibility envelope; drives the ``depth_fit`` score. Calibrated to the real
# depth→concept distribution of the enriched SubseaIQ catalog.
#
# Calibration v3: the moored-floater bands (TLP / spar / semisub) were nearly
# identical, so depth_fit could not separate them and the spar/TLP picks lost to
# the semisub's flatter, higher base profile. They are now tightened to the
# observed GoM medians — TLP ≈ 1036 m, spar ≈ 1265 m, semisub ≈ 1958 m — so the
# bands tile by depth (TLP shallowest, then spar, then semisub). This recovered
# spar (0→7) and roughly doubled TLP recall (15→30) with no leakage: water depth
# is a pure input. See ``docs/domains/field-development/calibration-v2.md``.
DEPTH_SWEET_M: dict[ConceptType, tuple[float, float]] = {
    ConceptType.NUI: (0.0, 120.0),
    ConceptType.FIXED_JACKET: (0.0, 300.0),
    ConceptType.COMPLIANT_TOWER: (400.0, 900.0),
    ConceptType.TLP: (400.0, 1400.0),
    ConceptType.SPAR: (700.0, 1600.0),
    ConceptType.SEMISUB_FPS: (1700.0, 2800.0),
    ConceptType.FPSO: (700.0, 3000.0),
    ConceptType.FLNG: (700.0, 3000.0),
    ConceptType.SUBSEA_TIEBACK: (0.0, 3000.0),  # flat — depends on host
    ConceptType.SUBSEA_TO_SHORE: (0.0, 3000.0),
}
_DEPTH_DECAY_M = 500.0  # linear fall-off outside the sweet-spot band


def _depth_fit(concept: ConceptType, depth_m: float | None) -> float:
    """1.0 inside the concept's sweet-spot band, decaying to 0 over a margin."""
    if depth_m is None:
        return 0.5  # neutral when depth is unknown
    band = DEPTH_SWEET_M.get(concept)
    if band is None:
        return 0.5
    lo, hi = band
    if lo <= depth_m <= hi:
        return 1.0
    gap = (lo - depth_m) if depth_m < lo else (depth_m - hi)
    return max(0.0, 1.0 - gap / _DEPTH_DECAY_M)


@dataclass(frozen=True)
class Thresholds:
    """Decision thresholds, sourced to the concept-selection briefing (§A5–A6)."""

    tieback_max_km: float = 60.0  # practical host-vs-tieback pivot
    tieback_marginal_mmboe: float = 50.0  # below this, tieback is favoured
    flow_assurance_warn_km: float = 32.0  # ~20 mi — economics deteriorate beyond
    hydrate_risk_km: float = 80.0  # long tiebacks need active heating/inhibition
    tieback_hard_max_km: float = 200.0  # beyond longest field records — infeasible
    nui_max_wells: int = 6  # NUI/minimal facility is for few wells


@dataclass
class ScoredConcept:
    """One ranked candidate concept with transparent scoring + rationale."""

    concept_type: ConceptType
    tree_type: TreeType
    topology: Topology | None = None
    processing: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    rationale: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# Base per-criterion profiles in [0, 1] (1 = favourable). Adjusted by inputs.
# Sourced qualitatively from briefing §A3–A5 (relative CAPEX, intervention cost,
# schedule, recovery, placement flexibility, baseline execution risk).
_CONCEPT_PROFILES: dict[ConceptType, dict[str, float]] = {
    ConceptType.SUBSEA_TIEBACK: dict(
        capex=0.95, opex=0.70, schedule=0.95, recovery=0.55, flexibility=0.80, risk=0.70
    ),
    ConceptType.NUI: dict(
        capex=0.60, opex=0.70, schedule=0.70, recovery=0.45, flexibility=0.35, risk=0.60
    ),
    ConceptType.FIXED_JACKET: dict(
        capex=0.70, opex=0.80, schedule=0.65, recovery=0.85, flexibility=0.55, risk=0.80
    ),
    ConceptType.COMPLIANT_TOWER: dict(
        capex=0.45, opex=0.70, schedule=0.45, recovery=0.80, flexibility=0.45, risk=0.55
    ),
    ConceptType.TLP: dict(
        capex=0.45, opex=0.80, schedule=0.50, recovery=0.90, flexibility=0.45, risk=0.65
    ),
    ConceptType.SPAR: dict(
        capex=0.40, opex=0.80, schedule=0.45, recovery=0.90, flexibility=0.45, risk=0.65
    ),
    ConceptType.SEMISUB_FPS: dict(
        capex=0.50, opex=0.65, schedule=0.55, recovery=0.70, flexibility=0.85, risk=0.70
    ),
    ConceptType.FPSO: dict(
        capex=0.40, opex=0.55, schedule=0.50, recovery=0.70, flexibility=0.85, risk=0.65
    ),
    ConceptType.FLNG: dict(
        capex=0.25, opex=0.50, schedule=0.35, recovery=0.65, flexibility=0.70, risk=0.45
    ),
    ConceptType.SUBSEA_TO_SHORE: dict(
        capex=0.55, opex=0.85, schedule=0.55, recovery=0.60, flexibility=0.70, risk=0.55
    ),
}

# Which concepts carry dry vs wet trees (briefing §A3).
_DRY_TREE = {
    ConceptType.FIXED_JACKET,
    ConceptType.COMPLIANT_TOWER,
    ConceptType.TLP,
    ConceptType.SPAR,
    ConceptType.NUI,
}


def _tieback_possible(c: FieldConcept, th: Thresholds) -> bool:
    """A tieback needs a reachable host: known distance, within the hard max,
    and spare capacity not explicitly ruled out. Without a host there is nothing
    to tie back to — so this gates *feasibility*, distinct from *attractiveness*.
    """
    if c.distance_to_host_km is None:
        return False
    if c.distance_to_host_km > th.tieback_hard_max_km:
        return False
    return c.host_spare_capacity is not False


def feasible_concepts(c: FieldConcept, th: Thresholds) -> list[ConceptType]:
    """Return concepts whose water-depth envelope admits this field.

    If water depth is unknown, all depth-feasible concepts are considered (the
    engine still ranks them on the other criteria). The subsea tieback is gated
    on a reachable host (see :func:`_tieback_possible`).
    """
    if c.water_depth_m is None:
        feasible = list(_CONCEPT_PROFILES.keys())
    else:
        feasible = [
            concept
            for concept, (lo, hi) in HOST_DEPTH_ENVELOPES_M.items()
            if lo <= c.water_depth_m <= hi
        ]
        # FLNG shares FPSO's envelope (stranded-gas variant).
        if ConceptType.FPSO in feasible:
            feasible.append(ConceptType.FLNG)
    if ConceptType.SUBSEA_TIEBACK in feasible and not _tieback_possible(c, th):
        feasible.remove(ConceptType.SUBSEA_TIEBACK)
    return feasible


def _tieback_attractive(c: FieldConcept, th: Thresholds) -> bool:
    """Host-vs-tieback pivot (briefing §A5): near + spare capacity + marginal."""
    if c.distance_to_host_km is None:
        return False
    near = c.distance_to_host_km <= th.tieback_max_km
    spare = c.host_spare_capacity is not False  # None treated as possible
    marginal = (
        c.recoverable_reserves_mmboe is None
        or c.recoverable_reserves_mmboe <= th.tieback_marginal_mmboe
    )
    return near and spare and marginal


def _choose_tree_type(concept: ConceptType, c: FieldConcept) -> TreeType:
    """Dry for TLP/Spar/jacket; wet for subsea/floating hosts (briefing §A3)."""
    return TreeType.DRY if concept in _DRY_TREE else TreeType.WET


def _choose_topology(c: FieldConcept) -> Topology | None:
    """Few wells -> satellite; many -> cluster (briefing §A4)."""
    if c.num_wells is None:
        return None
    return Topology.SATELLITE if c.num_wells <= 3 else Topology.CLUSTER


def _processing_triggers(c: FieldConcept, th: Thresholds) -> list[str]:
    """Boosting / processing recommendations (briefing §A4)."""
    out: list[str] = []
    if c.distance_to_host_km and c.distance_to_host_km >= th.tieback_max_km:
        out.append("multiphase_boosting")
    if (
        c.fluid_type
        and c.fluid_type.value in ("gas", "gas_condensate")
        and (c.distance_to_host_km and c.distance_to_host_km >= th.hydrate_risk_km)
    ):
        out.append("subsea_compression")
    return out


def _score_concept(
    concept: ConceptType,
    c: FieldConcept,
    th: Thresholds,
    weights: CriteriaWeights,
    tieback_pref: bool,
) -> ScoredConcept:
    """Score a single feasible concept and build its rationale."""
    scores = dict(_CONCEPT_PROFILES[concept])
    scores["depth_fit"] = _depth_fit(concept, c.water_depth_m)
    scores["region_fit"] = _region_fit(concept, c.region)
    rationale: list[str] = []
    warnings: list[str] = []
    is_tieback = concept == ConceptType.SUBSEA_TIEBACK

    # --- Basin development culture (briefing §A2; see basin.py) ---
    basin = _region_to_basin(c.region)
    if basin is not None:
        pretty = basin.replace("_", " ")
        if scores["region_fit"] >= 0.9:
            rationale.append(f"typical of {pretty} development practice")
        elif scores["region_fit"] <= 0.2:
            warnings.append(f"atypical concept for {pretty}")

    # --- Reserves: large reserves favour a dedicated host's recovery; ---
    # --- small/marginal favour the cheap tieback. ---
    if c.recoverable_reserves_mmboe is not None:
        if c.recoverable_reserves_mmboe > th.tieback_marginal_mmboe and not is_tieback:
            scores["recovery"] = min(1.0, scores["recovery"] + 0.05)
            rationale.append(
                f"large reserves ({c.recoverable_reserves_mmboe:g} MMboe) justify a "
                "dedicated host"
            )
        if c.recoverable_reserves_mmboe <= th.tieback_marginal_mmboe and is_tieback:
            scores["capex"] = min(1.0, scores["capex"] + 0.03)
            rationale.append("marginal reserves favour a low-CAPEX tieback")

    # --- Tieback feasibility / flow assurance ---
    if is_tieback:
        if tieback_pref:
            rationale.append(
                f"host within {th.tieback_max_km:g} km with spare capacity"
            )
        else:
            scores["risk"] = max(0.0, scores["risk"] - 0.25)
            warnings.append("tieback not clearly attractive (distance/capacity/size)")
        d = c.distance_to_host_km
        if d is not None and d > th.flow_assurance_warn_km:
            scores["risk"] = max(0.0, scores["risk"] - 0.15)
            warnings.append(
                f"tieback {d:g} km exceeds ~{th.flow_assurance_warn_km:g} km — "
                "flow-assurance economics deteriorate (insulation/heating needed)"
            )
        if d is not None and d > th.hydrate_risk_km:
            warnings.append(
                f"tieback {d:g} km is a long offset — active heating / boosting "
                "likely required"
            )

    # --- NUI / minimal facility is for marginal, low-well-count fields; ---
    # --- penalise it for scale (many wells or large reserves). ---
    if concept == ConceptType.NUI:
        big_count = c.num_wells is not None and c.num_wells > th.nui_max_wells
        big_reserves = (
            c.recoverable_reserves_mmboe is not None
            and c.recoverable_reserves_mmboe > th.tieback_marginal_mmboe
        )
        if big_count or big_reserves:
            scores["recovery"] = max(0.0, scores["recovery"] - 0.25)
            scores["flexibility"] = max(0.0, scores["flexibility"] - 0.20)
            warnings.append(
                "NUI/minimal facility suits marginal, low-well-count fields — "
                "scale here favours a full platform"
            )

    # --- Dry-tree recovery uplift when reservoir is compact/stacked ---
    if (
        concept in _DRY_TREE
        and c.reservoir_distribution == ReservoirDistribution.COMPACT_STACKED
    ):
        scores["recovery"] = min(1.0, scores["recovery"] + 0.05)
        rationale.append("compact/stacked reservoir suits dry-tree vertical access")
    if (
        concept not in _DRY_TREE
        and c.reservoir_distribution == ReservoirDistribution.DISTRIBUTED
    ):
        scores["flexibility"] = min(1.0, scores["flexibility"] + 0.05)
        rationale.append("distributed reservoir suits flexible subsea well placement")

    # --- Metocean: hurricanes penalise permanently-moored FPSO unless ---
    # --- disconnectable; harsh-persistent favours robust fixed/subsea. ---
    if (
        c.metocean_regime == MetoceanRegime.HURRICANE_CYCLONE
        and concept == ConceptType.FPSO
    ):
        scores["risk"] = max(0.0, scores["risk"] - 0.20)
        warnings.append("hurricane regime: FPSO needs a disconnectable turret")

    # --- Storage / export: no host within reach favours FPSO (storage) ---
    if (
        concept == ConceptType.FPSO
        and c.distance_to_shore_km is not None
        and c.distance_to_shore_km > 200
    ):
        scores["flexibility"] = min(1.0, scores["flexibility"] + 0.05)
        rationale.append("remote from shore — FPSO storage avoids an export pipeline")

    total = _weighted_total(scores, weights)
    return ScoredConcept(
        concept_type=concept,
        tree_type=_choose_tree_type(concept, c),
        topology=_choose_topology(c) if concept not in _DRY_TREE else None,
        processing=_processing_triggers(c, th) if concept not in _DRY_TREE else [],
        scores={k: round(v, 4) for k, v in scores.items()},
        total_score=round(total, 4),
        rationale=rationale,
        warnings=warnings,
    )


def _weighted_total(scores: dict[str, float], weights: CriteriaWeights) -> float:
    """Normalized simple additive weighting over the criteria."""
    w = weights.as_dict()
    wsum = sum(w.values()) or 1.0
    return sum(scores[k] * w[k] for k in CRITERIA) / wsum


def recommend(
    concept: FieldConcept,
    weights: CriteriaWeights | None = None,
    thresholds: Thresholds | None = None,
    top_n: int | None = None,
) -> list[ScoredConcept]:
    """Rank feasible development concepts for a field.

    Args:
        concept: Input parameters (a :class:`FieldConcept`; need not be complete).
        weights: Criteria weights; defaults to :class:`CriteriaWeights`.
        thresholds: Decision thresholds; defaults to :class:`Thresholds`.
        top_n: If given, return only the top N concepts.

    Returns:
        Concepts ranked by descending ``total_score`` (ties broken by concept
        name for determinism). Empty only if no concept is feasible.
    """
    weights = weights or CriteriaWeights()
    th = thresholds or Thresholds()

    candidates = feasible_concepts(concept, th)
    tieback_pref = _tieback_attractive(concept, th)

    scored = [
        _score_concept(cc, concept, th, weights, tieback_pref) for cc in candidates
    ]
    scored.sort(key=lambda s: (-s.total_score, s.concept_type.value))
    return scored[:top_n] if top_n else scored
