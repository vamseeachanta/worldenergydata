"""ABOUTME: Build the regional (facility-level) decommissioning-liability front door.
ABOUTME: Prices the curated offshore-asset portfolio by region x asset type.

Reads the curated production-facility inventory
(``data/modules/offshore_assets/curated/production_facilities.csv`` — 836
facilities) and prices every facility with the parametric
``DecommissioningCostEstimator`` (region multipliers gom 1.0 / ncs 1.3 /
ukcs 1.25 / brazil 1.1 / west_africa 1.15).

The honest, non-obvious story: two forces set the bill and pull opposite ways.
Per identical asset the North Sea costs 25-30% more (the region multiplier), but
the money is in floating production — 159 FPSOs carry $14.8B of the $17.5B
modeled liability, concentrated in Brazil and West-Africa deepwater, NOT the
North Sea's cheap-to-remove fixed jackets (the asset-mix effect). At portfolio
level the mix dominates the multiplier: mean $/facility runs GoM > NCS > UKCS.

Outputs (self-contained, no external assets):
    reports/decommissioning/regional_liability.csv
    reports/decommissioning/regional_liability.html

FLAG-DON'T-FAKE: every number below is computed from the source file via
``facility_liability.price_portfolio``. 421 of 836 facilities are modeled; the
414 in regions with no cost multiplier are excluded, and the 1 Artificial Island
is not a priced offshore-structure removal. Costs use weight=0 and the depth
floor (per-facility weight is not carried); the FPSO base cost is low-confidence.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(
    0, str(PROJECT_ROOT / "packages" / "worldenergydata-decommissioning" / "src")
)
from worldenergydata.decommissioning.cost_model import (  # noqa: E402
    DecommissioningCostEstimator,
)
from worldenergydata.decommissioning.facility_liability import (  # noqa: E402
    price_portfolio,
)

SRC = (
    PROJECT_ROOT
    / "data"
    / "modules"
    / "offshore_assets"
    / "curated"
    / "production_facilities.csv"
)
OUT_CSV = PROJECT_ROOT / "reports" / "decommissioning" / "regional_liability.csv"
OUT_HTML = PROJECT_ROOT / "reports" / "decommissioning" / "regional_liability.html"

REGION_LABEL = {
    "gom": "Gulf of Mexico",
    "ncs": "Norway (NCS)",
    "ukcs": "UK (UKCS)",
    "brazil": "Brazil",
    "west_africa": "West Africa",
}
REGION_MULT = {"gom": 1.0, "ncs": 1.3, "ukcs": 1.25, "brazil": 1.1, "west_africa": 1.15}
ASSET_LABEL = {
    "fpso": "FPSO / floating production",
    "spar": "Spar",
    "tlp": "TLP",
    "jacket": "Fixed jacket",
    "subsea_tree": "Subsea tree",
}
ASSET_COLOR = {
    "fpso": "var(--accent)",
    "spar": "var(--done)",
    "tlp": "var(--good)",
    "jacket": "var(--future)",
    "subsea_tree": "var(--muted)",
}
ASSET_ORDER = ["fpso", "spar", "tlp", "jacket", "subsea_tree"]


def _b(musd: float) -> str:
    return f"${musd / 1000:.1f}B"


def main() -> None:
    df = pd.read_csv(SRC)
    n_total = len(df)
    res = price_portfolio(df)

    # Like-for-like reference: one identical asset (jacket @ 100 m) across regions,
    # showing the pure multiplier premium with the asset mix held constant.
    est = DecommissioningCostEstimator()
    llf = {
        reg: est.estimate("jacket", water_depth_m=100.0, region=reg).estimated_cost_musd
        for reg in REGION_MULT
    }

    # ---- Write per-facility CSV ---------------------------------------------
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    counts = res["counts"]
    with OUT_CSV.open("w", newline="") as fh:
        fh.write(
            "# Regional decommissioning liability (facility-level, offshore-assets)\n"
            f"# source: {SRC.relative_to(PROJECT_ROOT)} | {n_total} facilities\n"
            f"# modeled={counts['modeled']} (5 regions with a cost multiplier);"
            f" unmodeled-region={counts['unmodeled_region']} excluded;"
            f" unmapped-asset={counts['unmapped_asset']} (Artificial Island) excluded\n"
            f"# total modeled liability = {_b(res['total_musd'])} ({res['total_musd']:,.0f} MUSD)\n"
            "# pricing: DecommissioningCostEstimator, weight=0, depth floor; FPSO base low-confidence\n"
        )
    pd.DataFrame(res["rows"]).to_csv(OUT_CSV, mode="a", index=False)

    html_str = render_html(n_total=n_total, res=res, llf=llf)
    OUT_HTML.write_text(html_str, encoding="utf-8")

    print(
        f"facilities={n_total} modeled={counts['modeled']} "
        f"unmodeled-region={counts['unmodeled_region']} "
        f"unmapped-asset={counts['unmapped_asset']}"
    )
    print(f"TOTAL modeled liability = {_b(res['total_musd'])} ({res['total_musd']:,.0f} MUSD)")
    for reg, d in sorted(res["by_region"].items(), key=lambda kv: -kv[1]["sum_musd"]):
        print(f"  {reg:12s} {_b(d['sum_musd'])}  n={d['count']}")
    for a in ASSET_ORDER:
        d = res["by_asset"].get(a)
        if d:
            print(f"  {a:12s} {_b(d['sum_musd'])}  n={d['count']}")
    print(f"wrote {OUT_CSV.relative_to(PROJECT_ROOT)} and {OUT_HTML.relative_to(PROJECT_ROOT)}")


def render_html(*, n_total: int, res: dict, llf: dict) -> str:
    by_region = res["by_region"]
    by_asset = res["by_asset"]
    means = res["mean_per_facility_by_region"]
    counts = res["counts"]
    total = res["total_musd"]

    # region x asset stacked $ bars, regions ordered by total liability desc
    reg_order = sorted(by_region, key=lambda r: -by_region[r]["sum_musd"])
    # per-facility rows aggregated into region x asset $ matrix
    rows_df = pd.DataFrame(res["rows"])
    mat = (
        rows_df.groupby(["region", "asset"])["cost_musd"].sum().unstack(fill_value=0.0)
    )
    max_reg = max(by_region[r]["sum_musd"] for r in reg_order)

    bar_w, gap, top, bottom, left = 118, 40, 30, 66, 8
    chart_w = left + len(reg_order) * (bar_w + gap) + 20
    chart_h = 320
    plot_h = chart_h - top - bottom
    bars = []
    x = left + 10
    for reg in reg_order:
        total_reg = by_region[reg]["sum_musd"]
        full_h = plot_h * (total_reg / max_reg)
        baseline = top + plot_h
        y_cursor = baseline
        for a in ASSET_ORDER:
            v = float(mat.loc[reg, a]) if a in mat.columns and reg in mat.index else 0.0
            if v <= 0:
                continue
            seg_h = full_h * (v / total_reg)
            y_cursor -= seg_h
            bars.append(
                f'<rect x="{x}" y="{y_cursor:.1f}" width="{bar_w}" height="{seg_h:.1f}" '
                f'fill="{ASSET_COLOR[a]}" rx="2">'
                f"<title>{html.escape(REGION_LABEL[reg])} · {html.escape(ASSET_LABEL[a])}: {_b(v)}</title></rect>"
            )
        top_y = baseline - full_h
        bars.append(
            f'<text x="{x + bar_w / 2:.0f}" y="{top_y - 20:.0f}" text-anchor="middle" class="bl">{_b(total_reg)}</text>'
            f'<text x="{x + bar_w / 2:.0f}" y="{top_y - 6:.0f}" text-anchor="middle" class="bm">n={by_region[reg]["count"]}</text>'
            f'<text x="{x + bar_w / 2:.0f}" y="{baseline + 20:.0f}" text-anchor="middle" class="bx">{html.escape(REGION_LABEL[reg])}</text>'
            f'<text x="{x + bar_w / 2:.0f}" y="{baseline + 36:.0f}" text-anchor="middle" class="bxm">×{REGION_MULT[reg]:g} · ${means[reg]:.0f}M/fac</text>'
        )
        x += bar_w + gap
    svg = (
        f'<svg viewBox="0 0 {chart_w} {chart_h}" width="100%" preserveAspectRatio="xMidYMid meet" '
        f'role="img" aria-label="Modeled decommissioning liability by region and asset type">'
        + "".join(bars)
        + f'<line x1="{left}" y1="{top + plot_h}" x2="{chart_w - 10}" y2="{top + plot_h}" stroke="var(--line)" stroke-width="1"/>'
        + "</svg>"
    )

    legend = "".join(
        f'<span><i style="background:{ASSET_COLOR[a]}"></i>{html.escape(ASSET_LABEL[a])}</span>'
        for a in ASSET_ORDER
        if a in by_asset
    )

    # asset roll-up table (money-is-in-FPSO)
    arows = []
    for a in ASSET_ORDER:
        d = by_asset.get(a)
        if not d:
            continue
        share = 100 * d["sum_musd"] / total
        arows.append(
            "<tr>"
            f'<td class="lab"><i style="background:{ASSET_COLOR[a]}"></i>{html.escape(ASSET_LABEL[a])}</td>'
            f'<td class="num">{d["count"]:,}</td>'
            f'<td class="num strong">{_b(d["sum_musd"])}</td>'
            f'<td class="num muted">{share:.0f}%</td>'
            "</tr>"
        )

    # region roll-up table
    rrows = []
    for reg in reg_order:
        d = by_region[reg]
        rrows.append(
            "<tr>"
            f'<td class="lab">{html.escape(REGION_LABEL[reg])}</td>'
            f'<td class="num muted">×{REGION_MULT[reg]:g}</td>'
            f'<td class="num">{d["count"]:,}</td>'
            f'<td class="num strong">{_b(d["sum_musd"])}</td>'
            f'<td class="num muted">${means[reg]:.1f}M</td>'
            "</tr>"
        )

    fpso = by_asset["fpso"]
    fpso_share = 100 * fpso["sum_musd"] / total
    gom_j = llf["gom"]
    ncs_prem = 100 * (llf["ncs"] / gom_j - 1)
    ukcs_prem = 100 * (llf["ukcs"] / gom_j - 1)

    return f"""<meta charset="utf-8">
