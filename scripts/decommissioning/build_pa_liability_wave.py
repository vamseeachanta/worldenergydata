"""ABOUTME: Build the GoM P&A liability-wave front-door page (issue #777, Abandon stage).
ABOUTME: Ages a real BSEE GoM borehole inventory into forward P&A liability and prices it.

Reads the BSEE curated well/borehole inventory
(``data/modules/bsee/current/wells/well_data.csv``) — the only repo dataset that
carries a real, populated GoM borehole *status* (``BOREHOLE_STAT_CD``) and a
status *date* (``BOREHOLE_STAT_DT``) for the full ~57k-borehole population.

Boreholes not yet permanently plugged (status ``TA`` temporarily-abandoned +
``COM`` completed/open) are the FORWARD P&A liability. Each is priced with the
decommissioning cost model (``well_p_and_a`` asset, region ``gom``). The
"liability wave" is the forward population rolled up by the DECADE the borehole
entered its current status (its idle / completion vintage) — older = more
overdue against BSEE's Idle Iron plug-or-justify rule.

Outputs (self-contained, no external assets):
    reports/decommissioning/pa_liability_wave.csv
    reports/decommissioning/pa_liability_wave.html

FLAG-DON'T-FAKE: every number below is computed from the source file. Per-well
WATER_DEPTH is populated for only 100 of 57,281 boreholes, so the depth term of
the cost model cannot be applied per well; costs are priced at the model's GoM
P&A base with a documented depth-sensitivity band instead of invented depths.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Decommissioning toolkit lives in its own package; import the cost model + regs
# directly (submodule import avoids the namespace package's heavier __init__).
sys.path.insert(
    0, str(PROJECT_ROOT / "packages" / "worldenergydata-decommissioning" / "src")
)
from worldenergydata.decommissioning.cost_model import (  # noqa: E402
    DecommissioningCostEstimator,
)
from worldenergydata.decommissioning.regulations import get_regulations  # noqa: E402

SRC = PROJECT_ROOT / "data" / "modules" / "bsee" / "current" / "wells" / "well_data.csv"
OUT_CSV = PROJECT_ROOT / "reports" / "decommissioning" / "pa_liability_wave.csv"
OUT_HTML = PROJECT_ROOT / "reports" / "decommissioning" / "pa_liability_wave.html"

FT_PER_M = 3.280839895

# Tiers of the forward P&A liability (boreholes NOT yet permanently plugged).
FORWARD_TIERS = {
    "TA": "Temporarily abandoned",  # imminent / overdue
    "COM": "Completed (open)",       # latent
}
RETIRED_CODE = "PA"  # permanently plugged & abandoned (wave already spent)


def decade_of(year: float) -> str:
    if pd.isna(year):
        return "Undated"
    y = int(year)
    if y < 1980:
        return "pre-1980"
    return f"{(y // 10) * 10}s"


DECADE_ORDER = ["pre-1980", "1980s", "1990s", "2000s", "2010s", "2020s", "Undated"]


def main() -> None:
    df = pd.read_csv(SRC, low_memory=False)
    n_total = len(df)
    code = df["BOREHOLE_STAT_CD"].astype(str).str.strip().str.upper()
    stat_dt = pd.to_datetime(df["BOREHOLE_STAT_DT"], errors="coerce")
    wd_ft = pd.to_numeric(df["WATER_DEPTH"], errors="coerce")

    status_counts = code.value_counts().to_dict()
    n_wd = int(wd_ft.notna().sum())

    est = DecommissioningCostEstimator()

    # ---- Per-well GoM P&A cost reference points (from the cost model) --------
    base = est.estimate("well_p_and_a", water_depth_m=0, region="gom")
    shelf = est.estimate("well_p_and_a", water_depth_m=60, region="gom")  # ~200 ft
    shelf_edge = est.estimate("well_p_and_a", water_depth_m=200, region="gom")
    # Deepwater reference = median of the boreholes that DO carry a depth (n=100)
    dw_med_ft = float(wd_ft.dropna().median())
    dw_med_m = dw_med_ft / FT_PER_M
    deep = est.estimate("well_p_and_a", water_depth_m=dw_med_m, region="gom")
    per_well_base = base.estimated_cost_musd  # 8.0 MUSD floor (depth term = 0)

    # ---- Forward liability population ---------------------------------------
    is_forward = code.isin(FORWARD_TIERS.keys())
    is_retired = code == RETIRED_CODE
    wave = pd.DataFrame(
        {
            "code": code,
            "decade": stat_dt.dt.year.map(decade_of),
        }
    )

    forward = wave[is_forward]
    retired = wave[is_retired]
    n_forward = len(forward)
    n_ta = int((code == "TA").sum())
    n_com = int((code == "COM").sum())
    n_pa = len(retired)

    # ---- Roll up by vintage decade ------------------------------------------
    rows = []
    for dec in DECADE_ORDER:
        ta = int(((forward["code"] == "TA") & (forward["decade"] == dec)).sum())
        com = int(((forward["code"] == "COM") & (forward["decade"] == dec)).sum())
        fwd = ta + com
        pa = int((retired["decade"] == dec).sum())
        rows.append(
            {
                "vintage_decade": dec,
                "ta_wells": ta,
                "com_wells": com,
                "forward_wells": fwd,
                "forward_liability_musd_base": round(fwd * per_well_base, 1),
                "pa_retired_wells": pa,
                "pa_retired_musd_base": round(pa * per_well_base, 1),
            }
        )
    table = pd.DataFrame(rows)
    # Drop all-zero decades to keep the CSV tight, but keep chronological order.
    table = table[(table["forward_wells"] > 0) | (table["pa_retired_wells"] > 0)]

    total_forward_musd = round(n_forward * per_well_base, 1)
    total_ta_musd = round(n_ta * per_well_base, 1)
    # Upper anchor = the whole forward population priced at a TYPICAL SHELF depth
    # (~60 m). The GoM P&A backlog is overwhelmingly shelf; deepwater wells cost
    # more PER WELL but are a small minority, so we do NOT price the whole
    # population at the deepwater rate (that would fabricate the depth mix).
    total_forward_shelf_musd = round(n_forward * shelf.estimated_cost_musd, 1)

    # ---- Write CSV -----------------------------------------------------------
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as fh:
        fh.write(
            "# GoM P&A liability wave (BSEE Abandon stage, issue #777)\n"
            f"# source: {SRC.relative_to(PROJECT_ROOT)} | {n_total} boreholes\n"
            f"# forward P&A population = TA (temporarily abandoned) + COM (completed/open)"
            f" = {n_forward} boreholes\n"
            f"# per-well GoM P&A cost (model well_p_and_a, region gom): base ${per_well_base}M"
            f" (depth term=0); shelf ~60m ${shelf.estimated_cost_musd}M;"
            f" deepwater ~{dw_med_m:.0f}m ${deep.estimated_cost_musd}M\n"
            f"# WATER_DEPTH populated for only {n_wd}/{n_total} boreholes -> $ priced at GoM base\n"
        )
    table.to_csv(OUT_CSV, mode="a", index=False)

    # ---- Regulatory hook -----------------------------------------------------
    idle_iron = next(
        (
            r
            for r in get_regulations("gom")
            if r.requirement_type == "well_plugging"
        ),
        None,
    )

    # ---- Build HTML ----------------------------------------------------------
    html_str = render_html(
        n_total=n_total,
        status_counts=status_counts,
        n_forward=n_forward,
        n_ta=n_ta,
        n_com=n_com,
        n_pa=n_pa,
        n_wd=n_wd,
        per_well_base=per_well_base,
        shelf=shelf,
        shelf_edge=shelf_edge,
        deep=deep,
        dw_med_m=dw_med_m,
        total_forward_musd=total_forward_musd,
        total_ta_musd=total_ta_musd,
        total_forward_shelf_musd=total_forward_shelf_musd,
        table=table,
        idle_iron=idle_iron,
    )
    OUT_HTML.write_text(html_str, encoding="utf-8")

    print(f"boreholes={n_total} forward(TA+COM)={n_forward} (TA={n_ta} COM={n_com}) PA={n_pa}")
    print(f"per-well base=${per_well_base}M forward floor=${total_forward_musd/1000:.1f}B "
          f"TA floor=${total_ta_musd/1000:.1f}B shelf-anchor=${total_forward_shelf_musd/1000:.1f}B")
    print(f"wrote {OUT_CSV.relative_to(PROJECT_ROOT)} and {OUT_HTML.relative_to(PROJECT_ROOT)}")


def _b(musd: float) -> str:
    return f"${musd/1000:.1f}B"


def render_html(**k) -> str:
    table: pd.DataFrame = k["table"]
    idle = k["idle_iron"]
    per = k["per_well_base"]

    # --- forward liability wave bar chart (SVG), by vintage decade -----------
    wave_rows = [r for _, r in table.iterrows() if r["forward_wells"] > 0]
    max_fwd = max((r["forward_wells"] for r in wave_rows), default=1)
    bar_w, gap, top, bottom, left = 96, 34, 34, 64, 8
    chart_w = left + len(wave_rows) * (bar_w + gap) + 20
    chart_h = 300
    plot_h = chart_h - top - bottom
    bars = []
    x = left + 10
    for r in wave_rows:
        h = plot_h * (r["forward_wells"] / max_fwd)
        y = top + (plot_h - h)
        baseline = top + plot_h
        musd = r["forward_liability_musd_base"]
        # Stacked: TA (imminent, alert) at the base, COM (latent, future) on top.
        ta_h = h * (r["ta_wells"] / r["forward_wells"]) if r["forward_wells"] else 0
        com_h = h - ta_h
        bars.append(
            f'<g>'
            f'<rect x="{x}" y="{baseline - ta_h:.1f}" width="{bar_w}" height="{ta_h:.1f}" '
            f'fill="var(--alert)" rx="3"><title>{html.escape(str(r["ta_wells"]))} temporarily abandoned (imminent)</title></rect>'
            f'<rect x="{x}" y="{baseline - h:.1f}" width="{bar_w}" height="{com_h:.1f}" '
            f'fill="var(--future)" rx="3"><title>{html.escape(str(r["com_wells"]))} completed/open</title></rect>'
            f'<text x="{x + bar_w/2:.0f}" y="{y - 22:.0f}" text-anchor="middle" '
            f'class="bl">{int(r["forward_wells"]):,}</text>'
            f'<text x="{x + bar_w/2:.0f}" y="{y - 8:.0f}" text-anchor="middle" '
            f'class="bm">{_b(musd)}</text>'
            f'<text x="{x + bar_w/2:.0f}" y="{top + plot_h + 20:.0f}" text-anchor="middle" '
            f'class="bx">{html.escape(str(r["vintage_decade"]))}</text>'
            f'</g>'
        )
        x += bar_w + gap
    svg = (
        f'<svg viewBox="0 0 {chart_w} {chart_h}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="Forward P&amp;A liability by vintage decade">'
        + "".join(bars)
        + f'<line x1="{left}" y1="{top+plot_h}" x2="{chart_w-10}" y2="{top+plot_h}" '
        f'stroke="var(--line)" stroke-width="1"/>'
        + "</svg>"
    )

    # --- vintage table rows ---------------------------------------------------
    trows = []
    for _, r in table.iterrows():
        trows.append(
            "<tr>"
            f'<td class="lab">{html.escape(str(r["vintage_decade"]))}</td>'
            f'<td class="num">{int(r["ta_wells"]):,}</td>'
            f'<td class="num">{int(r["com_wells"]):,}</td>'
            f'<td class="num strong">{int(r["forward_wells"]):,}</td>'
            f'<td class="num">{_b(r["forward_liability_musd_base"])}</td>'
            f'<td class="num muted">{int(r["pa_retired_wells"]):,}</td>'
            "</tr>"
        )

    idle_txt = (
        f'{html.escape(idle.regulatory_body)} {html.escape(idle.reference_doc)} — '
        f'"{html.escape(idle.key_threshold)}" ({idle.lead_time_months}-month lead time)'
        if idle
        else "BSEE Idle Iron (NTL 2018-N02)"
    )

    sc = k["status_counts"]
    def scget(c):
        return int(sc.get(c, 0))

    return f"""<meta charset="utf-8">
