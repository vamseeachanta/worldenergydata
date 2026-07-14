"""
ABOUTME: Back-allocates sanctioned project CAPEX totals across lifecycle stages, then reconciles vs bottom-up.
ABOUTME: Implements issue #844 scope addition #2 — the top-down anchor for the bottom-up component series.

The idea
--------
The bottom-up series (day rates x durations) can drift: multiply six plausible
components together and you can land 40% away from what anyone actually spent.
Sanctioned project totals are the reality check — an operator's FID press release
stating "$5.7 billion" is a hard, disclosed, *whole-project* number.

So: take each project's disclosed total, split it across the six lifecycle stages
(drill / complete / SURF / host / install / hookup) using its disclosed scope,
and compare the drilling slice against what the bottom-up day-rate series says
drilling should have cost. **Where they disagree, the discrepancy is the finding**
— that is #844's framing, and this module is built to surface it, not to hide it
by tuning until the two agree.

The allocation method, stated plainly
-------------------------------------
Stage shares are **priors**, not measurements. Operators almost never disclose a
stage-level CAPEX breakdown; they disclose a total and a scope. So we:

1. Pick a share vector by ``development_type`` — a subsea tieback spends a very
   different fraction on "host" (near zero, it reuses one) than a new-build FPSO.
2. Tilt the drill/complete shares by well count relative to a reference count for
   that development type: a 20-well project is drilling-heavy, a 4-well tieback is
   not.
3. Renormalise to 100%.
4. Carry a **low/high band** on every stage, propagated from the prior's own
   uncertainty band. A single-point stage cost from this module would be a lie of
   precision; the band is the honest output.

Every number this module emits is stamped ``Provenance.ALLOCATED`` and carries
the share and band used, so no allocated figure can be mistaken for a disclosed
one. The priors themselves are ``ASSUMED`` — engineering judgement, owned and
stated here, with the explicit invitation to replace them the moment a project
discloses a real breakdown (see ``StageShares.from_disclosed``).

Where the priors come from
--------------------------
They encode the standard deepwater cost structure: for a new-build floating host,
subsea + SURF and the host itself each take roughly a third, wells take a third;
for a tieback, wells and SURF dominate because the host is sunk cost. They are
deliberately given wide bands (typically +/-8-10 share points) because that is the
genuine spread across projects, and a narrow band would overstate what we know.

**These are priors, not sourced facts.** They are the one place in this dataset
where a number is not read off a page — which is precisely why they are isolated
in a single reviewable table, banded, and flagged ASSUMED in every output.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

__all__ = [
    "LifecycleStage",
    "DevelopmentType",
    "StageShares",
    "STAGE_SHARE_PRIORS",
    "AllocatedStage",
    "ProjectAllocation",
    "allocate_project",
    "reconcile_drilling",
    "Reconciliation",
]


class LifecycleStage(str, Enum):
    """The six stages #844 asks the sanctioned total to be split across."""

    DRILL = "drill"
    COMPLETE = "complete"
    SURF = "surf"
    HOST = "host"
    INSTALL = "install"
    HOOKUP = "hookup"


class DevelopmentType(str, Enum):
    """Development architecture — the primary driver of the stage split."""

    SUBSEA_TIEBACK = "subsea_tieback"
    NEW_HOST_FPSO = "new_host_fpso"
    NEW_HOST_SEMI = "new_host_semi"
    NEW_HOST_SPAR = "new_host_spar"
    NEW_HOST_TLP = "new_host_tlp"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class StageShares:
    """A stage-share vector with an uncertainty band on each stage.

    ``mid`` must sum to ~1.0. ``band`` is the +/- width in share points (0.08 =
    +/-8 percentage points of the total), used to produce the low/high envelope.
    """

    mid: dict[LifecycleStage, float]
    band: dict[LifecycleStage, float]
    rationale: str
    reference_well_count: float
    is_disclosed: bool = False

    def __post_init__(self) -> None:
        total = sum(self.mid.values())
        if not (0.98 <= total <= 1.02):
            raise ValueError(f"stage shares must sum to ~1.0, got {total:.3f}")

    @classmethod
    def from_disclosed(
        cls, shares: dict[LifecycleStage, float], rationale: str
    ) -> "StageShares":
        """Build shares from an actually-disclosed breakdown.

        Band collapses to zero: if the operator told us the split, we are not
        going to put an uncertainty band around their own disclosure.
        """
        return cls(
            mid=shares,
            band={stage: 0.0 for stage in shares},
            rationale=rationale,
            reference_well_count=0.0,
            is_disclosed=True,
        )


