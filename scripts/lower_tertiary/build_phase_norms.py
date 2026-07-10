#!/usr/bin/env python3
"""ABOUTME: Build the phase-norm layer (issue #848): _norms.json + 5 stage
ABOUTME: distribution pages under reports/lower_tertiary/lifecycle/norms/.

Reads config/phase_norms.yml, computes field metrics + leave-one-field-out play
baselines via worldenergydata.field_development.phase_norms, enforces the
golden-reconciliation and join-coverage gates, then writes:

  - reports/lower_tertiary/lifecycle/_norms.json          (machine contract)
  - reports/lower_tertiary/lifecycle/norms/<stage>.html   (5 stage pages)

Usage:
    python scripts/lower_tertiary/build_phase_norms.py
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import site_nav  # noqa: E402  (nav-spine helper, issue #850)

from worldenergydata.field_development import phase_norms as pn  # noqa: E402


def _crumb(stage: str) -> str:
    return site_nav.crumb_for("norms", {"stage": stage, "stage_title": stage.title()})


LIFECYCLE = REPO / "reports/lower_tertiary/lifecycle"
NORMS_DIR = LIFECYCLE / "norms"

STAGE_TITLES = {
    "drill": "Drill — days to total depth",
    "complete": "Complete — completion days",
    "produce": "Produce — uptime, decline, cumulative oil",
    "workover": "Workover — interventions per well",
    "abandon": "Abandon — plug & abandonment context",
}

STAGE_POP_NOTE = {
    "drill": "Population: FDAS V30 Lower Tertiary development wellbores "
    "(calendar TD−spud days; curated workbook, TOTALS/blank rows dropped).",
    "complete": "Population: FDAS V30 Lower Tertiary development wellbores "
    "with completion-day values.",
    "produce": "Population: producing LT wells in the well benchmark "
    "(survivor population — fields without producing wells show no data).",
    "workover": "Population: producing LT wells in the well benchmark; "
    "interventions per well = total interventions ÷ wells.",
    "abandon": "Per-field abandonment populations are not derivable in v1 "
    "(young LT fields). The all-GoM share below is CONTEXT, not a norm.",
}

CSS = """
:root{--navy:#0B3D91;--teal:#0f8a7e;--ink:#13233f;--mut:#5b6b86;--bg:#f8fafc;
--card:#ffffff;--line:#dbe4f0;--warn:#b45309}
*{box-sizing:border-box}body{margin:0;font:15px/1.55 system-ui,Segoe UI,Roboto,
sans-serif;color:var(--ink);background:var(--bg)}
.wrap{max-width:1100px;margin:0 auto;padding:28px 20px 60px}
h1{color:var(--navy);font-size:26px;margin:0 0 4px}
h2{color:var(--navy);font-size:19px;margin:28px 0 8px}
.sub{color:var(--mut);margin:0 0 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:16px 18px;margin:14px 0}
.thesis{border-left:4px solid var(--teal);padding-left:12px;font-size:16px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}
th{color:var(--mut);font-weight:600}
.badge{display:inline-block;border-radius:999px;padding:1px 9px;font-size:12px;
background:#eef2f7;color:var(--mut)}
.badge.warn{background:#fef3c7;color:var(--warn)}
.badge.roadmap{background:#e0e7ff;color:#3730a3}
.delta-neg{color:var(--teal);font-weight:600}
.delta-pos{color:#b91c1c;font-weight:600}
.plot{overflow-x:auto}
.crumbs{font-size:13px;color:var(--mut);margin-bottom:14px}
.crumbs a{color:var(--teal);text-decoration:none}
.note{font-size:13px;color:var(--mut)}
.anchor-row:target{background:#ecfdf5}
"""


def esc(s) -> str:
    return html.escape(str(s))


def fmt_delta(dp) -> str:
    if dp is None:
        return "—"
    cls = "delta-neg" if dp < 0 else "delta-pos"
    sign = "+" if dp > 0 else "−"
    return f'<span class="{cls}">{sign}{abs(dp)}% vs LT</span>'


def strip_plot_svg(pool, field_points, unit) -> str:
    """One-axis strip plot: play population as grey dots, per-field medians as
    labeled teal markers."""
    values = pool + [v for _, v in field_points]
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    W, H = 980, 46 + 18 * len(field_points)

    def x(v):
        return 40 + (v - lo) / span * (W - 80)

    dots = "".join(
        f'<circle cx="{x(v):.1f}" cy="30" r="3.2" fill="#94a3b8" opacity="0.55"/>'
        for v in pool
    )
    marks = []
    for i, (name, v) in enumerate(sorted(field_points, key=lambda t: t[1])):
        y = 30
        ly = 52 + 18 * i
        marks.append(
            f'<line x1="{x(v):.1f}" y1="{y}" x2="{x(v):.1f}" y2="{ly - 6}" '
            f'stroke="#0f766e" stroke-width="1" opacity="0.5"/>'
            f'<circle cx="{x(v):.1f}" cy="{y}" r="4.5" fill="#0f766e"/>'
            f'<text x="{x(v):.1f}" y="{ly}" font-size="11" fill="#0b2545" '
            f'text-anchor="middle">{esc(name)} {v:g}</text>'
        )
    axis = (
        f'<line x1="40" y1="30" x2="{W - 40}" y2="30" stroke="#cbd5e1"/>'
        f'<text x="40" y="16" font-size="11" fill="#6b7280">{lo:g} {esc(unit)}</text>'
        f'<text x="{W - 40}" y="16" font-size="11" fill="#6b7280" '
        f'text-anchor="end">{hi:g} {esc(unit)}</text>'
    )
    return (
        f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" '
        f'role="img" aria-label="distribution strip plot">{axis}{dots}'
        f"{''.join(marks)}</svg>"
    )


def stage_insight(stage, entries, display_names) -> str:
    """Thesis + a number, computed from the data (no hand-waving)."""
    chip_entries = [
        e
        for e in entries
        if e.stage == stage and e.field is not None and e.delta_play_pct is not None
    ]
    if not chip_entries:
        if stage == "abandon":
            return (
                "No Lower Tertiary field has an abandonment record population "
                "yet — the play is young. The honest statement is the gap "
                "itself; the all-GoM context share below shows what the basin's "
                "full life-cycle eventually looks like."
            )
        return (
            "Not enough populated fields for a cross-field thesis yet — "
            "states below are shown honestly rather than filled."
        )
    best = min(chip_entries, key=lambda e: e.delta_play_pct)
    worst = max(chip_entries, key=lambda e: e.delta_play_pct)
    lower_better = stage in ("drill", "complete", "workover")
    hero, lag = (best, worst) if lower_better else (worst, best)
    return (
        f"Spread is the story: {esc(display_names.get(hero.field_id, hero.field_id))} "
        f"runs {abs(hero.delta_play_pct):g}% "
        f"{'below' if hero.delta_play_pct < 0 else 'above'} the "
        f"leave-one-out play median on {esc(hero.unit)}, while "
        f"{esc(display_names.get(lag.field_id, lag.field_id))} sits "
        f"{abs(lag.delta_play_pct):g}% "
        f"{'above' if lag.delta_play_pct > 0 else 'below'} it "
        f"(n={hero.field.n} / n={lag.field.n} wells)."
    )


def render_stage_page(
    stage, entries, lt_rows, bench_rows, cfg, display_names, abandon_ctx=None
) -> str:
    stage_entries = [e for e in entries if e.stage == stage]
    metric_ids = sorted({e.metric_id for e in stage_entries})
    chip_metric = cfg["chip_metrics"][stage]

    sections = []
    for mid in metric_ids:
        mes = [e for e in stage_entries if e.metric_id == mid]
        with_vals = [e for e in mes if e.field is not None]
        unit = mes[0].unit
        spec = pn.METRICS.get(mid)
        pool = []
        if spec:
            key = spec[4]
            rows = lt_rows if spec[1] == pn.XLSX_POP else bench_rows
            pool = [r[key] for r in rows if r.get(key) is not None]
        plot = (
            strip_plot_svg(
                pool,
                [
                    (display_names.get(e.field_id, e.field_id), e.field.value)
                    for e in with_vals
                ],
                unit,
            )
            if with_vals
            else ""
        )
        rows_html = []
        for e in sorted(
            mes, key=lambda x: (x.field is None, x.field.value if x.field else 0)
        ):
            name = display_names.get(e.field_id, e.field_id)
            if e.field is None:
                state = {
                    "no_data": "no well-level data (pre-production)",
                    "insufficient": "insufficient wells",
                    "unavailable": "unavailable in v1",
                }.get(e.field_status, e.field_status)
                rows_html.append(
                    f'<tr class="anchor-row" id="{e.field_id}"><td>{esc(name)}</td>'
                    f'<td colspan="3"><span class="badge warn">{esc(state)}</span></td>'
                    f'<td><span class="badge roadmap">country: roadmap #681</span></td></tr>'
                )
                continue
            nb = f'{e.field.value:g} {esc(e.unit)} <span class="badge">n={e.field.n}</span>'
            if e.field_status == "low_n":
                nb += ' <span class="badge warn">low n</span>'
            play = (
                f'{e.play.metric.value:g} <span class="badge">n={e.play.metric.n}</span>'
                if e.play.status == "ok"
                else f'<span class="badge warn">{esc(e.play.reason or e.play.status)}</span>'
            )
            rows_html.append(
                f'<tr class="anchor-row" id="{e.field_id}"><td>{esc(name)}</td>'
                f"<td>{nb}</td><td>{play}</td><td>{fmt_delta(e.delta_play_pct)}</td>"
                f'<td><span class="badge roadmap">country: roadmap #681</span></td></tr>'
            )
        star = " (poster chip metric)" if mid == chip_metric else ""
        sections.append(
            f"<h2>{esc(mid)}{star}</h2>"
            f'<div class="card"><div class="plot">{plot}</div>'
            f"<table><thead><tr><th>Field</th><th>Field value</th>"
            f"<th>Play baseline (leave-one-out)</th><th>Δ vs play</th>"
            f"<th>Country</th></tr></thead><tbody>{''.join(rows_html)}</tbody>"
            f"</table></div>"
        )

    ctx_html = ""
    if stage == "abandon" and abandon_ctx and abandon_ctx.get("share_pct") is not None:
        ctx_html = (
            f'<div class="card"><strong>All-GoM context:</strong> '
            f'{abandon_ctx["share_pct"]:g}% of {abandon_ctx["n"]:,} GoM boreholes '
            f"with a status code are PA/TA today "
            f'({abandon_ctx["pa_n"]:,} boreholes). '
            f'<div class="note">{esc(abandon_ctx["caveat"])}</div></div>'
        )

    insight = stage_insight(stage, entries, display_names)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(STAGE_TITLES[stage])} — LT phase norms</title>
<style>{CSS}</style></head><body><div class="wrap">
{_crumb(stage)}
<h1>{esc(STAGE_TITLES[stage])}</h1>
<p class="sub">Field vs Lower Tertiary play (leave-one-field-out) · basis:
calendar days where durations apply · country baselines
<span class="badge roadmap">ROADMAP — drilling-well database #681</span></p>
<div class="card thesis">{insight}</div>
<p class="note">{esc(STAGE_POP_NOTE[stage])}</p>
{ctx_html}
{''.join(sections)}
<p class="note">Generated by scripts/lower_tertiary/build_phase_norms.py ·
provenance in <a href="../_norms.json">_norms.json</a> · issue
<a href="https://github.com/vamseeachanta/worldenergydata/issues/848">#848</a></p>
</div></body></html>
"""


def main() -> int:
    cfg = pn.load_config()
    src = cfg["sources"]
    xlsx = REPO / src["lt_dc_xlsx"]
    bench_csv = REPO / src["benchmark_csv"]
    well_data = REPO / src["well_data_csv"]
    facts = json.loads((REPO / src["facts_json"]).read_text())
    display_names = {f["id"]: f["name"] for f in facts}

    lt_rows, exclusions = pn.load_lt_population(xlsx, cfg)
    bench_rows = pn.load_benchmark(bench_csv, cfg)

    pn.assert_golden(lt_rows, cfg)
    coverage = pn.benchmark_consistency(bench_rows, lt_rows)
    pn.assert_join_coverage(coverage, cfg)

    entries = pn.compute_norms(lt_rows, bench_rows, cfg)
    abandon_ctx = pn.compute_abandon_context(well_data, cfg)

    provenance = pn.build_provenance(
        sources=[
            {
                "path": src["lt_dc_xlsx"],
                "sha256": pn.sha256_of(xlsx),
                "rows_used": len(lt_rows),
            },
            {
                "path": src["benchmark_csv"],
                "sha256": pn.sha256_of(bench_csv),
                "rows_used": len(bench_rows),
            },
        ],
        exclusions=exclusions,
        join_coverage=round(coverage, 4),
        extras={"abandon_context": abandon_ctx, "config": "config/phase_norms.yml"},
    )
    chips = {fid: pn.chips_for_field(entries, fid, cfg) for fid in cfg["field_ids"]}
    pn.write_norms_json(entries, provenance, LIFECYCLE / "_norms.json", chips=chips)
    print(f"  wrote _norms.json ({len(entries)} entries, coverage {coverage:.1%})")

    NORMS_DIR.mkdir(parents=True, exist_ok=True)
    for stage in pn.STAGES:
        page = render_stage_page(
            stage, entries, lt_rows, bench_rows, cfg, display_names, abandon_ctx
        )
        out = NORMS_DIR / f"{stage}.html"
        out.write_text(page)
        print(f"  wrote norms/{out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