<title>GoM P&amp;A Liability Wave</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {{
    --bg:#eef2f6; --panel:#fff; --panel-2:#f6f9fc; --ink:#0c1a28; --muted:#5a6b7b;
    --line:#d6e0ea; --accent:#d9822b; --accent-ink:#7a4410; --done:#1d5fa8;
    --future:#a9bccd; --good:#2e9e6b; --alert:#c0453b;
    --shadow:0 1px 2px rgba(12,26,40,.06),0 8px 24px rgba(12,26,40,.06);
    --mono:ui-monospace,"SF Mono","Cascadia Code",Consolas,monospace;
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }}
  @media (prefers-color-scheme:dark){{:root{{
    --bg:#0a141f; --panel:#10202f; --panel-2:#0d1b28; --ink:#e8eef4; --muted:#8ca0b3;
    --line:#24384b; --accent:#f0a24a; --accent-ink:#f7c489; --done:#4d91d6;
    --future:#3a5064; --good:#43b982; --alert:#e0685e;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);
  }}}}
  :root[data-theme="light"]{{--bg:#eef2f6;--panel:#fff;--panel-2:#f6f9fc;--ink:#0c1a28;--muted:#5a6b7b;--line:#d6e0ea;--accent:#d9822b;--done:#1d5fa8;--future:#a9bccd;--good:#2e9e6b;--alert:#c0453b;}}
  :root[data-theme="dark"]{{--bg:#0a141f;--panel:#10202f;--panel-2:#0d1b28;--ink:#e8eef4;--muted:#8ca0b3;--line:#24384b;--accent:#f0a24a;--done:#4d91d6;--future:#3a5064;--good:#43b982;--alert:#e0685e;}}
  *{{box-sizing:border-box;}} body{{margin:0;}}
  .wrap{{background:var(--bg);color:var(--ink);font-family:var(--sans);padding:clamp(16px,3vw,40px);min-height:100%;-webkit-font-smoothing:antialiased;}}
  .sheet{{max-width:1080px;margin:0 auto;background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);overflow:hidden;}}
  .head{{padding:clamp(20px,2.6vw,34px);border-bottom:1px solid var(--line);}}
  .eyebrow{{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin:0 0 8px;}}
  .title{{font-size:clamp(26px,3.6vw,40px);font-weight:800;letter-spacing:-.02em;margin:0;line-height:1.03;text-wrap:balance;}}
  .thesis{{color:var(--ink);margin:14px 0 0;font-size:clamp(15px,1.6vw,18px);max-width:70ch;line-height:1.5;}}
  .thesis b{{color:var(--alert);}}
  .body{{padding:clamp(20px,2.6vw,34px);}}
  .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:0 0 26px;}}
  .kpi{{background:var(--panel-2);border:1px solid var(--line);border-radius:10px;padding:14px 16px;}}
  .kpi .n{{font-size:clamp(22px,3vw,30px);font-weight:800;letter-spacing:-.02em;line-height:1;}}
  .kpi .n.alert{{color:var(--alert);}} .kpi .n.accent{{color:var(--accent);}}
  .kpi .l{{color:var(--muted);font-size:12px;margin-top:7px;line-height:1.35;}}
  h2{{font-size:13px;font-family:var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:30px 0 12px;font-weight:600;}}
  .chartwrap{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel-2);padding:16px;}}
  .bl{{fill:var(--ink);font-family:var(--sans);font-size:15px;font-weight:800;}}
  .bm{{fill:var(--accent-ink,var(--accent));font-family:var(--mono);font-size:12px;font-weight:700;}}
  @media (prefers-color-scheme:dark){{.bm{{fill:var(--accent);}}}}
  .bx{{fill:var(--muted);font-family:var(--mono);font-size:12px;}}
  .legend{{display:flex;gap:18px;flex-wrap:wrap;margin:12px 2px 0;font-size:12px;color:var(--muted);}}
  .legend i{{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;vertical-align:-1px;}}
  table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:6px;}}
  thead th{{text-align:right;font-family:var(--mono);font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--line);}}
  thead th:first-child{{text-align:left;}}
  td{{padding:8px 10px;border-bottom:1px solid var(--line);}}
  td.lab{{font-weight:600;}} td.num{{text-align:right;font-variant-numeric:tabular-nums;font-family:var(--mono);}}
  td.strong{{font-weight:800;}} td.muted{{color:var(--muted);}}
  tbody tr:last-child td{{border-bottom:none;}}
  .note{{color:var(--muted);font-size:12.5px;line-height:1.55;margin:10px 0 0;}}
  .reg{{background:var(--panel-2);border-left:3px solid var(--alert);border-radius:0 8px 8px 0;padding:12px 16px;margin:16px 0;font-size:13.5px;line-height:1.5;}}
  .foot{{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:12px;line-height:1.6;}}
  code{{font-family:var(--mono);font-size:.92em;background:var(--panel-2);padding:1px 5px;border-radius:4px;}}
  a{{color:var(--done);}}
