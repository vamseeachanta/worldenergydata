# ABOUTME: E5 (#1028) — reconciliation harness: cross-check the four cost tables and score the A1 stage-share priors.
# ABOUTME: award-sum vs gross coverage, partner-net/interest vs gross, award-anchored stage shares vs priors, outturn multipliers.
"""
reconciliation
==============

The payoff of the hardening epic (#1023): four *independent* views of the same
project cost, cross-checked, with the residuals reported as findings.

1. **Coverage** — sum of capex-comparable valued awards vs the sanctioned gross.
   How much of the top-down total do the bottom-up awards actually account for?
2. **Partner check** — each partner's disclosed net share ÷ its working interest
   vs the gross. Guyana nets exclude the FPSO, so this is a *loose* check with a
   stated tolerance, not an equality.
3. **Stage anchor** — where an award maps to a lifecycle stage AND carries a
   value, the award-implied stage share (award / gross) is compared to the A1
   prior's band. This is the direct evidence for/against decision A1: an anchor
   inside the band *corroborates* the prior; one outside *challenges* it.
4. **Outturn** — the sanction→final multiplier from the revision trails. States
   how far FID figures actually run from outturn.

Nothing here invents a number. `not_public`, `lease_contract`, `midstream` and
`combined`-without-a-low-bound awards are excluded from the capex sums by
construction (see ``_capex_comparable``), so coverage is never inflated by a
lease value or a third-party pipeline.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from worldenergydata.cost.timeseries.back_allocation import (
    STAGE_SHARE_PRIORS,
    DevelopmentType,
    LifecycleStage,
)

# Award asset class -> the lifecycle stage it belongs to. `other` (services,
# mooring, export, O&M) has no clean single stage and is left unmapped — it is
# counted in coverage but never used to anchor a stage share.
ASSET_TO_STAGE: dict[str, LifecycleStage] = {
    "drilling_rig": LifecycleStage.DRILL,
    "sps": LifecycleStage.COMPLETE,  # subsea production system = subsea completions/trees
    "surf": LifecycleStage.SURF,
    "production_hub": LifecycleStage.HOST,
    "installation": LifecycleStage.INSTALL,
}

# Award VALUE_BASIS values that represent a real, capex-comparable project cost.
# Everything else (not_public, lease_contract, midstream, combined) is excluded.
_CAPEX_COMPARABLE = {"point", "band", "backlog"}


def _read(curated: Path, name: str) -> list[dict]:
    with open(curated / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _num(s: str) -> Optional[float]:
    s = (s or "").strip()
    return float(s) if s else None


def _capex_comparable_low(award: dict) -> Optional[float]:
    """The conservative (low-bound) capex-comparable value of an award, or None.

    Bands use their LOW bound (a band is a range; crediting the top would
    over-state coverage). Excluded bases return None.
    """
    if award["VALUE_BASIS"] not in _CAPEX_COMPARABLE:
        return None
    return _num(award["VALUE_LOW_MM"])


# ---------------------------------------------------------------------------
# 1. Coverage
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Coverage:
    project: str
    gross_mm: float
    valued_award_low_mm: float
    coverage_low_pct: float
    n_valued_awards: int
    n_not_public_awards: int


def compute_coverage(curated: Path) -> list[Coverage]:
    sanctioned = {
        r["PROJECT"]: _num(r["SANCTIONED_CAPEX_USD_MM"])
        for r in _read(curated, "sanctioned_projects.csv")
    }
    awards = _read(curated, "contract_awards.csv")
    by_project: dict[str, list[dict]] = {}
    for a in awards:
        by_project.setdefault(a["PROJECT"], []).append(a)

    out: list[Coverage] = []
    for project, rows in by_project.items():
        gross = sanctioned.get(project)
        if not gross:
            continue
        low_sum = sum(v for a in rows if (v := _capex_comparable_low(a)) is not None)
        n_valued = sum(1 for a in rows if _capex_comparable_low(a) is not None)
        n_np = sum(1 for a in rows if a["VALUE_BASIS"] == "not_public")
        out.append(
            Coverage(
                project=project,
                gross_mm=gross,
                valued_award_low_mm=low_sum,
                coverage_low_pct=100.0 * low_sum / gross,
                n_valued_awards=n_valued,
                n_not_public_awards=n_np,
            )
        )
    return sorted(out, key=lambda c: c.coverage_low_pct, reverse=True)


# ---------------------------------------------------------------------------
# 2. Partner-net checks
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PartnerCheck:
    project: str
    company: str
    interest_pct: float
    net_mm: float
    implied_gross_mm: float
    disclosed_gross_mm: Optional[float]
    ratio: Optional[float]  # implied_gross / disclosed_gross
    note: str


def compute_partner_checks(curated: Path) -> list[PartnerCheck]:
    stmts = _read(curated, "project_cost_statements.csv")
    gross_by_project: dict[str, float] = {}
    for s in stmts:
        if s["FIGURE_TYPE"] == "gross_capex":
            gross_by_project[s["PROJECT"]] = _num(s["VALUE_MM"])

    out: list[PartnerCheck] = []
    for s in stmts:
        if s["FIGURE_TYPE"] != "net_share" or not s["INTEREST_PCT"]:
            continue
        net = _num(s["VALUE_MM"])
        pct = _num(s["INTEREST_PCT"])
        if not net or not pct:
            continue
        implied = net / (pct / 100.0)
        gross = gross_by_project.get(s["PROJECT"])
        ratio = (implied / gross) if gross else None
        note = ""
        if gross and ratio is not None:
            if ratio < 0.9:
                note = "implied below gross — net likely excludes a scope element (e.g. FPSO)"
            elif ratio > 1.1:
                note = "implied above gross — check interest or base"
            else:
                note = "implied ~= gross (within 10%)"
        out.append(
            PartnerCheck(
                project=s["PROJECT"],
                company=s["COMPANY"],
                interest_pct=pct,
                net_mm=net,
                implied_gross_mm=implied,
                disclosed_gross_mm=gross,
                ratio=ratio,
                note=note,
            )
        )
    return out


# ---------------------------------------------------------------------------
# 3. Stage anchors — the direct A1 evidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageAnchor:
    project: str
    dev_type: str
    stage: str
    award_low_mm: float
    gross_mm: float
    implied_share: float  # award_low / gross
    prior_mid: float
    prior_low: float
    prior_high: float
    verdict: str  # in_band | below_band | above_band
    is_lower_bound: bool  # True when the award is only PART of the stage
    contractor: str
    note: str


def _anchor_is_lower_bound(award: dict) -> bool:
    """Does this award under-represent its stage's full cost?

    A ``below_band`` verdict only *challenges* the A1 prior when the award is
    the stage's full scope. It is a mere floor when:

    - it is a band low-bound (the true value is somewhere in the range);
    - it is a single drilling rig's backlog (one of several rigs on the job);
    - it is an FPSO buyout (the hull purchase price — a fraction of the full HOST
      stage, which also carries topsides fab, integration and lease-capitalized
      cost).

    A ``surf`` or ``complete`` award booked as a ``point`` value is the full
    EPCI scope, so it is genuine evidence and returns False.
    """
    if award["VALUE_BASIS"] == "band":
        return True
    if award["ASSET_CLASS"] in ("drilling_rig", "production_hub"):
        return True
    return False


def compute_stage_anchors(curated: Path) -> list[StageAnchor]:
    sanctioned = {r["PROJECT"]: r for r in _read(curated, "sanctioned_projects.csv")}
    awards = _read(curated, "contract_awards.csv")

    out: list[StageAnchor] = []
    for a in awards:
        low = _capex_comparable_low(a)
        stage = ASSET_TO_STAGE.get(a["ASSET_CLASS"])
        if low is None or stage is None:
            continue
        srow = sanctioned.get(a["PROJECT"])
        if not srow:
            continue
        gross = _num(srow["SANCTIONED_CAPEX_USD_MM"])
        if not gross:
            continue
        try:
            dev = DevelopmentType(srow["DEVELOPMENT_TYPE"])
        except ValueError:
            continue
        priors = STAGE_SHARE_PRIORS.get(dev)
        if priors is None or stage not in priors.mid:
            continue
        implied = low / gross
        mid = priors.mid[stage]
        band = priors.band[stage]
        lo, hi = mid - band, mid + band
        if implied < lo:
            verdict = "below_band"
        elif implied > hi:
            verdict = "above_band"
        else:
            verdict = "in_band"
        # A drilling_rig award is a single rig's backlog, not the whole DRILL
        # stage, so a below-band DRILL anchor is expected (partial scope).
        lower_bound = _anchor_is_lower_bound(a)
        note = ""
        if a["ASSET_CLASS"] == "drilling_rig":
            note = (
                "single-rig backlog — a partial DRILL cost, so below-band is expected"
            )
        elif a["ASSET_CLASS"] == "production_hub":
            note = "FPSO buyout / hull price — a fraction of full HOST, so below-band is expected"
        elif a["VALUE_BASIS"] == "band":
            note = f"'{a['BAND_WORD']}' band low-bound — implied share is a floor"
        else:
            note = "full-scope explicit award — a genuine test of the prior"
        out.append(
            StageAnchor(
                project=a["PROJECT"],
                dev_type=dev.value,
                stage=stage.value,
                award_low_mm=low,
                gross_mm=gross,
                implied_share=implied,
                prior_mid=mid,
                prior_low=lo,
                prior_high=hi,
                verdict=verdict,
                is_lower_bound=lower_bound,
                contractor=a["CONTRACTOR"],
                note=note,
            )
        )
    return sorted(out, key=lambda s: (s.project, s.stage))


# ---------------------------------------------------------------------------
# 4. Outturn multipliers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Outturn:
    project: str
    currency: str
    sanction_mm: float
    final_mm: float
    multiplier: float  # final / sanction
    final_kind: str


def compute_outturn(curated: Path) -> list[Outturn]:
    trails = _read(curated, "cost_revision_trails.csv")
    by_key: dict[tuple[str, str], dict[str, tuple[float, str]]] = {}
    for t in trails:
        v = _num(t["VALUE_MM"])
        if v is None:
            continue
        key = (t["PROJECT"], t["CURRENCY"])
        by_key.setdefault(key, {})
        # keep the first of each kind (sanction) and prefer outturn over forecast
        k = t["KIND"]
        if k == "sanction_estimate" and "sanction" not in by_key[key]:
            by_key[key]["sanction"] = (v, k)
        elif k in ("final_outturn", "final_forecast"):
            cur = by_key[key].get("final")
            if cur is None or (k == "final_outturn" and cur[1] != "final_outturn"):
                by_key[key]["final"] = (v, k)

    out: list[Outturn] = []
    for (project, ccy), d in by_key.items():
        if "sanction" in d and "final" in d:
            s, _ = d["sanction"]
            f, fk = d["final"]
            if s > 0:
                out.append(
                    Outturn(
                        project=project,
                        currency=ccy,
                        sanction_mm=s,
                        final_mm=f,
                        multiplier=f / s,
                        final_kind=fk,
                    )
                )
    return sorted(out, key=lambda o: o.multiplier, reverse=True)


# ---------------------------------------------------------------------------
# Roll-up
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Reconciliation:
    coverage: list[Coverage]
    partner_checks: list[PartnerCheck]
    stage_anchors: list[StageAnchor]
    outturn: list[Outturn]


def reconcile(curated: Path) -> Reconciliation:
    return Reconciliation(
        coverage=compute_coverage(curated),
        partner_checks=compute_partner_checks(curated),
        stage_anchors=compute_stage_anchors(curated),
        outturn=compute_outturn(curated),
    )
