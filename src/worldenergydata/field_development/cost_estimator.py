# ABOUTME: Parametric per-concept CAPEX/OPEX estimator (issue #643, epic #567).
# ABOUTME: Layers concept-specific adjustments onto the field-level FDAS economics.
"""
worldenergydata.field_development.cost_estimator
================================================

The FDAS economics in :mod:`worldenergydata.field_development.integrations` are
**depth-driven and field-level**: at a given water depth every concept inherits
the same dev-system CAPEX (``dry`` / ``subsea15`` / ``subsea20``). That is the
right altitude for a sanity-check NPV, but a Concept-Select comparison needs to
*separate* the candidates — a subsea tieback to a host is not the same cost as a
dedicated FPSO at the same depth.

This module adds that separation **by reuse, not re-derivation**:

* the **base CAPEX** is :func:`integrations.estimate_economics` (FDAS host +
  per-well assumptions) — never recomputed here;
* the **base annual OPEX** is the FDAS ``FIXED_OPEX_MM_PER_YEAR`` assumption for
  the same depth-classified dev system;
* the **per-concept multipliers** are derived from the same priors the
  recommendation engine already scores on — :data:`recommendation._CONCEPT_PROFILES`
  (relative CAPEX/OPEX), :func:`recommendation._depth_fit` /
  :data:`recommendation.DEPTH_SWEET_M` (the depth-fit penalty), and
  :class:`recommendation.Thresholds` (the flow-assurance tieback threshold, the
  single source of truth for the long-offset penalty).

Every multiplier is a **qualitative engineering prior** (Concept-Select / AACE
Class 5 fidelity), documented inline with its rationale — not an empirically
calibrated cost model. Costs round to 0.1 MM. If FDAS cannot classify a dev
system (e.g. unknown water depth) the estimator **degrades gracefully**: it
returns an estimate carrying a ``note`` rather than raising.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from worldenergydata.field_development.enums import ConceptType
from worldenergydata.field_development.integrations import (
    dev_system_for,
    estimate_economics,
)
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.recommendation import (
    _CONCEPT_PROFILES,
    ScoredConcept,
    Thresholds,
    _depth_fit,
)

# --------------------------------------------------------------------------- #
# Tunable priors (all qualitative Concept-Select-fidelity factors)
# --------------------------------------------------------------------------- #
# The concept CAPEX prior in ``_CONCEPT_PROFILES`` is in [0, 1] where 1.0 =
# *most favourable* (cheapest). We map it to a multiplier centred on the median
# prior (0.5): a cheaper-than-median concept pulls CAPEX below the field base, a
# costlier one pushes it above. The span is tuned so the spread of the real
# priors yields the acceptance-criterion gap — a subsea tieback (prior 0.95)
# lands ~10% below an FPSO (prior 0.40) at the same depth (within the 5–15% band).
_CAPEX_PRIOR_SPAN = 0.20
_CAPEX_PRIOR_MID = 0.5

# Depth-fit penalty: a concept used outside its sweet-spot band (per
# ``DEPTH_SWEET_M``, surfaced via ``_depth_fit`` in [0, 1]) costs more — hull
# size, mooring, or riser design must stretch beyond the type's comfortable
# envelope. A total miss (fit 0.0) adds up to +30% CAPEX.
_DEPTH_PENALTY_SPAN = 0.30

# Long-tieback flow-assurance penalty: beyond the ``Thresholds`` flow-assurance
# warning distance (~32 km / 20 mi) insulation, heating, and boosting drive
# subsea CAPEX up. Modelled as +0.5%/km past the threshold, capped at +25% so a
# very long offset cannot run away. The threshold itself is *not* duplicated —
# it is read from ``Thresholds`` (the source of truth).
_TIEBACK_PENALTY_PER_KM = 0.005
_TIEBACK_PENALTY_CAP = 0.25

# Final CAPEX adjustment is clamped to this defensive envelope.
_CAPEX_ADJ_MIN = 0.80
_CAPEX_ADJ_MAX = 1.50

# OPEX concept prior maps the same way (1.0 = cheapest to operate). A wider span
# than CAPEX reflects how much intervention/manning philosophy varies by concept
# (e.g. a subsea-to-shore tieback vs an FLNG).
_OPEX_PRIOR_SPAN = 0.40
_OPEX_PRIOR_MID = 0.5

# OPEX scales with field size: more reserves means more wells, throughput, and
# intervention exposure. Scaled by sqrt of reserves vs a 100-MMboe reference so
# the factor grows sub-linearly, clamped to keep marginal/giant fields sane.
_OPEX_REF_RESERVES_MMBOE = 100.0
_OPEX_RESERVES_MIN = 0.60
_OPEX_RESERVES_MAX = 1.70

# Final OPEX factor envelope (issue acceptance: ~[0.5, 2.0]).
_OPEX_FACTOR_MIN = 0.50
_OPEX_FACTOR_MAX = 2.00

# Default field life (years) used only to rank a portfolio by lifecycle cost when
# the field life is not supplied.
_DEFAULT_FIELD_LIFE_YEARS = 20.0

# Concepts whose CAPEX carries the long-offset flow-assurance penalty — i.e. the
# ones that actually flow back to a remote host/shore.
_TIEBACK_CONCEPTS = {ConceptType.SUBSEA_TIEBACK, ConceptType.SUBSEA_TO_SHORE}


@dataclass
class PerConceptCostEstimate:
    """A transparent per-concept CAPEX/OPEX estimate at Concept-Select fidelity.

    ``capex_mm`` / ``annual_opex_mm`` are ``None`` when the underlying FDAS
    economics could not be classified (graceful degrade); ``note`` then explains
    why. ``capex_adjustment`` and ``opex_factor`` are the multipliers applied to
    the FDAS field-level base; ``depth_fit_penalty`` and ``tieback_penalty_pct``
    expose the two CAPEX penalty components so they can be audited.
    """

    concept_type: ConceptType
    capex_mm: Optional[float] = None
    annual_opex_mm: Optional[float] = None
    capex_adjustment: float = 1.0
    opex_factor: float = 1.0
    depth_fit_penalty: float = 0.0  # fractional CAPEX increase from depth misfit
    tieback_penalty_pct: float = 0.0  # CAPEX increase (%) from long-offset
    dev_system: Optional[str] = None
    rationale: list[str] = field(default_factory=list)
    note: str = ""


# --------------------------------------------------------------------------- #
# CAPEX adjustment
# --------------------------------------------------------------------------- #
def _concept_capex_mult(concept: ConceptType) -> float:
    """Multiplier from the concept's relative-CAPEX prior (1.0 = field median)."""
    score = _CONCEPT_PROFILES[concept]["capex"]
    return 1.0 + _CAPEX_PRIOR_SPAN * (_CAPEX_PRIOR_MID - score)