</style>
<div class="wrap"><div class="sheet">
  <div class="head">
    <p class="eyebrow">World Energy Data · Decommissioning · Abandon stage (issue #777)</p>
    <h1 class="title">The Gulf of Mexico P&amp;A liability wave</h1>
    <p class="thesis"><b>{k['n_forward']:,} GoM boreholes are drilled but not yet permanently plugged</b>
    ({k['n_ta']:,} temporarily abandoned + {k['n_com']:,} completed/open). At the decommissioning
    model's GoM P&amp;A cost of <b>${per:.0f}–{k['shelf'].estimated_cost_musd:.0f}M</b> per shelf well
    (deepwater wells run higher, ~${k['deep'].estimated_cost_musd:.0f}M each), that is
    <b>{_b(k['total_forward_musd'])}&nbsp;–&nbsp;{_b(k['total_forward_shelf_musd'])}</b> of latent P&amp;A liability —
    and the {k['n_ta']:,} already-idled wells ({_b(k['total_ta_musd'])}) are the imminent, overdue crest.</p>
  </div>
  <div class="body">
    <div class="kpis">
      <div class="kpi"><div class="n alert">{k['n_forward']:,}</div><div class="l">Boreholes awaiting P&amp;A (TA + completed/open)</div></div>
      <div class="kpi"><div class="n">{_b(k['total_forward_musd'])}</div><div class="l">Latent liability floor @ ${per:.0f}M/well (GoM base)</div></div>
      <div class="kpi"><div class="n alert">{k['n_ta']:,}</div><div class="l">Temporarily abandoned = overdue Idle-Iron crest</div></div>
      <div class="kpi"><div class="n accent">{k['n_pa']:,}</div><div class="l">Already permanently plugged (wave to date)</div></div>
    </div>

    <h2>Forward liability wave — by idle / completion vintage</h2>
    <div class="chartwrap">{svg}</div>
    <div class="legend">
      <span><i style="background:var(--alert)"></i>Temporarily abandoned (imminent, overdue &gt;5&nbsp;yr rule)</span>
      <span><i style="background:var(--future)"></i>Completed / open (latent future P&amp;A)</span>
      <span>Bar label = borehole count · figure = liability @ ${per:.0f}M/well</span>
    </div>
    <p class="note">Vintage = the decade each borehole entered its current BSEE status
    (<code>BOREHOLE_STAT_DT</code>). Wells idled in earlier decades are the most overdue: the deeper
    the vintage, the longer the plug-or-justify clock has run.</p>

    <div class="reg"><b>Regulatory driver.</b> {idle_txt}. The {k['n_ta']:,} temporarily-abandoned
    boreholes are precisely the population this rule targets — each a deferred, not discharged, P&amp;A obligation.</div>

    <h2>Vintage roll-up</h2>
    <table>
      <thead><tr><th>Vintage decade</th><th>Temp. abandoned</th><th>Completed / open</th>
      <th>Forward P&amp;A wells</th><th>Liability @ ${per:.0f}M</th><th>Already plugged</th></tr></thead>
      <tbody>{''.join(trows)}
      <tr><td class="lab strong">Total</td><td class="num">{k['n_ta']:,}</td><td class="num">{k['n_com']:,}</td>
      <td class="num strong">{k['n_forward']:,}</td><td class="num strong">{_b(k['total_forward_musd'])}</td>
      <td class="num muted">{k['n_pa']:,}</td></tr>
      </tbody>
    </table>

    <h2>Per-well P&amp;A cost (decommissioning cost model, region = GoM)</h2>
    <p class="note">
      <code>well_p_and_a</code> = $8.0M base + $0.015M per m water depth × GoM multiplier 1.0.
      Reference points: base / shelf floor <b>${per:.0f}M</b> (depth term = 0);
      shelf ~60&nbsp;m <b>${k['shelf'].estimated_cost_musd:.1f}M</b>;
      shelf edge ~200&nbsp;m <b>${k['shelf_edge'].estimated_cost_musd:.0f}M</b>;
      deep water ~{k['dw_med_m']:.0f}&nbsp;m <b>${k['deep'].estimated_cost_musd:.0f}M</b>
      (model confidence: {html.escape(k['deep'].confidence)}). The <b>headline liability range prices the whole
      forward population at the shelf band</b> (${per:.0f}–{k['shelf'].estimated_cost_musd:.0f}M/well), where the
      GoM P&amp;A backlog overwhelmingly sits; the deepwater figure is per-well escalation, not applied to every
      well (the data does not carry a per-well depth to weight the mix). Cited P&amp;A cost benchmark, not a project quote.
    </p>

    <p class="note"><b>Forward P&amp;A demand context.</b> The
    <a href="../../docs/intervention-db/intervention-stats-brief.html">GoM intervention-access brief</a>
    already flags heavy dead-well work — tubing pull / recompletion / <b>P&amp;A</b> — as forward-looking
    rig-day demand across every water-depth band, with the deep bands short of GoM-resident heavy-intervention
    units (e.g. 5,000–10,000&nbsp;ft: ~4.4× the resident rig-days). That access gap is the SUPPLY side of the same
    wave this page prices on the LIABILITY side; the demand figures are cited from the brief, not recomputed here.</p>

    <div class="foot">
      <b>Source.</b> BSEE curated borehole inventory <code>data/modules/bsee/current/wells/well_data.csv</code>
      — {k['n_total']:,} boreholes. Status mix: PA {scget('PA'):,} · ST {scget('ST'):,} · COM {scget('COM'):,}
      · TA {scget('TA'):,} · CNL {scget('CNL'):,} · other {scget('DSI')+scget('AST')+scget('DRL')+scget('APD'):,}.
      Sidetrack (<code>ST</code>) and cancelled/permit (<code>CNL</code>/<code>DSI</code>/<code>APD</code>) boreholes are
      excluded from the forward P&amp;A count (not standalone plug units).<br>
      <b>Data limits.</b> Per-well <code>WATER_DEPTH</code> is populated for only {k['n_wd']:,} of {k['n_total']:,}
      boreholes, so the cost model's depth term cannot be applied per well; every $ figure is priced at the GoM
      P&amp;A base (${per:.0f}M) as a floor, with the shelf-to-deepwater band shown separately. Counts are boreholes,
      not distinct wellbores (a re-entered well may carry multiple status records). "Completed/open" includes active
      producers whose P&amp;A obligation is real but not yet due; the temporarily-abandoned tier is the imminent
      subset. Cost factors are parametric industry benchmarks (model confidence: medium), not project estimates.<br>
      Generated by <code>scripts/decommissioning/build_pa_liability_wave.py</code> · cost model
      <code>worldenergydata.decommissioning.cost_model</code> · regs <code>{html.escape(idle.reference_doc) if idle else 'BSEE NTL 2018-N02'}</code>.
    </div>
  </div>
</div></div>
"""


if __name__ == "__main__":
    main()