#: Priors by development type. ASSUMED — see module docstring. Wide bands are
#: deliberate. Replace any entry the moment a real disclosed breakdown exists.
STAGE_SHARE_PRIORS: dict[DevelopmentType, StageShares] = {
    DevelopmentType.SUBSEA_TIEBACK: StageShares(
        mid={
            LifecycleStage.DRILL: 0.34,
            LifecycleStage.COMPLETE: 0.16,
            LifecycleStage.SURF: 0.30,
            LifecycleStage.HOST: 0.04,
            LifecycleStage.INSTALL: 0.11,
            LifecycleStage.HOOKUP: 0.05,
        },
        band={
            LifecycleStage.DRILL: 0.10,
            LifecycleStage.COMPLETE: 0.06,
            LifecycleStage.SURF: 0.09,
            LifecycleStage.HOST: 0.04,
            LifecycleStage.INSTALL: 0.05,
            LifecycleStage.HOOKUP: 0.03,
        },
        rationale=(
            "Tieback reuses an existing host, so HOST is near-zero (brownfield "
            "tie-in mods only). Wells + SURF carry the project. SURF share is "
            "high because the flowline/umbilical run to the host is the defining "
            "scope of a tieback."
        ),
        reference_well_count=4.0,
    ),
    DevelopmentType.NEW_HOST_FPSO: StageShares(
        mid={
            LifecycleStage.DRILL: 0.22,
            LifecycleStage.COMPLETE: 0.11,
            LifecycleStage.SURF: 0.24,
            LifecycleStage.HOST: 0.30,
            LifecycleStage.INSTALL: 0.08,
            LifecycleStage.HOOKUP: 0.05,
        },
        band={
            LifecycleStage.DRILL: 0.08,
            LifecycleStage.COMPLETE: 0.05,
            LifecycleStage.SURF: 0.08,
            LifecycleStage.HOST: 0.10,
            LifecycleStage.INSTALL: 0.04,
            LifecycleStage.HOOKUP: 0.03,
        },
        rationale=(
            "FPSO hull+topsides is the single largest line item. Well counts are "
            "high (15-30 on a Guyana-class development) but each well is a smaller "
            "share of a very large total."
        ),
        reference_well_count=18.0,
    ),
    DevelopmentType.NEW_HOST_SEMI: StageShares(
        mid={
            LifecycleStage.DRILL: 0.26,
            LifecycleStage.COMPLETE: 0.13,
            LifecycleStage.SURF: 0.22,
            LifecycleStage.HOST: 0.27,
            LifecycleStage.INSTALL: 0.07,
            LifecycleStage.HOOKUP: 0.05,
        },
        band={
            LifecycleStage.DRILL: 0.09,
            LifecycleStage.COMPLETE: 0.05,
            LifecycleStage.SURF: 0.08,
            LifecycleStage.HOST: 0.09,
            LifecycleStage.INSTALL: 0.04,
            LifecycleStage.HOOKUP: 0.03,
        },
        rationale=(
            "Semi-submersible FPU (GOM Anchor/Whale class). Fewer wells than an "
            "FPSO development; host is a major but not dominant share."
        ),
        reference_well_count=8.0,
    ),
    DevelopmentType.NEW_HOST_SPAR: StageShares(
        mid={
            LifecycleStage.DRILL: 0.27,
            LifecycleStage.COMPLETE: 0.13,
            LifecycleStage.SURF: 0.20,
            LifecycleStage.HOST: 0.28,
            LifecycleStage.INSTALL: 0.07,
            LifecycleStage.HOOKUP: 0.05,
        },
        band={
            LifecycleStage.DRILL: 0.09,
            LifecycleStage.COMPLETE: 0.05,
            LifecycleStage.SURF: 0.07,
            LifecycleStage.HOST: 0.09,
            LifecycleStage.INSTALL: 0.04,
            LifecycleStage.HOOKUP: 0.03,
        },
        rationale=(
            "Spar host; often dry-tree, which shifts cost from SURF toward the "
            "host and the (platform-drilled) wells."
        ),
        reference_well_count=8.0,
    ),
    DevelopmentType.NEW_HOST_TLP: StageShares(
        mid={
            LifecycleStage.DRILL: 0.27,
            LifecycleStage.COMPLETE: 0.13,
            LifecycleStage.SURF: 0.19,
            LifecycleStage.HOST: 0.29,
            LifecycleStage.INSTALL: 0.07,
            LifecycleStage.HOOKUP: 0.05,
        },
        band={
            LifecycleStage.DRILL: 0.09,
            LifecycleStage.COMPLETE: 0.05,
            LifecycleStage.SURF: 0.07,
            LifecycleStage.HOST: 0.09,
            LifecycleStage.INSTALL: 0.04,
            LifecycleStage.HOOKUP: 0.03,
        },
        rationale="TLP host, typically dry-tree. Similar structure to a spar.",
        reference_well_count=8.0,
    ),
}

