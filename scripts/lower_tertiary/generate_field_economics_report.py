#!/usr/bin/env python3
"""ABOUTME: Generate a field-economics report with an NPV-over-time timeline at the top.
ABOUTME: Annotates the cumulative-NPV series with critical BSEE well operations (WAR/OGOR).

This is an ADDITIVE presentation/visualization layer on top of the sanctioned
V30 financial model. It does NOT change the computed final NPV:

  - The cumulative-NPV series is built by
    ``worldenergydata.lower_tertiary.v30_financial_reproducer.build_field_npv_timeline``,
    which reconstructs the *same* monthly cashflow + trimmed-discount formula
    that ``reproduce_v30_financials`` uses. The terminal cumulative NPV equals
    the sanctioned golden-baseline value (Julia ~= -$531M).
  - Operations annotations (well-added / workover / recompletion / re-entry /
    sidetrack) are derived deterministically from BSEE WAR (Well Activity
    Reports) and OGOR-A production data. They are markers only; they do not
    feed the cashflow model.

The V30 reproducer reads OGOR-A from yearly ``.zip`` archives. When those zips
are not present in a checkout (only the pickled ``.bin`` DataFrames are), this
script monkeypatches ``load_ogor_production`` to read the headerless ``.bin``
files using the exact same column schema / normalisation as the zip loader.

Usage
-----
    uv run python scripts/lower_tertiary/generate_field_economics_report.py \
        --dev Julia --lease G20351

Output
------
    reports/lower_tertiary/field_economics_<dev>.md
"""

from __future__ import annotations

import argparse
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

import sys

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from worldenergydata.lower_tertiary import v30_reproducer  # noqa: E402

# The WAR/OGOR operations-timeline helpers and the .bin OGOR-A fallback loader
# were promoted to ``worldenergydata.lower_tertiary.ops_timeline`` so the engine
# path and other ``src/`` modules can import them without ``sys.path`` hacks.
# They are re-exported here under their original (incl. legacy private) names so
# this report generator's behaviour is unchanged.
from worldenergydata.lower_tertiary.ops_timeline import (  # noqa: E402,F401
    INTERVENTION_CODES,
    OGOR_COLUMNS,
    WAR_ACTIVITY_LABELS,
    _read_war_bin,
    build_operations_timeline,
    derive_first_production_dates,
    derive_spud_milestones,
    derive_war_operations,
    detect_latest_ogor_month,
    detect_reentries,
)
from worldenergydata.lower_tertiary.ops_timeline import (  # noqa: E402,F401
    ensure_ogor_loader as _ensure_ogor_loader,
)
from worldenergydata.lower_tertiary.ops_timeline import (  # noqa: E402,F401
    leases_for_dev,
)
from worldenergydata.lower_tertiary.ops_timeline import (
    load_ogor_from_bin as _load_ogor_from_bin,
)
from worldenergydata.lower_tertiary.ops_timeline import month_end_str as _month_end_str

# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


def _fmt_usd_mm(v: float) -> str:
    return f"{v / 1e6:,.1f}"


def _read_latest_comparison(dev_name: str) -> dict | None:
    """Read latest-window vs V30 oil/revenue for *dev_name* from latest_baseline.yml.

    Returns a dict with ``latest_oil_bbl``, ``latest_revenue_usd``,
    ``v30_oil_bbl``, ``v30_revenue_usd`` (the V30 figures come from each
    project's ``v30_comparison`` block), or ``None`` if the file / project is
    absent. Used only to render the latest financial summary; never fabricated.
    """
    path = (
        PROJECT_ROOT / "config" / "analysis" / "lower_tertiary" / "latest_baseline.yml"
    )
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    for proj in (data or {}).get("projects", {}).values():
        if proj.get("display_name") == dev_name:
            cmp = proj.get("v30_comparison", {})
            return {
                "latest_oil_bbl": proj.get("total_oil_bbl"),
                "latest_revenue_usd": proj.get("total_revenue_usd"),
                "v30_oil_bbl": cmp.get("v30_oil_bbl"),
                "v30_revenue_usd": cmp.get("v30_revenue_usd"),
            }
    return None


