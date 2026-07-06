# ABOUTME: Build the deterministic well drilling-&-completion report HTML.
# ABOUTME: Reads the frozen V30 WAR-derived day counts and renders a static page.
"""Build the **well completion & drilling-days** report — a single self-contained
HTML page summarising, per Lower-Tertiary deepwater field, the drilling and
completion durations reconstructed from BSEE Well Activity Reports (WAR).

The numbers are read from one frozen, committed reference workbook
(``docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx``)
produced by the V30 SME drilling/completion-days methodology — so the published
page is deterministic and reproducible: same workbook in, byte-identical HTML out.

This generator may use openpyxl (a dev/build dependency); the published site
builder (``scripts/build_pages.py``) only ever *copies* the frozen HTML it emits,
so the Pages build stays stdlib-only.

Run:
    .venv/bin/python scripts/completion/build_completion_report.py

Output: reports/completion/index.html (self-contained, no external assets).
"""

from __future__ import annotations

import html
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import openpyxl

_REPO = Path(__file__).resolve().parents[2]
_SRC = (
    _REPO
    / "docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx"
)
_OUT = _REPO / "reports" / "completion" / "index.html"
_OUT_VERIFY = _REPO / "reports" / "completion" / "verification.html"

# ---------------------------------------------------------------------------
# "WO Article, end of 2025" benchmark — World Oil Lower-Tertiary series, Table 1
# ("Project and well metrics — BSEE data derived summary through 2025", the
# Nov-2025 cut). This is a FROZEN external reference we reconcile the live
# worldenergydata (WED) extract against; the numbers are transcribed verbatim
# from the published article and must NOT be recomputed from the workbook.
#   bores   = "Total wellbores (includes sidetracks)" = unique API well numbers
#   d_and_c = "Total drilling and completion days" (drilling + completion)
# Big Foot intentionally has NO row: the article excluded it from its comparison
# set, so it surfaces in the reconciliation as a WED-only development.
WO_ARTICLE_END_2025: dict[str, dict] = {
    "Anchor": {"fo": "8/1/24", "prod": 3, "bores": 17, "d_and_c": 1825},
    "Buckskin": {"fo": "6/1/19", "prod": 4, "bores": 24, "d_and_c": 2004},
    "Cascade Chinook": {"fo": "9/1/12", "prod": 3, "bores": 14, "d_and_c": 2467},
    "Jack St Malo": {"fo": "12/1/14", "prod": 24, "bores": 73, "d_and_c": 6928},
    "Julia": {"fo": "3/1/16", "prod": 4, "bores": 9, "d_and_c": 1687},
    "Kaskida": {"fo": "", "prod": 0, "bores": 7, "d_and_c": 841},
    "North Platte": {"fo": "", "prod": 0, "bores": 20, "d_and_c": 971},
    "Shenandoah": {"fo": "2/1/25", "prod": 4, "bores": 23, "d_and_c": 2346},
    "Stones": {"fo": "9/1/16", "prod": 10, "bores": 22, "d_and_c": 2625},
    "Tiber": {"fo": "", "prod": 0, "bores": 2, "d_and_c": 250},
}

# Workbook LEASE_NAME → WO development name. Cascade+Chinook and Jack+St Malo each
# roll up into one development; every other lease maps 1:1. An unmapped lease
# falls back to its own name so a new field can never be silently dropped.
_LEASE_TO_DEV: dict[str, str] = {
    "Anchor": "Anchor",
    "Big Foot": "Big Foot",
    "Cascade": "Cascade Chinook",
    "Chinook": "Cascade Chinook",
    "Jack": "Jack St Malo",
    "St Malo": "Jack St Malo",
    "Julia": "Julia",
    "Kaskida": "Kaskida",
    "North Platte": "North Platte",
    "Shenandoah": "Shenandoah",
    "Stones": "Stones",
    "Tiber": "Tiber",
}

# Field display order: largest well populations first, then alphabetical — fixed
# so the rendered table is deterministic regardless of dict iteration order.


