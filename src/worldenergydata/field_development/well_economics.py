# ABOUTME: Per-well economics engine (issue #849) — rig-day proxy construction
# ABOUTME: cost, benchmark revenue verbatim, coverage matrix with honest states.
"""Per-well economics for the well life-cycle timeline pages.

Turns observed well quantities into defensible proxy estimates:

- construction cost = rig-days x day-rate (``RegionalCostLoader``, the
  ``day_rates.yml`` database) — rig-days come SOLELY from the well facts
  record, never from benchmark calendar spans;
- revenue = the benchmark's ``est_revenue_mm`` verbatim (gross, BSEE monthly
  production x EIA WTI monthly) — never recomputed;
- gross-revenue coverage (indicative, upper bound) — degraded or suppressed
  per an explicit state matrix; no number is ever fabricated.

All monetary policy lives in ``config/well_economics.yml`` and
``config/analysis/cost_data/day_rates.yml``; this module holds no rates.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    WaterDepthBand,
    classify_water_depth_band,
)

SCHEMA_VERSION = "1.0"
FT_TO_M = 0.3048

USD_PER_MM = 1_000_000


@dataclass(frozen=True)
class RateCell:
    activity: str
    band: str
    year_requested: int
    year_used: int
    usd_per_day: float
    rate_status: str  # exact | clamped
    vintage_fallback: str  # spud_year | first_oil_year | td_year_early_biased
    hpht_applied: bool


@dataclass(frozen=True)
class WellEconomics:
    drill_cost_usd: float | None
    completion_cost_usd: float | None
    construction_cost_usd: float | None
    rate_cells: list[RateCell]
    revenue_mm_usd: float | None
    revenue_flag: str | None
    revenue_source: str
    coverage_ratio: float | None
    coverage_status: str  # indicative | degraded | suppressed
    coverage_reason: str | None
    status: str
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        def mm(v):
            return None if v is None else round(v / USD_PER_MM, 2)

        return {
            "schema_version": SCHEMA_VERSION,
            "drill_cost_mm_usd": mm(self.drill_cost_usd),
            "completion_cost_mm_usd": mm(self.completion_cost_usd),
            "construction_cost_mm_usd": mm(self.construction_cost_usd),
            "rate_cells": [
                {
                    "activity": c.activity,
                    "band": c.band,
                    "year_requested": c.year_requested,
                    "year_used": c.year_used,
                    "usd_per_day": c.usd_per_day,
                    "rate_status": c.rate_status,
                    "vintage_fallback": c.vintage_fallback,
                    "hpht_applied": c.hpht_applied,
                }
                for c in self.rate_cells
            ],
            "revenue_mm_usd": self.revenue_mm_usd,
            "revenue_flag": self.revenue_flag,
            "revenue_source": self.revenue_source,
            "coverage_ratio": (
                None if self.coverage_ratio is None else round(self.coverage_ratio, 1)
            ),
            "coverage_status": self.coverage_status,
            "coverage_reason": self.coverage_reason,
            "status": self.status,
            "notes": list(self.notes),
        }


REVENUE_SOURCE = "gross · BSEE monthly production × EIA WTI monthly (benchmark)"

NOMINAL_NOTE = (
    "Nominal-USD proxy: day rates are nominal per-vintage-year; revenue is "
    "nominal realized; the coverage ratio mixes vintages and excludes "
    "royalty (~18.75%), working interest, services, mob/demob, opex, "
    "facilities, P&A and discounting — an indicative upper bound only."
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def water_depth_band_from_ft(depth_ft: float) -> WaterDepthBand:
    """Classify water depth given FEET (the classifier itself takes metres)."""
    return classify_water_depth_band(depth_ft * FT_TO_M)


def rate_db_year_range(rates_dir: str | Path) -> tuple[int, int]:
    """Derive the (min, max) indexed year across all cells of day_rates.yml.

    No hardcoded years: the range comes from the database itself so a future
    #844 refresh widens the clamp window automatically.
    """
    with open(Path(rates_dir) / "day_rates.yml") as fh:
        doc = yaml.safe_load(fh)
    years: set[int] = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(k, int) or (isinstance(k, str) and str(k).isdigit()):
                    years.add(int(k))
                else:
                    walk(v)

    walk(doc.get("regions", {}))
    if not years:
        raise ValueError(f"no year-indexed rates found under {rates_dir}")
    return min(years), max(years)


def _year_of(datestr) -> int | None:
    if not datestr:
        return None
    try:
        return int(str(datestr)[:4])
    except ValueError:
        return None


def load_revenue_map(csv_path: str | Path) -> dict[str, tuple[float, str]]:
    """api12 -> (est_revenue_mm, revenue_flag), string-keyed.

    Uses the csv module (strings in) so the api12 int64-dtype join hazard
    cannot occur.
    """
    out: dict[str, tuple[float, str]] = {}
    with open(csv_path, newline="") as fh:
        for r in csv.DictReader(fh):
            api = (r.get("api12") or "").strip().zfill(12)
            raw = (r.get("est_revenue_mm") or "").strip()
            if not api or not raw:
                continue
            try:
                mm = float(raw)
            except ValueError:
                continue
            out[api] = (mm, (r.get("revenue_flag") or "").strip())
    return out


def norms_comparison(well: dict, field_id: str, norms_path: str | Path) -> dict:
    """Well-vs-field/play drill-days comparison from the #848 norms contract.

    Degrades to ``{"state": "pending"}`` on absent, malformed, or partial
    contract — never crashes, never fabricates.
    """
    p = Path(norms_path)
    if not p.exists():
        return {"state": "pending"}
    try:
        doc = json.loads(p.read_text())
        entry = next(
            e
            for e in doc["entries"]
            if e["field_id"] == field_id
            and e["metric_id"] == "drill_days_median"
            and e.get("field")
        )
    except (json.JSONDecodeError, KeyError, StopIteration):
        return {"state": "pending"}
    days = well.get("drilling_rig_days")
    field_median = entry["field"]["value"]
    out = {
        "state": "ok",
        "field_median": field_median,
        "field_n": entry["field"]["n"],
    }
    if days:
        out["well_vs_field_pct"] = round((days - field_median) / field_median * 100, 1)
    play = entry.get("play") or {}
    if play.get("status") == "ok" and play.get("metric"):
        out["play_median"] = play["metric"]["value"]
        out["play_n"] = play["metric"]["n"]
        if days:
            out["well_vs_play_pct"] = round(
                (days - out["play_median"]) / out["play_median"] * 100, 1
            )
    return out


# ---------------------------------------------------------------------------
# core computation
# ---------------------------------------------------------------------------


def _rate_cell(
    loader,
    year_range: tuple[int, int],
    activity: ActivityType,
    band: WaterDepthBand,
    year_requested: int,
    vintage_fallback: str,
    hpht: bool,
    region: str,
) -> RateCell:
    lo, hi = year_range
    year_used = min(max(year_requested, lo), hi)
    usd = loader.get_day_rate(region, band, activity, year_used, hpht=hpht)
    return RateCell(
        activity=activity.value,
        band=band.value,
        year_requested=year_requested,
        year_used=year_used,
        usd_per_day=usd,
        rate_status="exact" if year_used == year_requested else "clamped",
        vintage_fallback=vintage_fallback,
        hpht_applied=hpht,
    )


def compute_well_economics(
    well: dict,
    field_ctx: dict,
    revenue: tuple[float, str] | None,
    loader,
    rates_dir: str | Path,
    cfg: dict,
) -> WellEconomics:
    """Compute the economics card payload for one well.

    ``revenue`` is a ``(est_revenue_mm, revenue_flag)`` tuple projected from
    the benchmark row — passing anything else raises (structural guard so
    benchmark calendar-day columns can never reach the cost path).
    """
    if revenue is not None and not (isinstance(revenue, tuple) and len(revenue) == 2):
        raise TypeError("revenue must be a (est_revenue_mm, revenue_flag) tuple")

    region = cfg["region"]
    hpht = bool(cfg.get("hpht_fields", {}).get(field_ctx["id"], False))
    band = water_depth_band_from_ft(field_ctx["water_depth_ft"])
    year_range = rate_db_year_range(rates_dir)

    notes = [NOMINAL_NOTE]
    rate_cells: list[RateCell] = []

    drill_days = well.get("drilling_rig_days") or 0
    compl_days = well.get("completion_rig_days") or 0

    drill_cost = compl_cost = total_cost = None
    if drill_days > 0 or compl_days > 0:
        spud_year = _year_of(well.get("spud_date"))
        if drill_days > 0 and spud_year:
            cell = _rate_cell(
                loader,
                year_range,
                ActivityType.DRILLING,
                band,
                spud_year,
                "spud_year",
                hpht,
                region,
            )
            rate_cells.append(cell)
            drill_cost = drill_days * cell.usd_per_day
        if compl_days > 0:
            fo_year = _year_of(well.get("first_oil"))
            td_year = _year_of(well.get("td_date"))
            if fo_year:
                year, fb = fo_year, "first_oil_year"
            elif td_year:
                year, fb = td_year, "td_year_early_biased"
            else:
                year, fb = None, None
            if year:
                cell = _rate_cell(
                    loader,
                    year_range,
                    ActivityType.COMPLETION,
                    band,
                    year,
                    fb,
                    hpht,
                    region,
                )
                rate_cells.append(cell)
                compl_cost = compl_days * cell.usd_per_day
        parts = [c for c in (drill_cost, compl_cost) if c is not None]
        total_cost = sum(parts) if parts else None

    rev_mm = rev_flag = None
    if revenue is not None:
        rev_mm, rev_flag = revenue

    # --- coverage matrix (plan r3) ---
    status = well.get("status") or "unknown"
    clean_flags = cfg.get("clean_revenue_flags", [""])
    producing = status in cfg.get("producing_statuses", ["producing"])
    clamped = any(c.rate_status == "clamped" for c in rate_cells)

    ratio = reason = None
    if total_cost is None:
        coverage = "suppressed"
        reason = "insufficient day data — no proxy cost"
    elif rev_mm is None:
        coverage = "suppressed"
        reason = "no benchmark revenue row"
    elif not producing:
        coverage = "suppressed"
        reason = f"well status '{status}' — ratio not meaningful"
    else:
        ratio = rev_mm * USD_PER_MM / total_cost
        if clamped:
            coverage = "degraded"
            reason = "clamped-rate proxy (vintage outside rate DB range)"
        elif rev_flag not in clean_flags:
            coverage = "degraded"
            reason = f"revenue flagged '{rev_flag}'"
        else:
            coverage = "indicative"

    return WellEconomics(
        drill_cost_usd=drill_cost,
        completion_cost_usd=compl_cost,
        construction_cost_usd=total_cost,
        rate_cells=rate_cells,
        revenue_mm_usd=rev_mm,
        revenue_flag=rev_flag,
        revenue_source=REVENUE_SOURCE,
        coverage_ratio=ratio,
        coverage_status=coverage,
        coverage_reason=reason,
        status=status,
        notes=notes,
    )