def _depth_capex_penalty(depth_fit: float) -> float:
    """Fractional CAPEX increase for using a concept outside its depth band."""
    clamped = max(0.0, min(1.0, depth_fit))
    return _DEPTH_PENALTY_SPAN * (1.0 - clamped)


def _tieback_capex_penalty(tieback_km: Optional[float]) -> float:
    """Fractional CAPEX increase for a tieback beyond the flow-assurance limit.

    The threshold is read from :class:`Thresholds` so this stays consistent with
    the recommendation engine's flow-assurance warning rather than duplicating
    the 32 km constant.
    """
    if tieback_km is None:
        return 0.0
    warn_km = Thresholds().flow_assurance_warn_km
    if tieback_km <= warn_km:
        return 0.0
    return min(_TIEBACK_PENALTY_CAP, _TIEBACK_PENALTY_PER_KM * (tieback_km - warn_km))


def capex_adjustment_for(
    concept: ConceptType,
    depth_fit: float = 1.0,
    tieback_km: Optional[float] = None,
) -> float:
    """Per-concept CAPEX multiplier on the FDAS field-level base (~[0.8, 1.5]).

    Combines three documented priors multiplicatively: the concept's relative
    CAPEX prior, the depth-fit penalty, and the long-tieback flow-assurance
    penalty. The result is clamped to a defensive envelope.

    Args:
        concept: The development concept being priced.
        depth_fit: Depth-fit score in [0, 1] from ``recommendation._depth_fit``.
        tieback_km: Host offset for tieback concepts; ``None`` to skip.
    """
    mult = _concept_capex_mult(concept)
    mult *= 1.0 + _depth_capex_penalty(depth_fit)
    mult *= 1.0 + _tieback_capex_penalty(tieback_km)
    return round(max(_CAPEX_ADJ_MIN, min(_CAPEX_ADJ_MAX, mult)), 4)


# --------------------------------------------------------------------------- #
# OPEX factor
# --------------------------------------------------------------------------- #
def _reserves_opex_scale(reserves_mmboe: Optional[float]) -> float:
    """Sub-linear (sqrt) OPEX scaling vs a reference field size."""
    if not reserves_mmboe or reserves_mmboe <= 0:
        return 1.0
    raw = math.sqrt(reserves_mmboe / _OPEX_REF_RESERVES_MMBOE)
    return max(_OPEX_RESERVES_MIN, min(_OPEX_RESERVES_MAX, raw))


def opex_factor_for(
    concept: ConceptType, reserves_mmboe: Optional[float] = None
) -> float:
    """Per-concept annual-OPEX multiplier on the FDAS fixed-OPEX base (~[0.5, 2]).

    Combines the concept's relative-OPEX prior with a reserves-based size scale,
    clamped to a defensive envelope.
    """
    score = _CONCEPT_PROFILES[concept]["opex"]
    concept_mult = 1.0 + _OPEX_PRIOR_SPAN * (_OPEX_PRIOR_MID - score)
    factor = concept_mult * _reserves_opex_scale(reserves_mmboe)
    return round(max(_OPEX_FACTOR_MIN, min(_OPEX_FACTOR_MAX, factor)), 4)