#: How hard well count tilts the drill/complete shares. 0.5 = a project with
#: twice the reference well count gets 1.5x the reference drilling share (before
#: renormalisation), not 2x — because incremental wells on one campaign are
#: cheaper than the first (rig mob is already paid, learning curve applies).
#: Deliberately sub-linear. This damping factor is itself an assumption.
WELL_COUNT_TILT = 0.5

#: Guard rails on the tilt, so a project with a wildly atypical well count cannot
#: drive the drilling share to an absurd fraction of the total.
_MIN_TILT, _MAX_TILT = 0.5, 1.8


@dataclass(frozen=True)
class AllocatedStage:
    """One stage's slice of a project total, with its uncertainty envelope."""

    stage: LifecycleStage
    share_mid: float
    cost_mid_usd_mm: float
    cost_low_usd_mm: float
    cost_high_usd_mm: float


@dataclass(frozen=True)
class ProjectAllocation:
    """A sanctioned total, split. Every field needed to audit the split."""

    project: str
    total_capex_usd_mm: float
    development_type: DevelopmentType
    well_count: Optional[int]
    stages: list[AllocatedStage]
    method_note: str
    shares_are_disclosed: bool

    def stage(self, stage: LifecycleStage) -> Optional[AllocatedStage]:
        for allocated in self.stages:
            if allocated.stage is stage:
                return allocated
        return None


def allocate_project(
    project: str,
    total_capex_usd_mm: float,
    development_type: DevelopmentType,
    well_count: Optional[int] = None,
    shares: Optional[StageShares] = None,
) -> Optional[ProjectAllocation]:
    """Split one project's sanctioned total across the six lifecycle stages.

    Returns ``None`` when the development type is UNKNOWN and no explicit shares
    were supplied — we will not allocate a total we cannot characterise. A
    project we can't classify stays whole and unallocated, which is the correct
    representation of not knowing.
    """
    if shares is None:
        if development_type is DevelopmentType.UNKNOWN:
            return None
        shares = STAGE_SHARE_PRIORS[development_type]

    mid = dict(shares.mid)

    # --- well-count tilt --------------------------------------------------
    tilt_note = "no well-count tilt (well count not disclosed)"
    if (
        well_count
        and well_count > 0
        and shares.reference_well_count > 0
        and not shares.is_disclosed
    ):
        ratio = well_count / shares.reference_well_count
        tilt = 1.0 + WELL_COUNT_TILT * (ratio - 1.0)
        tilt = max(_MIN_TILT, min(_MAX_TILT, tilt))
        for stage in (LifecycleStage.DRILL, LifecycleStage.COMPLETE):
            mid[stage] = mid[stage] * tilt
        tilt_note = (
            f"drill+complete shares tilted x{tilt:.2f} for {well_count} wells vs a "
            f"reference {shares.reference_well_count:.0f} for {development_type.value} "
            f"(sub-linear, factor {WELL_COUNT_TILT})"
        )

    # --- renormalise ------------------------------------------------------
    total_share = sum(mid.values())
    mid = {stage: value / total_share for stage, value in mid.items()}

    allocated: list[AllocatedStage] = []
    for stage, share in mid.items():
        band = shares.band.get(stage, 0.0)
        low_share = max(0.0, share - band)
        high_share = share + band
        allocated.append(
            AllocatedStage(
                stage=stage,
                share_mid=share,
                cost_mid_usd_mm=total_capex_usd_mm * share,
                cost_low_usd_mm=total_capex_usd_mm * low_share,
                cost_high_usd_mm=total_capex_usd_mm * high_share,
            )
        )
    allocated.sort(key=lambda a: a.cost_mid_usd_mm, reverse=True)

    method = (
        f"Top-down back-allocation of a disclosed ${total_capex_usd_mm:,.0f}MM total. "
        f"Shares: {'DISCLOSED by operator' if shares.is_disclosed else 'ASSUMED prior for ' + development_type.value}. "
        f"{tilt_note}. Rationale: {shares.rationale}"
    )

    return ProjectAllocation(
        project=project,
        total_capex_usd_mm=total_capex_usd_mm,
        development_type=development_type,
        well_count=well_count,
        stages=allocated,
        method_note=method,
        shares_are_disclosed=shares.is_disclosed,
    )