def _sparkline(values: list[float]) -> str:
    """Unicode block sparkline (deterministic) for the cumulative NPV path."""
    blocks = "▁▂▃▄▅▆▇█"
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return blocks[0] * len(values)
    out = []
    for v in values:
        idx = int((v - lo) / (hi - lo) * (len(blocks) - 1))
        out.append(blocks[idx])
    return "".join(out)


def _signed_bar(value: float, max_abs: float, width: int = 24) -> str:
    """Horizontal Unicode bar for a signed contribution (deterministic).

    Positive contributions grow right with full blocks; negative grow with a
    distinct glyph. Length is proportional to |value| / max_abs.
    """
    if max_abs <= 0:
        return ""
    n = int(round(abs(value) / max_abs * width))
    n = max(n, 1) if abs(value) > 0 else 0
    glyph = "█" if value >= 0 else "▓"
    return glyph * n


def build_report(
    dev_name: str, lease_num: str | None = None, end_date: str | None = None
) -> str:
    from worldenergydata.lower_tertiary.v30_financial_reproducer import (
        build_field_npv_timeline,
        build_well_npv_stackup,
        reproduce_v30_financials,
    )

    source_desc = _ensure_ogor_loader()

    # Resolve the field's lease(s). A single explicit --lease overrides; else
    # auto-derive every lease mapped to the development (multi-lease fields).
    leases = [lease_num.upper()] if lease_num else leases_for_dev(dev_name)
    lease_label = (
        leases[0] if len(leases) == 1 else f"{len(leases)} leases ({', '.join(leases)})"
    )

    # Window: None => frozen V30 (through 2025-05-31); else the latest end_date.
    is_latest = end_date is not None
    ops_end = end_date if is_latest else "2025-05-31"
    start_label = "2000-09"
    end_label = pd.Timestamp(ops_end).strftime("%Y-%m")
    if is_latest:
        window_label = (
            f"{start_label} -> {end_label} (latest); "
            f"frozen V30 reference NPV = -$530.6M"
        )
    else:
        window_label = f"{start_label} -> {end_label} (V30 frozen window)"

    tl = build_field_npv_timeline(dev_name, end_date=end_date)
    timeline: pd.DataFrame = tl["timeline"].copy()
    timeline["month"] = timeline["date"].dt.to_period("M").dt.to_timestamp()

    ops = build_operations_timeline(leases, ops_end, dev_name=dev_name)

    # Map each operation onto the NPV at its month (nearest <= month).
    npv_by_month = dict(zip(timeline["month"], timeline["cumulative_npv_usd"]))

    def npv_at(month: pd.Timestamp) -> float | None:
        if month in npv_by_month:
            return npv_by_month[month]
        prior = timeline[timeline["month"] <= month]
        if prior.empty:
            return None
        return float(prior["cumulative_npv_usd"].iloc[-1])

    # Full financials for the headline reconciliation.
    fin = reproduce_v30_financials()
    sanctioned_npv = fin[dev_name]["npv_usd"]

    # Latest revenue/oil comparison (read once; reused by the summary + the
    # Financial Summary table below). None for the frozen report.
    cmp = _read_latest_comparison(dev_name) if is_latest else None

    # ---- Price sensitivity + breakeven (NPV is affine in a WTI multiplier) ----
    # One extra scaled timeline pins the exact NPV-vs-price line; everything
    # else (each sensitivity point, the breakeven price) follows analytically.
    price_sens: dict | None = None
    avg_wti = tl.get("avg_realized_wti_usd")
    base_npv = tl["terminal_npv_usd"]
    if avg_wti is not None and not (isinstance(avg_wti, float) and np.isnan(avg_wti)):
        _m = 1.20
        tl_pert = build_field_npv_timeline(
            dev_name, end_date=end_date, wti_price_multiplier=_m
        )
        dnpv_dm = (tl_pert["terminal_npv_usd"] - base_npv) / (_m - 1.0)
        if abs(dnpv_dm) > 1.0:  # sensible slope (positive: NPV rises with price)
            dnpv_per_dollar = dnpv_dm / avg_wti  # $ NPV per +$1/bbl realized
            m_breakeven = 1.0 - base_npv / dnpv_dm
            wti_breakeven = avg_wti * m_breakeven

            def _npv_at_wti(p: float) -> float:
                return base_npv + ((p / avg_wti) - 1.0) * dnpv_dm

            grid = [avg_wti - 20, avg_wti - 10, avg_wti, avg_wti + 10, avg_wti + 20]
            price_sens = {
                "avg_wti": avg_wti,
                "dnpv_per_dollar": dnpv_per_dollar,
                "wti_breakeven": wti_breakeven,
                "rows": [(p, _npv_at_wti(p)) for p in grid if p > 0],
            }

    # ---- Build the yearly cumulative-NPV table (compact) ----
    timeline["year"] = timeline["date"].dt.year
    yearly = (
        timeline.groupby("year")
        .agg(
            cumulative_npv_usd=("cumulative_npv_usd", "last"),
            net_cashflow_usd=("net_cashflow_usd", "sum"),
            month_end=("month", "last"),
        )
        .reset_index()
    )

    # Operation markers grouped by year for the table.
    ops_by_year: dict[int, list[str]] = {}
    if not ops.empty:
        for _, r in ops.iterrows():
            yr = r["date"].year
            marker = f"{r['operation']}: {r['detail']}"
            bucket = ops_by_year.setdefault(yr, [])
            # Collapse identical markers within a year (e.g. two re-drills of
            # the same well) for the yearly summary; the Critical Operations
            # Detail table below still lists each dated event separately.
            if marker not in bucket:
                bucket.append(marker)

    spark = _sparkline(list(yearly["cumulative_npv_usd"]))

    # Trough of the cumulative-NPV path (deepest point of capital exposure) and
    # the recovery since — used by the summary headline and the sparkline caption.
    _trough_idx = yearly["cumulative_npv_usd"].idxmin()
    trough_npv = float(yearly.loc[_trough_idx, "cumulative_npv_usd"])
    trough_year = int(yearly.loc[_trough_idx, "year"])
    terminal_npv = float(tl["terminal_npv_usd"])
    first_npv = float(yearly["cumulative_npv_usd"].iloc[0])
    recovery = terminal_npv - trough_npv

    lines: list[str] = []
    lines.append(f"# {dev_name} Field Economics Report")
    lines.append("")
    lines.append(
        f"**Development:** {dev_name} ({tl['dev_system']}) &middot; "
        f"**Lease:** {lease_label} &middot; "
        f"**First oil:** {pd.Timestamp(tl['first_oil']).date() if tl['first_oil'] is not None else 'n/a'} &middot; "
        f"**Discount rate:** {tl['discount_rate_annual'] * 100:.0f}% annual"
    )
    lines.append("")
    lines.append(f"**Data window:** {window_label}")
    lines.append("")

    # -------------------------- EXECUTIVE SUMMARY ---------------------------
    # Verdict-first headline so a client reads the bottom line before the
    # tables. All figures trace to the same model the detail sections use.
    f0 = fin[dev_name]
    sign = "NPV-negative" if terminal_npv < 0 else "NPV-positive"
    one_time_capital = f0["dnc_total_usd"] + f0["facilities_cost_usd"]
    oil_mm = cmp["latest_oil_bbl"] / 1e6 if cmp and cmp.get("latest_oil_bbl") else None
    rev_mm = (
        cmp["latest_revenue_usd"] / 1e6
        if cmp and cmp.get("latest_revenue_usd")
        else f0["revenue_usd"] / 1e6
    )
    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"On public BSEE production + cost data, **{dev_name}** is "
        f"**{sign} at {tl['discount_rate_annual'] * 100:.0f}%** life-to-date: "
        f"terminal cumulative NPV **${terminal_npv / 1e6:,.1f} M**"
        + (
            f" (frozen V30 sanctioned reference ${sanctioned_npv / 1e6:,.1f} M)."
            if is_latest
            else " (sanctioned V30 model)."
        )
    )
    lines.append("")
    bullet_oil = f"**{oil_mm:,.1f} MMbbl** oil produced" if oil_mm is not None else None
    summary_bullets = []
    if bullet_oil:
        summary_bullets.append(
            f"- {bullet_oil} from **{f0['producers']} producing wells** "
            f"(**{f0['wellbores']} total wellbores**), generating "
            f"**${rev_mm:,.0f} M** gross revenue."
        )
    else:
        summary_bullets.append(
            f"- **{f0['producers']} producing wells** "
            f"(**{f0['wellbores']} total wellbores**), generating "
            f"**${rev_mm:,.0f} M** gross revenue."
        )
    summary_bullets.append(
        f"- A **high-capex, deepwater** signature: **${one_time_capital / 1e6:,.0f} M** "
        f"of one-time D&C + facilities capital is the dominant driver of the NPV."
    )
    summary_bullets.append(
        f"- The cumulative-NPV path bottomed at **${trough_npv / 1e6:,.1f} M** "
        f"in **{trough_year}** and has since recovered "
        f"**${recovery / 1e6:+,.1f} M** as production paid back capital."
    )
    lines.extend(summary_bullets)
    lines.append("")

    if is_latest:
        lines.append(
            "> **LATEST run.** The NPV timeline is built from the V30 cashflow "
            "model extended through the latest available BSEE OGOR-A month "
            "(`build_field_npv_timeline(dev, end_date=...)`). The terminal "
            "cumulative NPV reflects the extended window and therefore differs "
            "from the frozen V30 sanctioned value (shown for reference below). "
            "The frozen V30 baseline (`golden_baseline_v30.yml`) is unchanged."
        )
    else:
        lines.append(
            "> Generated from the sanctioned V30 financial model "
            "(`build_field_npv_timeline` reuses the same monthly cashflow + "
            "trimmed-discount formula as `reproduce_v30_financials`). The NPV "
            "timeline below is an additive presentation layer; it does not alter "
            "the computed final NPV."
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # =========================== NPV TIMELINE (TOP) =========================
    lines.append("## NPV Timeline")
    lines.append("")
    if is_latest:
        delta = tl["terminal_npv_usd"] - sanctioned_npv
        lines.append(
            f"Cumulative discounted NPV evolution over field life, with critical "
            f"well operations annotated. "
            f"Terminal cumulative NPV = **${tl['terminal_npv_usd'] / 1e6:,.1f} M** "
            f"(frozen V30 reference: ${sanctioned_npv / 1e6:,.1f} M; "
            f"delta {delta / 1e6:+,.1f} M)."
        )
    else:
        lines.append(
            f"Cumulative discounted NPV evolution over field life, with critical "
            f"well operations annotated. Terminal cumulative NPV = "
            f"**${tl['terminal_npv_usd'] / 1e6:,.1f} M** "
            f"(reconciles to sanctioned baseline ${sanctioned_npv / 1e6:,.1f} M)."
        )
    lines.append("")
    lines.append(
        f"Cumulative NPV path (by year): `{spark}`  "
        f"_start ${first_npv / 1e6:,.0f}M → trough ${trough_npv / 1e6:,.0f}M "
        f"({trough_year}) → latest ${terminal_npv / 1e6:,.0f}M_"
    )
    lines.append("")
    lines.append(
        "| Year | Net Cashflow ($MM) | Cumulative NPV ($MM) | Critical Operations |"
    )
    lines.append(
        "|------|-------------------:|---------------------:|---------------------|"
    )
    for _, row in yearly.iterrows():
        yr = int(row["year"])
        markers = ops_by_year.get(yr, [])
        marker_txt = "<br>".join(markers) if markers else ""
        lines.append(
            f"| {yr} | {_fmt_usd_mm(row['net_cashflow_usd'])} "
            f"| {_fmt_usd_mm(row['cumulative_npv_usd'])} | {marker_txt} |"
        )
    lines.append("")

    # ---- Operations timeline detail ----
    lines.append("### Critical Operations Detail")
    lines.append("")
    if ops.empty:
        lines.append("_No well operations derived from WAR/OGOR for this lease._")
    else:
        lines.append("| Date | Operation | Well | Cumulative NPV at event ($MM) |")
        lines.append("|------|-----------|------|------------------------------:|")
        for _, r in ops.iterrows():
            npv_here = npv_at(r["month"])
            npv_txt = f"{npv_here / 1e6:,.1f}" if npv_here is not None else "—"
            lines.append(
                f"| {r['date'].date()} | {r['operation']} | {r['detail']} | {npv_txt} |"
            )
    lines.append("")
    lines.append(
        "_Operations are derived deterministically from BSEE Well Activity "
        "Reports (`bin/war/`) and OGOR-A first-production dates "
        f"({source_desc}). Activity codes: DRL=drilling, COM=completion, "
        "WO=workover, REC=recompletion, ST=sidetrack; re-entries detected via "
        "API completion-suffix changes on a shared wellbore. Markers are "
        "annotations only and do not feed the cashflow model._"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # ===================== WELL-LEVEL NPV STACKUP ==========================
    stk = build_well_npv_stackup(dev_name, end_date=end_date)
    lines.append("## Well-Level NPV Stackup")
    lines.append("")
    lines.append(
        f"Field terminal NPV decomposed into per-well contributions that sum "
        f"exactly to the field total. Field NPV = "
        f"**${stk['field_terminal_npv_usd'] / 1e6:,.1f} M**; "
        f"sum of per-well net NPV = **${stk['sum_well_npv_usd'] / 1e6:,.1f} M** "
        f"(residual ${stk['residual_usd']:,.4f})."
    )
    lines.append("")
    lines.append(
        "| Rank | Well (API) | Name | Oil (MMbbl) | Gross well NPV ($MM) | "
        "Allocated shared cost ($MM) | Net well NPV ($MM) | % of field NPV |"
    )
    lines.append(
        "|-----:|-----------|------|------------:|---------------------:|"
        "----------------------------:|-------------------:|-----------:|"
    )
    field_npv = stk["field_terminal_npv_usd"]
    for i, w in enumerate(stk["wells"], start=1):
        pct = 100.0 * w["net_npv_usd"] / field_npv if field_npv else 0.0
        lines.append(
            f"| {i} | {w['api']} | {w['well_name']} "
            f"| {w['oil_bbl'] / 1e6:,.2f} "
            f"| {w['gross_npv_usd'] / 1e6:,.1f} "
            f"| {w['shared_npv_usd'] / 1e6:,.1f} "
            f"| {w['net_npv_usd'] / 1e6:,.1f} "
            f"| {pct:,.1f}% |"
        )
    lines.append("")
    lines.append(
        "> **Reading the ranking.** Under production-pro-rata allocation, the "
        "largest producer absorbs the most shared capital — so the "
        "highest-output well can show the *most negative* net NPV. The "
        "**Gross well NPV** column reflects standalone operating performance; "
        "the **Net well NPV** column reflects each well's share of the "
        "fully-loaded field (which is NPV-negative overall, so every well's "
        "net is negative). **Bottom line:** a negative *net* NPV here is an "
        "allocation outcome on an NPV-negative field, not a verdict on the "
        "well's own performance — read the **Gross well NPV** column for "
        "standalone results."
    )
    lines.append("")

    # Ranked signed-contribution visual (consistent with the sparkline style).
    max_abs = max((abs(w["net_npv_usd"]) for w in stk["wells"]), default=0.0)
    lines.append("Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):")
    lines.append("")
    lines.append("```")
    for w in stk["wells"]:
        bar = _signed_bar(w["net_npv_usd"], max_abs)
        label = f"{w['well_name'] or w['api']:<8}"
        lines.append(f"{label} {w['net_npv_usd'] / 1e6:>8,.1f} M  {bar}")
    lines.append("```")
    lines.append("")
    _slug = dev_name.lower().replace("/", "_").replace(" ", "_")
    _dev_arg = f'"{dev_name}"' if " " in dev_name else dev_name
    lines.append(
        f"**[Interactive NPV waterfalls →](./{_slug}_npv_stackup.html)** — two "
        "views: an **over-time NPV bridge** (each year's change in cumulative "
        "NPV, with the biggest swings annotated by the events that drove them) "
        "and this **per-well stackup** (each well's net NPV stepping to the "
        "field total). Hover any bar for detail. Rebuild with "
        f"`uv run --with plotly python scripts/lower_tertiary/"
        f"build_npv_stackup_chart.py --dev {_dev_arg}`."
    )
    lines.append("")

    # Block-scope grouping (if cleanly available) or a documented gap.
    if stk["blocks"]:
        lines.append("**By block (OGOR `AREA_CODE_BLOCK_NUM`):**")
        lines.append("")
        lines.append("| Block | Oil (MMbbl) | % of field oil |")
        lines.append("|-------|------------:|---------------:|")
        for b in stk["blocks"]:
            lines.append(
                f"| {b['block']} | {b['oil_bbl'] / 1e6:,.2f} "
                f"| {b['oil_share'] * 100:,.1f}% |"
            )
        lines.append("")
    blocks_note = re.sub(r" {2,}", " ", str(stk["blocks_note"]))
    lines.append(f"_Block scope: {blocks_note}_")
    lines.append("")
    n_prod = fin[dev_name].get("producers")
    n_bores = fin[dev_name].get("wellbores")
    if n_prod is not None and n_bores is not None and n_bores != n_prod:
        lines.append(
            f"_The stackup covers the {n_prod} producing wells. The field's "
            f"{n_bores} total wellbores also include appraisal and "
            f"sidetrack/re-drill bores; their drilling & completion capital is "
            f"part of the shared cost allocated pro-rata (it is not attributed "
            f"to a single producer)._"
        )
        lines.append("")
    lines.append(
        "_**Allocation assumption.** Shared field costs (facilities, fixed opex, "
        "host) and the drilling/completion cost of non-producing bores "
        "(appraisal/sidetrack wells with no production to stand against) are "
        "pooled and allocated to the producing wells pro-rata by each well's "
        "share of total field oil production. Each producing well's own revenue, "
        "royalty, variable opex, and directly-resolvable D&C are attributed to "
        "it. Per-well NPVs sum to the field NPV._"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # =========================== WELL GEOMETRY (3D) =========================
    # Interactive 3D well-path renders (Plotly + Three.js) are produced
    # separately by scripts/bsee/demo_well_path_<field>.py from BSEE
    # directional-survey data. They are LINKED here only once the rendered well
    # set is verified to match this report's lease-resolved producers, so the
    # economics and the geometry never silently describe different wells.
    slug = dev_name.lower().replace("/", "_").replace(" ", "_")
    lines.append("## Well Geometry (3D)")
    lines.append("")
    lines.append(
        "Interactive 3D well-path views — minimum-curvature trajectories from "
        "BSEE directional surveys, rendered with Plotly and Three.js — are in "
        "development for this field. When verified they will live at:"
    )
    lines.append("")
    lines.append(f"- `reports/bsee/{slug}_well_path_plotly.html`")
    lines.append(f"- `reports/bsee/{slug}_well_path_threejs.html`")
    lines.append("")
    lines.append(
        "_They are intentionally **not linked yet**: the geometry render must "
        "first be confirmed to cover the same lease-resolved producers shown in "
        "the NPV stackup above (same APIs, same field), so the economics and the "
        "well paths never describe different wells._"
    )
    if slug == "julia":
        lines.append("")
        lines.append(
            "_Julia status: the current demo render (`scripts/bsee/"
            "demo_well_path_julia.py`) selects wells by `WELL_NAME` prefix and "
            "picks up unrelated shelf wells, with an API collision on "
            "`608124009400` (DC101 here vs. JU101 in the well catalog). Tracked "
            "in worldenergydata#493 — re-select by lease G20351, then embed._"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # =========================== FINANCIAL SUMMARY ==========================
    f = fin[dev_name]
    rate_pct = f"{tl['discount_rate_annual'] * 100:.0f}"
    if is_latest:
        lines.append("## Financial Summary")
        lines.append("")
        lines.append(
            f"**Latest window ({start_label} -> {end_label}) vs frozen V30 "
            "reference.** D&C and facilities are one-time capital already "
            "incurred, so they are unchanged from V30; revenue, royalty and opex "
            "scale with the additional production."
        )
        lines.append("")
        lines.append("| Metric | Latest | Frozen V30 (reference) |")
        lines.append("|--------|------:|------:|")
        lines.append(
            f"| **NPV @ {rate_pct}%** "
            f"| **${_fmt_usd_mm(tl['terminal_npv_usd'])} M** "
            f"| ${_fmt_usd_mm(f['npv_usd'])} M |"
        )
        if cmp and cmp.get("latest_revenue_usd") and cmp.get("v30_revenue_usd"):
            lines.append(
                f"| Revenue | ${_fmt_usd_mm(cmp['latest_revenue_usd'])} M "
                f"| ${_fmt_usd_mm(cmp['v30_revenue_usd'])} M |"
            )
        if cmp and cmp.get("latest_oil_bbl") and cmp.get("v30_oil_bbl"):
            lines.append(
                f"| Oil produced (MMbbl) | {cmp['latest_oil_bbl'] / 1e6:,.1f} "
                f"| {cmp['v30_oil_bbl'] / 1e6:,.1f} |"
            )
        lines.append("")
        lines.append(
            "_Latest NPV from `build_field_npv_timeline(dev, end_date)`; latest "
            "revenue/oil from `latest_baseline.yml` (regenerated through "
            f"{end_label}). A full latest component breakdown (royalty/opex split) "
            "is not recomputed here — the frozen V30 breakdown below is the "
            "audited source-of-record._"
        )
        lines.append("")
        lines.append("### Frozen V30 reference (audited source-of-record)")
    else:
        lines.append("## Financial Summary (V30 sanctioned model)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|------:|")
    lines.append(f"| Revenue | ${_fmt_usd_mm(f['revenue_usd'])} M |")
    lines.append(f"| Royalty | ${_fmt_usd_mm(f['royalty_usd'])} M |")
    lines.append(f"| Variable opex | ${_fmt_usd_mm(f['variable_opex_usd'])} M |")
    lines.append(f"| Fixed opex | ${_fmt_usd_mm(f['fixed_opex_usd'])} M |")
    lines.append(f"| D&C cost | ${_fmt_usd_mm(f['dnc_total_usd'])} M |")
    lines.append(f"| Facilities cost | ${_fmt_usd_mm(f['facilities_cost_usd'])} M |")
    lines.append(
        f"| Net cashflow (undiscounted) | ${_fmt_usd_mm(f['net_cashflow_usd'])} M |"
    )
    lines.append(
        f"| **NPV @ {tl['discount_rate_annual'] * 100:.0f}%** | **${_fmt_usd_mm(f['npv_usd'])} M** |"
    )
    mirr = f.get("mirr_annual")
    if mirr is not None and not (isinstance(mirr, float) and np.isnan(mirr)):
        lines.append(f"| MIRR (annual) | {mirr * 100:.2f}% |")
    lines.append(f"| Producers | {f['producers']} |")
    lines.append(f"| Injectors | {f['injectors']} |")
    lines.append(f"| Wellbores | {f['wellbores']} |")
    lines.append("")
    lines.append(
        "_Return metric: **MIRR** is the sanctioned return measure for these "
        "developments, not IRR. Deepwater Lower-Tertiary cashflows are heavily "
        "front-loaded (large D&C + facilities outflows, then a long production "
        "tail), so the net-cashflow sign changes more than once and the IRR "
        "polynomial can have multiple — or no — real roots; MIRR (single "
        "reinvestment/finance rate at the 10% discount rate) is well-defined "
        "and unambiguous. NPV @ 10% remains the primary value metric._"
    )
    lines.append("")
    lines.append(
        "_Source-of-record: `config/analysis/lower_tertiary/golden_baseline_v30.yml`. "
        "NPV reproduced within golden-baseline tolerance by "
        "`worldenergydata.lower_tertiary.v30_financial_reproducer`._"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # ============================ PRICE SENSITIVITY =========================
    if price_sens is not None:
        rate_pct = f"{tl['discount_rate_annual'] * 100:.0f}"
        avgw = price_sens["avg_wti"]
        be = price_sens["wti_breakeven"]
        per_mm = price_sens["dnpv_per_dollar"] / 1e6
        lines.append("## Price Sensitivity")
        lines.append("")
        be_phrase = (
            f"zero at a flat-equivalent realized WTI of ${be:,.0f}/bbl"
            if be > 0
            else "zero at no achievable price — non-price costs exceed oil "
            "revenue at any positive WTI under this discount rate"
        )
        lines.append(
            f"NPV is linear in the oil price deck: each **+$1/bbl** on the "
            f"realized oil price moves field NPV by **${per_mm:+,.1f} M**. "
            f"Life-to-date NPV reaches **{be_phrase}**, versus the actual "
            f"volume-weighted realized **${avgw:,.0f}/bbl** over the window."
        )
        lines.append("")
        lines.append(
            f"| Flat-equivalent realized WTI ($/bbl) | NPV @ {rate_pct}% ($MM) |"
        )
        lines.append("|-------------------------------------:|------------------:|")
        for p, npv in price_sens["rows"]:
            mark = "  ← actual" if abs(p - avgw) < 1e-6 else ""
            lines.append(f"| {p:,.0f}{mark} | {_fmt_usd_mm(npv)} |")
        lines.append("")
        lines.append(
            "_Exact, not sampled: NPV is affine in a uniform price multiplier "
            "(revenue and royalty scale with price; variable/fixed opex, D&C, "
            "facilities and discounting do not), so one base run plus one scaled "
            "run define the entire line. 'Flat-equivalent realized WTI' is the "
            "volume-weighted average price; the underlying deck is the historical "
            "monthly WTI path._"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

    # =============================== NEXT STEPS / CTAs =======================
    dev_arg = f'"{dev_name}"' if " " in dev_name else dev_name
    lines.append("## Next Steps")
    lines.append("")
    lines.append(
        f"- **Get a tailored analysis.** Want this for your own assets — a "
        f"different field, a custom price deck, sensitivities, or a partner-level "
        f"working-interest view? **AceEngineer** builds traceable field economics "
        f"from public data. Contact **vamsee.achanta@aceengineer.com** to scope an "
        f"engagement."
    )
    lines.append(
        f"- **Explore the full play.** {dev_name} is one of **10 Lower Tertiary "
        f"(Wilcox) fields** covered by this model. Regenerate any field with "
        f"`--dev <Field>`, or ask for the **portfolio economics report** for the "
        f"whole-play NPV view (Jack/St. Malo, Stones, Big Foot, Anchor, "
        f"Cascade/Chinook, and more)."
    )
    lines.append(
        "- **See the methodology.** Every number here traces to **public BSEE "
        "OGOR-A production + drilling/WAR records** run through the sanctioned V30 "
        "cashflow model — no black box. The pipeline (BSEE public data → parsed "
        "`.bin` → V30 NPV) is reproducible end-to-end and reconciles to the frozen "
        "golden baseline."
    )
    lines.append(f"- **Run it yourself.** Refresh the data and regenerate this report:")
    lines.append("")
    lines.append("  ```bash")
    lines.append(
        "  # 1. refresh the latest BSEE OGOR-A production (2025 + current year)"
    )
    lines.append("  uv run python scripts/refresh_bsee_ogor_recent.py")
    lines.append("  # 2. regenerate this report (latest window is the default;")
    lines.append("  #    leases are auto-derived for the field)")
    lines.append(
        f"  uv run python scripts/lower_tertiary/generate_field_economics_report.py "
        f"--dev {dev_arg}"
    )
    lines.append("  # frozen V30 reference report: add --frozen")
    lines.append("  ```")
    lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", default="Julia", help="Development display name")
    parser.add_argument(
        "--lease",
        default=None,
        help="Surface lease number. Omit to auto-derive ALL leases mapped to "
        "the field (required for multi-lease fields like Jack St Malo).",
    )
    win = parser.add_mutually_exclusive_group()
    win.add_argument(
        "--latest",
        action="store_true",
        help="Build a LATEST report through the newest available OGOR-A month "
        "(auto-detected from the .bin data). This is the DEFAULT.",
    )
    win.add_argument(
        "--frozen",
        "--v30",
        dest="frozen",
        action="store_true",
        help="Build the FROZEN V30 report (production through 2025-05-31, frozen "
        "WTI). Selects the sanctioned reference window instead of the latest one.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Explicit upper date bound YYYY-MM-DD (implies the latest window). "
        "When omitted (and not --frozen), the latest OGOR-A month is auto-detected.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output markdown path (default: reports/lower_tertiary/field_economics_<dev>.md)",
    )
    args = parser.parse_args(argv)

    # Ensure the .bin loader is patched before auto-detecting the latest month.
    _ensure_ogor_loader()

    # Default = LATEST window. --frozen selects the V30 reference window.
    end_date: str | None = args.end_date
    is_latest = (not args.frozen) or args.end_date is not None
    if is_latest and end_date is None:
        latest_month = detect_latest_ogor_month()
        end_date = _month_end_str(latest_month)
        print(
            f"Auto-detected latest OGOR-A month: {latest_month.strftime('%Y-%m')} "
            f"-> end_date {end_date}"
        )

    report = build_report(
        args.dev, args.lease, end_date=end_date if is_latest else None
    )

    if args.out:
        out_path = Path(args.out)
    else:
        slug = args.dev.lower().replace(" ", "_").replace("/", "_")
        # Frozen V30 -> *_v30.md; latest -> the canonical unsuffixed report.
        suffix = "" if is_latest else "_v30"
        out_path = (
            PROJECT_ROOT
            / "reports"
            / "lower_tertiary"
            / f"field_economics_{slug}{suffix}.md"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