def _base_annual_opex_mm(concept: FieldConcept) -> Optional[float]:
    """FDAS fixed annual OPEX for the depth-classified dev system; None if N/A."""
    sysname = dev_system_for(concept)
    if sysname in (None, "unknown"):
        return None
    try:
        from worldenergydata.fdas.core.config import AssumptionsManager
    except Exception:  # pragma: no cover - defensive, FDAS optional
        return None
    return AssumptionsManager().get(sysname, "FIXED_OPEX_MM_PER_YEAR", 0.0)


# --------------------------------------------------------------------------- #
# Top-level estimate
# --------------------------------------------------------------------------- #
def estimate_per_concept_costs(
    concept: FieldConcept, scored: ScoredConcept
) -> PerConceptCostEstimate:
    """Estimate CAPEX/OPEX for one scored concept against a field's parameters.

    Reuses :func:`integrations.estimate_economics` for the field-level CAPEX base
    and the FDAS fixed-OPEX assumption for the base annual OPEX, then applies the
    per-concept :func:`capex_adjustment_for` and :func:`opex_factor_for`
    multipliers. Degrades gracefully (capex/opex ``None`` + ``note``) when FDAS
    cannot classify a dev system.
    """
    ct = scored.concept_type
    eco = estimate_economics(concept)

    depth_fit = _depth_fit(ct, concept.water_depth_m)
    tieback_km = concept.distance_to_host_km if ct in _TIEBACK_CONCEPTS else None
    capex_adj = capex_adjustment_for(ct, depth_fit, tieback_km)
    opex_factor = opex_factor_for(ct, concept.recoverable_reserves_mmboe)

    depth_pen = _depth_capex_penalty(depth_fit)
    tieback_pen_pct = round(_tieback_capex_penalty(tieback_km) * 100.0, 1)

    est = PerConceptCostEstimate(
        concept_type=ct,
        capex_adjustment=capex_adj,
        opex_factor=opex_factor,
        depth_fit_penalty=round(depth_pen, 4),
        tieback_penalty_pct=tieback_pen_pct,
        dev_system=eco.dev_system,
    )

    # --- CAPEX (graceful degrade if FDAS yielded no field-level CAPEX) ---
    if eco.capex_mm is None:
        est.note = (
            eco.note or "field-level CAPEX unavailable — per-concept CAPEX skipped"
        )
    else:
        est.capex_mm = round(eco.capex_mm * capex_adj, 1)
        est.rationale.append(
            f"base CAPEX {eco.capex_mm:g} $MM ({eco.dev_system}) "
            f"× {capex_adj:g} concept adjustment = {est.capex_mm:g} $MM"
        )
        if depth_pen > 0:
            est.rationale.append(
                f"depth fit {depth_fit:.2f} adds {depth_pen * 100:.1f}% CAPEX "
                f"(outside the {ct.value} sweet-spot band)"
            )
        if tieback_pen_pct > 0:
            est.rationale.append(
                f"tieback {tieback_km:g} km exceeds the "
                f"{Thresholds().flow_assurance_warn_km:g} km flow-assurance "
                f"threshold, adding {tieback_pen_pct:.1f}% CAPEX"
            )

    # --- OPEX (independent graceful degrade) ---
    base_opex = _base_annual_opex_mm(concept)
    if base_opex is None:
        if not est.note:
            est.note = "dev system unclassified — annual OPEX skipped"
    else:
        est.annual_opex_mm = round(base_opex * opex_factor, 1)
        res = concept.recoverable_reserves_mmboe
        est.rationale.append(
            f"base OPEX {base_opex:g} $MM/yr × {opex_factor:g} factor"
            + (f" (reserves {res:g} MMboe)" if res else "")
            + f" = {est.annual_opex_mm:g} $MM/yr"
        )

    return est


def _lifecycle_cost(est: PerConceptCostEstimate, field_life_years: float) -> float:
    """Rough lifecycle cost (CAPEX + OPEX×life) for portfolio ranking; inf if N/A."""
    if est.capex_mm is None:
        return float("inf")
    life = field_life_years or _DEFAULT_FIELD_LIFE_YEARS
    return est.capex_mm + (est.annual_opex_mm or 0.0) * life


def estimate_field_cost_portfolio(
    concept: FieldConcept, scored_concepts: list[ScoredConcept]
) -> dict[ConceptType, PerConceptCostEstimate]:
    """Cost every scored concept for a field, ordered by ascending lifecycle cost.

    Concepts whose economics could not be estimated (no CAPEX) sort last. The
    result is keyed by :class:`ConceptType` for O(1) lookup while preserving the
    cheapest-first ordering (Python dicts are insertion-ordered).
    """
    life = concept.field_life_years or _DEFAULT_FIELD_LIFE_YEARS
    estimates = {
        sc.concept_type: estimate_per_concept_costs(concept, sc)
        for sc in scored_concepts
    }
    ordered = sorted(estimates.items(), key=lambda kv: _lifecycle_cost(kv[1], life))
    return dict(ordered)