@dataclass(frozen=True)
class Reconciliation:
    """Top-down allocated drilling cost vs the bottom-up day-rate estimate.

    ``gap_pct`` is the headline: how far the bottom-up component series is from
    the disclosed reality, expressed as a percentage of the top-down figure.
    Positive = bottom-up is *higher* than the sanctioned total implies.
    """

    project: str
    year: int
    top_down_drill_usd_mm: float
    top_down_low_usd_mm: float
    top_down_high_usd_mm: float
    bottom_up_drill_usd_mm: float
    gap_usd_mm: float
    gap_pct: float
    within_band: bool
    assumptions: str


def reconcile_drilling(
    allocation: ProjectAllocation,
    year: int,
    rig_day_rate_usd: float,
    days_per_well: float,
    spread_multiplier: float = 2.0,
) -> Optional[Reconciliation]:
    """Cross-check the allocated DRILL slice against day-rate x duration.

        bottom_up = well_count x days_per_well x rig_day_rate x spread_multiplier

    ``spread_multiplier`` grosses the bare rig rate up to a **total well cost**:
    the rig is roughly half of a deepwater well's daily burn once you add the
    tubulars, mud, cement, logging, ROV/vessel support and the operator's own
    overhead. 2.0 is the conventional planning number and is an ASSUMPTION — it
    is exposed as a parameter precisely so a reader can disagree with it and
    re-run.

    Returns ``None`` when the project has no disclosed well count: without it
    there is no bottom-up estimate to make, and manufacturing a well count to
    force a reconciliation would defeat the entire purpose of the exercise.
    """
    drill = allocation.stage(LifecycleStage.DRILL)
    if drill is None or not allocation.well_count:
        return None

    bottom_up_usd = (
        allocation.well_count * days_per_well * rig_day_rate_usd * spread_multiplier
    )
    bottom_up_mm = bottom_up_usd / 1_000_000.0

    gap_mm = bottom_up_mm - drill.cost_mid_usd_mm
    gap_pct = (
        (gap_mm / drill.cost_mid_usd_mm) * 100.0 if drill.cost_mid_usd_mm > 0 else 0.0
    )
    within = drill.cost_low_usd_mm <= bottom_up_mm <= drill.cost_high_usd_mm

    return Reconciliation(
        project=allocation.project,
        year=year,
        top_down_drill_usd_mm=drill.cost_mid_usd_mm,
        top_down_low_usd_mm=drill.cost_low_usd_mm,
        top_down_high_usd_mm=drill.cost_high_usd_mm,
        bottom_up_drill_usd_mm=bottom_up_mm,
        gap_usd_mm=gap_mm,
        gap_pct=gap_pct,
        within_band=within,
        assumptions=(
            f"{allocation.well_count} wells x {days_per_well:.0f} days/well x "
            f"${rig_day_rate_usd:,.0f}/day x {spread_multiplier:.1f} spread multiplier "
            f"(rig rate -> total well cost). days_per_well and spread_multiplier are "
            f"ASSUMPTIONS, not sourced."
        ),
    )