<title>Regional Decommissioning Liability</title>
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
  .crumb{{font-size:12.5px;margin:0 0 12px;}} .crumb a{{color:var(--done);text-decoration:none;}}
  .eyebrow{{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin:0 0 8px;}}
  .title{{font-size:clamp(26px,3.6vw,40px);font-weight:800;letter-spacing:-.02em;margin:0;line-height:1.03;text-wrap:balance;}}
  .thesis{{color:var(--ink);margin:14px 0 0;font-size:clamp(15px,1.6vw,18px);max-width:74ch;line-height:1.5;}}
  .thesis b{{color:var(--accent-ink,var(--accent));}}
  @media (prefers-color-scheme:dark){{.thesis b{{color:var(--accent);}}}}
  .body{{padding:clamp(20px,2.6vw,34px);}}
  .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:0 0 26px;}}
  .kpi{{background:var(--panel-2);border:1px solid var(--line);border-radius:10px;padding:14px 16px;}}
  .kpi .n{{font-size:clamp(22px,3vw,30px);font-weight:800;letter-spacing:-.02em;line-height:1;}}
  .kpi .n.accent{{color:var(--accent);}} .kpi .n.done{{color:var(--done);}}
  .kpi .l{{color:var(--muted);font-size:12px;margin-top:7px;line-height:1.35;}}
  h2{{font-size:13px;font-family:var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:30px 0 12px;font-weight:600;}}
  .chartwrap{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel-2);padding:16px;}}
  .bl{{fill:var(--ink);font-family:var(--sans);font-size:15px;font-weight:800;}}
  .bm{{fill:var(--muted);font-family:var(--mono);font-size:11px;}}
  .bx{{fill:var(--ink);font-family:var(--sans);font-size:12.5px;font-weight:600;}}
  .bxm{{fill:var(--muted);font-family:var(--mono);font-size:10.5px;}}
  .legend{{display:flex;gap:18px;flex-wrap:wrap;margin:12px 2px 0;font-size:12px;color:var(--muted);}}
  .legend i,.lab i{{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;vertical-align:-1px;}}
  .callout{{background:var(--panel-2);border-left:3px solid var(--accent);border-radius:0 8px 8px 0;padding:14px 18px;margin:16px 0;font-size:14px;line-height:1.55;}}
  .callout b{{color:var(--accent-ink,var(--accent));}}
  @media (prefers-color-scheme:dark){{.callout b{{color:var(--accent);}}}}
  table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:6px;}}
  thead th{{text-align:right;font-family:var(--mono);font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--line);}}
  thead th:first-child{{text-align:left;}}
  td{{padding:8px 10px;border-bottom:1px solid var(--line);}}
  td.lab{{font-weight:600;}} td.num{{text-align:right;font-variant-numeric:tabular-nums;font-family:var(--mono);}}
  td.strong{{font-weight:800;}} td.muted{{color:var(--muted);}}
  tbody tr:last-child td{{border-bottom:none;}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:24px;}}
  @media (max-width:720px){{.grid2{{grid-template-columns:1fr;}}}}
  .note{{color:var(--muted);font-size:12.5px;line-height:1.55;margin:10px 0 0;}}
  .foot{{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:12px;line-height:1.6;}}
  code{{font-family:var(--mono);font-size:.92em;background:var(--panel-2);padding:1px 5px;border-radius:4px;}}
  a{{color:var(--done);}}