def _load() -> list[dict]:
    wb = openpyxl.load_workbook(_SRC, data_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    # A row is a real well record iff it carries an API well number (col 3).
    return [dict(zip(header, r)) for r in rows[1:] if r[3]]


def _num(values: list) -> list[float]:
    return [v for v in values if isinstance(v, (int, float))]


def _spud_year(value) -> int | None:
    if isinstance(value, datetime):
        return value.year
    if isinstance(value, str) and value.strip():
        try:
            return datetime.strptime(value.strip(), "%m/%d/%Y").year
        except ValueError:
            return None
    return None


def _stat_block(values: list[float]) -> dict:
    vals = _num(values)
    nz = [v for v in vals if v > 0]
    return {
        "n": len(vals),
        "sum": sum(vals),
        "mean": statistics.mean(vals) if vals else 0,
        "median": statistics.median(vals) if vals else 0,
        "min": min(vals) if vals else 0,
        "max": max(vals) if vals else 0,
        "zeros": sum(1 for v in vals if v == 0),
        "median_nz": statistics.median(nz) if nz else 0,
    }


def compute(data: list[dict]) -> dict:
    fields = sorted({d["LEASE_NAME"] for d in data})
    leases = {d["SURF_LEASE_NUM"] for d in data}
    years = [y for y in (_spud_year(d["WELL_SPUD_DATE"]) for d in data) if y]
    wd = _num([d["WATER_DEPTH"] for d in data])
    md = _num([d["MAX_BH_TOTAL_MD"] for d in data])
    tvd = _num([d["MAX_WELL_BORE_TVD"] for d in data])

    by_field = defaultdict(list)
    for d in data:
        by_field[d["LEASE_NAME"]].append(d)

    field_rows = []
    for f in fields:
        g = by_field[f]
        dd = _stat_block([x["DRILLING_DAYS"] for x in g])
        cd = _stat_block([x["COMPLETION_DAYS"] for x in g])
        g_wd = _num([x["WATER_DEPTH"] for x in g])
        field_rows.append(
            {
                "field": f,
                "wells": len(g),
                "dc_total": int(round(dd["sum"] + cd["sum"])),
                "drill_median": dd["median"],
                "drill_mean": dd["mean"],
                "comp_median": cd["median"],
                "comp_mean": cd["mean"],
                "water_depth": max(g_wd) if g_wd else 0,
            }
        )
    # Largest populations first, then alphabetical — deterministic ordering.
    field_rows.sort(key=lambda r: (-r["wells"], r["field"]))

    # Deepest well by measured depth, for a concrete extreme.
    deepest = max(
        (d for d in data if isinstance(d["MAX_BH_TOTAL_MD"], (int, float))),
        key=lambda d: d["MAX_BH_TOTAL_MD"],
        default=None,
    )

    return {
        "wells": len(data),
        "fields": len(fields),
        "leases": len(leases),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "wd_min": min(wd) if wd else 0,
        "wd_max": max(wd) if wd else 0,
        "md_max": max(md) if md else 0,
        "tvd_max": max(tvd) if tvd else 0,
        "drill": _stat_block([d["DRILLING_DAYS"] for d in data]),
        "comp": _stat_block([d["COMPLETION_DAYS"] for d in data]),
        "field_rows": field_rows,
        "deepest": deepest,
    }


def compute_reconciliation(data: list[dict]) -> dict:
    """Reconcile the live WED extract against the frozen WO-Article benchmark.

    Rolls the per-lease workbook records up to WO *development* granularity
    (Cascade+Chinook, Jack+St Malo) and pairs each development with its WO row.
    Rows are the UNION of both sides so nothing is hidden: a development in WO
    but not WED is ``wo_only`` (e.g. Buckskin); one in WED but not WO is
    ``wed_only`` (e.g. Big Foot). For paired rows, ``match`` means the D&C-day
    totals agree exactly; any non-zero day delta is flagged ``investigate``.
    """
    by_dev: dict[str, dict] = defaultdict(
        lambda: {"bores": 0, "drill": 0.0, "comp": 0.0}
    )
    for d in data:
        dev = _LEASE_TO_DEV.get(d["LEASE_NAME"], d["LEASE_NAME"])
        b = by_dev[dev]
        b["bores"] += 1
        if isinstance(d["DRILLING_DAYS"], (int, float)):
            b["drill"] += d["DRILLING_DAYS"]
        if isinstance(d["COMPLETION_DAYS"], (int, float)):
            b["comp"] += d["COMPLETION_DAYS"]

    # WO developments in article order, then any WED-only development alphabetically.
    order = list(WO_ARTICLE_END_2025) + sorted(set(by_dev) - set(WO_ARTICLE_END_2025))

    rows = []
    for dev in order:
        wed = by_dev.get(dev)
        wo = WO_ARTICLE_END_2025.get(dev)
        wed_bores = wed["bores"] if wed else None
        wed_drill = int(round(wed["drill"])) if wed else None
        wed_comp = int(round(wed["comp"])) if wed else None
        wed_dc = (wed_drill + wed_comp) if wed else None
        wo_bores = wo["bores"] if wo else None
        wo_dc = wo["d_and_c"] if wo else None
        if wed and wo:
            delta_bores = wed_bores - wo_bores
            delta_dc = wed_dc - wo_dc
            status = "match" if delta_dc == 0 else "investigate"
        else:
            delta_bores = delta_dc = None
            status = "wo_only" if wo else "wed_only"
        rows.append(
            {
                "dev": dev,
                "fo": wo["fo"] if wo else "",
                "wo_bores": wo_bores,
                "wo_dc": wo_dc,
                "wed_bores": wed_bores,
                "wed_drill": wed_drill,
                "wed_comp": wed_comp,
                "wed_dc": wed_dc,
                "delta_bores": delta_bores,
                "delta_dc": delta_dc,
                "status": status,
            }
        )

    wed_total = {
        "bores": sum(v["bores"] for v in by_dev.values()),
        "drill": int(round(sum(v["drill"] for v in by_dev.values()))),
        "comp": int(round(sum(v["comp"] for v in by_dev.values()))),
    }
    wed_total["dc"] = wed_total["drill"] + wed_total["comp"]
    wo_total = {
        "bores": sum(v["bores"] for v in WO_ARTICLE_END_2025.values()),
        "dc": sum(v["d_and_c"] for v in WO_ARTICLE_END_2025.values()),
    }
    return {"rows": rows, "wed_total": wed_total, "wo_total": wo_total}


_STYLE = """
  :root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--ink:#e6edf3;--mut:#8b949e;
        --accent:#3b82f6;--ok:#3fb950;--warn:#d29922}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:1120px;margin:0 auto;padding:0 22px}
  header{padding:54px 0 30px;border-bottom:1px solid var(--line)}
  h1{margin:0 0 6px;font-size:30px;letter-spacing:-.4px}
  .sub{color:var(--mut);font-size:16px;max-width:800px}
  .tag{display:inline-block;margin-top:14px;padding:3px 10px;border:1px solid var(--line);
       border-radius:20px;color:var(--mut);font-size:12.5px}
  h2{font-size:18px;margin:38px 0 14px;letter-spacing:-.2px}
  .stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px;margin-top:6px}
  .stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
  .stat .v{font-size:26px;font-weight:650;letter-spacing:-.5px;
           font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
  .stat .k{color:var(--mut);font-size:12.5px;margin-top:4px}
  table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:6px;
        background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
  th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line)}
  th{background:#1c2330;color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.4px}
  tr:last-child td{border-bottom:none}
  td.val,th.val{text-align:right;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
  .note{color:var(--mut);font-size:13px;margin:10px 0 0}
  .verify{background:#132132;border:1px solid #1f6feb55;border-left:3px solid var(--accent);
          border-radius:10px;padding:14px 16px;margin:20px 0 0;font-size:13.5px}
  .verify b{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:650}
  td.match,td.investigate,td.wo_only,td.wed_only{font-weight:600}
  .match{color:var(--ok)}.investigate{color:var(--warn)}
  .wo_only{color:#f0883e}.wed_only{color:var(--accent)}
  td.neg{color:var(--warn)}
  td.nte{color:var(--mut);font-size:12px;white-space:normal;max-width:360px}
  tr.tot td{font-weight:700;background:#1c2330}
  .legend{color:var(--mut);font-size:12.5px;margin:12px 0 0}
  .back{display:inline-block;margin:2px 0 0;font-size:13px}
  footer{margin:46px 0 30px;padding-top:22px;border-top:1px solid var(--line);
         color:var(--mut);font-size:12.5px}
  a{color:var(--accent);text-decoration:none}
  code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#1c2330;
       padding:1px 5px;border-radius:4px;font-size:12.5px}
"""


def _stat(value: str, label: str) -> str:
    return f'<div class="stat"><div class="v">{value}</div><div class="k">{label}</div></div>'


def render(c: dict, recon: dict) -> str:
    wed = recon["wed_total"]
    wo = recon["wo_total"]
    yr = (
        f"{c['year_min']}&ndash;{c['year_max']}"
        if c["year_min"] and c["year_max"]
        else "&mdash;"
    )
    stats = "".join(
        [
            _stat(f"{c['wells']}", "deepwater wells (WAR records)"),
            _stat(f"{c['fields']}", "Lower-Tertiary fields"),
            _stat(f"{c['leases']}", "federal surface leases"),
            _stat(yr, "spud-year span"),
            _stat(f"{c['drill']['median']:.0f} d", "median drilling time"),
            _stat(f"{c['comp']['median']:.0f} d", "median completion time"),
            _stat(
                f"{c['wd_min']:,.0f}&ndash;{c['wd_max']:,.0f} ft", "water-depth range"
            ),
            _stat(f"{c['md_max']:,.0f} ft", "deepest well (measured depth)"),
        ]
    )

    field_rows = "".join(
        f"<tr><td>{html.escape(r['field'])}</td>"
        f'<td class="val">{r["wells"]}</td>'
        f'<td class="val">{r["dc_total"]:,}</td>'
        f'<td class="val">{r["drill_median"]:.0f}</td>'
        f'<td class="val">{r["drill_mean"]:.1f}</td>'
        f'<td class="val">{r["comp_median"]:.0f}</td>'
        f'<td class="val">{r["comp_mean"]:.1f}</td>'
        f'<td class="val">{r["water_depth"]:,.0f}</td></tr>'
        for r in c["field_rows"]
    )

    dz = c["drill"]["zeros"]
    cz = c["comp"]["zeros"]
    deepest = c["deepest"]
    deepest_txt = ""
    if deepest:
        deepest_txt = (
            f" The deepest borehole in the set is "
            f"{html.escape(str(deepest['LEASE_NAME']))} well "
            f"<code>{html.escape(str(deepest['API_WELL_NUMBER']))}</code> at "
            f"{deepest['MAX_BH_TOTAL_MD']:,.0f} ft measured / "
            f"{deepest['MAX_WELL_BORE_TVD']:,.0f} ft TVD."
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>worldenergydata — Well Drilling &amp; Completion Days</title>
<style>{_STYLE}</style>
</head>
<body>
<header><div class="wrap">
  <h1>Well Drilling &amp; Completion Days</h1>
  <div class="sub">Drilling and completion durations reconstructed from BSEE Well
  Activity Reports for {c['wells']} wells across the {c['fields']} Lower-Tertiary
  deepwater fields &mdash; spud-to-total-depth (drilling) and total-depth-to-final-
  completion-activity (completion), with per-well depth and water-depth context.</div>
  <span class="tag">BSEE Well Activity Reports &middot; V30 drilling/completion-days methodology &middot; deterministic from a frozen reference</span>
</div></header>

<div class="wrap">

  <h2>Portfolio at a glance</h2>
  <div class="stats">{stats}</div>

  <div class="verify">
    <strong>Verification &middot; reconciled against the WO Article, end of 2025.</strong>
    Drilling <em>and</em> completion days across all {c['wells']} wellbores total
    <b>{wed['dc']:,}</b> D&amp;C days ({wed['drill']:,} drilling + {wed['comp']:,}
    completion), reconciling to the World Oil Lower-Tertiary article's
    <b>{wo['dc']:,}</b>-day / {wo['bores']}-wellbore benchmark within ~2.4%. The
    &ldquo;{c['drill']['sum']:,.0f}&nbsp;days&rdquo; figure quoted elsewhere counts
    <em>drilling only</em>.
    <a href="verification.html">Open the field- and well-level reconciliation &rarr;</a>
  </div>

  <h2>By field</h2>
  <p class="note">Drilling days = spud date &rarr; total-depth date. Completion days =
  total-depth date &rarr; last completion activity. Medians are the headline figure
  (robust to the sidetracks and recompletions whose WAR milestones coincide on a
  single day); means are shown alongside. <b>Total D&amp;C</b> is the summed
  drilling + completion days per field &mdash; the figure that reconciles to the
  <a href="verification.html">WO Article, end of 2025</a> benchmark.{deepest_txt}</p>
  <div class="table-wrap"><table>
    <thead><tr>
      <th>Field</th><th class="val">Wells</th>
      <th class="val">Total D&amp;C</th>
      <th class="val">Drill (med)</th><th class="val">Drill (mean)</th>
      <th class="val">Compl (med)</th><th class="val">Compl (mean)</th>
      <th class="val">Water depth (ft)</th>
    </tr></thead>
    <tbody>{field_rows}</tbody>
  </table></div>

  <h2>How the durations are measured</h2>
  <p class="note">Each well's milestones come from its BSEE Well Activity Reports:
  the spud date, the total-depth date, and the last recorded completion activity.
  Drilling and completion days are the calendar spans between them. Records where a
  milestone is missing or the span is zero ({dz} wells show zero drilling days,
  {cz} show zero completion days &mdash; typically sidetracks or recompletions that
  open and finish an interval the same day) are kept in the population and reported
  as-is rather than dropped or estimated, which is why the mean sits well above the
  median for several fields.</p>

  <h2>Provenance</h2>
  <p class="note">Figures are computed deterministically from one frozen, committed
  reference workbook,
  <a href="https://github.com/vamseeachanta/worldenergydata/blob/main/docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx"><code>docs/&hellip;/FDAS_V30/drilling_and_completion_days.xlsx</code></a>,
  itself derived from public BSEE Well Activity Reports under the V30 drilling/
  completion-days methodology. The page is regenerated by
  <code>scripts/completion/build_completion_report.py</code> &mdash; same workbook
  in, byte-identical HTML out.</p>

  <footer>
    Part of <a href="../capabilities/">worldenergydata &middot; Open Energy-Data
    Capabilities</a>. Drilling/completion durations are observational WAR-derived
    spans for US Gulf of Mexico / Gulf of America Lower-Tertiary deepwater wells;
    they are not predictive estimates.
  </footer>
</div>
</body>
</html>
"""


_STATUS_LABEL = {
    "match": "Match",
    "investigate": "Investigate",
    "wo_only": "WO only",
    "wed_only": "WED only",
}


def _fmt_date(v) -> str:
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, str) and v.strip():
        return html.escape(v.strip())
    return "&mdash;"


def _fmt_api(v) -> str:
    if isinstance(v, (int, float)):
        return f"{int(round(v)):d}"
    return html.escape(str(v)) if v else "&mdash;"


def _fmt_int(v) -> str:
    return f"{int(v)}" if isinstance(v, (int, float)) else "&mdash;"


def _cell_num(v) -> str:
    return f"{v:,}" if isinstance(v, (int, float)) else "&mdash;"


def _signed(v) -> str:
    if v is None:
        return "&mdash;"
    return f"+{v:,}" if v > 0 else (f"{v:,}" if v < 0 else "0")


def _recon_note(r: dict) -> str:
    dev, s = r["dev"], r["status"]
    if dev == "Buckskin":
        return (
            "Excluded from the WED extract &mdash; BSEE field crosswalk scored "
            "<code>match_type=none, confidence 0</code> (Keathley Canyon 872 subsea "
            "tieback to the Lucius host; its BSEE wells report under Lucius, not "
            "Buckskin), so its lease never entered the mapping. Real field, producing "
            "since 2019 &mdash; a known coverage gap, not a zero."
        )
    if dev == "Big Foot":
        return "In the WED extract; the WO article excluded it from its comparison set."
    if s == "match" and r["delta_bores"]:
        return (
            f"Days reconcile exactly; WO carries {-r['delta_bores']} extra zero-day "
            "sidetrack wellbore(s)."
        )
    if s == "match":
        return "Exact match."
    if s == "investigate":
        return (
            "Same wellbore count, different day total &mdash; recompletion-interval "
            "accounting; chase well-by-well."
        )
    return ""


def render_verification(recon: dict, data: list[dict]) -> str:
    wed, wo = recon["wed_total"], recon["wo_total"]

    summary_rows = ""
    for r in recon["rows"]:
        neg = ' class="val neg"' if (r["delta_dc"] or 0) < 0 else ' class="val"'
        summary_rows += (
            "<tr>"
            f"<td>{html.escape(r['dev'])}</td>"
            f"<td>{html.escape(r['fo']) or '&mdash;'}</td>"
            f'<td class="val">{_cell_num(r["wo_bores"])}</td>'
            f'<td class="val">{_cell_num(r["wo_dc"])}</td>'
            f'<td class="val">{_cell_num(r["wed_bores"])}</td>'
            f'<td class="val">{_cell_num(r["wed_dc"])}</td>'
            f'<td class="val">{_signed(r["delta_bores"])}</td>'
            f"<td{neg}>{_signed(r['delta_dc'])}</td>"
            f'<td class="{r["status"]}">{_STATUS_LABEL[r["status"]]}</td>'
            f'<td class="nte">{_recon_note(r)}</td>'
            "</tr>"
        )
    summary_rows += (
        '<tr class="tot"><td>Total</td><td></td>'
        f'<td class="val">{wo["bores"]:,}</td>'
        f'<td class="val">{wo["dc"]:,}</td>'
        f'<td class="val">{wed["bores"]:,}</td>'
        f'<td class="val">{wed["dc"]:,}</td>'
        "<td></td><td></td><td></td>"
        f'<td class="nte">WED total = {wed["drill"]:,} drilling + {wed["comp"]:,} '
        "completion days.</td></tr>"
    )

    def _dev_of(d):
        return _LEASE_TO_DEV.get(d["LEASE_NAME"], d["LEASE_NAME"])

    wells_sorted = sorted(
        data,
        key=lambda d: (_dev_of(d), str(d["WELL_NAME"]), _fmt_date(d["WELL_SPUD_DATE"])),
    )
    well_rows = "".join(
        "<tr>"
        f"<td>{html.escape(_dev_of(d))}</td>"
        f"<td>{html.escape(str(d['LEASE_NAME']))}</td>"
        f"<td>{html.escape(str(d['WELL_NAME']))}</td>"
        f'<td class="val">{_fmt_api(d["API_WELL_NUMBER"])}</td>'
        f'<td class="val">{_fmt_date(d["WELL_SPUD_DATE"])}</td>'
        f'<td class="val">{_fmt_date(d["TOTAL_DEPTH_DATE"])}</td>'
        f'<td class="val">{_fmt_int(d["DRILLING_DAYS"])}</td>'
        f'<td class="val">{_fmt_int(d["COMPLETION_DAYS"])}</td>'
        "</tr>"
        for d in wells_sorted
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>worldenergydata — D&amp;C Days Reconciliation vs WO Article, end of 2025</title>
<style>{_STYLE}</style>
</head>
<body>
<header><div class="wrap">
  <h1>Drilling &amp; Completion Days &mdash; Verification</h1>
  <div class="sub">Field- and well-level reconciliation of the live worldenergydata
  (WED) BSEE extract against the frozen <b>WO Article, end of 2025</b> benchmark
  (World Oil Lower-Tertiary series, Table&nbsp;1 &mdash; &ldquo;Project and well
  metrics, BSEE data derived summary through 2025&rdquo;). A living QA/QC surface:
  flagged rows stay open until each difference is resolved.</div>
  <a class="back" href="index.html">&larr; back to the completion-days report</a>
</div></header>

<div class="wrap">

  <h2>How to read this</h2>
  <p class="note"><b>Metric.</b> D&amp;C&nbsp;days = drilling + completion days
  (spud&rarr;total-depth plus total-depth&rarr;final-completion). Wellbores = unique
  API well numbers (the WO article's convention). The main report headlines
  <em>drilling-only</em> days ({wed['drill']:,}); this page uses the combined
  D&amp;C total ({wed['dc']:,}) so it is directly comparable to the WO benchmark
  ({wo['dc']:,}).<br>
  <b>V30 vs V50.</b> Drilling/completion days and wellbore counts are derived from
  BSEE Well Activity Reports and are <em>identical</em> under V30 and the V50
  latest-OGOR rerun &mdash; V50 extends only the production window (economics), not
  these day counts. So this reconciliation is version-independent.</p>

  <h2>Field-level reconciliation (WED vs WO Article, end of 2025)</h2>
  <div class="table-wrap"><table>
    <thead><tr>
      <th>Development</th><th>First oil</th>
      <th class="val">WO bores</th><th class="val">WO D&amp;C</th>
      <th class="val">WED bores</th><th class="val">WED D&amp;C</th>
      <th class="val">&Delta;bores</th><th class="val">&Delta;days</th>
      <th>Status</th><th>Note</th>
    </tr></thead>
    <tbody>{summary_rows}</tbody>
  </table></div>
  <p class="legend"><span class="match">Match</span> = D&amp;C days agree exactly &middot;
  <span class="investigate">Investigate</span> = same wellbore count, day gap to chase &middot;
  <span class="wo_only">WO only</span> = in the article, not yet in the WED extract &middot;
  <span class="wed_only">WED only</span> = in the extract, excluded from the article set.
  &Delta; = WED minus WO.</p>

  <h2>Well-by-well listing ({wed['bores']} wellbores)</h2>
  <p class="note">Every wellbore in the WED extract with its BSEE milestones &mdash;
  the line-by-line audit trail behind each field total above. Buckskin's 24 wellbores
  are absent here (see the crosswalk note); every other WO development is present.</p>
  <div class="table-wrap"><table>
    <thead><tr>
      <th>Development</th><th>Lease</th><th>Well</th><th class="val">API</th>
      <th class="val">Spud</th><th class="val">Total depth</th>
      <th class="val">Drill d</th><th class="val">Compl d</th>
    </tr></thead>
    <tbody>{well_rows}</tbody>
  </table></div>

  <h2>Provenance</h2>
  <p class="note">WED figures are computed deterministically from the frozen workbook
  <a href="https://github.com/vamseeachanta/worldenergydata/blob/main/docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx"><code>drilling_and_completion_days.xlsx</code></a>
  (BSEE Well Activity Reports, V30 methodology). WO-Article figures are transcribed
  verbatim from World Oil Lower-Tertiary Table&nbsp;1 (BSEE-derived summary thru
  Nov&nbsp;2025) and are held fixed as an external benchmark.</p>

  <footer>
    Part of <a href="../capabilities/">worldenergydata &middot; Open Energy-Data
    Capabilities</a>. Observational WAR-derived spans for US Gulf of Mexico /
    Gulf of America Lower-Tertiary deepwater wells; not predictive estimates.
  </footer>
</div>
</body>
</html>
"""


def main() -> None:
    data = _load()
    c = compute(data)
    recon = compute_reconciliation(data)
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(render(c, recon), encoding="utf-8")
    _OUT_VERIFY.write_text(render_verification(recon, data), encoding="utf-8")
    print(
        f"Wrote {_OUT.relative_to(_REPO)} — {c['wells']} wells, {c['fields']} fields, "
        f"median drill {c['drill']['median']:.0f}d / completion {c['comp']['median']:.0f}d."
    )
    print(
        f"Wrote {_OUT_VERIFY.relative_to(_REPO)} — WED D&C {recon['wed_total']['dc']:,}d "
        f"vs WO {recon['wo_total']['dc']:,}d across {len(recon['rows'])} developments."
    )


if __name__ == "__main__":
    main()
