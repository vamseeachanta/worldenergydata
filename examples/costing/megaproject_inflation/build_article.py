"""Build the article "Offshore mega-project cost inflation over time" (r2) from the public series in data/.

Inputs beside this file: data/*.csv (FRED downloads, recorded in sources.csv), article.body.html (the prose, with
{{key}} placeholders that the build fills from the computed results), pictures/*.svg (the opening picture). The
quoted Upstream Capital Costs Index values, the sanction estimates, the contract awards and the dated cost statements
are read from the repository's curated cost files (projects.py; hashes in project_sources.csv).

Outputs in out/: the article page, results.json, and for every figure a static SVG and the CSV of its data.

Checks (the build fails on any of them):
- sources: every saved file matches its SHA-256 in sources.csv;
- architecture limits: "What we did" <= 70 words, "Why it matters" <= 70 (prompt line apart, <= 25), "What is inside"
  <= 50, introduction 110 to 190 words; no digits in the first two parts; the introduction opens on its subject,
  never on who asked (no "asked"); body 500 to 800 words; at most 2 hypotheses (a public data piece); infographic
  <= 70 words and <= 8 numbers, each also in the body (its chart and caption line apart);
- citations: every [n] is a reference and every reference is cited;
- leak check on the visible text: local paths, @-mentions, question marks and em dashes, plus the patterns of an
  optional private file (names that must never appear in a public page).

Usage (from the repository root):
  python examples/costing/megaproject_inflation/build_article.py --pin <commit> [--built "17 Nov 2026, 22:00 UTC"]
      [--leak-file <private pattern file>]
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import hashlib
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import inflation as f  # noqa: E402
import projects as P  # noqa: E402

REPO = HERE.parents[2]
UCCI_FILE = REPO / "data" / "modules" / "cost" / "curated" / "cost_component_timeseries.csv"
OUT = HERE / "out"
TITLE = "Offshore mega-project cost inflation over time"
REPO_URL = "https://github.com/vamseeachanta/worldenergydata"
PROMPT_PATH = "examples/costing/megaproject_inflation/PROMPT.md"

LABELS = {
    "cpi": "Consumer prices (CPI)", "drilling": "Drilling oil and gas wells", "support": "Support activities",
    "machinery": "Oil and gas field machinery", "steel_mill": "Steel mill products", "steel_pipe": "Steel pipe and tube",
    "shipbuilding": "Ship building and repairing", "engineering": "Engineering services", "brent": "Brent crude oil",
    "blend": "Capital blend (seven indexes)", "two": "Two-index blend",
}
COMPONENTS = ["drilling", "steel_pipe", "steel_mill", "machinery", "shipbuilding", "support", "engineering"]

# Generic checks on the visible text; a team keeps its own names (people, clients, hosts) in a private pattern file
# passed with --leak-file, one regular expression per line.
LEAK = [r"\b[A-Za-z]:[\\/]", r"/mnt/", r"\\\\", r"(?<![\w.])@[A-Za-z]", r"\?", "—"]

# Quoted index values left out of Figure 3, Table A5 and every number built on them, by quarter, until their source
# sentence is read again. The reference stays in the list and Appendix A names it.
SET_ASIDE = {"2013Q3"}

# Publication dates of the press articles whose title in the curated file carries none, by quoted quarter.
ARTICLE_DATES = {"2006Q4": "1 Mar 2007", "2008Q3": "11 Dec 2008", "2010Q3": "9 Dec 2010", "2012Q1": "2 Jul 2012",
                 "2019Q3": "2 Dec 2019", "2019Q4": "2 Mar 2020", "2020Q2": "7 Sep 2020", "2020Q3": "7 Dec 2020"}


def dated(u: dict) -> dict:
    """The quoted point with its article date added to the source title, as in "IHS CERA press release (11 Dec 2008)"."""
    d = ARTICLE_DATES.get(u["quarter"])
    return dict(u, source=f"{u['source']} ({d})") if d and "(" not in u["source"] else u


# ------------------------------------------------------------------ data and results
def load() -> dict:
    rows = list(csv.DictReader((HERE / "sources.csv").open(encoding="utf-8")))
    bad = []
    for r in rows:
        p = UCCI_FILE if r["key"] == "ucci_quoted" else HERE / r["local_file"]
        if hashlib.sha256(p.read_bytes()).hexdigest() != r["sha256"]:
            bad.append(r["key"])
    if bad:
        raise SystemExit(f"sources check failed (hash mismatch): {bad}")
    monthly = {r["key"]: f.read_fred(HERE / r["local_file"]) for r in rows if r["key"] != "ucci_quoted"}
    return {"sources": rows, "monthly": monthly, "ucci": [dated(u) for u in f.read_ucci_quoted(UCCI_FILE)],
            "projects": P.load()}


def pct(x: float, d: int = 1) -> float:
    return round(100.0 * x, d)


def compute(d: dict) -> dict:
    M = d["monthly"]
    A = {k: f.annual_means(v) for k, v in M.items()}
    R = {k: f.rebase(v, f.BASE_YEAR) for k, v in A.items()}
    Rm = {k: {ym: 100.0 * v / A[k][f.BASE_YEAR] for ym, v in M[k].items()} for k in M}
    B, B2 = f.blend(R, f.BLEND_WEIGHTS), f.blend(R, f.TWO_INDEX_WEIGHTS)
    R["blend"], R["two"] = B, B2
    real = {k: f.real(R[k], R["cpi"]) for k in R if k != "cpi"}
    y0, y1 = f.BASE_YEAR, f.LAST_FULL_YEAR
    res: dict = {"base_year": y0, "last_full_year": y1}
    res["index"] = {}
    for k in COMPONENTS + ["blend", "two", "brent", "cpi"]:
        r = real.get(k, R[k])
        res["index"][k] = {
            "label": LABELS[k], "value_last": round(R[k][y1], 1), "rise_pct": pct(R[k][y1] / 100.0 - 1.0),
            "cagr_pct": pct(f.cagr(R[k], y0, y1), 2), "real_cagr_pct": pct(f.cagr(r, y0, y1), 2),
            "cycles": {lab: {"nominal_pct": pct(f.change(R[k], a, b)), "real_pct": pct(f.change(r, a, b))}
                       for lab, a, b in f.CYCLES}}
    # monthly turning points named in the body
    def turn(k, a, b, fn):
        ks = [x for x in M[k] if a <= x <= b]
        return fn(ks, key=M[k].get)
    t = {}
    p = turn("drilling", "2012-01", "2015-12", max)
    q = turn("drilling", p, "2018-12", min)
    t["drilling_bust"] = {"from": p, "to": q, "change_pct": pct(M["drilling"][q] / M["drilling"][p] - 1)}
    q = turn("steel_mill", "2020-01", "2021-12", min)
    p = turn("steel_mill", q, "2024-12", max)
    t["steel_boom"] = {"from": q, "to": p, "change_pct": pct(M["steel_mill"][p] / M["steel_mill"][q] - 1)}
    res["turns"] = t
    # 2026 to date against the 2025 mean
    months26 = sorted(ym for ym in M["cpi"] if ym.startswith("2026"))
    ytd = {k: sum(M[k][m] for m in months26) / len(months26) / A[k][y1] - 1 for k in M}
    bl26 = sum(w * (sum(M[k][m] for m in months26) / len(months26)) / A[k][y0] * 100 for k, w in f.BLEND_WEIGHTS.items())
    res["ytd"] = {"months": f"{months26[0]} to {months26[-1]}", "steel_mill_pct": pct(ytd["steel_mill"]),
                  "cpi_pct": pct(ytd["cpi"]), "blend_pct": pct(bl26 / B[y1] - 1), "brent_pct": pct(ytd["brent"])}
    # oil price link
    br, dr = f.yoy(A["brent"]), f.yoy(A["drilling"])
    ys = [y for y in range(1988, y1 + 1) if y in br and y in dr and (y - 1) in br]
    corr = {"drilling_lag1": round(f.pearson([br[y - 1] for y in ys], [dr[y] for y in ys]), 2),
            "drilling_same": round(f.pearson([br[y] for y in ys], [dr[y] for y in ys]), 2), "drilling_years": len(ys),
            "drilling_first": ys[0], "drilling_last": ys[-1]}
    for k in ("steel_mill", "machinery", "support", "shipbuilding", "engineering"):
        dk = f.yoy(A[k])
        yk = [y for y in range(1999, y1 + 1) if y in br and y in dk]
        corr[k] = round(f.pearson([br[y] for y in yk], [dk[y] for y in yk]), 2)
        corr[k + "_lag1"] = round(f.pearson([br[y - 1] for y in yk], [dk[y] for y in yk]), 2)
        corr[k + "_years"] = len(yk)
        corr["others_first"], corr["others_last"] = yk[0], yk[-1]
    res["corr"] = corr
    # quarterly blends against quoted UCCI values
    Bm = f.blend(Rm, f.BLEND_WEIGHTS)
    B2m = f.blend(Rm, f.TWO_INDEX_WEIGHTS)
    Bq, B2q = f.quarter_means(Bm), f.quarter_means(B2m)
    uc = []
    for u in d["ucci"]:
        if u["quarter"] in SET_ASIDE:
            continue
        uc.append(dict(u, blend=round(Bq[u["quarter"]], 1), two=round(B2q[u["quarter"]], 1),
                       gap_pct=pct(u["value"] / Bq[u["quarter"]] - 1), gap_two_pct=pct(u["value"] / B2q[u["quarter"]] - 1)))
    boom = [u for u in uc if "2008" <= u["quarter"][:4] <= "2013"]
    calm = [u for u in uc if u not in boom]
    res["ucci"] = {"points": uc, "set_aside": [u for u in d["ucci"] if u["quarter"] in SET_ASIDE],
                   "boom_n": len(boom), "boom_first": int(boom[0]["quarter"][:4]), "boom_last": int(boom[-1]["quarter"][:4]),
                   "boom_gap_min": min(u["gap_pct"] for u in boom),
                   "boom_gap_max": max(u["gap_pct"] for u in boom),
                   "calm_gap_min": min(u["gap_pct"] for u in calm), "calm_gap_max": max(u["gap_pct"] for u in calm),
                   "boom_two_min": min(u["gap_two_pct"] for u in boom), "boom_two_max": max(u["gap_two_pct"] for u in boom),
                   "calm_two_min": min(u["gap_two_pct"] for u in calm), "calm_two_max": max(u["gap_two_pct"] for u in calm),
                   "peak": next(u for u in uc if u["quarter"] == "2008Q3"),
                   "boom_under_min": min(pct(Bq[u["quarter"]] / u["value"] - 1) for u in boom),
                   "boom_under_max": max(pct(Bq[u["quarter"]] / u["value"] - 1) for u in boom),
                   "gap_2006q3_pct": pct(next(u for u in uc if u["quarter"] == "2006Q4")["value"] / Bq["2006Q3"] - 1)}
    # escalation over execution windows
    esc = {}
    variants = {"blend": B, "two": B2,
                "equal": f.blend(R, {k: 1 / 7 for k in f.BLEND_WEIGHTS})}
    for n in (5, 8):
        for name, ix in variants.items():
            for basis, series in (("nominal", ix), ("real", f.real(ix, R["cpi"]))):
                e = f.escalation_by_fid(series, n)
                v = list(e.values())
                esc[f"{name}_{basis}_{n}"] = {
                    "n_windows": len(v), "fid_first": min(e), "fid_last": max(e),
                    "p10": pct(f.percentile(v, 10)), "p50": pct(f.percentile(v, 50)), "p90": pct(f.percentile(v, 90)),
                    "max": pct(max(v)), "max_fid": max(e, key=e.get), "min": pct(min(v)), "min_fid": min(e, key=e.get),
                    "by_fid": {str(s): pct(x) for s, x in e.items()}}
    # flat spend profile as a sensitivity on the main blend
    for n in (5, 8):
        Br = f.real(B, R["cpi"])
        fids = [int(x) for x in esc[f"blend_real_{n}"]["by_fid"]]
        flat = {s: sum(Br[s + k] / Br[s] for k in range(n)) / n - 1 for s in fids}
        v = list(flat.values())
        esc[f"flat_real_{n}"] = {"p50": pct(f.percentile(v, 50)), "p90": pct(f.percentile(v, 90))}
    for n in (5, 8):
        e = esc[f"blend_real_{n}"]
        e["contingency_pts"] = round(e["p90"] - e["p50"], 1)
    res["esc"] = esc
    # project-level view from the curated public records: award value against the sanction estimate, and the final
    # figure against the sanction estimate beside the capital blend (nominal) over the project's own years
    pj = d["projects"]
    cov = P.coverage(pj["sanctioned"], pj["awards"])
    out = P.outturn(pj["trails"], pj["qualifiers"])
    for o in out:
        if o["final_year"] > y1:
            raise SystemExit(f"final statement after {y1}: {o['project']}")
        o["market_pct"] = 100.0 * P.market_escalation(B, o["sanction_year"], o["final_year"], f.window_escalation)
    comp = [o for o in out if o["computable"]]
    boom = [o for o in comp if 2009 <= o["sanction_year"] <= 2013]
    bust = [o for o in comp if o["sanction_year"] == 2015]
    above = lambda o: o["change_pct"] > 0 and o["bound"] != "at most"  # noqa: E731
    below = lambda o: o["change_pct"] < 0 and o["bound"] != "at least"  # noqa: E731
    res["projects"] = {
        "counts": P.award_counts(pj["awards"]), "summary": P.summary(cov, out), "confirm_by": P.CONFIRM_BY,
        "coverage": cov, "outturn": out,
        "boom": {"n": len(boom), "above": sum(above(o) for o in boom), "below": sum(below(o) for o in boom)},
        "bust": {"n": len(bust), "below": sum(below(o) for o in bust)},
        "market_min": min(o["market_pct"] for o in out), "market_max": max(o["market_pct"] for o in out),
        "market_bb_min": min(o["market_pct"] for o in boom + bust), "market_bb_max": max(o["market_pct"] for o in boom + bust),
        "read": sorted({r["ACCESSED_DATE"] for t in ("sanctioned", "awards", "trails") for r in pj[t]}),
        "hashed": {r["file"]: r["hashed_utc"] for r in pj["record"].values()}}
    res["series"] = {"annual": {k: {str(y): round(v, 3) for y, v in R[k].items() if y >= 1997} for k in R},
                     "real": {k: {str(y): round(v, 3) for y, v in real[k].items() if y >= 1997} for k in real},
                     "monthly": {k: {ym: round(v, 3) for ym, v in Rm[k].items() if ym >= "2000-01"} for k in Rm},
                     "blend_q": {q: round(v, 3) for q, v in Bq.items() if q >= "2000"},
                     "two_q": {q: round(v, 3) for q, v in B2q.items() if q >= "2000"}}
    return res


# ------------------------------------------------------------------ figures
STYLE_LIGHT = (".s1{stroke:#245c94}.f1{fill:#245c94}.s2{stroke:#1fa596}.f2{fill:#1fa596}.ref{stroke:#6b7780}"
               ".fref{fill:#6b7780}.grid{stroke:#e3e8ec}.axis{stroke:#8a969e}.band{fill:#eef4f8}.ring{stroke:#ffffff}"
               ".s3{stroke:#e69f00}.f3{fill:#e69f00}.rim{stroke:#0b3d5c}.ring2{fill:#ffffff;stroke:#245c94}"
               "text{font:12px 'Segoe UI',Helvetica,Arial,sans-serif;fill:#26323a}.muted{fill:#5a6b76}")


def sgn(v: float, d: int = 1) -> str:
    """Signed number with the true minus sign; zero carries no sign."""
    t = f"{abs(v):.{d}f}"
    if float(t) == 0:
        return t
    return ("+" if v > 0 else "\u2212") + t


def esc_(s) -> str:
    return html.escape(str(s), quote=True)


def svg_open(w, h, title, fid):
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-labelledby="{fid}t" class="viz">'
            f'<title id="{fid}t">{esc_(title)}</title>')


def nice_ticks(lo, hi, step):
    v = lo
    out = []
    while v <= hi + 1e-9:
        out.append(v)
        v += step
    return out


def fig_real_bars(res) -> tuple[str, list[list]]:
    keys = sorted(COMPONENTS + ["blend"], key=lambda k: res["index"][k]["real_cagr_pct"], reverse=True)
    w, rowh, left, right, top = 640, 30, 210, 70, 26
    h = top + rowh * len(keys) + 52
    lo, hi = -1.0, 3.0
    sx = lambda v: left + (v - lo) / (hi - lo) * (w - left - right)  # noqa: E731
    out = [svg_open(w, h, "Growth above CPI, per year, 2000 to 2025, by index", "f2")]
    for t in nice_ticks(lo, hi, 1.0):
        out.append(f'<line class="grid" x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 46}"/>'
                   f'<text class="muted" x="{sx(t):.1f}" y="{h - 30}" text-anchor="middle">{sgn(t, 0)} %</text>')
    rows = []
    for i, k in enumerate(keys):
        v = res["index"][k]["real_cagr_pct"]
        y = top + i * rowh
        x0, x1 = sorted((sx(0), sx(v)))
        cls = "f2" if k == "blend" else "f1"
        tip = (f"{LABELS[k]}: {sgn(v, 2)} % a year above CPI; nominal {res['index'][k]['cagr_pct']:.2f} % a year; "
               f"2025 value {res['index'][k]['value_last']:.1f} (2000 = 100)")
        out.append(f'<g class="hit" tabindex="0" data-tip="{esc_(tip)}"><title>{esc_(tip)}</title>'
                   f'<rect x="0" y="{y}" width="{w}" height="{rowh}" fill="transparent"/>'
                   f'<rect class="{cls}" x="{x0:.1f}" y="{y + 7}" width="{max(x1 - x0, 1.5):.1f}" height="{rowh - 14}" rx="3"/>'
                   f'<text x="{left - 8}" y="{y + rowh / 2 + 4}" text-anchor="end">{esc_(LABELS[k])}</text>'
                   f'<text x="{max(x1, sx(0)) + 6:.1f}" y="{y + rowh / 2 + 4}">{sgn(v, 2)} %</text></g>')
        rows.append([LABELS[k], f"{v:.2f}", f"{res['index'][k]['cagr_pct']:.2f}", f"{res['index'][k]['value_last']:.1f}"])
    out.append(f'<line class="axis" x1="{sx(0):.1f}" x2="{sx(0):.1f}" y1="{top - 6}" y2="{h - 46}"/>'
               f'<text x="{(left + w - right) / 2:.1f}" y="{h - 8}" text-anchor="middle">Growth above consumer prices '
               f'(% a year, 2000 to 2025)</text></svg>')
    return "".join(out), [["Index", "Growth above CPI (% a year)", "Nominal growth (% a year)", "2025 value (2000 = 100)"]] + rows


CYCLE_BANDS = [(2004, 2008), (2014, 2016), (2021, 2023)]


def fig_small_multiples(res) -> tuple[str, list[list]]:
    mon = res["series"]["monthly"]
    keys = COMPONENTS + ["blend_m"]
    blend_m = {}
    for ym in mon["cpi"]:
        if all(ym in mon[k] for k in f.BLEND_WEIGHTS):
            blend_m[ym] = sum(w * mon[k][ym] for k, w in f.BLEND_WEIGHTS.items())
    mon = dict(mon, blend_m=blend_m)
    w, h, l, r, t, b = 300, 170, 34, 8, 24, 20
    lo, hi = 50, 500
    x0, x1 = 2000, 2027
    sx = lambda yr: l + (yr - x0) / (x1 - x0) * (w - l - r)  # noqa: E731
    sy = lambda v: t + (hi - min(max(v, lo), hi)) / (hi - lo) * (h - t - b)  # noqa: E731
    annual = res["series"]["annual"]
    panels = []
    for k in keys:
        name = LABELS["blend"] if k == "blend_m" else LABELS[k]
        p = [svg_open(w, h, f"{name} and CPI, monthly, 2000 = 100", f"f1{k}")]
        for a, z in CYCLE_BANDS:
            p.append(f'<rect class="band" x="{sx(a):.1f}" y="{t}" width="{sx(z + 1) - sx(a):.1f}" height="{h - t - b}"/>')
        for v in (100, 200, 300, 400, 500):
            p.append(f'<line class="grid" x1="{l}" x2="{w - r}" y1="{sy(v):.1f}" y2="{sy(v):.1f}"/>'
                     f'<text class="muted" x="{l - 4}" y="{sy(v) + 4:.1f}" text-anchor="end">{v}</text>')
        for yr in (2000, 2010, 2020):
            p.append(f'<text class="muted" x="{sx(yr):.1f}" y="{h - 5}" text-anchor="middle">{yr}</text>')
        for series, cls, sw in ((mon["cpi"], "ref", 1.5), (mon[k], "s1", 2)):
            pts = " ".join(f"{sx(int(ym[:4]) + (int(ym[5:7]) - 0.5) / 12):.1f},{sy(v):.1f}" for ym, v in sorted(series.items()))
            p.append(f'<polyline class="{cls}" fill="none" stroke-width="{sw}" stroke-linejoin="round" points="{pts}"/>')
        ak = "blend" if k == "blend_m" else k
        for yr in range(2000, 2026):
            tip = f"{name}, {yr}: {annual[ak][str(yr)]:.1f}; CPI {annual['cpi'][str(yr)]:.1f} (annual means, 2000 = 100)"
            p.append(f'<rect class="hit" x="{sx(yr):.1f}" y="{t}" width="{sx(yr + 1) - sx(yr):.1f}" height="{h - t - b}" '
                     f'fill="transparent" data-tip="{esc_(tip)}"><title>{esc_(tip)}</title></rect>')
        p.append(f'<text x="{l}" y="14" font-weight="600">{esc_(name)}</text></svg>')
        panels.append("".join(p))
    rows = [["Year", "CPI"] + [LABELS[k] for k in COMPONENTS] + [LABELS["blend"]]]
    for yr in range(2000, 2026):
        rows.append([str(yr), f"{annual['cpi'][str(yr)]:.1f}"] + [f"{annual[k][str(yr)]:.1f}" for k in COMPONENTS]
                    + [f"{annual['blend'][str(yr)]:.1f}"])
    return "".join(f'<div class="sm">{pnl}</div>' for pnl in panels), rows


def fig_ucci(res) -> tuple[str, list[list]]:
    bq, tq = res["series"]["blend_q"], res["series"]["two_q"]
    w, h, l, r, t, b = 640, 320, 44, 16, 50, 28
    lo, hi = 50, 300
    x0, x1 = 2000, 2027
    qx = lambda q: int(q[:4]) + (int(q[5]) - 0.5) / 4  # noqa: E731
    sx = lambda yr: l + (yr - x0) / (x1 - x0) * (w - l - r)  # noqa: E731
    sy = lambda v: t + (hi - v) / (hi - lo) * (h - t - b)  # noqa: E731
    out = [svg_open(w, h, "Public capital blends and quoted Upstream Capital Costs Index values, 2000 = 100", "f3"),
           f'<text x="{l - 38}" y="{t - 8}">Index (2000 = 100)</text>']
    for v in range(50, 301, 50):
        out.append(f'<line class="grid" x1="{l}" x2="{w - r}" y1="{sy(v):.1f}" y2="{sy(v):.1f}"/>'
                   f'<text class="muted" x="{l - 6}" y="{sy(v) + 4:.1f}" text-anchor="end">{v}</text>')
    for yr in range(2000, 2027, 5):
        out.append(f'<text class="muted" x="{sx(yr):.1f}" y="{h - 8}" text-anchor="middle">{yr}</text>')
    for series, cls in ((tq, "s1"), (bq, "s2")):
        pts = " ".join(f"{sx(qx(q)):.1f},{sy(v):.1f}" for q, v in sorted(series.items()))
        out.append(f'<polyline class="{cls}" fill="none" stroke-width="2" stroke-linejoin="round" points="{pts}"/>')
    rows = [["Quarter", "Quoted index value", "Capital blend", "Two-index blend", "Quoted over capital blend (%)",
             "Source", "Words quoted"]]
    for u in res["ucci"]["points"]:
        x, y = sx(qx(u["quarter"])), sy(u["value"])
        tip = (f"{u['quarter'][:4]} Q{u['quarter'][5]}: quoted index {u['value']:.1f}; capital blend {u['blend']:.1f}; "
               f"two-index blend {u['two']:.1f}. Source: {u['source']}")
        out.append(f'<g class="hit" tabindex="0" data-tip="{esc_(tip)}"><title>{esc_(tip)}</title>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="transparent"/>'
                   f'<path class="fref ring" stroke-width="2" d="M{x:.1f} {y - 6:.1f} L{x + 6:.1f} {y:.1f} L{x:.1f} {y + 6:.1f} '
                   f'L{x - 6:.1f} {y:.1f} Z"/></g>')
        rows.append([u["quarter"], f"{u['value']:.1f}", f"{u['blend']:.1f}", f"{u['two']:.1f}", f"{u['gap_pct']:.1f}",
                     f"{u['source']}, {u['url']}", u["quoted"]])
    lg = (f'<g class="lg"><line class="s2" x1="{l}" x2="{l + 22}" y1="12" y2="12" stroke-width="2"/>'
          f'<text x="{l + 28}" y="16">Capital blend (seven indexes)</text>'
          f'<line class="s1" x1="{l + 220}" x2="{l + 242}" y1="12" y2="12" stroke-width="2"/>'
          f'<text x="{l + 248}" y="16">Two-index blend</text>'
          f'<path class="fref" d="M{l + 380} 6 L{l + 386} 12 L{l + 380} 18 L{l + 374} 12 Z"/>'
          f'<text x="{l + 392}" y="16">Quoted sector index</text></g>')
    out.append(lg + "</svg>")
    return "".join(out), rows


def fig_escalation(res) -> tuple[str, list[list]]:
    e5, e8 = res["esc"]["blend_real_5"], res["esc"]["blend_real_8"]
    w, h, l, r, t, b = 640, 340, 44, 130, 50, 48
    lo, hi = -15, 35
    x0, x1 = 1996, 2022
    sx = lambda yr: l + (yr - x0) / (x1 - x0) * (w - l - r)  # noqa: E731
    sy = lambda v: t + (hi - v) / (hi - lo) * (h - t - b)  # noqa: E731
    out = [svg_open(w, h, "Escalation above CPI over the execution window, by sanction year", "f4")]
    for v in range(-15, 36, 5):
        out.append(f'<line class="{"axis" if v == 0 else "grid"}" x1="{l}" x2="{w - r}" y1="{sy(v):.1f}" y2="{sy(v):.1f}"/>'
                   f'<text class="muted" x="{l - 6}" y="{sy(v) + 4:.1f}" text-anchor="end">{sgn(v, 0).lstrip("+")}</text>')
    for yr in range(2000, 2022, 5):
        out.append(f'<text class="muted" x="{sx(yr):.1f}" y="{h - 28}" text-anchor="middle">{yr}</text>')
    out.append(f'<text x="{(l + w - r) / 2:.1f}" y="{h - 6}" text-anchor="middle">Sanction year</text>'
               f'<text x="{l - 38}" y="{t - 8}">Escalation above consumer prices over the window (%)</text>')
    for lab, val in (("8-year P90", e8["p90"]), ("8-year P50", e8["p50"])):
        out.append(f'<line class="ref" x1="{l}" x2="{w - r}" y1="{sy(val):.1f}" y2="{sy(val):.1f}" stroke-width="1"/>'
                   f'<text class="muted" x="{w - r + 6}" y="{sy(val) + 4:.1f}">{lab} {val:.1f} %</text>')
    for e, cls, shape in ((e5, "f1", "c"), (e8, "f2", "s")):
        n = 5 if e is e5 else 8
        for s, v in e["by_fid"].items():
            x, y = sx(int(s)), sy(v)
            tip = f"Sanction {s}, {n}-year window: {sgn(v)} % above CPI"
            mark = (f'<circle class="{cls} ring" stroke-width="2" cx="{x:.1f}" cy="{y:.1f}" r="5"/>' if shape == "c" else
                    f'<rect class="{cls} ring" stroke-width="2" x="{x - 5:.1f}" y="{y - 5:.1f}" width="10" height="10" rx="1"/>')
            out.append(f'<g class="hit" data-tip="{esc_(tip)}"><title>{esc_(tip)}</title>'
                       f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="transparent"/>{mark}</g>')
    out.append(f'<g class="lg"><circle class="f1" cx="{l + 8}" cy="12" r="5"/><text x="{l + 18}" y="16">5-year window</text>'
               f'<rect class="f2" x="{l + 133}" y="7" width="10" height="10" rx="1"/><text x="{l + 150}" y="16">'
               f'8-year window</text></g></svg>')
    rows = [["Sanction year", "5-year window, above CPI (%)", "8-year window, above CPI (%)",
             "5-year window, nominal (%)", "8-year window, nominal (%)"]]
    n5, n8 = res["esc"]["blend_nominal_5"]["by_fid"], res["esc"]["blend_nominal_8"]["by_fid"]
    for s in e5["by_fid"]:
        rows.append([s, f"{e5['by_fid'][s]:.1f}", f"{e8['by_fid'].get(s, float('nan')):.1f}".replace("nan", ""),
                     f"{n5[s]:.1f}", f"{n8.get(s, float('nan')):.1f}".replace("nan", "")])
    return "".join(out), rows


CYCLE_NAMES = {(2004, 2008): "Boom 2004 to 2008", (2014, 2016): "Bust 2014 to 2016", (2021, 2023): "Boom 2021 to 2023"}


def fig_grip(res) -> tuple[str, list[list]]:
    """Top chart: the capital blend (drawn as the Deckhand rope), consumer prices and Brent crude oil, monthly,
    2000 = 100, over the three cycle bands. The subject fills the frame: tight margins, large type."""
    mon = res["series"]["monthly"]
    blend_m = {ym: sum(w * mon[k][ym] for k, w in f.BLEND_WEIGHTS.items())
               for ym in mon["cpi"] if all(ym in mon[k] for k in f.BLEND_WEIGHTS)}
    w, h, l, r, t, b = 1040, 430, 56, 150, 58, 34
    lo, hi = 50, 500
    x0, x1 = 2000, 2027
    sx = lambda yr: l + (yr - x0) / (x1 - x0) * (w - l - r)  # noqa: E731
    sy = lambda v: t + (hi - min(max(v, lo), hi)) / (hi - lo) * (h - t - b)  # noqa: E731
    out = [svg_open(w, h, "Getting a grip on offshore project cost: capital blend, consumer prices and Brent crude "
                    "oil, monthly, 2000 = 100, with the three cost cycles", "f0"),
           f'<text x="{l}" y="24" style="font-size:20px;font-weight:700">Getting a grip on offshore project cost</text>'
           f'<text class="muted" x="{l}" y="46" style="font-size:14px">Monthly, each series over its 2000 mean, times 100</text>']
    for (a, z), name in CYCLE_NAMES.items():
        out.append(f'<rect class="band" x="{sx(a):.1f}" y="{t}" width="{sx(z + 1) - sx(a):.1f}" height="{h - t - b}"/>'
                   f'<text class="muted" x="{sx(a) + 4:.1f}" y="{t + 16}" style="font-size:13px;font-weight:600">{name}</text>')
    for v in (100, 200, 300, 400, 500):
        out.append(f'<line class="grid" x1="{l}" x2="{w - r}" y1="{sy(v):.1f}" y2="{sy(v):.1f}"/>'
                   f'<text class="muted" x="{l - 6}" y="{sy(v) + 5:.1f}" text-anchor="end" style="font-size:14px">{v}</text>')
    for yr in range(2000, 2027, 5):
        out.append(f'<text class="muted" x="{sx(yr):.1f}" y="{h - 10}" text-anchor="middle" style="font-size:14px">{yr}</text>')

    def path(series):
        return " ".join(f"{sx(int(ym[:4]) + (int(ym[5:7]) - 0.5) / 12):.1f},{sy(v):.1f}" for ym, v in sorted(series.items()))
    out.append(f'<polyline class="s3" fill="none" stroke-width="1.6" stroke-dasharray="5 4" points="{path(mon["brent"])}"/>'
               f'<polyline class="ref" fill="none" stroke-width="2.4" points="{path(mon["cpi"])}"/>'
               f'<polyline class="rim" fill="none" stroke-width="9" stroke-linejoin="round" stroke-linecap="round" '
               f'points="{path(blend_m)}"/><polyline class="s2" fill="none" stroke-width="5.5" stroke-linejoin="round" '
               f'stroke-linecap="round" points="{path(blend_m)}"/>')
    last = max(blend_m)
    for key, val, name, cls in (("blend", blend_m[last], "Capital blend", "f2"), ("cpi", mon["cpi"][last], "Consumer prices", "fref"),
                                ("brent", mon["brent"][last], "Brent crude oil", "f3")):
        out.append(f'<text class="{cls}" x="{sx(2026.9) + 6:.1f}" y="{sy(val) + 5:.1f}" style="font-size:15px;font-weight:700">{name}</text>')
    annual = res["series"]["annual"]
    rows = [["Year", "Capital blend", "Consumer prices", "Brent crude oil"]]
    for yr in range(2000, 2026):
        y_ = str(yr)
        tip = (f"{yr} (annual means, 2000 = 100): capital blend {annual['blend'][y_]:.1f}; consumer prices "
               f"{annual['cpi'][y_]:.1f}; Brent crude oil {annual['brent'][y_]:.1f}")
        out.append(f'<rect class="hit" x="{sx(yr):.1f}" y="{t}" width="{sx(yr + 1) - sx(yr):.1f}" height="{h - t - b}" '
                   f'fill="transparent" data-tip="{esc_(tip)}"><title>{esc_(tip)}</title></rect>')
        rows.append([y_, f"{annual['blend'][y_]:.1f}", f"{annual['cpi'][y_]:.1f}", f"{annual['brent'][y_]:.1f}"])
    out.append("</svg>")
    return "".join(out), rows


def short(name: str) -> str:
    """Project name without its bracketed note: "Martin Linge (ex-Hild)" -> "Martin Linge"."""
    return name.split(" (")[0]


def fig_projects(res) -> tuple[str, list[list]]:
    """Figure 5: final over sanction, per project where the statements' words allow it, beside the capital blend over
    the project's own years. A final that is an upper bound is a triangle pointing left (the change is at most that)."""
    out_ = [o for o in res["projects"]["outturn"] if o["computable"]]
    w, rowh, left, right, top = 700, 28, 290, 16, 44
    h = top + rowh * len(out_) + 52
    lo, hi = -40.0, 110.0
    sx = lambda v: left + (v - lo) / (hi - lo) * (w - left - right)  # noqa: E731
    out = [svg_open(w, h, "Final cost over the sanction estimate, by project, beside the capital blend over the same "
                    "years", "f5")]
    for v in range(-40, 111, 20):
        out.append(f'<line class="{"axis" if v == 0 else "grid"}" x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{top - 6}" '
                   f'y2="{h - 46}"/><text class="muted" x="{sx(v):.1f}" y="{h - 30}" text-anchor="middle">'
                   f'{sgn(v, 0).lstrip("+")}</text>')
    rows = [["Project", "Currency", "Sanction year", "Final year", "Final over sanction (%)",
             "Capital blend over the same years (%)", "Final figure"]]
    for i, o in enumerate(out_):
        y = top + i * rowh + rowh / 2
        assumed = not (o["sanction_primary"] and o["final_primary"])
        kind = "forecast at completion" if o["final_kind"] == "final_forecast" else "outturn"
        lab = f"{short(o['project'])} ({o['currency']}), {o['sanction_year']} to {o['final_year']}"
        tip = (f"{o['project']}: sanction estimate {o['sanction_mm']:,.0f} million {o['currency']} ({o['sanction_date']}); "
               f"final {o['final_mm']:,.0f} million ({o['final_date']}, {kind}): {o['bound'] + ' ' if o['bound'] else ''}"
               f"{sgn(o['change_pct'])} %. Capital blend over the same years: {sgn(o['market_pct'])} %."
               + (" A figure from a secondary source, or derived: ASSUMED - to be confirmed." if assumed else ""))
        xm, xp = sx(o["market_pct"]), sx(o["change_pct"])
        cls = "ring2" if assumed else "f1 ring"
        if o["bound"] == "at most":
            mark = (f'<path class="{cls}" stroke-width="2" d="M{xp - 8:.1f} {y:.1f} L{xp + 5:.1f} {y - 7:.1f} '
                    f'L{xp + 5:.1f} {y + 7:.1f} Z"/>')
        elif o["bound"] == "at least":
            mark = (f'<path class="{cls}" stroke-width="2" d="M{xp + 8:.1f} {y:.1f} L{xp - 5:.1f} {y - 7:.1f} '
                    f'L{xp - 5:.1f} {y + 7:.1f} Z"/>')
        else:
            mark = (f'<path class="{cls}" stroke-width="2" d="M{xp:.1f} {y - 7:.1f} L{xp + 7:.1f} {y:.1f} L{xp:.1f} '
                    f'{y + 7:.1f} L{xp - 7:.1f} {y:.1f} Z"/>')
        out.append(f'<g class="hit" tabindex="0" data-tip="{esc_(tip)}"><title>{esc_(tip)}</title>'
                   f'<rect x="0" y="{y - rowh / 2:.1f}" width="{w}" height="{rowh}" fill="transparent"/>'
                   f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end">{esc_(lab)}{" *" if assumed else ""}</text>'
                   f'<circle class="f2 ring" stroke-width="2" cx="{xm:.1f}" cy="{y:.1f}" r="5.5"/>{mark}</g>')
        rows.append([o["project"], o["currency"], str(o["sanction_year"]), str(o["final_year"]),
                     (o["bound"] + " " if o["bound"] else "") + f"{o['change_pct']:.1f}".replace("-", "\u2212"),
                     f"{o['market_pct']:.1f}",
                     kind + ("; ASSUMED - to be confirmed" if assumed else "")])
    out.append(f'<text x="{(left + w - right) / 2:.1f}" y="{h - 8}" text-anchor="middle">Change from the sanction '
               f'estimate (%)</text>'
               f'<g class="lg"><path class="f1" d="M{left} 12 L{left + 7} 19 L{left} 26 L{left - 7} 19 Z"/>'
               f'<text x="{left + 12}" y="23">Final over sanction</text>'
               f'<path class="f1" d="M{left + 150} 19 L{left + 163} 12 L{left + 163} 26 Z"/>'
               f'<text x="{left + 170}" y="23">At most</text>'
               f'<circle class="f2" cx="{left + 250}" cy="19" r="5.5"/><text x="{left + 262}" y="23">Capital blend, same '
               f'years</text></g></svg>')
    return "".join(out), rows