</style>
<div class="wrap"><div class="sheet">
  <div class="head">
    <p class="crumb"><a href="../capabilities/insights.html">&larr; Life-cycle insights hub</a> &middot; <a href="pa-liability-wave.html">GoM P&amp;A liability wave</a></p>
    <p class="eyebrow">World Energy Data · Decommissioning · Regional liability</p>
    <h1 class="title">Two forces set the decommissioning bill — and they pull opposite ways</h1>
    <p class="thesis">Per <em>identical</em> asset the North Sea costs 25–30% more to remove (the regional multiplier).
    But the money is in floating production: <b>{fpso["count"]} FPSOs carry {_b(fpso["sum_musd"])} of the {_b(total)} modeled liability</b>
    ({fpso_share:.0f}%), concentrated in Brazil and West-Africa deepwater — <em>not</em> the North Sea's cheap-to-remove fixed jackets.
    At portfolio level the asset mix, not the multiplier, sets the realized bill.</p>
  </div>
  <div class="body">
    <div class="kpis">
      <div class="kpi"><div class="n">{_b(total)}</div><div class="l">Total modeled liability ({counts["modeled"]} facilities, 5 regions)</div></div>
      <div class="kpi"><div class="n accent">{_b(fpso["sum_musd"])}</div><div class="l">FPSO share = {fpso_share:.0f}% of the bill ({fpso["count"]} units)</div></div>
      <div class="kpi"><div class="n done">+{ncs_prem:.0f}% / +{ukcs_prem:.0f}%</div><div class="l">NCS / UKCS like-for-like premium per identical jacket vs GoM</div></div>
      <div class="kpi"><div class="n">{counts["modeled"]}/{n_total}</div><div class="l">Facilities modeled; {counts["unmodeled_region"]} unmodeled-region excluded</div></div>
    </div>

    <h2>Modeled liability by region &times; asset type</h2>
    <div class="chartwrap">{svg}</div>
    <div class="legend">{legend}<span>Bar = total $ liability · label under bar = region multiplier &amp; mean $/facility</span></div>
    <p class="note">Regions are ordered by total modeled liability. The stacked segments are the asset-type $ split within each
    region — the tall floating-production (FPSO) blocks in Brazil and West Africa, not the North Sea's higher multiplier,
    are what set the totals.</p>

    <div class="callout"><b>Multiplier vs mix.</b> Hold the asset constant — one jacket at 100&nbsp;m — and the pure regional
    premium is exactly the multiplier: <b>NCS +{ncs_prem:.0f}%</b> and <b>UKCS +{ukcs_prem:.0f}%</b> over GoM.
    Yet the realized <em>mean $/facility</em> inverts that ranking — GoM&nbsp;${means["gom"]:.1f}M &gt; NCS&nbsp;${means["ncs"]:.1f}M
    &gt; UKCS&nbsp;${means["ukcs"]:.1f}M — because the GoM sample carries a heavier floating-production mix than the North Sea's
    fixed jackets. The mix dominates the multiplier. So "the North Sea is most expensive" is true per structure and
    <em>false</em> at portfolio level.</p>

    <div class="grid2">
      <div>
        <h2>By asset type — the money is floating</h2>
        <table>
          <thead><tr><th>Asset type</th><th>n</th><th>Liability</th><th>Share</th></tr></thead>
          <tbody>{"".join(arows)}
          <tr><td class="lab strong">Total</td><td class="num strong">{counts["modeled"]:,}</td>
          <td class="num strong">{_b(total)}</td><td class="num muted">100%</td></tr>
          </tbody>
        </table>
      </div>
      <div>
        <h2>By region — multiplier &amp; realized mean</h2>
        <table>
          <thead><tr><th>Region</th><th>Mult</th><th>n</th><th>Liability</th><th>Mean/fac</th></tr></thead>
          <tbody>{"".join(rrows)}</tbody>
        </table>
      </div>
    </div>

    <div class="foot">
      <b>Source.</b> Curated offshore-asset inventory
      <code>data/modules/offshore_assets/curated/production_facilities.csv</code> — {n_total:,} facilities.
      <b>{counts["modeled"]} modeled</b> across the five regions the cost model carries a multiplier for
      (GoM&nbsp;×1.0, NCS&nbsp;×1.3, UKCS&nbsp;×1.25, Brazil&nbsp;×1.1, West&nbsp;Africa&nbsp;×1.15);
      <b>{counts["unmodeled_region"]} facilities in unmodeled regions are excluded</b> (no cost factor), and the
      {counts["unmapped_asset"]} Artificial Island is not a priced offshore-structure removal.<br>
      <b>Data limits.</b> Facilities are priced at the cost model's base + water-depth floor with
      <b>weight = 0</b> (per-facility topside weight is not carried), so totals are conservative on the tonnage term.
      The <b>FPSO base cost is model confidence "low"</b>; because FPSOs dominate the bill, the headline total is
      most sensitive to that one factor. Region multipliers and asset base costs are parametric industry benchmarks,
      not project quotes.<br>
      Generated by <code>scripts/decommissioning/build_regional_liability.py</code> · logic
      <code>worldenergydata.decommissioning.facility_liability</code> · cost model
      <code>worldenergydata.decommissioning.cost_model</code>.
    </div>
  </div>
</div></div>
"""


if __name__ == "__main__":
    main()