def table_html(rows: list[list], cls="hs-table") -> str:
    head = "".join(f"<th>{esc_(c)}</th>" for c in rows[0])
    def cell(c):
        c = str(c)
        return "\u2212" + c[1:] if re.match(r"^-\d", c) else c
    body = "".join("<tr>" + "".join(f"<td>{esc_(cell(c))}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f'<div class="hs-table-wrap"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def write_static(name: str, svg: str, rows: list[list]) -> None:
    fig = OUT / "figures"
    fig.mkdir(parents=True, exist_ok=True)
    if not svg.startswith("<svg"):
        parts = re.findall(r"<svg.*?</svg>", svg, flags=re.S)
        n = len(parts)
        cols = 4
        w, h = 300, 170
        inner = "".join(f'<g transform="translate({(i % cols) * w} {(i // cols) * h})">'
                        + p.replace('<svg viewBox="0 0 300 170"', f'<svg width="{w}" height="{h}" viewBox="0 0 300 170"')
                        + "</g>" for i, p in enumerate(parts))
        svg = f'<svg viewBox="0 0 {cols * w} {((n + cols - 1) // cols) * h}" role="img">{inner}</svg>'
    svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    svg = svg.replace(">", f"><style>{STYLE_LIGHT}</style>", 1)
    (fig / f"{name}.svg").write_text(svg, encoding="utf-8", newline="\n")
    with (fig / f"{name}.csv").open("w", encoding="utf-8", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)


# ------------------------------------------------------------------ page
CSS = """
:root{color-scheme:light;--bg:#ffffff;--surface:#ffffff;--text:#26323a;--muted:#5a6b76;--heading:#0b3d5c;--line:#d0d7de;
--tint:#eef4f8;--accent:#1fa596;--kicker:#0d7680;--link:#0b5f8a;--s1:#245c94;--s2:#1fa596;--ref:#6b7780;--grid:#e3e8ec;
--axis:#8a969e;--band:#eef4f8;--ring:#ffffff;--s3:#e69f00;--rim:#0b3d5c}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#061a28;--surface:#0b2638;
--text:#e4edf2;--muted:#9db2c0;--heading:#ffffff;--line:#21475f;--tint:#10324a;--accent:#2aa898;--kicker:#3FC4B8;
--link:#9fd3ff;--s1:#3a78b8;--s2:#2aa898;--ref:#9db2c0;--grid:#1b3d53;--axis:#4f7f99;--band:#10324a;--ring:#0b2638;
--s3:#e69f00;--rim:#9fd3ff}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#061a28;--surface:#0b2638;--text:#e4edf2;--muted:#9db2c0;--heading:#ffffff;
--line:#21475f;--tint:#10324a;--accent:#2aa898;--kicker:#3FC4B8;--link:#9fd3ff;--s1:#3a78b8;--s2:#2aa898;--ref:#9db2c0;
--grid:#1b3d53;--axis:#4f7f99;--band:#10324a;--ring:#0b2638;--s3:#e69f00;--rim:#9fd3ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:17px/1.55 "Segoe UI",Helvetica,Arial,sans-serif}
.art{max-width:920px;margin:0 auto;padding:24px 16px 64px}
h1,h2,h3{color:var(--heading);line-height:1.25}h1{font-size:1.9em;margin:.2em 0 .3em}h2{font-size:1.3em;margin:1.6em 0 .4em}
h3{font-size:1.05em}a{color:var(--link)}.hs-small{font-size:.86em}.hs-kicker{color:var(--kicker);font-weight:600;
text-transform:uppercase;letter-spacing:.05em;font-size:.82em;margin:.6em 0 .2em}
.masthead-line{color:var(--muted)}
.opening img,.ig-scene img{display:block;width:100%;height:auto;border-radius:8px}.opening{margin:0 0 12px}.ig-scene{margin:0 0 8px}
.ig{margin:20px 0 28px}.ig-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}
.ig-p{border:1px solid var(--line);border-top:3px solid var(--heading);border-radius:6px;padding:10px;background:var(--surface)}
.ig-p p{margin:.2em 0;font-size:15px;line-height:1.4}.ig-k{font:600 12px/1.3 "Segoe UI",Helvetica,Arial,sans-serif;
text-transform:uppercase;letter-spacing:.04em;color:var(--kicker)}.ig-act{border-top-color:var(--accent);background:var(--tint)}
@media (max-width:760px){.ig-grid{grid-template-columns:1fr}}
.intro h2{font-size:1.1em;margin:1em 0 .3em}
.hyp{border-left:4px solid var(--heading);background:var(--tint);padding:8px 12px;margin:12px 0}.hyp p{margin:0}
.cap{margin:.4em 0 .2em}.fn{margin:0 0 1em;padding-left:1.2em}
.refs li{margin:.25em 0;overflow-wrap:anywhere}
figure{margin:12px 0}.viz{width:100%;height:auto;max-width:680px;display:block}
.viz text{font:12px "Segoe UI",Helvetica,Arial,sans-serif;fill:var(--text)}.viz .muted{fill:var(--muted)}
.s1{stroke:var(--s1)}.f1{fill:var(--s1)}.s2{stroke:var(--s2)}.f2{fill:var(--s2)}.ref{stroke:var(--ref)}.fref{fill:var(--ref)}
.grid{stroke:var(--grid)}.axis{stroke:var(--axis)}.band{fill:var(--band)}.ring{stroke:var(--ring)}
.s3{stroke:var(--s3)}.f3{fill:var(--s3)}.rim{stroke:var(--rim)}.ring2{fill:var(--surface);stroke:var(--s1)}
.ig-scene{margin:0 0 8px}.ig-scene .viz{max-width:none}.ig-cap{margin:2px 0 10px}
.smg .viz text{font-size:15px}.smg .viz text[font-weight]{font-size:16px}.smg{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}@media (max-width:760px){.smg{grid-template-columns:1fr 1fr}}
.lgd{display:flex;flex-wrap:wrap;gap:14px;font-size:.86em;color:var(--muted);margin:4px 0}
.lgd i{display:inline-block;width:18px;height:0;border-top:2px solid;vertical-align:middle;margin-right:5px}
.lgd b{display:inline-block;width:14px;height:10px;background:var(--band);border:1px solid var(--line);vertical-align:middle;margin-right:5px}
.hs-table-wrap{overflow-x:auto}.hs-table{border-collapse:collapse;font-size:.86em;margin:6px 0}
.hs-table th,.hs-table td{border:1px solid var(--line);padding:4px 7px;text-align:left;vertical-align:top}
.hs-table th{background:var(--tint)}
details{margin:6px 0}summary{cursor:pointer;color:var(--link)}
.signoff{margin-top:20px;border-top:1px solid var(--line);padding-top:8px}
.prompt{border-left:4px solid var(--accent);margin:8px 0;padding:6px 12px;background:var(--tint)}
#tip{position:fixed;pointer-events:none;background:var(--surface);color:var(--text);border:1px solid var(--line);
border-radius:6px;padding:6px 9px;font-size:13px;max-width:320px;box-shadow:0 2px 8px rgba(0,0,0,.18);display:none;z-index:9}
.hit:focus{outline:2px solid var(--accent)}
"""

TIP_JS = """
(function(){var t=document.createElement('div');t.id='tip';document.body.appendChild(t);
function show(e,el){t.textContent=el.getAttribute('data-tip');t.style.display='block';var r=el.getBoundingClientRect();
var x=(e&&e.clientX)||r.left+r.width/2,y=(e&&e.clientY)||r.top;t.style.left=Math.min(x+12,window.innerWidth-330)+'px';
t.style.top=(y+14)+'px';}
document.querySelectorAll('[data-tip]').forEach(function(el){var ti=el.querySelector('title');if(ti){el.setAttribute('aria-label',ti.textContent);}
el.addEventListener('mousemove',function(e){show(e,el)});el.addEventListener('focus',function(){show(null,el)});
el.addEventListener('mouseleave',function(){t.style.display='none'});el.addEventListener('blur',function(){t.style.display='none'});});})();
"""


def words(fragment: str) -> list[str]:
    t = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    t = re.sub(r"<h2\b.*?</h2>", " ", t, flags=re.S | re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"\[\d+\]", " ", t)
    return t.split()


def between(src: str, tag: str) -> str:
    m = re.search(rf"<!--{tag}-START-->(.*?)<!--{tag}-END-->", src, flags=re.S)
    if not m:
        raise SystemExit(f"marker {tag} missing")
    return m.group(1)


def numbers(text: str) -> set[str]:
    return set(re.findall(r"\d[\d,]*(?:\.\d+)?", text))


def day(iso: str) -> str:
    return dt.date.fromisoformat(iso).strftime("%d %b %Y").lstrip("0")


def refs(d: dict, res: dict) -> list[dict]:
    out = []
    for r in d["sources"]:
        if r["key"] == "ucci_quoted":
            continue
        out.append({"cite": f"{r['publisher']}, {r['title']} ({r['series_id']}), retrieved through FRED, Federal "
                            f"Reserve Bank of St. Louis, on {day(r['retrieved_utc'][:10])}", "url": r["url"]})
    seen = {}
    for u in sorted(res["ucci"]["points"] + res["ucci"]["set_aside"], key=lambda p: p["quarter"]):
        if u["url"] not in seen:
            seen[u["url"]] = u
            out.append({"cite": f"{u['source']}, quoting the S&P Global (formerly IHS) Upstream Capital Costs Index; "
                                f"read {day(u['accessed'])}", "url": u["url"]})
    out.append({"cite": "worldenergydata, escalation method note docs/modules/cost/ESCALATION.md",
                "url": f"{REPO_URL}/blob/main/docs/modules/cost/ESCALATION.md"})
    pj = d["projects"]
    reads = sorted({r["ACCESSED_DATE"] for t in ("sanctioned", "awards", "trails") for r in pj[t]})
    out.append({"cite": "worldenergydata, curated cost tables: sanctioned projects, contract awards and dated cost "
                        "statements, each row with its source, the words quoted and the date read (rows read "
                        f"{day(reads[0])} to {day(reads[-1])})",
                "url": f"{REPO_URL}/tree/main/data/modules/cost/curated"})
    for i, r in enumerate(out, 1):
        r["n"] = i
    return out


def fill(body: str, res: dict, ctx: dict) -> str:
    def rep(m):
        key = m.group(1)
        if key in ctx:
            return ctx[key]
        cur = res
        for part in key.split("."):
            cur = cur[part]
        return f"{cur}"
    return re.sub(r"\{\{([A-Za-z0-9_.\-]+)\}\}", rep, body)


PICTURE_REV = "r2"


def picture(kind: str) -> str:
    p = HERE / "pictures" / f"megaproject-inflation-{PICTURE_REV}-{kind}.svg"
    if not p.exists():
        return ""
    svg = p.read_text(encoding="utf-8")
    alt = html.unescape(re.search(r'aria-label="([^"]*)"', svg).group(1))
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    if kind == "opening":
        return (f'<figure class="opening"><img src="{uri}" alt="{esc_(alt)}" width="1200"><figcaption class="hs-small">'
                f'Getting a grip on the cost: the Deckhand holds the rope that traces the capital blend from 2000 to 2025.'
                f'</figcaption></figure>')
    return f'<p class="ig-scene"><img src="{uri}" alt="{esc_(alt)}" width="1040"></p>'


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def month(ym: str) -> str:
    return f"{MONTHS[int(ym[5:7]) - 1]} {ym[:4]}"


def text_values(res: dict, rf: list[dict]) -> dict:
    """Every number the prose quotes, formatted once from the results (placeholders T_*)."""
    ix, c, E, U, t = res["index"], res["corr"], res["esc"], res["ucci"], res["turns"]
    cyc = lambda k, lab, kind: ix[k]["cycles"][lab][kind]  # noqa: E731
    flat_max = max(abs(ix[k]["real_cagr_pct"]) for k in ("engineering", "shipbuilding", "support"))
    sens8 = [E[k]["p90"] for k in ("blend_real_8", "two_real_8", "equal_real_8", "flat_real_8")]
    peak_ref = next(r["n"] for r in rf if r["url"] == U["peak"]["url"])
    if U["boom_two_min"] < 0 < U["boom_two_max"]:
        two_boom = f"from {abs(U['boom_two_min']):.1f} % below to {U['boom_two_max']:.1f} % above it"
    elif U["boom_two_min"] >= 0:
        two_boom = f"{U['boom_two_min']:.1f} % to {U['boom_two_max']:.1f} % above it"
    else:
        two_boom = f"{abs(U['boom_two_max']):.1f} % to {abs(U['boom_two_min']):.1f} % below it"
    v = {
        "cpi_rise": f"{ix['cpi']['rise_pct']:.1f}", "cpi_cagr": f"{ix['cpi']['cagr_pct']:.2f}",
        "drill_rise": f"{ix['drilling']['rise_pct']:.1f}", "pipe_rise": f"{ix['steel_pipe']['rise_pct']:.1f}",
        "drill_real": f"{ix['drilling']['real_cagr_pct']:.2f}", "pipe_real": f"{ix['steel_pipe']['real_cagr_pct']:.2f}",
        "flat_max": f"{flat_max:.2f}", "blend_cagr": f"{ix['blend']['cagr_pct']:.2f}",
        "blend_real": f"{ix['blend']['real_cagr_pct']:.2f}",
        "boom1": f"{cyc('blend', '2004-2008 boom', 'nominal_pct'):.1f}",
        "boom1_real": f"{cyc('blend', '2004-2008 boom', 'real_pct'):.1f}",
        "drill_boom1": f"{cyc('drilling', '2004-2008 boom', 'nominal_pct'):.1f}",
        "bust": f"{abs(cyc('blend', '2014-2016 bust', 'nominal_pct')):.1f}",
        "drill_bust": f"{abs(t['drilling_bust']['change_pct']):.1f}", "drill_bust_from": month(t["drilling_bust"]["from"]),
        "drill_bust_to": month(t["drilling_bust"]["to"]),
        "boom3": f"{cyc('blend', '2021-2023 boom', 'nominal_pct'):.1f}",
        "boom3_real": f"{cyc('blend', '2021-2023 boom', 'real_pct'):.1f}",
        "steel_boom": f"{t['steel_boom']['change_pct']:.1f}", "steel_boom_from": month(t["steel_boom"]["from"]),
        "steel_boom_to": month(t["steel_boom"]["to"]),
        "ytd_blend": f"{res['ytd']['blend_pct']:.1f}", "ytd_steel": f"{res['ytd']['steel_mill_pct']:.1f}",
        "ytd_brent": f"{res['ytd']['brent_pct']:.1f}",
        "r_drill": f"{c['drilling_lag1']:.2f}", "r_steel": f"{c['steel_mill']:.2f}", "r_eng": f"{c['engineering']:.2f}", "r_ship": f"{c['shipbuilding']:.2f}",
        "r_eng_lag": f"{c['engineering_lag1']:.2f}", "r_ship_lag": f"{c['shipbuilding_lag1']:.2f}",
        "r_drill_n": str(c["drilling_years"]), "r_drill_first": str(c["drilling_first"]),
        "r_drill_last": str(c["drilling_last"]), "r_oth_n": str(c["steel_mill_years"]),
        "r_oth_first": str(c["others_first"]), "r_oth_last": str(c["others_last"]),
        "under_min": f"{abs(U['boom_under_max']):.1f}", "under_max": f"{abs(U['boom_under_min']):.1f}",
        "gap_2006q3": sgn(U["gap_2006q3_pct"]), "r8_n": str(E["blend_real_8"]["n_windows"]),
        "sens_lo_chk": f"{min(sens8[1:]):.1f}", "sens_hi_chk": f"{max(sens8[1:]):.1f}",
        "peak": f"{U['peak']['value']:.0f}", "peak_ref": str(peak_ref), "peak_blend": f"{U['peak']['blend']:.1f}",
        "boom_n": str(U["boom_n"]), "boom_y0": str(U["boom_first"]), "boom_y1": str(U["boom_last"]),
        "n_quoted": str(len(U["points"])), "calm_n": str(len(U["points"]) - U["boom_n"]),
        "gap_min": f"{U['boom_gap_min']:.1f}", "gap_max": f"{U['boom_gap_max']:.1f}",
        "calm_lo": f"{abs(U['calm_gap_max']):.1f}", "calm_hi": f"{abs(U['calm_gap_min']):.1f}",
        "two_boom": two_boom, "two_calm_lo": f"{abs(U['calm_two_max']):.1f}", "two_calm_hi": f"{abs(U['calm_two_min']):.1f}",
        "r5_first": str(E["blend_real_5"]["fid_first"]), "r5_last": str(E["blend_real_5"]["fid_last"]),
        "r5_p50": f"{E['blend_real_5']['p50']:.1f}", "r5_p90": f"{E['blend_real_5']['p90']:.1f}",
        "r8_first": str(E["blend_real_8"]["fid_first"]), "r8_last": str(E["blend_real_8"]["fid_last"]),
        "r8_p50": f"{E['blend_real_8']['p50']:.1f}", "r8_p90": f"{E['blend_real_8']['p90']:.1f}",
        "n8_p50": f"{E['blend_nominal_8']['p50']:.1f}", "n8_p90": f"{E['blend_nominal_8']['p90']:.1f}",
        "r8_max_fid": str(E["blend_real_8"]["max_fid"]), "r8_max": f"{E['blend_real_8']['max']:.1f}",
        "n8_max": f"{E['blend_nominal_8']['by_fid'][str(E['blend_real_8']['max_fid'])]:.1f}",
        "r8_min_fid": str(E["blend_real_8"]["min_fid"]), "r8_min": f"{E['blend_real_8']['min']:.1f}".replace("-", "−"),
        "c5": f"{E['blend_real_5']['contingency_pts']:.1f}", "c8": f"{E['blend_real_8']['contingency_pts']:.1f}",
        "sens_lo": f"{min(sens8):.1f}", "sens_hi": f"{max(sens8):.1f}",
    }
    pj = res["projects"]
    k, sm = pj["counts"], pj["summary"]
    v.update({
        "aw_n": str(k["awards"]), "aw_valued": str(k["valued"]), "aw_proj": str(k["projects"]),
        "aw_primary": str(k["valued_primary"]), "aw_secondary": str(k["valued_secondary"]),
        "cov_n": str(sm["n_cov"]), "cov_med": f"{sm['share_median']:.1f}", "cov_min": f"{sm['share_min']:.0f}",
        "cov_max": f"{sm['share_max']:.1f}", "cov_max_p": short(sm["share_max_project"]),
        "out_n": str(sm["n_out"]), "out_assumed": str(sm["n_out_assumed"]), "out_fc": str(sm["n_out_forecast"]),
        "comp_n": str(sm["n_comp"]), "comp_assumed": str(sm["n_comp_assumed"]), "comp_fc": str(sm["n_comp_forecast"]),
        "final_secondary": str(sm["n_final_secondary"]),
        "out_min": f"{abs(sm['out_min']):.1f}", "out_min_p": short(sm["out_min_project"]), "out_min_y": str(sm["out_min_year"]),
        "out_max": f"{sm['out_max']:.1f}", "out_max_p": short(sm["out_max_project"]), "out_max_y": str(sm["out_max_year"]),
        "boom_pn": str(pj["boom"]["n"]), "boom_above": str(pj["boom"]["above"]), "bust_pn": str(pj["bust"]["n"]),
        "mkt_min": sgn(pj["market_min"]), "mkt_max": sgn(pj["market_max"]),
        "mkt_bb_min": sgn(pj["market_bb_min"]), "mkt_bb_max": sgn(pj["market_bb_max"]),
        "proj_read": f"{day(pj['read'][0])} to {day(pj['read'][-1])}",
        "confirm_by": pj["confirm_by"]})
    if pj["bust"]["below"] != pj["bust"]["n"]:
        raise SystemExit("text says every 2015 sanction finished below its estimate; the data no longer does")
    return {"T_" + k: x for k, x in v.items()}


def check(body_src: str, filled: str, page: str, refs_: list[dict], leak: list[str]) -> tuple[list[str], dict]:
    errs, facts = [], {}
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", filled)}
    cited |= {int(n) for n in re.findall(r"\breference (\d+)\b", filled)}  # a reference named in a note
    for a, b in re.findall(r"\[(\d+)\]–\[(\d+)\]", filled):
        cited |= set(range(int(a), int(b) + 1))
    ns = {r["n"] for r in refs_}
    if cited - ns:
        errs.append(f"cited but not a reference: {sorted(cited - ns)}")
    if ns - cited:
        errs.append(f"reference never cited: {sorted(ns - cited)}")
    why_src = between(filled, "INTRO-WHY")
    prompt_line = re.search(r'<li class="prompt-line">(.*?)</li>', why_src, flags=re.S)
    why_wo = why_src.replace(prompt_line.group(0), "") if prompt_line else why_src
    what, why, inside = len(words(between(filled, "INTRO-WHAT"))), len(words(why_wo)), len(words(between(filled, "INTRO-INSIDE")))
    pl = len(words(prompt_line.group(1))) if prompt_line else 0
    facts.update(intro_what=what, intro_why=why, intro_inside=inside, intro_total=what + why + inside, prompt_line=pl)
    if what > 70 or why > 70 or inside > 50 or pl > 25 or not 110 <= what + why + inside <= 190:
        errs.append(f"introduction limits: {what}/{why}/{inside}, prompt line {pl}")
    stray = {n for n in numbers(" ".join(words(between(filled, "INTRO-WHAT") + why_wo)))
             if not re.fullmatch(r"(19|20)\d\d", n)}       # years are not result numbers
    if stray:
        errs.append(f"numbers in the first two parts of the introduction: {sorted(stray)}")
    intro = " ".join(words(between(filled, "INTRO-WHAT") + why_src + between(filled, "INTRO-INSIDE")))
    if re.search(r"asked|asks", intro, flags=re.I):
        errs.append("the introduction says who asked; open on the subject and the facts")
    body = between(filled, "BODY")
    body_nofig = re.sub(r"<!--FIG-START-->.*?<!--FIG-END-->", " ", body, flags=re.S)
    facts["body_words"] = len(words(body_nofig))
    if not 500 <= facts["body_words"] <= 800:
        errs.append(f"body words {facts['body_words']} outside 500 to 800")
    facts["hypotheses"] = body.count("Our hypothesis:")
    if facts["hypotheses"] > 2:
        errs.append("more than 2 hypotheses in a public data piece")
    ig = re.sub(r"<figcaption.*?</figcaption>", " ", between(filled, "INFOGRAPHIC"), flags=re.S)
    ig = re.sub(r"<!--SCENE-START-->.*?<!--SCENE-END-->", " ", ig, flags=re.S)
    facts["infographic_words"] = len(words(ig))
    ig_nums = numbers(" ".join(words(ig)))
    facts["infographic_numbers"] = len(ig_nums)
    if facts["infographic_words"] > 70 or len(ig_nums) > 8:
        errs.append(f"infographic limits: {facts['infographic_words']} words, {len(ig_nums)} numbers")
    missing = ig_nums - numbers(" ".join(words(body)))
    if missing:
        errs.append(f"infographic numbers not in the body: {sorted(missing)}")
    vis = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.S | re.I)
    vis += " " + " ".join(re.findall(r'(?:alt|data-tip|aria-label)="([^"]*)"', page))
    vis = re.sub(r"data:image/svg\+xml;base64,[A-Za-z0-9+/=]+", " ", vis)
    vis = re.sub(r'<ol class="refs.*?</ol>', " ", vis, flags=re.S)
    vis = html.unescape(re.sub(r"<[^>]+>", " ", vis))
    vis = re.sub(r"https?://\S+", " ", vis)
    hits = [p for p in leak if re.search(p, vis)]
    if hits:
        errs.append(f"leak check: {hits}")
    facts["leak_patterns"] = len(leak)
    return errs, facts


def build(pin: str, built: str, leak: list[str] | None = None) -> tuple[str, list[str], dict, dict]:
    d = load()
    res = compute(d)
    rf = refs(d, res)
    f2, t2 = fig_real_bars(res)
    f1, t1 = fig_small_multiples(res)
    f3, t3 = fig_ucci(res)
    f4, t4 = fig_escalation(res)
    f0, t0 = fig_grip(res)
    f5, t5 = fig_projects(res)
    for name, svg, rows in (("fig2-cycles", f1, t1), ("fig1-growth-above-cpi", f2, t2), ("fig3-sector-index-check", f3, t3),
                            ("fig4-escalation-by-sanction-year", f4, t4), ("fig0-cost-grip", f0, t0),
                            ("fig5-final-over-sanction", f5, t5)):
        write_static(name, svg, rows)
    used = {u["url"] for u in res["ucci"]["points"]}
    n_ucci = [r["n"] for r in rf if "Upstream Capital Costs" in r["cite"] and r["url"] in used]
    runs = []  # consecutive reference numbers as [a]–[b], a lone one as [a]
    for n in n_ucci:
        if runs and n == runs[-1][1] + 1:
            runs[-1][1] = n
        else:
            runs.append([n, n])
    ucci_refs = ", ".join(f"[{a}]–[{b}]" if b > a else f"[{a}]" for a, b in runs)
    aside = " ".join(
        f"{u['quarter'][:4]} Q{u['quarter'][5]} value ({u['value']:.0f}, reference "
        f"{next(r['n'] for r in rf if r['url'] == u['url'])}) set aside until its source is read again."
        for u in res["ucci"]["set_aside"])
    if aside:
        aside += (f" Figure 3, Table A5 and the text use the other {len(res['ucci']['points'])} quoted quarters.")
    E = res["esc"]
    weights = [["Index", "Weight", "What it stands for"]] + [
        [LABELS[k], f"{w:.2f}", txt] for k, w, txt in (
            ("machinery", f.BLEND_WEIGHTS["machinery"], "Wellheads, trees, pumps, compressors and process equipment"),
            ("drilling", f.BLEND_WEIGHTS["drilling"], "Development drilling"),
            ("shipbuilding", f.BLEND_WEIGHTS["shipbuilding"], "Hull and module fabrication in a yard"),
            ("engineering", f.BLEND_WEIGHTS["engineering"], "Engineering, design and project management"),
            ("steel_mill", f.BLEND_WEIGHTS["steel_mill"], "Plate and sections for structures"),
            ("support", f.BLEND_WEIGHTS["support"], "Installation, well services and marine support"),
            ("steel_pipe", f.BLEND_WEIGHTS["steel_pipe"], "Line pipe, casing and risers"))]
    cyc = [["Index"] + [f"{lab}, nominal (%)" for lab, _, _ in f.CYCLES] + [f"{lab}, above CPI (%)" for lab, _, _ in f.CYCLES]]
    for k in COMPONENTS + ["blend", "cpi", "brent"]:
        c = res["index"][k]["cycles"]
        cyc.append([LABELS[k]] + [sgn(c[lab]["nominal_pct"]) for lab, _, _ in f.CYCLES]
                   + [("" if k == "cpi" else sgn(c[lab]["real_pct"])) for lab, _, _ in f.CYCLES])
    sens = [["Case", "5-year P50 (%)", "5-year P90 (%)", "8-year P50 (%)", "8-year P90 (%)"]]
    for lab, key in (("Capital blend, bell-shaped spend (base case)", "blend_real"),
                     ("Two-index blend of the repository method", "two_real"),
                     ("Seven indexes, equal weights", "equal_real"), ("Capital blend, even spend", "flat_real"),
                     ("Capital blend, nominal (CPI included)", "blend_nominal")):
        sens.append([lab, f"{E[key + '_5']['p50']:.1f}", f"{E[key + '_5']['p90']:.1f}", f"{E[key + '_8']['p50']:.1f}",
                     f"{E[key + '_8']['p90']:.1f}"])
    src_rows = [["Series", "Publisher", "First and last month", "Retrieved (UTC)", "SHA-256 of the saved file"]] + [
        [r["series_id"], r["publisher"], f"{r['first_observation']} to {r['last_observation']}", r["retrieved_utc"],
         r["sha256"]] for r in d["sources"]]
    pj = res["projects"]
    mark = "†"   # dagger: a value from a secondary source, ASSUMED - to be confirmed (note above the table)
    cover = [["Project", "Sanction year", "Estimate at sanction ($ million)", "Awards", "Awards with a value",
              "Awards set against the estimate", "Their value, low bound ($ million)", "Share of the estimate (%)"]]
    for c in pj["coverage"]:
        cover.append([c["project"], str(c["fid"]), f"{c['gross_mm']:,.0f}" + ("" if c["gross_primary"] else " " + mark),
                      str(c["n_awards"]), str(c["n_valued"]), str(c["n_comparable"]),
                      f"{c['awards_low_mm']:,.0f}" + ("" if c["awards_primary"] or not c["n_comparable"] else " " + mark),
                      f"{c['share_low_pct']:.1f}"])
    words_ = {"exact": "", "approximate": "about ", "lower_bound": "more than ", "upper_bound": "within ",
              "derived": "derived ", "unsupported": "", "not reviewed": ""}
    outt = [["Project", "Currency", "Sanction estimate (million)", "Final figure (million)", "Final over sanction (%)",
             "Capital blend, same years (%)"]]
    for o in pj["outturn"]:
        kind = "forecast at completion" if o["final_kind"] == "final_forecast" else "outturn"
        sb = f", {o['sanction_basis']}" if o["sanction_basis"] else ""
        fb = f", {o['final_basis']}" if o["final_basis"] else ""
        if o["computable"]:
            ch = (o["bound"] + " " if o["bound"] else "") + sgn(o["change_pct"])
            if o["conflict"]:
                ch += f" ({o['conflict']})"
        elif o["final_qualifier"] == "unsupported":
            ch = "not computable: the source does not state a final cost"
        else:
            ch = "not computable: both figures are lower bounds"
        outt.append([o["project"], o["currency"],
                     f"{words_[o['sanction_qualifier']]}{o['sanction_mm']:,.0f} ({o['sanction_date']}{sb})"
                     + ("" if o["sanction_primary"] else " " + mark),
                     f"{words_[o['final_qualifier']]}{o['final_mm']:,.0f} ({o['final_date']}, {kind}{fb})"
                     + ("" if o["final_primary"] else " " + mark),
                     ch, sgn(o["market_pct"])])
    lgd = ('<div class="lgd"><span><i class="s1" style="border-color:var(--s1)"></i>Index</span>'
           '<span><i style="border-color:var(--ref)"></i>Consumer prices (CPI)</span>'
           '<span><b></b>Cycle years 2004 to 2008, 2014 to 2016, 2021 to 2023</span></div>')
    ctx = {
        "OPENING": picture("opening"), "BUILT": esc_(built),
        "SCENE": (f'<!--SCENE-START--><div class="ig-scene">{f0}</div><p class="ig-cap hs-small">Getting a grip on the '
                  f'cost: the capital blend, consumer prices and Brent crude oil, 2000 to 2026, with the three cost '
                  f'cycles shaded. Hover on a year for its annual means.</p><!--SCENE-END-->'),
        "FIG5": f'<figure>{f5}', "FIG5T": f'<details><summary>Figure 5 as a table</summary>{table_html(t5)}</details></figure>',
        "TAB_COVER": table_html(cover), "TAB_OUTTURN": table_html(outt),
        "REF_PROJ": f"[{next(r['n'] for r in rf if r['url'].endswith('/data/modules/cost/curated'))}]",
        "REF_PROJ_N": str(next(r["n"] for r in rf if r["url"].endswith("/data/modules/cost/curated"))),
        "FIG_CYC": '<figure>' + lgd + f'<div class="smg">{f1}</div>',
        "FIG_CYC_T": f'<details><summary>Figure 2 as a table</summary>{table_html(t1)}</details></figure>',
        "FIG_GROW": f'<figure>{f2}', "FIG_GROW_T": f'<details><summary>Figure 1 as a table</summary>{table_html(t2)}</details></figure>',
        "FIG3": f'<figure>{f3}', "FIG3T": f'<details><summary>Figure 3 as a table</summary>'
                                          f'{table_html([r[:5] for r in t3])}</details></figure>',
        "FIG4": f'<figure>{f4}', "FIG4T": f'<details><summary>Figure 4 as a table</summary>{table_html(t4)}</details></figure>',
        "TAB_SOURCES": table_html(src_rows), "TAB_WEIGHTS": table_html(weights), "TAB_CYCLES": table_html(cyc),
        "TAB_SENS": table_html(sens), "TAB_UCCI": table_html([[r[0], r[1], r[2], r[4], r[6]] for r in t3]),
        "UCCI_REFS": ucci_refs, "SET_ASIDE": aside,
        "REF_ESC": f"[{next(r['n'] for r in rf if r['url'].endswith('/ESCALATION.md'))}]",
        "PIN": pin, "PIN7": pin[:7], "PROMPT_URL": f"{REPO_URL}/blob/{pin}/{PROMPT_PATH}",
        "REFS": "<ol class=\"refs hs-small\">" + "".join(
            f'<li id="ref-{r["n"]}" value="{r["n"]}">{esc_(r["cite"])}. <a href="{esc_(r["url"])}">{esc_(r["url"])}</a>.</li>'
            for r in rf) + "</ol>",
    }
    ctx.update(text_values(res, rf))
    body_src = (HERE / "article.body.html").read_text(encoding="utf-8")
    filled = fill(body_src, res, ctx)
    filled = re.sub(r"\[(\d+)\]", r'<a class="cite" href="#ref-\1">[\1]</a>', filled)
    plain_for_check = fill(body_src, res, {**ctx, **{k: "" for k in ("FIG_CYC", "FIG_GROW", "FIG3", "FIG4", "FIG_CYC_T",
                                                                      "FIG_GROW_T", "FIG3T", "FIG4T", "FIG5", "FIG5T",
                                                                      "OPENING", "SCENE")}})
    page = ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{esc_(TITLE)}</title>"
            "<meta name=\"description\" content=\"Public US price indexes for offshore drilling, equipment, steel, "
            "fabrication and engineering, rebased to 2000 against consumer prices: the long-run rise above general "
            "inflation, three boom and bust cycles, the escalation range for an assumed 5-year or 8-year spend, and "
            "the final cost of offshore projects against their sanction estimates from public records.\">"
            f"<style>{CSS}</style></head><body><main class=\"art\">{filled}</main><script>{TIP_JS}</script></body></html>\n")
    errs, facts = check(body_src, plain_for_check, page, rf, LEAK + (leak or []))
    return page, errs, facts, res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", required=True, help="commit that holds PROMPT.md, for the pinned prompt link")
    ap.add_argument("--built", help='build time as shown on the page, e.g. "17 Nov 2026, 22:00 UTC"')
    ap.add_argument("--out", default=str(OUT / "megaproject-cost-inflation-r2.html"))
    ap.add_argument("--leak-file", help="private file of extra regular expressions that must not appear, one a line")
    a = ap.parse_args(argv)
    built = a.built or dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y, %H:%M UTC").lstrip("0")
    extra = []
    if a.leak_file:
        extra = [ln.strip() for ln in Path(a.leak_file).read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.startswith("#")]
    page, errs, facts, res = build(a.pin, built, extra)
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    slim = {k: v for k, v in res.items() if k != "series"}
    (OUT / "results.json").write_text(json.dumps(slim, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    if errs:
        print("checks FAILED:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1
    Path(a.out).write_text(page, encoding="utf-8", newline="\n")
    print(f"wrote {Path(a.out).name}; checks ok; facts {json.dumps(facts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
